from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from kombu.exceptions import OperationalError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.bill import Bill, BillStatus
from app.models.user import User
from app.schemas.bill import BillResponse, BillUploadResponse
from app.tasks.celery_app import process_bill_task
from app.utils.file_validation import (
    build_storage_path,
    sanitize_filename,
    validate_file_content,
    validate_upload,
)

router = APIRouter(prefix="/bills", tags=["Bills"])
settings = get_settings()


@router.post("/upload", response_model=BillUploadResponse)
async def upload_bills(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    created: list[Bill] = []
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    for upload in files:
        ext = validate_upload(upload)
        header = await upload.read(16)
        await upload.seek(0)
        await validate_file_content(header, ext)

        content = await upload.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
            )

        path = build_storage_path(current_user.id, ext)
        path.write_bytes(content)

        bill = Bill(
            user_id=current_user.id,
            original_filename=sanitize_filename(upload.filename or "upload"),
            stored_path=str(path),
            mime_type=upload.content_type or "application/octet-stream",
            file_size_bytes=len(content),
            status=BillStatus.PENDING,
        )
        db.add(bill)
        await db.flush()
        created.append(bill)

    await db.commit()

    try:
        for bill in created:
            process_bill_task.apply_async(args=(bill.id,), retry=True)
    except OperationalError as exc:
        for bill in created:
            bill.status = BillStatus.FAILED
            bill.error_message = f"Could not queue bill for processing: {exc}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bill uploaded, but Redis/Celery is unavailable. Start Redis and retry.",
        ) from exc

    return BillUploadResponse(
        bills=[BillResponse.model_validate(b) for b in created],
        message=f"{len(created)} bill(s) queued for processing",
    )


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
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
    return bill


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bill(
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
    await db.delete(bill)
