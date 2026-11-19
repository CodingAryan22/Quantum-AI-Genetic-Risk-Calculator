import re

import streamlit as st

# Import our custom modules
import ui_modules
import data_manager
import quantum_engine
import ai_synthesizer
import pdf_builder

st.set_page_config(
    page_title="RiskPredict · Genetic Disease Risk",
    page_icon="🧬",
    layout="wide",
    # "auto" = open on desktop, collapsed on phones (where it would cover the page).
    initial_sidebar_state="auto",
)

RESULTS_KEY = "_analysis_results"

# ==========================================
# 1. SIDEBAR
# ==========================================
with st.sidebar:
    ui_modules.sidebar_brand()

    ui_modules.sidebar_label("Workspace")
    if st.button("Clear form", icon=":material/restart_alt:", key="btn-clear-form", width="stretch"):
        data_manager.clear_form()
        st.session_state.pop(RESULTS_KEY, None)
        st.session_state["form_cleared"] = True
        st.rerun()
    if st.button("Clear all records", icon=":material/delete:", key="btn-clear-all", width="stretch"):
        data_manager.clear_session_state()
        st.session_state["records_cleared"] = True
        st.rerun()

    ui_modules.sidebar_label("Appearance")
    dark_mode = st.toggle("Dark mode", value=False, key="dark_mode")

    ui_modules.sidebar_promo()

ui_modules.apply_theme(dark_mode)

if st.session_state.pop("form_cleared", False):
    st.toast("Patient entry form cleared.", icon="✨")
if st.session_state.pop("records_cleared", False):
    st.toast("All records cleared.", icon="✨")

# ==========================================
# 2. PAGE HEADER
# ==========================================
results = st.session_state.get(RESULTS_KEY)
header_badge = ""
if results:
    label, kind = ui_modules.risk_level(results["mean"])
    header_badge = ui_modules.badge(label, kind, dot=True)

if results:
    ui_modules.page_header(
        "Patient risk overview",
        "Hybrid Monte Carlo simulation and AI synthesis for hereditary disease risk.",
        header_badge,
    )
else:
    ui_modules.landing_hero()
    ui_modules.feature_tiles()

# ==========================================
# 3. DATA COLLECTION FORM
# ==========================================
with ui_modules.card("form"):
    ui_modules.card_header(
        "Patient details",
        "Enter clinical and demographic details to generate a personalized assessment.",
        right_html="",
    )
    patient_data = data_manager.render_collection_form()

    _, btn_col = st.columns([3, 1.3])
    with btn_col:
        run_analysis = st.button("Generate risk analysis", type="primary", width="stretch")

    problems = data_manager.validate_patient(patient_data) if run_analysis else []
    if problems:
        st.error(
            "**Please fix the following before generating the analysis:**\n\n"
            + "\n".join(f"- {p}" for p in problems),
            icon=":material/error:",
        )

# ==========================================
# 4. PROCESSING
# ==========================================
if run_analysis and not problems:
    with st.spinner("Running simulation and generating AI summary…"):
        risk_table, risk_plot = quantum_engine.run_simulation(patient_data)
        ai_summary = ai_synthesizer.generate_report(patient_data, risk_table)
        pdf_bytes = pdf_builder.generate_pdf(patient_data, risk_table, ai_summary)

    row = risk_table.iloc[0]
    ci_bounds = [float(v) for v in re.findall(r"[\d.]+", row["90% Confidence Interval"])]
    st.session_state[RESULTS_KEY] = {
        "patient": patient_data,
        "plot": risk_plot,
        "summary": ai_summary,
        "pdf": pdf_bytes,
        "base_str": row["Base Deterministic Risk"],
        "base": float(row["Base Deterministic Risk"].rstrip("%")),
        "mean": float(row["Simulated Mean"].rstrip("%")),
        "ci_str": row["90% Confidence Interval"],
        "ci": (ci_bounds[0], ci_bounds[1]),
    }
    st.rerun()

# ==========================================
# 5. DASHBOARD
# ==========================================
if not results:
    ui_modules.empty_results()
    ui_modules.evidence_section()
else:
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    ui_modules.risk_banner(results["mean"])
    ui_modules.kpi_tiles(results["base_str"], results["mean"], results["ci"], results["base"])
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    left, right = st.columns([1, 1.6], gap="medium")
    with left:
        with ui_modules.card("donut"):
            ui_modules.card_header("Risk tier breakdown", "Share of simulation runs in each tier")
            st.plotly_chart(
                ui_modules.tier_donut(results["plot"]),
                width="stretch",
                config=ui_modules.chart_config(),
                theme=None,
            )
    with right:
        with ui_modules.card("dist"):
            ui_modules.card_header(
                "Simulated risk distribution",
                "Spread of 1,500 Monte Carlo runs. Shaded band is the 90% interval.",
            )
            st.plotly_chart(
                ui_modules.distribution_area(results["plot"], results["mean"], *results["ci"]),
                width="stretch",
                config=ui_modules.chart_config(),
                theme=None,
            )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    with ui_modules.card("factors"):
        ui_modules.card_header(
            "Risk factors",
            "What contributes to this patient's baseline score.",
            right_html="",
        )
        ui_modules.factor_table(results["patient"])

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    with ui_modules.card("summary"):
        head_col, btn_col = st.columns([3, 1])
        with head_col:
            ui_modules.card_header(
                "AI clinical summary",
                "Plain-language interpretation of the results.",
                right_html="",
            )
        with btn_col:
            st.download_button(
                label="⬇  Export PDF",
                data=results["pdf"],
                file_name=f"Risk_Report_{results['patient'].get('Name') or 'Patient'}.pdf",
                mime="application/pdf",
                width="stretch",
                on_click="ignore",
            )
        st.markdown(results["summary"])

    st.markdown(
        '<div class="footer-note">This tool provides an educational risk estimate and does '
        "not replace professional genetic counseling or clinical diagnosis.</div>",
        unsafe_allow_html=True,
    )
