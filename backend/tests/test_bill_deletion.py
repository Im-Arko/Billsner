from unittest.mock import Mock

import pytest
from sqlalchemy import func, select

from app.models.bill import BillStatus
from app.models.embedding import BillEmbedding
from app.models.expense import Expense
from app.models.ocr_result import OCRResult
from app.services import bill_service
from tests.test_bill_processing import make_bill


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["bills", "expenses"])
async def test_delete_clears_duplicate_references_and_all_bill_data(
    client, async_session, test_user, tmp_path, monkeypatch, route,
):
    bill = await make_bill(async_session, test_user, tmp_path, BillStatus.COMPLETED)
    bill_id = bill.id
    path = tmp_path / "bill.png"
    expense = Expense(user_id=test_user.id, bill_id=bill_id, total_amount=100, currency="INR")
    async_session.add(expense)
    await async_session.flush()
    duplicate = Expense(user_id=test_user.id, total_amount=100, currency="INR",
                        is_duplicate=True, duplicate_of_id=expense.id, duplicate_confidence=0.99)
    async_session.add_all([
        duplicate,
        OCRResult(bill_id=bill_id, raw_text="receipt", confidence_score=0.9),
        BillEmbedding(bill_id=bill_id, chroma_id=f"bill_{bill_id}"),
    ])
    await async_session.commit()
    cleanup = Mock()
    monkeypatch.setattr(bill_service, "delete_bill_embeddings", cleanup)

    response = await client.delete(f"/api/v1/{route}/{bill_id}")
    assert response.status_code == 204
    await async_session.refresh(duplicate)
    duplicate = (await async_session.scalars(select(Expense))).one()
    assert not duplicate.is_duplicate
    assert duplicate.duplicate_of_id is None
    assert duplicate.duplicate_confidence is None
    for model in (OCRResult, BillEmbedding):
        assert (await async_session.scalar(select(func.count()).select_from(model))) == 0
    assert not path.exists()
    cleanup.assert_called_once_with(bill_id, test_user.id)
    assert (await client.get(f"/api/v1/bills/{bill_id}")).status_code == 404


@pytest.mark.asyncio
async def test_foreign_bill_cannot_be_deleted(client, async_session, test_user, tmp_path, monkeypatch):
    bill = await make_bill(async_session, test_user, tmp_path, BillStatus.COMPLETED)
    # Use another valid owner, while the authenticated user remains unchanged.
    from app.models.user import User

    other = User(email="other@example.com", hashed_password="hashed", full_name="Other")
    async_session.add(other)
    await async_session.flush()
    bill.user_id = other.id
    await async_session.commit()
    cleanup = Mock()
    monkeypatch.setattr(bill_service, "delete_bill_embeddings", cleanup)
    assert (await client.delete(f"/api/v1/bills/{bill.id}")).status_code == 404
    assert (tmp_path / "bill.png").exists()
    cleanup.assert_not_called()


@pytest.mark.asyncio
async def test_processing_bill_cannot_be_deleted(client, async_session, test_user, tmp_path):
    bill = await make_bill(async_session, test_user, tmp_path, BillStatus.PROCESSING)
    response = await client.delete(f"/api/v1/bills/{bill.id}")
    assert response.status_code == 409
    assert (tmp_path / "bill.png").exists()


@pytest.mark.asyncio
async def test_summary_includes_processing_failure(client, async_session, test_user, tmp_path):
    bill = await make_bill(async_session, test_user, tmp_path, BillStatus.FAILED)
    bill.error_message = "Bill couldn't be processed: no valid positive total amount was found."
    await async_session.commit()
    response = await client.get("/api/v1/expenses/summary")
    assert response.status_code == 200
    assert response.json()["recent_bills"][0]["error_message"] == bill.error_message


@pytest.mark.asyncio
async def test_failed_bill_cleanup_removes_uncommitted_vectors(
    client, async_session, test_user, tmp_path, monkeypatch,
):
    bill = await make_bill(async_session, test_user, tmp_path, BillStatus.FAILED)
    cleanup = Mock()
    monkeypatch.setattr(bill_service, "delete_bill_embeddings", cleanup)
    response = await client.delete(f"/api/v1/bills/{bill.id}")
    assert response.status_code == 204
    cleanup.assert_called_once_with(bill.id, test_user.id)
