"""Bill upload and processing orchestration."""

from __future__ import annotations

import json
import asyncio
import logging
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_extractor import extract_structured_data
from app.ai.ocr_pipeline import extract_text_from_file
from app.ai.vector_store import build_document_text, find_duplicates, upsert_bill_embedding
from app.models.bill import Bill, BillStatus
from app.models.embedding import BillEmbedding
from app.models.expense import Expense
from app.models.ocr_result import OCRResult
from app.models.vendor import Vendor

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _log_stage(bill_id: int, stage: str, event: str, **fields) -> None:
    field_text = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info(
        "bill_processing_stage bill_id=%s stage=%s event=%s %s",
        bill_id,
        stage,
        event,
        field_text,
        extra={"bill_id": bill_id, "stage": stage, "event": event, **fields},
    )


def _timed_sync(bill_id: int, stage: str, func: Callable[[], T]) -> T:
    start = time.perf_counter()
    _log_stage(bill_id, stage, "start")
    try:
        result = func()
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "%s failed for bill %s",
            stage,
            bill_id,
            extra={"bill_id": bill_id, "stage": stage, "event": "error", "elapsed_ms": elapsed_ms},
        )
        raise
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    _log_stage(bill_id, stage, "end", elapsed_ms=elapsed_ms)
    return result


async def _timed_db(
    bill_id: int,
    stage: str,
    operation: Awaitable[T],
    timeout_seconds: int,
) -> T:
    start = time.perf_counter()
    _log_stage(bill_id, stage, "start", timeout_seconds=timeout_seconds)
    try:
        result = await asyncio.wait_for(operation, timeout=timeout_seconds)
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "%s failed for bill %s",
            stage,
            bill_id,
            extra={"bill_id": bill_id, "stage": stage, "event": "error", "elapsed_ms": elapsed_ms},
        )
        raise
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    _log_stage(bill_id, stage, "end", elapsed_ms=elapsed_ms)
    return result


async def process_bill_pipeline(db: AsyncSession, bill_id: int) -> None:
    from app.config import get_settings

    settings = get_settings()
    db_timeout = settings.DB_OPERATION_TIMEOUT_SECONDS

    _log_stage(bill_id, "pipeline", "start")
    result = await _timed_db(
        bill_id,
        "db_load_bill",
        db.execute(select(Bill).where(Bill.id == bill_id)),
        db_timeout,
    )
    bill = result.scalar_one_or_none()
    if not bill:
        _log_stage(bill_id, "pipeline", "end", reason="bill_not_found")
        return

    bill.status = BillStatus.PROCESSING
    await _timed_db(bill_id, "db_flush_processing_status", db.flush(), db_timeout)

    try:
        ocr_data = _timed_sync(
            bill_id,
            "ocr",
            lambda: extract_text_from_file(bill.stored_path),
        )
        ocr_row = OCRResult(
            bill_id=bill.id,
            raw_text=ocr_data.raw_text,
            confidence_score=ocr_data.confidence_score,
            preprocessing_applied=json.dumps(ocr_data.preprocessing_applied),
        )
        db.add(ocr_row)
        await _timed_db(bill_id, "db_flush_ocr", db.flush(), db_timeout)

        extracted = _timed_sync(
            bill_id,
            "llm_extract",
            lambda: extract_structured_data(ocr_data.raw_text),
        )
        expense_date: date | None = None
        if extracted.date:
            try:
                expense_date = date.fromisoformat(extracted.date[:10])
            except ValueError:
                pass

        vendor_id = None
        if extracted.vendor_name:
            v_result = await _timed_db(
                bill_id,
                "db_lookup_vendor",
                db.execute(
                    select(Vendor).where(
                        Vendor.normalized_name == extracted.vendor_name.lower().strip()
                    )
                ),
                db_timeout,
            )
            vendor = v_result.scalar_one_or_none()
            if not vendor:
                vendor = Vendor(
                    name=extracted.vendor_name,
                    gst_number=extracted.gst_number,
                    normalized_name=extracted.vendor_name.lower().strip(),
                )
                db.add(vendor)
                await _timed_db(bill_id, "db_flush_vendor", db.flush(), db_timeout)
            vendor_id = vendor.id

        expense = Expense(
            user_id=bill.user_id,
            bill_id=bill.id,
            vendor_id=vendor_id,
            vendor_name=extracted.vendor_name,
            bill_number=extracted.bill_number,
            total_amount=(
                Decimal(str(extracted.total_amount))
                if extracted.total_amount is not None
                else None
            ),
            tax_amount=(
                Decimal(str(extracted.tax_amount))
                if extracted.tax_amount is not None
                else None
            ),
            gst_number=extracted.gst_number,
            expense_date=expense_date,
            currency=extracted.currency or "INR",
            payment_method=extracted.payment_method,
            category_name=extracted.expense_category,
            secondary_categories=extracted.secondary_categories or None,
            line_items=extracted.line_items or None,
            classification_confidence=extracted.classification_confidence,
        )
        db.add(expense)
        await _timed_db(bill_id, "db_flush_expense", db.flush(), db_timeout)

        doc = _timed_sync(
            bill_id,
            "vector_document_build",
            lambda: build_document_text(
                ocr_data.raw_text,
                extracted.vendor_name,
                extracted.total_amount,
                extracted.expense_category,
                extracted.date,
            ),
        )
        chroma_id = _timed_sync(
            bill_id,
            "vector_upsert",
            lambda: upsert_bill_embedding(
                bill.id,
                bill.user_id,
                doc,
                {
                    "expense_id": expense.id,
                    "vendor": extracted.vendor_name or "",
                    "amount": str(extracted.total_amount or ""),
                    "category": extracted.expense_category or "",
                },
            ),
        )
        db.add(
            BillEmbedding(
                bill_id=bill.id,
                chroma_id=chroma_id,
            )
        )

        dupes = _timed_sync(
            bill_id,
            "vector_duplicate_search",
            lambda: find_duplicates(doc, bill.user_id, bill.id),
        )
        if dupes:
            top = dupes[0]
            if top["similarity_score"] >= 0.85:
                expense.is_duplicate = True
                expense.duplicate_confidence = top["similarity_score"]
                meta = top.get("metadata", {})
                if meta.get("expense_id"):
                    try:
                        expense.duplicate_of_id = int(meta["expense_id"])
                    except (TypeError, ValueError):
                        pass

        bill.status = BillStatus.COMPLETED
    except Exception as exc:
        logger.exception("Bill processing pipeline failed for bill %s", bill_id)
        bill.status = BillStatus.FAILED
        bill.error_message = str(exc)[:2000]
        await _timed_db(bill_id, "db_commit_failure_status", db.commit(), db_timeout)
        raise

    await _timed_db(bill_id, "db_commit_success", db.commit(), db_timeout)
    _log_stage(bill_id, "pipeline", "end", status="completed")
