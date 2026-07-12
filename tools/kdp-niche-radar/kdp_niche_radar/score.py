"""Score keywords by demand vs competition (spec req 3).

demand      = breadth * (1 / position)         # autocomplete breadth, rank-weighted
competition = median(rating_count of top 8)    # how entrenched the incumbents are
score       = demand / competition             # higher is a better opportunity
golden      = meaningful demand AND median rating_count < 150 (a beatable niche)

Failed rows (ok=False) carry score=None and sort last. Deterministic.
"""
from statistics import median

GOLDEN_MAX_COMPETITION = 150
GOLDEN_MIN_DEMAND = 1.0


def _median_ratings(top8: list) -> float:
    counts = [r.get("rating_count", 0) or 0 for r in (top8 or [])]
    return median(counts) if counts else 0


def score_keywords(rows: list) -> list:
    scored = []
    for row in rows:
        if not row.get("ok"):
            scored.append({**row, "demand": None, "competition": None,
                           "score": None, "golden": False, "_sort": -1})
            continue
        demand = row["breadth"] * (1.0 / row["position"])
        competition = _median_ratings(row.get("top8"))
        if competition and competition > 0:
            s = demand / competition
            golden = competition < GOLDEN_MAX_COMPETITION and demand >= GOLDEN_MIN_DEMAND
        else:
            s, golden = None, False   # competition undefined -> no score
        scored.append({**row, "demand": demand, "competition": competition,
                       "score": s, "golden": golden,
                       "_sort": s if s is not None else -1})
    scored.sort(key=lambda r: r["_sort"], reverse=True)
    return [{k: v for k, v in r.items() if k != "_sort"} for r in scored]
