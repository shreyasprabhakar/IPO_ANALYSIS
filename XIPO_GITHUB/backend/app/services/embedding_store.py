"""
Embedding Store Service
Generates embeddings for chunked text using SentenceTransformers
and stores them in a FAISS index for retrieval.
"""

import os
import re
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Directories
FAISS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/faiss")
)
os.makedirs(FAISS_DIR, exist_ok=True)

# Model to use for embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def build_faiss_index(chunks_path: str, company_name: str) -> dict:
    """
    Build FAISS index from chunked text.
    
    Args:
        chunks_path: Path to the chunks JSON file.
        company_name: Name of the company (used for the saved filename).
    
    Returns:
        dict with keys:
            - faiss_index_path: path to saved FAISS index
            - meta_path: path to saved metadata JSON
            - total_chunks: number of chunks indexed
            - embedding_dim: dimension of embeddings
    """
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")
    
    # Load chunks
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    if not chunks:
        raise ValueError("No chunks found in the file")
    
    # Load embedding model
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Extract texts for embedding
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    
    # Get embedding dimension
    embedding_dim = embeddings.shape[1]
    
    # Create FAISS index (L2 distance)
    index = faiss.IndexFlatL2(embedding_dim)
    
    # Add embeddings to index
    index.add(embeddings.astype('float32'))
    
    # Prepare metadata (without full text to save space, store chunk_id, section)
    metadata = []
    for chunk in chunks:
        metadata.append({
            "chunk_id": chunk["chunk_id"],
            "company_name": chunk["company_name"],
            "section": chunk["section"],
            "text": chunk["text"],  # Keep text for retrieval
            "char_count": chunk["char_count"]
        })
    
    # Save FAISS index
    safe_name = _safe_filename(company_name)
    index_path = os.path.join(FAISS_DIR, f"{safe_name}.index")
    faiss.write_index(index, index_path)
    
    # Save metadata
    meta_path = os.path.join(FAISS_DIR, f"{safe_name}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return {
        "faiss_index_path": os.path.normpath(index_path),
        "meta_path": os.path.normpath(meta_path),
        "total_chunks": len(chunks),
        "embedding_dim": embedding_dim,
    }
