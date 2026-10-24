from types import SimpleNamespace
from unittest.mock import Mock
import subprocess
import sys
import time
import threading

import pytest
from sqlalchemy import func, select

from app.ai.llm_extractor import ExtractionSchema
from app.models.bill import Bill, BillStatus
from app.models.embedding import BillEmbedding
from app.models.expense import Expense
from app.models.ocr_result import OCRResult
from app.services import bill_service
from app.tasks import runner as task_module


async def make_bill(session, user, tmp_path, status=BillStatus.PENDING):
    path = tmp_path / "bill.png"
    path.write_bytes(b"test receipt")
    bill = Bill(user_id=user.id, original_filename="bill.png", stored_path=str(path),
                mime_type="image/png", file_size_bytes=12, status=status)
    session.add(bill)
    await session.commit()
    return bill


@pytest.fixture
def pipeline_ai(monkeypatch):
    monkeypatch.setattr(bill_service, "extract_text_from_file", lambda _: SimpleNamespace(
        raw_text="Total INR 100.00", confidence_score=0.9, preprocessing_applied=[]))
    monkeypatch.setattr(bill_service, "extract_structured_data", lambda _: ExtractionSchema(total_amount=100))
    upsert = Mock(return_value="bill_test")
    cleanup = Mock()
    monkeypatch.setattr(bill_service, "upsert_bill_embedding", upsert)
    monkeypatch.setattr(bill_service, "delete_bill_embeddings", cleanup)
    monkeypatch.setattr(bill_service, "find_duplicates", lambda *args: [])
    return upsert, cleanup


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [None, 0, -1, float("nan"), float("inf"), 0.001])
async def test_unusable_total_fails_without_partial_records(
    async_session, test_user, tmp_path, monkeypatch, pipeline_ai, amount,
):
    bill = await make_bill(async_session, test_user, tmp_path)
    bill_id = bill.id
    monkeypatch.setattr(bill_service, "extract_structured_data", lambda _: ExtractionSchema(total_amount=amount))
    with pytest.raises(bill_service.BillProcessingError):
        await bill_service.process_bill_pipeline(async_session, bill_id)
    await async_session.refresh(bill)
    assert bill.status == BillStatus.FAILED
    assert "couldn't be processed" in bill.error_message
    for model in (Expense, OCRResult, BillEmbedding):
        assert (await async_session.scalar(select(func.count()).select_from(model))) == 0
    pipeline_ai[0].assert_not_called()


@pytest.mark.asyncio
async def test_processing_succeeds_and_repeated_delivery_is_noop(
    async_session, test_user, tmp_path, monkeypatch, pipeline_ai,
):
    bill = await make_bill(async_session, test_user, tmp_path)
    monkeypatch.setattr(bill_service, "extract_structured_data", lambda _: ExtractionSchema(total_amount=100))
    await bill_service.process_bill_pipeline(async_session, bill.id)
    await async_session.refresh(bill)
    assert bill.status == BillStatus.COMPLETED
    bill_id = bill.id
    await bill_service.process_bill_pipeline(async_session, bill_id)
    assert (await async_session.scalar(select(func.count()).select_from(Expense))) == 1
    pipeline_ai[0].assert_called_once()


@pytest.mark.asyncio
async def test_failed_flush_rolls_back_before_saving_failure(
    async_session, test_user, tmp_path, monkeypatch, pipeline_ai,
):
    bill = await make_bill(async_session, test_user, tmp_path)
    bill_id = bill.id
    # Simulate a previous OCR row to trigger a real UNIQUE constraint failure.
    async_session.add(OCRResult(bill_id=bill_id, raw_text="old", confidence_score=0.9))
    await async_session.commit()
    with pytest.raises(Exception, match="UNIQUE constraint failed"):
        await bill_service.process_bill_pipeline(async_session, bill_id)
    await async_session.refresh(bill)
    assert bill.status == BillStatus.FAILED
    assert "UNIQUE constraint failed" in bill.error_message
    assert (await async_session.scalar(select(func.count()).select_from(Expense))) == 0


@pytest.mark.asyncio
async def test_deleted_vector_candidate_is_not_flagged_duplicate(
    async_session, test_user, tmp_path, monkeypatch, pipeline_ai,
):
    bill = await make_bill(async_session, test_user, tmp_path)
    monkeypatch.setattr(bill_service, "extract_structured_data", lambda _: ExtractionSchema(total_amount=100))
    monkeypatch.setattr(bill_service, "find_duplicates", lambda *args: [
        {"similarity_score": 0.99, "metadata": {"expense_id": "999999"}}
    ])
    await bill_service.process_bill_pipeline(async_session, bill.id)
    expense = (await async_session.scalars(select(Expense))).one()
    assert not expense.is_duplicate
    assert expense.duplicate_of_id is None


def test_task_kills_blocked_process_and_marks_failure(monkeypatch):
    process = Mock()
    process.__enter__ = Mock(return_value=process)
    process.__exit__ = Mock(return_value=False)
    process.wait.return_value = 0
    monkeypatch.setattr(task_module.time, "monotonic", Mock(side_effect=[0, 600]))
    monkeypatch.setattr(task_module.subprocess, "Popen", Mock(return_value=process))
    mark_failed = Mock()
    monkeypatch.setattr(task_module, "_persist_failure", mark_failed)
    with pytest.raises(TimeoutError, match="timed out"):
        task_module.process_bill_task(42)
    process.kill.assert_called_once()
    mark_failed.assert_called_once()


@pytest.mark.asyncio
async def test_vector_failure_removes_partial_expense_and_embedding(
    async_session, test_user, tmp_path, monkeypatch, pipeline_ai,
):
    bill = await make_bill(async_session, test_user, tmp_path)
    bill_id, user_id = bill.id, test_user.id
    monkeypatch.setattr(bill_service, "extract_structured_data", lambda _: ExtractionSchema(total_amount=100))
    monkeypatch.setattr(bill_service, "find_duplicates", Mock(side_effect=RuntimeError("vector failure")))
    with pytest.raises(RuntimeError, match="vector failure"):
        await bill_service.process_bill_pipeline(async_session, bill_id)
    await async_session.refresh(bill)
    assert bill.status == BillStatus.FAILED
    assert bill.error_message == "vector failure"
    assert (await async_session.scalar(select(func.count()).select_from(Expense))) == 0
    pipeline_ai[1].assert_called_once_with(bill_id, user_id)


def test_task_returns_success_for_completed_subprocess(monkeypatch):
    process = Mock()
    process.__enter__ = Mock(return_value=process)
    process.__exit__ = Mock(return_value=False)
    process.wait.return_value = 0
    monkeypatch.setattr(task_module.subprocess, "Popen", Mock(return_value=process))
    assert task_module.process_bill_task(42) == "processed bill 42"
    process.kill.assert_not_called()


def test_shutdown_allows_a_completed_child_to_finish_cleanup(monkeypatch):
    process = Mock()
    process.__enter__ = Mock(return_value=process)
    process.__exit__ = Mock(return_value=False)
    process.wait.side_effect = [subprocess.TimeoutExpired("bill worker", 0.25), 0]
    monkeypatch.setattr(task_module.subprocess, "Popen", Mock(return_value=process))
    persist_failure = Mock()
    monkeypatch.setattr(task_module, "_persist_failure", persist_failure)
    stop = threading.Event()
    stop.set()
    assert task_module.process_bill_task(42, stop) == "processed bill 42"
    process.kill.assert_not_called()
    persist_failure.assert_not_called()


def test_task_deadline_stops_a_real_blocking_process(monkeypatch):
    real_popen = subprocess.Popen
    processes = []

    def start_blocked_process(*args, **kwargs):
        process = real_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(task_module.subprocess, "Popen", start_blocked_process)
    monkeypatch.setattr(task_module.settings, "BILL_PROCESSING_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(task_module, "_persist_failure", Mock())
    start = time.monotonic()
    with pytest.raises(TimeoutError, match="timed out after 1s"):
        task_module.process_bill_task(42)
    assert time.monotonic() - start < 10
    assert processes[0].poll() is not None
