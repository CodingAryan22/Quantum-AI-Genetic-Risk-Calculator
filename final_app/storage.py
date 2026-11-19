"""
Where patient assessments are saved.

    MongoStore  - MongoDB (local server or MongoDB Atlas), used when reachable
    LocalStore  - a JSON file in final_app/data/, used as a fallback so the app
                  keeps working without a database

Configuration (Streamlit secrets or environment variables):

    MONGODB_URI = "mongodb://localhost:27017"            # default
    MONGODB_URI = "mongodb+srv://user:pass@cluster.../"   # MongoDB Atlas
    MONGODB_DB  = "riskpredict"                          # default database name

Every assessment is one document in the `assessments` collection. Patients are
grouped by name (case- and space-insensitive), so assessing the same name again
adds to that patient's history.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from features import positive_markers
except ModuleNotFoundError:  # imported as final_app.storage
    from .features import positive_markers

DEFAULT_URI = "mongodb://localhost:27017"
DEFAULT_DB = "riskpredict"
COLLECTION = "assessments"
LOCAL_PATH = Path(__file__).resolve().parent / "data" / "patient_records.json"

# Cancers linked to each scored gene (published associations; see ui_modules.EVIDENCE).
GENE_DISEASES = {
    "BRCA1": ["Breast cancer", "Ovarian cancer"],
    "BRCA2": ["Breast cancer", "Ovarian cancer", "Prostate cancer", "Pancreatic cancer"],
    "APC": ["Colorectal cancer (FAP)"],
    "TP53": ["Li-Fraumeni syndrome (breast, sarcoma, brain, adrenal, leukemia)"],
}


def _setting(name: str, default: str) -> str:
    try:
        import streamlit as st
        return st.secrets.get(name) or os.environ.get(name) or default
    except Exception:
        return os.environ.get(name) or default


def patient_key(name: str) -> str:
    """Groups assessments of the same person: lower-case, single spaces."""
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def linked_diseases(markers: list[str]) -> list[str]:
    seen, out = set(), []
    for m in markers:
        for d in GENE_DISEASES.get(m, []):
            if d not in seen:
                seen.add(d)
                out.append(d)
    return out


def build_record(patient: dict, results: dict, tier: str) -> dict:
    """The document saved for one assessment (no uploaded files, no charts)."""
    markers = positive_markers(patient)
    return {
        "patient_key": patient_key(patient.get("Name")),
        "created_at": datetime.now(timezone.utc),
        "patient": {
            "name": (patient.get("Name") or "").strip(),
            "age": patient.get("Age"),
            "gender": patient.get("Gender"),
            "height_cm": patient.get("Height"),
            "weight_kg": patient.get("Weight"),
            "blood_group": patient.get("Blood Group"),
            "ancestry": patient.get("Ancestry"),
            "smoking": patient.get("Smoking History"),
            "markers": markers,
            "other_markers": list(patient.get("Other Genetic Markers") or []),
            "family_history": dict(patient.get("Family History") or {}),
            "notes": patient.get("Additional Details") or "",
        },
        "diseases": linked_diseases(markers),
        "result": {
            "baseline": results["base"],
            "mean": results["mean"],
            "ci_low": results["ci"][0],
            "ci_high": results["ci"][1],
            "tier": tier,
            "models": results.get("models") or {},
            "reference": results.get("reference"),
        },
        "summary": results.get("summary") or "",
    }


def group_patients(records: list[dict]) -> list[dict]:
    """One row per patient (latest assessment first), with their full history."""
    by_key: dict[str, list[dict]] = {}
    for r in records:
        by_key.setdefault(r["patient_key"], []).append(r)
    patients = []
    for key, history in by_key.items():
        history.sort(key=lambda r: r["created_at"], reverse=True)
        latest = history[0]
        diseases = []
        for r in history:
            for d in r.get("diseases", []):
                if d not in diseases:
                    diseases.append(d)
        patients.append({
            "key": key,
            "name": latest["patient"]["name"],
            "age": latest["patient"].get("age"),
            "gender": latest["patient"].get("gender"),
            "markers": latest["patient"].get("markers", []) + latest["patient"].get("other_markers", []),
            "diseases": diseases,
            "assessments": len(history),
            "last_assessed": latest["created_at"],
            "latest_mean": latest["result"]["mean"],
            "latest_tier": latest["result"]["tier"],
            "history": history,
        })
    patients.sort(key=lambda p: p["last_assessed"], reverse=True)
    return patients


class MongoStore:
    name = "MongoDB"

    def __init__(self, uri: str, db_name: str):
        from pymongo import ASCENDING, DESCENDING, MongoClient

        self.client = MongoClient(uri, serverSelectionTimeoutMS=2500)
        self.client.admin.command("ping")  # fail fast if the server isn't reachable
        self.col = self.client[db_name][COLLECTION]
        self.col.create_index([("patient_key", ASCENDING), ("created_at", DESCENDING)])
        self.location = f"{db_name}.{COLLECTION}"

    def save(self, record: dict) -> str:
        return str(self.col.insert_one(dict(record)).inserted_id)

    def all_records(self) -> list[dict]:
        records = list(self.col.find({}).sort("created_at", -1))
        for r in records:
            r["_id"] = str(r["_id"])
            if r["created_at"].tzinfo is None:  # MongoDB returns naive UTC datetimes
                r["created_at"] = r["created_at"].replace(tzinfo=timezone.utc)
        return records

    def delete_patient(self, key: str) -> int:
        return self.col.delete_many({"patient_key": key}).deleted_count


class LocalStore:
    name = "Local file"

    def __init__(self, path: Path = LOCAL_PATH):
        self.path = Path(path)
        self.location = str(self.path)

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for r in data:
            r["created_at"] = datetime.fromisoformat(r["created_at"])
        return data

    def _write(self, records: list[dict]):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out = [{**r, "created_at": r["created_at"].isoformat()} for r in records]
        self.path.write_text(json.dumps(out, indent=1), encoding="utf-8")

    def save(self, record: dict) -> str:
        records = self._read()
        record = {**record, "_id": uuid.uuid4().hex}
        records.append(record)
        self._write(records)
        return record["_id"]

    def all_records(self) -> list[dict]:
        return sorted(self._read(), key=lambda r: r["created_at"], reverse=True)

    def delete_patient(self, key: str) -> int:
        records = self._read()
        keep = [r for r in records if r["patient_key"] != key]
        self._write(keep)
        return len(records) - len(keep)


def connect():
    """
    Returns (store, error). Tries MongoDB first; if it can't be reached, falls
    back to the local JSON file and returns the reason as `error`.
    """
    uri = _setting("MONGODB_URI", DEFAULT_URI)
    db_name = _setting("MONGODB_DB", DEFAULT_DB)
    try:
        return MongoStore(uri, db_name), None
    except Exception as exc:  # pymongo missing, server down, bad URI, auth failure...
        return LocalStore(), f"{type(exc).__name__}: {str(exc)[:160]}"
