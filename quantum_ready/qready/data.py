"""
Patients for the quantum experiments: the same synthetic cohort the web app is
trained on (final_app/data/synthetic_patients.csv), read only.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "final_app" / "data" / "synthetic_patients.csv"
METRICS_PATH = ROOT / "final_app" / "models" / "metrics.json"

# Same order as final_app/ml/schema.py FEATURES.
FEATURES = ["BRCA1", "BRCA2", "APC", "TP53", "Female", "Age", "Smoking",
            "First-degree relatives", "Second-degree relatives"]

DEFAULT_SCALE = 0.1  # the web app's tuned value; replaced by metrics.json when present


def load_cohort(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Create it with `python -m ml.synthetic_data` in final_app/."
        )
    return pd.read_csv(path)


def app_scale() -> float:
    """The angle scale the web app's quantum model was tuned to."""
    try:
        metrics = json.loads(METRICS_PATH.read_text())
        return float(metrics["quantum"]["best_params"]["scale"])
    except (OSError, KeyError, ValueError):
        return DEFAULT_SCALE


def sample(df: pd.DataFrame, n_train: int, n_test: int, seed: int = 0):
    """
    Small stratified train/test split, both with the cohort's outcome rate (and at
    least 2 positives each), so hardware-sized experiments still have cases to find.
    """
    rng = np.random.default_rng(seed)
    pos = rng.permutation(np.flatnonzero(df["Outcome"].to_numpy() == 1))
    neg = rng.permutation(np.flatnonzero(df["Outcome"].to_numpy() == 0))
    rate = len(pos) / len(df)

    def take(n, p_off, n_off):
        k = max(2, round(n * rate))
        return np.concatenate([pos[p_off:p_off + k], neg[n_off:n_off + n - k]]), k, n - k

    train_idx, kp, kn = take(n_train, 0, 0)
    test_idx, _, _ = take(n_test, kp, kn)
    X = df[FEATURES].to_numpy(float)
    y = df["Outcome"].to_numpy(int)
    return X[train_idx], y[train_idx], X[test_idx], y[test_idx]


class AngleScaler:
    """Min-max scales each feature to [0, pi * scale] (fit on training patients only)."""

    def __init__(self, scale: float):
        self.scale = scale

    def fit(self, X):
        self.lo, self.hi = X.min(axis=0), X.max(axis=0)
        return self

    def transform(self, X):
        span = np.where(self.hi > self.lo, self.hi - self.lo, 1.0)
        return np.clip((X - self.lo) / span, 0.0, 1.0) * np.pi * self.scale
