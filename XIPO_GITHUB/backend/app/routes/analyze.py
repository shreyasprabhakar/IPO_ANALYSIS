"""
Unified Pipeline Router
POST /api/analyze - Orchestrates the entire workflow from company name to final IPO report.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.sebi_scraper import search_sebi_rhp
from app.services.sebi_pdf_downloader import download_rhp_pdf
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.chunker import chunk_text_file
from app.services.embedding_store import build_faiss_index
from app.services.report_generator import generate_default_report
from app.services.financial_extractor import extract_financial_metrics, compute_ratios
from app.services.health_score import compute_health_score


router = APIRouter(prefix="/api/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    company_name: str
    top_k: int = 6
    debug: bool = False


class AnalyzeResponse(BaseModel):
    company_name: str
    analysis_report: dict
    health_score: dict
    financials: dict
    chat_ready: bool
    # Debug fields (only when debug=True)
    pdf_info: Optional[dict] = None
    file_paths: Optional[dict] = None


@router.post("", response_model=AnalyzeResponse)
def analyze_company(request: AnalyzeRequest):
    """
    Run the complete IPO analysis pipeline for a company.
    
    Steps:
    1. Search SEBI for RHP HTML URL
    2. Download PDF from SEBI
    3. Extract text from PDF
    4. Chunk text into passages
    5. Build FAISS index
    6. Generate default IPO report
    7. Extract financial metrics
    8. Compute financial ratios
    9. Compute health score
    
    Returns comprehensive analysis with report, financials, and health score.
    """
    company_name = request.company_name
    top_k = request.top_k
    debug = request.debug
    
    try:
        # A) SEBI RHP Search
        search_result = search_sebi_rhp(company_name)
        if search_result.get("status") != "ok":
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"No strong RHP match found for company: {company_name}",
                    "top_matches": search_result.get("top_matches", []),
                    "pages_scanned": search_result.get("pages_scanned", 0),
                }
            )
        
        rhp_html_url = search_result["rhp_html_url"]
        
        # B) PDF Download
        try:
            download_result = download_rhp_pdf(rhp_html_url, company_name)
            pdf_path = download_result["pdf_saved_path"]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download PDF: {str(e)}"
            )
        
        # C) Text Extraction
        try:
            extract_result = extract_text_from_pdf(pdf_path, company_name)
            text_path = extract_result["text_saved_path"]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )
        
        # D) Chunking + FAISS
        try:
            chunk_result = chunk_text_file(text_path, company_name)
            chunks_path = chunk_result["chunks_saved_path"]
            
            faiss_result = build_faiss_index(chunks_path, company_name)
            index_path = faiss_result["faiss_index_path"]
            meta_path = faiss_result["meta_path"]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build FAISS index: {str(e)}"
            )
        
        # E) Default Report Generation
        try:
            report_result = generate_default_report(company_name, top_k)
            analysis_report = report_result["report"]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate report: {str(e)}"
            )
        
        # F) Financial Metrics + Ratios
        try:
            metrics_result = extract_financial_metrics(text_path, company_name)
            extracted_metrics = metrics_result["extracted_metrics"]
            
            ratios_result = compute_ratios(extracted_metrics, company_name)
            ratios_path = ratios_result["ratios_saved_path"]
            ratios = ratios_result["ratios"]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract financials: {str(e)}"
            )
        
        # G) Health Score
        try:
            health_result = compute_health_score(
                company_name=company_name,
                ratios_path=ratios_path,
                text_path=text_path,
                debug=debug
            )
            
            # Clean health score for user (remove debug fields if not in debug mode)
            if not debug:
                health_score_clean = {
                    "score": health_result["score"],
                    "category": health_result["category"],
                    "sector_used": health_result["sector_used"],
                }
            else:
                health_score_clean = health_result
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compute health score: {str(e)}"
            )
        
        # Build response
        response = {
            "company_name": company_name,
            "analysis_report": analysis_report,
            "health_score": health_score_clean,
            "financials": {
                "metrics": extracted_metrics,
                "ratios": ratios,
            },
            "chat_ready": True,
        }
        
        # Add debug info if requested
        if debug:
            response["pdf_info"] = {
                "rhp_html_url": rhp_html_url,
                "matched_company": search_result.get("matched_company_title"),
                "match_score": search_result.get("match_score"),
                "doc_type": search_result.get("doc_type"),
                "pages_scanned": search_result.get("pages_scanned"),
                "pdf_url": download_result.get("pdf_url_used"),
                "pages_extracted": extract_result.get("pages_extracted"),
                "chars_extracted": extract_result.get("chars_extracted"),
            }
            response["file_paths"] = {
                "pdf_path": pdf_path,
                "text_path": text_path,
                "chunks_path": chunks_path,
                "faiss_index_path": index_path,
                "faiss_meta_path": meta_path,
                "metrics_path": metrics_result.get("metrics_saved_path"),
                "ratios_path": ratios_path,
            }
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during analysis: {str(e)}"
        )
