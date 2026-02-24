# Step 10: Financial Metrics Extractor — Testing Guide

## Created / Modified Files

| File | Action |
|---|---|
| `backend/app/services/financial_extractor.py` | **NEW** — Extracts 7 financial metrics via regex, computes 3 ratios |
| `backend/app/routes/financials.py` | **NEW** — `POST /api/financials/extract` endpoint |
| `backend/app/main.py` | **MODIFIED** — Registered `financials_router` |

## How to Test

### 1. Start the server

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Open Swagger UI

Navigate to **http://localhost:8000/docs**

### 3. Test the endpoint

Use `POST /api/financials/extract` with:

```json
{
  "company_name": "Reva Diamonds",
  "text_saved_path": "data/extracted_text/reva_diamonds.txt"
}
```

### 4. Expected response structure

```json
{
  "company_name": "Reva Diamonds",
  "metrics_saved_path": "data\\financials\\reva_diamonds_metrics.json",
  "ratios_saved_path": "data\\financials\\reva_diamonds_ratios.json",
  "extracted_metrics": {
    "revenue": 1234.56,
    "pat": 100.0,
    "ebitda": 200.0,
    "total_assets": 5000.0,
    "net_worth": 3000.0,
    "total_debt": 1500.0,
    "eps": 10.5,
    "extraction_notes": ["revenue: extracted via pattern '...'", "..."],
    "currency_unit_guess": "₹ in lakhs"
  },
  "ratios": {
    "net_profit_margin": 0.081,
    "ebitda_margin": 0.162,
    "debt_to_equity": 0.5
  }
}
```

> **Note:** Actual numeric values depend on the RHP text content. Some metrics may be `null` if the regex patterns don't find a matching value in the document.

### 5. Verify saved files

Check that JSON files were created in:
- `data/financials/reva_diamonds_metrics.json`
- `data/financials/reva_diamonds_ratios.json`

## What is NOT implemented (by design)

- ML-based health score
- UI / Streamlit frontend
- No new pip dependencies added
