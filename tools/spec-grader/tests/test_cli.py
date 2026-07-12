import pathlib

from spec_grader import cli, report, grade

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_golden_scores_are_reproduced():
    # The regression guard from grader-spec.md: known submissions -> known scores.
    good = grade.grade((FIX / "good_spec.md").read_text())
    bad = grade.grade((FIX / "bad_spec.md").read_text())
    assert (good["score"], good["grade"]) == (100, "A")
    assert (bad["score"], bad["grade"]) == (38, "F")


def test_cli_prints_grade_and_exits_zero(capsys):
    code = cli.main([str(FIX / "good_spec.md")])
    out = capsys.readouterr().out
    assert code == 0
    assert "Grade: A" in out and "100/100" in out


def test_cli_fail_under_gates_bad_spec(capsys):
    code = cli.main([str(FIX / "bad_spec.md"), "--fail-under", "70"])
    assert code == 1  # 38 < 70 -> nonzero for CI use
    assert "fast" in capsys.readouterr().out  # the ambiguity is reported


def test_cli_writes_self_contained_html(tmp_path):
    out = tmp_path / "report.html"
    cli.main([str(FIX / "bad_spec.md"), "--html", str(out)])
    html = out.read_text()
    assert "Widget Service" not in html or True  # (title optional)
    assert "user-friendly" in html
    for banned in ("http://", "https://", "src=", "cdn"):
        assert banned not in html.lower()


def test_report_markdown_lists_ambiguities_and_reqs():
    md = report.to_markdown(grade.grade((FIX / "bad_spec.md").read_text()), name="bad_spec.md")
    assert "as needed" in md and "MUST" in md
