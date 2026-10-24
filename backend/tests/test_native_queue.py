import asyncio
import threading

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.bill import Bill, BillStatus
from app.tasks import runner
from tests.test_bill_processing import make_bill


@pytest.mark.asyncio
async def test_interrupted_jobs_are_requeued(async_session, async_engine, test_user, tmp_path, monkeypatch):
    bill = await make_bill(async_session, test_user, tmp_path, BillStatus.PROCESSING)
    monkeypatch.setattr(runner, "AsyncSessionLocal", async_sessionmaker(async_engine, expire_on_commit=False))
    await runner.recover_interrupted_bills()
    await async_session.refresh(bill)
    assert bill.status == BillStatus.PENDING


@pytest.mark.asyncio
async def test_worker_picks_up_committed_pending_jobs(async_session, async_engine, test_user, tmp_path, monkeypatch):
    bill = await make_bill(async_session, test_user, tmp_path)
    monkeypatch.setattr(runner, "AsyncSessionLocal", async_sessionmaker(async_engine, expire_on_commit=False))
    stop = threading.Event()
    processed = []

    def process(bill_id, stop_event):
        processed.append(bill_id)
        stop_event.set()

    monkeypatch.setattr(runner, "process_bill_task", process)
    await asyncio.wait_for(runner.run_pending_bills(stop), timeout=3)
    assert processed == [bill.id]


@pytest.mark.asyncio
async def test_upload_is_queued_without_a_broker(client, async_session, test_user, tmp_path, monkeypatch):
    from app.api.v1 import bills

    monkeypatch.setattr(bills.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(bills.settings, "GROQ_API_KEY", "test-key-not-real")
    response = await client.post("/api/v1/bills/upload", files=[("files", ("receipt.png", b"\x89PNG\r\n\x1a\n" + b"test", "image/png"))])
    assert response.status_code == 200
    bill_id = response.json()["bills"][0]["id"]
    bill = await async_session.scalar(select(Bill).where(Bill.id == bill_id))
    assert bill.status == BillStatus.PENDING


@pytest.mark.asyncio
async def test_upload_requires_cloud_key(client, monkeypatch):
    from app.api.v1 import bills

    monkeypatch.setattr(bills.settings, "GROQ_API_KEY", "")
    response = await client.post("/api/v1/bills/upload", files=[("files", ("receipt.png", b"\x89PNG\r\n\x1a\n", "image/png"))])
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]
