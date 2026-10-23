import pytest

from final_app.quantum_engine import calculate_deterministic_risk, run_simulation


def test_inconclusive_markers_do_not_inflate_risk_excessively():
    patient = {
        "Age": 35,
        "Smoking History": "Never Smoked",
        "Genetic Markers": {
            "BRCA1": "Inconclusive",
            "BRCA2": "Negative",
            "APC": "Negative",
            "TP53": "Negative",
        },
    }

    risk = calculate_deterministic_risk(patient)
    assert risk < 25, f"Inconclusive markers should not inflate risk this much: {risk}"


def test_simulation_is_reproducible_with_seed():
    patient = {
        "Age": 42,
        "Smoking History": "Former Smoker",
        "Genetic Markers": {
            "BRCA1": "Positive",
            "BRCA2": "Negative",
            "APC": "Negative",
            "TP53": "Positive",
        },
    }

    first = run_simulation(patient, iterations=600, seed=42)
    second = run_simulation(patient, iterations=600, seed=42)

    assert first[0].equals(second[0])
