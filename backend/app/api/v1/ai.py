import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.classifier import classify_expense
from app.ai.ocr_pipeline import extract_text_from_file
from app.ai.vector_store import build_document_text, find_duplicates
from app.api.deps import get_current_user
from app.database import get_db
from app.models.bill import Bill
from app.models.ocr_result import OCRResult
from app.models.user import User
from app.schemas.ai import (
    ClassificationRequest,
    ClassificationResponse,
    DuplicateDetectionResponse,
    DuplicateMatch,
    OCRResponse,
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/ocr/{bill_id}", response_model=OCRResponse)
async def run_ocr(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bill).where(Bill.id == bill_id, Bill.user_id == current_user.id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    ocr_data = await asyncio.to_thread(extract_text_from_file, bill.stored_path)
    return OCRResponse(
        bill_id=bill.id,
        raw_text=ocr_data.raw_text,
        confidence_score=ocr_data.confidence_score,
        preprocessing_applied=ocr_data.preprocessing_applied,
    )


@router.post("/classify", response_model=ClassificationResponse)
async def classify(body: ClassificationRequest):
    cat, secondary, conf, method = await asyncio.to_thread(classify_expense, body.text, body.vendor_name)
    return ClassificationResponse(
        category=cat,
        secondary_categories=secondary,
        confidence=conf,
        method=method,
    )


@router.get("/duplicates/{bill_id}", response_model=DuplicateDetectionResponse)
async def detect_duplicates(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bill).where(Bill.id == bill_id, Bill.user_id == current_user.id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    ocr_result = await db.execute(
        select(OCRResult).where(OCRResult.bill_id == bill_id)
    )
    ocr = ocr_result.scalar_one_or_none()
    text = ocr.raw_text if ocr else ""
    doc = build_document_text(text, None, None, None, None)
    matches_raw = await asyncio.to_thread(find_duplicates, doc, current_user.id, bill_id)

    matches = [
        DuplicateMatch(
            expense_id=int(m["metadata"].get("expense_id", 0) or 0),
            bill_id=int(m["metadata"].get("bill_id", 0) or 0),
            similarity_score=m["similarity_score"],
            duplicate_confidence=m["similarity_score"],
            vendor_name=m["metadata"].get("vendor"),
            total_amount=float(m["metadata"]["amount"])
            if m["metadata"].get("amount")
            else None,
        )
        for m in matches_raw
    ]
    is_dup = bool(matches and matches[0].similarity_score >= 0.85)
    return DuplicateDetectionResponse(
        bill_id=bill_id,
        is_likely_duplicate=is_dup,
        matches=matches,
    )
