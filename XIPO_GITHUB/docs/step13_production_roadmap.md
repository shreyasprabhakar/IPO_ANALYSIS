# Step 13 -- Production Roadmap

This document outlines what would need to change to take XIPO from a
local development prototype to a production-grade deployable application.
Each section identifies a current limitation, proposes a concrete improvement,
and notes the effort involved.

---

## 1. Infrastructure

### 1.1 Containerisation

**Current state:** The application runs directly on the developer's machine
with a local Python virtual environment. Setup requires manual installation of
dependencies, Ollama, and model weights.

**Production approach:**

- Package the backend as a Docker container with all Python dependencies
  pre-installed.
- Package the frontend as a separate container.
- Use Docker Compose to orchestrate backend, frontend, and Ollama.
- Mount `data/` as a persistent volume so indexed data survives container
  restarts.

**Benefit:** One-command deployment on any machine with Docker installed.

### 1.2 Cloud Deployment

**Current state:** Runs on `localhost` only.

**Production approach:**

- Deploy backend on a cloud platform (AWS ECS, GCP Cloud Run, or Azure
  Container Instances).
- Deploy frontend on the same platform or a static hosting service.
- Use a reverse proxy (Nginx or Caddy) to route `/api/` to the backend
  and `/` to the frontend.
- Configure HTTPS with a TLS certificate.

### 1.3 Database

**Current state:** All data stored as flat JSON and TXT files on the local
file system.

**Production approach:**

- Migrate metadata (company analysis results, health scores) to PostgreSQL
  or SQLite.
- Continue storing FAISS index files on disk (FAISS does not support database
  storage natively).
- Store PDF files in object storage (S3 or GCS) rather than local disk.

**Benefit:** Supports concurrent access, querying, and backup/restore.

---

## 2. Performance and Scalability

### 2.1 LLM Inference

**Current state:** Ollama runs on CPU. Report generation takes 3--5 minutes.

**Improvements:**

| Improvement                    | Expected Impact                      |
|--------------------------------|--------------------------------------|
| GPU-accelerated Ollama         | 5--10x faster inference              |
| Smaller model (e.g., Phi-3)   | 2--3x faster with slight quality loss|
| Parallel section generation    | Generate 7 report sections concurrently instead of sequentially |
| Response streaming             | Show partial answers as they generate |
| Cloud LLM API (fallback)      | Sub-second latency for premium users |

### 2.2 Embedding Caching

**Current state:** `SentenceTransformer` model is loaded fresh for every RAG
query.

**Improvement:** Load the model once at application startup and keep it in
memory. This eliminates the 2--3 second model loading overhead per query.

### 2.3 FAISS Index Management

**Current state:** One flat index file per company.

**Improvements:**

- Merge all company indices into a single partitioned index.
- Use `IndexIVFFlat` or `IndexHNSW` for sub-linear search at scale.
- Add metadata filtering (by section, by chunk type) using a hybrid
  search approach.

---

## 3. Data Quality

### 3.1 Financial Extraction Accuracy

**Current state:** Regex patterns extract 7 metrics. Some documents yield
`null` for most metrics due to unusual formatting.

**Improvements:**

- Add table-aware extraction using pdfplumber's table detection API.
- Use an LLM to extract metrics from tables where regex fails.
- Validate extracted values against expected ranges (e.g., revenue should
  be positive, margins should be between -1 and 1).
- Add support for multiple time periods (extract 3 years of data instead
  of just the latest).

### 3.2 Chunking Quality

**Current state:** Fixed character-based chunking with section header
detection.

**Improvements:**

- Implement semantic chunking: split at paragraph or sentence boundaries
  rather than at a fixed character count.
- Add overlap between adjacent chunks (e.g., 100-character overlap) to
  prevent information loss at chunk boundaries.
- Detect and preserve tables as atomic chunks rather than splitting them
  mid-row.

### 3.3 Training Dataset Expansion

**Current state:** ~68 companies in the health score reference dataset.

**Improvement:** Expand to 500+ companies across all SEBI-listed sectors by
scraping historical IPO data and computing metrics programmatically.

---

## 4. Reliability

### 4.1 Error Recovery

**Current state:** If any pipeline stage fails, the entire analysis fails
with an HTTP error.

**Improvements:**

- Implement partial results: if financial extraction fails but the report
  succeeds, return the report with a warning flag.
- Add a task queue (Celery or RQ) so long-running analyses do not block
  the API server.
- Implement idempotent retries: if a user refreshes during analysis, resume
  from the last completed stage instead of restarting.

### 4.2 Health Checks and Monitoring

**Current state:** A single `/api/health` endpoint returns a static message.

**Improvements:**

- Check Ollama connectivity in the health endpoint.
- Check disk space availability.
- Add structured logging (JSON format) for all service calls.
- Integrate with a monitoring service (Prometheus + Grafana, or Datadog).

### 4.3 Rate Limiting

**Current state:** No rate limiting on any endpoint.

**Improvement:** Add rate limiting to prevent abuse, especially on the
`/api/analyze` endpoint which triggers external requests to SEBI.

---

## 5. Security

### 5.1 Input Validation

**Current state:** Pydantic models validate field types but not content.

**Improvements:**

- Sanitise company name input to prevent path traversal attacks (the
  `_safe_filename` function partially addresses this).
- Add maximum length limits to all string inputs.
- Validate that file paths in requests point to expected directories only.

### 5.2 Authentication

**Current state:** All endpoints are public with no authentication.

**Improvement:** Add API key authentication or OAuth2 for production use.

### 5.3 CORS

**Current state:** No CORS configuration (frontend and backend run on
different ports locally).

**Improvement:** Configure explicit CORS origins for the production frontend
domain.

---

## 6. User Experience

### 6.1 Progress Indicators

**Current state:** Streamlit shows a spinner during analysis with no detail.

**Improvement:** Implement server-sent events (SSE) or WebSocket to stream
pipeline progress to the frontend. Show which stage is currently executing
and an estimated time remaining.

### 6.2 Company Suggestions

**Current state:** When a company is not found, the UI shows top matches
from the current SEBI listings.

**Improvement:** Maintain a cached list of all known SEBI filings and provide
autocomplete suggestions as the user types.

### 6.3 Report Export

**Current state:** Reports are displayed in the UI only.

**Improvement:** Add PDF and DOCX export functionality for the analysis
report.

### 6.4 Comparison Mode

**Current state:** Only one company can be analysed at a time.

**Improvement:** Allow side-by-side comparison of two IPOs, including
health scores, financial metrics, and report sections.

---

## 7. Testing

### 7.1 Automated Tests

**Current state:** No automated test suite. Testing is done manually via
Swagger UI.

**Improvements:**

- Add unit tests for all service functions using pytest.
- Add integration tests that mock Ollama responses and SEBI pages.
- Add end-to-end tests using a test FAISS index with known chunks.
- Set up CI/CD (GitHub Actions) to run tests on every pull request.

### 7.2 Test Data

**Current state:** Test data is generated by running the pipeline on real
SEBI documents.

**Improvement:** Create a fixed test dataset with known expected outputs for
each pipeline stage. This enables regression testing without depending on
SEBI availability.

---

## 8. Priority Matrix

| Improvement                        | Impact | Effort | Priority |
|------------------------------------|--------|--------|----------|
| Embedding model caching            | High   | Low    | P0       |
| Docker containerisation            | High   | Medium | P1       |
| Automated test suite               | High   | Medium | P1       |
| GPU-accelerated Ollama             | High   | Low    | P1       |
| Parallel report generation         | Medium | Medium | P2       |
| Semantic chunking                  | Medium | Medium | P2       |
| PostgreSQL migration               | Medium | High   | P2       |
| Progress streaming (SSE/WebSocket) | Medium | Medium | P2       |
| Training dataset expansion         | Medium | High   | P3       |
| LLM-based financial extraction     | Medium | High   | P3       |
| Report PDF export                  | Low    | Low    | P3       |
| Company comparison mode            | Low    | Medium | P3       |

---

## 9. Viva Preparation: Key Questions

**Q: What is the biggest bottleneck in the current system?**
A: LLM inference. Report generation requires 7 sequential LLM calls, each
taking 10--30 seconds on CPU. GPU acceleration or a faster model would
reduce total time from minutes to seconds.

**Q: How would you scale this to handle 100 concurrent users?**
A: Three changes: (1) Add a task queue so analysis runs asynchronously, (2)
deploy multiple backend instances behind a load balancer, (3) use a cloud LLM
API or GPU-accelerated Ollama to handle concurrent inference requests.

**Q: What would break first in production?**
A: The SEBI scraper, because it depends on SEBI's website structure and could
be blocked by rate limiting or CAPTCHA. A more robust approach would cache
known filings and only scrape for new/unknown companies.

**Q: How would you add multi-user authentication?**
A: Add FastAPI OAuth2 middleware with JWT tokens. Each user's analysis data
would be namespaced by user ID in the database and file system.
