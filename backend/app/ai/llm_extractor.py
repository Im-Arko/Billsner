"""LangChain-based structured extraction from OCR text."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.ai.classifier import classify_by_keywords
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EXTRACTION_PROMPT = """You are an expert invoice parser. Extract ONLY fields explicitly present in the bill text.
Do NOT invent or guess values. Use null for missing fields.

Bill text:
{text}

Return strict JSON with these keys:
- vendor_name (string|null)
- bill_number (string|null)
- total_amount (number|null)
- tax_amount (number|null)
- gst_number (string|null)
- date (ISO date string YYYY-MM-DD or null)
- currency (string, default INR)
- payment_method (string|null)
- expense_category (one of: Fuel, Hotel, Food, Travel, Medical, Shopping, Miscellaneous)
- secondary_categories (array of strings)
- line_items (array of {{description, quantity, unit_price, amount}})
- classification_confidence (0-1 based on clarity of text)

JSON only, no markdown."""


class ExtractionSchema(BaseModel):
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
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    classification_confidence: float = Field(default=0.5, ge=0, le=1)


def _get_llm():
    if settings.LLM_PROVIDER == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0,
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0,
    )


def _parse_json_fallback(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in LLM response")


def extract_structured_data(ocr_text: str, max_retries: int = 2) -> ExtractionSchema:
    if not ocr_text.strip():
        return ExtractionSchema(classification_confidence=0.0)

    parser = JsonOutputParser(pydantic_object=ExtractionSchema)
    prompt = ChatPromptTemplate.from_messages(
        [("system", "You extract invoice data. Never hallucinate."), ("human", EXTRACTION_PROMPT)]
    )
    chain = prompt | _get_llm() | parser

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            result = chain.invoke({"text": ocr_text[:12000]})
            if isinstance(result, dict):
                return ExtractionSchema.model_validate(result)
            return result
        except Exception as exc:
            last_error = exc
            logger.warning("LLM extraction attempt %s failed: %s", attempt + 1, exc)

    try:
        llm = _get_llm()
        raw = llm.invoke(EXTRACTION_PROMPT.format(text=ocr_text[:12000]))
        content = raw.content if hasattr(raw, "content") else str(raw)
        data = _parse_json_fallback(content)
        return ExtractionSchema.model_validate(data)
    except Exception as exc:
        logger.error("Fallback parsing failed: %s", exc)
        last_error = exc

    keyword_cat, kw_conf = classify_by_keywords(ocr_text)
    return ExtractionSchema(
        expense_category=keyword_cat,
        classification_confidence=kw_conf * 0.5,
    )
