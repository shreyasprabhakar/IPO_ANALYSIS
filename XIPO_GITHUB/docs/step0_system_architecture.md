# Step 0 -- System Architecture

## 1. Problem Statement

Indian retail investors lack accessible, structured tools for analysing IPO
(Initial Public Offering) Red Herring Prospectuses (RHPs). These documents,
filed with SEBI, typically span 300--600 pages and contain critical information
about financials, risks, business models, and fund utilisation. Manual reading
is impractical for most investors.

XIPO automates the end-to-end process: locate the prospectus, extract its
content, build a searchable knowledge base, generate an analyst-grade report,
compute a quantitative health score, and expose an interactive Q&A chatbot --
all from a single company name input.

---

## 2. High-Level Architecture

The system follows a layered, service-oriented design built on two processes:

```
[Streamlit Frontend]  --->  [FastAPI Backend]
                                   |
          +------------------------+------------------------+
          |            |           |           |            |
     SEBI Scraper  PDF Pipeline  RAG Engine  Financial   Health
      + Downloader   (Extract,    (FAISS +   Extractor    Score
                      Chunk,      Ollama)     (Regex)     (Percentile
                      Embed)                               Rank)
          |            |           |           |            |
          +------------+-----------+-----------+------------+
                                   |
                        [Local File System]
                        data/pdfs, extracted_text,
                        chunks, faiss, financials
```

### Frontend Layer (Streamlit)

- Single-page application in `frontend/app.py`.
- Communicates with the backend exclusively via HTTP (JSON over REST).
- Renders report sections, health score card, and a conversational chatbot.
- Manages client-side state with `st.session_state`.

### Backend Layer (FastAPI)

- Entry point: `backend/app/main.py`.
- Eleven routers registered under the `/api` prefix.
- Each router delegates to a corresponding service module under
  `backend/app/services/`.
- Routers handle HTTP concerns (validation, status codes); services contain
  pure business logic.

### Storage Layer (Local File System)

All intermediate and final artefacts are persisted under `data/`:

| Directory          | Contents                                     |
|--------------------|----------------------------------------------|
| `data/pdfs/`       | Downloaded RHP PDFs                          |
| `data/extracted_text/` | Plain-text extraction from PDFs          |
| `data/chunks/`     | Chunked JSON files (800--1200 chars each)    |
| `data/faiss/`      | FAISS index files and chunk metadata         |
| `data/financials/` | Metrics, ratios, and health score JSONs      |
| `data/training/`   | Pre-built training dataset for health scores |

---

## 3. Pipeline Stages

When a user enters a company name and clicks "Analyze IPO", the unified
`/api/analyze` endpoint orchestrates the following stages sequentially:

| Stage | Service                  | Input                         | Output                           |
|-------|--------------------------|-------------------------------|----------------------------------|
| 1     | `sebi_scraper`           | Company name                  | RHP HTML URL on SEBI             |
| 2     | `sebi_pdf_downloader`    | HTML URL                      | Downloaded PDF file              |
| 3     | `pdf_extractor`          | PDF file path                 | Plain text file                  |
| 4     | `chunker`                | Text file path                | JSON array of chunks             |
| 5     | `embedding_store`        | Chunks JSON path              | FAISS index + metadata           |
| 6     | `report_generator`       | Company name (uses RAG)       | 7-section analysis report        |
| 7     | `financial_extractor`    | Text file path                | Metrics JSON and ratios JSON     |
| 8     | `health_score`           | Ratios path + text path       | Score (0--100) with category     |

Stages are ordered by dependency: later stages depend on artefacts produced by
earlier stages. If any stage fails, the pipeline halts and returns an HTTP error
with a message indicating which stage failed.

---

## 4. Technology Stack

| Component           | Technology                                       | Rationale                                                    |
|---------------------|--------------------------------------------------|--------------------------------------------------------------|
| Backend framework   | FastAPI                                          | Async-capable, auto-generated OpenAPI docs, type safety      |
| Frontend framework  | Streamlit                                        | Rapid prototyping, built-in widgets, no HTML/CSS needed      |
| PDF extraction      | pdfplumber                                       | Reliable table/text extraction from scanned and digital PDFs |
| Embeddings          | SentenceTransformers (`all-MiniLM-L6-v2`)        | Lightweight (80 MB), fast inference, 384-dim vectors         |
| Vector search       | FAISS (`IndexFlatL2`)                            | In-process, no server dependency, exact L2 search            |
| LLM                 | Ollama (`llama3:8b`)                             | Fully local, no API keys, no cost, privacy-preserving        |
| Web scraping        | requests + BeautifulSoup                         | Standard library pair, sufficient for server-rendered pages  |
| Fuzzy matching      | difflib `SequenceMatcher`                        | No extra dependency, good enough for company name matching   |
| Financial extraction| Regex + heuristics                               | Zero-dependency, transparent, auditable extraction rules     |

---

## 5. Data Flow Summary

```
Company Name
    |
    v
SEBI Website --[scrape + fuzzy match]--> RHP HTML URL
    |
    v
RHP PDF --[pdfplumber]--> Plain Text (.txt)
    |
    v
Plain Text --[chunker]--> Chunks JSON (800-1200 chars each)
    |
    v
Chunks --[SentenceTransformer]--> Embeddings --[FAISS]--> Vector Index
    |
    v
Vector Index + Ollama --[RAG]--> 7-section Analysis Report
    |
    v
Plain Text --[regex]--> Financial Metrics --[arithmetic]--> Ratios
    |
    v
Ratios + Training Data --[percentile rank]--> Health Score (0-100)
    |
    v
All results --> JSON API Response --> Streamlit UI
```

---

## 6. Endpoint Map

All endpoints are registered under the `/api` prefix in `main.py`.

| Method | Resolved Path             | Purpose                        |
|--------|---------------------------|--------------------------------|
| GET    | `/`                       | Root health check              |
| GET    | `/api/health`             | Backend health status          |
| POST   | `/api/sebi/search`        | Search SEBI for RHP            |
| POST   | `/api/download`           | Download RHP PDF               |
| POST   | `/api/extract`            | Extract text from PDF          |
| POST   | `/api/chunk`              | Chunk extracted text           |
| POST   | `/api/faiss/build`        | Build FAISS index              |
| POST   | `/api/api/rag/ask`        | RAG Q&A (prefix stacking)      |
| POST   | `/api/financials/extract` | Extract financial metrics      |
| POST   | `/api/healthscore`        | Compute health score           |
| POST   | `/api/report/generate`    | Generate analysis report       |
| POST   | `/api/api/analyze`        | Unified pipeline (prefix stacking) |

Note: The `analyze` and `rag` routers use nested `/api` prefixes in their
router definitions, resulting in the `/api/api/...` paths when combined with the
global `/api` prefix in `main.py`. This is an intentional design choice for
internal consistency, documented in `BUGS_AND_FIXES.md`.

---

## 7. Key Architectural Decisions

1. **Monorepo structure.** Backend and frontend live in the same repository
   under `backend/` and `frontend/` respectively. This simplifies deployment
   and keeps documentation co-located.

2. **No database.** All data is stored as flat files (JSON, TXT, PDF, FAISS
   binary). This eliminates database setup and is sufficient for a
   single-user analysis tool.

3. **Local LLM.** Using Ollama with llama3:8b runs entirely on the user's
   machine. There is no dependency on external APIs, no cost per query, and
   no data is sent to third parties.

4. **Service-router separation.** Each route handler delegates to a service
   function. This means services can be tested and reused independently of
   the HTTP layer.

5. **Incremental caching.** If intermediate artefacts (PDF, text, FAISS index)
   already exist for a company, the pipeline can skip those stages on
   subsequent runs, reducing latency from minutes to seconds.
