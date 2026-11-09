"""Rule-based checks. Each rule is deterministic, documented, and says whether
it is a hard structural fact or a heuristic that needs human judgment.

A finding is a dict:
  {key, rule, name, severity, targets, message, fix, judgment, waived, waiver}
`key` is stable across runs ("WB006:N1~R9") so findings can be waived and
diffed between revisions.
"""
import re

from spec_grader.ambiguity import find_ambiguities

from . import model
from .text import content_tokens, is_negative, jaccard

BLOCKING, WARNING, INFO = "blocking", "warning", "info"
_SEVERITY_ORDER = {BLOCKING: 0, WARNING: 1, INFO: 2}

RULES = {
    "WB001": "ambiguous-wording",
    "WB002": "missing-criterion",
    "WB003": "incomplete-criterion",
    "WB004": "unobservable-outcome",
    "WB005": "open-decision",
    "WB006": "nongoal-conflict",
    "WB007": "bound-conflict",
    "WB008": "polarity-conflict",
    "WB009": "duplicate",
    "WB010": "compound",
    "WB011": "missing-section",
    "WB012": "unvalidated-assumption",
    "WB013": "dangling-reference",
    "WB014": "unclassified",
}

LIMITS = [
    "Whether this is the right product to build, or whether users want it.",
    "Contradictions that need domain knowledge (for example 'votes are anonymous' "
    "versus 'the organizer sees who voted'). Only word overlap, negation and numeric "
    "bounds are compared.",
    "Whether an acceptance criterion is sufficient, only whether it is complete and "
    "names an observable outcome.",
    "Ambiguity outside the curated Spec Grader lexicon.",
    "Feasibility, effort, security or legal risk.",
]

GRADE_DISCLAIMER = ("A numeric grade is never proof of success: it measures wording, "
                    "not whether the spec describes the right thing or whether the "
                    "built software works.")

_OBSERVABLE = re.compile(
    r"\d|\"[^\"]+\"|'[^']+'|\b(shows?|displays?|returns?|saves?|stores?|sends?|exits?|"
    r"appears?|lists?|rejects?|contains?|equals?|prints?|receives?|records?|closes?|"
    r"opens?|creates?|deletes?|redirects?|highlights?|disables?|enables?|counts?|"
    r"is (?:shown|hidden|marked|set|blocked|visible)|are (?:shown|hidden|listed|visible))\b",
    re.I)
_MODAL = re.compile(r"\b(must|shall|should|needs? to|has to|have to)\b", re.I)

_UPPER = (r"within|under|less than|at most|no more than|up to|maximum of|max|below|"
          r"fewer than|in")
_LOWER = r"at least|more than|over|minimum of|no less than|above|longer than"
_UNITS = {
    "ms": ("time", 0.001), "millisecond": ("time", 0.001), "milliseconds": ("time", 0.001),
    "s": ("time", 1), "sec": ("time", 1), "secs": ("time", 1), "second": ("time", 1),
    "seconds": ("time", 1), "min": ("time", 60), "mins": ("time", 60),
    "minute": ("time", 60), "minutes": ("time", 60), "h": ("time", 3600),
    "hr": ("time", 3600), "hrs": ("time", 3600), "hour": ("time", 3600),
    "hours": ("time", 3600), "day": ("time", 86400), "days": ("time", 86400),
    "kb": ("size", 0.001), "mb": ("size", 1), "gb": ("size", 1000),
    "%": ("percent", 1), "percent": ("percent", 1),
}
_BOUND = re.compile(
    rf"\b(?P<cmp>{_LOWER}|{_UPPER})\s+(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>"
    + "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
    + r")(?![a-z])", re.I)


def _finding(rule, severity, targets, message, fix, judgment=False):
    targets = list(targets)
    return {"key": f"{rule}:{'~'.join(targets)}" if targets else rule,
            "rule": rule, "name": RULES[rule], "severity": severity,
            "targets": targets, "message": message, "fix": fix,
            "judgment": judgment, "waived": False, "waiver": None}


def _criteria_by_req(spec):
    out = {}
    for ac in spec["acceptance"]:
        out.setdefault(ac.get("requirement"), []).append(ac)
    return out


def _ambiguity(spec):
    out = []
    for r in spec["requirements"]:
        terms = sorted({a["term"] for a in find_ambiguities(r["text"])})
        if terms:
            sev = BLOCKING if r["priority"] == "must" else WARNING
            out.append(_finding("WB001", sev, [r["id"]],
                                f"{r['id']} uses ambiguous wording: {', '.join(terms)}.",
                                "Replace each term with a number, a list, or an observable "
                                "behavior."))
    for ac in spec["acceptance"]:
        text = " ".join(ac.get(k, "") for k in ("given", "when", "then"))
        terms = sorted({a["term"] for a in find_ambiguities(text)})
        if terms:
            out.append(_finding("WB001", BLOCKING, [ac["id"]],
                                f"{ac['id']} uses ambiguous wording: {', '.join(terms)}.",
                                "A criterion must be checkable. Name the exact value."))
    return out


def _criteria(spec):
    out = []
    by_req = _criteria_by_req(spec)
    for r in spec["requirements"]:
        if r["id"] not in by_req and r["priority"] != "could":
            sev = BLOCKING if r["priority"] == "must" else WARNING
            out.append(_finding("WB002", sev, [r["id"]],
                                f"{r['id']} ({r['priority']}) has no acceptance criterion.",
                                f"spec-bench add DIR criterion --req {r['id']} --given ... "
                                "--when ... --then ..."))
    for ac in spec["acceptance"]:
        missing = [k for k in ("given", "when", "then") if not str(ac.get(k, "")).strip()]
        if missing:
            out.append(_finding("WB003", BLOCKING, [ac["id"]],
                                f"{ac['id']} is missing: {', '.join(missing)}.",
                                "Fill in given (starting state), when (action) and then "
                                "(observable result)."))
        elif not _OBSERVABLE.search(ac["then"]):
            out.append(_finding("WB004", WARNING, [ac["id"]],
                                f"{ac['id']} 'then' names no number, quoted text or observable "
                                "verb, so a tester may not know what to look for.",
                                "State what the user or a test sees: a value, a message, a "
                                "saved record.", judgment=True))
    return out


def _decisions(spec):
    out = []
    dependents = {}
    for r in spec["requirements"]:
        for d in r.get("depends_on", []):
            dependents.setdefault(d, []).append(r["id"])
    for d in spec["decisions"]:
        if d["status"] != "decided":
            deps = dependents.get(d["id"], [])
            opts = f" Options: {', '.join(d['options'])}." if d.get("options") else ""
            if deps:
                out.append(_finding("WB005", BLOCKING, [d["id"]] + deps,
                                    f"{d['id']} is open and {', '.join(deps)} depend(s) on it: "
                                    f"{d['question']}{opts}",
                                    f"spec-bench decide DIR {d['id']} --choice ... --rationale ..."))
            else:
                out.append(_finding("WB005", WARNING, [d["id"]],
                                    f"{d['id']} is open: {d['question']}{opts}",
                                    f"Decide it, or link the requirements it affects with "
                                    f"--depends {d['id']}."))
    return out


_NONGOAL_STOP = {"scope", "v1", "v2", "version", "integration", "support", "feature",
                 "release", "phase", "mvp", "first"}


def _nongoal_conflicts(spec):
    out = []
    for n in spec["non_goals"]:
        core = content_tokens(n["text"], extra_stop=_NONGOAL_STOP | {"out", "in"})
        if not core:
            continue
        for r in spec["requirements"]:
            if core <= content_tokens(r["text"]):
                sev = BLOCKING if len(core) >= 2 else WARNING
                out.append(_finding(
                    "WB006", sev, [n["id"], r["id"]],
                    f"{r['id']} asks for what non-goal {n['id']} rules out "
                    f"(shared words: {', '.join(sorted(core))}). {n['id']}: \"{n['text']}\" "
                    f"{r['id']}: \"{r['text']}\"",
                    "Remove or rescope one of them, or record a decision explaining both.",
                    judgment=len(core) < 2))
    return out


def bounds(text: str) -> list:
    """Extract numeric limits: [{kind: upper|lower, value, dim, subject}]."""
    out = []
    for m in _BOUND.finditer(text):
        cmp_ = m.group("cmp").lower()
        unit = m.group("unit").lower()
        dim, factor = _UNITS[unit]
        if cmp_ == "in" and dim != "time":
            continue
        kind = "lower" if re.fullmatch(_LOWER, cmp_) else "upper"
        subject = content_tokens(text[: m.start()])
        out.append({"kind": kind, "value": float(m.group("num")) * factor, "dim": dim,
                    "subject": subject, "phrase": m.group(0)})
    return out


def _bound_conflicts(spec):
    items = [(i, b) for coll in ("requirements", "constraints", "goals")
             for i in spec[coll] for b in bounds(i["text"])]
    out = []
    seen = set()
    for x in range(len(items)):
        for y in range(x + 1, len(items)):
            (ia, a), (ib, b) = items[x], items[y]
            if ia["id"] == ib["id"] or a["dim"] != b["dim"] or not (a["subject"] & b["subject"]):
                continue
            pair = (ia["id"], ib["id"])
            if pair in seen:
                continue
            shared = ", ".join(sorted(a["subject"] & b["subject"]))
            if a["kind"] != b["kind"]:
                lo, hi = (a, b) if a["kind"] == "lower" else (b, a)
                if lo["value"] > hi["value"]:
                    seen.add(pair)
                    out.append(_finding(
                        "WB007", BLOCKING, list(pair),
                        f"{ia['id']} \"{a['phrase']}\" and {ib['id']} \"{b['phrase']}\" "
                        f"cannot both hold for: {shared}.",
                        "Pick one limit, or make clear they apply to different things."))
            elif a["value"] != b["value"]:
                seen.add(pair)
                out.append(_finding(
                    "WB007", WARNING, list(pair),
                    f"{ia['id']} \"{a['phrase']}\" and {ib['id']} \"{b['phrase']}\" set "
                    f"different limits on: {shared}.",
                    "Use one number, or name the two different things being limited.",
                    judgment=True))
    return out


def _polarity_conflicts(spec):
    out = []
    reqs = spec["requirements"]
    for x in range(len(reqs)):
        for y in range(x + 1, len(reqs)):
            a, b = reqs[x], reqs[y]
            if is_negative(a["text"]) == is_negative(b["text"]):
                continue
            sim = jaccard(content_tokens(a["text"]), content_tokens(b["text"]))
            if sim >= 0.6:
                out.append(_finding(
                    "WB008", BLOCKING, [a["id"], b["id"]],
                    f"{a['id']} and {b['id']} say opposite things about the same behavior "
                    f"({round(sim * 100)} percent word overlap). {a['id']}: \"{a['text']}\" "
                    f"{b['id']}: \"{b['text']}\"",
                    "Keep one, or state the condition that separates them."))
    return out


def _duplicates(spec):
    out = []
    reqs = spec["requirements"]
    for x in range(len(reqs)):
        for y in range(x + 1, len(reqs)):
            a, b = reqs[x], reqs[y]
            if is_negative(a["text"]) != is_negative(b["text"]):
                continue
            sim = jaccard(content_tokens(a["text"]), content_tokens(b["text"]))
            if sim >= 0.8:
                out.append(_finding("WB009", WARNING, [a["id"], b["id"]],
                                    f"{a['id']} and {b['id']} look like duplicates "
                                    f"({round(sim * 100)} percent word overlap).",
                                    "Merge them so each behavior is specified once."))
    return out


def _compound(spec):
    out = []
    for r in spec["requirements"]:
        if len(_MODAL.findall(r["text"])) >= 2:
            out.append(_finding("WB010", WARNING, [r["id"]],
                                f"{r['id']} bundles more than one requirement.",
                                "Split it so each part can pass or fail on its own.",
                                judgment=True))
    return out


def _sections(spec):
    out = []
    if not spec["requirements"]:
        out.append(_finding("WB011", BLOCKING, [], "The spec has no requirements.",
                            "Add at least one requirement."))
    if not spec["problem"].strip():
        out.append(_finding("WB011", WARNING, ["problem"], "The problem statement is empty.",
                            "spec-bench edit DIR problem --text ..."))
    for coll in ("users", "goals", "non_goals"):
        if not spec[coll]:
            label = model.COLLECTIONS[coll][1].lower()
            out.append(_finding("WB011", WARNING, [coll], f"No {label} are listed.",
                                f"Add {label}: an implementer uses them to settle edge cases."))
    return out


def _assumptions(spec):
    return [_finding("WB012", WARNING, [a["id"]],
                     f"{a['id']} has no validation plan: \"{a['text']}\"",
                     f"spec-bench edit DIR {a['id']} --validation \"how and when you will "
                     "check it\"")
            for a in spec["assumptions"] if not (a.get("validation") or "").strip()]


def _dangling(spec):
    out = []
    req_ids = {r["id"] for r in spec["requirements"]}
    dec_ids = {d["id"] for d in spec["decisions"]}
    for ac in spec["acceptance"]:
        if ac.get("requirement") not in req_ids:
            out.append(_finding("WB013", BLOCKING, [ac["id"]],
                                f"{ac['id']} points at requirement "
                                f"{ac.get('requirement') or '(none)'}, which does not exist.",
                                f"spec-bench edit DIR {ac['id']} --req R..."))
    for r in spec["requirements"]:
        for d in r.get("depends_on", []):
            if d not in dec_ids:
                why = ("which is not a decision; depends_on lists the decisions a "
                       "requirement waits on" if model.prefix_of(d) != "D"
                       else "which does not exist")
                out.append(_finding("WB013", BLOCKING, [r["id"], d],
                                    f"{r['id']} depends on {d}, {why}.",
                                    f"Remove {d} from {r['id']}'s depends_on."))
    return out


def _unclassified(spec):
    return [_finding("WB014", INFO, [x["id"]],
                     f"Intake could not classify line {x.get('source', {}).get('line', '?')}: "
                     f"\"{x['text']}\"",
                     f"Turn it into a real item (requirement, non-goal, ...) and remove "
                     f"{x['id']}, or remove it if it adds nothing.")
            for x in spec["unclassified"]]


_RULE_FNS = [_ambiguity, _criteria, _decisions, _nongoal_conflicts, _bound_conflicts,
             _polarity_conflicts, _duplicates, _compound, _sections, _assumptions,
             _dangling, _unclassified]


def _natural(item_id):
    m = re.fullmatch(r"([A-Za-z_]+)(\d*)", item_id)
    if not m:
        return (item_id, 0)
    return (m.group(1), int(m.group(2) or 0))


def run(spec: dict) -> list:
    findings = []
    for fn in _RULE_FNS:
        findings.extend(fn(spec))
    waivers = {w["key"]: w["reason"] for w in spec.get("waivers", [])}
    for f in findings:
        if f["key"] in waivers:
            f["waived"], f["waiver"] = True, waivers[f["key"]]
    findings.sort(key=lambda f: (f["waived"], _SEVERITY_ORDER[f["severity"]], f["rule"],
                                 [_natural(t) for t in f["targets"]]))
    return findings


def summary(findings: list) -> dict:
    live = [f for f in findings if not f["waived"]]
    counts = {s: sum(1 for f in live if f["severity"] == s) for s in (BLOCKING, WARNING, INFO)}
    counts["waived"] = len(findings) - len(live)
    counts["ready"] = counts[BLOCKING] == 0
    return counts


def stale_waivers(spec: dict, findings: list) -> list:
    """Waivers whose finding no longer fires (worth cleaning up)."""
    keys = {f["key"] for f in findings}
    return [w for w in spec.get("waivers", []) if w["key"] not in keys]

