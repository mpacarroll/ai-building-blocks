# KDP Niche Radar

Find low-competition book niches in under a minute. Type a phrase, get a scored keyword report — demand versus competition, with the beatable "golden" niches flagged.

**Runs entirely on your machine. No account, no cloud, no tracking. Nothing you research leaves your computer** — which is exactly what the $20-a-month subscription tools can't say.

## Install
```
pipx install kdp-niche-radar      # recommended (isolated)
# or: pip install kdp-niche-radar
```

## Use
```
radar "sobriety journal"          # writes report.html + run.json in the current folder
radar "chess journal" --out ~/research --limit 40
radar --compare last-week.json this-week.json   # track a niche over time
```
Open `report.html` in any browser — it is self-contained and works offline. Golden rows are niches with real demand and soft competition (median competitor ratings under 150).

Licensed via Gumroad. Verify once online; it then runs offline for 30 days. Set your key with `--key` or the `RADAR_LICENSE` environment variable.

## How the score works
- **demand** = autocomplete breadth × rank weight (how widely Amazon suggests the phrase)
- **competition** = median number of ratings across the top 8 results (how entrenched the incumbents are)
- **score** = demand ÷ competition; higher is a better opening
- **golden** = meaningful demand and median competitor ratings under 150

It is a compass, not gospel — the metrics are proxies. Use judgment.

## Honesty notes
- Amazon's page markup changes; if results come back empty, the selectors in `fetch.py` need updating. Every tool in this category has this fragility.
- Be polite: the tool throttles to about one request per second and identifies itself honestly. Do not hammer it.

## Built in the open
This tool was built spec-first: see [`../../specs/kdp-niche-radar.md`](../../specs/kdp-niche-radar.md) for the spec it was implemented from, and the plan that turned that spec into test-driven tasks. Every function had a failing test before it had code.

Made by Mick. [Who's Mick? →](../../README.md)  ·  MIT licensed.
