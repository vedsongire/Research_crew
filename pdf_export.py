"""
pdf_export.py — converts a research report (markdown string) into a clean PDF.

TEACHING NOTE: we already have the report as markdown text (from crew.py's
output). fpdf2 is a lightweight, dependency-light PDF library — no browser
engine needed (unlike weasyprint), which keeps this simple to explain and
fast to install. We do a light manual markdown -> PDF conversion (headings,
bold, plain paragraphs) rather than pulling in a full HTML rendering stack,
since our reports only use a few markdown features.
"""

import re
from datetime import datetime

from fpdf import FPDF


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "AI Research Assistant Crew - Report", align="C")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def markdown_report_to_pdf(markdown_text: str, topic: str, output_path: str) -> str:
    """
    Converts the crew's markdown report into a PDF saved at output_path.
    Handles: # / ## / ### headings, **bold** inline, and plain paragraphs.
    Returns the path written.
    """
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 10, topic, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}")
    pdf.ln(14)

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if not line:
            pdf.ln(4)
            continue

        if line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 8, line[4:], new_x="LMARGIN", new_y="NEXT")
            continue
        if line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(0, 9, line[3:], new_x="LMARGIN", new_y="NEXT")
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(10, 10, 10)
            pdf.multi_cell(0, 10, line[2:], new_x="LMARGIN", new_y="NEXT")
            continue

        # Strip **bold** markers for plain rendering (fpdf2's multi_cell
        # doesn't do inline mixed styling without more machinery than this
        # project needs — plain text is a reasonable, explainable trade-off).
        clean_line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        clean_line = re.sub(r"^-\s+", "- ", clean_line)  # bullets (core font has no bullet glyph)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 7, clean_line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    return output_path