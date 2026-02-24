# XIPO -- IPO RHP Analyzer

An AI-powered tool for analyzing Indian IPO Red Herring Prospectuses (RHPs).
Enter a company name and receive a full analysis report, financial health score,
and an interactive Q&A chatbot -- all powered by local LLM inference.

---

## Features

- **Automated SEBI Scraping** -- Locates and downloads the correct RHP from
  SEBI's public filings using fuzzy matching and document type detection.
- **RAG-Based Q&A** -- Chunks the prospectus, builds FAISS embeddings, and
  answers questions using Ollama (llama3:8b) running locally.
- **Financial Health Score** -- Extracts financial metrics via regex, computes
  ratios, and ranks the company against a training dataset using percentile
  scoring (0--100).
- **Automated Report Generation** -- Produces a 7-section analyst-style report
  covering company overview, business model, strengths, risks, financials,
  use of proceeds, and investment perspective.
- **Streamlit Frontend** -- Clean UI with health score card, report display,
  chatbot, and Developer Mode for debugging.

---

## Tech Stack

| Component       | Technology                                |
|-----------------|-------------------------------------------|
| Backend         | FastAPI + Uvicorn                         |
| Frontend        | Streamlit                                 |
| PDF Extraction  | pdfplumber                                |
| Embeddings      | SentenceTransformers (all-MiniLM-L6-v2)   |
| Vector Search   | FAISS (IndexFlatL2)                       |
| LLM             | Ollama (llama3:8b, local)                 |
| Web Scraping    | requests + BeautifulSoup                  |

---

## Project Structure

```
XIPO/
  backend/
    app/
      main.py              # FastAPI entry point
      routes/               # API route handlers
      services/             # Business logic (scraper, RAG, scoring, etc.)
    requirements.txt
  frontend/
    app.py                  # Streamlit UI
    requirements.txt
  data/
    training/               # Pre-built training dataset for health scores
    pdfs/                   # Downloaded RHP PDFs (generated at runtime)
    chunks/                 # Chunked text (generated at runtime)
    faiss/                  # FAISS indices (generated at runtime)
    financials/             # Extracted metrics (generated at runtime)
    extracted_text/         # Plain text from PDFs (generated at runtime)
    cache/                  # Cached data (generated at runtime)
  docs/                     # Technical documentation (14 files)
  HOW_TO_RUN.md             # Setup and running instructions
  BUGS_AND_FIXES.md         # Bug history and resolutions
```

---

## Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/) installed with the `llama3:8b` model pulled

### 1. Install Ollama and Pull Model

```bash
ollama pull llama3:8b
```

### 2. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://127.0.0.1:8000`. API docs at `http://127.0.0.1:8000/docs`.

### 3. Start Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Frontend opens at `http://localhost:8501`.

### 4. Analyze an IPO

Enter a company name (e.g., "Awfis") in the UI and click **Analyze IPO**.

For detailed setup instructions, see [HOW_TO_RUN.md](HOW_TO_RUN.md).

---

## Documentation

The `docs/` folder contains 14 technical documents covering:

| Document | Topic |
|----------|-------|
| `step0_system_architecture.md` | Full system overview and data flow |
| `step1_design_decisions.md` | Technology choices and trade-offs |
| `step2_sebi_scraper_architecture.md` | SEBI scraper deep dive |
| `step9_rag_testing.md` | RAG endpoint testing guide |
| `step9.5_improved_rag_testing.md` | Debug mode and response quality |
| `step9.6_quick_test.md` | Answer consistency verification |
| `step9.7_rag_architecture_deep.md` | RAG internals and prompt engineering |
| `step10_financial_extractor.md` | Financial extraction testing |
| `step11_healthscore.md` | Health score endpoint testing |
| `step11.5_model_theory.md` | Scoring methodology and math |
| `step11.8_report_generator.md` | Report generation testing |
| `step12_unified_pipeline.md` | Unified pipeline endpoint |
| `step12.5_frontend_architecture.md` | Frontend architecture |
| `step13_production_roadmap.md` | Production improvements roadmap |

---

## License

This project was developed for academic purposes.
