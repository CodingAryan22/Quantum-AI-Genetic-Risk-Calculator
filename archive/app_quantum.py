import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from fpdf import FPDF
import plotly.express as px
import tempfile
import os
import json
import google.generativeai as genai
from PIL import Image

# --- 1. SETUP & SESSION STATE ---
st.set_page_config(page_title="Quantum Clinical Logic Model", layout="wide")

# Added new columns for extended patient details
EXPECTED_COLS = [
    'date', 'time', 'Full Name', 'Age', 'Gender', 'Blood Group', 
    'Height (cm)', 'Weight (kg)', 'Ancestry', 'Smoking',
    'brca1', 'brca2', 'tp53', 'apc', 'pten', 'Risk Score', 'Status', 'Diseases'
]

if 'history_quantum_df' not in st.session_state:
    st.session_state.history_quantum_df = pd.DataFrame(columns=EXPECTED_COLS)

# UNIFIED WIDGET STATE INITIALIZATION (Includes new fields)
widget_defaults = {
    "input_name": "", 
    "input_age": 30, 
    "input_gender": "Unknown", 
    "input_bg": "Unknown",
    "input_height": 170,        
    "input_weight": 70,         
    "input_ancestry": "Unknown",
    "input_smoke": "Never",     
    "input_brca1": "Inconclusive", 
    "input_brca2": "Inconclusive", 
    "input_tp53": "Inconclusive",
    "input_apc": "Inconclusive", 
    "input_pten": "Inconclusive", 
    "last_file": None
}

for key, default_val in widget_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_val


# --- 2. HELPERS & SAFETY NETS ---
def clear_form_data():
    for k, v in widget_defaults.items():
        st.session_state[k] = v
    if "pdf_uploader" in st.session_state: 
        del st.session_state["pdf_uploader"]

def clear_all_records():
    st.session_state.history_quantum_df = pd.DataFrame(columns=EXPECTED_COLS)

def sanitize_text(text):
    """Removes unusual unicode characters to prevent FPDF crashes."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '–': '-', '—': '-', '…': '...', '•': '-', '↳': '->', '→': '->'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

def calculate_quantum_risk(age, gender, brca1, brca2, tp53, apc, pten):
    """
    Simulates a quantum probability algorithm using state vectors and expectation values.
    Calculation: E = <psi|O|psi>
    """
    amplitudes = {'Positive': 0.85, 'Inconclusive': 0.35, 'Negative': 0.05}
    
    m_states = [
        amplitudes.get(brca1, 0.05), 
        amplitudes.get(brca2, 0.05), 
        amplitudes.get(tp53, 0.05), 
        amplitudes.get(apc, 0.05), 
        amplitudes.get(pten, 0.05)
    ]
    
    age_factor = min(age / 100.0, 1.0) * 0.6
    m_states.append(age_factor)
    
    state_vector = np.array(m_states)
        
    risk_observable = np.array([0.9, 0.85, 0.95, 0.75, 0.70, 0.4]) 
    expectation = np.dot(state_vector ** 2, risk_observable)
    
    score = min(max(int((expectation / 3.14) * 100), 0), 100) 
    
    if score >= 70: status = "High Risk"
    elif score >= 30: status = "Moderate Risk"
    else: status = "Low Risk"
    
    diseases = []
    if brca1 == 'Positive' or brca2 == 'Positive': diseases.append("Hereditary Breast and Ovarian Cancer (HBOC) Syndrome")
    if tp53 == 'Positive': diseases.append("Li-Fraumeni Syndrome (LFS)")
    if apc == 'Positive': diseases.append("Familial Adenomatous Polyposis (FAP)")
    if pten == 'Positive': diseases.append("Cowden Syndrome (PTEN Hamartoma Tumor Syndrome)")
    
    if not diseases:
        diseases.append("No primary correlated syndromes identified.")
        
    return score, status, diseases

# --- PDF GENERATORS ---
def generate_single_pdf(data_row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Quantum Clinical Risk Report", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, sanitize_text(f"Date: {data_row['date']} {data_row['time']}"), ln=True)
    pdf.cell(0, 8, sanitize_text(f"Patient Name: {data_row['Full Name']}"), ln=True)
    pdf.cell(0, 8, sanitize_text(f"Age: {data_row['Age']} | Gender: {data_row['Gender']} | Blood Group: {data_row['Blood Group']}"), ln=True)
    # Added new demographics to PDF
    pdf.cell(0, 8, sanitize_text(f"Height: {data_row['Height (cm)']}cm | Weight: {data_row['Weight (kg)']}kg | Ancestry: {data_row['Ancestry']}"), ln=True)
    pdf.cell(0, 8, sanitize_text(f"Smoking History: {data_row['Smoking']}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Input State Vectors:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, sanitize_text(f"BRCA1: {data_row['brca1']} | BRCA2: {data_row['brca2']} | TP53: {data_row['tp53']}"), ln=True)
    pdf.cell(0, 8, sanitize_text(f"APC: {data_row['apc']} | PTEN: {data_row['pten']}"), ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, sanitize_text(f"Calculated Quantum Probability: {data_row['Risk Score']}% ({data_row['Status']})"), ln=True)
    pdf.ln(5)
    
    pdf.set_text_color(102, 0, 102)
    pdf.cell(0, 10, "Quantum Entangled Conditions:", ln=True)
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font("Arial", '', 12)
    diseases = data_row.get('Diseases', [])
    if isinstance(diseases, str): 
        try: diseases = json.loads(diseases.replace("'", '"')) 
        except: diseases = [diseases]
        
    for condition in diseases:
        pdf.cell(0, 8, sanitize_text(f"- {condition}"), ln=True)
            
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

def generate_all_reports_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Quantum Clinical - Master Records Report", ln=True, align="C")
    pdf.ln(10)
    
    for index, row in df.iterrows():
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 6, sanitize_text(f"Patient: {row['Full Name']} (Age: {row['Age']}, Gender: {row['Gender']})"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, sanitize_text(f"States -> BRCA1:{row['brca1']}, BRCA2:{row['brca2']}, TP53:{row['tp53']}, APC:{row['apc']}, PTEN:{row['pten']}"), ln=True)
        pdf.cell(0, 6, sanitize_text(f"Probability -> Score: {row['Risk Score']}% | Status: {row['Status']}"), ln=True)
        pdf.ln(4)
        pdf.cell(0, 0, "", "T")
        pdf.ln(4)
        
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# --- 3. UI & SIDEBAR ---
st.title("⚛️ Quantum Clinical Logic Model")
st.markdown("""<style>div.stButton > button[kind="primary"] { padding: 1rem 2rem; font-size: 18px; font-weight: bold; background-color: #6a0dad; border: none; }</style>""", unsafe_allow_html=True)

try: 
    user_api_key = st.secrets["GEMINI_API_KEY"]
except KeyError: 
    user_api_key = None

with st.sidebar:
    st.header("📄 Auto-Fill from Report")
    uploaded_file = st.file_uploader("Upload Lab Report", type=["pdf", "png", "jpg", "jpeg"], key="pdf_uploader")
    
    if uploaded_file and uploaded_file.name != st.session_state.last_file:
        try:
            if not user_api_key: 
                st.error("⚠️ Gemini API key missing. Cannot process document.")
            else:
                with st.spinner("🤖 Gemini Vision is reading the document..."):
                    genai.configure(api_key=user_api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = """Extract patient details from the document: 
                              "Name", "Age" (int), "Gender" ("Male", "Female", "Other"), "Blood Group". 
                              For BRCA1, BRCA2, TP53, APC, PTEN use ONLY "Positive", "Negative", or "Inconclusive". 
                              Return valid JSON only matching these exact keys."""
                    
                    if uploaded_file.type == "application/pdf":
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                        
                        pdf_file = genai.upload_file(tmp_path)
                        response = model.generate_content([prompt, pdf_file])
                        
                        os.remove(tmp_path)
                        genai.delete_file(pdf_file.name)
                        
                    elif uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                        image = Image.open(uploaded_file)
                        response = model.generate_content([prompt, image])
                    
                    clean_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                    data = json.loads(clean_json)
                    
                    st.session_state.input_name = data.get("Name", "")
                    st.session_state.input_age = int(data.get("Age", 30)) if str(data.get("Age")).isdigit() else 30
                    
                    g_val = data.get("Gender", "Unknown")
                    st.session_state.input_gender = g_val if g_val in ["Male", "Female", "Other"] else "Unknown"
                    
                    b_val = data.get("Blood Group", "Unknown")
                    st.session_state.input_bg = b_val if b_val in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] else "Unknown"
                    
                    st.session_state.input_brca1 = data.get("BRCA1", "Inconclusive")
                    st.session_state.input_brca2 = data.get("BRCA2", "Inconclusive")
                    st.session_state.input_tp53 = data.get("TP53", "Inconclusive")
                    st.session_state.input_apc = data.get("APC", "Inconclusive")
                    st.session_state.input_pten = data.get("PTEN", "Inconclusive")
                    
                    st.session_state.last_file = uploaded_file.name
                    st.success("Document Processed Successfully!")
                    st.rerun() 
                    
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()
    st.header("👤 Patient Details")
    name = st.text_input("Full Name", key="input_name")
    
    # Split UI into two columns for the new data points
    colA, colB = st.columns(2)
    with colA:
        age = st.slider("Age", 1, 100, key="input_age")
        height = st.number_input("Height (cm)", 100, 250, key="input_height")
        bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"], key="input_bg")
    with colB:
        gender = st.selectbox("Gender", ["Male", "Female", "Other", "Unknown"], key="input_gender")
        weight = st.number_input("Weight (kg)", 30, 200, key="input_weight")
        ancestry = st.selectbox("Ancestry", ["Unknown", "European", "Ashkenazi Jewish", "Asian", "African", "Hispanic", "Mixed"], key="input_ancestry")
        
    st.write("")
    smoke = st.selectbox("Smoking History", ["Never", "Former Smoker", "Current Smoker"], key="input_smoke")

    st.write("")
    additional_details = st.text_area("Additional Details (Optional)", key="input_additional_details", height=80)
    
    st.divider()
    st.header("🧬 Genetic Marker States")
    brca1 = st.selectbox("BRCA1 State", ["Positive", "Negative", "Inconclusive"], key="input_brca1")
    brca2 = st.selectbox("BRCA2 State", ["Positive", "Negative", "Inconclusive"], key="input_brca2")
    tp53 = st.selectbox("TP53 State", ["Positive", "Negative", "Inconclusive"], key="input_tp53")
    apc = st.selectbox("APC State", ["Positive", "Negative", "Inconclusive"], key="input_apc")
    pten = st.selectbox("PTEN State", ["Positive", "Negative", "Inconclusive"], key="input_pten")

    st.divider()
    st.header("⚙️ Administrative")
    st.button("🧹 Clear Form", on_click=clear_form_data, use_container_width=True)
    st.button("🗑️ Clear All Records", on_click=clear_all_records, type="secondary", use_container_width=True)


# --- 4. EXECUTION ---
if st.button("⚛️ Run Quantum Analysis", type="primary", use_container_width=True):
    
    # --- NEW VALIDATION CHECKS ---
    if not name.strip():
        st.warning("⚠️ Please enter the Patient's Full Name before running the analysis.")
        st.stop() # Halts the script
        
    if gender == "Unknown":
        st.warning("⚠️ Please select the Patient's Gender. Gender is required for accurate probability amplitudes.")
        st.stop()
        
    if bg == "Unknown":
        st.info("ℹ️ Note: Blood group is marked as Unknown. Proceeding with baseline states.")
    # -----------------------------

    with st.spinner("Calculating quantum probability amplitudes..."):
        score, status, diseases = calculate_quantum_risk(age, gender, brca1, brca2, tp53, apc, pten)
        
        if status == "High Risk": st.error(f"🚨 **HIGH RISK PROBABILITY:** Quantum Expectation is {score}%")
        elif status == "Moderate Risk": st.warning(f"⚠️ **MODERATE RISK:** Quantum Expectation is {score}%")
        else: st.success(f"✅ **LOW RISK:** Quantum Expectation is {score}%")
        
        st.divider()
        st.subheader("Quantum Entangled Conditions")
        for condition in diseases:
            st.write(f"**• {condition}**")
                
        # Save new demographic data
        new_record = {
            'date': datetime.now().strftime("%Y-%m-%d"), 'time': datetime.now().strftime("%H:%M:%S"),
            'Full Name': name.strip(), 'Age': age, 'Gender': gender, 'Blood Group': bg,
            'Height (cm)': height, 'Weight (kg)': weight, 'Ancestry': ancestry, 'Smoking': smoke,
            'brca1': brca1, 'brca2': brca2, 'tp53': tp53, 'apc': apc, 'pten': pten,
            'Risk Score': score, 'Status': status, 'Diseases': diseases
        }
        st.session_state.history_quantum_df = pd.concat([st.session_state.history_quantum_df, pd.DataFrame([new_record])], ignore_index=True)

# --- 5. RECORDS & DOWNLOADS ---
if not st.session_state.history_quantum_df.empty:
    st.divider()
    st.header("📋 Quantum Patient Records")
    display_df = st.session_state.history_quantum_df.drop(columns=['Diseases'])
    st.dataframe(display_df, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📥 Download Individual Patient Reports", expanded=True):
        st.markdown("Generate a specific Quantum Clinical PDF dosier for a single patient below:")
        st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)
        
        for idx in reversed(st.session_state.history_quantum_df.index):
            row = st.session_state.history_quantum_df.loc[idx]
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1: st.markdown(f"<div style='padding-top:10px'><b>{row['Full Name']}</b></div>", unsafe_allow_html=True)
            with col2: st.markdown(f"<div style='padding-top:10px'>Probability: {row['Risk Score']}%</div>", unsafe_allow_html=True)
            with col3: st.markdown(f"<div style='padding-top:10px'>Status: {row['Status']}</div>", unsafe_allow_html=True)
            with col4:
                single_pdf = generate_single_pdf(row)
                with open(single_pdf, "rb") as f:
                    st.download_button(
                        label="⬇ Download PDF", data=f, file_name=f"Quantum_Report_{row['Full Name'].replace(' ', '_')}_{row['date']}.pdf",
                        mime="application/pdf", key=f"dl_quantum_btn_{idx}" 
                    )
            st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)

    all_pdf = generate_all_reports_pdf(st.session_state.history_quantum_df)
    with open(all_pdf, "rb") as f:
        st.download_button("🗃️ Download All Quantum Records", data=f, file_name="All_Quantum_Records.pdf", mime="application/pdf", use_container_width=True)


# --- 6. GRAPHICAL ANALYSIS ---
if not st.session_state.history_quantum_df.empty:
    st.divider()
    
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    status_colors = {"High Risk": "#6a0dad", "Moderate Risk": "#b19cd9", "Low Risk": "#dcd0ff", "Error": "#FF0000"}
    result_colors = {"Negative": "#dcd0ff", "Positive": "#4b0082", "Inconclusive": "#999999"}

    with row1_col1:
        st.markdown("**Quantum Probabilities by Patient**")
        fig1 = px.bar(st.session_state.history_quantum_df, x="Full Name", y="Risk Score", color="Status", color_discrete_map=status_colors)
        fig1.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig1, use_container_width=True)

    with row1_col2:
        st.markdown("**Probability States Distribution**")
        fig2 = px.pie(st.session_state.history_quantum_df, names="Status", hole=0.5, color="Status", color_discrete_map=status_colors)
        fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    with row2_col1:
        # Changed this graph to measure Ancestry instead of Blood Group to match the new updates
        st.markdown("**Probability Distribution by Ancestry**")
        fig3 = px.bar(st.session_state.history_quantum_df, x="Ancestry", y="Risk Score", color="Status", color_discrete_map=status_colors)
        fig3.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig3, use_container_width=True)

    with row2_col2:
        st.markdown("**Marker State Summary**")
        markers_df = st.session_state.history_quantum_df[['brca1', 'brca2', 'tp53', 'apc', 'pten']].melt(var_name='Marker Type', value_name='Result')
        fig4 = px.histogram(markers_df, x="Marker Type", color="Result", barmode="group", color_discrete_map=result_colors)
        fig4.update_layout(yaxis_title="count", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig4, use_container_width=True)