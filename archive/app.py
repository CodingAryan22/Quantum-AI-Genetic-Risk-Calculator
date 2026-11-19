import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from fpdf import FPDF
import plotly.express as px
import tempfile
import os
import google.generativeai as genai
from PIL import Image
import json

# --- 1. SETUP & SESSION STATE ---
st.set_page_config(page_title="Hereditary Disease Prediction System", layout="wide")

EXPECTED_COLS = [
    'date', 'time', 'Full Name', 'Age', 'Gender', 'Blood Group', 
    'Height (cm)', 'Weight (kg)', 'Ancestry', 'Smoking',
    'brca1', 'brca2', 'tp53', 'apc', 'pten', 
    'Base Risk', 'Quantum Mean', 'CI_Lower', 'CI_Upper', 'Status', 'Diseases'
]

if 'history_df' not in st.session_state:
    st.session_state.history_df = pd.DataFrame(columns=EXPECTED_COLS)

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
    "input_additional_details": ""
}

for key, default_val in widget_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_val


# --- 2. CORE CLINICAL MATH & SIMULATION ---
def clear_form_data():
    for k, v in widget_defaults.items():
        st.session_state[k] = v

def clear_all_records():
    st.session_state.history_df = pd.DataFrame(columns=EXPECTED_COLS)

def sanitize_text(text):
    if not isinstance(text, str): text = str(text)
    return text.encode('ascii', 'ignore').decode('ascii')

def calculate_clinical_risk(age, gender, blood_group, brca1, brca2, tp53, apc, pten):
    """Baseline risk with uncertainty handled explicitly instead of inflating inconclusive markers."""
    base_risk = 12 + (max(0, age - 30) * 0.4)
    bg_rr = 1.0
    if blood_group in ["A+", "A-", "AB+", "AB-"]: bg_rr = 1.10
    elif blood_group in ["B+", "B-"]: bg_rr = 1.05
    personal_baseline = base_risk * bg_rr

    penetrance = {'APC': 99, 'TP53': 90, 'PTEN': 85, 'BRCA1': 72, 'BRCA2': 69}
    weights = {'APC': 5, 'TP53': 4, 'PTEN': 3, 'BRCA1': 2, 'BRCA2': 2}

    if gender == 'Male': penetrance['TP53'] = 73

    def get_marker_value(gene, state):
        if state == 'Positive':
            return penetrance[gene]
        elif state == 'Inconclusive':
            return min(personal_baseline + 5, penetrance[gene] * 0.5)
        else:
            return personal_baseline * 0.35

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


def run_quantum_simulation(base_score, iterations=1000, seed=None):
    """Simulates biological variance with a reproducible seeded RNG when provided."""
    rng = np.random.default_rng(seed)
    simulated_scores = rng.normal(loc=base_score, scale=4.5, size=iterations)
    simulated_scores = np.clip(simulated_scores, 0, 99)

    mean_score = np.mean(simulated_scores)
    ci_lower = np.percentile(simulated_scores, 5)
    ci_upper = np.percentile(simulated_scores, 95)

    return round(mean_score, 1), round(ci_lower, 1), round(ci_upper, 1)


# --- 3. PDF GENERATORS ---
def generate_single_pdf(data_row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Standard Clinical Genetic Report", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, sanitize_text(f"Patient Name: {data_row['Full Name']}"), ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, sanitize_text(f"Age: {data_row['Age']} | Gender: {data_row['Gender']} | Blood Group: {data_row['Blood Group']}"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Height: {data_row['Height (cm)']}cm | Weight: {data_row['Weight (kg)']}kg"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Ancestry: {data_row['Ancestry']} | Smoking History: {data_row['Smoking']}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Risk Assessment Results:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, sanitize_text(f"Base Deterministic Risk: {data_row['Base Risk']}%"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Quantum Simulated Mean: {data_row['Quantum Mean']}%"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"90% Confidence Interval: [{data_row['CI_Lower']}%, {data_row['CI_Upper']}%]"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Status Category: {data_row['Status']}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Detected Associated Syndromes:", ln=True)
    pdf.set_font("Arial", '', 11)
    for disease in data_row['Diseases']:
        pdf.cell(0, 6, sanitize_text(f"- {disease}"), ln=True)
            
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name


# --- 4. UI & SIDEBAR ---
st.title("🧬 Hereditary Disease Prediction System")
st.markdown("Standard Model utilizing deterministic scoring and Monte Carlo quantum simulation.")
st.markdown("<br>", unsafe_allow_html=True) 

with st.sidebar:
    # --- MISSING AUTO-FILL SECTION RESTORED ---
    try: 
        user_api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError: 
        user_api_key = None

    st.header("📄 Auto-Fill from Lab Report")
    st.write("") 
    uploaded_file = st.file_uploader("Upload Lab Report", type=["pdf", "png", "jpg", "jpeg"], key="ai_pdf_uploader")
    
    if uploaded_file and uploaded_file.name != st.session_state.get("ai_last_file", None):
        try:
            if not user_api_key: 
                st.error("⚠️ Gemini API key missing in secrets. Cannot process document.")
            else:
                with st.spinner("🤖 Extracting patient data..."):
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
                    
                    st.session_state.ai_last_file = uploaded_file.name
                    st.success("Document Processed Successfully!")
                    st.rerun() 
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    # --- END OF RESTORED SECTION ---

    # Your standard Patient Details section continues here...
    st.header("👤 Patient Details")
    st.write("") 
    name = st.text_input("Full Name", key="input_name")
    
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)

    st.header("🧬 Genetic Marker States")
    st.write("") 
    brca1 = st.selectbox("BRCA1 State", ["Positive", "Negative", "Inconclusive"], key="input_brca1")
    brca2 = st.selectbox("BRCA2 State", ["Positive", "Negative", "Inconclusive"], key="input_brca2")
    tp53 = st.selectbox("TP53 State", ["Positive", "Negative", "Inconclusive"], key="input_tp53")
    apc = st.selectbox("APC State", ["Positive", "Negative", "Inconclusive"], key="input_apc")
    pten = st.selectbox("PTEN State", ["Positive", "Negative", "Inconclusive"], key="input_pten")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)

    st.header("⚙️ Administrative")
    st.write("") 
    st.button("🧹 Clear Form", on_click=clear_form_data, use_container_width=True)
    st.button("🗑️ Clear All Records", on_click=clear_all_records, type="secondary", use_container_width=True)


# --- 5. EXECUTION ---
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

if st.button("📊 Calculate Standard Risk & Simulate", type="primary", use_container_width=True):
    
    # --- NEW VALIDATION CHECKS ---
    if not name.strip():
        st.warning("⚠️ Please enter the Patient's Full Name before running the simulation.")
        st.stop() # Halts the script so it doesn't calculate
        
    if gender == "Unknown":
        st.warning("⚠️ Please select the Patient's Gender. Gender is required for accurate BRCA and TP53 calculations.")
        st.stop()
        
    if bg == "Unknown":
        st.info("ℹ️ Note: Blood group is marked as Unknown. Proceeding with baseline risk estimates.")
    # -----------------------------

    with st.spinner("Calculating deterministic baseline and running probabilistic simulation..."):
        # 1. Classical Calculation
        base_score, status, diseases = calculate_clinical_risk(age, gender, bg, brca1, brca2, tp53, apc, pten)
        
        # 2. Quantum / Probabilistic Simulation
        q_mean, ci_lower, ci_upper = run_quantum_simulation(base_score, iterations=1500)
        
        st.markdown("<br>", unsafe_allow_html=True) 
        st.subheader("Calculation Results")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Base Deterministic Risk", f"{base_score}%")
        #col2.metric("Simulated Mean", f"{q_mean}%")
        col3.metric("90% Confidence Interval", f"[{ci_lower}%, {ci_upper}%]")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if status == "High Hereditary Risk": st.error(f"**Status:** {status}")
        elif status == "Elevated Risk": st.warning(f"**Status:** {status}")
        else: st.success(f"**Status:** {status}")
        
        st.info(f"**Associated Syndromes Detected:** {', '.join(diseases)}")
            
        new_record = {
            'date': datetime.now().strftime("%Y-%m-%d"), 'time': datetime.now().strftime("%H:%M:%S"),
            'Full Name': name.strip(), 'Age': age, 'Gender': gender, 'Blood Group': bg,
            'Height (cm)': height, 'Weight (kg)': weight, 'Ancestry': ancestry, 'Smoking': smoke,
            'brca1': brca1, 'brca2': brca2, 'tp53': tp53, 'apc': apc, 'pten': pten,
            'Base Risk': base_score, 'Quantum Mean': q_mean, 'CI_Lower': ci_lower, 'CI_Upper': ci_upper, 
            'Status': status, 'Diseases': diseases
        }
        st.session_state.history_df = pd.concat([st.session_state.history_df, pd.DataFrame([new_record])], ignore_index=True)

# ... (rest of the code continues to # --- 6. RECORDS & DASHBOARD ---)


# --- 6. RECORDS & DASHBOARD ---
if not st.session_state.history_df.empty:
    st.markdown("<br><br>", unsafe_allow_html=True) 
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.header("📋 Clinical Database")
    st.write("")
    
    display_df = st.session_state.history_df.drop(columns=['Diseases'])
    st.dataframe(display_df, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True) 
    with st.expander("📥 Download Standard Reports", expanded=False):
        for idx in reversed(st.session_state.history_df.index):
            row = st.session_state.history_df.loc[idx]
            col1, col2, col3 = st.columns([3, 3, 2])
            with col1: st.write(f"**{row['Full Name']}**")
            with col2: st.write(f"Simulated Risk: {row['Quantum Mean']}% ({row['Status']})")
            with col3:
                single_pdf = generate_single_pdf(row)
                with open(single_pdf, "rb") as f:
                    st.download_button("Download Report", data=f, file_name=f"Report_{row['Full Name'].replace(' ', '_')}.pdf", mime="application/pdf", key=f"dl_{idx}")

    st.markdown("<br><br>", unsafe_allow_html=True) 
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.header("📈 Cohort Analytics Dashboard")
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        # Using Quantum Mean for the charting instead of static base score
        fig1 = px.bar(st.session_state.history_df, x="Full Name", y="Quantum Mean", color="Status", title="Simulated Risk Scores by Patient")
        st.plotly_chart(fig1, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        fig3 = px.bar(st.session_state.history_df, x="Ancestry", y="Quantum Mean", color="Status", title="Risk Distribution by Ancestry")
        st.plotly_chart(fig3, use_container_width=True)
        
    with col2:
        fig2 = px.pie(st.session_state.history_df, names="Status", hole=0.4, title="Patient Population Risk Distribution")
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        markers = ['brca1', 'brca2', 'tp53', 'apc', 'pten']
        melted_df = st.session_state.history_df.melt(value_vars=markers, var_name='Marker', value_name='Result')
        melted_df = melted_df[melted_df['Result'] != 'Inconclusive'] 
        fig4 = px.histogram(melted_df, x="Marker", color="Result", barmode="group", title="Marker Prevalence Summary")
        st.plotly_chart(fig4, use_container_width=True)