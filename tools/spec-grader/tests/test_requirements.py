from spec_grader import requirements as req


def test_extracts_normative_keywords_only():
    text = (
        "The API MUST return HTTP 200.\n"
        "The client SHALL retry once.\n"
        "The cache is REQUIRED to expire after 30 days.\n"
        "The UI should look nice.\n"          # 'should' is non-normative -> not counted
        "Some background prose here.\n"
    )
    reqs = req.extract(text)
    assert len(reqs) == 3
    assert {r["keyword"] for r in reqs} == {"MUST", "SHALL", "REQUIRED"}
    assert all(r["ambiguous"] is False for r in reqs)


def test_flags_a_requirement_that_is_also_ambiguous():
    text = "The system MUST be fast and MUST handle errors gracefully."
    reqs = req.extract(text)
    assert len(reqs) == 2  # two MUSTs on one line -> two requirements
    assert all(r["ambiguous"] for r in reqs)


def test_lowercase_must_is_not_a_normative_requirement():
    # RFC 2119 keywords are capitalized when normative.
    assert req.extract("You must be logged in, obviously.") == []


def test_numbered_list_items_count_as_requirements():
    # Many good specs enumerate requirements as a numbered list instead of MUST.
    text = ("## Functional requirements\n"
            "1. Expand the seed through autocomplete.\n"
            "2. Fetch the top 30 results.\n"
            "3. Score each keyword.\n")
    reqs = req.extract(text)
    assert len(reqs) == 3
    assert {r["keyword"] for r in reqs} == {"list-item"}


def test_numbered_item_with_must_is_not_double_counted():
    reqs = req.extract("1. The service MUST return 200.")
    assert len(reqs) == 1
