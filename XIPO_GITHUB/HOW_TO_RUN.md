# XIPO -- How to Run

## 1. Project Overview

XIPO (eXtended IPO analyzer) is an end-to-end system for analyzing Indian IPO Red
Herring Prospectuses (RHPs). It automates the entire workflow from document
acquisition to investment insight generation.

**High-level pipeline:**

```
SEBI Scraping --> PDF Download --> Text Extraction --> Chunking --> FAISS Indexing
    --> RAG-based Report Generation --> Financial Metric Extraction
    --> ML Health Score --> Streamlit UI
```

The backend is built with FastAPI and exposes a RESTful API. The frontend is a
Streamlit application that orchestrates the full pipeline through a single user
action: entering a company name.

---

## 2. Folder Structure

```
XIPO/
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── main.py            # Application entry point and router registration
│   │   ├── routes/            # API route handlers
│   │   └── services/          # Core business logic (scraper, RAG engine, etc.)
│   ├── tests/                 # Unit and integration tests
│   └── requirements.txt       # Backend Python dependencies
│
├── frontend/                  # Streamlit UI application
│   ├── app.py                 # Main Streamlit application
│   └── requirements.txt       # Frontend Python dependencies
│
├── data/                      # All generated artifacts (created at runtime)
│   ├── pdfs/                  # Downloaded RHP PDF files
│   ├── extracted_text/        # Raw text extracted from PDFs
│   ├── chunks/                # Chunked text passages (JSON)
│   ├── faiss/                 # FAISS vector index and metadata files
│   ├── financials/            # Extracted financial metrics and computed ratios
│   ├── reports/               # Generated IPO analysis reports
│   ├── news/                  # Cached news data (if applicable)
│   └── training/              # ML training data for health score model
│
├── docs/                      # Step-by-step development documentation
├── models/                    # Trained ML model artifacts
├── notebooks/                 # Jupyter notebooks for experimentation
├── .venv/                     # Python virtual environment (local, not committed)
└── README.md
```

All directories under `data/` are populated automatically when the pipeline runs.
Artifacts are organized by company name within each subdirectory.

---

## 3. Requirements

| Requirement              | Details                                              |
|--------------------------|------------------------------------------------------|
| Python                   | 3.10 or higher                                       |
| Virtual environment      | Recommended (venv or conda)                          |
| Ollama                   | Required -- local LLM inference server               |
| LLM model                | `llama3:8b` (pulled via Ollama)                      |
| Internet access           | Required for SEBI website scraping and PDF download   |
| Operating system         | Windows 10/11 (tested); Linux/macOS should also work |

---

## 4. Setup Instructions

### Step A -- Clone or Download the Project

```bash
git clone <repository-url>
cd XIPO
```

Or download and extract the project archive, then navigate into the `XIPO` root
directory.

### Step B -- Create a Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step C -- Install Backend Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### Step D -- Install Frontend Dependencies

```powershell
cd ..\frontend
pip install -r requirements.txt
```

Return to the project root after installation:

```powershell
cd ..
```

---

## 5. Run the Backend

From the `backend/` directory, with the virtual environment activated:

```powershell
cd backend
uvicorn app.main:app --reload
```

- The server starts at **http://127.0.0.1:8000**
- Interactive API documentation (Swagger UI) is available at **http://127.0.0.1:8000/docs**
- The `--reload` flag enables hot-reloading during development

Verify the server is running by visiting the root endpoint:

```
GET http://127.0.0.1:8000/
Response: {"message": "XIPO backend running"}
```

---

## 6. Run the Frontend

Open a second terminal, activate the virtual environment, then run:

```powershell
cd frontend
streamlit run app.py
```

- The Streamlit UI opens automatically in the default web browser
- Enter a company name (e.g., "Awfis", "Flair Writing") and click **Analyze IPO**
- The system executes the full pipeline: SEBI search, PDF download, text
  extraction, chunking, FAISS indexing, report generation, financial extraction,
  and health scoring
- After analysis completes, a chatbot interface becomes available for follow-up
  questions

---

## 7. Ollama Setup

Ollama is required for all LLM-powered features including RAG-based question
answering and report generation.

### Installation

Download and install Ollama from [https://ollama.com](https://ollama.com).

### Pull the Required Model

```bash
ollama pull llama3:8b
```

### Start the Model

```bash
ollama run llama3:8b
```

Ollama must remain running in the background for the duration of your session.
The backend communicates with Ollama's local API (default: `http://localhost:11434`)
to generate answers and reports.

**Why Ollama is needed:** The RAG engine sends retrieved document chunks along
with user questions to the LLM for answer synthesis. The report generator uses
the same mechanism to produce structured IPO analysis sections. Without Ollama
running, all report generation and chatbot queries will fail.

---

## 8. API Endpoints

All endpoints are served by the FastAPI backend at `http://127.0.0.1:8000`.
Refer to the Swagger UI at `/docs` for full request/response schemas.

| Method | Endpoint                | Purpose                                              |
|--------|-------------------------|------------------------------------------------------|
| POST   | `/api/api/analyze`      | Run the complete IPO analysis pipeline for a company |
| POST   | `/api/api/rag/ask`      | Ask a follow-up question about an analyzed company   |
| POST   | `/api/sebi/search`      | Search SEBI for RHP documents by company name        |
| POST   | `/api/financials/extract` | Extract financial metrics from RHP text            |
| POST   | `/api/healthscore`      | Compute the financial health score                   |

### Primary Endpoints

**POST /api/api/analyze**

Orchestrates the entire pipeline. Accepts a `company_name` and returns the
analysis report, financial metrics, computed ratios, and a health score.

**POST /api/api/rag/ask**

Accepts a `company_name` and a `question`. Retrieves relevant chunks from the
FAISS index and generates an LLM-powered answer. Requires that the company has
been previously analyzed (FAISS index must exist).

---

## 9. Data Storage Behavior

All data artifacts are stored under the `data/` directory and are organized by
company name.

| Directory           | Contents                                              |
|---------------------|-------------------------------------------------------|
| `data/pdfs/`        | Downloaded RHP PDF files from SEBI                    |
| `data/extracted_text/` | Plain text extracted from PDFs                     |
| `data/chunks/`      | Text split into passage-level chunks (JSON format)    |
| `data/faiss/`       | FAISS vector index (`.index`) and metadata (`.json`)  |
| `data/financials/`  | Extracted financial metrics and computed ratios (JSON) |
| `data/reports/`     | Generated IPO analysis reports                        |

Each pipeline run for a new company creates a new set of files under these
directories. If a company has already been analyzed, existing artifacts (such as
the FAISS index) are reused for subsequent chatbot queries.

---

## 10. Troubleshooting

| Symptom                                     | Likely Cause                              | Resolution                                                                                     |
|---------------------------------------------|-------------------------------------------|------------------------------------------------------------------------------------------------|
| **404 Not Found** on API calls              | Incorrect endpoint prefix                 | Verify the URL matches the paths listed in Section 8. The `analyze` and `rag` endpoints use a double `/api/api/` prefix due to nested router configuration. |
| **Read timed out** during analysis          | Ollama is slow or unresponsive            | Increase the request timeout. Ensure Ollama is running and the `llama3:8b` model is loaded. First invocations are slower due to model loading. |
| **Unexpected EOF** or extraction errors     | Corrupted or non-standard PDF             | Re-download the PDF or try a different company. Some SEBI PDFs are scanned images and cannot be text-extracted. |
| **Report generation fails silently**        | Ollama is not running                     | Start Ollama with `ollama run llama3:8b` before using the application.                         |
| **Slow first-time processing**              | FAISS index being built from scratch      | The first analysis for any company is slower because it must download the PDF, extract text, build chunks, and create the FAISS index. Subsequent chatbot queries reuse the existing index. |
| **Connection refused** on backend           | Backend server not started                | Run `uvicorn app.main:app --reload` from the `backend/` directory.                             |
| **Module not found** errors                 | Dependencies not installed or wrong venv  | Ensure the virtual environment is activated and dependencies are installed per Section 4.       |
