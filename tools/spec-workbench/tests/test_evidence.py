import json

import pytest

from spec_workbench import cli, evidence as ev, export, model, store


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setenv("SPEC_BENCH_NOW", "2026-11-09T09:00:00Z")


def spec3():
    s = model.empty_spec("T")
    for n in (1, 2, 3):
        model.add(s, "requirements", {"text": f"It must do thing {n}."})
        model.add(s, "acceptance", {"requirement": f"R{n}", "given": "g", "when": "w",
                                    "then": f"it shows {n}"})
    return s


def junit(tmp_path, cases, name="junit.xml"):
    body = []
    for case_name, outcome, msg in cases:
        inner = {"passed": "", "failed": f'<failure message="{msg}">{msg}</failure>',
                 "error": f'<error message="{msg}"/>', "skipped": '<skipped message="s"/>'}[outcome]
        body.append(f'<testcase classname="tests.test_acc" name="{case_name}">{inner}</testcase>')
    p = tmp_path / name
    p.write_text(f'<testsuites><testsuite name="pytest">{"".join(body)}</testsuite></testsuites>')
    return p


def test_fingerprint_is_stable_and_tracks_wording_only():
    ac = {"id": "AC1", "requirement": "R1", "given": "g", "when": "w", "then": "t",
          "status": "draft"}
    fp = ev.fingerprint(ac)
    assert len(fp) == 10 and fp == ev.fingerprint(dict(ac))
    assert ev.fingerprint({**ac, "status": "agreed"}) == fp          # status is not wording
    assert ev.fingerprint({**ac, "then": "t  "}) == fp               # whitespace is not wording
    assert ev.fingerprint({**ac, "then": "u"}) != fp
    assert ev.fingerprint({**ac, "requirement": "R2"}) != fp


def test_scan_pins_binds_to_next_test_only(tmp_path):
    f = tmp_path / "test_acc.py"
    f.write_text("# spec-bench: AC1 fp=aaaaaaaaaa\n# spec-bench: AC2 fp=bbbbbbbbbb\n"
                 "@pytest.mark.x\ndef test_one():\n    pass\n\n"
                 "# spec-bench: AC3 fp=cccccccccc\nX = 1\ndef test_two():\n    pass\n")
    pins = ev.scan_pins([tmp_path])
    assert pins == {("test_acc", "test_one"): {"AC1": "aaaaaaaaaa", "AC2": "bbbbbbbbbb"}}
    with pytest.raises(ev.EvidenceError):
        ev.scan_pins([tmp_path / "missing"])


def test_every_status(tmp_path):
    s = spec3()
    model.add(s, "requirements", {"text": "It must do thing 4."})
    for n in (4, 5, 6):
        model.add(s, "acceptance", {"requirement": "R4", "given": "g", "when": "w",
                                    "then": f"it shows {n}"})
    fps = {ac["id"]: ev.fingerprint(ac) for ac in s["acceptance"]}
    pins = {("test_acc", "test_ac1_ok"): {"AC1": fps["AC1"]},
            ("test_acc", "test_ac2_old"): {"AC2": "0000000000"},
            ("test_acc", "test_ac4_fails"): {"AC4": fps["AC4"]},
            ("test_acc", "test_ac5_skel"): {"AC5": fps["AC5"]}}
    tests = ev.parse_junit(junit(tmp_path, [
        ("test_ac1_ok", "passed", ""), ("test_ac2_old", "passed", ""),
        ("test_ac3_nopin", "passed", ""), ("test_ac4_fails", "failed", "assert 1 == 2"),
        ("test_ac5_skel", "failed", "NotImplementedError: write the check for AC5"),
        ("test_ac6_skip[param]", "skipped", ""), ("test_ac99_gone", "passed", ""),
        ("test_helper", "passed", "")]))
    r = ev.evaluate(s, tests, pins)
    st = {k: v["status"] for k, v in r["criteria"].items()}
    assert st == {"AC1": "verified", "AC2": "stale", "AC3": "unpinned", "AC4": "failing",
                  "AC5": "unwritten", "AC6": "skipped"}
    assert [o["criterion"] for o in r["orphans"]] == ["AC99"]
    assert r["unmapped"] == ["test_acc::test_helper"]
    roll = ev.requirement_rollup(s, r["criteria"])
    assert roll == {"R1": "verified", "R2": "stale", "R3": "unpinned", "R4": "failing"}


def test_untested_and_mixed_results(tmp_path):
    s = spec3()
    fp1 = ev.fingerprint(s["acceptance"][0])
    pins = {("test_acc", "test_a"): {"AC1": fp1}, ("test_acc", "test_b"): {"AC1": fp1}}
    tests = ev.parse_junit(junit(tmp_path, [("test_a", "passed", ""),
                                            ("test_b", "error", "boom")]))
    r = ev.evaluate(s, tests, pins)
    assert r["criteria"]["AC1"]["status"] == "failing"   # one failure outweighs a pass
    assert r["criteria"]["AC2"]["status"] == "untested"
    assert ev.requirement_rollup(s, r["criteria"])["R2"] == "untested"


def test_parse_junit_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("not xml")
    with pytest.raises(ev.EvidenceError):
        ev.parse_junit(bad)
    with pytest.raises(ev.EvidenceError):
        ev.parse_junit(tmp_path / "missing.xml")
    other = tmp_path / "other.xml"
    other.write_text("<html/>")
    with pytest.raises(ev.EvidenceError, match="not a JUnit"):
        ev.parse_junit(other)


def test_current_view_marks_drift_since_the_run():
    s = spec3()
    run = {"run": 1, "criteria": {}, "orphans": [], "unmapped": []}
    for ac in s["acceptance"]:
        run["criteria"][ac["id"]] = {"status": "verified", "fingerprint": ev.fingerprint(ac),
                                     "tests": [{"test": f"t::{ac['id']}", "outcome": "passed",
                                                "message": "", "pin": ev.fingerprint(ac)}]}
    model.edit(s, "AC2", {"then": "it shows 22"})
    model.remove(s, "AC3")
    model.add(s, "acceptance", {"requirement": "R3", "given": "g", "when": "w", "then": "x 1"})
    view = ev.current_view(s, run)
    st = {k: v["status"] for k, v in view["criteria"].items()}
    assert st == {"AC1": "verified", "AC2": "stale", "AC4": "untested"}
    assert "wording changed" in view["criteria"]["AC2"]["note"]
    assert [o["criterion"] for o in view["orphans"]] == ["AC3"]


def test_runs_are_saved_numbered_and_damage_is_skipped(tmp_path):
    s = spec3()
    store.create(tmp_path, s, "first")
    r = ev.evaluate(s, [], {})
    assert ev.save_run(tmp_path, 1, "a.xml", r) == 1
    assert ev.save_run(tmp_path, 1, "b.xml", r) == 2
    (tmp_path / "evidence" / "0003.json").write_text("{broken")
    assert [x["source"] for x in ev.runs(tmp_path)] == ["a.xml", "b.xml"]
    assert ev.save_run(tmp_path, 1, "c.xml", r) == 4   # never overwrites, even damaged files
    assert (tmp_path / "evidence" / "0003.json").read_text() == "{broken"


def _workspace_with_tests(tmp_path):
    ws = tmp_path / "ws"
    store.create(ws, spec3(), "first")
    skel = tmp_path / "tests" / "test_acc.py"
    skel.parent.mkdir()
    cli.main(["export", str(ws), "--format", "pytest", "--out", str(skel)])
    return ws, skel


def test_verify_cli_saves_gates_and_feeds_exports(tmp_path, capsys):
    ws, skel = _workspace_with_tests(tmp_path)
    assert skel.read_text().count("# spec-bench: AC") == 3
    xml = junit(tmp_path, [("test_ac1_it_must_do_thing_1", "passed", ""),
                           ("test_ac2_it_must_do_thing_2", "passed", ""),
                           ("test_ac3_it_must_do_thing_3", "failed",
                            "NotImplementedError: write the check for AC3")])
    capsys.readouterr()
    args = ["verify", str(ws), "--junit", str(xml), "--tests", str(skel.parent)]
    assert cli.main(args + ["--fail-on", "failing"]) == 0
    out = capsys.readouterr().out
    assert "2 of 3 criteria verified" in out and "1 unwritten" in out
    assert "not that it checks what the criterion says" in out
    assert cli.main(args + ["--fail-on", "unverified", "--no-save"]) == 1
    assert len(ev.runs(ws)) == 1
    capsys.readouterr()
    assert cli.main(args + ["--json", "--no-save"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["counts"]["verified"] == 2 and data["requirements"]["R3"] == "unwritten"

    cli.main(["export", str(ws), "--format", "checklist"])
    checklist = capsys.readouterr().out
    assert "- [x] AC1" in checklist and "- [ ] AC3" in checklist and "evidence run 1" in checklist
    cli.main(["export", str(ws), "--format", "html"])
    page = capsys.readouterr().out
    assert "2 of 3 criteria verified" in page
    assert "http://" not in page and "https://" not in page and "src=" not in page

    # Change AC1's wording: the saved run now reads stale for it.
    cli.main(["edit", str(ws), "AC1", "--then", "it shows 100"])
    capsys.readouterr()
    assert cli.main(["evidence", str(ws), "1", "--fail-on", "unverified"]) == 1
    out = capsys.readouterr().out
    assert "AC1   STALE" in out and "wording changed after evidence run 1" in out
    cli.main(["evidence", str(ws)])
    assert "2/3 verified" in capsys.readouterr().out


def test_verify_errors_exit_2(tmp_path, capsys):
    ws, _ = _workspace_with_tests(tmp_path)
    assert cli.main(["verify", str(ws), "--junit", str(tmp_path / "nope.xml")]) == 2
    assert "cannot read JUnit" in capsys.readouterr().err
    assert cli.main(["evidence", str(ws), "7"]) == 2


def test_html_without_evidence_says_how_to_get_it():
    page = export.to_html(spec3(), 1)
    assert "No test evidence yet" in page
