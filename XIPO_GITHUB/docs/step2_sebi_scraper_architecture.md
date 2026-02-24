# Step 2 -- SEBI Scraper Architecture

## 1. Purpose

The SEBI scraper is responsible for locating the correct Red Herring Prospectus
(RHP) for a given company name on the SEBI (Securities and Exchange Board of
India) website. This is the first stage in the XIPO pipeline and its accuracy
determines whether the entire downstream analysis processes the correct document.

---

## 2. The SEBI Website Challenge

SEBI publishes public issue filings at:

```
https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=11
```

Key challenges:

1. **No search API.** SEBI provides no endpoint to search by company name.
   Documents are listed chronologically across paginated pages.
2. **AJAX pagination.** Page navigation is handled by an internal AJAX endpoint
   (`getnewslistinfo.jsp`), not by URL query parameters. Direct URL manipulation
   does not work.
3. **Session dependency.** The AJAX endpoint requires a `JSESSIONID` cookie
   obtained by visiting the listing page first.
4. **Inconsistent titles.** Filing titles follow no strict format. The same
   company may appear as "Zomato Limited - RHP", "RHP of Zomato Limited",
   or "Corrigendum to RHP - Zomato Limited".

---

## 3. Architecture

### 3.1 Session Establishment

```
Step 1: GET SEBI_LISTING_URL
        --> Server sets JSESSIONID cookie
        --> HTML response contains page 0 entries
        --> Parse entries from page 0
```

A `requests.Session` object is used to persist the cookie across subsequent
AJAX calls. This mirrors how a browser would naturally navigate the site.

### 3.2 Pagination via AJAX

```
Step 2: For page_index in 1..MAX_PAGES:
        POST SEBI_AJAX_URL with payload {doDirect: page_index, sid:3, ...}
        --> Returns HTML fragment with 25 entries
        --> Parse entries
        --> Stop early if a strong match is already found
```

The `doDirect` parameter controls which page is returned. Each page contains
up to 25 entries (`PAGE_SIZE = 25`). A maximum of 10 pages are scanned
(`MAX_PAGES = 10`), yielding up to 250 candidate filings.

### 3.3 Text Normalisation

Both the user query and each candidate title undergo the same normalisation
before comparison:

```python
def normalize_company_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)    # remove punctuation
    tokens = text.split()
    tokens = [t for t in tokens if t not in _STOPWORDS]
    return " ".join(tokens).strip()
```

Stopwords removed: `rhp`, `drhp`, `limited`, `ltd`, `india`, `indian`,
`private`, `pvt`, `company`, `co`, `industries`, `industry`.

**Why this matters:** Without normalisation, searching for "Zomato" would yield
a low match score against "Zomato Limited - RHP" because the extra words dilute
the similarity ratio. After normalisation, the comparison becomes "zomato" vs
"zomato", which is a perfect match.

### 3.4 Fuzzy Matching with Boosts

The base similarity is computed using `difflib.SequenceMatcher`. Two boosts
are applied on top:

| Boost        | Condition                              | Effect                          |
|--------------|----------------------------------------|---------------------------------|
| Substring    | Query (>= 4 chars) is a substring of title | Score raised to at least 0.90 |
| Token overlap| All query tokens are present in title  | Score raised to at least 0.85   |

These boosts handle partial queries ("Zomato" matching a long normalised title)
and multi-word queries ("Tata Technologies" matching "tata technologies").

### 3.5 Document Type Detection

Every candidate is classified into one of five types:

| Type         | Detection rule                    | Priority |
|--------------|-----------------------------------|----------|
| CORRIGENDUM  | "corrigendum" in title (lowercase)| 1 (low)  |
| ADDENDUM     | "addendum" in title (lowercase)   | 1 (low)  |
| DRHP         | "drhp" in title (lowercase)       | 2        |
| RHP          | "rhp" in title (lowercase)        | 3 (high) |
| OTHER        | None of the above                 | 0        |

Order matters: "corrigendum" is checked first because a title like
"Corrigendum to RHP" contains both "corrigendum" and "rhp". Without this
ordering, it would be misclassified as RHP.

### 3.6 Candidate Selection

Only `RHP` and `DRHP` candidates above the minimum match score (0.65) are
eligible for selection. Candidates are sorted by:

1. Document priority (descending): RHP > DRHP
2. Match score (descending)

Corrigendum and Addendum documents are never selected, regardless of their
match score. This prevents the system from returning a one-page errata sheet
instead of the full 400-page prospectus.

### 3.7 Early Termination

Pagination stops as soon as the best RHP/DRHP candidate reaches a score of
0.80 (`STRONG_MATCH_THRESHOLD`). This avoids unnecessary requests to SEBI
when a good match is found early.

---

## 4. PDF Download and Validation

Once the scraper identifies the RHP HTML URL, the `sebi_pdf_downloader`
service takes over:

1. **Fetch the HTML page.** The RHP URL on SEBI points to an HTML wrapper page,
   not directly to a PDF.

2. **Extract the real PDF link.** The downloader searches through `<a>`,
   `<iframe>`, `<embed>` tags, and inline JavaScript for a URL ending in `.pdf`
   or containing the `web/?file=` SEBI wrapper pattern.

3. **Normalise the URL.** SEBI often wraps PDF links as:
   ```
   https://www.sebi.gov.in/web/?file=https://www.sebi.gov.in/sebi_data/attachdocs/...pdf
   ```
   The normaliser extracts the real PDF URL from the `file` query parameter.

4. **Download with validation.** The PDF is downloaded with streaming
   (`iter_content`), then validated:
   - File must exist.
   - File size must exceed 50 KB (rejects blocked/empty responses).
   - First 4 bytes must be `%PDF` (rejects HTML error pages saved as .pdf).

5. **Retry logic.** If validation fails, the download is retried up to 3 times
   with a 2-second delay between attempts.

---

## 5. Error Handling and Fallback

When no suitable match is found, the scraper returns:

```json
{
  "status": "not_found",
  "input_company": "XYZ Nonexistent",
  "top_matches": [
    {"title": "...", "score": 0.45, "doc_type": "RHP", "url": "..."},
    ...
  ],
  "pages_scanned": 10
}
```

The top 5 candidates (across all document types) are always included for
transparency and debugging. The frontend uses this to show "Did you mean?"
suggestions to the user.

---

## 6. Configuration Constants

| Constant               | Value | Purpose                                    |
|------------------------|-------|--------------------------------------------|
| `PAGE_SIZE`            | 25    | Entries per SEBI page                      |
| `MAX_PAGES`            | 10    | Maximum pages to scrape                    |
| `MIN_MATCH_SCORE`      | 0.65  | Minimum similarity to accept a candidate   |
| `STRONG_MATCH_THRESHOLD`| 0.80 | Score above which pagination stops early   |
| `PAGE_DELAY`           | 0.2s  | Delay between AJAX requests (rate limiting)|

---

## 7. Limitations

1. **SEBI website changes.** The scraper depends on SEBI's current HTML
   structure and AJAX endpoint. If SEBI redesigns their website, the scraper
   will need to be updated.

2. **No historical depth.** With `MAX_PAGES = 10` (250 entries), the scraper
   can only locate IPOs filed within the most recent ~250 filings. Older IPOs
   may not be found.

3. **Fuzzy matching accuracy.** Very common company names (e.g., "India")
   or very short names (e.g., "Ola") may match multiple candidates. The
   stopword removal and document type priority mitigate this but do not
   eliminate it entirely.

4. **Rate limiting.** While a 0.2-second delay is currently sufficient, SEBI
   could introduce stricter rate limiting or CAPTCHA challenges. The scraper
   does not handle CAPTCHAs.

---

## 8. Viva Preparation: Key Questions

**Q: Why not use SEBI's search functionality directly?**
A: SEBI does not provide a public search API for filings. The listing page uses
AJAX pagination with session cookies, which the scraper replicates.

**Q: How do you handle companies that appear on page 5 of SEBI listings?**
A: The scraper paginates through up to 10 pages using the AJAX `doDirect`
parameter. Each page returns 25 entries, allowing coverage of up to 250
filings.

**Q: What prevents the scraper from returning a Corrigendum instead of an RHP?**
A: Document type detection classifies each title, and the selection logic only
considers RHP and DRHP types. Corrigendum and Addendum are explicitly excluded
regardless of their fuzzy match score.

**Q: What happens if two companies have very similar names?**
A: The candidate with the highest combined score (document priority + match
score) is selected. The top 5 alternatives are always returned so the user can
manually verify the match.
