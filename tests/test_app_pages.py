"""Smoke tests: the app and each page render without an exception (no Gemini calls)."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import ai_synthesizer
import storage
import ui_modules
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
    monkeypatch.setattr(ai_synthesizer, "generate_summary", lambda *a, **k: {
        "text": "Test summary.", "source": "ai", "model": "test", "notice": None})


@pytest.fixture(autouse=True)
def temp_records(monkeypatch, tmp_path):
    """Never write test patients into the real database."""
    store = storage.LocalStore(tmp_path / "records.json")
    monkeypatch.setattr(views, "get_store", lambda: (store, None))


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


@pytest.mark.parametrize(
    "page", ["home", "new_assessment", "results", "patient_records", "model_comparison", "about"])
def test_page_renders(page):
    _page(page)


def test_results_page_with_an_analysis_shows_all_tabs():
    results = views.run_analysis(PATIENT)
    at = _page("results", {views.RESULTS_KEY: results})
    assert [t.label for t in at.tabs] == ["Overview", "Models", "Details"]
    assert any(b.label == "Edit" for b in at.button)
    assert results["summary"] == "Test summary."


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_wizard_unlocks_each_step_only_when_it_is_complete():
    at = _page("new_assessment")
    assert _button(at, "Next").disabled  # step 1 is empty

    at.text_input(key="name_0").set_value("Test Patient")
    at.number_input(key="age_0").set_value(45)
    at.selectbox(key="gender_0").set_value("Female")
    at.number_input(key="height_0").set_value(165.0)
    at.number_input(key="weight_0").set_value(60.0)
    at.run()
    assert _button(at, "Next").disabled  # blood group still missing
    at.selectbox(key="blood_group_0").set_value("O+").run()
    _button(at, "Next").click().run()

    # Step 2: ancestry is required, everything else has a default.
    assert any(s.key == "ancestry_0" for s in at.selectbox)
    assert _button(at, "Next").disabled
    at.selectbox(key="ancestry_0").set_value("Asian").run()
    _button(at, "Next").click().run()

    # Step 3 is optional, so Generate is ready; Back still keeps earlier answers.
    assert not _button(at, "Generate risk analysis").disabled
    _button(at, "Back").click().run()
    _button(at, "Back").click().run()
    assert at.text_input(key="name_0").value == "Test Patient"


def test_patient_records_page_lists_saved_patients():
    store, _ = views.get_store()
    tier, _ = ui_modules.risk_level(42.8)
    results = {"base": 43.0, "mean": 42.8, "ci": (35.7, 50.4), "models": {}, "summary": "S."}
    store.save(storage.build_record(PATIENT, results, tier))
    at = _page("patient_records")
    html = " ".join(m.value for m in at.markdown)
    assert "Test Patient" in html and "Breast cancer" in html


def test_start_over_clears_the_form_and_result():
    at = _page("new_assessment", {views.RESULTS_KEY: {"mean": 10}})
    at.text_input(key="name_0").set_value("Someone").run()
    _button(at, "Yes, start over").click().run()
    assert not at.exception, at.exception
    assert views.RESULTS_KEY not in at.session_state
    assert at.text_input(key="name_1").value == ""  # fresh, empty form (new generation)


def _save_one():
    store, _ = views.get_store()
    tier, _ = ui_modules.risk_level(42.8)
    results = {"base": 43.0, "mean": 42.8, "ci": (35.7, 50.4), "models": {}, "summary": "S."}
    store.save(storage.build_record(PATIENT, results, tier))
    return store


def test_delete_all_asks_for_confirmation_first():
    store = _save_one()
    at = _page("patient_records")
    _button(at, "Delete all").click().run()
    assert len(store.all_records()) == 1  # nothing deleted yet, only the bar appears
    assert any("Delete all records?" in m.value for m in at.markdown)

    _button(at, "Cancel").click().run()
    assert not any(b.label == "Yes, delete all" for b in at.button)
    assert len(store.all_records()) == 1

    _button(at, "Delete all").click().run()
    _button(at, "Yes, delete all").click().run()
    assert not at.exception, at.exception
    assert store.all_records() == []


def test_export_all_offers_csv_and_pdf():
    _save_one()
    at = _page("patient_records")
    labels = [d.proto.label for d in at.get("download_button")]
    assert "CSV spreadsheet" in labels and "PDF report" in labels


def test_results_page_runs_a_queued_analysis_and_saves_it():
    at = _page("results", {views.PENDING_KEY: PATIENT})
    assert not at.exception, at.exception
    assert views.PENDING_KEY not in at.session_state
    assert at.session_state[views.RESULTS_KEY]["summary"] == "Test summary."
    assert [t.label for t in at.tabs] == ["Overview", "Models", "Details"]
    store, _ = views.get_store()
    assert [r["patient"]["name"] for r in store.all_records()] == ["Test Patient"]


def test_retry_ai_summary_replaces_the_standard_summary(monkeypatch):
    # First run: the AI is down, so the standard summary is used and saved.
    monkeypatch.setattr(ai_synthesizer, "generate_summary", lambda *a, **k: {
        "text": "Standard text.", "source": "fallback", "model": None,
        "notice": "AI summary unavailable: the free Gemini daily limit has been used up."})
    at = _page("results", {views.PENDING_KEY: PATIENT})
    assert any(b.label == "Retry AI summary" for b in at.button)
    store, _ = views.get_store()
    assert store.all_records()[0]["summary_source"] == "fallback"

    # Retry once the AI works again: page, PDF and saved record all update.
    monkeypatch.setattr(ai_synthesizer, "generate_summary", lambda *a, **k: {
        "text": "Fresh AI text.", "source": "ai", "model": "test", "notice": None})
    _button(at, "Retry AI summary").click().run()
    assert not at.exception, at.exception
    assert at.session_state[views.RESULTS_KEY]["summary"] == "Fresh AI text."
    assert not any(b.label == "Retry AI summary" for b in at.button)
    saved = store.all_records()[0]
    assert saved["summary"] == "Fresh AI text." and saved["summary_source"] == "ai"
