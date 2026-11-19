import os
import re

import google.generativeai as genai
import streamlit as st

try:
    from features import positive_markers
except ModuleNotFoundError:  # imported as final_app.ai_synthesizer
    from .features import positive_markers

MARKER_INFO = {
    "BRCA1": "BRCA1 (associated with elevated risk of hereditary breast and ovarian cancers)",
    "BRCA2": "BRCA2 (associated with elevated risk of breast, ovarian and prostate cancers)",
    "APC": "APC (associated with familial adenomatous polyposis and colorectal cancer risk)",
    "TP53": "TP53 (associated with Li-Fraumeni syndrome and risk of many cancer types)",
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_LONG_ID = re.compile(r"\b[A-Z]{0,4}\d{6,}\b")


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


def deidentify(text: str, name: str = "") -> str:
    """
    Removes direct identifiers from free text before it leaves the app:
    the patient's name (full and each part), email addresses, phone numbers
    and long ID-like numbers (MRNs, Aadhaar/SSN-style numbers).
    """
    if not text:
        return ""
    # Patterns first: replacing the name first would break up e.g. "priya.s@mail.com".
    text = _EMAIL.sub("[email removed]", text)
    text = _PHONE.sub("[phone removed]", text)
    text = _LONG_ID.sub("[ID removed]", text)
    for part in sorted({name.strip(), *name.split()}, key=len, reverse=True):
        if len(part) >= 2:
            text = re.sub(rf"\b{re.escape(part)}\b", "the patient", text, flags=re.I)
    return text


def _age_band(age) -> str:
    """Sends a 10-year band instead of the exact age."""
    try:
        decade = int(float(age)) // 10 * 10
    except (TypeError, ValueError):
        return "not given"
    return f"{decade}-{decade + 9}"


def build_prompt(patient_data: dict, risk_table, model_predictions: dict | None = None) -> str:
    """
    Builds the Gemini prompt from de-identified data only: no name, an age band
    instead of the exact age, and identifiers scrubbed from the free-text notes.
    """
    simulated_mean_val = float(risk_table["Simulated Mean"].iloc[0].replace("%", ""))
    ci_range = risk_table["90% Confidence Interval"].iloc[0]

    marker_descriptions = [MARKER_INFO[m] for m in positive_markers(patient_data) if m in MARKER_INFO]
    for marker in patient_data.get("Other Genetic Markers", []):
        marker_descriptions.append(
            f"{deidentify(str(marker), patient_data.get('Name') or '')} (reported by the clinician; "
            "not included in the numeric risk score - explain its general significance if it is "
            "a recognised gene)"
        )
    markers_text = (
        "\n".join(f"    - {d}" for d in marker_descriptions)
        if marker_descriptions else "    No high-risk targeted gene mutations detected."
    )

    family = patient_data.get("Family History", {}) or {}
    family_text = (
        f"{family.get('First-degree', 0)} first-degree and "
        f"{family.get('Second-degree', 0)} second-degree relatives with cancer"
    )

    models_text = ""
    if model_predictions:
        lines = "\n".join(f"    - {k}: {v * 100:.0f}%" for k, v in model_predictions.items())
        models_text = (
            "\n    - Machine-learning models (20-year risk, trained on synthetic data):\n" + lines
        )

    if simulated_mean_val >= 50.0:
        risk_tier = "HIGH RISK"
    elif simulated_mean_val >= 20.0:
        risk_tier = "MODERATE / CONCERNING RISK"
    else:
        risk_tier = "LOW RISK"

    notes = deidentify(patient_data.get("Additional Details") or "", patient_data.get("Name") or "")

    return f"""
    You are an expert clinical genetic assistant communicating directly with a patient.
    Provide an informative, empathetic clinical narrative explaining their risk evaluation.
    Address the reader as "you". Do not invent or use a name.

    PATIENT CONTEXT (de-identified):
    - Age band: {_age_band(patient_data.get('Age'))}; sex: {patient_data.get('Gender', 'not given')}
    - Rule-based risk score with Monte Carlo uncertainty: {simulated_mean_val}% ({risk_tier})
    - 90% Confidence Interval: {ci_range}{models_text}
    - Flagged Genetic Mutations:
{markers_text}
    - Family history: {family_text}
    - Lifestyle / Notes: Smoking Status: {patient_data.get('Smoking History', 'N/A')}. Additional Notes: {notes or 'None'}.

    OUTPUT INSTRUCTIONS:
    Write a concise 2-paragraph response following this structure:

    Paragraph 1 (Disease & Marker Information):
    - Explain what the identified genetic mutations, family history or lifestyle risk factors mean in plain, supportive terms.
    - Describe the specific medical conditions associated with these genes so the patient understands why their risk score is at {simulated_mean_val}%.

    Paragraph 2 (Tiered Action Plan & Guidance):
    - IF HIGH RISK (>= 50%): Strongly and immediately urge the patient to schedule a comprehensive clinical evaluation with a specialist (Oncologist, Medical Geneticist, or Genetic Counselor) for diagnostic testing and formal management. Do not try to offer DIY remedies for high risk.
    - IF MODERATE / CONCERNING RISK (20% - 49.9%): Provide practical remedial steps and preventive care strategies (e.g., targeted routine screenings like colonoscopies/mammograms, lifestyle/diet adjustments, smoking cessation, and consulting a primary physician).
    - IF LOW RISK (< 20%): Reassure the patient while encouraging standard health maintenance, balanced lifestyle choices, and routine annual checkups.

    Do not repeat the raw math metrics in a robotic way. Focus on education and clear next steps.
    """


def generate_report(patient_data: dict, risk_table, model_predictions: dict | None = None) -> str:
    """
    Generates an educational clinical summary explaining detected disease risks
    and providing actionable remedial or medical advice based on risk severity.
    Only de-identified data is sent to Gemini (see build_prompt).
    """
    if not configure_api():
        return "⚠️ **System Notice:** API key not found. Please configure your GEMINI_API_KEY in Streamlit secrets to enable AI Synthesis."

    prompt = build_prompt(patient_data, risk_table, model_predictions)
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
