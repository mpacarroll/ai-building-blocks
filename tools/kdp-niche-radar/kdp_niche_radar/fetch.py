"""Fetch and parse Amazon books search-results pages (spec req 2).

Public pages, polite scraping (>=1s throttle, honest UA, one retry, 15s timeout).
Every keyword is fail-soft: a fetch/parse error degrades to an ok=False row with
a warning, never an exception that aborts the run.

NOTE: Amazon's markup changes over time. The selectors below match the current
public search page; if result parsing starts returning zeros, update the regexes
here — that fragility is inherent to every tool in this category.
"""
import re
import time

import requests

from .suggest import UA, DELAY_SECONDS

SEARCH_URL = "https://www.amazon.com/s"
_COUNT = re.compile(r"of\s+([\d,]+)\s+results", re.I)
_BLOCK = re.compile(r'data-component-type="s-search-result".*?(?=data-component-type="s-search-result"|</body>)',
                    re.S)
_TITLE = re.compile(r"<h2[^>]*>.*?<span[^>]*>([^<]+)</span>", re.S)
_PRICE = re.compile(r'a-offscreen">([^<]+)</span>')
_RATINGS = re.compile(r's-underline-text">\s*([\d,]+)\s*</span>')


def parse_search_results(html: str) -> dict:
    m = _COUNT.search(html)
    result_count = int(m.group(1).replace(",", "")) if m else None
    top8 = []
    for block in _BLOCK.findall(html):
        if len(top8) == 8:
            break
        title = _TITLE.search(block)
        price = _PRICE.search(block)
        ratings = _RATINGS.search(block)
        top8.append({
            "title": title.group(1).strip() if title else None,
            "price": price.group(1).strip() if price else None,
            "rating_count": int(ratings.group(1).replace(",", "")) if ratings else 0,
        })
    return {"result_count": result_count, "top8": top8}


def fetch_keyword(keyword: str, session=None) -> dict:
    """Fetch one keyword's search page, fail-soft. Returns a row dict."""
    get = (session.get if session else requests.get)
    last_err = None
    for attempt in range(2):  # one retry
        try:
            r = get(SEARCH_URL, params={"k": keyword, "i": "stripbooks"},
                    headers=UA, timeout=15)
            r.raise_for_status()
            parsed = parse_search_results(r.text)
            return {"keyword": keyword, "ok": True, "error": None, **parsed}
        except Exception as e:  # noqa: BLE001 — fail-soft is the contract
            last_err = str(e)
            if attempt == 0:
                time.sleep(DELAY_SECONDS)
    return {"keyword": keyword, "ok": False, "error": last_err,
            "result_count": None, "top8": []}
