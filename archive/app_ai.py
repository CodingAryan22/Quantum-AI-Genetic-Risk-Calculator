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
import textwrap

# --- 1. SETUP & SESSION STATE ---
st.set_page_config(page_title="AI Clinical Assistant", layout="wide")

EXPECTED_COLS = [
    'date', 'time', 'Full Name', 'Age', 'Gender', 'Blood Group', 
    'Height (cm)', 'Weight (kg)', 'Ancestry', 'Smoking',
    'brca1', 'brca2', 'tp53', 'apc', 'pten', 'Risk Score', 'Status', 'Diseases', 'AI_Report'
]

if 'history_ai_df' not in st.session_state:
    st.session_state.history_ai_df = pd.DataFrame(columns=EXPECTED_COLS)

widget_defaults = {
    "ai_input_name": "", 
    "ai_input_age": 30, 
    "ai_input_gender": "Unknown", 
    "ai_input_bg": "Unknown",
    "ai_input_height": 170,        
    "ai_input_weight": 70,         
    "ai_input_ancestry": "Unknown",
    "ai_input_smoke": "Never",     
    "ai_input_brca1": "Inconclusive", 
    "ai_input_brca2": "Inconclusive", 
    "ai_input_tp53": "Inconclusive",
    "ai_input_apc": "Inconclusive", 
    "ai_input_pten": "Inconclusive", 
    "ai_last_file": None
}

for key, default_val in widget_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_val


# --- 2. CORE CLINICAL MATH & HELPERS ---
def clear_form_data():
    for k, v in widget_defaults.items():
        st.session_state[k] = v
    if "ai_pdf_uploader" in st.session_state: 
        del st.session_state["ai_pdf_uploader"]

def clear_all_records():
    st.session_state.history_ai_df = pd.DataFrame(columns=EXPECTED_COLS)

def sanitize_text(text):
    if not isinstance(text, str): text = str(text)
    return text.encode('ascii', 'ignore').decode('ascii')

def calculate_clinical_risk(age, gender, blood_group, brca1, brca2, tp53, apc, pten):
    base_risk = 12 + (max(0, age - 30) * 0.4)
    bg_rr = 1.0
    if blood_group in ["A+", "A-", "AB+", "AB-"]: bg_rr = 1.10
    elif blood_group in ["B+", "B-"]: bg_rr = 1.05
    personal_baseline = base_risk * bg_rr

    penetrance = {'APC': 99, 'TP53': 90, 'PTEN': 85, 'BRCA1': 72, 'BRCA2': 69}
    weights = {'APC': 5, 'TP53': 4, 'PTEN': 3, 'BRCA1': 2, 'BRCA2': 2}
    
    if gender == 'Male': penetrance['TP53'] = 73
        
    def get_marker_value(gene, state):
        if state == 'Positive': return penetrance[gene]
        elif state == 'Inconclusive': return personal_baseline + 10 
        else: return personal_baseline 
        
    val_apc = get_marker_value('APC', apc)
    val_tp53 = get_marker_value('TP53', tp53)
    val_pten = get_marker_value('PTEN', pten)
    val_brca1 = get_marker_value('BRCA1', brca1)
    val_brca2 = get_marker_value('BRCA2', brca2)
    
    numerator = (val_apc * weights['APC']) + (val_tp53 * weights['TP53']) + (val_pten * weights['PTEN']) + (val_brca1 * weights['BRCA1']) + (val_brca2 * weights['BRCA2'])
    denominator = sum(weights.values()) 
    score = int(numerator / denominator)
    score = min(score, 99) 
    
    if score >= 45: status = "High Hereditary Risk"
    elif score >= 20: status = "Elevated Risk"
    else: status = "Average Population Risk"
    
    diseases = []
    if brca1 == 'Positive' or brca2 == 'Positive': 
        if gender == 'Male': diseases.append("HBOC Syndrome (Male Profile)")
        else: diseases.append("Hereditary Breast and Ovarian Cancer (HBOC)")
    if tp53 == 'Positive': diseases.append("Li-Fraumeni Syndrome (LFS)")
    if apc == 'Positive': diseases.append("Familial Adenomatous Polyposis (FAP)")
    if pten == 'Positive': diseases.append("Cowden Syndrome")
    if not diseases: diseases.append("No primary pathogenic variants detected.")
        
    return score, status, diseases

# --- 3. AI REPORT GENERATION ---
def generate_ai_report(api_key, name, age, gender, bg, height, weight, ancestry, smoke, brca1, brca2, tp53, apc, pten, score, status, diseases):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are an expert, empathetic genetic counselor. I have calculated the clinical lifetime cancer risk for a patient using an epidemiological model.
    
    Patient Data:
    - Name: {name if name else 'Patient'}
    - Age/Gender: {age}, {gender}
    - Ancestry: {ancestry}
    - Blood Group: {bg}
    - Height/Weight: {height} cm, {weight} kg
    - Smoking History: {smoke}
    
    Genetic Panel Results:
    - BRCA1: {brca1}
    - BRCA2: {brca2}
    - TP53: {tp53}
    - APC: {apc}
    - PTEN: {pten}
    
    Mathematical Output (Already Calculated):
    - Lifetime Risk Score: {score}%
    - Risk Category: {status}
    - Associated Syndromes: {', '.join(diseases)}
    
    Please write a comprehensive, patient-friendly clinical report. 
    1. Start with an empathetic but professional summary of the patient's baseline profile (factor in their lifestyle/ancestry if relevant).
    2. Explain what their specific calculated risk score ({score}%) and status ({status}) mean in plain English.
    3. Discuss their specific genetic markers. Explain positive markers and associated syndromes, or explain Variants of Uncertain Significance (VUS) for inconclusive ones.
    4. Provide 3-4 highly actionable next steps (e.g., screening schedules, lifestyle changes).
    5. Conclude with a medical disclaimer noting this is an AI-generated academic prototype and not a substitute for a doctor.
    
    Use clear text. Do not use complex markdown tables or excessive symbols.
    """
    response = model.generate_content(prompt)
    return response.text

# --- 4. PDF GENERATORS ---
def generate_single_ai_pdf(data_row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "AI-Generated Clinical Genetic Report", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, sanitize_text(f"Patient Name: {data_row['Full Name']} (Age: {data_row['Age']} | Gen: {data_row['Gender']} | Ancestry: {data_row['Ancestry']})"), ln=True)
    pdf.cell(0, 8, sanitize_text(f"Calculated Lifetime Risk: {data_row['Risk Score']}% ({data_row['Status']})"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 11)
    
    clean_text = data_row.get('AI_Report', 'No report available.')
    clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')
    clean_text = clean_text.replace('*', '').replace('#', '').replace('_', '')
    
    paragraphs = clean_text.split('\n')
    for p in paragraphs:
        p = p.strip()
        if p:
            wrapped_lines = textwrap.wrap(p, width=95)
            for w_line in wrapped_lines:
                pdf.cell(0, 6, w_line, ln=True)
        else:
            pdf.ln(3) 
            
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

def generate_all_ai_reports_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Master AI Consultation Records", ln=True, align="C")
    pdf.ln(10)
    for index, row in df.iterrows():
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 6, sanitize_text(f"Patient: {row['Full Name']} (Age: {row['Age']}, Gender: {row['Gender']})"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, sanitize_text(f"Calculated Risk: {row['Risk Score']}% | Status: {row['Status']}"), ln=True)
        pdf.ln(4)
        pdf.cell(0, 0, "", "T")
        pdf.ln(4)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name


# --- 5. UI & SIDEBAR ---
st.title("AI Clinical Genetics Counselor")
st.markdown("Combines rigorous mathematical risk calculation with empathetic, AI-driven patient communication.")
st.markdown("<br>", unsafe_allow_html=True) 

try: 
    user_api_key = st.secrets["GEMINI_API_KEY"]
except KeyError: 
    user_api_key = None

with st.sidebar:
    st.header("📄 Auto-Fill from Lab Report")
    st.write("") 
    uploaded_file = st.file_uploader("Upload Lab Report", type=["pdf", "png", "jpg", "jpeg"], key="ai_pdf_uploader")
    
    if uploaded_file and uploaded_file.name != st.session_state.ai_last_file:
        try:
            if not user_api_key: 
                st.error("⚠️ Gemini API key missing. Cannot process document.")
            else:
                with st.spinner("Extracting patient data..."):
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
                    else:
                        image = Image.open(uploaded_file)
                        response = model.generate_content([prompt, image])
                    
                    clean_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                    data = json.loads(clean_json)
                    
                    st.session_state.ai_input_name = data.get("Name", "")
                    st.session_state.ai_input_age = int(data.get("Age", 30)) if str(data.get("Age")).isdigit() else 30
                    g_val = data.get("Gender", "Unknown")
                    st.session_state.ai_input_gender = g_val if g_val in ["Male", "Female", "Other"] else "Unknown"
                    b_val = data.get("Blood Group", "Unknown")
                    st.session_state.ai_input_bg = b_val if b_val in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] else "Unknown"
                    
                    st.session_state.ai_input_brca1 = data.get("BRCA1", "Inconclusive")
                    st.session_state.ai_input_brca2 = data.get("BRCA2", "Inconclusive")
                    st.session_state.ai_input_tp53 = data.get("TP53", "Inconclusive")
                    st.session_state.ai_input_apc = data.get("APC", "Inconclusive")
                    st.session_state.ai_input_pten = data.get("PTEN", "Inconclusive")
                    
                    st.session_state.ai_last_file = uploaded_file.name
                    st.success("Document Processed Successfully!")
                    st.rerun() 
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.header("👤 Patient Details")
    st.write("") 
    name = st.text_input("Full Name", key="ai_input_name")
    
    colA, colB = st.columns(2)
    with colA:
        age = st.slider("Age", 1, 100, key="ai_input_age")
        height = st.number_input("Height (cm)", 100, 250, key="ai_input_height")
        bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"], key="ai_input_bg")
    with colB:
        gender = st.selectbox("Gender", ["Male", "Female", "Other", "Unknown"], key="ai_input_gender")
        weight = st.number_input("Weight (kg)", 30, 200, key="ai_input_weight")
        ancestry = st.selectbox("Ancestry", ["Unknown", "European", "Ashkenazi Jewish", "Asian", "African", "Hispanic", "Mixed"], key="ai_input_ancestry")
        
    st.write("")
    smoke = st.selectbox("Smoking History", ["Never", "Former Smoker", "Current Smoker"], key="ai_input_smoke")

    st.write("")
    additional_details = st.text_area("Additional Details (Optional)", key="input_additional_details", height=80)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)

    st.header("🧬 Genetic Marker States")
    st.write("") 
    brca1 = st.selectbox("BRCA1 State", ["Positive", "Negative", "Inconclusive"], key="ai_input_brca1")
    brca2 = st.selectbox("BRCA2 State", ["Positive", "Negative", "Inconclusive"], key="ai_input_brca2")
    tp53 = st.selectbox("TP53 State", ["Positive", "Negative", "Inconclusive"], key="ai_input_tp53")
    apc = st.selectbox("APC State", ["Positive", "Negative", "Inconclusive"], key="ai_input_apc")
    pten = st.selectbox("PTEN State", ["Positive", "Negative", "Inconclusive"], key="ai_input_pten")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)

    st.header("⚙️ Administrative")
    st.write("") 
    st.button("🧹 Clear Form", on_click=clear_form_data, use_container_width=True)
    st.button("🗑️ Clear All Records", on_click=clear_all_records, type="secondary", use_container_width=True)


# --- 6. EXECUTION ---
st.markdown("<br>", unsafe_allow_html=True) 

st.markdown("""
    <style>
    button[kind="primary"] {
        height: 70px;
        font-size: 24px !important;
        font-weight: bold !important;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

if st.button("Generate AI Patient Report", type="primary", use_container_width=True):
    
    # --- NEW VALIDATION CHECKS ---
    if not name.strip():
        st.warning("⚠️ Please enter the Patient's Full Name before generating the report.")
        st.stop() # Halts the script so it doesn't process blank data
        
    if gender == "Unknown":
        st.warning("⚠️ Please select the Patient's Gender. Gender is strongly required for accurate BRCA and TP53 calculations.")
        st.stop()
        
    if bg == "Unknown":
        st.info("ℹ️ Note: Blood group is marked as Unknown. Proceeding with baseline risk estimates.")
    # -----------------------------

    if not user_api_key:
        st.error("⚠️ Please configure your GEMINI_API_KEY in the secrets to generate AI reports.")
    else:
        with st.spinner("1. Calculating mathematical risk model..."):
            score, status, diseases = calculate_clinical_risk(age, gender, bg, brca1, brca2, tp53, apc, pten)
        
        with st.spinner("2. AI synthesizing clinical report..."):
            try:
                # Passing the new variables to the AI
                ai_report = generate_ai_report(
                    user_api_key, name, age, gender, bg, height, weight, ancestry, smoke, 
                    brca1, brca2, tp53, apc, pten, score, status, diseases
                )
                
                st.markdown("<br>", unsafe_allow_html=True) 
                st.subheader("Calculation Summary")
                if status == "High Hereditary Risk": st.error(f"**Status:** {status} | **Lifetime Risk:** {score}%")
                elif status == "Elevated Risk": st.warning(f"**Status:** {status} | **Lifetime Risk:** {score}%")
                else: st.success(f"**Status:** {status} | **Lifetime Risk:** {score}%")
                st.markdown("<br>", unsafe_allow_html=True) 
                
                st.success("Detailed Report Generated Below")
                with st.container(border=True):
                    st.markdown(ai_report)
                    
                new_record = {
                    'date': datetime.now().strftime("%Y-%m-%d"), 'time': datetime.now().strftime("%H:%M:%S"),
                    'Full Name': name.strip(), 'Age': age, 'Gender': gender, 'Blood Group': bg,
                    'Height (cm)': height, 'Weight (kg)': weight, 'Ancestry': ancestry, 'Smoking': smoke,
                    'brca1': brca1, 'brca2': brca2, 'tp53': tp53, 'apc': apc, 'pten': pten,
                    'Risk Score': score, 'Status': status, 'Diseases': diseases, 'AI_Report': ai_report
                }
                st.session_state.history_ai_df = pd.concat([st.session_state.history_ai_df, pd.DataFrame([new_record])], ignore_index=True)
                
            except Exception as e:
                st.error(f"Error generating AI report: {e}")


# --- 7. RECORDS & DASHBOARD ---
if not st.session_state.history_ai_df.empty:
    st.markdown("<br><br>", unsafe_allow_html=True) 
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.header("📋 AI Consultation Database")
    st.write("")
    
    # Hide the long text columns from the main dashboard view to keep it clean
    display_df = st.session_state.history_ai_df.drop(columns=['Diseases', 'AI_Report'])
    st.dataframe(display_df, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True) 
    with st.expander("📥 Download AI Consultation Reports", expanded=False):
        for idx in reversed(st.session_state.history_ai_df.index):
            row = st.session_state.history_ai_df.loc[idx]
            col1, col2, col3 = st.columns([3, 3, 2])
            with col1: st.write(f"**{row['Full Name']}**")
            with col2: st.write(f"Risk: {row['Risk Score']}% ({row['Status']})")
            with col3:
                single_pdf = generate_single_ai_pdf(row)
                with open(single_pdf, "rb") as f:
                    st.download_button("Download Full Report", data=f, file_name=f"AI_Report_{row['Full Name'].replace(' ', '_')}.pdf", mime="application/pdf", key=f"dl_ai_{idx}")

    st.markdown("<br>", unsafe_allow_html=True)
    all_pdf = generate_all_ai_reports_pdf(st.session_state.history_ai_df)
    with open(all_pdf, "rb") as f:
        st.download_button("🗃️ Download Master AI Database PDF", data=f, file_name="Master_AI_Consultations.pdf", mime="application/pdf", use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True) 
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.header("📈 AI Cohort Analytics Dashboard")
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(st.session_state.history_ai_df, x="Full Name", y="Risk Score", color="Status", title="Risk Scores by Patient")
        st.plotly_chart(fig1, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        fig3 = px.bar(st.session_state.history_ai_df, x="Ancestry", y="Risk Score", color="Status", title="Risk Distribution by Ancestry")
        st.plotly_chart(fig3, use_container_width=True)
        
    with col2:
        fig2 = px.pie(st.session_state.history_ai_df, names="Status", hole=0.4, title="Patient Population Risk Distribution")
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        markers = ['brca1', 'brca2', 'tp53', 'apc', 'pten']
        melted_df = st.session_state.history_ai_df.melt(value_vars=markers, var_name='Marker', value_name='Result')
        melted_df = melted_df[melted_df['Result'] != 'Inconclusive'] 
        fig4 = px.histogram(melted_df, x="Marker", color="Result", barmode="group", title="Marker Prevalence Summary")
        st.plotly_chart(fig4, use_container_width=True)