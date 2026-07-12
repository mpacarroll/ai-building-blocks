from spec_grader import grade


def test_clean_spec_scores_100_grade_a():
    text = ("The API MUST return HTTP 200 within 500 milliseconds.\n"
            "The client SHALL retry once on a timeout.")
    r = grade.grade(text)
    assert r["n_requirements"] == 2
    assert r["n_ambiguities"] == 0
    assert r["score"] == 100 and r["grade"] == "A"


def test_one_ambiguous_requirement_of_two_scores_73_grade_c():
    text = ("The system MUST be fast.\n"
            "The client SHALL retry once on a timeout.")
    r = grade.grade(text)
    # ambiguous_ratio 0.5 -> -25 ; one ambiguity ('fast') -> -2 ; 100-27 = 73
    assert r["n_requirements"] == 2 and r["n_ambiguous_requirements"] == 1
    assert r["score"] == 73 and r["grade"] == "C"


def test_spec_with_no_normative_requirements_fails():
    r = grade.grade("This is prose describing the system in general terms.")
    assert r["n_requirements"] == 0
    assert r["grade"] == "F"
    assert "no testable" in r["summary"].lower()


def test_grade_is_deterministic():
    text = "The system MUST be scalable and MUST handle errors gracefully."
    assert grade.grade(text) == grade.grade(text)
