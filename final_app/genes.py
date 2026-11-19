"""
The "other" hereditary cancer genes (beyond BRCA1, BRCA2, APC and TP53) and
how much risk each one carries.

Lifetime risk to about age 80 of the gene's main cancers, by sex (female, male).
Rounded midpoints of published ranges, mainly GeneReviews and the NCCN
genetic/familial high-risk assessment guidelines:

    PALB2          breast ~50-55%, plus ovarian / pancreatic
    CHEK2          breast ~25-30% (c.1100delC), modest colorectal / prostate
    ATM            breast ~20-30%, pancreatic / prostate
    PTEN           Cowden syndrome: breast up to 85%, thyroid, endometrial, kidney
    CDH1           diffuse gastric ~35-40%, lobular breast ~40-55%
    STK11          Peutz-Jeghers syndrome: any cancer ~80-90%
    MLH1, MSH2     Lynch syndrome: colorectal ~40-50%, endometrial ~40-55%
    MSH6           Lynch: colorectal ~15-20%, endometrial ~40%
    PMS2           Lynch: colorectal ~10-15%, endometrial ~15-25%
    RAD51C/RAD51D  ovarian ~10-15%, breast ~20%
    BRIP1          ovarian ~5-6%
    MUTYH          assumed biallelic (MUTYH-associated polyposis): colorectal ~70%.
                   A single (heterozygous) MUTYH change raises risk only slightly;
                   the form cannot tell the two apart.

These are the same kind of published figures the synthetic cohort already
uses for the four main genes (see ml/synthetic_data.py).
"""

import numpy as np

OTHER_GENES = {
    "PALB2": {"cancers": "Breast/Pancreatic Cancer Risk", "lifetime": (0.55, 0.05)},
    "CHEK2": {"cancers": "Breast/Colorectal Cancer Risk", "lifetime": (0.28, 0.10)},
    "ATM": {"cancers": "Breast/Pancreatic Cancer Risk", "lifetime": (0.25, 0.08)},
    "PTEN": {"cancers": "Cowden Syndrome: Breast/Thyroid/Uterine", "lifetime": (0.85, 0.40)},
    "CDH1": {"cancers": "Diffuse Gastric/Lobular Breast Cancer Risk", "lifetime": (0.55, 0.40)},
    "STK11": {"cancers": "Peutz-Jeghers Syndrome: GI/Pancreatic/Breast", "lifetime": (0.85, 0.80)},
    "MLH1": {"cancers": "Lynch Syndrome: Colorectal/Endometrial", "lifetime": (0.70, 0.50)},
    "MSH2": {"cancers": "Lynch Syndrome: Colorectal/Endometrial", "lifetime": (0.75, 0.55)},
    "MSH6": {"cancers": "Lynch Syndrome: Colorectal/Endometrial", "lifetime": (0.45, 0.20)},
    "PMS2": {"cancers": "Lynch Syndrome: Colorectal/Endometrial", "lifetime": (0.25, 0.12)},
    "RAD51C": {"cancers": "Ovarian/Breast Cancer Risk", "lifetime": (0.30, 0.03)},
    "RAD51D": {"cancers": "Ovarian/Breast Cancer Risk", "lifetime": (0.30, 0.03)},
    "BRIP1": {"cancers": "Ovarian Cancer Risk", "lifetime": (0.06, 0.02)},
    "MUTYH": {"cancers": "MUTYH Polyposis: Colorectal Cancer Risk", "lifetime": (0.70, 0.70)},
}

# Rule-score points per unit of lifetime risk. Matches the existing hand weights:
# BRCA1 (80% lifetime) -> 28 points vs its 30, BRCA2 (70%) -> 24.5 vs 25.
RULE_POINTS_PER_RISK = 35.0

# A gene with at least this lifetime risk counts as high-penetrance: cancers
# appear earlier, like the four main genes (earlier age-of-onset curve).
HIGH_PENETRANCE = 0.40


def canonical(name) -> str | None:
    """'palb2 ' -> 'PALB2'; None if it isn't one of the known other genes."""
    key = str(name or "").strip().upper()
    return key if key in OTHER_GENES else None


def split_known(names) -> tuple[list[str], list[str]]:
    """(known genes, in canonical spelling; genes the app has no risk figures for)."""
    known, unknown = [], []
    for n in names or []:
        c = canonical(n)
        if c and c not in known:
            known.append(c)
        elif not c and str(n).strip():
            unknown.append(str(n).strip())
    return known, unknown


def rule_points(gene: str) -> float:
    """Rule-score points for one known gene (sex-blind, like the four main genes)."""
    return round(RULE_POINTS_PER_RISK * max(OTHER_GENES[gene]["lifetime"]), 1)


def lifetime(gene: str, female: float) -> float:
    """Lifetime risk for the patient's sex; female=0.5 (other / not given) averages the two."""
    f, m = OTHER_GENES[gene]["lifetime"]
    return float(female) * f + (1.0 - float(female)) * m


def combined_risk(names, female: float) -> float:
    """
    Combined lifetime risk from all of a patient's known other genes, treating
    them as independent: 1 - product(1 - risk). 0 when there are none.
    This single number is the ML models' "Other gene risk" feature.
    """
    known, _ = split_known(names)
    survival = np.prod([1.0 - lifetime(g, female) for g in known]) if known else 1.0
    return float(1.0 - survival)
