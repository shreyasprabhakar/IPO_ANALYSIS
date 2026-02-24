"""
SEBI RHP Scraper Service
Scrapes SEBI public issues filings pages and returns the best RHP match
for a given company name using fuzzy matching (difflib).

Features:
  - Uses SEBI's internal AJAX endpoint for reliable pagination
  - Document-type detection (RHP > DRHP > skip corrigendum/addendum)
  - Aggressive text normalization for partial-query resilience
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEBI_BASE_URL = "https://www.sebi.gov.in"

# The main listing page (visited once to establish session cookies)
SEBI_LISTING_URL = (
    f"{SEBI_BASE_URL}/sebiweb/home/HomeAction.do"
    "?doListing=yes&sid=3&ssid=15&smid=11"
)

# AJAX endpoint that actually supports page navigation via POST
SEBI_AJAX_URL = f"{SEBI_BASE_URL}/sebiweb/ajax/home/getnewslistinfo.jsp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Extra headers required by the AJAX endpoint
AJAX_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": SEBI_LISTING_URL,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# Number of entries per SEBI listing page
PAGE_SIZE = 25

# Maximum listing pages to scrape
MAX_PAGES = 10

# Minimum similarity before a candidate is considered a valid match
MIN_MATCH_SCORE = 0.65

# Stop scanning more pages once the best *RHP* score meets this threshold
STRONG_MATCH_THRESHOLD = 0.80

# Delay in seconds between consecutive page requests
PAGE_DELAY = 0.2

# Words removed from BOTH the user query and candidate titles before
# similarity comparison so that partial queries like "Zomato" match
# "Zomato Limited - RHP" cleanly.
_STOPWORDS = {
    "rhp", "drhp",
    "limited", "ltd",
    "india", "indian",
    "private", "pvt",
    "company", "co",
    "industries", "industry",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_company_text(text):
    """
    Lowercase, strip punctuation, remove noise stopwords, and collapse spaces.
    Used for BOTH user query and candidate title before similarity scoring.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)          # remove punctuation
    tokens = text.split()
    tokens = [t for t in tokens if t not in _STOPWORDS]
    return " ".join(tokens).strip()


def detect_doc_type(title_raw):
    """
    Classify a SEBI filing title into a document type.

    Returns one of: "CORRIGENDUM", "ADDENDUM", "RHP", "DRHP", "OTHER"
    """
    lower = title_raw.lower()
    if "corrigendum" in lower:
        return "CORRIGENDUM"
    if "addendum" in lower:
        return "ADDENDUM"
    if "drhp" in lower:
        return "DRHP"
    if "rhp" in lower:
        return "RHP"
    return "OTHER"


def _get_doc_priority(doc_type):
    """
    Return numeric priority for document type.
    Higher priority = more preferred.
    """
    priority_map = {
        "RHP": 3,
        "DRHP": 2,
        "ADDENDUM": 1,
        "CORRIGENDUM": 1,
        "OTHER": 0,
    }
    return priority_map.get(doc_type, 0)


def select_best_candidate(candidates, min_score=MIN_MATCH_SCORE):
    """
    Pick the best candidate using priority-based selection.
    
    Sorts by: (1) doc_priority (higher first), (2) match_score (higher first).
    Only RHP and DRHP are eligible for selection.
    Addendum / Corrigendum / Other are never selected.

    Args:
        candidates: list of candidate dicts (must have match_score, doc_type).
        min_score:  minimum similarity to accept.

    Returns:
        The chosen candidate dict, or None if nothing qualifies.
    """
    # Filter to only RHP and DRHP types above threshold
    eligible = [
        c for c in candidates
        if c["doc_type"] in ("RHP", "DRHP") and c["match_score"] >= min_score
    ]
    
    if not eligible:
        return None
    
    # Sort by priority (descending), then by score (descending)
    eligible.sort(
        key=lambda c: (_get_doc_priority(c["doc_type"]), c["match_score"]),
        reverse=True
    )
    
    return eligible[0]



def _compute_boosted_score(query_norm, title_norm):
    """
    Compute fuzzy match score with boosts for short queries.

    Args:
        query_norm: normalized query string
        title_norm: normalized title string

    Returns:
        float score between 0 and 1
    """
    # Base difflib score
    score = SequenceMatcher(None, query_norm, title_norm).ratio()

    # Boost A: Substring boost
    if len(query_norm) >= 4 and query_norm in title_norm:
        score = max(score, 0.90)

    # Boost B: Token overlap boost
    query_tokens = set(query_norm.split())
    title_tokens = set(title_norm.split())
    if query_tokens and query_tokens.issubset(title_tokens):
        score = max(score, 0.85)

    return score


def _parse_entries(html):
    """
    Parse listing HTML (full page or AJAX fragment) and return entries.
    Each entry is {"title": str, "url": str}.
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/filings/public-issues/" in href and href.endswith(".html"):
            title = link.get_text(strip=True)
            if not title:
                continue
            full_url = href if href.startswith("http") else f"{SEBI_BASE_URL}{href}"
            entries.append({"title": title, "url": full_url})

    return entries


def _create_session():
    """
    Create a requests.Session and visit the main listing page once so that
    the session acquires the JSESSIONID cookie needed by the AJAX endpoint.

    Returns (session, page0_entries).
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        r = session.get(SEBI_LISTING_URL, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return session, []

    entries = _parse_entries(r.text)
    return session, entries


def _scrape_page_ajax(session, page_index):
    """
    Fetch a single listing page via the SEBI AJAX endpoint.
    page_index is 0-based (page 0 = first page).
    """
    payload = {
        "sid": "3",
        "ssid": "15",
        "smid": "11",
        "doDirect": str(page_index),
        "next": "n",
        "search": "",
        "fromDate": "",
        "toDate": "",
        "deptId": "-1",
    }
    try:
        r = session.post(
            SEBI_AJAX_URL,
            data=payload,
            headers=AJAX_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
    except requests.RequestException:
        return []

    return _parse_entries(r.text)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def search_sebi_rhp(company_name):
    """
    Search SEBI public issues filings for a company's main RHP page.

    Scrapes pages incrementally via the SEBI AJAX endpoint, scores each
    candidate after stopword normalisation, and picks the best RHP
    (never corrigendum / addendum).

    Args:
        company_name: Name (or partial name) of the company to search for.

    Returns:
        dict with keys:
            status          – "ok" | "not_found"
            input_company   – original query
            (if ok)
              matched_company_title – raw SEBI title of the chosen filing
              match_score           – similarity (0-1)
              doc_type              – "RHP" or "DRHP"
              rhp_html_url          – URL
            pages_scanned          – int
            pagination_mode_used   – str (always "ajax_doDirect")
            unique_titles_count    – int
            top_matches            – list of top 5 candidates
    """
    query_norm = normalize_company_text(company_name)
    all_candidates = []
    pages_scanned = 0
    best_rhp_score = 0.0
    seen_titles = set()
    pagination_mode = "ajax_doDirect"

    # Establish session (visits main page → gets JSESSIONID cookie + page 0)
    session, page0_entries = _create_session()
    pages_scanned += 1

    if not page0_entries:
        return {
            "status": "not_found",
            "input_company": company_name,
            "pages_scanned": pages_scanned,
            "pagination_mode_used": pagination_mode,
            "unique_titles_count": 0,
            "top_matches": [],
        }

    # Score page 0 entries
    for entry in page0_entries:
        doc_type = detect_doc_type(entry["title"])
        title_norm = normalize_company_text(entry["title"])
        score = _compute_boosted_score(query_norm, title_norm)
        candidate = {
            "title_raw": entry["title"],
            "title_normalized": title_norm,
            "url": entry["url"],
            "doc_type": doc_type,
            "match_score": round(score, 4),
        }
        all_candidates.append(candidate)
        seen_titles.add(entry["title"])
        if doc_type in ("RHP", "DRHP") and score > best_rhp_score:
            best_rhp_score = score

    # Remaining pages via AJAX (page 1 … MAX_PAGES-1)
    for page_index in range(1, MAX_PAGES):
        if best_rhp_score >= STRONG_MATCH_THRESHOLD:
            break

        time.sleep(PAGE_DELAY)
        entries = _scrape_page_ajax(session, page_index)
        pages_scanned += 1

        if not entries:
            break

        for entry in entries:
            if entry["title"] in seen_titles:
                continue
            doc_type = detect_doc_type(entry["title"])
            title_norm = normalize_company_text(entry["title"])
            score = _compute_boosted_score(query_norm, title_norm)
            candidate = {
                "title_raw": entry["title"],
                "title_normalized": title_norm,
                "url": entry["url"],
                "doc_type": doc_type,
                "match_score": round(score, 4),
            }
            all_candidates.append(candidate)
            seen_titles.add(entry["title"])
            if doc_type in ("RHP", "DRHP") and score > best_rhp_score:
                best_rhp_score = score

    # Build top-5 list (across ALL doc types, for transparency)
    top_matches = sorted(
        all_candidates, key=lambda c: c["match_score"], reverse=True
    )[:5]
    top_matches_clean = [
        {
            "title": c["title_raw"],
            "score": c["match_score"],
            "doc_type": c["doc_type"],
            "url": c["url"],
        }
        for c in top_matches
    ]

    # Selection: RHP first, then DRHP; never corrigendum/addendum
    chosen = select_best_candidate(all_candidates)

    base_response = {
        "input_company": company_name,
        "pages_scanned": pages_scanned,
        "pagination_mode_used": pagination_mode,
        "unique_titles_count": len(seen_titles),
        "top_matches": top_matches_clean,
    }

    if chosen is None:
        return {**base_response, "status": "not_found"}

    return {
        **base_response,
        "status": "ok",
        "matched_company_title": chosen["title_raw"],
        "match_score": chosen["match_score"],
        "doc_type": chosen["doc_type"],
        "rhp_html_url": chosen["url"],
    }
