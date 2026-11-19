"""AI summary: model fallback order, quota messages and the built-in standard summary."""

import pytest

import ai_synthesizer
import quantum_engine

PATIENT = {
    "Name": "Test Patient", "Age": 45, "Gender": "Female", "Smoking History": "Never Smoked",
    "Genetic Markers": {"BRCA1": True, "BRCA2": False, "APC": False, "TP53": False},
    "Family History": {"First-degree": 1, "Second-degree": 0},
}
DAILY = Exception('429 quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier" '
                  "retry_delay { seconds: 59845 }")


def _table():
    table, _ = quantum_engine.run_simulation(PATIENT, seed=1)
    return table


@pytest.fixture
def fake_gemini(monkeypatch):
    """Replace Gemini: `answers[model]` is either the reply text or an exception to raise."""
    answers, calls = {}, []

    class FakeModel:
        def __init__(self, name):
            self.name = name

        def generate_content(self, prompt, request_options=None):
            calls.append(self.name)
            answer = answers[self.name]
            if isinstance(answer, Exception):
                raise answer
            return type("Response", (), {"text": answer})()

    monkeypatch.setattr(ai_synthesizer, "configure_api", lambda: True)
    monkeypatch.setattr(ai_synthesizer.genai, "GenerativeModel", FakeModel)
    monkeypatch.setattr(ai_synthesizer, "_models", lambda: ["first", "second"])
    return answers, calls


def test_first_model_answers(fake_gemini):
    answers, calls = fake_gemini
    answers.update(first="AI text", second="unused")
    out = ai_synthesizer.generate_summary(PATIENT, _table())
    assert out == {"text": "AI text", "source": "ai", "model": "first", "notice": None}
    assert calls == ["first"]


def test_out_of_quota_model_falls_through_to_the_next(fake_gemini):
    answers, calls = fake_gemini
    answers.update(first=DAILY, second="Lite text")
    out = ai_synthesizer.generate_summary(PATIENT, _table())
    assert out["source"] == "ai" and out["model"] == "second" and out["text"] == "Lite text"


def test_all_models_down_gives_the_standard_summary_and_an_accurate_reason(fake_gemini):
    answers, _ = fake_gemini
    answers.update(first=DAILY, second=DAILY)
    out = ai_synthesizer.generate_summary(PATIENT, _table())
    assert out["source"] == "fallback"
    assert "daily limit" in out["notice"] and "17 hours" in out["notice"]
    assert "BRCA1" in out["text"] and "moderate risk" in out["text"]
    assert "429" not in out["text"] and "quota" not in out["text"].lower()


def test_no_api_key_gives_the_standard_summary(monkeypatch):
    monkeypatch.setattr(ai_synthesizer, "configure_api", lambda: False)
    out = ai_synthesizer.generate_summary(PATIENT, _table())
    assert out["source"] == "fallback" and "API key" in out["notice"]


def test_per_minute_limit_message():
    msg = ai_synthesizer._describe_error(Exception("429 PerMinute retry_delay { seconds: 31 }"))
    assert "per-minute" in msg and "31 seconds" in msg


def test_slow_model_is_skipped(fake_gemini):
    answers, _ = fake_gemini
    answers.update(first=type("DeadlineExceeded", (Exception,), {})("504 Deadline Exceeded"),
                   second="Lite text")
    out = ai_synthesizer.generate_summary(PATIENT, _table())
    assert out["source"] == "ai" and out["model"] == "second"
    assert "took too long" in ai_synthesizer._describe_error(
        type("DeadlineExceeded", (Exception,), {})("504"))
