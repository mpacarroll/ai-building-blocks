"""Turn a messy brief into a draft structured spec.

Deterministic and rule based: every sentence is classified by documented cue
words, in a fixed order, and every item records the line it came from. A
sentence that matches no cue goes to `unclassified`, never to the bin, so the
author decides what it was.

Classification order (first match wins):
  section heading hint > decision > non-goal > assumption > problem > goal >
  users > requirement > constraint > unclassified
"""
import re

from . import model
from .text import sentences

# Section headings override sentence cues for the lines beneath them.
_SECTION_HINTS = [
    (re.compile(r"out of scope|non-?goals?|not doing|won'?t do", re.I), "non_goals"),
    (re.compile(r"open questions?|questions|decisions?|unknowns?", re.I), "decisions"),
    (re.compile(r"assumptions?", re.I), "assumptions"),
    (re.compile(r"\b(users?|audience|personas?|who)\b", re.I), "users"),
    (re.compile(r"\bgoals?\b|\bwhy\b|objectives?", re.I), "goals"),
    (re.compile(r"constraints?|budget|limits?", re.I), "constraints"),
    (re.compile(r"requirements?|features?|must.haves?|behaviou?r", re.I), "requirements"),
    (re.compile(r"problem|background|context", re.I), "problem"),
]

_DECISION = re.compile(r"\?\s*$|\bnot sure\b|\btbd\b|\bundecided\b|"
                       r"\bneed to decide\b|\beither\b.+\bor\b", re.I)
_NON_GOAL = re.compile(r"^(no|not)\b|out of scope|not in scope|\bwon'?t\b|\bwill not\b|"
                       r"\bdon'?t need\b|\bno need\b|\bnon-?goal\b|\bnot going to\b|"
                       r"\bnot (?:in|for) v\d\b", re.I)
_ASSUMPTION = re.compile(r"\bassum(e|es|ed|ing|ption)\b|\bprobably\b|\bpresumably\b|"
                         r"\bi think\b|\bwe think\b|\blikely\b|\bi guess\b|\bi believe\b", re.I)
_PROBLEM = re.compile(r"\bwaste[sd]?\b|\bproblem\b|\bpain\b|\bstruggl|\bfrustrat|"
                      r"\bcurrently\b|\btoday\b|\bannoying\b|\btakes too long\b", re.I)
_GOAL = re.compile(r"\bgoal\b|\bso that\b|\bwe want to\b|\bthe point is\b|\baim\b|"
                   r"\bobjective\b|\bsuccess (is|means|looks like)\b", re.I)
_USERS = re.compile(r"^(it'?s|this is|built|made|designed|meant) for\b|^(users?|audience|"
                    r"customers?) (are|is|will be)\b|\bused by\b|\btarget users?\b", re.I)
_MUST = re.compile(r"\b(must|shall|needs? to|has to|have to|required|requires?|always|"
                   r"never|cannot|can'?t)\b", re.I)
_SHOULD = re.compile(r"\bshould\b", re.I)
_COULD = re.compile(r"\b(would be nice|nice to have|could|optionally|bonus)\b", re.I)
_CAPABILITY = re.compile(r"\b(can|will|able to|lets?|allows?)\b", re.I)
_CONSTRAINT = re.compile(r"\bbudget\b|\bdeadline\b|\bonly use\b|\bno more than\b|"
                         r"\blimited to\b|\bwithin \d|\bby (jan|feb|mar|apr|may|jun|jul|"
                         r"aug|sep|oct|nov|dec)|\bteam of\b|\bdevelopers?\b", re.I)

_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_HEADING = re.compile(r"^\s*(#{1,6})\s+(.*)$")


def _priority(sentence: str) -> str:
    if _COULD.search(sentence):
        return "could"
    if _MUST.search(sentence):
        return "must"
    if _SHOULD.search(sentence):
        return "should"
    return "must"


def _options(question: str) -> list:
    """'Slack or email?' -> ['Slack', 'email']. Best effort; options are editable."""
    q = question.rstrip(" ?.")
    m = re.search(r"([\w'\-]+)\s+or\s+((?:[\w'\-]+\s*){1,4})$", q)
    if not m:
        return []
    return [m.group(1).strip(), m.group(2).strip()]


def classify(sentence: str, section: str = None) -> str:
    """Return the collection name (or 'problem') a sentence belongs to."""
    if section:
        return section
    if _DECISION.search(sentence):
        return "decisions"
    if _NON_GOAL.search(sentence):
        return "non_goals"
    if _ASSUMPTION.search(sentence):
        return "assumptions"
    if _PROBLEM.search(sentence):
        return "problem"
    if _GOAL.search(sentence):
        return "goals"
    if _USERS.search(sentence):
        return "users"
    if _MUST.search(sentence) or _SHOULD.search(sentence) or _COULD.search(sentence) \
            or _CAPABILITY.search(sentence):
        return "requirements"
    if _CONSTRAINT.search(sentence):
        return "constraints"
    return "unclassified"


def _section_for(heading: str):
    for pat, coll in _SECTION_HINTS:
        if pat.search(heading):
            return coll
    return None


def intake(brief: str, title: str = None) -> dict:
    """Build a draft spec from brief text. Never invents content: every item is
    a sentence from the brief, with its line number."""
    spec = model.empty_spec(title or "Untitled spec")
    problem_parts = []
    section = None
    titled = bool(title)
    for lineno, raw in enumerate(brief.splitlines(), start=1):
        h = _HEADING.match(raw)
        if h:
            text = h.group(2).strip()
            if not titled:
                spec["title"] = text
                titled = True
            else:
                section = _section_for(text)
            continue
        line = _BULLET.sub("", raw).strip()
        if not line:
            continue
        if not titled:
            spec["title"] = line[:80]
            titled = True
        for sent in sentences(line):
            _place(spec, sent, lineno, section, problem_parts)
    spec["problem"] = " ".join(problem_parts)
    return spec


def _place(spec, sent, lineno, section, problem_parts):
    source = {"line": lineno, "text": sent}
    kind = classify(sent, section)
    if kind == "problem":
        problem_parts.append(sent)
        return
    if kind == "decisions":
        question = sent
        req_part = None
        # "We need to send a reminder, Slack or email?" -> requirement + decision.
        if "," in sent and sent.rstrip().endswith("?"):
            head, tail = sent.rsplit(",", 1)
            if _MUST.search(head) or _SHOULD.search(head) or _CAPABILITY.search(head):
                req_part, question = head.strip() + ".", tail.strip()
        d = model.add(spec, "decisions", {"question": question, "options": _options(question),
                                          "source": source})
        if req_part:
            model.add(spec, "requirements", {"text": req_part, "priority": _priority(req_part),
                                             "depends_on": [d["id"]], "source": source})
        return
    if kind == "requirements":
        model.add(spec, kind, {"text": sent, "priority": _priority(sent), "source": source})
        return
    model.add(spec, kind, {"text": sent, "source": source})
