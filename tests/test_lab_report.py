"""Reading gene results from an uploaded lab report."""

from pathlib import Path

import lab_report

GENES = ["BRCA1", "BRCA2", "APC", "TP53", "CHEK2", "PALB2"]
SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample_lab_report.pdf"


def _status(text):
    return {f["gene"]: f["status"] for f in lab_report.find_genes(text, GENES)}


def test_sample_pdf_is_read_correctly():
    result = lab_report.read_report(SAMPLE.read_bytes(), GENES)
    assert result["has_text"]
    assert {f["gene"]: f["status"] for f in result["findings"]} == {
        "BRCA1": "positive", "CHEK2": "positive", "TP53": "uncertain",
        "APC": "negative", "BRCA2": "negative", "PALB2": "negative",
    }


def test_negative_wording_wins_over_the_word_pathogenic():
    assert _status("BRCA2: no pathogenic variant detected") == {"BRCA2": "negative"}
    assert _status("BRCA1 likely benign") == {"BRCA1": "negative"}


def test_vus_is_uncertain_not_positive():
    assert _status("TP53 variant of uncertain significance") == {"TP53": "uncertain"}
    assert _status("TP53 VUS detected") == {"TP53": "uncertain"}


def test_whole_word_matching_only():
    assert _status("Capacity of the APCs lab; BRCA12 control") == {}
    assert _status("APC heterozygous pathogenic") == {"APC": "positive"}


def test_most_definite_result_wins_across_lines():
    text = "Genes tested: BRCA1, BRCA2\nBRCA1 c.68_69delAG Pathogenic"
    assert _status(text)["BRCA1"] == "positive"
    assert _status(text)["BRCA2"] == "mentioned"


def test_unreadable_file_reports_no_text():
    assert lab_report.read_report(b"not a pdf", GENES) == {"has_text": False, "findings": []}
