"""Durable local bill queue supervised by the API, without a broker service."""

import asyncio
import logging
import os
import subprocess
import sys
import threading
import time

from sqlalchemy import select, update

from app.config import BACKEND_DIR, get_settings
from app.database import AsyncSessionLocal
from app.models.bill import Bill, BillStatus

settings = get_settings()
logger = logging.getLogger(__name__)

async def _mark_bill_failed(bill_id: int, message: str) -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database import create_database_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.bill import Bill, BillStatus

    engine = create_database_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            result = await asyncio.wait_for(
                session.execute(select(Bill).where(Bill.id == bill_id)),
                timeout=settings.DB_OPERATION_TIMEOUT_SECONDS,
            )
            bill = result.scalar_one_or_none()
            if bill and bill.status != BillStatus.COMPLETED and not (
                bill.status == BillStatus.FAILED and bill.error_message
            ):
                bill.status = BillStatus.FAILED
                bill.error_message = message[:2000]
                await asyncio.wait_for(
                    session.commit(),
                    timeout=settings.DB_OPERATION_TIMEOUT_SECONDS,
                )
    finally:
        await engine.dispose()



def _persist_failure(bill_id: int, message: str) -> None:
    try:
        asyncio.run(_mark_bill_failed(bill_id, message))
    except Exception:
        logger.exception("Could not persist failure status for bill %s", bill_id)


def process_bill_task(bill_id: int, stop: threading.Event | None = None) -> str:
    timeout_seconds = settings.BILL_PROCESSING_TIMEOUT_SECONDS
    start = time.monotonic()
    logger.info("bill_task bill_id=%s event=start timeout_seconds=%s", bill_id, timeout_seconds)
    try:
        with subprocess.Popen(
            [sys.executable, "-m", "app.tasks.bill_worker", str(bill_id)],
            cwd=str(BACKEND_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        ) as process:
            try:
                while True:
                    remaining = timeout_seconds - (time.monotonic() - start)
                    if remaining <= 0:
                        raise TimeoutError(f"Bill processing timed out after {timeout_seconds}s")
                    try:
                        return_code = process.wait(timeout=min(0.25, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        if stop is not None and stop.is_set():
                            # The completed status may already be committed while
                            # the child closes its database connections.
                            try:
                                return_code = process.wait(timeout=2)
                                break
                            except subprocess.TimeoutExpired:
                                raise RuntimeError("Bill processing interrupted because the API is shutting down. Please retry.")
                        continue
                if return_code:
                    raise RuntimeError(f"Bill processing subprocess exited with code {return_code}")
            except BaseException:
                process.kill()
                process.wait()
                raise
    except Exception as exc:
        _persist_failure(bill_id, str(exc))
        logger.exception("Bill processing failed for bill %s", bill_id)
        raise
    logger.info("bill_task bill_id=%s event=success", bill_id)
    return f"processed bill {bill_id}"


async def recover_interrupted_bills() -> None:
    # Only one API process should run the local queue. Uncommitted pipeline writes
    # roll back when its subprocess exits, so interrupted work can be tried again.
    async with AsyncSessionLocal() as session:
        await session.execute(update(Bill).where(Bill.status == BillStatus.PROCESSING).values(
            status=BillStatus.PENDING, error_message=None,
        ))
        await session.commit()


async def run_pending_bills(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            async with AsyncSessionLocal() as session:
                bill_id = await session.scalar(
                    select(Bill.id).where(Bill.status == BillStatus.PENDING)
                    .order_by(Bill.created_at, Bill.id).limit(1)
                )
            if bill_id is not None:
                await asyncio.to_thread(process_bill_task, bill_id, stop)
                continue
        except Exception:
            logger.exception("Local bill queue operation failed")
        await asyncio.sleep(settings.WORKER_POLL_SECONDS)
