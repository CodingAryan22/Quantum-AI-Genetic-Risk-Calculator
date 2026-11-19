"""
The app's pages. final_app.py builds the navigation from pages() and runs the
selected one; each page is a plain function.

    Home              hero + published research figures
    New assessment    the patient form; Generate runs everything and opens Results
    Results           patient summary bar, then Overview / Models / Details tabs
    Model comparison  classical vs quantum metrics
    About             method, data, privacy and disclaimer
"""

import re

import streamlit as st

import ai_synthesizer
import data_manager
import pdf_builder
import quantum_engine
import ui_modules
from ml import predictor, synthetic_data
from ml.schema import MARKERS, patient_to_vector

RESULTS_KEY = "_analysis_results"


# ==========================================
# SHARED HELPERS
# ==========================================
@st.cache_resource(show_spinner="Loading ML models…")
def get_models():
    """Trained models, loaded once per server. None if `python -m ml.train` hasn't been run."""
    try:
        return predictor.load_models()
    except predictor.ModelsNotTrained:
        return None


@st.cache_data
def get_metrics():
    return predictor.load_metrics()


def reference_risk(patient_data: dict) -> float:
    """The formula that generated the training data, applied to this patient."""
    x = dict(zip(predictor.FEATURES, patient_to_vector(patient_data)))
    return synthetic_data.true_risk(
        {m: x[m] >= 0.5 for m in MARKERS}, x["Female"], x["Age"], int(x["Smoking"]),
        int(x["First-degree relatives"]), int(x["Second-degree relatives"]),
    )


def run_analysis(patient_data: dict) -> dict:
    """Runs every model and the AI summary for one patient; returns the results dict."""
    models = get_models()
    risk_table, risk_plot = quantum_engine.run_simulation(patient_data)
    model_preds, explanation = None, None
    if models:
        model_preds = predictor.predict_all(models, patient_data)
        explanation = predictor.explain(models, patient_data)
    ai_summary = ai_synthesizer.generate_report(patient_data, risk_table, model_preds)
    pdf_bytes = pdf_builder.generate_pdf(patient_data, risk_table, ai_summary, model_preds)

    row = risk_table.iloc[0]
    ci_low, ci_high = (float(v) for v in re.findall(r"[\d.]+", row["90% Confidence Interval"]))
    return {
        "patient": patient_data,
        "plot": risk_plot,
        "summary": ai_summary,
        "pdf": pdf_bytes,
        "base_str": row["Base Deterministic Risk"],
        "base": float(row["Base Deterministic Risk"].rstrip("%")),
        "mean": float(row["Simulated Mean"].rstrip("%")),
        "ci": (ci_low, ci_high),
        "models": model_preds,
        "explanation": explanation,
        "reference": reference_risk(patient_data),
    }


def _gap(rem: float = 0.5):
    st.markdown(f"<div style='height:{rem}rem'></div>", unsafe_allow_html=True)


# ==========================================
# PAGES
# ==========================================
def home():
    ui_modules.landing_hero()
    left, right, _ = st.columns([1.5, 1.2, 3])
    with left:
        if st.button("Start new assessment", type="primary", icon=":material/add:", width="stretch"):
            st.switch_page(pages()["new"])
    with right:
        if st.button("See the models", icon=":material/insights:", width="stretch"):
            st.switch_page(pages()["models"])
    _gap(1.5)
    ui_modules.evidence_section()


def new_assessment():
    ui_modules.page_header(
        "New assessment",
        "Enter the patient's details. Required fields are marked *.",
    )
    with ui_modules.card("form"):
        patient_data = data_manager.render_collection_form()
        _, btn_col = st.columns([3, 1.3])
        with btn_col:
            generate = st.button("Generate risk analysis", type="primary", width="stretch")

        problems = data_manager.validate_patient(patient_data) if generate else []
        if problems:
            st.error(
                "**Please fix the following before generating the analysis:**\n\n"
                + "\n".join(f"- {p}" for p in problems),
                icon=":material/error:",
            )

    if generate and not problems:
        with st.spinner("Running the models and writing the AI summary…"):
            st.session_state[RESULTS_KEY] = run_analysis(patient_data)
        st.switch_page(pages()["results"])


def results():
    res = st.session_state.get(RESULTS_KEY)
    if not res:
        ui_modules.page_header("Results", "The latest assessment appears here.")
        ui_modules.empty_results()
        _, mid, _ = st.columns([1.2, 1, 1.2])
        with mid:
            if st.button("Start new assessment", type="primary", icon=":material/add:", width="stretch"):
                st.switch_page(pages()["new"])
        return

    patient = res["patient"]
    label, kind = ui_modules.risk_level(res["mean"])

    # --- Patient summary bar: who this is, plus Edit / Export ---
    info, edit_col, pdf_col = st.columns([4, 1, 1.2], vertical_alignment="center")
    with info:
        ui_modules.patient_summary(patient, ui_modules.badge(label, kind, dot=True))
    with edit_col:
        if st.button("Edit", icon=":material/edit:", width="stretch"):
            st.switch_page(pages()["new"])
    with pdf_col:
        st.download_button(
            "Export PDF",
            icon=":material/download:",
            data=res["pdf"],
            file_name=f"Risk_Report_{patient.get('Name') or 'Patient'}.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch",
            on_click="ignore",
        )
    _gap(0.25)

    overview, models_tab, details = st.tabs(["Overview", "Models", "Details"])

    with overview:
        ui_modules.risk_banner(res["mean"])
        ui_modules.headline_card(res["mean"], *res["ci"], res.get("models"))
        _gap()
        with ui_modules.card("summary"):
            ui_modules.card_header(
                "AI clinical summary",
                "Plain-language interpretation, written from de-identified data.",
                right_html="",
            )
            st.markdown(res["summary"])

    with models_tab:
        models = get_models()
        if res.get("models") and models:
            m_left, m_right = st.columns([1.35, 1], gap="medium")
            with m_left:
                with ui_modules.card("models"):
                    ui_modules.card_header(
                        "Machine-learning predictions",
                        "20-year risk from models trained on 2,000 synthetic patients.",
                        right_html=ui_modules.badge("Synthetic training data", "warn", dot=True),
                    )
                    ui_modules.model_predictions(res["models"], res.get("reference"))
            with m_right:
                with ui_modules.card("explain"):
                    ui_modules.card_header(
                        "Why this risk?",
                        "What pushes this patient's risk up or down (logistic regression).",
                        right_html="",
                    )
                    ui_modules.explanation_chart(
                        res["explanation"],
                        predictor.average_risk(models),
                        res["models"]["Logistic regression"],
                    )
        else:
            ui_modules.models_missing_notice()

    with details:
        ui_modules.kpi_tiles(res["base_str"], res["mean"], res["ci"], res["base"])
        _gap(1)
        with ui_modules.card("dist"):
            ui_modules.card_header(
                "Simulated risk distribution",
                "Spread of 1,500 Monte Carlo runs. Shaded band is the 90% interval.",
                right_html="",
            )
            st.plotly_chart(
                ui_modules.distribution_area(res["plot"], res["mean"], *res["ci"]),
                width="stretch", config=ui_modules.chart_config(), theme=None,
            )
        _gap()
        with ui_modules.card("factors"):
            ui_modules.card_header(
                "Risk factors",
                "Points each factor adds to the rule-based baseline score.",
                right_html="",
            )
            ui_modules.factor_table(patient)

    ui_modules.footer_note()


def model_comparison():
    metrics = get_metrics()
    if metrics:
        ui_modules.model_comparison(metrics)
    else:
        ui_modules.models_missing_notice()


def about():
    ui_modules.about_page(get_metrics())


def pages() -> dict:
    """
    The app's pages, keyed by short name. Built fresh on every run (the usual
    Streamlit pattern): st.Page objects made outside a running app don't work.
    """
    return {
        "home": st.Page(home, title="Home", icon=":material/home:", url_path="home", default=True),
        "new": st.Page(new_assessment, title="New assessment", icon=":material/add_circle:",
                       url_path="new-assessment"),
        "results": st.Page(results, title="Results", icon=":material/monitoring:",
                           url_path="results"),
        "models": st.Page(model_comparison, title="Model comparison", icon=":material/insights:",
                          url_path="model-comparison"),
        "about": st.Page(about, title="About & method", icon=":material/info:", url_path="about"),
    }
