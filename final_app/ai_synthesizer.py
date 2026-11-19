import os
import time
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


# Tried in order. Each model has its own free daily quota, so when one is used up
# or busy the next usually still answers.
DEFAULT_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it",
]
REQUEST_TIMEOUT_S = 25  # per model attempt
TOTAL_BUDGET_S = 45     # for all attempts together


def _models() -> list[str]:
    """Models to try in order; override with GEMINI_MODELS = "a,b" in secrets or env."""
    try:
        raw = st.secrets.get("GEMINI_MODELS") or os.environ.get("GEMINI_MODELS")
    except Exception:
        raw = os.environ.get("GEMINI_MODELS")
    return [m.strip() for m in raw.split(",") if m.strip()] if raw else DEFAULT_MODELS


def _describe_error(exc: Exception) -> str:
    """A short, accurate reason for the user (daily vs per-minute quota, etc.)."""
    msg = str(exc)
    if "429" in msg or "ResourceExhausted" in type(exc).__name__ or "quota" in msg.lower():
        wait = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", msg)
        seconds = int(wait.group(1)) if wait else None
        if "PerDay" in msg:
            when = f" It resets in about {max(1, round(seconds / 3600))} hours." if seconds else ""
            return f"the free Gemini daily limit has been used up.{when}"
        when = f" Try again in about {seconds} seconds." if seconds else " Try again in a minute."
        return f"the free Gemini per-minute limit was reached.{when}"
    if "API key" in msg or "API_KEY" in msg:
        return "the Gemini API key was rejected."
    if "DeadlineExceeded" in type(exc).__name__ or "timed out" in msg.lower() or "504" in msg:
        return "the AI service took too long to respond."
    if "ServiceUnavailable" in type(exc).__name__ or "503" in msg or "high demand" in msg:
        return "the AI service is busy right now."
    return f"the AI service returned an error ({type(exc).__name__})."


def fallback_summary(patient_data: dict, risk_table) -> str:
    """
    A standard summary written from fixed guidance text, used when the AI
    service is unavailable. Built only from the patient's results.
    """
    mean = float(risk_table["Simulated Mean"].iloc[0].replace("%", ""))
    ci = risk_table["90% Confidence Interval"].iloc[0]
    markers = positive_markers(patient_data)
    others = list(patient_data.get("Other Genetic Markers") or [])
    family = patient_data.get("Family History", {}) or {}
    first, second = family.get("First-degree", 0) or 0, family.get("Second-degree", 0) or 0
    smoking = patient_data.get("Smoking History") or "Never Smoked"

    findings = []
    if markers:
        findings.append("Your results show a change in " + "; ".join(
            MARKER_INFO[m].replace(" (", ", which is ").rstrip(")") for m in markers if m in MARKER_INFO) + ".")
    else:
        findings.append("None of the four scored genes (BRCA1, BRCA2, APC, TP53) showed a harmful change.")
    if others:
        findings.append(f"Other reported changes ({', '.join(others)}) are noted for your doctor "
                        "but are not part of the numeric score.")
    if first or second:
        findings.append(f"You reported {first} close (first-degree) and {second} second-degree "
                        "relatives with cancer, which raises hereditary risk.")
    if smoking != "Never Smoked":
        findings.append(f"Smoking history ({smoking.lower()}) also adds to the overall risk.")
    lo, hi = (float(v) for v in re.findall(r"[\d.]+", ci)[:2])
    para1 = (f"Your estimated risk is about {mean:.0f}% (likely between {lo:.0f}% and {hi:.0f}%). "
             + " ".join(findings))

    if mean >= 50:
        para2 = ("This is a high-risk result. Please arrange a full clinical evaluation soon with a "
                 "specialist such as a medical geneticist, oncologist or genetic counselor, who can "
                 "confirm these findings and plan diagnostic tests and ongoing management.")
    elif mean >= 20:
        para2 = ("This is a moderate risk. Talk to your doctor about earlier or more frequent "
                 "screening suited to these genes (for example mammograms or colonoscopy), and "
                 "consider genetic counseling. Not smoking, staying active and a balanced diet "
                 "also help lower overall risk.")
    else:
        para2 = ("This is a low risk. Keep up routine check-ups and the screening recommended for "
                 "your age, along with a healthy lifestyle. Tell your doctor if your family "
                 "history changes.")
    return f"{para1}\n\n{para2}"


def generate_summary(patient_data: dict, risk_table, model_predictions: dict | None = None) -> dict:
    """
    The clinical summary for one patient. Tries each Gemini model in turn
    (a model that is out of quota is skipped), then falls back to the
    standard summary. Only de-identified data is sent (see build_prompt).

    Returns {"text", "source": "ai" | "fallback", "model", "notice"}, where
    `notice` explains why the AI summary is missing (None when it worked).
    """
    if not configure_api():
        return {"text": fallback_summary(patient_data, risk_table), "source": "fallback",
                "model": None, "notice": "No Gemini API key is configured."}

    prompt = build_prompt(patient_data, risk_table, model_predictions)
    reason = None
    deadline = time.monotonic() + TOTAL_BUDGET_S
    for name in _models():
        remaining = deadline - time.monotonic()
        if remaining < 5:  # not enough time left for another model to answer
            reason = reason or "the AI service took too long to respond."
            break
        try:
            # No hidden library retries, and a time limit per model, so a slow or
            # rate-limited model never leaves the page waiting for minutes.
            text = genai.GenerativeModel(name).generate_content(
                prompt,
                request_options={"retry": None, "timeout": min(REQUEST_TIMEOUT_S, remaining)},
            ).text
            if text and text.strip():
                return {"text": text, "source": "ai", "model": name, "notice": None}
        except Exception as exc:  # quota, network, safety block, removed model...
            reason = _describe_error(exc)
    return {"text": fallback_summary(patient_data, risk_table), "source": "fallback",
            "model": None, "notice": f"AI summary unavailable: {reason or 'no response.'}"}


def generate_report(patient_data: dict, risk_table, model_predictions: dict | None = None) -> str:
    """Summary text only (kept for older callers)."""
    return generate_summary(patient_data, risk_table, model_predictions)["text"]
