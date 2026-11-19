"""Smoke tests: the app and each page render without an exception (no Gemini calls)."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import ai_synthesizer
import views

APP = os.path.join(os.path.dirname(__file__), "..", "final_app", "final_app.py")

PATIENT = {
    "Name": "Test Patient", "Age": 45, "Gender": "Female", "Height": None, "Weight": None,
    "Blood Group": "Select", "Ancestry": "Select", "Smoking History": "Never Smoked",
    "Family History": {"First-degree": 1, "Second-degree": 0},
    "Genetic Markers": {"BRCA1": True, "BRCA2": False, "APC": False, "TP53": False},
    "Other Genetic Markers": [], "Lab Report": None, "Additional Details": "",
}


@pytest.fixture(autouse=True)
def no_gemini(monkeypatch):
    """Never call the real Gemini API from tests."""
    monkeypatch.setattr(ai_synthesizer, "generate_report", lambda *a, **k: "Test summary.")


def _page(function_name: str, state: dict | None = None) -> AppTest:
    at = AppTest.from_string(
        "import ui_modules, views\n"
        "ui_modules.apply_theme(False)\n"
        f"views.{function_name}()\n",
        default_timeout=60,
    )
    for k, v in (state or {}).items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def test_full_app_starts_on_home():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert any("Start new assessment" in b.label for b in at.button)


@pytest.mark.parametrize("page", ["home", "new_assessment", "results", "model_comparison", "about"])
def test_page_renders(page):
    _page(page)


def test_results_page_with_an_analysis_shows_all_tabs():
    results = views.run_analysis(PATIENT)
    at = _page("results", {views.RESULTS_KEY: results})
    assert [t.label for t in at.tabs] == ["Overview", "Models", "Details"]
    assert any(b.label == "Edit" for b in at.button)
    assert results["summary"] == "Test summary."


def test_generate_with_empty_form_shows_validation_errors():
    at = _page("new_assessment")
    next(b for b in at.button if b.label == "Generate risk analysis").click().run()
    assert not at.exception, at.exception
    assert any("Please fix the following" in e.value for e in at.error)
    assert views.RESULTS_KEY not in at.session_state
