import os
import re
import tempfile
from fpdf import FPDF
import pandas as pd

try:
    from features import positive_markers as _positive_markers
except ModuleNotFoundError:  # imported as final_app.pdf_builder
    from .features import positive_markers as _positive_markers

# The built-in PDF fonts only cover Latin-1, so map common "smart" punctuation
# from the AI output to plain equivalents instead of letting it become "?".
_PUNCTUATION = {
    "—": "-", "–": "-", "‒": "-", "−": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "•": "-", " ": " ", "≥": ">=", "≤": "<=",
}

# Colours matching the app's purple theme.
BRAND_FILL = (244, 235, 255)
BRAND_TEXT = (83, 56, 158)
BODY_TEXT = (16, 24, 40)


def _pdf_text(text) -> str:
    """Makes any value safe to print with the built-in Latin-1 PDF fonts."""
    text = "" if text is None else str(text)
    for src, dst in _PUNCTUATION.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


def _strip_markdown(text: str) -> str:
    """Turns the AI's Markdown into plain text: no **, *, _ or # markers."""
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)               # headings
    text = re.sub(r"^(\s*)[*+]\s+", r"\1- ", text, flags=re.M)              # bullets
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)                         # bold
    text = re.sub(r"(?<![\w*])([*_])(?!\s)(.+?)(?<!\s)\1(?![\w*])", r"\2", text)  # italics
    return text


def _section(pdf, title: str):
    """Purple section header bar, then resets to body text style."""
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(*BRAND_FILL)
    pdf.set_text_color(*BRAND_TEXT)
    pdf.cell(0, 10, title, 0, 1, 'L', fill=True)
    pdf.ln(2)
    pdf.set_text_color(*BODY_TEXT)
    pdf.set_font('Arial', '', 11)


class PDF(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Title
        self.cell(0, 10, 'Hereditary Disease Risk Prediction Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'RiskPredict - Hybrid Classical / Quantum ML Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(patient_data: dict, risk_table: pd.DataFrame, ai_summary: str,
                 model_predictions: dict | None = None) -> bytes:
    """
    Compiles patient data, risk metrics, and the AI summary into a formatted PDF.
    Returns the PDF as a byte string for Streamlit to download.
    """
    pdf = PDF()
    pdf.add_page()
    
    # --- 1. Patient Demographics ---
    _section(pdf, ' 1. Patient Demographics & Vitals')
    name = patient_data.get('Name', 'N/A')
    age = patient_data.get('Age', 'N/A')
    gender = patient_data.get('Gender', 'N/A')
    blood_group = patient_data.get('Blood Group', 'N/A')
    
    pdf.cell(0, 8, _pdf_text(f"Name: {name}   |   Age: {age}   |   Gender: {gender}   |   Blood Group: {blood_group}"), 0, 1)
    pdf.ln(5)

    # --- 2. Genetic Profile ---
    _section(pdf, ' 2. Genetic Markers & Family History')
    positive_markers = _positive_markers(patient_data)
    
    # Free-typed markers may contain characters the built-in PDF fonts can't encode.
    other_markers = [
        _pdf_text(m)
        for m in patient_data.get("Other Genetic Markers", [])
    ]

    if positive_markers or other_markers:
        for marker in positive_markers:
            pdf.cell(0, 6, f"- {marker} Mutation Detected", 0, 1)
        for marker in other_markers:
            pdf.cell(0, 6, f"- {marker} Mutation Reported (not included in risk score)", 0, 1)
    else:
        pdf.cell(0, 6, "No high-risk genetic mutations selected.", 0, 1)
    family = patient_data.get("Family History", {}) or {}
    pdf.cell(0, 6, f"- Relatives with cancer: {family.get('First-degree', 0)} first-degree, "
                   f"{family.get('Second-degree', 0)} second-degree", 0, 1)
    pdf.ln(5)

    # --- 3. Risk Analysis Metrics ---
    _section(pdf, ' 3. Rule-based Score & Monte Carlo Uncertainty')
    base_risk = risk_table["Base Deterministic Risk"].iloc[0]
    sim_mean = risk_table["Simulated Mean"].iloc[0]
    ci_range = risk_table["90% Confidence Interval"].iloc[0]
    
    pdf.cell(0, 8, f"Rule-based baseline score: {base_risk}", 0, 1)
    pdf.cell(0, 8, f"Monte Carlo mean (1,500 runs): {sim_mean}", 0, 1)
    pdf.cell(0, 8, f"90% interval: {ci_range}", 0, 1)
    pdf.ln(5)

    section = 4
    if model_predictions:
        _section(pdf, f' {section}. Machine-Learning Predictions (20-year risk)')
        for model_name, p in model_predictions.items():
            pdf.cell(0, 7, _pdf_text(f"{model_name}: {p * 100:.0f}%"), 0, 1)
        pdf.set_font('Arial', 'I', 9)
        pdf.multi_cell(0, 5, "Models were trained on simulated (synthetic) patients and are "
                             "for education and research only.")
        pdf.set_font('Arial', '', 11)
        pdf.ln(5)
        section += 1

    # --- AI Clinical Synthesis ---
    _section(pdf, f' {section}. AI-Generated Clinical Synthesis')
    # Multi_cell handles text wrapping automatically
    safe_summary = _pdf_text(_strip_markdown(ai_summary))
    pdf.multi_cell(0, 6, safe_summary)

    # --- Output to Bytes ---
    # We save to a temporary file, read the bytes, and pass it to Streamlit
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()
        
    os.remove(tmp_path)
    return pdf_bytes

DISCLAIMER = ("Educational estimate only. Models were trained on simulated (synthetic) "
              "patients; this is not a medical diagnosis.")


def _write_patient_history(pdf, patient: dict):
    """
    Writes one patient's sections (details, mutations and linked diseases,
    assessment table, latest AI summary) onto the current page of `pdf`.
    `patient` is one entry from storage.group_patients().
    """
    history = patient["history"]
    latest = history[0]
    info = latest["patient"]

    _section(pdf, ' 1. Patient Details')
    fam = info.get("family_history") or {}
    lines = [
        f"Name: {info.get('name')}   |   Age: {info.get('age')}   |   Gender: {info.get('gender')}",
        f"Height: {info.get('height_cm')} cm   |   Weight: {info.get('weight_kg')} kg   |   "
        f"Blood group: {info.get('blood_group')}",
        f"Ancestry: {info.get('ancestry')}   |   Smoking: {info.get('smoking')}",
        f"Relatives with cancer: {fam.get('First-degree', 0)} first-degree, "
        f"{fam.get('Second-degree', 0)} second-degree",
    ]
    for line in lines:
        pdf.cell(0, 7, _pdf_text(line), 0, 1)
    pdf.ln(4)

    _section(pdf, ' 2. Mutations & Linked Diseases')
    markers = (info.get("markers") or []) + (info.get("other_markers") or [])
    pdf.cell(0, 7, _pdf_text("Mutations: " + (", ".join(markers) or "None reported")), 0, 1)
    diseases = patient.get("diseases") or []
    pdf.multi_cell(0, 6, _pdf_text("Linked diseases: " + ("; ".join(diseases) or "None")))
    pdf.ln(4)

    _section(pdf, f' 3. Assessment History ({len(history)})')
    widths = [42, 26, 30, 28, 64]
    headers = ["Date", "Risk", "90% range", "Tier", "ML models (20-yr): LR / RF / QK"]
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(*BRAND_FILL)
    for w, h in zip(widths, headers):
        pdf.cell(w, 7, h, 1, 0, 'L', fill=True)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for r in history:
        res, models = r["result"], r["result"].get("models") or {}
        model_txt = " / ".join(
            f"{models[k] * 100:.0f}%" for k in ("Logistic regression", "Random forest", "Quantum kernel SVM")
            if k in models
        ) or "-"
        row = [
            r["created_at"].astimezone().strftime("%d %b %Y %H:%M"),
            f"{res['mean']:.0f}%",
            f"{res['ci_low']:.0f}-{res['ci_high']:.0f}%",
            res.get("tier", ""),
            model_txt,
        ]
        for w, v in zip(widths, row):
            pdf.cell(w, 7, _pdf_text(v), 1, 0, 'L')
        pdf.ln()
    pdf.ln(5)

    if latest.get("summary"):
        _section(pdf, ' 4. Latest AI-Generated Clinical Summary')
        pdf.multi_cell(0, 6, _pdf_text(_strip_markdown(latest["summary"])))
        pdf.ln(3)


def _disclaimer(pdf):
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(*BODY_TEXT)
    pdf.multi_cell(0, 5, DISCLAIMER)


def generate_patient_history_pdf(patient: dict) -> bytes:
    """One patient's full saved record as a PDF."""
    pdf = PDF()
    pdf.add_page()
    _write_patient_history(pdf, patient)
    _disclaimer(pdf)
    return bytes(pdf.output())


def generate_all_patients_pdf(patients: list) -> bytes:
    """
    Every saved patient: an overview table on the first page, then each
    patient's full history starting on its own page.
    """
    pdf = PDF()
    pdf.add_page()
    total = sum(p["assessments"] for p in patients)
    _section(pdf, f' All Patients ({len(patients)} patients, {total} assessments)')

    widths = [46, 14, 20, 22, 26, 16, 46]
    headers = ["Patient", "Age", "Sex", "Latest risk", "Tier", "Visits", "Last assessed"]
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(*BRAND_FILL)
    for w, h in zip(widths, headers):
        pdf.cell(w, 7, h, 1, 0, 'L', fill=True)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for p in patients:
        row = [
            p["name"],
            "" if p.get("age") is None else str(int(p["age"])),
            p.get("gender") or "",
            f"{p['latest_mean']:.0f}%",
            p["latest_tier"],
            str(p["assessments"]),
            p["last_assessed"].astimezone().strftime("%d %b %Y %H:%M"),
        ]
        for w, v in zip(widths, row):
            pdf.cell(w, 7, _pdf_text(v)[:30], 1, 0, 'L')
        pdf.ln()
    pdf.ln(5)
    _disclaimer(pdf)

    for p in patients:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(*BRAND_TEXT)
        pdf.cell(0, 9, _pdf_text(p["name"]), 0, 1)
        pdf.set_text_color(*BODY_TEXT)
        pdf.ln(2)
        _write_patient_history(pdf, p)
    return bytes(pdf.output())
