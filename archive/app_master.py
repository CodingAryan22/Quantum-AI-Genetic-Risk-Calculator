import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import PyPDF2
import re
import plotly.express as px
import tempfile
import os
import random
import google.generativeai as genai
from PIL import Image
import json

# --- MACHINE LEARNING & QUANTUM IMPORTS ---
from sklearn.ensemble import RandomForestRegressor
from qiskit.circuit.library import ZZFeatureMap
from qiskit_machine_learning.algorithms import QSVR
from qiskit_machine_learning.kernels import FidelityQuantumKernel

# --- 1. MODEL TRAINING & LOADING (Caches so it only runs once) ---

@st.cache_resource
def train_ai_model():
    """Trains a Random Forest model on 2000 synthetic clinical records."""
    X, y = [], []
    for _ in range(2000):
        age = random.randint(1, 100)
        gender = random.choice([0, 1]) 
        brca1, brca2, tp53, apc, pten = [random.choice([0, 1]) for _ in range(5)]
        
        # Standard Classical Logic
        risk = 5
        if brca1: risk += 25
        if brca2: risk += 20
        if tp53: risk += 30
        if apc: risk += 25
        if pten: risk += 20
        if age > 60: risk += 15
        elif age > 40: risk += 8
        if gender == 1 and (brca1 or brca2): risk += 8
        
        X.append([age, gender, brca1, brca2, tp53, apc, pten])
        y.append(min(100, risk))
        
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(np.array(X), np.array(y))
    return model

@st.cache_resource
def train_quantum_model():
    """Trains a Quantum SVR on a small subset (100 records) due to compute limits."""
    X, y = [], []
    for _ in range(100):
        age = random.randint(1, 100)
        gender = random.choice([0, 1]) 
        brca1, brca2, tp53, apc, pten = [random.choice([0, 1]) for _ in range(5)]
        
        risk = 5
        if brca1: risk += 25
        if brca2: risk += 20
        if tp53: risk += 30
        if apc: risk += 25
        if pten: risk += 20
        if age > 60: risk += 15
        elif age > 40: risk += 8
        if gender == 1 and (brca1 or brca2): risk += 8
        
        age_norm = age / 100.0
        X.append([age_norm, gender, brca1, brca2, tp53, apc, pten])
        y.append(min(100, risk))

    feature_map = ZZFeatureMap(feature_dimension=7, reps=1)
    q_kernel = FidelityQuantumKernel(feature_map=feature_map)
    q_model = QSVR(quantum_kernel=q_kernel)
    q_model.fit(np.array(X), np.array(y))
    return q_model

# Load the Brains!
with st.spinner("🧠 Initializing Models... (Quantum Simulator may take 15-30 seconds)"):
    ai_model = train_ai_model()
    quantum_model = train_quantum_model()

def calculate_standard_risk(age, gender, brca1, brca2, tp53, apc, pten):
    """The hardcoded classical IF/THEN clinical logic."""
    risk = 5
    if brca1: risk += 25
    if brca2: risk += 20
    if tp53: risk += 30
    if apc: risk += 25
    if pten: risk += 20
    if age > 60: risk += 15
    elif age > 40: risk += 8
    if gender == 1 and (brca1 or brca2): risk += 8
    return min(100, risk)

# --- 2. HELPERS & SAFETY NETS ---
def get_safe_val(data, key, default="N/A"):
    if isinstance(data, (dict, pd.Series)): return data.get(key, default)
    return default

def clear_dashboard():
    """Clears both the form inputs AND the live analytics dashboard."""
    keys = ["form_name", "form_age", "form_gender", "form_bg", "form_brca1", "form_brca2", "form_tp53", "form_apc", "form_pten", "last_file"]
    defaults = ["", 30, "Unknown", "Unknown", "Inconclusive", "Inconclusive", "Inconclusive", "Inconclusive", "Inconclusive", None]
    for k, d in zip(keys, defaults): st.session_state[k] = d
    st.session_state.current_results = None  # Wipes the dashboard
    if "pdf_uploader" in st.session_state: del st.session_state["pdf_uploader"]

# --- 3. UI SETUP & SESSION STATE ---
st.set_page_config(page_title="Master Cancer Predictor", layout="wide")
st.markdown("""<style>div.stButton > button[kind="primary"] { padding: 1.5rem 2rem; font-size: 22px; font-weight: bold; }</style>""", unsafe_allow_html=True)
st.title("🏆 Master Hereditary Cancer Prediction Dashboard")
st.caption("Comparing Classical Standard, Machine Learning, and Quantum Computing Models")

EXPECTED_COLS = ['date', 'time', 'Full Name', 'Age', 'Gender', 'Blood Group', 'brca1', 'brca2', 'tp53', 'apc', 'pten', 'Std Score', 'AI Score', 'Quantum Score', 'Status']

# Changed from history_df to current_results
if 'current_results' not in st.session_state: st.session_state.current_results = None
if "form_name" not in st.session_state: clear_dashboard()

# --- 4. SIDEBAR: AUTO-FILL & INPUT ---
with st.sidebar:
    try: user_api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError: 
        st.error("API Key not found in secrets.toml!")
        user_api_key = None
    
    st.divider()
    st.header("📄 Auto-Fill from Report")
    uploaded_file = st.file_uploader("Upload Lab Report (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"], key="pdf_uploader")
    
    if uploaded_file and uploaded_file.name != st.session_state.last_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PyPDF2.PdfReader(uploaded_file)
                text = "".join([page.extract_text() for page in reader.pages])
                
                name_m = re.search(r"(?i)(?:Nam\s*e|Name|Patient)\s*[:\-]?\s*(.*?)(?=\s*Age|\s*Blood|\n|$)", text)
                if name_m: st.session_state.form_name = re.sub(r'\b([A-Za-z])\s+([a-z]+)\b', r'\1\2', name_m.group(1).strip())
                
                age_m = re.search(r"(?i)Age\s*[:\-]?\s*(\d+)", text)
                if age_m: st.session_state.form_age = int(age_m.group(1))
                
                gender_m = re.search(r"(?i)(?:Sex|Gender)\s*[:\-]?\s*(Male|Female|M|F|Other)", text)
                if gender_m:
                    g_val = gender_m.group(1).upper()
                    st.session_state.form_gender = "Male" if g_val.startswith('M') else "Female" if g_val.startswith('F') else "Other"

                bg_m = re.search(r"(?i)Blood\s*Group\s*[:\-]?\s*(A|B|AB|O)\s*([\+\-])", text)
                if bg_m: st.session_state.form_bg = f"{bg_m.group(1).upper()}{bg_m.group(2)}"

                def extract_marker(pattern, text_data):
                    match = re.search(pattern, text_data)
                    if match:
                        line = match.group(0).lower()
                        if any(w in line for w in ["pos", "mut", "detect"]): return "Positive"
                        if any(w in line for w in ["neg", "normal", "not detect"]): return "Negative"
                    return "Inconclusive"

                st.session_state.form_brca1 = extract_marker(r"(?i)BRCA[- ]?1[^\n]*", text)
                st.session_state.form_brca2 = extract_marker(r"(?i)BRCA[- ]?2[^\n]*", text)
                st.session_state.form_tp53 = extract_marker(r"(?i)TP[- ]?53[^\n]*", text)
                st.session_state.form_apc = extract_marker(r"(?i)APC[^\n]*", text)
                st.session_state.form_pten = extract_marker(r"(?i)PTEN[^\n]*", text)
                
                st.session_state.last_file = uploaded_file.name
                st.success("PDF Processed Successfully!")

            elif uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                if not user_api_key:
                    st.error("⚠️ Gemini API key missing.")
                else:
                    with st.spinner("🤖 Gemini Vision is reading..."):
                        genai.configure(api_key=user_api_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        image = Image.open(uploaded_file)
                        prompt = """Extract: "Name", "Age" (int), "Gender" ("Male", "Female", "Other"), "Blood Group". 
                                  For BRCA1, BRCA2, TP53, APC, PTEN use ONLY "Positive", "Negative", or "Inconclusive". Return valid JSON only."""
                        response = model.generate_content([prompt, image])
                        
                        try:
                            clean_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                            data = json.loads(clean_json)
                            
                            st.session_state.form_name = data.get("Name", "")
                            st.session_state.form_age = int(data.get("Age", 30)) if str(data.get("Age")).isdigit() else 30
                            st.session_state.form_gender = data.get("Gender", "Unknown")
                            st.session_state.form_bg = data.get("Blood Group", "Unknown")
                            st.session_state.form_brca1 = data.get("BRCA1", "Inconclusive")
                            st.session_state.form_brca2 = data.get("BRCA2", "Inconclusive")
                            st.session_state.form_tp53 = data.get("TP53", "Inconclusive")
                            st.session_state.form_apc = data.get("APC", "Inconclusive")
                            st.session_state.form_pten = data.get("PTEN", "Inconclusive")
                            
                            st.session_state.last_file = uploaded_file.name
                            st.success("Image Processed!")
                        except:
                            st.error("Parse failed. Try clearer image.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.header("👤 Patient Details")
    name = st.text_input("Full Name", key="form_name")
    age = st.slider("Age", 1, 100, key="form_age")
    gender = st.selectbox("Gender", ["Male", "Female", "Other", "Unknown"], key="form_gender")
    blood_group = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"], key="form_bg")
    
    st.divider()
    st.header("🧬 Genetic Markers")
    brca1 = st.selectbox("BRCA1", ["Positive", "Negative", "Inconclusive"], key="form_brca1")
    brca2 = st.selectbox("BRCA2", ["Positive", "Negative", "Inconclusive"], key="form_brca2")
    tp53 = st.selectbox("TP53", ["Positive", "Negative", "Inconclusive"], key="form_tp53")
    apc = st.selectbox("APC", ["Positive", "Negative", "Inconclusive"], key="form_apc")
    pten = st.selectbox("PTEN", ["Positive", "Negative", "Inconclusive"], key="form_pten")

    st.divider()
    st.header("⚙️ Administrative Functions")
    # New combined clear button
    st.button("🧹 Clear Patient & Dashboard", on_click=clear_dashboard, use_container_width=True)

# --- 5. THE MASTER ENGINE ---
if st.button("🚀 RUN MASTER ANALYSIS", type="primary", use_container_width=True):
    if name.strip() == "" and age == 30 and gender == "Unknown" and brca1 == "Inconclusive":
        st.error("⚠️ No data entered!")
    else:
        # Prepare binary features
        bin_gender = 1 if gender == "Female" else 0
        bin_b1 = 1 if brca1 == "Positive" else 0
        bin_b2 = 1 if brca2 == "Positive" else 0
        bin_t53 = 1 if tp53 == "Positive" else 0
        bin_apc = 1 if apc == "Positive" else 0
        bin_pten = 1 if pten == "Positive" else 0
        
        col1, col2, col3 = st.columns(3)
        
        # --- MODEL 1: STANDARD CLASSICAL ---
        with col1:
            st.subheader("🏥 Standard Logic")
            start_t = time.time()
            std_score = calculate_standard_risk(age, bin_gender, bin_b1, bin_b2, bin_t53, bin_apc, bin_pten)
            std_time = time.time() - start_t
            st.metric(label="Calculated Risk", value=f"{std_score}%")
            st.caption(f"⏱️ Executed in {std_time:.4f} sec")

        # --- MODEL 2: AI MACHINE LEARNING ---
        with col2:
            st.subheader("🧠 Machine Learning")
            start_t = time.time()
            ai_features = np.array([[age, bin_gender, bin_b1, bin_b2, bin_t53, bin_apc, bin_pten]])
            raw_ai = ai_model.predict(ai_features)[0]
            if brca1 == "Inconclusive": raw_ai += 2
            if brca2 == "Inconclusive": raw_ai += 2
            ai_score = round(min(100, max(0, raw_ai)))
            ai_time = time.time() - start_t
            st.metric(label="AI Predicted Risk", value=f"{ai_score}%")
            st.caption(f"⏱️ Executed in {ai_time:.4f} sec")

        # --- MODEL 3: QUANTUM SIMULATOR ---
        with col3:
            st.subheader("⚛️ Quantum SVR")
            start_t = time.time()
            q_features = np.array([[age/100.0, bin_gender, bin_b1, bin_b2, bin_t53, bin_apc, bin_pten]])
            try:
                raw_q = quantum_model.predict(q_features)[0]
            except:
                raw_q = 50
            q_score = round(min(100, max(0, raw_q)))
            q_time = time.time() - start_t
            st.metric(label="Quantum Risk", value=f"{q_score}%")
            st.caption(f"⏱️ Executed in {q_time:.4f} sec")

        # Save to Current Results (Overwrites instead of appending)
        final_status = "High Risk" if ai_score >= 55 else "Moderate Risk" if ai_score >= 25 else "Low Risk"
        new_data = {
            'date': datetime.now().strftime("%Y-%m-%d"), 'time': datetime.now().strftime("%H:%M:%S"),
            'Full Name': name if name.strip() else "Unknown", 'Age': age, 'Gender': gender, 'Blood Group': blood_group,
            'brca1': brca1, 'brca2': brca2, 'tp53': tp53, 'apc': apc, 'pten': pten,
            'Std Score': std_score, 'AI Score': ai_score, 'Quantum Score': q_score, 'Status': final_status
        }
        st.session_state.current_results = pd.DataFrame([new_data])[EXPECTED_COLS]
        st.success("✅ Master Analysis Complete!")

# --- 6. LIVE ANALYTICS ---
if st.session_state.current_results is not None:
    st.divider()
    st.header("📊 Live Model Comparison")
    
    # Show the single record
    st.dataframe(st.session_state.current_results, use_container_width=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Focused Discrepancy Chart
    patient_data = st.session_state.current_results.iloc[0]
    chart_data = pd.DataFrame({
        "Model Type": ["Standard (Clinical)", "AI (Random Forest)", "Quantum (QSVR)"],
        "Risk Score": [patient_data["Std Score"], patient_data["AI Score"], patient_data["Quantum Score"]]
    })
    
    st.subheader(f"⚖️ Model Discrepancy Analysis for: {patient_data['Full Name']}")
    
    # Create a nice colored bar chart with text labels outside the bars
    fig = px.bar(chart_data, x="Model Type", y="Risk Score", color="Model Type", 
                 range_y=[0, 100], text="Risk Score",
                 color_discrete_sequence=["#3366CC", "#109618", "#990099"])
    fig.update_traces(textposition='outside', textfont_size=14)
    st.plotly_chart(fig, use_container_width=True)