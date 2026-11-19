"""
Loads the trained models and scores a single patient for the app.
"""

import json
from pathlib import Path

import joblib
import numpy as np

from .schema import FEATURE_LABELS, FEATURES, patient_to_vector
from .train import MODEL_FILES, MODELS_DIR


class ModelsNotTrained(FileNotFoundError):
    pass


def load_models(models_dir: Path = MODELS_DIR) -> dict:
    """Returns {model name: fitted model}. Raises ModelsNotTrained if files are missing."""
    missing = [f for f in MODEL_FILES.values() if not (models_dir / f).exists()]
    if missing:
        raise ModelsNotTrained(
            f"Missing {', '.join(missing)} in {models_dir}. Run `python -m ml.train` "
            "from the final_app folder."
        )
    return {name: joblib.load(models_dir / f) for name, f in MODEL_FILES.items()}


def load_metrics(models_dir: Path = MODELS_DIR) -> dict | None:
    path = models_dir / "metrics.json"
    return json.loads(path.read_text()) if path.exists() else None


def predict_all(models: dict, patient_data: dict) -> dict:
    """Predicted 20-year risk (0-1) from every trained model."""
    x = patient_to_vector(patient_data).reshape(1, -1)
    return {name: float(model.predict_proba(x)[0, 1]) for name, model in models.items()}


def explain(models: dict, patient_data: dict) -> list[dict]:
    """
    Why the logistic regression gave this patient their risk.

    For a logistic regression the log-odds are an exact sum:
        log-odds = intercept + sum_i coef_i * z_i,   z_i = (x_i - mean_i) / std_i
    so coef_i * z_i is feature i's exact contribution compared with an average
    patient in the training data (z_i = 0). Positive = pushes risk up.

    Returns one dict per feature, sorted by absolute contribution.
    """
    pipeline = models["Logistic regression"]
    scaler, lr = pipeline[0], pipeline[-1]
    x = patient_to_vector(patient_data)
    z = (x - scaler.mean_) / scaler.scale_
    contrib = lr.coef_[0] * z
    rows = [
        {"feature": f, "label": FEATURE_LABELS[f], "value": float(v), "log_odds": float(c)}
        for f, v, c in zip(FEATURES, x, contrib)
    ]
    return sorted(rows, key=lambda r: abs(r["log_odds"]), reverse=True)


def average_risk(models: dict) -> float:
    """Logistic-regression risk of an exactly average training patient (all z = 0)."""
    lr = models["Logistic regression"][-1]
    return float(1.0 / (1.0 + np.exp(-lr.intercept_[0])))
