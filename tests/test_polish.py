"""Tests for form validation, the bounded simulation and PDF text cleanup."""

import os
import sys

import numpy as np

# The app's modules import each other as top-level modules (`import ui_modules`),
# the way `streamlit run final_app.py` loads them, so put final_app/ on the path.
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "final_app"))

import data_manager  # noqa: E402
import pdf_builder  # noqa: E402
import quantum_engine  # noqa: E402


def _patient(**overrides):
    patient = {
        "Name": "Test Patient",
        "Age": 45,
        "Gender": "Female",
        "Height": None,
        "Weight": None,
        "Smoking History": "Never Smoked",
        "Genetic Markers": {"BRCA1": False, "BRCA2": False, "APC": False, "TP53": False},
    }
    patient.update(overrides)
    return patient


def test_complete_form_passes_validation():
    assert data_manager.validate_patient(_patient()) == []


def test_empty_form_lists_every_required_field():
    problems = data_manager.validate_patient(
        _patient(Name="  ", Age=None, Gender="Select")
    )
    assert len(problems) == 3


def test_unrealistic_height_and_weight_are_rejected():
    problems = data_manager.validate_patient(_patient(Height=500.0, Weight=0.5))
    assert len(problems) == 2


def test_low_risk_simulation_does_not_pile_up_at_zero():
    table, fig = quantum_engine.run_simulation(_patient(), iterations=4000, seed=7)
    lower = float(table["90% Confidence Interval"].iloc[0].split("%")[0].lstrip("["))
    mean = float(table["Simulated Mean"].iloc[0].rstrip("%"))
    assert lower > 0.0, "5th percentile should be above 0% once clipping is gone"
    assert abs(mean - 5.0) < 0.5, "simulated mean should match the 5% baseline"


def test_simulation_stays_inside_0_to_100_for_extreme_risk():
    markers = {"BRCA1": True, "BRCA2": True, "APC": True, "TP53": True}
    table, fig = quantum_engine.run_simulation(
        _patient(**{"Genetic Markers": markers, "Age": 80}), iterations=4000, seed=7
    )
    z = np.array(fig.data[0].z)
    assert np.isclose(z.sum(), 100.0, atol=0.5), "every run must land in a 0-100% bin"


def test_pdf_text_strips_markdown_and_smart_punctuation():
    raw = "## Heading\n**Bold** and *BRCA1* — it’s “fine”.\n* item\nsnake_case 2*3"
    clean = pdf_builder._pdf_text(pdf_builder._strip_markdown(raw))
    assert clean == "Heading\nBold and BRCA1 - it's \"fine\".\n- item\nsnake_case 2*3"
