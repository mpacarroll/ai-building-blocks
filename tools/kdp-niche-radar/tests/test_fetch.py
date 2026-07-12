import pathlib

from kdp_niche_radar import fetch

FIXTURE = (pathlib.Path(__file__).parent / "fixtures" / "search_results.html").read_text()


def test_parse_extracts_result_count_and_top8():
    parsed = fetch.parse_search_results(FIXTURE)
    assert parsed["result_count"] == 3847
    assert len(parsed["top8"]) == 8
    first = parsed["top8"][0]
    assert first["title"] == "Sobriety Journal for Women"
    assert first["price"] == "$12.99"
    assert first["rating_count"] == 1204


def test_parse_caps_at_eight_even_with_more_results():
    extra = FIXTURE.replace("</div></body>", "")
    block = ('<div data-component-type="s-search-result"><h2><a><span>Extra</span></a></h2>'
             '<span class="a-price"><span class="a-offscreen">$1</span></span>'
             '<span class="a-size-base s-underline-text">3</span></div>')
    parsed = fetch.parse_search_results(extra + block * 5 + "</div></body></html>")
    assert len(parsed["top8"]) == 8


def test_fetch_keyword_fail_soft_on_network_error(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("network down")

    monkeypatch.setattr(fetch.requests, "get", boom)
    row = fetch.fetch_keyword("sobriety journal")
    assert row["ok"] is False
    assert row["result_count"] is None
    assert "network down" in row["error"]
    assert row["keyword"] == "sobriety journal"


def test_fetch_keyword_ok_path(monkeypatch):
    class Resp:
        status_code = 200
        text = FIXTURE
        def raise_for_status(self): pass

    monkeypatch.setattr(fetch.requests, "get", lambda url, **kw: Resp())
    monkeypatch.setattr(fetch.time, "sleep", lambda *a: None)
    row = fetch.fetch_keyword("sobriety journal")
    assert row["ok"] is True
    assert row["result_count"] == 3847
    assert len(row["top8"]) == 8
