"""Structured expense records extracted from bills."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bill_id: Mapped[int | None] = mapped_column(
        ForeignKey("bills.id"), unique=True, nullable=True
    )
    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendors.id"), nullable=True, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_categories.id"), nullable=True, index=True
    )

    vendor_name: Mapped[str | None] = mapped_column(String(255), index=True)
    bill_number: Mapped[str | None] = mapped_column(String(100), index=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), index=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expense_date: Mapped[date | None] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(100), index=True)
    secondary_categories: Mapped[list | None] = mapped_column(JSON, nullable=True)
    line_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(nullable=True)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("expenses.id"), nullable=True
    )
    duplicate_confidence: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="expenses")
    bill: Mapped["Bill | None"] = relationship(back_populates="expense")
    vendor: Mapped["Vendor | None"] = relationship(back_populates="expenses")
    category: Mapped["ExpenseCategory | None"] = relationship(
        back_populates="expenses"
    )
