"""Other hereditary genes (PALB2, CHEK2, Lynch genes...) now count in every calculation."""

import numpy as np
import pandas as pd
import pytest

import ai_synthesizer
import genes
import quantum_engine
from ml import predictor, synthetic_data
from ml.schema import FEATURES, patient_to_vector


def _patient(others=(), gender="Female", **overrides):
    patient = {
        "Name": "Test Patient", "Age": 45, "Gender": gender, "Smoking History": "Never Smoked",
        "Genetic Markers": {"BRCA1": False, "BRCA2": False, "APC": False, "TP53": False},
        "Family History": {"First-degree": 0, "Second-degree": 0},
        "Other Genetic Markers": list(others),
    }
    patient.update(overrides)
    return patient


def test_every_dropdown_gene_has_risk_figures():
    for gene, info in genes.OTHER_GENES.items():
        f, m = info["lifetime"]
        assert 0 < f < 1 and 0 < m < 1 and info["cancers"], gene


def test_known_genes_add_rule_points_and_unknown_ones_do_not():
    base = quantum_engine.calculate_deterministic_risk(_patient())
    palb2 = quantum_engine.calculate_deterministic_risk(_patient(["PALB2"]))
    typed = quantum_engine.calculate_deterministic_risk(_patient(["MADEUP1"]))
    assert palb2 == pytest.approx(base + genes.rule_points("PALB2"), abs=0.11)
    assert typed == base


def test_rule_points_follow_published_risk():
    # High-penetrance genes outweigh moderate ones, and BRCA1-level risk ~ BRCA1's 30 points.
    assert genes.rule_points("MSH2") > genes.rule_points("CHEK2") > genes.rule_points("BRIP1")
    assert 25 <= genes.RULE_POINTS_PER_RISK * 0.80 <= 30


def test_gene_names_are_matched_case_insensitively():
    assert genes.split_known(["palb2 ", "PALB2", "xyz1"]) == (["PALB2"], ["xyz1"])


def test_combined_risk_uses_sex_and_combines_independently():
    assert genes.combined_risk(["PALB2"], 1.0) == pytest.approx(0.55)
    assert genes.combined_risk(["PALB2"], 0.0) == pytest.approx(0.05)
    both = genes.combined_risk(["PALB2", "CHEK2"], 1.0)
    assert both == pytest.approx(1 - 0.45 * 0.72)
    assert genes.combined_risk(["MADEUP1"], 1.0) == 0.0


def test_feature_vector_carries_other_gene_risk():
    x = dict(zip(FEATURES, patient_to_vector(_patient(["MLH1"]))))
    assert x["Other gene risk"] == pytest.approx(0.70)


def test_true_risk_rises_with_other_gene_risk():
    args = ({}, 1.0, 45, 0, 0, 0)
    assert synthetic_data.true_risk(*args, other_risk=0.7) > 2 * synthetic_data.true_risk(*args)


def test_cohort_contains_other_gene_carriers_with_higher_outcomes():
    df = synthetic_data.generate(n=2000, seed=7)
    carriers = df["Other gene risk"] > 0
    assert 0.05 < carriers.mean() < 0.2
    assert df.loc[carriers, "True Risk"].mean() > df.loc[~carriers, "True Risk"].mean()


@pytest.fixture(scope="module")
def saved_models():
    try:
        return predictor.load_models()
    except predictor.ModelsNotTrained:
        pytest.skip("models/ not trained; run `python -m ml.train`")


@pytest.mark.parametrize("gene", ["MLH1", "PALB2", "STK11"])
def test_trained_models_score_other_gene_carriers_higher(saved_models, gene):
    low = predictor.predict_all(saved_models, _patient())
    high = predictor.predict_all(saved_models, _patient([gene]))
    for name in ("Logistic regression", "Random forest"):
        assert high[name] > low[name], (gene, name)


def test_summary_text_separates_scored_and_unscored_genes():
    table = pd.DataFrame([{"Simulated Mean": "30.0%", "90% Confidence Interval": "[25.0%, 35.0%]"}])
    text = ai_synthesizer.fallback_summary(_patient(["PALB2", "MADEUP1"]), table)
    assert "PALB2" in text and "included in your score" in text
    assert "MADEUP1" in text and "not part of the numeric score" in text
    prompt = ai_synthesizer.build_prompt(_patient(["PALB2", "MADEUP1"]), table)
    assert "included in the risk score" in prompt and "not included in the numeric" in prompt
