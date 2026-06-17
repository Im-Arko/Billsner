"""Uploaded bill / invoice files."""

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BillStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(500))
    stored_path: Mapped[str] = mapped_column(String(1000))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus), default=BillStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="bills")
    ocr_result: Mapped["OCRResult | None"] = relationship(
        back_populates="bill",
        uselist=False,
        cascade="all, delete-orphan",
    )
    expense: Mapped["Expense | None"] = relationship(
        back_populates="bill",
        uselist=False,
        cascade="all, delete-orphan",
    )

    embedding: Mapped["BillEmbedding | None"] = relationship(
        back_populates="bill",
        uselist=False,
        cascade="all, delete-orphan",
    )