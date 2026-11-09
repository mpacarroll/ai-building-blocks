import re

from spec_workbench import diff, export, model


def base():
    s = model.empty_spec("Poll")
    s["problem"] = "Lunch takes too long."
    model.add(s, "requirements", {"text": "It must be fast."})
    model.add(s, "requirements", {"text": "Votes are counted.", "priority": "should"})
    model.add(s, "decisions", {"question": "Slack or email?", "options": ["Slack", "email"]})
    return s


def test_diff_lists_item_changes_and_finding_deltas():
    a = base()
    b = model.clone(a)
    model.edit(b, "R1", {"text": "Results must appear within 2 seconds."})
    model.remove(b, "R2")
    model.add(b, "acceptance", {"requirement": "R1", "given": "a closed poll", "when": "it closes",
                                "then": "results show within 2 seconds"})
    model.decide(b, "D1", "email")
    d = diff.diff(a, b)
    assert [i["id"] for i in d["added"]] == ["AC1"]
    assert [i["id"] for i in d["removed"]] == ["R2"]
    assert {c["id"] for c in d["changed"]} == {"R1", "D1"}
    resolved = {f["key"] for f in d["resolved"]}
    assert {"WB001:R1", "WB002:R1", "WB005:D1"} <= resolved
    text = diff.to_text(d, 1, 2)
    assert "+ AC1" in text and "- R2" in text and "[fixed] WB001:R1" in text


def test_markdown_numbers_requirements_and_feeds_spec_grader():
    md = export.to_markdown(base(), rev=3)
    assert "1. **R1** (must) It must be fast." in md
    assert "Revision 3." in md and "D1 (open)" in md
    lint = export.lint(base())
    assert lint["n_requirements"] == 2 and lint["n_ambiguities"] >= 1


def test_checklist_lists_gaps_and_open_decisions():
    c = export.to_checklist(base())
    assert "not proof" in c
    assert "- [ ] R1 (must)" in c and "- [ ] D1: Slack or email?" in c


def test_pytest_skeleton_fails_until_written(tmp_path):
    s = base()
    model.add(s, "acceptance", {"requirement": "R1", "given": 'a "quoted" state', "when": "x",
                                "then": 'shows """ triple'})
    src = export.to_pytest(s)
    compile(src, "skel.py", "exec")
    assert src.count("raise NotImplementedError") == 1
    assert "#   R2: Votes are counted." in src
    ns = {}
    exec(src, ns)
    test = [v for k, v in ns.items() if k.startswith("test_")][0]
    try:
        test()
        raise AssertionError("skeleton test passed")
    except NotImplementedError:
        pass


def test_html_is_self_contained_and_honest():
    s = base()
    s["title"] = "<script>alert(1)</script>"
    html = export.to_html(s, rev=2, history=[{"rev": 1, "at": "t", "message": "m"}])
    for banned in ("http://", "https://", "src=", "<script>alert"):
        assert banned not in html
    assert "Not ready to build" in html
    assert "never proof of success" in html
    assert "What these checks cannot judge" in html
    assert re.search(r"prefers-color-scheme:dark", html)
