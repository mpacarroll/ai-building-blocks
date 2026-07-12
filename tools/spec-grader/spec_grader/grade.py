"""Turn the ambiguity + requirement analysis into one score and a letter grade.

The formula is deterministic and documented, so a grade is reproducible and
arguable — never a black box:

  no normative requirements -> score 40, grade F (nothing binding to build to)
  otherwise:
    penalty_req = 50 * (ambiguous requirements / total requirements)
    penalty_amb = min(30, 2 * total ambiguity flags)
    score = max(0, round(100 - penalty_req - penalty_amb))
  grade: >=90 A, >=80 B, >=70 C, >=60 D, else F
"""
from .ambiguity import find_ambiguities
from .requirements import extract

_NO_REQ_SCORE = 40


def _letter(score: int) -> str:
    for cutoff, letter in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= cutoff:
            return letter
    return "F"


def grade(text: str) -> dict:
    reqs = extract(text)
    ambiguities = find_ambiguities(text)
    n_req = len(reqs)
    n_ambig_req = sum(1 for r in reqs if r["ambiguous"])

    if n_req == 0:
        score = _NO_REQ_SCORE
        summary = ("No testable requirements found. A spec needs normative "
                   "statements (MUST / SHALL / REQUIRED) or an implementer has "
                   "nothing binding to build to.")
    else:
        penalty_req = 50 * (n_ambig_req / n_req)
        penalty_amb = min(30, 2 * len(ambiguities))
        score = max(0, round(100 - penalty_req - penalty_amb))
        summary = (f"{n_req} testable requirement(s), {n_ambig_req} of them ambiguous; "
                   f"{len(ambiguities)} ambiguous phrase(s) total.")

    return {
        "requirements": reqs,
        "ambiguities": ambiguities,
        "n_requirements": n_req,
        "n_ambiguous_requirements": n_ambig_req,
        "n_ambiguities": len(ambiguities),
        "score": score,
        "grade": _letter(score),
        "summary": summary,
    }
