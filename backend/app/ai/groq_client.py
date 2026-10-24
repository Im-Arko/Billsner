"""Small Groq Cloud client shared by extraction and classification."""

import httpx

from app.config import get_settings


class GroqError(RuntimeError):
    pass


def complete_json(system: str, user: str) -> str:
    settings = get_settings()
    if not settings.GROQ_API_KEY.strip():
        raise GroqError("Set GROQ_API_KEY in backend/.env before processing bills.")
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.LLM_TIMEOUT_SECONDS, connect=10)) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                    "max_completion_tokens": 4096,
                },
            )
    except httpx.TimeoutException as exc:
        raise GroqError("Groq request timed out. Please retry the bill.") from exc
    except httpx.RequestError as exc:
        raise GroqError("Cannot reach Groq Cloud. Check your internet connection.") from exc
    if response.status_code in {401, 403}:
        raise GroqError("Groq rejected the API key or model access. Check GROQ_API_KEY and GROQ_MODEL.")
    if response.status_code == 429:
        raise GroqError("Groq rate limit reached. Wait a moment and retry the bill.")
    if response.is_error:
        raise GroqError(f"Groq returned HTTP {response.status_code}. Check the configured model or retry later.")
    try:
        message = response.json()["choices"][0]
        content = message["message"]["content"]
        if message.get("finish_reason") == "length":
            raise GroqError("Groq response was truncated. Please retry with a smaller bill.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty response")
        return content
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise GroqError("Groq returned an unreadable response. Please retry the bill.") from exc
