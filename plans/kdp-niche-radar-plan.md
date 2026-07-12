# KDP Niche Radar Implementation Plan

> **For agentic workers:** implement task-by-task, test-first. Steps use checkbox syntax. Built with the superpowers `writing-plans` + `test-driven-development` skills.

**Goal:** a local CLI that turns a niche phrase into a scored keyword/competition report.

**Architecture:** pure, testable modules (suggest → fetch → score → report), a license gate, and a thin CLI that wires them. Zero data leaves the machine.

**Tech stack:** Python 3.10+, stdlib + `requests`, `pytest`.

## Global constraints
- stdlib + `requests` only; no accounts, no telemetry.
- Every network call: 15s timeout, one retry, fail-soft per keyword.
- Test-first: no production code without a failing test observed first.

---

This plan was executed to completion. Each task below shipped with its tests green and the RED observed before GREEN. The tasks, in order:

### Task 1 — Package scaffold
`pyproject.toml` + `kdp_niche_radar/__init__.py` + `radar` entry point. ✅

### Task 2 — Suggest (spec req 1)
`suggest.expand_seeds(seed, suggest_fn, limit) -> [(keyword, breadth)]`, seed excluded, ranked by breadth, capped at limit. Vendored from the research stack so the tool ships standalone. ✅ `tests/test_suggest.py`

### Task 3 — Fetch, fail-soft (spec req 2)
`fetch.fetch_keyword(kw) -> {keyword, result_count, top8[], ok, error}`; parses the search page for result count + top-8 title/price/rating_count; timeout + one retry; any failure degrades to `ok=False`, never raises. ✅ `tests/test_fetch.py` (+ fixture)

### Task 4 — Score + golden (spec req 3)
`score.score_keywords(rows)`: demand = breadth × 1/position; competition = median top-8 ratings; score = demand/competition; golden = demand ≥ 1 and median < 150. Failed rows sort last with `score=None`. Deterministic. ✅ `tests/test_score.py`

### Task 5 — Report + CSV + compare (spec req 4)
`report.render(scored, seed)` → self-contained offline HTML (no external refs; CSV as a `data:` URI); `report.compare(a, b)` diffs two runs. ✅ `tests/test_report.py`

### Task 6 — License, offline-tolerant (spec accept-test 3)
`license.verify(key, product, cache_path, now, verifier)`: verify once online, then run offline for 30 days against a local cache. ✅ `tests/test_license.py`

### Task 7 — CLI
`radar "<phrase>"` runs the pipeline behind the license gate and writes `report.html` + `run.json`; `--compare a.json b.json`. ✅ `tests/test_cli.py`

### Task 8 — End-to-end + packaging
Full pipeline from stubbed fixtures yields a deterministic report with a golden flag; `pipx`-installable; `radar --help` works. ✅ verified: 20 tests green, entry point live, report renders with **zero external requests** in a real browser.
