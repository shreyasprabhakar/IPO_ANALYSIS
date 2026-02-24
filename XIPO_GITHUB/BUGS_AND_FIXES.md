# XIPO -- Bugs Encountered and Fixes Applied

This document records all significant bugs encountered during the development of
the XIPO project, including the context in which each bug was discovered and the
solution that was applied.

---

## Bug 1: Missing `__init__.py` Files in ML Scorer Module

**Phase**: Backend Integration (Health Score Module)

**Symptom**: `ModuleNotFoundError: No module named 'ml_scorer'` when the backend
attempted to import the ML scorer package for computing financial health scores.

**Root Cause**: The `ml_scorer/`, `ml_scorer/runtime/`, `ml_scorer/extractors/`,
and `ml_scorer/features/` directories were missing `__init__.py` files. Python
requires these files to recognize directories as importable packages.

**Fix**: Created empty `__init__.py` files in all four directories.

**Lesson**: Always ensure that every Python package directory contains an
`__init__.py` file, even if it is empty.

---

## Bug 2: SEBI Scraper Returning Wrong Document Type

**Phase**: SEBI Scraping and Document Retrieval (Step 6)

**Symptom**: The scraper sometimes returned a Corrigendum or Addendum instead of
the actual RHP or DRHP document. This happened because the fuzzy match score for
a Corrigendum title could be higher than the correct RHP title.

**Root Cause**: The original matching logic used only fuzzy string similarity
without distinguishing between document types. Corrigendum titles often contained
the exact company name, yielding a higher match score than RHP titles which
sometimes included additional text.

**Fix**: Implemented a multi-step solution:
1. Added a document type detection mechanism to classify results as RHP, DRHP,
   Corrigendum, Addendum, or Other.
2. Introduced text normalization to strip common stopwords ("limited", "rhp",
   "india") from both the query and candidate titles before matching.
3. Modified the selection logic to prioritize RHP and DRHP documents over
   Corrigendum/Addendum, even if the latter had a higher raw fuzzy score.
4. Added a configurable threshold for weak matches, returning a "not_found"
   status with top alternatives when no suitable document was identified.

**Files Changed**: `backend/app/services/sebi_scraper.py`,
`backend/app/routes/analyze.py`

---

## Bug 3: Frontend Calling Wrong API Endpoint Prefix (Analyze)

**Phase**: Streamlit UI Implementation (Frontend Integration)

**Symptom**: The Streamlit frontend returned a `422 Unprocessable Entity` or
unexpected response when calling the analyze endpoint.

**Root Cause**: The `analyze` router in `backend/app/routes/analyze.py` defines
its own prefix as `/api/analyze`. When registered in `main.py` with an additional
`prefix="/api"`, the full resolved path becomes `/api/api/analyze`. The frontend
was initially calling `/api/analyze`, which did not match.

**Fix**: Updated the frontend in `frontend/app.py` to call
`{BACKEND_URL}/api/api/analyze` to match the actual resolved route.

**Files Changed**: `frontend/app.py`

---

## Bug 4: Frontend Calling Wrong API Endpoint Prefix (RAG Chatbot)

**Phase**: Chatbot Integration (Frontend-Backend Connection)

**Symptom**: The chatbot in the Streamlit UI returned a `404 Not Found` error
when submitting a question.

**Root Cause**: The `rag` router in `backend/app/routes/rag.py` was defined as
`APIRouter()` with no prefix, and the endpoint decorator was
`@router.post("/rag/ask")`. Combined with the `prefix="/api"` in `main.py`, the
resolved path was `/api/rag/ask`. However, the frontend was calling
`/api/api/rag/ask` for consistency with the analyze endpoint pattern.

**Fix**: Added `prefix="/api/rag"` to the `APIRouter()` constructor in `rag.py`
and shortened the endpoint decorator to `@router.post("/ask")`. This made the
resolved path `/api/api/rag/ask`, matching the frontend call.

**Files Changed**: `backend/app/routes/rag.py`

**Technical Detail**: FastAPI prefix stacking works by concatenating the
`include_router` prefix with the router-level prefix and then the endpoint path.
The analyze router already had a nested `/api/analyze` prefix, but the rag router
did not, creating an inconsistency.

---

## Bug 5: Ollama LLM Read Timeout During Report Generation

**Phase**: Report Generation and RAG Responses

**Symptom**: Report sections displayed error messages such as "Failed to call
Ollama" or "Read timed out" instead of actual analysis content. Some sections
generated successfully while others failed.

**Root Cause**: The default HTTP timeout for Ollama API calls was too short.
The `llama3:8b` model, running locally, occasionally takes longer than the
default timeout to generate responses, especially for complex or lengthy sections.

**Fix**: Applied a three-part solution:
1. Increased the Ollama API call timeout in `backend/app/services/rag_engine.py`
   from the default to 300 seconds.
2. Added a retry mechanism (one automatic retry) for timeout and connection
   errors in the RAG engine.
3. Created a `clean_report_text()` function in `frontend/app.py` that detects
   error keywords in report sections and replaces them with a user-friendly
   message instead of showing raw error text.

**Files Changed**: `backend/app/services/rag_engine.py`,
`backend/app/services/report_generator.py`, `frontend/app.py`

---

## Bug 6: Stale Session State Showing Old Company Results

**Phase**: Streamlit UI (User Experience)

**Symptom**: After analyzing one company and then searching for a different
company that was not found (404), the UI continued to display the previous
company's report and health score.

**Root Cause**: The Streamlit session state variables (`analyzed_company`,
`analysis_result`, `chat_history`) were not being cleared when a new search
resulted in an error or a 404 response.

**Fix**: Added explicit state clearing logic in `frontend/app.py` for both
404 (not found) and error (500) responses:

```python
st.session_state.analyzed_company = None
st.session_state.analysis_result = None
st.session_state.chat_history = []
```

**Files Changed**: `frontend/app.py`

---

## Bug 7: Company Name Whitespace Causing Match Failures

**Phase**: Streamlit UI (Input Handling)

**Symptom**: Entering a company name with leading or trailing spaces caused the
SEBI search to fail or return unexpected results.

**Root Cause**: The company name from the text input was sent directly to the
backend without trimming whitespace. The SEBI scraper's fuzzy matching was
sensitive to extra spaces.

**Fix**: Added `.strip()` to the company name before sending it to the backend:

```python
"company_name": company_name.strip()
```

**Files Changed**: `frontend/app.py`

---

## Bug 8: No Visibility Into Backend Errors for Debugging

**Phase**: Streamlit UI (Developer Experience)

**Symptom**: When the backend returned an error, the frontend showed only a
generic error message with no detail about the HTTP status code, URL, or
response body. This made debugging difficult.

**Root Cause**: The original error handling in `frontend/app.py` discarded the
response details and showed only a simplified message.

**Fix**: Implemented a two-part solution:
1. Added a Developer Mode toggle that, when enabled, shows a debug expander
   with the full HTTP status code, request URL, and raw JSON or text response.
2. In production mode (Developer Mode off), errors are displayed cleanly
   without raw JSON dumps.

**Files Changed**: `frontend/app.py`

---

## Bug 9: 404 Response Not Showing Suggestions

**Phase**: Streamlit UI (SEBI Search Feedback)

**Symptom**: When a company was not found on SEBI, the UI showed only a generic
"Error 404" message without displaying the top alternative matches that the
backend was returning.

**Root Cause**: The frontend was not parsing the JSON body of 404 responses.
The backend's `analyze` endpoint returns a structured 404 response containing
`top_matches` with alternative company names and their match scores, but the
frontend treated all non-200 responses the same way.

**Fix**: Added specific handling for 404 responses in `frontend/app.py`:
- Parse the JSON body to extract `top_matches`
- Display a "Did you mean one of these?" section with company names and scores
- Show debug information in Developer Mode

**Files Changed**: `frontend/app.py`

---

## Bug 10: Duplicate Analyze Requests on Button Double-Click

**Phase**: Streamlit UI (Request Management)

**Symptom**: Rapidly clicking the "Analyze IPO" button could trigger multiple
concurrent analysis requests, leading to duplicate processing and potential
race conditions.

**Root Cause**: Streamlit reruns the entire script on each interaction. Without
a guard, each click triggered a new backend call even if a previous one was
still in progress.

**Fix**: Added an `is_analyzing` flag in session state:
- Set to `True` when analysis starts
- Disables the button during processing
- Reset to `False` in a `finally` block to ensure cleanup even on errors

**Files Changed**: `frontend/app.py`

---

## Summary Table

| Bug | Phase | Severity | Root Cause Category |
|-----|-------|----------|---------------------|
| 1. Missing `__init__.py` | Backend Integration | Critical | Module structure |
| 2. Wrong document type from SEBI | SEBI Scraping | High | Matching algorithm |
| 3. Wrong endpoint prefix (analyze) | Frontend Integration | Critical | Routing configuration |
| 4. Wrong endpoint prefix (RAG) | Chatbot Integration | Critical | Routing configuration |
| 5. Ollama read timeout | Report Generation | High | Timeout configuration |
| 6. Stale session state | UI/UX | Medium | State management |
| 7. Whitespace in company name | UI/UX | Low | Input sanitization |
| 8. No debug visibility | Developer Experience | Medium | Error handling |
| 9. 404 not showing suggestions | UI/UX | Medium | Response parsing |
| 10. Duplicate requests | UI/UX | Medium | Concurrency guard |
