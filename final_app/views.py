"""
The app's pages. final_app.py builds the navigation from pages() and runs the
selected one; each page is a plain function.

    Home              hero + published research figures
    New assessment    the patient form; Generate runs everything and opens Results
    Results           patient summary bar, then Overview / Models / Details tabs
    Patient records   every saved assessment (MongoDB), grouped by patient
    Model comparison  classical vs quantum metrics
    About             method, data, privacy and disclaimer
"""

import re
from datetime import datetime

import streamlit as st

import ai_synthesizer
import data_manager
import pdf_builder
import quantum_engine
import storage
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


@st.cache_resource(show_spinner="Connecting to the database…")
def get_store():
    """(store, error): MongoDB if reachable, otherwise the local JSON file."""
    return storage.connect()


def save_assessment(patient_data: dict, results: dict):
    """Saves one assessment; a database problem never blocks the results."""
    store, _ = get_store()
    tier, _ = ui_modules.risk_level(results["mean"])
    try:
        store.save(storage.build_record(patient_data, results, tier))
        st.session_state["_saved_to"] = store.name
    except Exception as exc:
        st.session_state["_save_error"] = f"Could not save this assessment: {exc}"


def start_over():
    """Clears the form (back to step 1) and the current result. Database untouched."""
    data_manager.clear_form()
    st.session_state.pop(RESULTS_KEY, None)
    st.session_state["_toast"] = "Form and current result cleared."


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
    head_col, reset_col = st.columns([4, 1], vertical_alignment="center")
    with head_col:
        ui_modules.page_header(
            "New assessment",
            "Three short steps. Next unlocks once the current step is complete.",
        )
    with reset_col:
        with st.container(key="start-over"), st.popover(
            "Start over", icon=":material/restart_alt:", key="start-over-menu",
        ):
            st.markdown("Clear every field and the current result, and go back to step 1? "
                        "Saved patient records are not affected.")
            st.button("Yes, start over", type="primary", width="stretch",
                      on_click=start_over, key="start-over-confirm")
    with ui_modules.card("form"):
        patient_data, generate = data_manager.render_collection_form()

    # Generate is disabled until every step is valid; check again to be safe.
    if generate and not data_manager.validate_patient(patient_data):
        with st.spinner("Running the models and writing the AI summary…"):
            results = run_analysis(patient_data)
            st.session_state[RESULTS_KEY] = results
            save_assessment(patient_data, results)
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

    if saved_to := st.session_state.pop("_saved_to", None):
        st.toast(f"Saved to patient records ({saved_to}).", icon="✅")
    if save_error := st.session_state.pop("_save_error", None):
        st.warning(save_error, icon=":material/warning:")

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


def _patient_actions_menu(store, p: dict, i: int):
    """The "⋮" menu on a patient's history: downloads, then delete with confirmation."""
    fname = storage.safe_filename(p["name"])
    key = p["key"]
    # The keyed container lets the theme CSS shape the button into a small "⋮" square.
    # Keys use the card index, since patient names can contain spaces.
    with st.container(key=f"patient-actions-{i}"), st.popover(
        "", icon=":material/more_vert:", key=f"patient-actions-menu-{i}",
    ):
        st.download_button(
            "Download PDF report", icon=":material/picture_as_pdf:", type="tertiary",
            data=pdf_builder.generate_patient_history_pdf(p),
            file_name=f"{fname}_history.pdf", mime="application/pdf",
            width="stretch", on_click="ignore", key=f"pdf-{key}",
        )
        st.download_button(
            "Download CSV", icon=":material/table:", type="tertiary",
            data=storage.records_to_csv(p["history"]),
            file_name=f"{fname}_history.csv", mime="text/csv",
            width="stretch", on_click="ignore", key=f"csv-{key}",
        )
        st.divider()
        n = p["assessments"]
        what = "this record" if n == 1 else f"all {n} records"
        sure = st.checkbox(f"Yes, delete {what} (can't be undone)", key=f"del-confirm-{key}")
        if st.button("Delete records", icon=":material/delete:", width="stretch",
                     disabled=not sure, key=f"del-{key}"):
            removed = store.delete_patient(key)
            st.session_state.pop(f"del-confirm-{key}", None)
            st.toast(f"Deleted {removed} record(s) for {p['name']}.", icon="🗑️")
            st.rerun()


def _delete_all_menu(store, patients: list):
    """Top-right "⋮" menu on Patient records: delete every saved record after typing DELETE."""
    total = sum(p["assessments"] for p in patients)
    with st.container(key="patient-actions-all"), st.popover(
        "", icon=":material/more_vert:", key="records-menu", disabled=not patients,
    ):
        st.markdown(f"**Delete all records**  \nPermanently deletes all {total} saved assessments "
                    f"for {len(patients)} patients from {store.name}. Export them first if you "
                    "might need them. This cannot be undone.")
        typed = st.text_input("Type DELETE to confirm", key="delete-all-confirm",
                              placeholder="DELETE")
        st.button("Delete all records", icon=":material/delete_forever:", width="stretch",
                  disabled=typed.strip() != "DELETE", key="delete-all",
                  on_click=_delete_all, args=(store,))


def _delete_all(store):
    removed = store.delete_all()
    st.session_state["delete-all-confirm"] = ""
    st.session_state["_toast"] = f"Deleted all {removed} saved assessments."


def patient_records():
    store, error = get_store()
    where = (f"MongoDB · {store.location}" if store.name == "MongoDB" else "Local file")
    try:
        patients = storage.group_patients(store.all_records())
        read_error = None
    except Exception as exc:
        patients, read_error = [], exc

    # Header: title on the left; "Export all" and a "⋮" menu (delete all) on the top right.
    head_col, export_col, menu_col = st.columns([2.4, 1, 0.22], vertical_alignment="center")
    with head_col:
        ui_modules.page_header(
            "Patient records",
            "Every saved assessment, grouped by patient name.",
            ui_modules.badge(where, "good" if store.name == "MongoDB" else "warn", dot=True),
        )
    with export_col:
        st.download_button(
            "Export all (CSV)", icon=":material/download:",
            data=storage.records_to_csv([r for p in patients for r in p["history"]]),
            file_name=f"riskpredict_all_patients_{datetime.now():%Y%m%d}.csv",
            mime="text/csv", width="stretch", on_click="ignore", key="export-all",
            disabled=not patients,
            help=f"Every saved assessment for all {len(patients)} patients, one row per assessment.",
        )
    with menu_col:
        _delete_all_menu(store, patients)
    if error:
        ui_modules.hint(
            "MongoDB not reachable, using a local file instead.",
            f"Start MongoDB or set MONGODB_URI, then reload. ({error})",
        )

    if read_error:
        st.error(f"Could not read records: {read_error}", icon=":material/error:")
        return

    if not patients:
        ui_modules.hint("No records yet.", "Each analysis you generate is saved here automatically.")
        if st.button("Start new assessment", type="primary", icon=":material/add:"):
            st.switch_page(pages()["new"])
        return

    ui_modules.records_stats(patients)
    _gap(1)

    search_col, tier_col = st.columns([1.6, 1.4], vertical_alignment="bottom")
    with search_col:
        query = st.text_input("Search", placeholder="Search by name, mutation or disease",
                              key="records-search", label_visibility="collapsed")
    with tier_col:
        tier = st.segmented_control("Tier", ["All", "Low", "Moderate", "High"], default="All",
                                    key="records-tier", label_visibility="collapsed")
    q = (query or "").strip().lower()
    shown = [
        p for p in patients
        if (not q or q in p["name"].lower()
            or any(q in m.lower() for m in p["markers"])
            or any(q in d.lower() for d in p["diseases"]))
        and (tier in (None, "All") or p["latest_tier"].startswith(tier))
    ]

    with ui_modules.card("records"):
        ui_modules.card_header(
            f"Patients ({len(shown)} of {len(patients)})",
            "Latest result per patient. Linked diseases come from the patient's mutations.",
            right_html="",
        )
        if shown:
            ui_modules.records_table(shown)
        else:
            st.caption("No patients match this search.")

    if not shown:
        return

    # Every matching patient's full history, one card each. The search box and
    # tier filter above narrow this list along with the table.
    _gap()
    ui_modules.section_title(
        f"Patient histories ({len(shown)})",
        "Search above by name, mutation or disease to find a patient.",
    )
    for i, p in enumerate(shown):
        _patient_history_card(store, p, i)
        _gap(0.5)

    ui_modules.footer_note()


def _patient_history_card(store, p: dict, i: int):
    """One patient's history: header with tier and ⋮ menu, chart, table, summary."""
    with ui_modules.card(f"history-{i}"):
        title_col, badge_col, menu_col = st.columns([6, 1.4, 0.45], vertical_alignment="top")
        with title_col:
            ui_modules.card_header(
                f"{p['name']} · {p['assessments']} assessment{'s' if p['assessments'] != 1 else ''}",
                "Risk over time. The shaded band is each assessment's 90% range."
                if p["assessments"] > 1 else "Every saved assessment, newest first.",
                right_html="",
            )
        with badge_col:
            st.markdown(
                '<div style="text-align:right;margin-top:-0.1rem">'
                + ui_modules.badge(p["latest_tier"], ui_modules.risk_level(p["latest_mean"])[1], dot=True)
                + "</div>",
                unsafe_allow_html=True,
            )
        with menu_col:
            _patient_actions_menu(store, p, i)

        if p["assessments"] > 1:
            ui_modules.history_chart(p["history"], key=f"history-chart-{i}")
        ui_modules.history_table(p["history"])

        latest = p["history"][0]
        if latest.get("summary"):
            with st.expander("Latest AI clinical summary"):
                st.markdown(latest["summary"])
        if latest["patient"].get("notes"):
            with st.expander("Clinical notes"):
                st.write(latest["patient"]["notes"])


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
        "records": st.Page(patient_records, title="Patient records", icon=":material/groups:",
                           url_path="patient-records"),
        "models": st.Page(model_comparison, title="Model comparison", icon=":material/insights:",
                          url_path="model-comparison"),
        "about": st.Page(about, title="About & method", icon=":material/info:", url_path="about"),
    }
