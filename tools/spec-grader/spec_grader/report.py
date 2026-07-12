"""Render a grade result as markdown (for the terminal) or a self-contained,
offline HTML file. No external resources."""
import html as _html


def to_markdown(result: dict, name: str = "") -> str:
    lines = [f"# Spec grade{': ' + name if name else ''}",
             f"**Grade: {result['grade']}**  ({result['score']}/100)",
             "", result["summary"], ""]
    if result["ambiguities"]:
        lines.append("## Ambiguous phrases")
        for a in result["ambiguities"]:
            lines.append(f"- line {a['line']}: \"{a['term']}\" — {a['why']}")
        lines.append("")
    if result["requirements"]:
        lines.append("## Testable requirements")
        for r in result["requirements"]:
            mark = "  ⚠ ambiguous" if r["ambiguous"] else ""
            lines.append(f"- line {r['line']}: {r['keyword']}{mark}")
    return "\n".join(lines)


def to_html(result: dict, name: str = "") -> str:
    rows = "".join(
        f"<tr><td>{a['line']}</td><td><code>{_html.escape(a['term'])}</code></td>"
        f"<td>{_html.escape(a['why'])}</td></tr>"
        for a in result["ambiguities"]
    ) or "<tr><td colspan='3'>None — nice and precise.</td></tr>"
    reqs = "".join(
        f"<li>line {r['line']}: <b>{r['keyword']}</b>"
        + (" <span class='warn'>ambiguous</span>" if r["ambiguous"] else "") + "</li>"
        for r in result["requirements"]
    ) or "<li>No testable requirements found.</li>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spec grade{': ' + _html.escape(name) if name else ''}</title>
<style>
 body{{font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:24px}}
 .grade{{font-size:2.4rem;font-weight:800}} table{{border-collapse:collapse;width:100%}}
 th,td{{text-align:left;padding:8px;border-bottom:1px solid #ccc;vertical-align:top}}
 .warn{{color:#b40;font-weight:700}} code{{background:rgba(128,128,128,.15);padding:1px 5px;border-radius:4px}}
</style></head><body>
<h1>Spec grade{': ' + _html.escape(name) if name else ''}</h1>
<p class="grade">{result['grade']} <small>({result['score']}/100)</small></p>
<p>{_html.escape(result['summary'])}</p>
<h2>Ambiguous phrases</h2>
<table><tr><th>Line</th><th>Phrase</th><th>Why it hurts the spec</th></tr>{rows}</table>
<h2>Testable requirements</h2><ul>{reqs}</ul>
</body></html>"""
