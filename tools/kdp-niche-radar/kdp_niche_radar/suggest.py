"""Amazon books autocomplete expansion. Vendored and adapted from the private
research stack's suggestlib so this tool ships standalone (spec req 1).

Public completion endpoint, no key. Polite: >=1s between calls, honest UA.
"""
import time

import requests

UA = {"User-Agent": "kdp-niche-radar/1.0 (keyword research; runs locally)"}
DELAY_SECONDS = 1.0
MODIFIERS = ["how", "for", "best", "with", "without", "guide", "workbook", "journal"]


def amazon_suggest(query: str) -> list:
    """Amazon completion API, books department."""
    r = requests.get(
        "https://completion.amazon.com/api/2017/suggestions",
        params={"mid": "ATVPDKIKX0DER", "alias": "stripbooks", "prefix": query},
        headers=UA, timeout=15,
    )
    r.raise_for_status()
    return [s["value"] for s in r.json().get("suggestions", [])]


def expand_seeds(seed: str, suggest_fn=amazon_suggest, limit: int = 30) -> list:
    """Expand one seed via base + modifier queries. Score each keyword by the
    number of distinct queries it appeared in (breadth = a demand proxy).

    Returns [(keyword, breadth)] sorted by breadth desc, seed itself excluded,
    capped at `limit`.
    """
    queries = [seed] + [f"{seed} {m}" for m in MODIFIERS] + [f"{m} {seed}" for m in ("best", "how")]
    scores = {}
    live = suggest_fn is amazon_suggest
    for q in queries:
        try:
            results = suggest_fn(q)
        except Exception:
            continue
        for kw in results:
            kw = kw.strip().lower()
            if kw and kw != seed.strip().lower():
                scores[kw] = scores.get(kw, 0) + 1
        if live:
            time.sleep(DELAY_SECONDS)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:limit]
