from spec_workbench import checks, model


def spec_with(**colls):
    s = model.empty_spec("T")
    s["problem"] = "p"
    for name in ("users", "goals", "non_goals"):
        model.add(s, name, {"text": f"{name} placeholder"})
    for coll, items in colls.items():
        for fields in items:
            model.add(s, coll, fields)
    return s


def keys(spec, live=True):
    return {f["key"] for f in checks.run(spec) if not (live and f["waived"])}


def by_key(spec):
    return {f["key"]: f for f in checks.run(spec)}


def test_ambiguity_blocks_must_and_warns_should():
    s = spec_with(requirements=[{"text": "It must be fast."},
                                {"text": "It should be intuitive.", "priority": "should"}])
    f = by_key(s)
    assert f["WB001:R1"]["severity"] == "blocking"
    assert f["WB001:R2"]["severity"] == "warning"


def test_missing_incomplete_and_unobservable_criteria():
    s = spec_with(requirements=[{"text": "Saves a draft every 30 seconds."},
                                {"text": "Exports CSV."}, {"text": "Remembers theme.", "priority": "could"}],
                  acceptance=[{"requirement": "R2", "given": "a list", "when": "export", "then": ""},
                              {"requirement": "R1", "given": "an open draft", "when": "30 s pass",
                               "then": "the user feels safe"}])
    k = keys(s)
    assert "WB003:AC1" in k            # empty then
    assert "WB004:AC2" in k            # no observable outcome
    assert "WB002:R3" not in k         # could-priority needs no criterion
    assert by_key(s)["WB004:AC2"]["judgment"] is True


def test_open_decision_blocks_only_when_depended_on():
    s = spec_with(requirements=[{"text": "Sends reminders.", "depends_on": ["D1"]}],
                  decisions=[{"question": "Slack or email?"}, {"question": "Colors?"}])
    f = by_key(s)
    assert f["WB005:D1~R1"]["severity"] == "blocking"
    assert f["WB005:D2"]["severity"] == "warning"


def test_nongoal_conflict():
    s = spec_with(non_goals=[{"text": "No mobile app in v1."}],
                  requirements=[{"text": "Members must get a push alert in the mobile app."}])
    assert by_key(s)["WB006:N2~R1"]["severity"] == "blocking"


def test_bounds_parse_and_conflict():
    b = checks.bounds("Results must load in under 1 second.")
    assert b[0]["kind"] == "upper" and b[0]["value"] == 1 and b[0]["subject"] == {"result", "load"}
    assert checks.bounds("Keep at least 15 minutes")[0]["value"] == 900
    assert checks.bounds("in 3 MB")[0:] == []           # "in" only bounds time
    s = spec_with(requirements=[{"text": "The poll must close within 10 minutes."},
                                {"text": "Polls must stay open at least 15 minutes."},
                                {"text": "Results show within 2 seconds."},
                                {"text": "Results load in under 1 second."}])
    f = by_key(s)
    assert f["WB007:R1~R2"]["severity"] == "blocking"
    assert f["WB007:R3~R4"]["severity"] == "warning"
    assert not any(k.startswith("WB007:R1~R3") or k.startswith("WB007:R2~R3") for k in f)


def test_polarity_duplicate_and_compound():
    s = spec_with(requirements=[{"text": "Voters can change their vote."},
                                {"text": "Voters cannot change their vote once cast."},
                                {"text": "Admins can export the audit log."},
                                {"text": "Admins can export audit logs."},
                                {"text": "It must save and must sync."}])
    k = keys(s)
    assert "WB008:R1~R2" in k and "WB009:R3~R4" in k and "WB010:R5" in k
    assert "WB009:R1~R2" not in k     # opposite polarity is a conflict, not a duplicate


def test_sections_assumptions_dangling_unclassified():
    s = model.empty_spec()
    model.add(s, "assumptions", {"text": "Everyone has email."})
    model.add(s, "acceptance", {"requirement": "R9", "given": "g", "when": "w", "then": "shows 1"})
    model.add(s, "unclassified", {"text": "Make it nice.", "source": {"line": 4}})
    f = by_key(s)
    assert f["WB011"]["severity"] == "blocking"            # no requirements at all
    assert {"WB011:problem", "WB011:users", "WB011:goals", "WB011:non_goals"} <= f.keys()
    assert "WB012:A1" in f and f["WB013:AC1"]["severity"] == "blocking"
    assert f["WB014:X1"]["severity"] == "info"
    model.add(s, "requirements", {"text": "Runs.", "depends_on": ["D7"]})
    assert "WB013:R1~D7" in keys(s)


def test_waiver_suppresses_but_keeps_finding_and_stale_waivers_are_reported():
    s = spec_with(requirements=[{"text": "It must be fast."}])
    model.waive(s, "WB001:R1", "fast is defined in C1")
    model.waive(s, "WB999:R1", "old")
    f = by_key(s)["WB001:R1"]
    assert f["waived"] and f["waiver"] == "fast is defined in C1"
    summ = checks.summary(checks.run(s))
    assert summ["waived"] == 1
    assert [w["key"] for w in checks.stale_waivers(s, checks.run(s))] == ["WB999:R1"]


def test_ready_means_zero_unwaived_blocking():
    s = spec_with(requirements=[{"text": "Shows the total in dollars."}],
                  acceptance=[{"requirement": "R1", "given": "2 items of 3 dollars",
                               "when": "the cart opens", "then": "the total shows 6 dollars"}])
    assert checks.summary(checks.run(s))["ready"] is True


def test_run_is_deterministic_and_naturally_sorted():
    reqs = [{"text": f"Item {n} must exist."} for n in range(1, 12)]
    s = spec_with(requirements=reqs)
    a, b = checks.run(s), checks.run(s)
    assert a == b
    order = [f["key"] for f in a if f["rule"] == "WB002"]
    assert order[:3] == ["WB002:R1", "WB002:R2", "WB002:R3"] and order[-1] == "WB002:R11"
