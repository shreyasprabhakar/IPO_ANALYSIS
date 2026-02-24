"""
PDF Text Extractor Service
Extracts text from RHP PDFs using pdfplumber and saves to data/extracted_text/.
"""

import os
import re
import pdfplumber

# Directory for extracted text
EXTRACTED_TEXT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/extracted_text")
)
os.makedirs(EXTRACTED_TEXT_DIR, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def extract_text_from_pdf(pdf_path: str, company_name: str) -> dict:
    """
    Extract text from a PDF file page-by-page using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.
        company_name: Name of the company (used for the saved filename).

    Returns:
        dict with keys:
            - text_saved_path: local path where the text was saved
            - pages_extracted: number of pages extracted
            - chars_extracted: total number of characters extracted
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    all_text = []
    pages_extracted = 0

    # Extract text page by page
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)
            pages_extracted += 1

    # Combine all text
    full_text = "\n\n".join(all_text)
    chars_extracted = len(full_text)

    # Save to file
    safe_name = _safe_filename(company_name)
    text_path = os.path.join(EXTRACTED_TEXT_DIR, f"{safe_name}.txt")

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    return {
        "text_saved_path": os.path.normpath(text_path),
        "pages_extracted": pages_extracted,
        "chars_extracted": chars_extracted,
    }
