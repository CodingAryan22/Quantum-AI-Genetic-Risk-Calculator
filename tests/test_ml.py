"""Tests for the ML pipeline: features, synthetic data, quantum kernel, training, prediction."""

import numpy as np
import pytest

from ml import predictor, synthetic_data
from ml.quantum_kernel import fidelity_kernel, statevectors
from ml.schema import FEATURES, patient_to_vector, row_to_patient
from ml.train import train_models
import quantum_engine


def _patient(**overrides):
    patient = {
        "Name": "Test Patient",
        "Age": 45,
        "Gender": "Female",
        "Smoking History": "Never Smoked",
        "Genetic Markers": {"BRCA1": False, "BRCA2": False, "APC": False, "TP53": False},
        "Family History": {"First-degree": 0, "Second-degree": 0},
    }
    patient.update(overrides)
    return patient


# ---------- feature schema ----------

def test_patient_vector_encodes_every_feature_in_order():
    x = patient_to_vector(_patient(**{
        "Genetic Markers": {"BRCA1": True, "TP53": "Inconclusive"},
        "Smoking History": "Current Smoker",
        "Family History": {"First-degree": 2, "Second-degree": 1},
    }))
    assert dict(zip(FEATURES, x)) == {
        "BRCA1": 1.0, "BRCA2": 0.0, "APC": 0.0, "TP53": 0.5, "Female": 1.0, "Age": 45.0,
        "Smoking": 2.0, "First-degree relatives": 2.0, "Second-degree relatives": 1.0,
    }


def test_blank_fields_get_safe_defaults():
    x = dict(zip(FEATURES, patient_to_vector({"Gender": "Select"})))
    assert x["Age"] == 45.0 and x["Female"] == 0.5 and x["BRCA1"] == 0.0


def test_dataset_rows_round_trip_through_the_form_format():
    df = synthetic_data.generate(n=50, seed=3)
    for _, row in df.iterrows():
        assert np.allclose(patient_to_vector(row_to_patient(row)), row[FEATURES].to_numpy(float))


# ---------- synthetic data ----------

def test_generator_is_reproducible():
    a, b = synthetic_data.generate(n=300, seed=7), synthetic_data.generate(n=300, seed=7)
    assert a.equals(b)


def test_synthetic_risks_are_valid_and_carriers_are_higher():
    df = synthetic_data.generate(n=2000, seed=1)
    assert df["True Risk"].between(0, 1).all()
    carrier = df[["BRCA1", "BRCA2", "APC", "TP53"]].sum(axis=1) > 0
    assert df.loc[carrier, "True Risk"].mean() > 3 * df.loc[~carrier, "True Risk"].mean()
    assert 0.05 < df["Outcome"].mean() < 0.40


def test_family_history_and_smoking_raise_true_risk():
    base = dict(markers={}, female=1.0, age=45, smoking=0, first_degree=0, second_degree=0)
    r0 = synthetic_data.true_risk(**base)
    assert synthetic_data.true_risk(**{**base, "first_degree": 2}) > r0
    assert synthetic_data.true_risk(**{**base, "smoking": 2}) > r0


# ---------- quantum kernel ----------

def test_fidelity_kernel_is_a_valid_kernel():
    rng = np.random.default_rng(0)
    states = statevectors(rng.uniform(0, np.pi, size=(12, 4)))
    K = fidelity_kernel(states, states)
    assert np.allclose(np.diag(K), 1.0)
    assert np.allclose(K, K.T)
    assert K.min() >= 0 and K.max() <= 1 + 1e-9
    assert np.linalg.eigvalsh(K).min() > -1e-8  # positive semi-definite


# ---------- training ----------

def test_quick_training_beats_chance_for_every_model():
    models, metrics = train_models(synthetic_data.generate(n=600, seed=11), quick=True)
    assert set(models) == {"Logistic regression", "Random forest", "Quantum kernel SVM"}
    for name, result in metrics["models"].items():
        assert result["auc"] > 0.6, f"{name} AUC {result['auc']}"
        assert 0 <= result["brier"] <= 0.25


# ---------- prediction with the saved models ----------

@pytest.fixture(scope="module")
def saved_models():
    try:
        return predictor.load_models()
    except predictor.ModelsNotTrained:
        pytest.skip("models/ not trained; run `python -m ml.train`")


def test_saved_models_give_probabilities(saved_models):
    for p in predictor.predict_all(saved_models, _patient()).values():
        assert 0.0 <= p <= 1.0


def test_brca1_carrier_scores_higher_than_non_carrier_in_every_model(saved_models):
    low = predictor.predict_all(saved_models, _patient())
    high = predictor.predict_all(saved_models, _patient(**{"Genetic Markers": {"BRCA1": True}}))
    for name in low:
        assert high[name] > low[name], name


def test_explanation_adds_up_to_the_logistic_regression_prediction(saved_models):
    patient = _patient(**{"Genetic Markers": {"BRCA2": True}, "Family History": {"First-degree": 1}})
    contributions = predictor.explain(saved_models, patient)
    intercept = saved_models["Logistic regression"][-1].intercept_[0]
    log_odds = intercept + sum(r["log_odds"] for r in contributions)
    expected = predictor.predict_all(saved_models, patient)["Logistic regression"]
    assert np.isclose(1 / (1 + np.exp(-log_odds)), expected)


def test_saved_metrics_match_the_saved_models(saved_models):
    metrics = predictor.load_metrics()
    assert set(saved_models) <= set(metrics["models"])
    assert metrics["dataset"]["features"] == FEATURES


# ---------- rule-based score: family history ----------

def test_family_history_adds_capped_points_to_rule_based_score():
    base = quantum_engine.calculate_deterministic_risk(_patient())
    one = quantum_engine.calculate_deterministic_risk(_patient(**{"Family History": {"First-degree": 1}}))
    many = quantum_engine.calculate_deterministic_risk(
        _patient(**{"Family History": {"First-degree": 9, "Second-degree": 9}}))
    assert one - base == quantum_engine.FIRST_DEGREE_POINTS
    assert many - base == 2 * quantum_engine.FIRST_DEGREE_POINTS + 2 * quantum_engine.SECOND_DEGREE_POINTS


# ---------- bootstrap comparison ----------

def test_bootstrap_flags_a_real_gap_but_not_noise():
    from ml.train import bootstrap_auc

    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    good = y + rng.normal(0, 0.6, 400)         # strongly informative
    twin = y + rng.normal(0, 0.6, 400)         # different model, same quality
    weak = y + rng.normal(0, 3.0, 400)         # barely informative
    out = bootstrap_auc(y, {"good": good, "twin": twin, "weak": weak}, n_boot=500)
    assert out["reference"] in ("good", "twin")
    other_twin = "twin" if out["reference"] == "good" else "good"
    assert out["pairs"]["weak"]["significant"]
    assert not out["pairs"][other_twin]["significant"]
    lo, hi = out["auc_ci"]["weak"]
    assert lo < hi


def test_saved_metrics_include_bootstrap_intervals():
    metrics = predictor.load_metrics()
    assert all(len(m["auc_ci"]) == 2 for m in metrics["models"].values())
    assert metrics["comparison"]["reference"] in metrics["models"]
