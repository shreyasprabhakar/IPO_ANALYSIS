"""
SEBI search route — accepts a company name and returns the best RHP match.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.sebi_scraper import search_sebi_rhp

router = APIRouter()


class SearchRequest(BaseModel):
    company_name: str


@router.post("/sebi/search")
def sebi_search(body: SearchRequest):
    """Search SEBI filings for a company's RHP page."""
    result = search_sebi_rhp(body.company_name)
    return result
