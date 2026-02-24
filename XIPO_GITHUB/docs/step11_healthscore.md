# Step 11: Financial Health Score — Testing Guide

## Created / Modified Files

| File | Action |
|---|---|
| `backend/app/services/health_score.py` | **NEW** — Sector-wise health score (percentile-rank, GLOBAL fallback) |
| `backend/app/routes/healthscore.py` | **NEW** — `POST /api/healthscore` endpoint |
| `backend/app/main.py` | **MODIFIED** — Registered `healthscore_router` |

## How to Test

### 1. Start the server

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Open Swagger UI

Navigate to **http://localhost:8000/docs**

### 3. Prerequisite

You must already have:
- An extracted text file (e.g. `data/extracted_text/reva_diamonds.txt`)
- A ratios JSON file (e.g. `data/financials/reva_diamonds_ratios.json`) — produced by Step 10

### 4. Test the endpoint (Clean Output - Default)

Use `POST /api/healthscore` with:

```json
{
  "company_name": "Reva Diamonds",
  "ratios_saved_path": "data/financials/reva_diamonds_ratios.json",
  "text_saved_path": "data/extracted_text/reva_diamonds.txt",
  "debug": false
}
```

**Expected clean response:**

```json
{
  "company_name": "Reva Diamonds",
  "sector_used": "GLOBAL",
  "score": 89.9,
  "category": "Strong",
  "peer_percentile": 0.899,
  "explanation": "This company is financially stronger than 89% of companies in the same sector. (GLOBAL fallback used)"
}
```

### 5. Test debug mode (Full Details)

Use `POST /api/healthscore` with `"debug": true`:

```json
{
  "company_name": "Reva Diamonds",
  "ratios_saved_path": "data/financials/reva_diamonds_ratios.json",
  "text_saved_path": "data/extracted_text/reva_diamonds.txt",
  "debug": true
}
```

**Expected debug response:**

```json
{
  "company_name": "Reva Diamonds",
  "sector_detected": null,
  "sector_used": "GLOBAL",
  "fallback_used": true,
  "total_companies_used": 68,
  "score": 89.9,
  "category": "Strong",
  "features_used": ["pat_margin_avg", "debt_to_equity_latest"],
  "feature_percentiles": {
    "pat_margin_avg": 0.65,
    "debt_to_equity_latest": 0.60
  },
  "healthscore_saved_path": "data\\financials\\reva_diamonds_healthscore.json"
}
```

> **Note:** Actual values depend on the company's ratios and how they rank in the training dataset. `sector_detected` may be `null` if the RHP text does not contain recognisable sector keywords, in which case GLOBAL fallback is used.

### 6. Verify saved file

Check that the JSON file was created at:
- `data/financials/reva_diamonds_healthscore.json`

## What is NOT implemented (by design)

- Streamlit / frontend UI for health score
- ML-based model training — uses percentile ranking against training data
- No new pip dependencies added
