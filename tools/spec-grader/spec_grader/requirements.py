"""Extract normative (testable) requirements from a spec using RFC 2119
keywords, and mark any that are also ambiguous — a mandatory requirement built
on a weasel word is the worst kind, because it looks binding but can't be verified.

Only the mandatory keywords count as testable requirements: MUST, MUST NOT,
SHALL, SHALL NOT, REQUIRED. They are matched capitalized, as RFC 2119 intends
normative use to be. SHOULD / MAY are advisory and deliberately not counted.
"""
import re

from .ambiguity import find_ambiguities

_KEYWORDS = ["MUST NOT", "SHALL NOT", "MUST", "SHALL", "REQUIRED"]
_PATTERN = re.compile(r"(?<![A-Za-z])(" + "|".join(_KEYWORDS) + r")(?![A-Za-z])")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+\S")


def extract(text: str) -> list:
    """Return [{line, text, keyword, ambiguous}] — the testable requirements.

    A requirement is either a normative RFC 2119 keyword (MUST/SHALL/REQUIRED)
    or a numbered list item (many specs enumerate requirements that way). A
    numbered line counts once even if it also contains a keyword, so the two
    forms are not double-counted.
    """
    out = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        line_ambiguous = bool(find_ambiguities(line))
        if _NUMBERED.match(line):
            out.append({"line": lineno, "text": line.strip(),
                        "keyword": "list-item", "ambiguous": line_ambiguous})
            continue
        for m in _PATTERN.finditer(line):
            out.append({"line": lineno, "text": line.strip(),
                        "keyword": m.group(1), "ambiguous": line_ambiguous})
    return out
