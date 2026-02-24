# Quick Test: Step 9.6 - Consistent Answer Quality

## Goal
Verify that debug mode ONLY controls response fields, NOT answer quality.

## Quick Test

### 1. Test Same Question in Both Modes

**Normal Mode:**
```bash
curl -X POST "http://localhost:8000/api/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "reva diamonds",
    "question": "What is the total issue size?",
    "debug": false
  }'
```

**Debug Mode:**
```bash
curl -X POST "http://localhost:8000/api/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "reva diamonds",
    "question": "What is the total issue size?",
    "debug": true
  }'
```

### 2. Verify Answer Quality

**Expected Results:**
- ✅ The `answer` field should be IDENTICAL in both responses
- ✅ Answer should be detailed, structured, analyst-style
- ✅ Answer should NEVER mention: chunks, retrieval, FAISS, embeddings, context
- ✅ Debug mode should ONLY add extra fields: `sources`, `retrieved_chunks_count`, `retrieved_context_preview`

### 3. Quick API Docs Test

1. Go to: `http://localhost:8000/docs`
2. Find `/api/rag/ask` endpoint
3. Test with `debug: false` - note the answer
4. Test with `debug: true` - verify answer is identical

## Validation Checklist

- [ ] Same question with `debug=false` and `debug=true` produces identical `answer` field
- [ ] Answer quality is professional and detailed in both modes
- [ ] Answer never mentions technical terms (chunks, FAISS, etc.)
- [ ] Debug mode only adds metadata fields, not different answer content
- [ ] Normal mode returns only: `company_name`, `question`, `answer`
- [ ] Debug mode returns: `company_name`, `question`, `answer`, `sources`, `retrieved_chunks_count`, `retrieved_context_preview`

## Implementation Note

✅ **Already Implemented Correctly**

The code already ensures:
1. Same prompt used regardless of debug mode (lines 94-109)
2. Same Ollama API call regardless of debug mode (lines 112-128)
3. Same answer generated regardless of debug mode (line 125)
4. Debug parameter ONLY controls return fields (lines 130-141)

No code changes were needed for Step 9.6!
