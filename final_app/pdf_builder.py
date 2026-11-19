import os
import re
import tempfile
from fpdf import FPDF
import pandas as pd

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
        self.cell(0, 10, 'Quantum-AI Clinical Dashboard', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(patient_data: dict, risk_table: pd.DataFrame, ai_summary: str) -> bytes:
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
    _section(pdf, ' 2. Genetic Markers Identified')
    genetics = patient_data.get("Genetic Markers", {})
    positive_markers = [marker for marker, present in genetics.items() if present]
    
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
    pdf.ln(5)

    # --- 3. Risk Analysis Metrics ---
    _section(pdf, ' 3. Quantum Monte Carlo Risk Metrics')
    base_risk = risk_table["Base Deterministic Risk"].iloc[0]
    sim_mean = risk_table["Simulated Mean"].iloc[0]
    ci_range = risk_table["90% Confidence Interval"].iloc[0]
    
    pdf.cell(0, 8, f"Standard Deterministic Baseline: {base_risk}", 0, 1)
    pdf.cell(0, 8, f"Simulated Quantum Mean: {sim_mean}", 0, 1)
    pdf.cell(0, 8, f"90% Statistical Confidence Interval: {ci_range}", 0, 1)
    pdf.ln(5)

    # --- 4. AI Clinical Synthesis ---
    _section(pdf, ' 4. AI-Generated Clinical Synthesis')
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