"""Upload sanitization and validation."""

import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

settings = get_settings()

MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"%PDF": "application/pdf",
}


def sanitize_filename(filename: str) -> str:
    name = os.path.basename(filename)
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:200] or "upload"


def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_upload(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename required",
        )
    ext = get_extension(file.filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )
    return ext


async def validate_file_content(header: bytes, ext: str) -> None:
    valid = False
    for magic, _ in MAGIC_BYTES.items():
        if header.startswith(magic):
            valid = True
            break
    if ext == "pdf" and header.startswith(b"%PDF"):
        valid = True
    if ext in ("jpg", "jpeg") and header.startswith(b"\xff\xd8"):
        valid = True
    if ext == "png" and header.startswith(b"\x89PNG"):
        valid = True
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match extension",
        )


def build_storage_path(user_id: int, ext: str) -> Path:
    upload_root = Path(settings.UPLOAD_DIR) / str(user_id)
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root / f"{uuid.uuid4().hex}.{ext}"
