import json
import pathlib

import pytest

from spec_workbench import cli

BRIEF = "# Poll\nVotes must be fast.\nNo mobile app in v1.\nMake it pop.\n"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setenv("SPEC_BENCH_NOW", "2026-11-09T09:00:00Z")


@pytest.fixture
def ws(tmp_path):
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF)
    w = tmp_path / "ws"
    assert cli.main(["intake", str(w), str(brief)]) == 0
    return w


def test_check_text_json_and_gates(ws, capsys):
    capsys.readouterr()
    assert cli.main(["check", str(ws)]) == 0
    out = capsys.readouterr().out
    assert "Not ready to build" in out and "never proof" in out and "cannot judge" in out
    assert cli.main(["check", str(ws), "--fail-on", "blocking"]) == 1
    capsys.readouterr()
    cli.main(["check", str(ws), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["revision"] == 1 and data["summary"]["ready"] is False
    assert "WB001:R1" in {f["key"] for f in data["findings"]}


def test_full_revision_loop(ws, capsys):
    run = lambda *a: cli.main(list(a))  # noqa: E731
    w = str(ws)
    assert run("edit", w, "R1", "--text", "Votes must be saved within 1 second.") == 0
    assert run("edit", w, "problem", "--text", "Lunch takes too long.") == 0
    assert run("add", w, "criterion", "--req", "R1", "--given", "an open poll",
               "--when", "a voter taps a place", "--then", "the vote shows within 1 second") == 0
    assert run("add", w, "decision", "Who breaks ties?", "--option", "organizer") == 0
    assert run("decide", w, "D1", "--choice", "organizer", "--rationale", "they order") == 0
    assert run("remove", w, "X1") == 0
    assert run("add", w, "user", "Office teams of 5 to 15 people.") == 0
    assert run("add", w, "goal", "Pick a place in five minutes.") == 0
    capsys.readouterr()
    assert run("check", w, "--fail-on", "warning") == 0, capsys.readouterr().out
    capsys.readouterr()
    assert run("history", w) == 0
    hist = capsys.readouterr().out.strip().splitlines()
    assert len(hist) == 9
    assert run("diff", w, "1", "9") == 0
    assert "[fixed] WB001:R1" in capsys.readouterr().out
    assert run("revert", w, "1") == 0
    capsys.readouterr()
    assert run("check", w, "--fail-on", "blocking") == 1    # back to the old problems
    assert len(list((ws / "history").glob("*.json"))) == 10  # revert never deletes history


def test_waive_and_apply_all_or_nothing(ws, tmp_path, capsys):
    w = str(ws)
    assert cli.main(["waive", w, "WB014:X1", "--reason", "decoration, not a requirement"]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"op": "remove", "id": "X1"}, {"op": "remove", "id": "R99"}]))
    before = (ws / "spec.json").read_text()
    assert cli.main(["apply", w, str(bad)]) == 2
    assert "operation 2" in capsys.readouterr().err
    assert (ws / "spec.json").read_text() == before
    good = tmp_path / "good.json"
    good.write_text(json.dumps([
        {"op": "add", "kind": "requirement", "as": "$r", "fields": {"text": "Totals must show."}},
        {"op": "add", "kind": "criterion", "fields": {"requirement": "$r", "given": "g",
                                                       "when": "w", "then": "shows 3"}}]))
    assert cli.main(["apply", w, str(good), "-m", "batch"]) == 0
    spec = json.loads((ws / "spec.json").read_text())
    assert spec["acceptance"][0]["requirement"] == "R2"


def test_errors_exit_2(tmp_path, capsys):
    assert cli.main(["check", str(tmp_path / "nope")]) == 2
    assert cli.main(["intake", str(tmp_path / "w"), str(tmp_path / "missing.md")]) == 2
    assert cli.main(["new", str(tmp_path / "t"), "--template", "cli-tool", "--title", "X"]) == 0
    assert cli.main(["edit", str(tmp_path / "t"), "D1"]) == 2
    assert "nothing to change" in capsys.readouterr().err


def test_templates_and_exports(tmp_path, capsys):
    assert cli.main(["templates"]) == 0
    assert "api-endpoint" in capsys.readouterr().out
    w = tmp_path / "t"
    cli.main(["new", str(w), "--template", "api-endpoint", "--title", "Search API"])
    for fmt in ("md", "json", "html", "checklist", "pytest"):
        out = tmp_path / f"o.{fmt}"
        assert cli.main(["export", str(w), "--format", fmt, "--out", str(out)]) == 0
        assert out.stat().st_size > 0
    assert "What is the rate limit per client?" in (tmp_path / "o.md").read_text()


def test_corrupt_workspace_is_recovered_from_cli(ws, capsys):
    (pathlib.Path(ws) / "spec.json").write_text("{")
    capsys.readouterr()
    assert cli.main(["check", str(ws)]) == 0
    assert "restored revision 1" in capsys.readouterr().err
