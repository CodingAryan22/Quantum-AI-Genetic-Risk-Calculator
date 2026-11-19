import re

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
    "family_first",
    "family_second",
    "brca1",
    "brca2",
    "apc",
    "tp53",
    "other_markers",
    "lab_report",
    "additional_details",
]

# Suggestions for the "Other mutations" box, with the cancers each gene is best
# known for (shown in the dropdown). Users can also type any other gene.
MARKER_INFO = {
    "PALB2": "Breast/Pancreatic Cancer Risk",
    "CHEK2": "Breast/Colorectal Cancer Risk",
    "ATM": "Breast/Pancreatic Cancer Risk",
    "PTEN": "Cowden Syndrome: Breast/Thyroid/Uterine",
    "CDH1": "Diffuse Gastric/Lobular Breast Cancer Risk",
    "STK11": "Peutz-Jeghers Syndrome: GI/Pancreatic/Breast",
    "MLH1": "Lynch Syndrome: Colorectal/Endometrial",
    "MSH2": "Lynch Syndrome: Colorectal/Endometrial",
    "MSH6": "Lynch Syndrome: Colorectal/Endometrial",
    "PMS2": "Lynch Syndrome: Colorectal/Endometrial",
    "RAD51C": "Ovarian/Breast Cancer Risk",
    "RAD51D": "Ovarian/Breast Cancer Risk",
    "BRIP1": "Ovarian Cancer Risk",
    "MUTYH": "MUTYH Polyposis: Colorectal Cancer Risk",
}
SUGGESTED_MARKERS = list(MARKER_INFO)


def marker_label(gene: str) -> str:
    """'PALB2 (Breast/Pancreatic Cancer Risk)'; genes typed by the user are shown as typed."""
    info = MARKER_INFO.get(gene)
    return f"{gene} ({info})" if info else gene


def _generation() -> int:
    """Returns the current form generation (used to build widget keys)."""
    return st.session_state.get(_RESET_KEY, 0)


def _wk(field: str) -> str:
    """Builds a unique widget key for a field at the current generation."""
    return f"{field}_{_generation()}"


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
    st.session_state[_STEP_KEY] = 0
    st.session_state.pop(_REPORT_KEY, None)


STEPS = ["Demographics & vitals", "Markers & history", "Notes"]
_STEP_KEY = "_form_step"

GENDERS = ["Select", "Male", "Female", "Other"]
BLOOD_GROUPS = ["Select", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ANCESTRIES = ["Select", "Asian", "African", "Caucasian", "Hispanic", "Other"]
SMOKING = ["Never Smoked", "Former Smoker", "Current Smoker"]


def current_step() -> int:
    return st.session_state.get(_STEP_KEY, 0)


def _go_to(step: int):
    st.session_state[_STEP_KEY] = step


def _val(field: str, default=None):
    """A form field's value, whether or not its widget is on screen this run."""
    return st.session_state.get(_wk(field), default)


def collect_patient() -> dict:
    """Builds the patient dictionary from every saved form value."""
    core = {
        "BRCA1": bool(_val("brca1", False)),
        "BRCA2": bool(_val("brca2", False)),
        "APC": bool(_val("apc", False)),
        "TP53": bool(_val("tp53", False)),
    }
    extra = []
    for marker in _val("other_markers", []) or []:
        marker = marker.strip()
        if not marker:
            continue
        # Typing one of the four scored genes counts as ticking its checkbox.
        if marker.upper() in core:
            core[marker.upper()] = True
        elif marker.lower() not in {m.lower() for m in extra}:
            extra.append(marker)

    return {
        "Name": _val("name", ""),
        "Age": _val("age"),
        "Gender": _val("gender", "Select"),
        "Height": _val("height"),
        "Weight": _val("weight"),
        "Blood Group": _val("blood_group", "Select"),
        "Ancestry": _val("ancestry", "Select"),
        "Smoking History": _val("smoking", "Never Smoked"),
        "Family History": {
            "First-degree": int(_val("family_first", 0) or 0),
            "Second-degree": int(_val("family_second", 0) or 0),
        },
        "Genetic Markers": core,
        "Other Genetic Markers": extra,
        "Lab Report": _val("lab_report"),
        "Additional Details": _val("additional_details", ""),
    }


def step_problems(step: int, patient: dict) -> list[str]:
    """What is still missing or wrong on one step (empty list = step complete)."""
    problems = []
    if step == 0:
        if not (patient.get("Name") or "").strip():
            problems.append("Enter the patient's full name.")
        if patient.get("Age") is None:
            problems.append("Enter the patient's age.")
        if patient.get("Gender") in (None, "Select"):
            problems.append("Select the patient's gender.")
        height, weight = patient.get("Height"), patient.get("Weight")
        if not height:
            problems.append("Enter the patient's height.")
        elif not 40 <= height <= 250:
            problems.append("Height should be between 40 and 250 cm.")
        if not weight:
            problems.append("Enter the patient's weight.")
        elif not 2 <= weight <= 350:
            problems.append("Weight should be between 2 and 350 kg.")
        if patient.get("Blood Group") in (None, "Select"):
            problems.append("Select the patient's blood group.")
    elif step == 1:
        if patient.get("Ancestry") in (None, "Select"):
            problems.append("Select the patient's ancestry/ethnicity.")
    # Step 3 (lab report and notes) is optional.
    return problems


def validate_patient(patient_data: dict) -> list[str]:
    """Every problem across all steps (empty = ready to generate)."""
    return [p for step in range(len(STEPS)) for p in step_problems(step, patient_data)]


def _stepper(step: int):
    items = []
    for i, label in enumerate(STEPS):
        state = "done" if i < step else "current" if i == step else "todo"
        mark = "✓" if i < step else str(i + 1)
        items.append(f'<div class="wz-step wz-{state}"><span class="wz-n">{mark}</span>'
                     f'<span class="wz-l">{label}</span></div>')
    bar = '<div class="wz-sep"></div>'.join(items)
    st.markdown(f'<div class="wz">{bar}</div>', unsafe_allow_html=True)


def _step_demographics():
    ui_modules.hint("Patient profile", "All fields on this step are required.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Full Name *", placeholder="e.g. Jane Smith", key=_wk("name"))
        st.number_input("Age *", min_value=0, max_value=120, step=1, value=None,
                        placeholder="Type age…", key=_wk("age"))
    with col2:
        st.selectbox("Gender *", GENDERS, key=_wk("gender"))
        st.number_input("Height (cm) *", min_value=0.0, step=1.0, value=None,
                        placeholder="e.g. 170", key=_wk("height"))
    with col3:
        st.number_input("Weight (kg) *", min_value=0.0, step=1.0, value=None,
                        placeholder="e.g. 70", key=_wk("weight"))
        st.selectbox("Blood Group *", BLOOD_GROUPS, key=_wk("blood_group"))


SCORED_GENES = ["BRCA1", "BRCA2", "APC", "TP53"]
_REPORT_KEY = "_lab_report_findings"  # parsed findings, kept after the upload widget unmounts


def _apply_report_findings():
    """Ticks / adds every gene the report marks as positive."""
    findings = st.session_state.get(_REPORT_KEY, {}).get("findings", [])
    others = list(st.session_state.get(_wk("other_markers"), []) or [])
    for f in findings:
        if f["status"] != "positive":
            continue
        if f["gene"] in SCORED_GENES:
            st.session_state[_wk(f["gene"].lower())] = True
        elif f["gene"] not in others:
            others.append(f["gene"])
    st.session_state[_wk("other_markers")] = others
    st.session_state["_toast"] = "Genes from the lab report were added to the form."


def _lab_report_panel():
    """Optional PDF upload that reads gene results and can fill the checkboxes."""
    import lab_report

    with st.expander("Fill from a lab report (PDF)", icon=":material/upload_file:",
                     expanded=_REPORT_KEY in st.session_state):
        upload = st.file_uploader(
            "Upload a genetic test report", type=["pdf"], key=_wk("lab_report"),
            help="The file is read in memory to find gene results and is not saved.",
        )
        if upload is not None:
            cached = st.session_state.get(_REPORT_KEY)
            if not cached or cached.get("file_id") != upload.file_id:
                result = lab_report.read_report(upload.getvalue(), SCORED_GENES + SUGGESTED_MARKERS)
                st.session_state[_REPORT_KEY] = {"file_id": upload.file_id, "name": upload.name, **result}
        report = st.session_state.get(_REPORT_KEY)
        if not report:
            st.caption("Upload a PDF and the genes it reports are found automatically.")
            return
        if not report["has_text"]:
            ui_modules.hint("No readable text in this PDF.",
                            "It may be a scanned image. Please tick the genes below by hand.")
            return
        if not report["findings"]:
            ui_modules.hint("No known genes found in this report.",
                            "Check the report and tick any mutations below by hand.")
            return
        kinds = {"positive": ("Positive", "bad"), "uncertain": ("Uncertain (VUS)", "warn"),
                 "negative": ("Negative", "good"), "mentioned": ("Mentioned", "neutral")}
        rows = "".join(
            f"<tr><td><span class='dt-title'>{f['gene']}</span></td>"
            f"<td>{ui_modules.badge(*kinds[f['status']], dot=True)}</td>"
            f"<td class='card-s'>{ui_modules._esc(f['evidence'])}</td></tr>"
            for f in report["findings"]
        )
        st.markdown(
            f"<div class='card-s' style='margin-bottom:0.4rem'>Found in <b>{ui_modules._esc(report['name'])}</b>:</div>"
            f"<div class='dt-wrap'><table class='dt dt-compact'><thead><tr><th>Gene</th><th>Result</th>"
            f"<th>From the report</th></tr></thead><tbody>{rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )
        positives = [f["gene"] for f in report["findings"] if f["status"] == "positive"]
        st.button(
            f"Apply to form ({', '.join(positives)})" if positives else "Nothing positive to apply",
            icon=":material/check:", type="primary", disabled=not positives,
            key="apply-report", on_click=_apply_report_findings,
            help="Ticks positive scored genes and adds other positive genes to 'Other mutations'. "
                 "Uncertain and negative results are not added.",
        )


def _step_markers():
    ui_modules.hint("Genetic & lifestyle factors",
                    "Tick any known mutations; leave them unticked if none were found.")
    _lab_report_panel()
    col4, col5 = st.columns(2)
    with col4:
        st.selectbox("Ancestry/Ethnicity *", ANCESTRIES, key=_wk("ancestry"))
        st.selectbox("Smoking History *", SMOKING, key=_wk("smoking"))
        st.markdown("**Family history of cancer**")
        st.number_input(
            "1st-degree relatives with cancer", min_value=0, max_value=10, step=1,
            help="Parents, brothers, sisters and children diagnosed with breast, "
            "ovarian, colorectal, prostate or another related cancer.",
            key=_wk("family_first"),
        )
        st.number_input(
            "2nd-degree relatives with cancer", min_value=0, max_value=10, step=1,
            help="Grandparents, aunts, uncles, nieces, nephews and half-siblings.",
            key=_wk("family_second"),
        )
    with col5:
        st.markdown("**Known genetic mutations (check all that apply)**")
        st.checkbox("BRCA1 (Breast/Ovarian Cancer Risk)", key=_wk("brca1"))
        st.checkbox("BRCA2 (Breast/Ovarian Cancer Risk)", key=_wk("brca2"))
        st.checkbox("APC (Colorectal Cancer Risk)", key=_wk("apc"))
        st.checkbox("TP53 (Li-Fraumeni Syndrome)", key=_wk("tp53"))
        st.multiselect(
            "Other mutations", SUGGESTED_MARKERS, accept_new_options=True,
            format_func=marker_label,
            placeholder="Type a gene (e.g. PALB2) and press Enter",
            help="Pick from the list or type any mutation and press Enter to add it. "
            "These are included in the report and AI summary but not in the numeric score.",
            key=_wk("other_markers"),
        )


def _step_notes():
    ui_modules.hint("Clinical notes", "Optional. Add anything else the clinician knows.")
    st.text_area(
        "Additional Clinical Details",
        placeholder="Enter any other relevant symptoms, family history, or physician notes...",
        height=140, key=_wk("additional_details"),
    )


def render_collection_form() -> tuple[dict, bool]:
    """
    Draws the 3-step patient form. Only the current step's fields are shown;
    Next unlocks once that step is complete, and the last step has Generate.

    Returns (patient_data, generate_clicked).
    """
    # Only one step's fields are drawn per run; keep the other steps' answers.
    keep_form_values()
    step = current_step()
    _stepper(step)
    [_step_demographics, _step_markers, _step_notes][step]()

    patient = collect_patient()
    problems = step_problems(step, patient)
    last = step == len(STEPS) - 1

    back_col, msg_col, next_col = st.columns([1, 2.6, 1.4], vertical_alignment="center")
    with back_col:
        if step > 0:
            st.button("Back", icon=":material/arrow_back:", width="stretch",
                      on_click=_go_to, args=(step - 1,), key="wz-back")
    with msg_col:
        if problems:
            # "Enter the patient's full name." -> "full name"; range errors stay as written.
            short = [
                re.sub(r"^(Enter|Select) the patient's ", "", p).rstrip(".")
                for p in problems
            ]
            st.markdown(f'<div class="wz-missing"><b>Still needed:</b> {", ".join(short)}</div>',
                        unsafe_allow_html=True)
    generate = False
    with next_col:
        if last:
            generate = st.button("Generate risk analysis", type="primary", width="stretch",
                                 disabled=bool(validate_patient(patient)), key="wz-generate")
        else:
            st.button("Next", type="primary", icon=":material/arrow_forward:",
                      icon_position="right", width="stretch", disabled=bool(problems),
                      on_click=_go_to, args=(step + 1,), key="wz-next")
    return patient, generate


def keep_form_values():
    """
    Re-saves every form field's current value in session state.

    Streamlit deletes a widget's state on any run where the widget isn't drawn,
    so leaving the New assessment page would wipe the form. Writing each value
    back to its own key on every run (before any page draws) keeps it. The lab
    report upload is skipped: Streamlit doesn't allow setting file uploads.
    """
    for field in FORM_FIELDS:
        if field == "lab_report":
            continue
        key = _wk(field)
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
