"""Bill upload and processing orchestration."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

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


async def process_bill_pipeline(db: AsyncSession, bill_id: int) -> None:
    result = await db.execute(select(Bill).where(Bill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        return

    bill.status = BillStatus.PROCESSING
    await db.flush()

    try:
        ocr_data = extract_text_from_file(bill.stored_path)
        ocr_row = OCRResult(
            bill_id=bill.id,
            raw_text=ocr_data.raw_text,
            confidence_score=ocr_data.confidence_score,
            preprocessing_applied=json.dumps(ocr_data.preprocessing_applied),
        )
        db.add(ocr_row)
        await db.flush()

        extracted = extract_structured_data(ocr_data.raw_text)
        expense_date: date | None = None
        if extracted.date:
            try:
                expense_date = date.fromisoformat(extracted.date[:10])
            except ValueError:
                pass

        vendor_id = None
        if extracted.vendor_name:
            v_result = await db.execute(
                select(Vendor).where(
                    Vendor.normalized_name == extracted.vendor_name.lower().strip()
                )
            )
            vendor = v_result.scalar_one_or_none()
            if not vendor:
                vendor = Vendor(
                    name=extracted.vendor_name,
                    gst_number=extracted.gst_number,
                    normalized_name=extracted.vendor_name.lower().strip(),
                )
                db.add(vendor)
                await db.flush()
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
        await db.flush()

        doc = build_document_text(
            ocr_data.raw_text,
            extracted.vendor_name,
            extracted.total_amount,
            extracted.expense_category,
            extracted.date,
        )
        chroma_id = upsert_bill_embedding(
            bill.id,
            bill.user_id,
            doc,
            {
                "expense_id": expense.id,
                "vendor": extracted.vendor_name or "",
                "amount": str(extracted.total_amount or ""),
                "category": extracted.expense_category or "",
            },
        )
        db.add(
            BillEmbedding(
                bill_id=bill.id,
                chroma_id=chroma_id,
            )
        )

        dupes = find_duplicates(doc, bill.user_id, bill.id)
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
        bill.status = BillStatus.FAILED
        bill.error_message = str(exc)[:2000]
        await db.commit()
        raise

    await db.commit()
