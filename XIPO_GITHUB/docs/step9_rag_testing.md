# Testing the RAG Endpoint (Step 9)

## Overview
The RAG (Retrieval-Augmented Generation) endpoint retrieves relevant chunks from FAISS and generates answers using Ollama.

## Prerequisites
- Backend server running: `uvicorn app.main:app --reload` (in `backend/` directory)
- Ollama running locally with `llama3:8b` model
- FAISS index built for at least one company (e.g., "reva diamonds")

## Endpoint Details

**URL:** `POST /api/rag/ask`

**Request Body:**
```json
{
  "company_name": "reva diamonds",
  "question": "What is the issue size?",
  "top_k": 6
}
```

**Response:**
```json
{
  "company_name": "reva diamonds",
  "question": "What is the issue size?",
  "answer": "The issue size is up to ₹3,800 million...",
  "sources": [
    {
      "chunk_id": 2,
      "section": "DETAILS OF THE ISSUE"
    }
  ],
  "retrieved_chunks_count": 6
}
```

## Testing Steps

### 1. Verify Ollama is Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/generate -d '{"model":"llama3:8b","prompt":"test","stream":false}'
```

### 2. Test via API Documentation
Navigate to: `http://localhost:8000/docs`

Find the `/api/rag/ask` endpoint and test with:
```json
{
  "company_name": "reva diamonds",
  "question": "What is the total issue size?",
  "top_k": 6
}
```

### 3. Test via cURL
```bash
curl -X POST "http://localhost:8000/api/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "reva diamonds",
    "question": "What is the total issue size?",
    "top_k": 6
  }'
```

### 4. Test via Python
```python
import requests

response = requests.post(
    "http://localhost:8000/api/rag/ask",
    json={
        "company_name": "reva diamonds",
        "question": "What is the total issue size?",
        "top_k": 6
    }
)

print(response.json())
```

## Sample Questions to Test

1. **Issue Details:**
   - "What is the total issue size?"
   - "What is the price band for the IPO?"
   - "When does the issue open and close?"

2. **Company Information:**
   - "Who are the promoters of the company?"
   - "What is the company's business?"
   - "Where is the registered office located?"

3. **Financial Information:**
   - "What are the objects of the issue?"
   - "How will the funds be utilized?"

## Expected Behavior

- **Success (200):** Returns answer with sources and chunk count
- **Not Found (404):** If FAISS index doesn't exist for the company
- **Server Error (500):** If Ollama is not running or other errors occur

## Troubleshooting

### Error: "FAISS index not found"
- Ensure you've built the FAISS index using `/api/faiss/build`
- Check that the company name matches exactly

### Error: "Failed to call Ollama API"
- Verify Ollama is running: `ollama serve`
- Check the model is available: `ollama list`
- Pull the model if needed: `ollama pull llama3:8b`

### Slow Response
- Ollama may take 10-30 seconds for first response
- Subsequent requests should be faster
- Consider reducing `top_k` if too slow
