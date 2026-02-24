# Step 12: Unified Pipeline Endpoint

## Overview
Created a single endpoint `/api/analyze` that runs the entire IPO analysis workflow from company name to final report.

## Implementation

### Files Created/Modified

#### Created:
- **`backend/app/routes/analyze.py`** - Unified pipeline router with POST `/api/analyze` endpoint

#### Modified:
- **`backend/app/main.py`** - Added analyze router to the FastAPI app

## Endpoint Details

### POST `/api/analyze`

Orchestrates the complete IPO analysis pipeline:

**Request Body:**
```json
{
  "company_name": "string",
  "top_k": 6,
  "debug": false
}
```

**Pipeline Steps:**
1. **SEBI RHP Search** - Search for company's RHP HTML URL
2. **PDF Download** - Download RHP PDF from SEBI
3. **Text Extraction** - Extract text from PDF using pdfplumber
4. **Chunking** - Split text into 800-1200 character chunks
5. **FAISS Index** - Build vector embeddings and FAISS index
6. **Report Generation** - Generate comprehensive IPO analysis report
7. **Financial Metrics** - Extract key financial metrics from text
8. **Financial Ratios** - Compute derived ratios (margins, debt-to-equity)
9. **Health Score** - Compute sector-wise financial health score (0-100)

**Response (debug=false):**
```json
{
  "company_name": "string",
  "analysis_report": {
    "company_overview": "...",
    "business_model": "...",
    "objects_of_issue": "...",
    "strengths": "...",
    "key_risks": "...",
    "financial_highlights": "...",
    "final_verdict": "..."
  },
  "health_score": {
    "score": 75.5,
    "category": "Good",
    "sector_used": "IT Services"
  },
  "financials": {
    "metrics": {
      "revenue": 1234.56,
      "pat": 234.56,
      "ebitda": 345.67,
      "total_assets": 5678.90,
      "net_worth": 2345.67,
      "total_debt": 1234.56,
      "eps": 12.34,
      "currency_unit_guess": "₹ in crores",
      "extraction_notes": [...]
    },
    "ratios": {
      "net_profit_margin": 0.19,
      "ebitda_margin": 0.28,
      "debt_to_equity": 0.53
    }
  },
  "chat_ready": true
}
```

**Response (debug=true):**
Includes all above fields plus:
```json
{
  "pdf_info": {
    "rhp_html_url": "...",
    "matched_company": "...",
    "match_score": 0.95,
    "pdf_url": "...",
    "pages_extracted": 350,
    "chars_extracted": 1234567
  },
  "file_paths": {
    "pdf_path": "...",
    "text_path": "...",
    "chunks_path": "...",
    "faiss_index_path": "...",
    "faiss_meta_path": "...",
    "metrics_path": "...",
    "ratios_path": "..."
  }
}
```

## Error Handling

All errors are caught and returned as clean HTTPException messages:

- **404** - No RHP found for company
- **500** - PDF download failed
- **500** - Text extraction failed
- **500** - FAISS index build failed
- **500** - Report generation failed
- **500** - Financial extraction failed
- **500** - Health score computation failed
- **500** - Unexpected error during analysis

## Testing

### Via FastAPI Docs

1. **Navigate to the API docs:**
   ```
   http://localhost:8000/docs
   ```

2. **Find the `/api/analyze` endpoint** under the "analyze" tag

3. **Click "Try it out"**

4. **Enter request body:**
   ```json
   {
     "company_name": "Zomato",
     "top_k": 6,
     "debug": true
   }
   ```

5. **Click "Execute"**

6. **Review the response** - should include:
   - Complete analysis report
   - Health score with category
   - Financial metrics and ratios
   - Debug info (if debug=true)

### Via cURL

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Zomato",
    "top_k": 6,
    "debug": false
  }'
```

### Expected Behavior

- **First run**: Will take 2-5 minutes as it downloads PDF, extracts text, builds FAISS index, etc.
- **Subsequent runs**: If data already exists, will reuse cached files (faster)
- **chat_ready: true**: Indicates FAISS index is built and RAG queries can be made via `/api/rag/ask`

## Notes

- No new dependencies added
- All services are orchestrated in correct order
- Proper error handling at each step
- Debug mode provides full transparency into the pipeline
- Production mode returns clean, user-friendly output
