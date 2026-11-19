"""
Reads gene results out of an uploaded lab report (PDF).

The PDF's text layer is extracted with PyPDF2; each line that names a known
gene is classified from the words around it:

    negative   - "not detected", "negative", "no pathogenic variant", "benign", ...
    uncertain  - "variant of uncertain significance", "VUS"
    positive   - "pathogenic", "likely pathogenic", "positive", "detected", ...
    mentioned  - the gene appears but the line gives no result

Negative wording is checked first, so "no pathogenic variant detected" is
negative, not positive. Scanned PDFs (images only) have no text layer; for those
`extract_text` returns "" and the clinician enters the genes by hand.
"""

import io
import re

NEGATIVE = ["not detected", "no pathogenic", "no mutation", "no variant", "no deleterious",
            "negative", "likely benign", "benign", "wild type", "wild-type", "normal",
            "not identified", "absent"]
UNCERTAIN = ["uncertain significance", "vus", "unclassified variant"]
POSITIVE = ["likely pathogenic", "pathogenic", "positive", "detected", "deleterious",
            "mutation identified", "variant identified", "carrier", "heterozygous", "homozygous"]

STATUS_ORDER = {"positive": 0, "uncertain": 1, "negative": 2, "mentioned": 3}


def extract_text(data: bytes) -> str:
    """All selectable text in the PDF ('' for scanned/image-only or unreadable files)."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception:
        return ""


def _classify(line: str) -> str:
    low = line.lower()
    if any(w in low for w in NEGATIVE):
        return "negative"
    if any(re.search(rf"\b{re.escape(w)}\b", low) for w in UNCERTAIN):
        return "uncertain"
    if any(w in low for w in POSITIVE):
        return "positive"
    return "mentioned"


def find_genes(text: str, genes: list[str]) -> list[dict]:
    """
    One finding per gene named in the text: {gene, status, evidence}. When a
    gene appears on several lines, the most definite result wins
    (positive > uncertain > negative > mentioned).
    """
    found: dict[str, dict] = {}
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        for gene in genes:
            # Whole-word match, so BRCA1 doesn't match inside BRCA12 and APC not inside "capacity".
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(gene)}(?![A-Za-z0-9])", line, flags=re.I):
                status = _classify(line)
                current = found.get(gene)
                if current is None or STATUS_ORDER[status] < STATUS_ORDER[current["status"]]:
                    found[gene] = {"gene": gene, "status": status, "evidence": line[:160]}
    return sorted(found.values(), key=lambda f: (STATUS_ORDER[f["status"]], f["gene"]))


def read_report(data: bytes, genes: list[str]) -> dict:
    """{'has_text': bool, 'findings': [...]} for an uploaded PDF."""
    text = extract_text(data)
    return {"has_text": bool(text), "findings": find_genes(text, genes) if text else []}
