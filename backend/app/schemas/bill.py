from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class BillStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class BillResponse(BaseModel):
    id: int
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: BillStatusEnum
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillUploadResponse(BaseModel):
    bills: list[BillResponse]
    message: str = "Upload accepted; processing started"


class BillUpdate(BaseModel):
    notes: str | None = None
