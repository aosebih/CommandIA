"""Retry and model fallback behaviour."""
import pytest

from ai.ai_brain import AIBrain, _suggested_retry_delay


class FakeError(Exception):
    pass


def test_suggested_delay_is_extracted_from_the_provider_message():
    error = FakeError(
        "You exceeded your current quota. Please retry in 15.56543398s."
    )
    assert _suggested_retry_delay(error) == pytest.approx(15.56543398)


def test_suggested_delay_is_none_without_the_message():
    assert _suggested_retry_delay(FakeError("boom")) is None


def test_backoff_grows_exponentially(brain):
    assert brain._retry_delay(FakeError("boom"), 1) == pytest.approx(2.0)
    assert brain._retry_delay(FakeError("boom"), 2) == pytest.approx(4.0)
    assert brain._retry_delay(FakeError("boom"), 3) == pytest.approx(8.0)


def test_provider_delay_wins_when_it_is_longer(brain):
    error = FakeError("Rate limit exceeded. Please retry in 15.5s.")
    assert brain._retry_delay(error, 1) == pytest.approx(15.5)


def test_backoff_wins_when_it_is_longer(brain):
    error = FakeError("Rate limit exceeded. Please retry in 1.0s.")
    assert brain._retry_delay(error, 3) == pytest.approx(8.0)


def test_delay_is_capped(brain):
    error = FakeError("Please retry in 900s.")
    assert brain._retry_delay(error, 1) == pytest.approx(60.0)


def test_fallback_model_is_used_when_the_primary_fails(monkeypatch):
    """A transient failure on the primary model must fall back to the next."""
    from google.genai import errors as genai_errors

    from tests.conftest import StubResponse

    calls = []

    class FlakyModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls.append(model)
            if model == "gemini-3.5-flash-lite":
                raise genai_errors.APIError(
                    code=503,
                    response_json={"error": {"message": "The model is overloaded."}},
                )
            return StubResponse('{"reply_to_customer": "ok", "extracted_data": {}}')

    class FlakyClient:
        models = FlakyModels()

    brain = AIBrain.__new__(AIBrain)
    brain.api_key = "stub"
    brain.model = "gemini-3.5-flash-lite"
    brain.models = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
    brain.system_prompt = "SYS"
    brain.client = FlakyClient()

    monkeypatch.setattr("ai.ai_brain.time.sleep", lambda seconds: None)

    response = brain._generate_content("prompt")
    assert response.text.startswith("{")
    # The primary model is retried up to MAX_RETRIES times, then the fallback
    # model takes over and succeeds.
    assert calls[-1] == "gemini-3.5-flash"
    assert calls.count("gemini-3.5-flash-lite") == 3


def test_permanent_error_is_not_retried(monkeypatch):
    from google.genai import errors as genai_errors

    calls = []

    class BrokenModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls.append(model)
            raise genai_errors.APIError(
                code=400,
                response_json={"error": {"message": "API key not valid."}},
            )

    class BrokenClient:
        models = BrokenModels()

    brain = AIBrain.__new__(AIBrain)
    brain.api_key = "stub"
    brain.model = "gemini-3.5-flash-lite"
    brain.models = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
    brain.system_prompt = "SYS"
    brain.client = BrokenClient()

    sleeps = []
    monkeypatch.setattr("ai.ai_brain.time.sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(genai_errors.APIError):
        brain._generate_content("prompt")

    # A permanent error is not retried, but the fallback model is still tried.
    assert sleeps == []
    assert calls == ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
