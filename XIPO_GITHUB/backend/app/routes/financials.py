"""
Financials route — accepts text path + company name, extracts metrics and ratios.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.financial_extractor import extract_financial_metrics, compute_ratios

router = APIRouter()


class FinancialsRequest(BaseModel):
    company_name: str
    text_saved_path: str


@router.post("/financials/extract")
def extract_financials(body: FinancialsRequest):
    """Extract financial metrics from RHP text and compute ratios."""
    metrics_result = extract_financial_metrics(
        body.text_saved_path, body.company_name
    )
    ratios_result = compute_ratios(
        metrics_result["extracted_metrics"], body.company_name
    )
    return {
        "company_name": body.company_name,
        "metrics_saved_path": metrics_result["metrics_saved_path"],
        "ratios_saved_path": ratios_result["ratios_saved_path"],
        "extracted_metrics": metrics_result["extracted_metrics"],
        "ratios": ratios_result["ratios"],
    }
