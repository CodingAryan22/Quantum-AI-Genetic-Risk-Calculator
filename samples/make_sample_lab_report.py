"""
Builds samples/sample_lab_report.pdf: a FICTIONAL genetic test report for demos
and tests. Run from the repo root:  python samples/make_sample_lab_report.py
"""

from pathlib import Path

from fpdf import FPDF

LINES = [
    ("Patient", "Sample Patient (fictional)"),
    ("Test", "Hereditary Cancer Multi-Gene Panel"),
    ("Report date", "19 Nov 2026"),
]
RESULTS = [
    ("BRCA1", "c.68_69delAG (p.Glu23fs)", "Pathogenic"),
    ("BRCA2", "-", "No pathogenic variant detected"),
    ("TP53", "c.215C>G (p.Pro72Arg)", "Variant of uncertain significance (VUS)"),
    ("APC", "-", "Negative"),
    ("CHEK2", "c.1100delC", "Likely pathogenic"),
    ("PALB2", "-", "Not detected"),
]


def build(path: Path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Genetic Test Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "FICTIONAL SAMPLE FOR SOFTWARE DEMONSTRATION - NOT A REAL PATIENT",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    for label, value in LINES:
        pdf.cell(0, 7, f"{label}: {value}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Results", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for gene, variant, result in RESULTS:
        pdf.cell(0, 7, f"{gene}   {variant}   {result}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Interpretation should be performed by a qualified genetic counselor.")
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_lab_report.pdf"
    build(out)
    print(f"Wrote {out}")
