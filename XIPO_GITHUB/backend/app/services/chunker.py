"""
Text Chunker Service
Splits extracted RHP text into smaller chunks with section detection.
Saves chunks as JSON for later embeddings + FAISS.
"""

import os
import re
import json

# Directory for chunked data
CHUNKS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/chunks")
)
os.makedirs(CHUNKS_DIR, exist_ok=True)

# Chunking parameters
MIN_CHUNK_SIZE = 800
MAX_CHUNK_SIZE = 1200
SECTION_HEADER_MAX_LENGTH = 80


def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _is_section_header(line: str) -> bool:
    """
    Detect if a line is a section header.
    Heuristic: ALL CAPS and length < 80 characters.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > SECTION_HEADER_MAX_LENGTH:
        return False
    # Check if mostly uppercase (at least 80% uppercase letters)
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    uppercase_count = sum(1 for c in letters if c.isupper())
    return (uppercase_count / len(letters)) >= 0.8


def _chunk_text(text: str) -> list[dict]:
    """
    Split text into chunks of approximately 800-1200 characters.
    Tries to preserve section headers.
    
    Returns list of dicts with keys: chunk_id, section, text, char_count
    """
    lines = text.split("\n")
    chunks = []
    current_section = "GENERAL"
    current_chunk = []
    current_size = 0
    chunk_id = 0
    
    for line in lines:
        # Check if this is a section header
        if _is_section_header(line):
            # Save current chunk if it exists
            if current_chunk:
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "chunk_id": chunk_id,
                    "section": current_section,
                    "text": chunk_text,
                    "char_count": len(chunk_text)
                })
                chunk_id += 1
                current_chunk = []
                current_size = 0
            
            # Update section
            current_section = line.strip()
            continue
        
        # Add line to current chunk
        line_size = len(line) + 1  # +1 for newline
        
        # If adding this line exceeds MAX_CHUNK_SIZE, save current chunk
        if current_size + line_size > MAX_CHUNK_SIZE and current_size >= MIN_CHUNK_SIZE:
            chunk_text = "\n".join(current_chunk)
            chunks.append({
                "chunk_id": chunk_id,
                "section": current_section,
                "text": chunk_text,
                "char_count": len(chunk_text)
            })
            chunk_id += 1
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    
    # Save final chunk if it exists
    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        chunks.append({
            "chunk_id": chunk_id,
            "section": current_section,
            "text": chunk_text,
            "char_count": len(chunk_text)
        })
    
    return chunks


def chunk_text_file(text_path: str, company_name: str) -> dict:
    """
    Chunk an extracted text file into smaller passages.
    
    Args:
        text_path: Path to the extracted text file.
        company_name: Name of the company (used for the saved filename).
    
    Returns:
        dict with keys:
            - chunks_saved_path: local path where chunks were saved
            - total_chunks: number of chunks created
            - total_chars: total number of characters across all chunks
    """
    if not os.path.exists(text_path):
        raise FileNotFoundError(f"Text file not found: {text_path}")
    
    # Read the text file
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Chunk the text
    chunks = _chunk_text(text)
    
    # Add company_name to each chunk
    for chunk in chunks:
        chunk["company_name"] = company_name
    
    # Calculate stats
    total_chunks = len(chunks)
    total_chars = sum(chunk["char_count"] for chunk in chunks)
    
    # Save to JSON
    safe_name = _safe_filename(company_name)
    chunks_path = os.path.join(CHUNKS_DIR, f"{safe_name}.json")
    
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    return {
        "chunks_saved_path": os.path.normpath(chunks_path),
        "total_chunks": total_chunks,
        "total_chars": total_chars,
    }
