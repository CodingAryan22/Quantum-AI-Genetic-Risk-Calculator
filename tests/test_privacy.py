"""The prompt sent to Gemini must not contain direct identifiers."""

import ai_synthesizer
import quantum_engine


def _patient():
    return {
        "Name": "Priya Sharma",
        "Age": 47,
        "Gender": "Female",
        "Smoking History": "Never Smoked",
        "Genetic Markers": {"BRCA1": True, "BRCA2": "Negative", "APC": False, "TP53": False},
        "Family History": {"First-degree": 1, "Second-degree": 0},
        "Additional Details": (
            "Priya reports a lump. Contact 98765 43210 or priya.s@example.com, MRN 12345678. "
            "Mrs Sharma's mother had breast cancer."
        ),
    }


def _prompt():
    patient = _patient()
    table, _ = quantum_engine.run_simulation(patient, seed=1)
    return ai_synthesizer.build_prompt(patient, table, {"Quantum kernel SVM": 0.8})


def test_prompt_contains_no_identifiers():
    prompt = _prompt().lower()
    for secret in ["priya", "sharma", "98765", "43210", "example.com", "12345678", " 47"]:
        assert secret not in prompt, secret


def test_prompt_keeps_the_clinical_information():
    prompt = _prompt()
    assert "Age band: 40-49" in prompt
    assert "BRCA1" in prompt and "BRCA2 (" not in prompt  # "Negative" is not a mutation
    assert "1 first-degree" in prompt
    assert "Quantum kernel SVM: 80%" in prompt
    assert "mother had breast cancer" in prompt


def test_deidentify_handles_text_without_a_name():
    assert ai_synthesizer.deidentify("", "Anyone") == ""
    assert ai_synthesizer.deidentify("call +91 98765 43210", "") == "call [phone removed]"
