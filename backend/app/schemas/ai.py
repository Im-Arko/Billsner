from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    bill_id: int
    raw_text: str
    confidence_score: float
    preprocessing_applied: list[str]


class ExtractedExpense(BaseModel):
    vendor_name: str | None = None
    bill_number: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    gst_number: str | None = None
    date: str | None = None
    currency: str = "INR"
    payment_method: str | None = None
    expense_category: str | None = None
    secondary_categories: list[str] = Field(default_factory=list)
    line_items: list[dict] = Field(default_factory=list)
    classification_confidence: float = Field(ge=0, le=1, default=0.5)


class ClassificationRequest(BaseModel):
    text: str
    vendor_name: str | None = None


class ClassificationResponse(BaseModel):
    category: str
    secondary_categories: list[str]
    confidence: float
    method: str


class DuplicateMatch(BaseModel):
    expense_id: int
    bill_id: int | None
    similarity_score: float
    duplicate_confidence: float
    vendor_name: str | None
    total_amount: float | None


class DuplicateDetectionResponse(BaseModel):
    bill_id: int
    is_likely_duplicate: bool
    matches: list[DuplicateMatch]
