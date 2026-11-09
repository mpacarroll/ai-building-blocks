from spec_workbench.intake import classify, intake


def test_classify_cue_order():
    assert classify("Should ties be broken randomly or by the organizer?") == "decisions"
    assert classify("No mobile app in v1.") == "non_goals"
    assert classify("Integrations are out of scope.") == "non_goals"
    assert classify("I assume everyone has email.") == "assumptions"
    assert classify("Every Friday we waste time arguing.") == "problem"
    assert classify("The goal is to decide in five minutes.") == "goals"
    assert classify("It's for small office teams.") == "users"
    assert classify("Votes need to be anonymous.") == "requirements"
    assert classify("Budget is one developer for two weeks.") == "constraints"
    assert classify("Make it look nice.") == "unclassified"


def test_intake_keeps_every_sentence_with_its_source_line():
    brief = "# Poll\n\nVotes must be anonymous. Make it pop.\n- It would be nice to save favorites.\n"
    spec = intake(brief)
    assert spec["title"] == "Poll"
    reqs = spec["requirements"]
    assert [r["priority"] for r in reqs] == ["must", "could"]
    assert reqs[0]["source"] == {"line": 3, "text": "Votes must be anonymous."}
    assert reqs[1]["source"]["line"] == 4
    assert spec["unclassified"][0]["text"] == "Make it pop."


def test_section_headings_override_cues():
    brief = "# T\n## Out of scope\n- Users must be able to export PDFs.\n## Open questions\n- Pricing\n"
    spec = intake(brief)
    assert spec["non_goals"][0]["text"] == "Users must be able to export PDFs."
    assert spec["decisions"][0]["question"] == "Pricing"
    assert spec["requirements"] == []


def test_requirement_with_trailing_question_becomes_linked_pair():
    spec = intake("# T\nWe need to send a reminder before the poll closes, Slack or email?\n")
    d, r = spec["decisions"][0], spec["requirements"][0]
    assert d["question"] == "Slack or email?" and d["options"] == ["Slack", "email"]
    assert r["text"] == "We need to send a reminder before the poll closes."
    assert r["depends_on"] == ["D1"]


def test_title_override_and_untitled_brief():
    assert intake("Votes must be anonymous.", title="Given")["title"] == "Given"
    assert intake("Lunch helper\nVotes must count.")["title"] == "Lunch helper"
