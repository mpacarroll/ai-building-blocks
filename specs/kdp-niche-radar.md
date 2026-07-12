# Spec: KDP Niche Radar (Micro-SaaS candidate #1)

**Status:** spec complete, build deferred to first free weekend post-launch. This spec is written to zero-edit standard: an agent should implement v1 from it without clarifying questions.

## Intent
Self-serve tool for KDP self-publishers: enter a niche phrase, get a scored keyword and competition report in under a minute. Replaces the manual `stack/research/kdp_keywords.py` workflow with a product. Comps (Publisher Rocket, $97 one-time; Book Bolt, $10–20/mo) validate willingness to pay.

## v1 shape (pick the cheapest distribution that ships)
**Gumroad-licensed desktop CLI + local HTML report.** No hosting, no accounts, no uptime obligation — pure passivity. A hosted web version is v2, only if v1 sells.
- Deliverable: a single Python package (pip-installable wheel + one-command runner) licensed per-buyer via Gumroad license key check (offline-tolerant: verify once, cache 30 days).
- Price: $29 one-time launch, $49 later. Free update stream via Gumroad.

## Functional requirements
1. `radar "<niche phrase>"` expands the seed through Amazon books autocomplete (reuse `suggestlib.expand_seeds` logic, vendored) with polite rate limiting (≥1s, honest UA).
2. For each of the top 30 keywords, fetch the Amazon search results page count and top-8 organic results' metadata (title, price, rating count) — public pages, polite scraping, hard fail-soft per keyword.
3. Score each keyword: demand proxy (suggest breadth × position) ÷ competition proxy (median rating count of top 8). Flag "golden" keywords (high demand, median rating count < 150).
4. Emit `report.html` (self-contained, no CDN): ranked table, golden flags, per-keyword top-8 snapshot, CSV export link (data URI).
5. `--compare a.json b.json` diffs two runs (niche tracking over time).

## Non-functional
- Python 3.10+, stdlib + requests + the vendored suggest module only. No accounts, no telemetry, no data leaves the machine (this is a selling point — say it in the listing).
- Every network call: 15s timeout, one retry, per-keyword failure degrades to partial report with a warnings section.
- Respect robots/ToS posture: throttle ≤1 req/s, identify honestly, document that heavy use may require the buyer's own judgment; no login-walled data ever.

## Acceptance tests (write first, per M4)
- Given a fixture of autocomplete + search-page HTML, the scorer produces the documented ranking deterministically.
- A keyword whose fetches all fail appears in the warnings section, not the table.
- License check: valid key cached; invalid key exits with the purchase URL; network-down + valid cache runs normally.
- Report renders offline (no external requests when opened).

## Out of scope v1
Hosted version, KDP category/BSR estimation, non-book marketplaces, Windows installer (document `pipx install`).

## Launch
List on Gumroad with a demo report as the preview; announce via newsletter + a flagship video ("I built the tool the KDP gurus sell courses about, in a weekend, from one spec" — the video is also bootcamp marketing).
