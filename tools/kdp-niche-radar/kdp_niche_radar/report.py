"""Render a self-contained, offline HTML report + CSV export (spec req 4).

No external resources (inline CSS only, CSV embedded as a data: URI), so the
report opens and works with the network off. compare() diffs two saved runs.
"""
import csv
import io
import urllib.parse

CSV_FIELDS = ["keyword", "breadth", "position", "demand", "competition", "score", "golden"]


def to_csv(scored: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
    w.writeheader()
    for row in scored:
        w.writerow({k: row.get(k) for k in CSV_FIELDS})
    return buf.getvalue()


def _fmt(x, nd=4):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def render(scored: list, seed: str) -> str:
    ok_rows = [r for r in scored if r.get("ok")]
    bad_rows = [r for r in scored if not r.get("ok")]

    body = []
    for r in ok_rows:
        cls = "golden" if r.get("golden") else ""
        tag = " <b>GOLDEN</b>" if r.get("golden") else ""
        body.append(
            f"<tr class='{cls}'><td>{r['keyword']}{tag}</td>"
            f"<td>{_fmt(r.get('demand'), 2)}</td><td>{_fmt(r.get('competition'), 0)}</td>"
            f"<td>{_fmt(r.get('score'))}</td></tr>"
        )
    warn = ""
    if bad_rows:
        items = "".join(f"<li>{r['keyword']} — {r.get('error', 'failed')}</li>" for r in bad_rows)
        warn = f"<h2>Skipped (fetch failed)</h2><ul class='warn'>{items}</ul>"

    csv_uri = "data:text/csv;charset=utf-8," + urllib.parse.quote(to_csv(scored))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KDP Niche Radar — {seed}</title>
<style>
 body{{font:16px/1.5 system-ui,sans-serif;max-width:820px;margin:0 auto;padding:24px}}
 table{{border-collapse:collapse;width:100%}} th,td{{text-align:left;padding:8px;border-bottom:1px solid #ccc}}
 tr.golden{{background:rgba(255,196,0,0.18)}} .warn{{opacity:.75}}
 caption{{text-align:left;opacity:.7;padding-bottom:8px}}
</style></head><body>
<h1>KDP Niche Radar</h1>
<p>Seed: <b>{seed}</b>. Golden = beatable demand (median competitor ratings under {150}).
Everything ran on your machine; nothing was sent anywhere.</p>
<table><caption>Ranked by opportunity score (demand ÷ competition)</caption>
<tr><th>Keyword</th><th>Demand</th><th>Median ratings</th><th>Score</th></tr>
{''.join(body)}
</table>
{warn}
<p><a download="kdp-niche-radar.csv" href="{csv_uri}">Download CSV</a></p>
</body></html>"""


def compare(run_a: dict, run_b: dict) -> dict:
    a = {r["keyword"]: r.get("score") for r in run_a.get("results", [])}
    b = {r["keyword"]: r.get("score") for r in run_b.get("results", [])}
    changed = {}
    for kw in a.keys() & b.keys():
        if a[kw] is not None and b[kw] is not None:
            changed[kw] = round(b[kw] - a[kw], 6)
    return {
        "changed": changed,
        "new": sorted(b.keys() - a.keys()),
        "dropped": sorted(a.keys() - b.keys()),
    }
