"""
SQLAlchemy ORM Models — Expense Bill Analyzer
Normalized schema with full relationships, indexes, and audit fields.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Index,
    Integer, JSON, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.mysql import CHAR, LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── User ─────────────────────────────────────────────────────────────────────
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "user", "viewer"), default="user", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    bills: Mapped[List["Bill"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")


# ── Vendor ───────────────────────────────────────────────────────────────────
class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    bills: Mapped[List["Bill"]] = relationship(back_populates="vendor")

    __table_args__ = (
        UniqueConstraint("normalized_name", "gst_number", name="uq_vendor_name_gst"),
    )


# ── ExpenseCategory ───────────────────────────────────────────────────────────
class ExpenseCategory(Base, TimestampMixin):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)

    expenses: Mapped[List["Expense"]] = relationship(back_populates="category")


# ── Bill ─────────────────────────────────────────────────────────────────────
class Bill(Base, TimestampMixin):
    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    vendor_id: Mapped[Optional[str]] = mapped_column(CHAR(36), ForeignKey("vendors.id"), nullable=True, index=True)

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "completed", "failed"),
        default="pending",
        nullable=False,
        index=True,
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="bills")
    vendor: Mapped[Optional["Vendor"]] = relationship(back_populates="bills")
    ocr_result: Mapped[Optional["OCRResult"]] = relationship(back_populates="bill", uselist=False)
    expense: Mapped[Optional["Expense"]] = relationship(back_populates="bill", uselist=False)
    embedding: Mapped[Optional["BillEmbedding"]] = relationship(back_populates="bill", uselist=False)
    duplicate_flags: Mapped[List["DuplicateFlag"]] = relationship(
        back_populates="source_bill",
        foreign_keys="DuplicateFlag.source_bill_id",
    )

    __table_args__ = (
        Index("ix_bills_user_status", "user_id", "status"),
        Index("ix_bills_file_hash", "file_hash"),
    )


# ── OCRResult ────────────────────────────────────────────────────────────────
class OCRResult(Base, TimestampMixin):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    bill_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("bills.id"), unique=True, nullable=False)

    raw_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    ocr_engine: Mapped[str] = mapped_column(String(50), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    language_detected: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    bill: Mapped["Bill"] = relationship(back_populates="ocr_result")


# ── Expense ───────────────────────────────────────────────────────────────────
class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    bill_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("bills.id"), unique=True, nullable=False)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("expense_categories.id"), nullable=True)

    # Extracted fields
    vendor_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bill_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bill_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    tax_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    line_items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # AI metadata
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    is_manually_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_raw_response: Mapped[Optional[str]] = mapped_column(LONGTEXT, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    bill: Mapped["Bill"] = relationship(back_populates="expense")
    category: Mapped[Optional["ExpenseCategory"]] = relationship(back_populates="expenses")

    __table_args__ = (
        Index("ix_expenses_user_date", "user_id", "bill_date"),
        Index("ix_expenses_amount", "total_amount"),
    )


# ── BillEmbedding ─────────────────────────────────────────────────────────────
class BillEmbedding(Base, TimestampMixin):
    __tablename__ = "bill_embeddings"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    bill_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("bills.id"), unique=True, nullable=False)
    chroma_doc_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)

    bill: Mapped["Bill"] = relationship(back_populates="embedding")


# ── DuplicateFlag ─────────────────────────────────────────────────────────────
class DuplicateFlag(Base, TimestampMixin):
    __tablename__ = "duplicate_flags"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=gen_uuid)
    source_bill_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("bills.id"), nullable=False)
    duplicate_bill_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("bills.id"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[str] = mapped_column(
        Enum("low", "medium", "high"), nullable=False
    )
    is_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True)

    source_bill: Mapped["Bill"] = relationship(
        back_populates="duplicate_flags", foreign_keys=[source_bill_id]
    )


# ── AuditLog ──────────────────────────────────────────────────────────────────
class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_action_resource", "action", "resource_type"),
    )
