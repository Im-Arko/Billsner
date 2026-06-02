"""Expense classification with LLM and keyword fallback."""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate

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


def classify_expense(
    text: str,
    vendor_name: str | None = None,
) -> tuple[str, list[str], float, str]:
    combined = f"{vendor_name or ''}\n{text}".strip()
    kw_cat, kw_conf = classify_by_keywords(combined)

    if not settings.OPENAI_API_KEY and settings.LLM_PROVIDER == "openai":
        return kw_cat, [], kw_conf, "keyword"

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"Classify expense into one primary category from: {', '.join(CATEGORIES)}. "
                "Also suggest up to 2 secondary categories. Respond as: "
                "PRIMARY|secondary1,secondary2|confidence(0-1)",
            ),
            ("human", "Vendor: {vendor}\n\nText:\n{text}"),
        ]
    )
    try:
        llm = _get_llm()
        resp = (prompt | llm).invoke(
            {"vendor": vendor_name or "unknown", "text": text[:4000]}
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        parts = content.strip().split("|")
        primary = parts[0].strip() if parts else kw_cat
        if primary not in CATEGORIES:
            primary = kw_cat
        secondary = []
        conf = kw_conf
        if len(parts) > 1 and parts[1].strip():
            secondary = [s.strip() for s in parts[1].split(",") if s.strip()]
        if len(parts) > 2:
            try:
                conf = float(parts[2].strip())
            except ValueError:
                pass
        return primary, secondary, conf, "llm"
    except Exception as exc:
        logger.warning("LLM classification failed: %s", exc)
        return kw_cat, [], kw_conf, "keyword"
