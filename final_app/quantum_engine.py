import numpy as np
import pandas as pd
import plotly.graph_objects as go

try:
    # `streamlit run final_app.py` loads the app's modules as top-level modules.
    from features import normalize_marker_status as _normalize_marker_status
    import genes
except ModuleNotFoundError:
    # Imported as `final_app.quantum_engine` (e.g. from the tests).
    from .features import normalize_marker_status as _normalize_marker_status
    from . import genes


# Points per affected relative, counting at most FAMILY_MAX_COUNTED of each kind.
FIRST_DEGREE_POINTS = 8.0   # parents, siblings, children
SECOND_DEGREE_POINTS = 3.0  # grandparents, aunts, uncles, nieces, nephews
FAMILY_MAX_COUNTED = 2


def family_history_points(patient_data: dict) -> float:
    """Rule-based points for relatives diagnosed with cancer."""
    family = patient_data.get("Family History", {}) or {}
    first = min(int(family.get("First-degree", 0) or 0), FAMILY_MAX_COUNTED)
    second = min(int(family.get("Second-degree", 0) or 0), FAMILY_MAX_COUNTED)
    return first * FIRST_DEGREE_POINTS + second * SECOND_DEGREE_POINTS


def calculate_deterministic_risk(patient_data: dict) -> float:
    """
    Rule-based (hand-weighted) risk score in %: genes (the four main ones plus
    other known genes from genes.py), age, smoking and family history. Not trained on data; the ML models in ml/ are compared against it.
    """
    base_risk = 5.0

    genetics = patient_data.get("Genetic Markers", {})
    marker_weights = {
        "BRCA1": 30.0,
        "BRCA2": 25.0,
        "APC": 20.0,
        "TP53": 35.0,
    }

    for marker_name, weight in marker_weights.items():
        status = _normalize_marker_status(genetics.get(marker_name))
        if status == "Positive":
            base_risk += weight
        elif status == "Inconclusive":
            base_risk += max(weight * 0.12, 2.0)

    # Other reported genes with published risk figures (see genes.py). Genes the
    # app has no figures for are recorded but add nothing.
    known_other, _ = genes.split_known(patient_data.get("Other Genetic Markers"))
    for gene in known_other:
        base_risk += genes.rule_points(gene)
    # The form sends None when Age is left blank, so fall back to 0.
    age = patient_data.get("Age") or 0
    if isinstance(age, str):
        try:
            age = float(age)
        except ValueError:
            age = 0

    # Check the older band first; otherwise "age > 50" swallows every 70+ patient.
    if age > 70:
        base_risk += 8.0
    elif age > 50:
        base_risk += 5.0

    smoking_history = patient_data.get("Smoking History", "Never Smoked")
    if smoking_history == "Current Smoker":
        base_risk += 10.0
    elif smoking_history == "Former Smoker":
        base_risk += 3.0

    base_risk += family_history_points(patient_data)

    final_risk = min(max(base_risk, 5.0), 95.0)
    return round(final_risk, 1)


def run_simulation(patient_data: dict, iterations: int = 1500, seed: int | None = None):
    """
    Monte Carlo uncertainty simulation around the rule-based baseline
    and converts the simulation density into a 2D Heatmap Matrix.
    """
    base_risk = calculate_deterministic_risk(patient_data)

    # Sample from a Beta distribution with mean = baseline and a 4.5-point
    # standard deviation. Unlike a clipped normal, a Beta stays inside 0-100%
    # on its own, so low-risk patients don't get a fake pile-up at exactly 0%.
    sigma = 4.5
    rng = np.random.default_rng(seed)
    m = base_risk / 100.0
    v = (sigma / 100.0) ** 2
    concentration = m * (1.0 - m) / v - 1.0
    simulated_distribution = 100.0 * rng.beta(
        m * concentration, (1.0 - m) * concentration, size=iterations
    )

    simulated_mean = round(float(np.mean(simulated_distribution)), 1)
    ci_lower = round(float(np.percentile(simulated_distribution, 5)), 1)
    ci_upper = round(float(np.percentile(simulated_distribution, 95)), 1)

    risk_table = pd.DataFrame([{
        "Base Deterministic Risk": f"{base_risk}%",
        "Simulated Mean": f"{simulated_mean}%",
        "90% Confidence Interval": f"[{ci_lower}%, {ci_upper}%]"
    }])

    # 1. Discretize Monte Carlo output into 20 Numerical Risk Score Bins (0% - 100%)
    num_bins = 20
    x_bins = np.linspace(0, 100, num_bins + 1)
    x_centers = (x_bins[:-1] + x_bins[1:]) / 2

    counts, _ = np.histogram(simulated_distribution, bins=x_bins)
    density = (counts / iterations) * 100  # Probability percentage per bin

    # 2. Define Clinical Stratification Rows (Y-axis)
    y_categories = ["High Risk (≥50%)", "Moderate Risk (20-50%)", "Low Risk (<20%)"]

    # 3. Construct 2D Numerical Matrix (3 x 20)
    z_matrix = np.zeros((3, num_bins))

    for i in range(num_bins):
        center = x_centers[i]
        bin_density = density[i]
        if center >= 50.0:
            z_matrix[0, i] = bin_density  # High Risk Tier Row
        elif center >= 20.0:
            z_matrix[1, i] = bin_density  # Moderate Risk Tier Row
        else:
            z_matrix[2, i] = bin_density  # Low Risk Tier Row

    # 4. Render 2D Heatmap using Plotly
    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=z_matrix,
        x=x_centers,  # Numerical floats allow add_vline math to succeed
        y=y_categories,
        colorscale=[
            [0.0, "#0f172a"],     # Dark slate for 0 probability density
            [0.15, "#0d9488"],    # Teal for low probability density
            [0.55, "#d97706"],    # Amber for moderate probability density
            [1.0, "#e11d48"]      # Red for high probability density concentration
        ],
        colorbar=dict(title="Density (%)", len=0.9),
        hovertemplate="Risk Range: %{x:.1f}%<br>Tier: %{y}<br>Probability Concentration: %{z:.1f}%<extra></extra>"
    ))

    # Add vertical reference marker for Simulated Mean Score
    fig.add_vline(
        x=simulated_mean,
        line_dash="dash",
        line_color="#ffffff",
        line_width=2,
        annotation_text=f"Mean ({simulated_mean}%)",
        annotation_position="top right",
        annotation_font_color="#ffffff"
    )

    fig.update_layout(
        title="<b>Monte Carlo Uncertainty Simulation (2D Risk Matrix Heatmap)</b>",
        xaxis=dict(
            title="Predicted Risk Score (%) Bins",
            ticksuffix="%",
            range=[0, 100]
        ),
        yaxis=dict(title="Clinical Risk Stratification"),
        margin=dict(l=20, r=20, t=50, b=20),
        template="plotly_white",
        height=340
    )

    return risk_table, fig