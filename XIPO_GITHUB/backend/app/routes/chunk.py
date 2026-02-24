"""
Chunk route — accepts text path + company name, chunks the text.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chunker import chunk_text_file

router = APIRouter()


class ChunkRequest(BaseModel):
    company_name: str
    text_saved_path: str


@router.post("/chunk")
def chunk_text(body: ChunkRequest):
    """Chunk extracted text into smaller passages."""
    result = chunk_text_file(body.text_saved_path, body.company_name)
    return {
        "company_name": body.company_name,
        "text_saved_path": body.text_saved_path,
        **result,
    }
