"""Expense classification with LLM and keyword fallback."""

from __future__ import annotations

import logging

import json
import math

from app.ai.groq_client import complete_json

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CATEGORIES = [
    "Fuel",
    "Hotel",
    "Food",
    "Travel",
    "Medical",
    "Shopping",
    "Miscellaneous",
]

KEYWORD_MAP: dict[str, list[str]] = {
    "Fuel": ["petrol", "diesel", "fuel", "hp", "ioc", "bharat petroleum", "gas station"],
    "Hotel": ["hotel", "lodging", "resort", "inn", "accommodation"],
    "Food": ["restaurant", "cafe", "food", "swiggy", "zomato", "dining"],
    "Travel": ["flight", "airline", "train", "uber", "ola", "taxi", "travel", "irctc"],
    "Medical": ["hospital", "pharmacy", "medical", "clinic", "medicine"],
    "Shopping": ["mart", "store", "amazon", "flipkart", "retail", "mall"],
}


def classify_by_keywords(text: str) -> tuple[str, float]:
    lower = text.lower()
    scores: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in lower:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    count = scores[best]
    if count == 0:
        return "Miscellaneous", 0.3
    confidence = min(0.95, 0.4 + count * 0.15)
    return best, confidence



def classify_expense(text: str, vendor_name: str | None = None) -> tuple[str, list[str], float, str]:
    combined = f"{vendor_name or ''}\n{text}".strip()
    kw_cat, kw_conf = classify_by_keywords(combined)
    try:
        content = complete_json(
            "Classify the expense into one of: " + ", ".join(CATEGORIES) +
            '. Return JSON with category (string), secondary_categories (array), confidence (0 to 1).',
            combined[:4000],
        )
        parsed = json.loads(content)
        primary = parsed.get("category", kw_cat)
        if primary not in CATEGORIES:
            primary = kw_cat
        secondary = parsed.get("secondary_categories", [])
        secondary = [s for s in secondary if s in CATEGORIES] if isinstance(secondary, list) else []
        confidence = float(parsed.get("confidence", kw_conf))
        if not math.isfinite(confidence):
            confidence = kw_conf
        return primary, secondary[:2], min(1.0, max(0.0, confidence)), "groq"
    except Exception as exc:
        logger.warning("Groq classification unavailable; using keywords: %s", exc)
        return kw_cat, [], kw_conf, "keyword"
