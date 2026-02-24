"""
Financial Health Score Service
Computes a sector-wise Financial Health Score (0-100) for an IPO company
by comparing its ratios against companies in the same sector from the
training dataset, with GLOBAL fallback when sector is missing or unseen.
"""

import os
import re
import json
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TRAINING_PATH = os.path.join(_BASE_DIR, "data", "training", "ipo_training_data_scored.json")
FINANCIALS_DIR = os.path.join(_BASE_DIR, "data", "financials")
os.makedirs(FINANCIALS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Feature mapping: ratios JSON key -> training dataset metric key
# ---------------------------------------------------------------------------

_RATIO_TO_METRIC = {
    "ebitda_margin": "ebitda_margin_avg",
    "net_profit_margin": "pat_margin_avg",
    "debt_to_equity": "debt_to_equity_latest",
}

# Features where *lower* is better (percentile is inverted)
_LOWER_IS_BETTER = {"debt_to_equity_latest"}

# All possible training metric keys
_ALL_METRIC_KEYS = [
    "ebitda_margin_avg",
    "pat_margin_avg",
    "revenue_cagr",
    "pat_cagr",
    "current_ratio_latest",
    "debt_to_equity_latest",
    "interest_coverage_latest",
    "asset_turnover_latest",
    "ocf_to_pat_avg",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


# ---------------------------------------------------------------------------
# A) extract_sector_from_text
# ---------------------------------------------------------------------------

_SECTOR_KEYWORDS = [
    r"(?:Industry|Sector)\s*:\s*([A-Za-z &/,]+)",
    r"(?:Industry|Sector)\s*[-–]\s*([A-Za-z &/,]+)",
    r"Business\s+Overview\b.*?(Manufacturing|Financial Services|IT Services"
    r"|Pharmaceuticals|FMCG|Healthcare|Infrastructure|Real Estate"
    r"|Chemicals|Textiles|Media|Energy|Retail|Logistics|Mining)",
]


def extract_sector_from_text(text_path: str) -> Optional[str]:
    """
    Scan the RHP text file for sector / industry keywords and return the
    detected sector string, or None if not found.
    """
    if not os.path.exists(text_path):
        return None

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Scan first 100k characters for speed
    snippet = text[:100000]

    for pattern in _SECTOR_KEYWORDS:
        match = re.search(pattern, snippet, re.IGNORECASE)
        if match:
            sector = match.group(1).strip().rstrip(".,;:")
            if sector:
                return sector

    return None


# ---------------------------------------------------------------------------
# B) load_training_dataset
# ---------------------------------------------------------------------------

def load_training_dataset() -> list:
    """Load ipo_training_data_scored.json and return a list of dicts."""
    with open(TRAINING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# C) compute_sector_statistics
# ---------------------------------------------------------------------------

def compute_sector_statistics(dataset: list, sector: Optional[str]) -> dict:
    """
    Filter the dataset by sector.  If the sector is None or no entries match,
    fall back to the full dataset.

    Returns:
        dict with keys: fallback_used, sector_used, total_companies_used, subset
    """
    if sector:
        subset = [
            entry for entry in dataset
            if entry.get("sector", "").strip().lower() == sector.strip().lower()
        ]
    else:
        subset = []

    if subset:
        return {
            "fallback_used": False,
            "sector_used": sector,
            "total_companies_used": len(subset),
            "subset": subset,
        }

    return {
        "fallback_used": True,
        "sector_used": "GLOBAL",
        "total_companies_used": len(dataset),
        "subset": dataset,
    }


# ---------------------------------------------------------------------------
# D) compute_health_score
# ---------------------------------------------------------------------------

def compute_health_score(
    company_name: str,
    ratios_path: str,
    text_path: str,
    debug: bool = False,
) -> dict:
    """
    Main orchestrator — computes the Financial Health Score for *company_name*.

    1. Load ratios from *ratios_path*
    2. Detect sector from *text_path*
    3. Filter training dataset by sector (with GLOBAL fallback)
    4. Compute percentile rank per feature within the sector subset
    5. Score = average percentile × 100
    6. Save result JSON to data/financials/<safe_name>_healthscore.json

    Returns:
        dict with company_name, sector_detected, sector_used, fallback_used,
        total_companies_used, score, category, features_used, feature_percentiles
    """
    # ---- Resolve paths relative to project root ----
    if not os.path.isabs(ratios_path):
        ratios_path = os.path.join(_BASE_DIR, ratios_path)
    if not os.path.isabs(text_path):
        text_path = os.path.join(_BASE_DIR, text_path)

    # ---- Load company ratios ----
    with open(ratios_path, "r", encoding="utf-8") as f:
        ratios = json.load(f)

    # Map ratios -> training feature names
    company_features = {}  # type: dict[str, Optional[float]]
    for ratio_key, metric_key in _RATIO_TO_METRIC.items():
        company_features[metric_key] = ratios.get(ratio_key)

    # Features the company's ratios file doesn't cover — set to None
    for key in _ALL_METRIC_KEYS:
        if key not in company_features:
            company_features[key] = None

    # ---- Sector detection ----
    sector_detected = extract_sector_from_text(text_path)

    # ---- Load dataset & filter ----
    dataset = load_training_dataset()
    stats = compute_sector_statistics(dataset, sector_detected)

    subset = stats["subset"]

    # ---- Percentile computation ----
    features_used = []     # type: list[str]
    feature_percentiles = {}  # type: dict[str, float]

    for metric_key in _ALL_METRIC_KEYS:
        company_val = company_features.get(metric_key)
        if company_val is None:
            continue

        # Collect all non-null values for this metric from the subset
        dataset_vals = [
            entry["metrics"][metric_key]
            for entry in subset
            if entry.get("metrics", {}).get(metric_key) is not None
        ]

        if not dataset_vals:
            continue

        # Compute percentile rank
        n = len(dataset_vals)
        if metric_key in _LOWER_IS_BETTER:
            # Lower is better → count how many are >= company value
            count = sum(1 for v in dataset_vals if v >= company_val)
        else:
            # Higher is better → count how many are <= company value
            count = sum(1 for v in dataset_vals if v <= company_val)

        percentile = count / n

        features_used.append(metric_key)
        feature_percentiles[metric_key] = round(percentile, 4)

    # ---- Final score ----
    if feature_percentiles:
        avg_percentile = sum(feature_percentiles.values()) / len(feature_percentiles)
        score = round(avg_percentile * 100, 2)
    else:
        score = 50.0  # default when no features available

    # Category
    if score < 40:
        category = "Weak"
    elif score <= 70:
        category = "Average"
    else:
        category = "Strong"

    # ---- Build full result ----
    full_result = {
        "company_name": company_name,
        "sector_detected": sector_detected,
        "sector_used": stats["sector_used"],
        "fallback_used": stats["fallback_used"],
        "total_companies_used": stats["total_companies_used"],
        "score": score,
        "category": category,
        "features_used": features_used,
        "feature_percentiles": feature_percentiles,
    }

    # ---- Save to JSON ----
    safe_name = _safe_filename(company_name)
    out_path = os.path.join(FINANCIALS_DIR, f"{safe_name}_healthscore.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_result, f, indent=2, ensure_ascii=False)

    full_result["healthscore_saved_path"] = os.path.normpath(out_path)

    # ---- Return clean or debug output ----
    if debug:
        return full_result

    # Clean output
    peer_percentile = round(score / 100.0, 4)
    
    # Build explanation
    explanation = f"This company is financially stronger than {int(peer_percentile * 100)}% of companies in the same sector."
    if stats["fallback_used"]:
        explanation += " (GLOBAL fallback used)"

    return {
        "company_name": company_name,
        "sector_used": stats["sector_used"],
        "score": score,
        "category": category,
        "peer_percentile": peer_percentile,
        "explanation": explanation,
    }
