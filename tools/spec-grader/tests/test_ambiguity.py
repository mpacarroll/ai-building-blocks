from spec_grader import ambiguity


def test_flags_weasel_words_with_line_and_reason():
    text = "The system should be fast and user-friendly.\nIt must handle errors as needed."
    flags = ambiguity.find_ambiguities(text)
    terms = {f["term"] for f in flags}
    assert "fast" in terms and "user-friendly" in terms and "as needed" in terms
    # each flag carries a 1-based line and a human reason
    fast = next(f for f in flags if f["term"] == "fast")
    assert fast["line"] == 1 and isinstance(fast["why"], str) and fast["why"]


def test_precise_requirement_has_no_flags():
    text = "The API MUST return HTTP 200 within 500 milliseconds for a valid request."
    assert ambiguity.find_ambiguities(text) == []


def test_matching_is_word_boundaried_and_case_insensitive():
    # "Fastener" must not match "fast"; "FAST" must match.
    assert ambiguity.find_ambiguities("Ship the fastener.") == []
    assert any(f["term"] == "fast" for f in ambiguity.find_ambiguities("It must be FAST."))


def test_multiword_phrases_detected():
    flags = ambiguity.find_ambiguities("Handle it as appropriate, and so on.")
    terms = {f["term"] for f in flags}
    assert "as appropriate" in terms and "and so on" in terms
