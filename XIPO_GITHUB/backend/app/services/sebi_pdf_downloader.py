import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from typing import Optional
from fastapi import HTTPException


DATA_PDF_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/pdfs")
)
os.makedirs(DATA_PDF_DIR, exist_ok=True)


def safe_filename(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _normalize_pdf_url(pdf_url: str) -> str:
    """
    SEBI often gives links like:
    https://www.sebi.gov.in/web/?file=https://www.sebi.gov.in/sebi_data/attachdocs/....pdf

    This function converts it to the real PDF:
    https://www.sebi.gov.in/sebi_data/attachdocs/....pdf
    """
    if "/web/?" in pdf_url and "file=" in pdf_url:
        parsed = urlparse(pdf_url)
        qs = parse_qs(parsed.query)
        if "file" in qs and len(qs["file"]) > 0:
            real = qs["file"][0]
            real = unquote(real)
            return real
    return pdf_url


def _extract_pdf_url(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")

    # 1) <a href="...">
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" in href.lower() or "web/?file=" in href.lower():
            return urljoin(base_url, href)

    # 2) <iframe src="...">
    for iframe in soup.find_all("iframe", src=True):
        src = iframe["src"].strip()
        if ".pdf" in src.lower() or "web/?file=" in src.lower():
            return urljoin(base_url, src)

    # 3) <embed src="...">
    for emb in soup.find_all("embed", src=True):
        src = emb["src"].strip()
        if ".pdf" in src.lower() or "web/?file=" in src.lower():
            return urljoin(base_url, src)

    # 4) Search scripts
    scripts = soup.find_all("script")
    for s in scripts:
        text = s.get_text(" ", strip=True)
        if not text:
            continue

        # Search for /web/?file=
        if "web/?file=" in text.lower():
            parts = re.split(r"[\s\"\'\(\)\[\]\{\}]+", text)
            for p in parts:
                if "web/?file=" in p.lower():
                    return urljoin(base_url, p)

        # Search for attachdocs pdf
        if ".pdf" in text.lower():
            parts = re.split(r"[\s\"\'\(\)\[\]\{\}]+", text)
            for p in parts:
                if ".pdf" in p.lower():
                    return urljoin(base_url, p)

    return None


def download_rhp_pdf(rhp_html_url: str, company_name: str) -> dict:
    """
    Downloads the real RHP PDF from a SEBI HTML page URL.
    Handles SEBI /web/?file= wrapper links properly.
    Retries download up to 3 times if file is corrupted.
    """
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1) Load HTML page
    try:
        r = session.get(rhp_html_url, headers=headers, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch SEBI page: {str(e)}"
        )

    extracted = _extract_pdf_url(r.text, rhp_html_url)
    if not extracted:
        raise HTTPException(
            status_code=404, 
            detail="Could not extract any PDF link from SEBI HTML page."
        )

    # 2) Normalize if SEBI web wrapper
    pdf_url = _normalize_pdf_url(extracted)

    # 3) Download real PDF with Referer and retry logic
    download_headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": rhp_html_url
    }
    
    max_retries = 3
    fname = safe_filename(company_name) + ".pdf"
    out_path = os.path.join(DATA_PDF_DIR, fname)
    
    for attempt in range(max_retries + 1):
        try:
            # Download stream to avoid loading large files instantly into memory
            r2 = session.get(pdf_url, headers=download_headers, timeout=120, stream=True)
            r2.raise_for_status()
            
            with open(out_path, "wb") as f:
                for chunk in r2.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 4) Validation
            is_valid = True
            
            # Check existence
            if not os.path.exists(out_path):
                is_valid = False
            else:
                # Check size > 50KB
                file_size = os.path.getsize(out_path)
                if file_size < 50 * 1024:
                    print(f"Validation failed: File size too small ({file_size} bytes)")
                    is_valid = False
                
                # Check PDF header
                if is_valid:
                    with open(out_path, "rb") as f:
                        header = f.read(4)
                        if header != b"%PDF":
                            print(f"Validation failed: Invalid header {header}")
                            is_valid = False
            
            if is_valid:
                # Success!
                return {
                    "pdf_url_extracted": extracted,
                    "pdf_url_used": pdf_url,
                    "pdf_saved_path": out_path
                }
            
            # If invalid, cleanup and retry
            if os.path.exists(out_path):
                os.remove(out_path)
                
            if attempt < max_retries:
                print(f"Download attempt {attempt+1} failed validation. Retrying in 2s...")
                time.sleep(2)
            
        except requests.RequestException as e:
            if os.path.exists(out_path):
                os.remove(out_path)
            
            if attempt < max_retries:
                print(f"Download attempt {attempt+1} failed with error: {e}. Retrying in 2s...")
                time.sleep(2)
            else:
                # Last attempt failed
                pass

    # If we get here, all retries failed
    raise HTTPException(
        status_code=400,
        detail="Downloaded file is not a valid PDF (SEBI returned incomplete/blocked response)"
    )
