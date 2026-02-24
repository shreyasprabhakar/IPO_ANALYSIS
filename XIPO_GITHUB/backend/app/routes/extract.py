"""
Extract route — accepts PDF path + company name, extracts text.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.pdf_extractor import extract_text_from_pdf

router = APIRouter()


class ExtractRequest(BaseModel):
    company_name: str
    pdf_saved_path: str


@router.post("/extract/text")
def extract_text(body: ExtractRequest):
    """Extract text from a PDF file."""
    result = extract_text_from_pdf(body.pdf_saved_path, body.company_name)
    return {
        "company_name": body.company_name,
        "pdf_saved_path": body.pdf_saved_path,
        **result,
    }
