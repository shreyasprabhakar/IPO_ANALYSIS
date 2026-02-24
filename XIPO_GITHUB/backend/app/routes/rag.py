"""
RAG route — accepts company name and question, returns AI-generated answer.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.rag_engine import answer_question

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RAGRequest(BaseModel):
    company_name: str = Field(..., description="Name of the company")
    question: str = Field(..., description="Question to ask about the company")
    top_k: int = Field(6, description="Number of chunks to retrieve", ge=1, le=20)
    debug: bool = Field(False, description="Enable debug mode to see sources and retrieval info")


@router.post("/ask")
def ask_question(body: RAGRequest):
    """
    Ask a question about a company using RAG.
    
    Retrieves relevant chunks from FAISS and generates an answer using Ollama.
    Set debug=true to see sources and retrieval information.
    """
    try:
        result = answer_question(
            company_name=body.company_name,
            question=body.question,
            top_k=body.top_k,
            debug=body.debug
        )
        
        # Build response - always include company_name and question
        response = {
            "company_name": body.company_name,
            "question": body.question,
            "answer": result["answer"]
        }
        
        # Add debug fields if debug mode is enabled
        if body.debug:
            response["sources"] = result.get("sources", [])
            response["retrieved_chunks_count"] = result.get("retrieved_chunks_count", 0)
            response["retrieved_context_preview"] = result.get("retrieved_context_preview", "")
        
        return response
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
