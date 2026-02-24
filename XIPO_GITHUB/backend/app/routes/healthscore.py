"""
Health Score route — accepts company name, ratios path, and text path,
computes a sector-wise Financial Health Score (0-100).
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.health_score import compute_health_score

router = APIRouter()


class HealthScoreRequest(BaseModel):
    company_name: str
    ratios_saved_path: str
    text_saved_path: str
    debug: bool = False


@router.post("/healthscore")
def get_health_score(body: HealthScoreRequest):
    """Compute Financial Health Score for the given IPO company."""
    result = compute_health_score(
        company_name=body.company_name,
        ratios_path=body.ratios_saved_path,
        text_path=body.text_saved_path,
        debug=body.debug,
    )
    return result
