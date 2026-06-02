"""Celery application and bill processing task."""

import asyncio

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "billanalyser",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
)


@celery_app.task(name="process_bill")
def process_bill_task(bill_id: int) -> str:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.services.bill_service import process_bill_pipeline

    async def _run():
        engine = create_async_engine(settings.DATABASE_URL)
        Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as session:
            await process_bill_pipeline(session, bill_id)
        await engine.dispose()

    asyncio.run(_run())
    return f"processed bill {bill_id}"
