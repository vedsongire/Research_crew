"""
Test Suite: PDF Export and Download Endpoint Verification.
"""

import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main import app
from pdf_export import markdown_report_to_pdf

client = TestClient(app)


def test_markdown_to_pdf_conversion():
    print("Testing direct markdown_report_to_pdf conversion...")
    sample_topic = "Advancements in Quantum Sensors"
    sample_md = (
        "# Executive Summary\n\n"
        "Quantum sensing is advancing rapidly in 2026.\n\n"
        "## Key Trends\n\n"
        "- High sensitivity measurements in navigation\n"
        "- Diamond nitrogen-vacancy centers\n\n"
        "### Strategic Outlook\n\n"
        "Early adoption expected in biomedical imaging.\n"
    )
    test_pdf_path = os.path.join(project_root, "outputs", "test_sample_report.pdf")
    out = markdown_report_to_pdf(sample_md, sample_topic, test_pdf_path)
    assert os.path.isfile(out), f"PDF file not created at {out}"
    assert os.path.getsize(out) > 0, "Generated PDF is empty"
    print(f"[PASSED] PDF successfully generated at {out} (size: {os.path.getsize(out)} bytes)")


def test_get_pdf_endpoint():
    print("\nTesting GET /research/{filename}/pdf endpoint...")
    # Request using the test_sample_report generated above
    response = client.get("/research/test_sample_report.pdf/pdf")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0
    print("[PASSED] GET /research/{filename}/pdf returned 200 OK with application/pdf content.")


if __name__ == "__main__":
    test_markdown_to_pdf_conversion()
    test_get_pdf_endpoint()
