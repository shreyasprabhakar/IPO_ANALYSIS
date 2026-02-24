"""
Download route — accepts RHP HTML URL + company name, downloads the PDF.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.sebi_pdf_downloader import download_rhp_pdf

router = APIRouter()


class DownloadRequest(BaseModel):
    company_name: str
    rhp_html_url: str


@router.post("/sebi/download-rhp")
def download_rhp(body: DownloadRequest):
    """Download the RHP PDF from a SEBI HTML page."""
    result = download_rhp_pdf(body.rhp_html_url, body.company_name)
    return {
        "company_name": body.company_name,
        "rhp_html_url": body.rhp_html_url,
        **result,
    }
