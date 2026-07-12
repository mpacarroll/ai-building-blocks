from kdp_niche_radar import report

SCORED = [
    {"keyword": "sober journal", "breadth": 6, "position": 1, "ok": True,
     "demand": 6.0, "competition": 50, "score": 0.12, "golden": True,
     "top8": [{"title": "A Sober Journal", "price": "$12.99", "rating_count": 50}]},
    {"keyword": "recovery diary", "breadth": 2, "position": 4, "ok": True,
     "demand": 0.5, "competition": 4000, "score": 0.000125, "golden": False, "top8": []},
    {"keyword": "broken kw", "ok": False, "error": "timeout",
     "demand": None, "competition": None, "score": None, "golden": False, "top8": []},
]


def test_report_is_offline_and_self_contained():
    html = report.render(SCORED, seed="sobriety journal")
    assert "sober journal" in html and "GOLDEN" in html.upper()
    # a broken keyword lands in a warnings area, not the main table silently dropped
    assert "broken kw" in html
    # no external resources of any kind
    for banned in ("http://", "https://", "src=", "cdn", "<link", "@import"):
        assert banned not in html.lower(), f"found external ref: {banned}"
    # CSV embedded as a data: URI download
    assert "data:text/csv" in html


def test_to_csv_has_header_and_rows():
    csv = report.to_csv(SCORED)
    assert csv.splitlines()[0].startswith("keyword,")
    assert "sober journal" in csv and "broken kw" in csv


def test_compare_reports_deltas_new_and_dropped():
    run_a = {"seed": "s", "results": [
        {"keyword": "sober journal", "score": 0.10},
        {"keyword": "gone kw", "score": 0.05}]}
    run_b = {"seed": "s", "results": [
        {"keyword": "sober journal", "score": 0.20},
        {"keyword": "new kw", "score": 0.30}]}
    diff = report.compare(run_a, run_b)
    assert diff["changed"]["sober journal"] == 0.10   # 0.20 - 0.10
    assert "new kw" in diff["new"]
    assert "gone kw" in diff["dropped"]
