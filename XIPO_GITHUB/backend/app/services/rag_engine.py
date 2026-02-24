"""
RAG Engine Service
Retrieves relevant chunks from FAISS and generates answers using Ollama.
"""

import os
import re
import json
import requests
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Directories
FAISS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/faiss")
)

# Model to use for embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:8b"


def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")



import time

def answer_question(company_name: str, question: str, top_k: int = 6, debug: bool = False, timeout: int = 60, retries: int = 0) -> dict:
    """
    Answer a question using RAG: retrieve relevant chunks from FAISS and generate answer using Ollama.
    
    Args:
        company_name: Name of the company (used to locate FAISS index and metadata).
        question: The question to answer.
        top_k: Number of top chunks to retrieve (default: 6).
        debug: If True, return debug information (sources, chunk count). Default: False.
        timeout: Timeout in seconds for the Ollama API call (default: 60).
        retries: Number of retries if the Ollama call fails or times out (default: 0).
    
    Returns:
        dict with keys:
            - answer: Generated answer from Ollama
            - sources: (only if debug=True) List of sources (chunk_id + section)
            - retrieved_chunks_count: (only if debug=True) Number of chunks retrieved
            - retrieved_context_preview: (only if debug=True) Preview of retrieved context
    """
    # Construct file paths
    safe_name = _safe_filename(company_name)
    index_path = os.path.join(FAISS_DIR, f"{safe_name}.index")
    meta_path = os.path.join(FAISS_DIR, f"{safe_name}_meta.json")
    
    # Check if files exist
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")
    
    # Load FAISS index
    index = faiss.read_index(index_path)
    
    # Load metadata
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Load embedding model
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Embed the question
    question_embedding = model.encode([question], convert_to_numpy=True)
    
    # Search FAISS for top_k similar chunks
    distances, indices = index.search(question_embedding.astype('float32'), top_k)
    
    # Retrieve the chunks
    retrieved_chunks = []
    sources = []
    
    for idx in indices[0]:
        if idx < len(metadata):
            chunk = metadata[idx]
            retrieved_chunks.append(chunk["text"])
            sources.append({
                "chunk_id": chunk["chunk_id"],
                "section": chunk["section"]
            })
    
    # Build the prompt for Ollama
    context = "\n\n---\n\n".join(retrieved_chunks)
    
    prompt = f"""You are a professional IPO analyst. Answer the user's question based on the information from the IPO prospectus provided below.

IMPORTANT INSTRUCTIONS:
- Answer directly and professionally as an IPO analyst would
- NEVER mention "chunks", "context", "FAISS", "embeddings", "retrieval", or any technical terms about how you got the information
- NEVER say "based on the context" or "according to the provided information"
- Simply state the facts as if you have expert knowledge of this IPO
- If the information is not available in the prospectus, clearly state: "This information is not available in the IPO prospectus."
- Use specific details when available.

IPO Prospectus Information:
{context}

Question: {question}

Answer:"""
    
    # Call Ollama API with retries
    max_attempts = 1 + retries
    last_error = None

    for attempt in range(max_attempts):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=timeout
            )
            response.raise_for_status()
            
            ollama_response = response.json()
            answer = ollama_response.get("response", "")
            
            # If successful, break the retry loop
            break
            
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_attempts - 1:
                # Wait a bit before retrying
                time.sleep(2)
                continue
            else:
                # Last attempt failed
                raise RuntimeError(f"Failed to call Ollama API after {max_attempts} attempts: {str(e)}")
    
    # Return response based on debug mode
    if debug:
        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks_count": len(retrieved_chunks),
            "retrieved_context_preview": context[:500] + "..." if len(context) > 500 else context
        }
    else:
        return {
            "answer": answer
        }
