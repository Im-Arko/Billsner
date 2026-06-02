"""
LLM Extraction Service — LangChain integration for structured data extraction.
Supports OpenAI GPT-4o and Ollama local models.
Includes retry logic, output parsing, and hallucination prevention.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from langchain.output_parsers import PydanticOutputParser, RetryWithErrorOutputParser
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Output Schema (also used by the parser) ───────────────────────────────────
class LineItemSchema(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class ExtractedExpense(BaseModel):
    vendor_name: Optional[str] = Field(None, description="Business or shop name")
    bill_number: Optional[str] = Field(None, description="Invoice or bill number")
    bill_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    total_amount: Optional[float] = Field(None, description="Grand total amount (numeric only)")
    tax_amount: Optional[float] = Field(None, description="Tax or GST amount (numeric only)")
    gst_number: Optional[str] = Field(None, description="GST registration number if present")
    currency: str = Field("INR", description="Currency code e.g. INR, USD, EUR")
    payment_method: Optional[str] = Field(None, description="Cash, Card, UPI, Net Banking, etc.")
    expense_category: Optional[str] = Field(
        None,
        description="One of: Fuel, Hotel, Food, Travel, Medical, Shopping, Utilities, Miscellaneous",
    )
    line_items: Optional[list[LineItemSchema]] = Field(None, description="Individual items if listed")
    extraction_confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence in extraction accuracy (0.0-1.0)"
    )

    @field_validator("bill_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Allow partial dates, normalize common formats
        v = v.strip()
        patterns = [
            r"^\d{4}-\d{2}-\d{2}$",
            r"^\d{2}/\d{2}/\d{4}$",
            r"^\d{2}-\d{2}-\d{4}$",
        ]
        for p in patterns:
            if re.match(p, v):
                return v
        return None  # reject invalid dates rather than hallucinate


# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a precise financial data extraction assistant. 
Your task is to extract structured expense data from OCR text of bills and invoices.

CRITICAL RULES:
- Extract ONLY information explicitly present in the text
- Do NOT invent, guess, or hallucinate any values
- If a field is not clearly present, return null for that field
- For amounts, extract numeric values only (no currency symbols)
- Return confidence score based on how clearly each field was readable
- Categories must be exactly one of: Fuel, Hotel, Food, Travel, Medical, Shopping, Utilities, Miscellaneous
- Dates must be in YYYY-MM-DD format

{format_instructions}"""

HUMAN_PROMPT = """Extract expense data from this OCR text:

---OCR TEXT START---
{ocr_text}
---OCR TEXT END---

Return a valid JSON object with extracted fields. Remember: null > hallucinated data."""


# ── LLM Factory ───────────────────────────────────────────────────────────────
def get_llm() -> BaseChatModel:
    if settings.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,  # deterministic extraction
            max_tokens=2000,
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
        )


# ── Extraction Service ────────────────────────────────────────────────────────
class LLMExtractionService:
    """
    Extracts structured expense data from OCR text using LangChain + LLM.
    Uses Pydantic output parser with retry-on-error fallback.
    """

    def __init__(self):
        self.llm = get_llm()
        self.parser = PydanticOutputParser(pydantic_object=ExtractedExpense)
        self.retry_parser = RetryWithErrorOutputParser.from_llm(
            parser=self.parser,
            llm=self.llm,
            max_retries=2,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(HUMAN_PROMPT),
        ])

    async def extract(self, ocr_text: str) -> ExtractedExpense:
        """Main extraction entry point. Returns structured expense data."""
        if not ocr_text or len(ocr_text.strip()) < 20:
            logger.warning("OCR text too short for reliable extraction")
            return ExtractedExpense(extraction_confidence=0.1)

        format_instructions = self.parser.get_format_instructions()
        messages = self.prompt.format_messages(
            ocr_text=ocr_text[:6000],  # token limit guard
            format_instructions=format_instructions,
        )

        try:
            response = await self.llm.ainvoke(messages)
            result = self._parse_with_fallback(response.content)
            logger.info(
                f"Extraction complete. Vendor={result.vendor_name}, "
                f"Amount={result.total_amount}, Confidence={result.extraction_confidence}"
            )
            return result
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}", exc_info=True)
            return self._fallback_extraction(ocr_text)

    def _parse_with_fallback(self, raw_output: str) -> ExtractedExpense:
        """Try strict parse, then JSON extraction, then keyword fallback."""
        # 1. Direct parse
        try:
            return self.parser.parse(raw_output)
        except Exception:
            pass

        # 2. Extract JSON block from response
        try:
            json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return ExtractedExpense(**data)
        except Exception:
            pass

        # 3. Keyword fallback
        return self._fallback_extraction(raw_output)

    def _fallback_extraction(self, text: str) -> ExtractedExpense:
        """Keyword-based extraction when LLM fails."""
        result: Dict[str, Any] = {"extraction_confidence": 0.3}

        # Amount patterns
        amount_pattern = re.search(
            r"(?:total|grand total|amount due)[:\s₹$]*([0-9,]+\.?\d*)",
            text,
            re.IGNORECASE,
        )
        if amount_pattern:
            result["total_amount"] = float(amount_pattern.group(1).replace(",", ""))

        # GST pattern
        gst_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b", text)
        if gst_match:
            result["gst_number"] = gst_match.group()

        # Date pattern
        date_match = re.search(r"\b(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\b", text)
        if date_match:
            result["bill_date"] = date_match.group()

        # Category inference
        text_lower = text.lower()
        categories = {
            "Fuel": ["petrol", "diesel", "fuel", "hp pump", "bpcl", "iocl"],
            "Hotel": ["hotel", "resort", "inn", "accommodation", "lodge"],
            "Food": ["restaurant", "café", "food", "meal", "dinner", "lunch"],
            "Travel": ["airline", "flight", "train", "cab", "taxi", "ola", "uber"],
            "Medical": ["pharmacy", "hospital", "clinic", "medicine", "dr."],
        }
        for cat, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                result["expense_category"] = cat
                break

        return ExtractedExpense(**result)


# Singleton
_extraction_service: Optional[LLMExtractionService] = None


def get_extraction_service() -> LLMExtractionService:
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = LLMExtractionService()
    return _extraction_service
