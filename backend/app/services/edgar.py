"""SEC EDGAR access: ticker→CIK resolution, company facts, submissions metadata.

Uses the documented JSON endpoints on data.sec.gov directly. All responses are
cached on disk; the SEC asks for a descriptive User-Agent with contact info.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

USER_AGENT = "Personal DCF dashboard omkar.nandode1@gmail.com"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

DAY = 86400
TICKER_MAP_TTL = 7 * DAY
FACTS_TTL = DAY


class EdgarError(Exception):
    """Raised when EDGAR data cannot be fetched or the ticker is unknown."""


def _cached_get(url: str, cache_name: str, ttl: float, force_refresh: bool = False) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / cache_name
    if not force_refresh and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    try:
        response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # Serve stale cache if the network is down but we have something
        if cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))
        raise EdgarError(f"EDGAR request failed for {url}: {exc}") from exc
    data = response.json()
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return data


def resolve_cik(ticker: str, force_refresh: bool = False) -> str:
    """Return the zero-padded 10-digit CIK for a ticker."""
    ticker = ticker.upper().strip()
    mapping = _cached_get(TICKER_MAP_URL, "company_tickers.json", TICKER_MAP_TTL, force_refresh)
    for entry in mapping.values():
        if entry["ticker"].upper() == ticker:
            return f"{entry['cik_str']:010d}"
    raise EdgarError(f"Ticker '{ticker}' not found in SEC company list")


def get_company_facts(cik: str, force_refresh: bool = False) -> dict:
    return _cached_get(
        COMPANY_FACTS_URL.format(cik=cik), f"facts_{cik}.json", FACTS_TTL, force_refresh
    )


def get_submissions(cik: str, force_refresh: bool = False) -> dict:
    return _cached_get(
        SUBMISSIONS_URL.format(cik=cik), f"submissions_{cik}.json", FACTS_TTL, force_refresh
    )
