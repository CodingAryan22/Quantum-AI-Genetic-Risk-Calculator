import streamlit as st
import ui_modules

# Session key that holds the current "form generation" number. Every widget in
# the patient entry form derives its Streamlit key from this value. When the
# form is cleared we bump the generation, which gives every widget a brand-new
# key and therefore a guaranteed clean remount with default values. This is the
# most reliable way to truly reset widget state in Streamlit.
_RESET_KEY = "_form_generation"

# The plain field names used to build widget keys. Each becomes "{name}_{gen}".
FORM_FIELDS = [
    "name",
    "age",
    "gender",
    "height",
    "weight",
    "blood_group",
    "ancestry",
    "smoking",
    "brca1",
    "brca2",
    "apc",
    "tp53",
    "other_markers",
    "lab_report",
    "additional_details",
]

# Suggestions for the "Other mutations" box. Users can also type anything else.
SUGGESTED_MARKERS = [
    "PALB2",
    "CHEK2",
    "ATM",
    "PTEN",
    "CDH1",
    "STK11",
    "MLH1",
    "MSH2",
    "MSH6",
    "PMS2",
    "RAD51C",
    "RAD51D",
    "BRIP1",
    "MUTYH",
]


def _generation() -> int:
    """Returns the current form generation (used to build widget keys)."""
    return st.session_state.get(_RESET_KEY, 0)


def _wk(field: str) -> str:
    """Builds a unique widget key for a field at the current generation."""
    return f"{field}_{_generation()}"


def clear_session_state():
    """
    Loops through Streamlit's session state and deletes every key.
    This forces all input widgets to reset to their default blank values.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def clear_form():
    """
    Resets the entire patient entry form (name, age, weight, selects,
    checkboxes and any uploaded lab report) while preserving global settings
    like the dark-mode toggle.

    Works by bumping the form generation number: every widget gets a brand-new
    key on the next render, so Streamlit fully remounts each one blank. This
    reliably clears fields that a simple session-state deletion may not reset.
    """
    # Remove the previous generation's widget keys from state.
    for field in FORM_FIELDS:
        old_key = f"{field}_{_generation()}"
        if old_key in st.session_state:
            del st.session_state[old_key]
    # Advance the generation so all widget keys change on the next run.
    st.session_state[_RESET_KEY] = _generation() + 1


def _info_card(icon: str, title: str, body: str):
    """Short hint line shown at the top of each form tab."""
    ui_modules.hint(title, body)


def render_collection_form():
    """
    Renders the clinical data input UI as a polished, wizard-style set of
    steps and returns a dictionary containing all patient data.

    The returned dictionary keeps the exact same schema as before so the
    quantum / AI / PDF modules continue to work unchanged.
    """
    tabs = st.tabs(
        ["Demographics & vitals", "Markers & history", "Reports & notes"]
    )

    # ---------------------------
    # STEP 1: Demographics & Vitals
    # ---------------------------
    with tabs[0]:
        _info_card(
            "👤",
            "Patient Profile",
            "Basic identifying and biometric information used to calibrate baseline risk.",
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Full Name *", placeholder="e.g. Jane Smith", key=_wk("name"))
            age = st.number_input(
                "Age *",
                min_value=0,
                max_value=120,
                step=1,
                value=None,
                placeholder="Type age…",
                key=_wk("age"),
            )
        with col2:
            gender = st.selectbox(
                "Gender *", ["Select", "Male", "Female", "Other"], key=_wk("gender")
            )
            height = st.number_input(
                "Height (cm)",
                min_value=0.0,
                step=1.0,
                value=None,
                placeholder="e.g. 170",
                key=_wk("height"),
            )
        with col3:
            weight = st.number_input(
                "Weight (kg)",
                min_value=0.0,
                step=1.0,
                value=None,
                placeholder="e.g. 70",
                key=_wk("weight"),
            )
            blood_group = st.selectbox(
                "Blood Group",
                ["Select", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                key=_wk("blood_group"),
            )

    # ---------------------------
    # STEP 2: Medical History & Genetic Markers
    # ---------------------------
    with tabs[1]:
        _info_card(
            "🧬",
            "Genetic & Lifestyle Factors",
            "Select any known hereditary markers and lifestyle factors that influence risk scoring.",
        )
        col4, col5 = st.columns(2)
        with col4:
            ancestry = st.selectbox(
                "Ancestry/Ethnicity",
                ["Select", "Asian", "African", "Caucasian", "Hispanic", "Other"],
                key=_wk("ancestry"),
            )
            smoking = st.selectbox(
                "Smoking History",
                ["Never Smoked", "Former Smoker", "Current Smoker"],
                key=_wk("smoking"),
            )
        with col5:
            st.markdown("**Known Genetic Mutations (check all that apply):**")
            brca1 = st.checkbox("BRCA1 (Breast/Ovarian Cancer Risk)", key=_wk("brca1"))
            brca2 = st.checkbox("BRCA2 (Breast/Ovarian Cancer Risk)", key=_wk("brca2"))
            apc = st.checkbox("APC (Colorectal Cancer Risk)", key=_wk("apc"))
            tp53 = st.checkbox("TP53 (Li-Fraumeni Syndrome)", key=_wk("tp53"))
            other_markers = st.multiselect(
                "Other mutations",
                SUGGESTED_MARKERS,
                accept_new_options=True,
                placeholder="Type a gene (e.g. PALB2) and press Enter",
                help="Pick from the list or type any mutation and press Enter to add it. "
                "These are included in the report and AI summary but not in the numeric score.",
                key=_wk("other_markers"),
            )

    # ---------------------------
    # STEP 3: Reports & Notes
    # ---------------------------
    with tabs[2]:
        _info_card(
            "🗂️",
            "Lab Reports & Clinical Notes",
            "Optionally attach a lab report for reference and add any physician notes.",
        )
        lab_report = st.file_uploader(
            "Upload Lab Report (PDF/IMG)", type=["pdf", "png", "jpg", "jpeg"], key=_wk("lab_report")
        )
        additional_details = st.text_area(
            "Additional Clinical Details",
            placeholder="Enter any other relevant symptoms, family history, or physician notes...",
            height=140,
            key=_wk("additional_details"),
        )

    # ---------------------------
    # Package everything into the standard dictionary
    # ---------------------------
    core = {"BRCA1": brca1, "BRCA2": brca2, "APC": apc, "TP53": tp53}
    extra = []
    for marker in other_markers:
        marker = marker.strip()
        if not marker:
            continue
        # Typing one of the four scored genes counts as ticking its checkbox.
        if marker.upper() in core:
            core[marker.upper()] = True
        elif marker.lower() not in {m.lower() for m in extra}:
            extra.append(marker)

    patient_data = {
        "Name": name,
        "Age": age,
        "Gender": gender,
        "Height": height,
        "Weight": weight,
        "Blood Group": blood_group,
        "Ancestry": ancestry,
        "Smoking History": smoking,
        "Genetic Markers": core,
        "Other Genetic Markers": extra,
        "Lab Report": lab_report,
        "Additional Details": additional_details,
    }

    return patient_data


def validate_patient(patient_data: dict) -> list[str]:
    """
    Returns a list of problems that should block the analysis (empty = OK).

    Name, age and gender are required; height and weight are optional but
    must be realistic when given.
    """
    problems = []
    if not (patient_data.get("Name") or "").strip():
        problems.append("Enter the patient's full name.")
    if patient_data.get("Age") is None:
        problems.append("Enter the patient's age.")
    if patient_data.get("Gender") in (None, "Select"):
        problems.append("Select the patient's gender.")

    height = patient_data.get("Height")
    if height and not 40 <= height <= 250:
        problems.append("Height should be between 40 and 250 cm.")
    weight = patient_data.get("Weight")
    if weight and not 2 <= weight <= 350:
        problems.append("Weight should be between 2 and 350 kg.")
    return problems
