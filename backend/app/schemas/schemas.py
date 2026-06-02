"""
Pydantic v2 Schemas — Request/Response models for all API endpoints.
Strict validation, serialization aliases, and example payloads included.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


# ── Base ──────────────────────────────────────────────────────────────────────
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserRegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseSchema):
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseSchema):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


# ── Bill Upload ───────────────────────────────────────────────────────────────
class BillUploadResponse(BaseSchema):
    id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "original_filename": "hotel_bill_march.pdf",
                "file_type": "application/pdf",
                "file_size_bytes": 204800,
                "status": "pending",
                "created_at": "2024-03-15T10:30:00Z",
            }
        },
    )


class BillStatusResponse(BaseSchema):
    id: str
    status: str
    processing_error: Optional[str] = None
    ocr_confidence: Optional[float] = None


# ── OCR ───────────────────────────────────────────────────────────────────────
class OCRResultResponse(BaseSchema):
    id: str
    bill_id: str
    raw_text: str
    confidence_score: Optional[float]
    ocr_engine: str
    page_count: int
    language_detected: Optional[str]
    created_at: datetime


# ── Line Item ─────────────────────────────────────────────────────────────────
class LineItem(BaseSchema):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[Decimal] = None
    total: Optional[Decimal] = None


# ── Expense ───────────────────────────────────────────────────────────────────
class ExpenseExtractedData(BaseSchema):
    """Schema for LLM-extracted expense fields."""
    vendor_name: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None  # ISO date string from LLM
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    gst_number: Optional[str] = None
    currency: str = "INR"
    payment_method: Optional[str] = None
    expense_category: Optional[str] = None
    line_items: Optional[List[LineItem]] = None
    extraction_confidence: Optional[float] = None


class ExpenseResponse(BaseSchema):
    id: str
    bill_id: str
    vendor_name: Optional[str]
    bill_number: Optional[str]
    bill_date: Optional[datetime]
    total_amount: Optional[Decimal]
    tax_amount: Optional[Decimal]
    gst_number: Optional[str]
    currency: str
    payment_method: Optional[str]
    category: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]]
    extraction_confidence: Optional[float]
    is_manually_verified: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ExpenseUpdateRequest(BaseSchema):
    vendor_name: Optional[str] = None
    bill_date: Optional[datetime] = None
    total_amount: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    payment_method: Optional[str] = None
    category_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=2000)
    is_manually_verified: Optional[bool] = None


# ── Filters & Search ──────────────────────────────────────────────────────────
class ExpenseFilterParams(BaseSchema):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    vendor_name: Optional[str] = None
    currency: Optional[str] = None
    payment_method: Optional[str] = None
    is_verified: Optional[bool] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class NLSearchRequest(BaseSchema):
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(10, ge=1, le=50)
    use_hybrid: bool = True  # combine semantic + SQL

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Show all hotel expenses from March above 5000",
                "limit": 10,
                "use_hybrid": True,
            }
        }
    )


class SearchResultItem(BaseSchema):
    expense: ExpenseResponse
    similarity_score: float
    match_reason: str


class NLSearchResponse(BaseSchema):
    query: str
    results: List[SearchResultItem]
    total_found: int
    search_type: Literal["semantic", "hybrid", "sql"]


# ── Duplicate Detection ───────────────────────────────────────────────────────
class DuplicateCheckResponse(BaseSchema):
    bill_id: str
    is_duplicate: bool
    duplicates: List[Dict[str, Any]]
    highest_similarity: Optional[float]


# ── Analytics / Dashboard ────────────────────────────────────────────────────
class MonthlySummary(BaseSchema):
    month: str  # "2024-03"
    total: Decimal
    count: int
    categories: Dict[str, Decimal]


class CategoryBreakdown(BaseSchema):
    category: str
    total: Decimal
    count: int
    percentage: float


class VendorSummary(BaseSchema):
    vendor_name: str
    total: Decimal
    count: int


class DashboardResponse(BaseSchema):
    total_expenses_this_month: Decimal
    total_expenses_all_time: Decimal
    bill_count: int
    duplicate_alerts: int
    category_breakdown: List[CategoryBreakdown]
    vendor_top10: List[VendorSummary]
    monthly_trend: List[MonthlySummary]
    recent_bills: List[BillUploadResponse]


# ── Export ────────────────────────────────────────────────────────────────────
class ExportRequest(BaseSchema):
    format: Literal["csv", "excel", "pdf"]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_ids: Optional[List[int]] = None
    include_line_items: bool = False


# ── Pagination ────────────────────────────────────────────────────────────────
class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
