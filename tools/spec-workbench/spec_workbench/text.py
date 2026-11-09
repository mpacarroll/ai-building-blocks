"""Small, deterministic text helpers shared by intake and checks."""
import re

STOPWORDS = set("""
a an the and or but if then else of to in on at by for with from as is are was
were be been being it its this that these those there their they them we our us
you your i me my he she his her so such than too very can could should would
will shall must may might do does did done have has had having also just only
not no never any all each every some into out over under about after before
when where which who whom what why how while able allow allows let lets get gets
need needs needed want wants one per via up down off own same other more most
less least way ways thing things make makes sure like etc
""".split())

NEGATIONS = {"not", "no", "never", "cannot", "can't", "won't", "don't", "doesn't",
             "without", "nor"}

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")


def stem(word: str) -> str:
    """A tiny suffix stripper: enough to match 'votes' with 'vote'."""
    for suffix in ("ing", "ies", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            if suffix == "ies":
                return word[:-3] + "y"
            if suffix == "s" and word.endswith("ss"):
                return word
            return word[: -len(suffix)]
    return word


def words(text: str) -> list:
    return _WORD.findall(text.lower())


def content_tokens(text: str, extra_stop=()) -> set:
    stop = STOPWORDS | NEGATIONS | set(extra_stop)
    return {stem(w) for w in words(text) if w not in stop and not w.isdigit()}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_negative(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"\b(must|shall|should|will|can|may)\s+not\b", lowered):
        return True
    return any(w in NEGATIONS for w in words(lowered))


_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


def sentences(line: str) -> list:
    return [s.strip() for s in _SENTENCE.split(line) if s.strip()]
