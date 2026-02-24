# Step 12.5 -- Frontend Architecture (Streamlit UI)

## 1. Overview

The XIPO frontend is a single-file Streamlit application (`frontend/app.py`,
~400 lines) that provides three user-facing features:

1. **Company analysis** -- enter a company name and receive a full IPO report.
2. **Health score display** -- a colour-coded card showing the financial health
   rating (0--100).
3. **Chatbot Q&A** -- ask follow-up questions about the analysed company using
   the RAG pipeline.

The frontend communicates with the FastAPI backend exclusively via HTTP POST
requests.

---

## 2. Application Layout

```
+-------------------------------------------------------+
|  XIPO -- IPO RHP Analyzer                              |
|  [ ] Developer Mode                                    |
|--------------------------+----------------------------|
|  [Company Name Input    ] | [Analyze IPO]             |
|--------------------------------------------------------|
|  Health Score Card (score/100, category, explanation)   |
|--------------------------------------------------------|
|  IPO Analysis Report                                   |
|    - Company Overview                                  |
|    - Business Model                                    |
|    - Key Strengths                                     |
|    - Key Risks                                         |
|    - Financial Highlights                              |
|    - Use of Proceeds                                   |
|    - Investment Recommendation                         |
|--------------------------------------------------------|
|  Ask Questions About This IPO                          |
|    Chat History (Q1/A1, Q2/A2, ...)                    |
|  [Question Input                ] [Ask]                |
|--------------------------------------------------------|
|  Footer                                                |
+--------------------------------------------------------+
```

All sections below the input bar are conditionally rendered: they appear only
after a successful analysis. The chatbot section appears only when a company
has been analysed and a FAISS index is available.

---

## 3. Session State Management

Streamlit reruns the entire script on every user interaction (button click,
text input change, checkbox toggle). To persist data across reruns, XIPO uses
`st.session_state`:

| Key                | Type          | Purpose                                 |
|--------------------|---------------|-----------------------------------------|
| `analyzed_company` | `str or None` | Currently analysed company name         |
| `analysis_result`  | `dict or None`| Full backend response for the analysis  |
| `chat_history`     | `list`        | List of `(question, answer)` tuples     |
| `debug_response`   | `dict or None`| Debug metadata from the last API call   |
| `is_analyzing`     | `bool`        | Guard flag to prevent duplicate requests|
| `developer_mode`   | `bool`        | Toggle for showing raw backend responses|

### Initialisation Pattern

Each state variable is initialised with a guard to prevent resetting on rerun:

```python
if "analyzed_company" not in st.session_state:
    st.session_state.analyzed_company = None
```

### State Clearing on New Search

When the user searches for a different company, all state is cleared to
prevent stale data from appearing:

```python
st.session_state.analyzed_company = None
st.session_state.analysis_result = None
st.session_state.chat_history = []
```

This clearing happens on both 404 (not found) and error (500) responses.

---

## 4. Backend Communication

### Two API Calls

The frontend makes exactly two types of HTTP requests:

| Function           | Endpoint                     | Timeout | Purpose              |
|--------------------|------------------------------|---------|----------------------|
| `analyze_company()`| `POST /api/api/analyze`      | 600s    | Full pipeline analysis|
| `ask_question()`   | `POST /api/api/rag/ask`      | 60s     | Single RAG Q&A       |

### Why the Double `/api/api/` Prefix

The backend registers routers with `prefix="/api"` in `main.py`. The `analyze`
and `rag` routers also define their own `/api` prefix internally. This results
in prefix stacking: `/api` (main.py) + `/api/analyze` (router) =
`/api/api/analyze`. The frontend matches this resolved path.

### Response Handling

The `analyze_company()` function classifies responses into three categories:

| Status Code | Internal Status | Action                                    |
|-------------|-----------------|-------------------------------------------|
| 200         | `success`       | Store result in session state, display UI |
| 404         | `not_found`     | Clear state, show "Did you mean?" suggestions |
| Other       | `error`         | Clear state, show error message            |

All responses capture debug metadata (status code, URL, response text) for
the Developer Mode expander.

---

## 5. Feature Details

### 5.1 Developer Mode

A checkbox at the top of the page toggles Developer Mode. When enabled:

- Error responses show the raw HTTP status code and response body.
- Successful analyses show a "Raw Backend Response" expander with the full
  JSON payload.
- 404 responses show the debug expander with URL and response details.

When disabled, errors show only user-friendly messages. This separation
ensures that end users see clean output while developers can troubleshoot
backend issues.

### 5.2 Health Score Card

The health score is rendered as a two-column layout:

- **Left column:** `st.metric()` widget showing the numeric score (e.g.,
  "75/100") with the category as a delta label.
- **Right column:** Colour-coded emoji and the explanation text.

The health score section only renders if the `health_score` key is present
and non-null in the analysis result.

### 5.3 Report Display

The `display_report()` function renders each section conditionally:

```python
if "company_overview" in report_data:
    st.subheader("Company Overview")
    st.write(clean_report_text(report_data["company_overview"]))
```

Each section's text is passed through `clean_report_text()` before rendering.

### 5.4 Error Text Cleaning

The `clean_report_text()` function detects error keywords in report section
text:

```python
error_keywords = [
    "Error retrieving information",
    "Failed to call Ollama",
    "Read timed out",
]
```

If any keyword is found, the raw error string is replaced with:
"This section could not be generated due to a temporary LLM timeout.
Please try again."

This prevents users from seeing backend stack traces or technical error
messages in the report sections.

### 5.5 Report Key Fallback

The backend may return the report under different keys depending on the
version. The frontend tries multiple keys in order:

```python
for k in ["report", "analysis_report", "analysis", "ipo_report", "final_report"]:
    if k in data and data[k]:
        report_data = data[k]
        break
```

This ensures forward compatibility if the backend response structure changes.

### 5.6 Chatbot

The chatbot maintains conversation history in `st.session_state.chat_history`
as a list of `(question, answer)` tuples. On each successful answer:

1. The tuple is appended to the history list.
2. `st.rerun()` is called to refresh the page and display the new entry.

The chatbot is only shown when `st.session_state.analyzed_company` is set,
ensuring the user cannot ask questions before an analysis is complete.

### 5.7 Duplicate Request Prevention

The `is_analyzing` flag prevents double-clicks from triggering multiple
backend calls:

```python
if st.session_state.is_analyzing:
    st.warning("Analysis already in progress...")
else:
    st.session_state.is_analyzing = True
    try:
        # ... perform analysis ...
    finally:
        st.session_state.is_analyzing = False
```

The `finally` block ensures the flag is always reset, even if an exception
occurs.

---

## 6. Input Sanitisation

Company names are stripped of whitespace before being sent to the backend:

```python
"company_name": company_name.strip()
```

This prevents match failures caused by accidental leading or trailing spaces
in the text input.

---

## 7. Limitations

1. **No persistent storage.** Closing the browser tab loses all session state,
   including chat history. There is no database or cookie-based persistence.

2. **Full-page reruns.** Streamlit's execution model means the entire script
   runs on every interaction. This can cause brief flickers and requires
   careful use of session state to avoid re-triggering API calls.

3. **No progress updates during analysis.** The spinner shows a generic
   "Analyzing..." message. There is no feedback about which pipeline stage
   is currently running.

4. **Single company at a time.** Analysing a new company clears the previous
   result. Side-by-side comparison is not supported.

---

## 8. Viva Preparation: Key Questions

**Q: Why does the frontend use a 600-second timeout for the analyze endpoint?**
A: The full analysis pipeline involves downloading a PDF from SEBI, extracting
text, building a FAISS index, and generating 7 LLM responses. On a CPU-only
machine, this can take 3--5 minutes. The 600-second (10-minute) timeout
provides sufficient margin.

**Q: How does the frontend prevent stale data from displaying?**
A: Every non-200 response triggers explicit clearing of `analyzed_company`,
`analysis_result`, and `chat_history` in session state. This ensures the UI
never shows results from a previously analysed company after a failed search.

**Q: What is the Developer Mode toggle for?**
A: It controls whether raw backend responses (JSON payloads, HTTP status codes,
request URLs) are shown in expandable sections. In production mode, users see
only clean, human-readable output.

**Q: How does the chatbot maintain conversation history?**
A: Each Q&A pair is appended to `st.session_state.chat_history`, which is a
Python list that persists across Streamlit reruns. The history is reset when
a new company is analysed.
