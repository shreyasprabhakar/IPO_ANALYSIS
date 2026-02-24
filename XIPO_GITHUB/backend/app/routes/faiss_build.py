"""
FAISS Build route — accepts chunks path + company name, builds FAISS index.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.embedding_store import build_faiss_index

router = APIRouter()


class FAISSBuildRequest(BaseModel):
    company_name: str
    chunks_saved_path: str


@router.post("/faiss/build")
def faiss_build(body: FAISSBuildRequest):
    """Build FAISS index from chunked text."""
    result = build_faiss_index(body.chunks_saved_path, body.company_name)
    return {
        "company_name": body.company_name,
        "chunks_saved_path": body.chunks_saved_path,
        **result,
    }
