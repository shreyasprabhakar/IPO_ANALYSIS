"""
Report generation route — generates comprehensive IPO analysis report.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.report_generator import generate_default_report

router = APIRouter()


class ReportRequest(BaseModel):
    company_name: str = Field(..., description="Name of the company")
    top_k: int = Field(6, description="Number of chunks to retrieve per question", ge=1, le=20)


@router.post("/report/generate")
def generate_report(body: ReportRequest):
    """
    Generate a comprehensive IPO analysis report for the given company.
    
    Uses the RAG pipeline to answer predefined questions about:
    - Company overview
    - Business model
    - Objects of issue
    - Strengths
    - Key risks
    - Financial highlights
    - Final verdict
    """
    try:
        result = generate_default_report(
            company_name=body.company_name,
            top_k=body.top_k
        )
        return result
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
