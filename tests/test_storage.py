"""Patient-record storage: record building, grouping, the local file and MongoDB."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

import storage

PATIENT = {
    "Name": "  Jane   Smith ", "Age": 45, "Gender": "Female", "Height": 165.0, "Weight": 60.0,
    "Blood Group": "O+", "Ancestry": "Asian", "Smoking History": "Never Smoked",
    "Family History": {"First-degree": 1, "Second-degree": 0},
    "Genetic Markers": {"BRCA1": True, "BRCA2": "Negative", "APC": False, "TP53": False},
    "Other Genetic Markers": ["PALB2"], "Lab Report": object(), "Additional Details": "notes",
}
RESULTS = {"base": 43.0, "mean": 42.8, "ci": (35.7, 50.4),
           "models": {"Random forest": 0.47}, "reference": 0.76, "summary": "Summary."}


def _record(name="Jane Smith", mean=42.8, when=None):
    rec = storage.build_record({**PATIENT, "Name": name}, {**RESULTS, "mean": mean}, "Moderate risk")
    if when:
        rec["created_at"] = when
    return rec


def test_record_contains_the_assessment_but_not_uploaded_files():
    rec = _record(name=PATIENT["Name"])
    assert rec["patient_key"] == "jane smith"
    assert rec["patient"]["name"] == "Jane   Smith"
    assert rec["patient"]["markers"] == ["BRCA1"]  # "Negative" is not a mutation
    assert rec["patient"]["other_markers"] == ["PALB2"]
    assert rec["diseases"] == ["Breast cancer", "Ovarian cancer"]
    assert rec["result"]["mean"] == 42.8 and rec["result"]["models"] == {"Random forest": 0.47}
    assert "lab" not in str(rec).lower()


def test_patients_are_grouped_by_name_with_latest_first():
    now = datetime.now(timezone.utc)
    records = [
        _record("Jane Smith", 30, now - timedelta(days=2)),
        _record("jane  smith", 55, now),
        _record("Raj Mehta", 10, now - timedelta(days=1)),
    ]
    patients = storage.group_patients(records)
    assert [p["name"] for p in patients] == ["jane  smith", "Raj Mehta"]
    jane = patients[0]
    assert jane["assessments"] == 2 and jane["latest_mean"] == 55
    assert [r["result"]["mean"] for r in jane["history"]] == [55, 30]


def test_local_store_saves_lists_and_deletes(tmp_path):
    store = storage.LocalStore(tmp_path / "records.json")
    store.save(_record("Jane Smith"))
    store.save(_record("Raj Mehta"))
    assert len(store.all_records()) == 2
    assert store.delete_patient("jane smith") == 1
    assert [r["patient"]["name"] for r in store.all_records()] == ["Raj Mehta"]


def test_connect_falls_back_to_the_local_file_when_mongodb_is_unreachable(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=300")
    store, error = storage.connect()
    assert isinstance(store, storage.LocalStore) and error


@pytest.fixture
def mongo_store():
    """A throwaway database on the local MongoDB server; skipped if none is running."""
    db_name = f"riskpredict_test_{uuid.uuid4().hex[:8]}"
    try:
        store = storage.MongoStore("mongodb://localhost:27017", db_name)
    except Exception:
        pytest.skip("no MongoDB server on localhost:27017")
    yield store
    store.client.drop_database(db_name)


def test_mongo_store_round_trip(mongo_store):
    mongo_store.save(_record("Jane Smith"))
    mongo_store.save(_record("Jane Smith", 60))
    records = mongo_store.all_records()
    assert len(records) == 2 and records[0]["created_at"].tzinfo is not None
    patients = storage.group_patients(records)
    assert patients[0]["assessments"] == 2
    assert mongo_store.delete_patient("jane smith") == 2


# ---------- downloads ----------

def test_csv_export_has_one_row_per_assessment_newest_first():
    import csv
    import io

    now = datetime.now(timezone.utc)
    records = [_record("Jane Smith", 30, now - timedelta(days=1)), _record("Raj Mehta", 55, now)]
    text = storage.records_to_csv(records).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert list(rows[0]) == storage.EXPORT_COLUMNS
    assert [r["Patient"] for r in rows] == ["Raj Mehta", "Jane Smith"]
    assert rows[0]["Mutations"] == "BRCA1" and rows[0]["Random forest (%)"] == "47.0"
    assert rows[0]["Linked diseases"] == "Breast cancer; Ovarian cancer"


def test_safe_filename():
    assert storage.safe_filename("Jane O'Neil Smith") == "Jane_ONeil_Smith"
    assert storage.safe_filename("  ") == "patient"


def test_patient_history_pdf_is_a_valid_pdf():
    import pdf_builder

    now = datetime.now(timezone.utc)
    patient = storage.group_patients([_record("Jane Smith", 30, now - timedelta(days=1)),
                                      _record("Jane Smith", 55, now)])[0]
    pdf = pdf_builder.generate_patient_history_pdf(patient)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1500
