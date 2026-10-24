import json

import httpx
import pytest

from app.ai import classifier, groq_client, llm_extractor


@pytest.fixture
def groq_request(monkeypatch):
    monkeypatch.setattr(groq_client.get_settings(), "GROQ_API_KEY", "test-key-not-real")
    original_client = httpx.Client

    def use_response(handler):
        monkeypatch.setattr(groq_client.httpx, "Client", lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs))

    return use_response


def test_groq_request_uses_hosted_model_and_json_mode(groq_request):
    def handler(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == groq_client.get_settings().GROQ_MODEL
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"total_amount": 123.45, "vendor_name": "Test Cafe"}'}}]})

    groq_request(handler)
    result = llm_extractor.extract_structured_data("Test Cafe Total 123.45")
    assert result.total_amount == 123.45
    assert result.vendor_name == "Test Cafe"


@pytest.mark.parametrize("status, message", [(401, "API key"), (403, "model access"), (429, "rate limit"), (503, "HTTP 503")])
def test_groq_failures_are_actionable(groq_request, status, message):
    groq_request(lambda _: httpx.Response(status))
    with pytest.raises(groq_client.GroqError, match=message):
        llm_extractor.extract_structured_data("Total 123.45")


def test_missing_groq_key_does_not_make_a_request(monkeypatch):
    monkeypatch.setattr(groq_client.get_settings(), "GROQ_API_KEY", "")
    with pytest.raises(groq_client.GroqError, match="GROQ_API_KEY"):
        groq_client.complete_json("Return JSON", "test")


def test_groq_timeout_has_clear_message(groq_request):
    def handler(request):
        raise httpx.ReadTimeout("test", request=request)
    groq_request(handler)
    with pytest.raises(groq_client.GroqError, match="timed out"):
        groq_client.complete_json("Return JSON", "test")


def test_invalid_bill_json_is_rejected(groq_request):
    groq_request(lambda _: httpx.Response(200, json={"choices": [{"message": {"content": '{"total_amount": "not an amount"}'}}]}))
    with pytest.raises(groq_client.GroqError, match="invalid bill data"):
        llm_extractor.extract_structured_data("Total unknown")


def test_classification_uses_groq(groq_request):
    groq_request(lambda _: httpx.Response(200, json={"choices": [{"message": {"content": '{"category": "Food", "secondary_categories": [], "confidence": 0.9}'}}]}))
    category, _, confidence, method = classifier.classify_expense("Lunch at Cafe")
    assert (category, confidence, method) == ("Food", 0.9, "groq")
