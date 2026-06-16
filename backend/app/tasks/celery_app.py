"""Celery application and bill processing task."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import suppress

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "billanalyser",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

redis_transport_options = {
    "socket_connect_timeout": 10,
    "socket_timeout": 30,
    "retry_on_timeout": True,
    "health_check_interval": 30,
    "socket_keepalive": True,
    "max_connections": 10,
}

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    broker_pool_limit=1 if os.name == "nt" else 10,
    broker_transport_options=redis_transport_options,
    result_backend_transport_options=redis_transport_options,
    redis_socket_connect_timeout=10,
    redis_socket_timeout=30,
    redis_retry_on_timeout=True,
    worker_pool="solo" if os.name == "nt" else "prefork",
    worker_concurrency=1 if os.name == "nt" else os.cpu_count() or 2,
)


def _log_task(bill_id: int, stage: str, event: str, **fields) -> None:
    field_text = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info(
        "celery_bill_task bill_id=%s stage=%s event=%s %s",
        bill_id,
        stage,
        event,
        field_text,
        extra={"bill_id": bill_id, "stage": stage, "event": event, **fields},
    )


async def _mark_bill_failed(bill_id: int, message: str) -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.bill import Bill, BillStatus

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            result = await asyncio.wait_for(
                session.execute(select(Bill).where(Bill.id == bill_id)),
                timeout=settings.DB_OPERATION_TIMEOUT_SECONDS,
            )
            bill = result.scalar_one_or_none()
            if bill:
                bill.status = BillStatus.FAILED
                bill.error_message = message[:2000]
                await asyncio.wait_for(
                    session.commit(),
                    timeout=settings.DB_OPERATION_TIMEOUT_SECONDS,
                )
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="process_bill",
)
def process_bill_task(self, bill_id: int) -> str:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    async def _run() -> None:
        from app.services.bill_service import process_bill_pipeline

        _log_task(bill_id, "db_engine", "start")
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with Session() as session:
                _log_task(bill_id, "pipeline", "start")
                await process_bill_pipeline(session, bill_id)
                _log_task(bill_id, "pipeline", "end")
        finally:
            _log_task(bill_id, "db_engine_dispose", "start")
            await engine.dispose()
            _log_task(bill_id, "db_engine_dispose", "end")

    start = time.perf_counter()
    timeout_seconds = settings.BILL_PROCESSING_TIMEOUT_SECONDS
    _log_task(
        bill_id,
        "task",
        "start",
        task_id=getattr(self.request, "id", None),
        timeout_seconds=timeout_seconds,
    )
    try:
        asyncio.run(asyncio.wait_for(_run(), timeout=timeout_seconds))
    except SoftTimeLimitExceeded:
        message = "Bill processing exceeded Celery soft time limit"
        with suppress(Exception):
            asyncio.run(_mark_bill_failed(bill_id, message))
        logger.exception("%s for bill %s", message, bill_id)
        raise
    except TimeoutError as exc:
        message = f"Bill processing timed out after {timeout_seconds}s"
        with suppress(Exception):
            asyncio.run(_mark_bill_failed(bill_id, message))
        logger.exception("%s for bill %s", message, bill_id)
        raise RuntimeError(message) from exc
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        with suppress(Exception):
            asyncio.run(_mark_bill_failed(bill_id, message))
        logger.exception("Bill processing failed for bill %s", bill_id)
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    _log_task(bill_id, "task", "success", elapsed_ms=elapsed_ms)
    return f"processed bill {bill_id}"
