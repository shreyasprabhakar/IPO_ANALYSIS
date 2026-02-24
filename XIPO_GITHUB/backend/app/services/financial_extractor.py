"""
Financial Metrics Extractor Service
Extracts key financial metrics from RHP text using regex + heuristics,
and computes derived financial ratios.
"""

import os
import re
import json


# Directory for financial data
FINANCIALS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/financials")
)
os.makedirs(FINANCIALS_DIR, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


# ---------------------------------------------------------------------------
# Currency-unit detection
# ---------------------------------------------------------------------------

_CURRENCY_PATTERNS = [
    (r"₹\s*in\s+lakhs", "₹ in lakhs"),
    (r"₹\s*in\s+lakh", "₹ in lakhs"),
    (r"in\s+lakhs", "₹ in lakhs"),
    (r"₹\s*in\s+crores?", "₹ in crores"),
    (r"in\s+crores?", "₹ in crores"),
    (r"₹\s*in\s+millions?", "₹ in millions"),
    (r"in\s+millions?", "₹ in millions"),
    (r"₹\s*in\s+thousands?", "₹ in thousands"),
]


def _detect_currency_unit(text: str) -> str:
    """Scan text for currency-unit indicators and return the best guess."""
    text_lower = text[:50000].lower()  # scan only first 50k chars for speed
    for pattern, label in _CURRENCY_PATTERNS:
        if re.search(pattern, text_lower):
            return label
    return "unknown"


# ---------------------------------------------------------------------------
# Numeric value extraction helper
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(
    r"[₹]?\s*([\d,]+(?:\.\d+)?)"  # e.g. 1,234.56 or ₹ 1234
)


def _first_number_after(text, keyword_pattern):
    """
    Find the first numeric value appearing after `keyword_pattern` in *text*.
    Returns a float or None if nothing found.
    """
    match = re.search(keyword_pattern, text, re.IGNORECASE)
    if not match:
        return None
    # Look in the 300 characters following the keyword
    rest = text[match.end(): match.end() + 300]
    num_match = _NUMBER_RE.search(rest)
    if num_match:
        raw = num_match.group(1).replace(",", "")
        try:
            return float(raw)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Metric extraction definitions
# ---------------------------------------------------------------------------

# Each entry: (metric_key, list_of_regex_patterns_to_try)
_METRIC_PATTERNS = [
    ("revenue", [
        r"Revenue\s+from\s+Operations",
        r"Total\s+Revenue",
        r"Revenue",
    ]),
    ("pat", [
        r"Profit\s+After\s+Tax",
        r"\bPAT\b",
        r"Net\s+Profit",
        r"Profit\s+for\s+the\s+(?:year|period)",
    ]),
    ("ebitda", [
        r"\bEBITDA\b",
        r"Earnings\s+Before\s+Interest.*?Tax.*?Depreciation",
    ]),
    ("total_assets", [
        r"Total\s+Assets",
    ]),
    ("net_worth", [
        r"Net\s*[Ww]orth",
        r"Networth",
        r"Shareholders['\u2019]?\s*Funds",
    ]),
    ("total_debt", [
        r"Total\s+Debt",
        r"Total\s+Borrowings",
        r"Borrowings",
    ]),
    ("eps", [
        r"Basic\s+EPS",
        r"\bEPS\b",
        r"Earnings\s+Per\s+Share",
    ]),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_financial_metrics(text_path: str, company_name: str) -> dict:
    """
    Read the extracted RHP text file and attempt to extract key financial
    metrics using regex + heuristics.

    Args:
        text_path: Path to the extracted text file.
        company_name: Name of the company (used for saved filenames).

    Returns:
        dict with keys:
            - metrics_saved_path: path where metrics JSON was saved
            - extracted_metrics: dict of metric values (includes
              extraction_notes and currency_unit_guess)
    """
    if not os.path.exists(text_path):
        raise FileNotFoundError(f"Text file not found: {text_path}")

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Detect currency unit
    currency_unit = _detect_currency_unit(text)

    # Extract each metric
    metrics = {}
    notes = []

    for key, patterns in _METRIC_PATTERNS:
        value = None
        matched_pattern = None
        for pat in patterns:
            value = _first_number_after(text, pat)
            if value is not None:
                matched_pattern = pat
                break
        metrics[key] = value
        if value is not None:
            notes.append(f"{key}: extracted via pattern '{matched_pattern}'")
        else:
            notes.append(f"{key}: not found in text")

    # Build result payload
    extracted_metrics = {
        **metrics,
        "extraction_notes": notes,
        "currency_unit_guess": currency_unit,
    }

    # Save to JSON
    safe_name = _safe_filename(company_name)
    out_path = os.path.join(FINANCIALS_DIR, f"{safe_name}_metrics.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(extracted_metrics, f, indent=2, ensure_ascii=False)

    return {
        "metrics_saved_path": os.path.normpath(out_path),
        "extracted_metrics": extracted_metrics,
    }


def compute_ratios(extracted_metrics: dict, company_name: str) -> dict:
    """
    Compute basic financial ratios from previously extracted metrics.

    Ratios computed:
        - net_profit_margin  = PAT / Revenue
        - ebitda_margin      = EBITDA / Revenue
        - debt_to_equity     = Total Debt / Net Worth

    Args:
        extracted_metrics: dict containing at least revenue, pat, ebitda,
                           total_debt, net_worth keys.
        company_name: Name of the company (used for saved filenames).

    Returns:
        dict with keys:
            - ratios_saved_path: path where ratios JSON was saved
            - ratios: dict of computed ratio values (None when inputs missing)
    """
    revenue = extracted_metrics.get("revenue")
    pat = extracted_metrics.get("pat")
    ebitda = extracted_metrics.get("ebitda")
    total_debt = extracted_metrics.get("total_debt")
    net_worth = extracted_metrics.get("net_worth")

    def _safe_div(numerator, denominator):
        if numerator is not None and denominator:
            try:
                return round(numerator / denominator, 4)
            except (ZeroDivisionError, TypeError):
                return None
        return None

    ratios = {
        "net_profit_margin": _safe_div(pat, revenue),
        "ebitda_margin": _safe_div(ebitda, revenue),
        "debt_to_equity": _safe_div(total_debt, net_worth),
    }

    # Save to JSON
    safe_name = _safe_filename(company_name)
    out_path = os.path.join(FINANCIALS_DIR, f"{safe_name}_ratios.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ratios, f, indent=2, ensure_ascii=False)

    return {
        "ratios_saved_path": os.path.normpath(out_path),
        "ratios": ratios,
    }
