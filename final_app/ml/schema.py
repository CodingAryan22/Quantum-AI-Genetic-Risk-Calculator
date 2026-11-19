"""
The single definition of the model features.

The synthetic generator, the training script and the app all go through
`patient_to_vector`, so a patient entered in the form is encoded exactly the
way the training data was.
"""

import numpy as np

try:
    from features import normalize_marker_status
except ModuleNotFoundError:  # imported as final_app.ml.schema
    from ..features import normalize_marker_status

MARKERS = ["BRCA1", "BRCA2", "APC", "TP53"]

# Order matters: models are trained on columns in exactly this order.
FEATURES = MARKERS + [
    "Female",
    "Age",
    "Smoking",
    "First-degree relatives",
    "Second-degree relatives",
]

# Human-readable labels for charts.
FEATURE_LABELS = {
    "BRCA1": "BRCA1 mutation",
    "BRCA2": "BRCA2 mutation",
    "APC": "APC mutation",
    "TP53": "TP53 mutation",
    "Female": "Sex (female)",
    "Age": "Age",
    "Smoking": "Smoking",
    "First-degree relatives": "Family history (1st-degree)",
    "Second-degree relatives": "Family history (2nd-degree)",
}

SMOKING_CODES = {"Never Smoked": 0, "Former Smoker": 1, "Current Smoker": 2}

# Reasonable defaults for fields left blank in the form.
DEFAULT_AGE = 45.0

_MARKER_VALUE = {"Positive": 1.0, "Inconclusive": 0.5, "Negative": 0.0}


def _female_value(gender) -> float:
    if gender == "Female":
        return 1.0
    if gender == "Male":
        return 0.0
    return 0.5  # "Other" / not given: halfway between the two


def patient_to_vector(patient_data: dict) -> np.ndarray:
    """Encodes a form-style patient dict as a 1-D feature vector (FEATURES order)."""
    genetics = patient_data.get("Genetic Markers", {}) or {}
    family = patient_data.get("Family History", {}) or {}

    age = patient_data.get("Age")
    try:
        age = float(age) if age is not None else DEFAULT_AGE
    except (TypeError, ValueError):
        age = DEFAULT_AGE

    values = [_MARKER_VALUE[normalize_marker_status(genetics.get(m))] for m in MARKERS]
    values += [
        _female_value(patient_data.get("Gender")),
        age,
        float(SMOKING_CODES.get(patient_data.get("Smoking History"), 0)),
        float(family.get("First-degree", 0) or 0),
        float(family.get("Second-degree", 0) or 0),
    ]
    return np.array(values, dtype=float)


def row_to_patient(row) -> dict:
    """Turns one row of the synthetic dataset back into a form-style patient dict."""
    smoking = {v: k for k, v in SMOKING_CODES.items()}[int(row["Smoking"])]
    return {
        "Age": float(row["Age"]),
        "Gender": "Female" if row["Female"] >= 0.5 else "Male",
        "Smoking History": smoking,
        "Genetic Markers": {m: bool(row[m]) for m in MARKERS},
        "Family History": {
            "First-degree": int(row["First-degree relatives"]),
            "Second-degree": int(row["Second-degree relatives"]),
        },
    }
