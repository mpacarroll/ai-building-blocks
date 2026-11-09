import pytest

from spec_workbench import model


def test_ids_are_sequential_and_never_reused_after_remove():
    s = model.empty_spec("T")
    r1 = model.add(s, "requirements", {"text": "A must work."})
    r2 = model.add(s, "requirements", {"text": "B must work."})
    assert (r1["id"], r2["id"]) == ("R1", "R2")
    model.remove(s, "R2")
    assert model.add(s, "requirements", {"text": "C must work."})["id"] == "R3"


def test_defaults_and_priority_validation():
    s = model.empty_spec()
    r = model.add(s, "requirements", {"text": "x"})
    assert r["priority"] == "must" and r["depends_on"] == []
    with pytest.raises(model.SpecError):
        model.add(s, "requirements", {"text": "y", "priority": "urgent"})
    with pytest.raises(model.SpecError):
        model.add(s, "requirements", {"text": ""})
    with pytest.raises(model.SpecError):
        model.edit(s, "R1", {"id": "R9"})


def test_decide_and_waive_require_content():
    s = model.empty_spec()
    model.add(s, "decisions", {"question": "Which?"})
    with pytest.raises(model.SpecError):
        model.decide(s, "D1", "  ")
    d = model.decide(s, "D1", "this", "because")
    assert d["status"] == "decided" and d["choice"] == "this"
    with pytest.raises(model.SpecError):
        model.waive(s, "WB001:R1", "")
    model.waive(s, "WB001:R1", "first")
    model.waive(s, "WB001:R1", "second")
    assert s["waivers"] == [{"key": "WB001:R1", "reason": "second"}]


def test_validate_rejects_bad_shapes():
    good = model.empty_spec()
    model.validate(good)
    for bad in ([], {"schema": 9}, {**good, "requirements": "x"},
                {**good, "requirements": [{"id": "D1", "text": "x"}]},
                {**good, "requirements": [{"id": "R1", "text": "a"}, {"id": "R1", "text": "b"}]}):
        with pytest.raises(model.SpecError):
            model.validate(bad)


def test_migrate_schema_zero_plain_strings():
    spec = model.migrate({"title": "Old", "requirements": ["It must run."],
                          "decisions": ["Which database?"]})
    model.validate(spec)
    assert spec["requirements"][0]["text"] == "It must run."
    assert spec["decisions"][0]["question"] == "Which database?"
    with pytest.raises(model.SpecError):
        model.migrate({"schema": 7})
