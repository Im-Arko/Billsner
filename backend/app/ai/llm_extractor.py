"""LangChain-based structured extraction from OCR text."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

import httpx

from pydantic import BaseModel, Field

from app.ai.classifier import classify_by_keywords
from app.config import get_settings

try:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    JsonOutputParser = None
    ChatPromptTemplate = None

logger = logging.getLogger(__name__)
settings = get_settings()

EXTRACTION_PROMPT = """You are an expert invoice parser. Extract ONLY fields explicitly present in the bill text.
Do NOT invent or guess values. Use null for missing fields.

Important rules:
- OCR text may contain recognition errors.
- The Indian Rupee symbol (₹) is often incorrectly recognized as '7'.
- If an amount appears unusually large and seems to be caused by a leading '7' replacing the ₹ symbol, correct it when the correction is obvious.
  Example:
    7366.00 -> 366.00
    7678.00 -> 678.00
- Use contextual clues such as subtotal, tax, total, and line item consistency.
- Do not invent vendors, dates, GST numbers, or amounts.
- Use null when a value cannot be determined confidently.
- Expense category must be one of:
  Fuel, Hotel, Food, Travel, Medical, Shopping, Miscellaneous


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

JSON only, no markdown. Do not include reasoning, analysis, or <think> blocks."""


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
        raise RuntimeError("Ollama is invoked through the direct HTTP client")
    if settings.LLM_PROVIDER != "groq":
        raise RuntimeError("No LLM provider configured")
    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )


def _log_stage(stage: str, event: str, **fields: Any) -> None:
    field_text = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info(
        "bill_processing_stage stage=%s event=%s %s",
        stage,
        event,
        field_text,
        extra={"stage": stage, "event": event, **fields},
    )


def _keyword_extraction(text: str, reason: str) -> ExtractionSchema:
    keyword_cat, kw_conf = classify_by_keywords(text)
    logger.warning(
        "llm_keyword_fallback reason=%s category=%s confidence=%.2f",
        reason,
        keyword_cat,
        kw_conf,
    )
    return ExtractionSchema(
        expense_category=keyword_cat,
        classification_confidence=kw_conf,
    )


def _timed_call(stage: str, func, timeout_seconds: int | None = None):
    start = time.perf_counter()
    _log_stage(stage, "start", timeout_seconds=timeout_seconds)
    try:
        result = func()
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "%s failed",
            stage,
            extra={"stage": stage, "event": "error", "elapsed_ms": elapsed_ms},
        )
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    if timeout_seconds is not None and elapsed_ms > timeout_seconds * 1000:
        logger.error(
            "%s exceeded timeout after returning",
            stage,
            extra={"stage": stage, "event": "timeout", "elapsed_ms": elapsed_ms},
        )
        raise TimeoutError(f"{stage} exceeded {timeout_seconds}s")
    _log_stage(stage, "end", elapsed_ms=elapsed_ms)
    return result


def _prompt_messages(prompt_value) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for message in prompt_value.to_messages():
        role = "user"
        message_type = getattr(message, "type", "")
        if message_type in {"system", "human", "ai"}:
            role = "user" if message_type == "human" else message_type
        messages.append({"role": role, "content": str(message.content)})
    return messages


def _invoke_ollama(prompt_value) -> str:
    if not settings.OLLAMA_BASE_URL:
        raise RuntimeError("OLLAMA_BASE_URL is not configured")
    if not settings.OLLAMA_MODEL:
        raise RuntimeError("OLLAMA_MODEL is not configured")

    url = urljoin(settings.OLLAMA_BASE_URL.rstrip("/") + "/", "api/chat")
    timeout = httpx.Timeout(
        connect=10.0,
        read=float(settings.LLM_TIMEOUT_SECONDS),
        write=10.0,
        pool=10.0,
    )
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": _prompt_messages(prompt_value),
        "stream": False,
        "format": "json",
        "keep_alive": "0",
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 128,
            "num_ctx": 2048,
        },
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
    data = response.json()
    message = data.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError(f"Unexpected Ollama response shape: {data!r}")
    return content


def _parse_json_fallback(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in LLM response")


def extract_structured_data(ocr_text: str, max_retries: int = 2) -> ExtractionSchema:
    print(ocr_text)
    if not ocr_text.strip():
        return ExtractionSchema(classification_confidence=0.0)

    if not settings.LLM_PROVIDER:
        _log_stage("llm", "skipped", reason="no_provider_configured")
        return _keyword_extraction(ocr_text, "no_provider_configured")

    if JsonOutputParser is None or ChatPromptTemplate is None:
        logger.error("LangChain core is unavailable")
        return _keyword_extraction(ocr_text, "langchain_core_unavailable")

    try:
        _log_stage("llm_setup", "start", provider=settings.LLM_PROVIDER)
        parser = JsonOutputParser(pydantic_object=ExtractionSchema)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You extract invoice data. Never hallucinate."),
                ("human", EXTRACTION_PROMPT),
            ]
        )
        prompt_value = prompt.invoke({"text": ocr_text[:12000]})
        _log_stage("llm_setup", "end", provider=settings.LLM_PROVIDER)
    except Exception:
        logger.exception("LLM setup failed")
        return _keyword_extraction(ocr_text, "llm_setup_failed")

    try:
        if settings.LLM_PROVIDER == "ollama":
            content = _timed_call(
                "ollama_http",
                lambda: _invoke_ollama(prompt_value),
                settings.LLM_TIMEOUT_SECONDS,
            )
        else:
            llm = _get_llm()
            raw = _timed_call(
                "llm_invoke",
                lambda: llm.invoke(prompt_value),
                settings.LLM_TIMEOUT_SECONDS,
            )
            content = raw.content if hasattr(raw, "content") else str(raw)
    except Exception:
        logger.exception("LLM invoke failed; using keyword fallback")
        return _keyword_extraction(ocr_text, "llm_invoke_failed")
    _log_stage("llm_response", "end", content_length=len(content))

    try:
        parsed = _timed_call(
            "parser",
            lambda: parser.parse(content),
            settings.LLM_PARSER_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("LangChain parser failed; trying JSON extraction fallback")
        try:
            parsed = _timed_call(
                "parser_fallback",
                lambda: _parse_json_fallback(content),
                settings.LLM_PARSER_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("All parser paths failed; using keyword fallback")
            return _keyword_extraction(ocr_text, "parser_failed")

    try:
        extracted = _timed_call(
            "schema_validation",
            lambda: ExtractionSchema.model_validate(parsed),
            settings.LLM_PARSER_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("Schema validation failed; using keyword fallback")
        return _keyword_extraction(ocr_text, "schema_validation_failed")
    _log_stage(
        "llm_extract",
        "end",
        vendor_present=bool(extracted.vendor_name),
        amount_present=extracted.total_amount is not None,
        category=extracted.expense_category,
    )
    return extracted
