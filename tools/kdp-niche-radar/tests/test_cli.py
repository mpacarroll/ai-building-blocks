import json
import pathlib

from kdp_niche_radar import cli, suggest, fetch, license as lic


def _stub_pipeline(monkeypatch, valid_license=True):
    monkeypatch.setattr(lic, "verify", lambda *a, **k: valid_license)
    monkeypatch.setattr(suggest, "expand_seeds",
                        lambda seed, **k: [("sober journal", 6), ("recovery diary", 2)])

    def fake_fetch(kw, session=None):
        if kw == "sober journal":
            return {"keyword": kw, "ok": True, "error": None, "result_count": 3000,
                    "top8": [{"title": "A", "price": "$12", "rating_count": 40}] * 8}
        return {"keyword": kw, "ok": True, "error": None, "result_count": 9000,
                "top8": [{"title": "B", "price": "$14", "rating_count": 8000}] * 8}

    monkeypatch.setattr(fetch, "fetch_keyword", fake_fetch)


def test_cli_runs_pipeline_to_report(tmp_path, monkeypatch, capsys):
    _stub_pipeline(monkeypatch)
    code = cli.main(["sobriety journal", "--out", str(tmp_path), "--key", "GOOD"])
    assert code == 0
    html = (tmp_path / "report.html").read_text()
    assert "sober journal" in html and "GOLDEN" in html.upper()
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["seed"] == "sobriety journal" and len(run["results"]) == 2


def test_cli_invalid_license_prints_purchase_url(tmp_path, monkeypatch, capsys):
    _stub_pipeline(monkeypatch, valid_license=False)
    code = cli.main(["sobriety journal", "--out", str(tmp_path), "--key", "BAD"])
    assert code != 0
    err = capsys.readouterr().err
    assert lic.PURCHASE_URL in err


def test_cli_compare_mode(tmp_path, monkeypatch, capsys):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"seed": "s", "results": [{"keyword": "k", "score": 0.1}]}))
    b.write_text(json.dumps({"seed": "s", "results": [{"keyword": "k", "score": 0.3}]}))
    code = cli.main(["--compare", str(a), str(b)])
    assert code == 0
    out = capsys.readouterr().out
    assert "k" in out  # the changed keyword is reported


def test_end_to_end_from_fixtures(tmp_path, monkeypatch):
    # Full pipeline, license valid, fetch stubbed from realistic rows -> golden flag present.
    _stub_pipeline(monkeypatch)
    code = cli.main(["sobriety journal", "--out", str(tmp_path), "--key", "GOOD"])
    assert code == 0
    run = json.loads((tmp_path / "run.json").read_text())
    assert any(r.get("golden") for r in run["results"])  # the low-competition keyword is golden
