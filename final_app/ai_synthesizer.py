import streamlit as st
import google.generativeai as genai
import os

def configure_api():
    """
    Attempts to load the Gemini API key from Streamlit secrets or local environment variables.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def generate_report(patient_data: dict, risk_table) -> str:
    """
    Generates an educational clinical summary explaining detected disease risks 
    and providing actionable remedial or medical advice based on risk severity.
    """
    if not configure_api():
        return "⚠️ **System Notice:** API key not found. Please configure your GEMINI_API_KEY in Streamlit secrets to enable AI Synthesis."

    # Extract numerical risk value
    simulated_mean_str = risk_table["Simulated Mean"].iloc[0]
    simulated_mean_val = float(simulated_mean_str.replace("%", ""))
    ci_range = risk_table["90% Confidence Interval"].iloc[0]

    # Map genetic markers to clinical descriptions
    genetics = patient_data.get("Genetic Markers", {})
    positive_markers = [marker for marker, present in genetics.items() if present]
    
    marker_descriptions = []
    if "BRCA1" in positive_markers:
        marker_descriptions.append("BRCA1 (Associated with elevated risk of hereditary Breast and Ovarian Cancers)")
    if "BRCA2" in positive_markers:
        marker_descriptions.append("BRCA2 (Associated with elevated risk of Breast, Ovarian, and Prostate Cancers)")
    if "APC" in positive_markers:
        marker_descriptions.append("APC (Associated with Familial Adenomatous Polyposis & Colorectal Cancer risk)")
    if "TP53" in positive_markers:
        marker_descriptions.append("TP53 (Associated with Li-Fraumeni Syndrome and multiple multi-organ cancer risks)")
    
    markers_text = "\n".join([f"- {desc}" for desc in marker_descriptions]) if marker_descriptions else "No high-risk targeted gene mutations detected."

    # Classify Risk Level for Prompt Context
    if simulated_mean_val >= 50.0:
        risk_tier = "HIGH RISK"
    elif simulated_mean_val >= 20.0:
        risk_tier = "MODERATE / CONCERNING RISK"
    else:
        risk_tier = "LOW RISK"

    # Crafting the targeted prompt
    prompt = f"""
    You are an expert clinical genetic assistant communicating directly with a patient.
    Provide an informative, empathetic clinical narrative explaining their risk evaluation.

    PATIENT CONTEXT:
    - Patient Name: {patient_data.get('Name', 'Patient')}
    - Calculated Quantum Risk Mean: {simulated_mean_val}% ({risk_tier})
    - 90% Confidence Interval: {ci_range}
    - Flagged Genetic Mutations:
    {markers_text}
    - Lifestyle / Notes: Smoking Status: {patient_data.get('Smoking History', 'N/A')}. Additional Notes: {patient_data.get('Additional Details', 'None')}.

    OUTPUT INSTRUCTIONS:
    Write a concise 2-paragraph response following this structure:

    Paragraph 1 (Disease & Marker Information):
    - Explain what the identified genetic mutations (or lifestyle risk factors) mean in plain, supportive terms. 
    - Describe the specific medical conditions associated with these genes so the patient understands why their risk score is at {simulated_mean_val}%.

    Paragraph 2 (Tiered Action Plan & Guidance):
    - IF HIGH RISK (>= 50%): Strongly and immediately urge the patient to schedule a comprehensive clinical evaluation with a specialist (Oncologist, Medical Geneticist, or Genetic Counselor) for diagnostic testing and formal management. Do not try to offer DIY remedies for high risk.
    - IF MODERATE / CONCERNING RISK (20% - 49.9%): Provide practical remedial steps and preventive care strategies (e.g., targeted routine screenings like colonoscopies/mammograms, lifestyle/diet adjustments, smoking cessation, and consulting a primary physician).
    - IF LOW RISK (< 20%): Reassure the patient while encouraging standard health maintenance, balanced lifestyle choices, and routine annual checkups.

    Do not repeat the raw math metrics in a robotic way. Focus on education and clear next steps.
    """

    model = genai.GenerativeModel('gemini-2.5-flash')

    try:
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            return "⚠️ **API Rate Limit Reached:** You have exceeded the free tier quota. Please wait 60 seconds and try again."
        else:
            return f"⚠️ **AI Synthesis Error:** Unable to generate report at this time. ({error_msg})"