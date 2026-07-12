"""Gumroad license verification, offline-tolerant (spec acceptance-test 3).

Verify once online, then run for up to 30 days offline against a local cache.
Keeps the tool usable on a plane while still gating on a real purchase.
No telemetry: the only network call is the license check itself.
"""
import json
import pathlib

import requests

CACHE_TTL_SECONDS = 30 * 86400
PURCHASE_URL = "https://gumroad.com/l/kdp-niche-radar"
_API = "https://api.gumroad.com/v2/licenses/verify"


def _online_verify(key: str, product_id: str) -> bool:
    r = requests.post(_API, data={"product_permalink": product_id, "license_key": key}, timeout=15)
    r.raise_for_status()
    return bool(r.json().get("success"))


def verify(key: str, product_id: str, cache_path, now: float, verifier=_online_verify) -> bool:
    """Return True if the license is valid, tolerating offline use within the
    cache TTL. `now` and `verifier` are injectable for testing.
    """
    cache_path = pathlib.Path(cache_path)
    try:
        valid = verifier(key, product_id)
        if valid:
            cache_path.write_text(json.dumps({"key": key, "verified_at": now}))
        return bool(valid)
    except Exception:
        # network (or API) failure — fall back to a fresh cached verification
        if not cache_path.exists():
            return False
        try:
            cached = json.loads(cache_path.read_text())
        except Exception:
            return False
        if cached.get("key") != key:
            return False
        return (now - cached.get("verified_at", 0)) <= CACHE_TTL_SECONDS
