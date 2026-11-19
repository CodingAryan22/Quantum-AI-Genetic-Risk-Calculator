"""
Trains and evaluates every risk model on the synthetic cohort.

    python -m ml.train            (run from the final_app folder)

Steps
1. Load data/synthetic_patients.csv (regenerated if missing).
2. Stratified 75/25 train/test split (fixed seed, so results are reproducible).
3. Models
     - Rule-based score  : the app's hand-weighted score (no training), for reference
     - Logistic regression (standardised features)
     - Random forest
     - Quantum kernel SVM: Qiskit ZZ feature map + fidelity kernel; scale and C
                           chosen by 5-fold cross-validation on the training set
4. Metrics on the held-out test set: ROC AUC, Brier score, and accuracy /
   sensitivity / specificity / F1 when "at risk" means predicted risk >= 20%
   (the app's moderate-risk threshold). Plus 5-fold CV AUC on the training set,
   fit time and prediction time.
5. Save models/*.joblib and models/metrics.json (read by the app).
"""

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, f1_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import synthetic_data
from .quantum_kernel import QuantumKernelSVM, circuit_summary, fidelity_kernel, statevectors
from .schema import FEATURES, row_to_patient

try:
    from quantum_engine import calculate_deterministic_risk
except ModuleNotFoundError:  # imported as final_app.ml.train
    from ..quantum_engine import calculate_deterministic_risk

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
SEED = 42
THRESHOLD = 0.20  # "at risk" cut-off, same as the app's moderate-risk tier

MODEL_FILES = {
    "Logistic regression": "logistic_regression.joblib",
    "Random forest": "random_forest.joblib",
    "Quantum kernel SVM": "quantum_kernel_svm.joblib",
}


def _rule_based_proba(X: pd.DataFrame) -> np.ndarray:
    return np.array([calculate_deterministic_risk(row_to_patient(r)) / 100.0
                     for _, r in X.iterrows()])


def _evaluate(y_true, proba) -> dict:
    flag = (proba >= THRESHOLD).astype(int)
    fpr, tpr, _ = roc_curve(y_true, proba)
    # Keep the ROC curve small enough for metrics.json.
    idx = np.unique(np.linspace(0, len(fpr) - 1, min(len(fpr), 80)).astype(int))
    return {
        "auc": round(float(roc_auc_score(y_true, proba)), 4),
        "brier": round(float(brier_score_loss(y_true, proba)), 4),
        "accuracy": round(float(accuracy_score(y_true, flag)), 4),
        "sensitivity": round(float(recall_score(y_true, flag)), 4),
        "specificity": round(float(recall_score(1 - np.asarray(y_true), 1 - flag)), 4),
        "f1": round(float(f1_score(y_true, flag)), 4),
        "roc": {"fpr": [round(float(v), 4) for v in fpr[idx]],
                "tpr": [round(float(v), 4) for v in tpr[idx]]},
    }


def _tune_quantum(X_train, y_train, scales, Cs, folds):
    """
    Picks (scale, C) by cross-validated AUC. Circuits are simulated once per
    scale; every C and fold then reuses the same kernel matrix.
    """
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)
    probe = QuantumKernelSVM()
    probe.x_min_, probe.x_max_ = X_train.min(axis=0), X_train.max(axis=0)
    best = None
    for scale in scales:
        probe.scale = scale
        states = statevectors(probe._angles(X_train))
        K = fidelity_kernel(states, states)
        for C in Cs:
            aucs = []
            for tr, va in cv.split(K, y_train):
                svc = SVC(kernel="precomputed", C=C).fit(K[np.ix_(tr, tr)], y_train[tr])
                aucs.append(roc_auc_score(y_train[va], svc.decision_function(K[np.ix_(va, tr)])))
            score = float(np.mean(aucs))
            if best is None or score > best["cv_auc"]:
                best = {"scale": scale, "C": C, "cv_auc": score,
                        "cv_auc_std": float(np.std(aucs)), "states": states}
    return best


def train_models(df: pd.DataFrame, quick: bool = False):
    """
    Trains every model and returns (fitted_models, metrics).
    quick=True uses fewer trees, a smaller quantum training set and grid (for tests).
    """
    X = df[FEATURES]
    y = df["Outcome"].to_numpy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=SEED)
    Xtr, Xte = X_train.to_numpy(float), X_test.to_numpy(float)
    folds = 3 if quick else 5
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)

    models, results = {}, {}

    # Rule-based score: no training, evaluated for reference.
    t0 = time.perf_counter()
    proba = _rule_based_proba(X_test)
    results["Rule-based score"] = {
        **_evaluate(y_test, proba), "cv_auc": None, "cv_auc_std": None, "fit_seconds": 0.0,
        "predict_ms": round((time.perf_counter() - t0) / len(X_test) * 1000, 3),
        "train_size": 0,
    }

    classical = {
        "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "Random forest": RandomForestClassifier(
            n_estimators=100 if quick else 400, min_samples_leaf=10, random_state=SEED, n_jobs=-1),
    }
    for name, model in classical.items():
        cv_scores = cross_val_score(model, Xtr, y_train, cv=cv, scoring="roc_auc")
        t0 = time.perf_counter()
        model.fit(Xtr, y_train)
        fit_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        proba = model.predict_proba(Xte)[:, 1]
        pred_ms = (time.perf_counter() - t0) / len(Xte) * 1000
        models[name] = model
        results[name] = {
            **_evaluate(y_test, proba),
            "cv_auc": round(float(cv_scores.mean()), 4),
            "cv_auc_std": round(float(cv_scores.std()), 4),
            "fit_seconds": round(fit_s, 3), "predict_ms": round(pred_ms, 3),
            "train_size": len(Xtr),
        }

    # Quantum kernel SVM.
    if quick:
        q_idx = np.random.default_rng(SEED).choice(len(Xtr), size=min(240, len(Xtr)), replace=False)
        Xq, yq, scales, Cs = Xtr[q_idx], y_train[q_idx], [0.5], [1.0]
    else:
        Xq, yq, scales, Cs = Xtr, y_train, [0.1, 0.25, 0.5, 1.0], [0.05, 0.25, 1.0, 4.0]
    t0 = time.perf_counter()
    best = _tune_quantum(Xq, yq, scales, Cs, folds)
    qsvm = QuantumKernelSVM(scale=best["scale"], C=best["C"], random_state=SEED)
    qsvm.x_min_, qsvm.x_max_ = Xq.min(axis=0), Xq.max(axis=0)
    t1 = time.perf_counter()
    qsvm.fit(Xq, yq, states=best["states"])
    fit_s = time.perf_counter() - t1
    tune_s = t1 - t0
    t0 = time.perf_counter()
    proba = qsvm.predict_proba(Xte)[:, 1]
    pred_ms = (time.perf_counter() - t0) / len(Xte) * 1000
    models["Quantum kernel SVM"] = qsvm
    results["Quantum kernel SVM"] = {
        **_evaluate(y_test, proba),
        "cv_auc": round(best["cv_auc"], 4), "cv_auc_std": round(best["cv_auc_std"], 4),
        "fit_seconds": round(fit_s, 3), "tuning_seconds": round(tune_s, 1),
        "predict_ms": round(pred_ms, 3), "train_size": len(Xq),
    }

    lr = models["Logistic regression"][-1]
    metrics = {
        "dataset": {
            "source": "synthetic (ml/synthetic_data.py) - simulated patients, not real data",
            "outcome": "hereditary-spectrum cancer diagnosed within 20 years",
            "n_patients": int(len(df)), "n_train": int(len(X_train)), "n_test": int(len(X_test)),
            "outcome_rate": round(float(y.mean()), 4),
            "features": FEATURES,
            "oracle_auc": round(float(roc_auc_score(y_test, df.loc[X_test.index, "True Risk"])), 4),
            "threshold": THRESHOLD,
        },
        "quantum": {**circuit_summary(len(FEATURES)),
                    "best_params": {"scale": best["scale"], "C": best["C"]}},
        "models": results,
        "feature_importance": {
            "Logistic regression (standardised coefficient)":
                dict(zip(FEATURES, [round(float(c), 4) for c in lr.coef_[0]])),
            "Random forest (impurity importance)":
                dict(zip(FEATURES, [round(float(v), 4)
                                    for v in models["Random forest"].feature_importances_])),
        },
    }
    return models, metrics


def main():
    if not synthetic_data.DATA_PATH.exists():
        synthetic_data.main()
    df = pd.read_csv(synthetic_data.DATA_PATH)
    print(f"Training on {len(df)} synthetic patients...")
    models, metrics = train_models(df)

    MODELS_DIR.mkdir(exist_ok=True)
    for name, model in models.items():
        joblib.dump(model, MODELS_DIR / MODEL_FILES[name], compress=3)
    (MODELS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"\nTest set ({metrics['dataset']['n_test']} patients), "
          f"best possible AUC {metrics['dataset']['oracle_auc']}")
    print(f"{'Model':<22}{'AUC':>7}{'CV AUC':>9}{'Brier':>8}{'Sens':>7}{'Spec':>7}{'Fit s':>8}")
    for name, r in metrics["models"].items():
        cv = f"{r['cv_auc']:.3f}" if r["cv_auc"] is not None else "-"
        print(f"{name:<22}{r['auc']:>7.3f}{cv:>9}{r['brier']:>8.3f}"
              f"{r['sensitivity']:>7.2f}{r['specificity']:>7.2f}{r['fit_seconds']:>8.2f}")
    print(f"\nSaved models and metrics to {MODELS_DIR}")


if __name__ == "__main__":
    main()
