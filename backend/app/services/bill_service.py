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

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_extractor import extract_structured_data
from app.ai.ocr_pipeline import extract_text_from_file
from app.ai.vector_store import (
    build_document_text, delete_bill_embeddings, find_duplicates, upsert_bill_embedding,
)
from app.models.bill import Bill, BillStatus
from app.models.embedding import BillEmbedding
from app.models.expense import Expense
from app.models.ocr_result import OCRResult
from app.models.vendor import Vendor

logger = logging.getLogger(__name__)
T = TypeVar("T")


class BillProcessingError(ValueError):
    """The uploaded bill did not contain a usable expense."""


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
        db.execute(select(Bill).where(Bill.id == bill_id).with_for_update()),
        db_timeout,
    )
    bill = result.scalar_one_or_none()
    if not bill:
        _log_stage(bill_id, "pipeline", "end", reason="bill_not_found")
        return

    if bill.status in {BillStatus.COMPLETED, BillStatus.PROCESSING}:
        await db.rollback()
        _log_stage(bill_id, "pipeline", "end", reason="already_processed_or_running")
        return

    bill.status = BillStatus.PROCESSING
    bill.error_message = None
    user_id = bill.user_id
    await _timed_db(bill_id, "db_commit_processing_status", db.commit(), db_timeout)

    chroma_id = None
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

        extracted = _timed_sync(
            bill_id,
            "llm_extract",
            lambda: extract_structured_data(ocr_data.raw_text),
        )
        amount = Decimal(str(extracted.total_amount)) if extracted.total_amount is not None else None
        if amount is None or not amount.is_finite() or amount <= 0 or amount.quantize(Decimal("0.01")) <= 0:
            raise BillProcessingError(
                "Bill couldn't be processed: no valid positive total amount was found. "
                "Please upload a clearer bill."
            )
        # Do not hold SQLite's write lock while waiting on the cloud request.
        await _timed_db(bill_id, "db_flush_ocr", db.flush(), db_timeout)
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
            total_amount=amount,
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
                meta = top.get("metadata", {})
                if meta.get("expense_id"):
                    try:
                        duplicate_id = int(meta["expense_id"])

                        duplicate_expense = await db.get(
                            Expense,
                            duplicate_id
                        )
                        logger.info(
                            "Duplicate search result: %s",
                            top
                        )
                        candidate_bill_id = meta.get("bill_id")
                        if (
                            duplicate_expense
                            and duplicate_expense.user_id == user_id
                            and duplicate_expense.id != expense.id
                            and candidate_bill_id is not None
                            and str(duplicate_expense.bill_id) == str(candidate_bill_id)
                        ):
                            expense.is_duplicate = True
                            expense.duplicate_confidence = top["similarity_score"]
                            expense.duplicate_of_id = duplicate_id
                            logger.info(
                                "Duplicate search result: %s",
                                top
                            )
                        else:
                            logger.warning(
                                "Duplicate candidate %s not found in database",
                                duplicate_id,
                            )

                    except (TypeError, ValueError):
                        pass

        bill.status = BillStatus.COMPLETED
        await _timed_db(bill_id, "db_commit_success", db.commit(), db_timeout)
    except Exception as exc:
        # A failed flush invalidates the transaction; it must be rolled back before
        # persisting failure. This also removes any partial OCR/vendor/expense rows.
        await db.rollback()
        if isinstance(exc, BillProcessingError):
            logger.warning("Bill %s couldn't be processed: %s", bill_id, exc)
        else:
            logger.exception("Bill processing pipeline failed for bill %s", bill_id)
        if chroma_id:
            try:
                delete_bill_embeddings(bill_id, user_id)
            except Exception:
                logger.exception("Could not remove failed bill %s from vector store", bill_id)
        await _timed_db(
            bill_id, "db_set_failure_status",
            db.execute(update(Bill).where(Bill.id == bill_id).values(
                status=BillStatus.FAILED, error_message=str(exc)[:2000],
            )), db_timeout,
        )
        await _timed_db(bill_id, "db_commit_failure_status", db.commit(), db_timeout)
        raise

    _log_stage(bill_id, "pipeline", "end", status="completed")


async def delete_bill(db: AsyncSession, bill_id: int, user_id: int) -> None:
    result = await db.execute(
        select(Bill).where(Bill.id == bill_id, Bill.user_id == user_id).with_for_update()
    )
    bill = result.scalar_one_or_none()
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.status == BillStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Cannot delete a bill while processing")

    expense_id = (await db.execute(
        select(Expense.id).where(Expense.bill_id == bill_id)
    )).scalar_one_or_none()
    if expense_id is not None:
        await db.execute(
            update(Expense).where(Expense.duplicate_of_id == expense_id).values(
                duplicate_of_id=None, is_duplicate=False, duplicate_confidence=None,
            )
        )

    stored_path = bill.stored_path
    needs_vector_cleanup = bill.status in {BillStatus.COMPLETED, BillStatus.FAILED} or (await db.execute(
        select(BillEmbedding.id).where(BillEmbedding.bill_id == bill_id)
    )).scalar_one_or_none() is not None
    # ORM cascades remove the OCR, expense and embedding rows in FK-safe order.
    await db.delete(bill)
    await db.commit()
    if needs_vector_cleanup:
        try:
            await asyncio.to_thread(delete_bill_embeddings, bill_id, user_id)
        except Exception:
            logger.exception("Could not remove deleted bill %s from vector store", bill_id)
    try:
        Path(stored_path).unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove uploaded file for bill %s", bill_id)
