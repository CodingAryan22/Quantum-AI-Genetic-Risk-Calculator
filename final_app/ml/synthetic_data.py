"""
Synthetic patient cohort for training and evaluating the risk models.

THIS IS SIMULATED DATA, NOT REAL PATIENTS. Real patient-level genetic data is
not publicly available, so each synthetic patient's *true* risk is computed
from published figures and stated assumptions, and their outcome is then
drawn at random from that risk. The models must learn the risk back from
noisy 0/1 outcomes, the same problem they would face on real data.

Outcome definition
------------------
    outcome = 1 if the patient is diagnosed with a hereditary-spectrum cancer
              (breast, ovarian, colorectal, prostate or Li-Fraumeni spectrum)
              within the next 20 years.

How the true risk is built
--------------------------
1. Lifetime risk to age 80 for each gene, by sex (published ranges, rounded):
     - no mutation: general-population lifetime risk of these cancers (SEER)
     - BRCA1 / BRCA2: NCI "BRCA Gene Changes" fact sheet (breast + ovarian
       for women; prostate + male breast for men)
     - APC: GeneReviews, close to 100% colorectal cancer in classic FAP
       without preventive surgery (lowered here because many have surgery)
     - TP53: GeneReviews, at least 90% (women) / 70% (men) for any cancer
   Several mutations combine as independent risks.
2. Modelling ASSUMPTIONS (not published effect sizes, chosen to be plausible):
     - each affected 1st-degree relative multiplies the hazard by 1.6 (max 3)
     - each affected 2nd-degree relative multiplies it by 1.2 (max 3)
     - current smoking x1.4, former smoking x1.15
3. The lifetime hazard is spread over age with a Weibull age-of-onset curve
   (carriers get cancer earlier: scale 55 years vs 72), and the 20-year risk
   is the share of that hazard falling between the current age and age + 20.

The cohort is "enriched" like a genetics-clinic referral population: mutation
carriers are far more common than the 1-in-400 seen in the general public, so
the models see enough carriers to learn from.

Run `python -m ml.synthetic_data` from the final_app folder to regenerate
data/synthetic_patients.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .schema import FEATURES, MARKERS

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_patients.csv"

# Lifetime risk (to age 80) of a hereditary-spectrum cancer: (female, male).
LIFETIME_RISK = {
    "none": (0.17, 0.15),
    "BRCA1": (0.80, 0.20),
    "BRCA2": (0.70, 0.35),
    "APC": (0.85, 0.85),
    "TP53": (0.90, 0.70),
}

# Share of patients carrying each mutation in the enriched cohort.
CARRIER_RATE = {"BRCA1": 0.07, "BRCA2": 0.07, "APC": 0.03, "TP53": 0.02}

RR_FIRST_DEGREE = 1.6
RR_SECOND_DEGREE = 1.2
RR_SMOKING = {0: 1.0, 1: 1.15, 2: 1.4}

ONSET_SHAPE = 4.0
ONSET_SCALE_CARRIER = 55.0
ONSET_SCALE_NONCARRIER = 72.0
HORIZON_YEARS = 20


def _onset_cdf(age, scale):
    """Weibull cumulative age-of-onset curve."""
    return 1.0 - np.exp(-((np.asarray(age, dtype=float) / scale) ** ONSET_SHAPE))


def true_risk(markers: dict, female: float, age: float, smoking: int,
              first_degree: int, second_degree: int) -> float:
    """20-year risk for one patient under the model described above."""
    sex = 0 if female >= 0.5 else 1
    survival = 1.0 - LIFETIME_RISK["none"][sex]
    carrier = False
    for m in MARKERS:
        if markers.get(m):
            survival *= 1.0 - LIFETIME_RISK[m][sex]
            carrier = True
    lifetime_hazard = -np.log(max(survival, 1e-6))

    lifetime_hazard *= RR_FIRST_DEGREE ** min(first_degree, 3)
    lifetime_hazard *= RR_SECOND_DEGREE ** min(second_degree, 3)
    lifetime_hazard *= RR_SMOKING[int(smoking)]

    scale = ONSET_SCALE_CARRIER if carrier else ONSET_SCALE_NONCARRIER
    # Hazard accumulated by each age, normalised so the full lifetime value is reached at 80.
    norm = _onset_cdf(80.0, scale)
    h_now = lifetime_hazard * _onset_cdf(age, scale) / norm
    h_later = lifetime_hazard * _onset_cdf(age + HORIZON_YEARS, scale) / norm
    return float(1.0 - np.exp(-(h_later - h_now)))


def generate(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Generates `n` synthetic patients. Same seed -> identical cohort."""
    rng = np.random.default_rng(seed)

    carriers = {m: rng.random(n) < CARRIER_RATE[m] for m in MARKERS}
    any_carrier = np.zeros(n, dtype=bool)
    for m in MARKERS:
        any_carrier |= carriers[m]

    female = (rng.random(n) < 0.55).astype(float)
    age = np.clip(rng.normal(48, 14, n), 18, 85).round()
    smoking = rng.choice([0, 1, 2], size=n, p=[0.60, 0.25, 0.15])
    # Carriers tend to have more affected relatives.
    first = np.clip(rng.poisson(np.where(any_carrier, 1.0, 0.35)), 0, 4)
    second = np.clip(rng.poisson(np.where(any_carrier, 1.3, 0.6)), 0, 5)

    df = pd.DataFrame({m: carriers[m].astype(int) for m in MARKERS})
    df["Female"] = female
    df["Age"] = age
    df["Smoking"] = smoking
    df["First-degree relatives"] = first
    df["Second-degree relatives"] = second

    df["True Risk"] = [
        true_risk({m: r[m] for m in MARKERS}, r["Female"], r["Age"], r["Smoking"],
                  r["First-degree relatives"], r["Second-degree relatives"])
        for _, r in df.iterrows()
    ]
    df["Outcome"] = (rng.random(n) < df["True Risk"]).astype(int)
    df.insert(0, "Patient_ID", [f"S{i:05d}" for i in range(1, n + 1)])
    return df[["Patient_ID"] + FEATURES + ["True Risk", "Outcome"]]


def main():
    df = generate()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.round({"True Risk": 4}).to_csv(DATA_PATH, index=False)
    print(f"Wrote {len(df)} patients to {DATA_PATH}")
    print(f"Outcome rate: {df['Outcome'].mean():.1%}  |  "
          f"carriers: {(df[MARKERS].sum(axis=1) > 0).mean():.1%}")


if __name__ == "__main__":
    main()
