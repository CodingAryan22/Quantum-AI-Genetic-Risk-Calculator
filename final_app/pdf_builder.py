import os
import tempfile
from fpdf import FPDF
import pandas as pd

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
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(200, 220, 220)
    pdf.cell(0, 10, ' 1. Patient Demographics & Vitals', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 11)
    name = patient_data.get('Name', 'N/A')
    age = patient_data.get('Age', 'N/A')
    gender = patient_data.get('Gender', 'N/A')
    blood_group = patient_data.get('Blood Group', 'N/A')
    
    pdf.cell(0, 8, f"Name: {name}   |   Age: {age}   |   Gender: {gender}   |   Blood Group: {blood_group}", 0, 1)
    pdf.ln(5)

    # --- 2. Genetic Profile ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, ' 2. Genetic Markers Identified', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 11)
    genetics = patient_data.get("Genetic Markers", {})
    positive_markers = [marker for marker, present in genetics.items() if present]
    
    if positive_markers:
        for marker in positive_markers:
            pdf.cell(0, 6, f"- {marker} Mutation Detected", 0, 1)
    else:
        pdf.cell(0, 6, "No high-risk genetic mutations selected.", 0, 1)
    pdf.ln(5)

    # --- 3. Risk Analysis Metrics ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, ' 3. Quantum Monte Carlo Risk Metrics', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 11)
    base_risk = risk_table["Base Deterministic Risk"].iloc[0]
    sim_mean = risk_table["Simulated Mean"].iloc[0]
    ci_range = risk_table["90% Confidence Interval"].iloc[0]
    
    pdf.cell(0, 8, f"Standard Deterministic Baseline: {base_risk}", 0, 1)
    pdf.cell(0, 8, f"Simulated Quantum Mean: {sim_mean}", 0, 1)
    pdf.cell(0, 8, f"90% Statistical Confidence Interval: {ci_range}", 0, 1)
    pdf.ln(5)

    # --- 4. AI Clinical Synthesis ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, ' 4. AI-Generated Clinical Synthesis', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 11)
    # Multi_cell handles text wrapping automatically
    # Ensure encoding works for special characters returned by AI
    safe_summary = ai_summary.encode('latin-1', 'replace').decode('latin-1')
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