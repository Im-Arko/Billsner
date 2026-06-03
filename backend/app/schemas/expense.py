from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class ExpenseResponse(BaseModel):
    id: int
    vendor_name: str | None
    bill_number: str | None
    total_amount: Decimal | None
    tax_amount: Decimal | None
    gst_number: str | None
    expense_date: date | None
    currency: str
    payment_method: str | None
    category_name: str | None
    secondary_categories: list[str] | None = None
    line_items: list[dict] | None = None
    classification_confidence: float | None
    is_manual_override: bool
    is_duplicate: bool
    duplicate_confidence: float | None
    bill_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseUpdate(BaseModel):
    category_name: str | None = None
    vendor_name: str | None = None
    total_amount: Decimal | None = None
    expense_date: date | None = None
    notes: str | None = None
    is_manual_override: bool = True


class ExpenseFilter(BaseModel):
    category: str | None = None
    vendor: str | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_duplicate: bool | None = None
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=10000)


class ExpenseSearch(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class ExpenseSummary(BaseModel):
    total_expenses: Decimal
    expense_count: int
    by_category: dict[str, Decimal]
    by_vendor: dict[str, Decimal]
    monthly_trend: list[dict]
    duplicate_count: int
    recent_bills: list[dict]
