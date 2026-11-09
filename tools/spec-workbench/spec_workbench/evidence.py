"""Evidence: tie acceptance criteria to real test results.

A spec that passes every check is still a plan. Evidence answers a different
question: for each criterion, did a test that was written against *this*
wording actually pass?

  fingerprint(ac)        a short hash of requirement, given, when, then
  scan_pins(paths)       '# spec-bench: AC3 fp=...' comments above test functions
  parse_junit(path)      test outcomes from a JUnit XML file (pytest --junitxml)
  evaluate(...)          one status per criterion, requirement roll-up, orphans
  save_run / runs        DIR/evidence/NNNN.json, never deleted
  current_view(...)      re-read an old run against the current spec (drift)

Everything is deterministic and local. Nothing here judges whether a test
checks what its criterion says; that stays a human call.
"""
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET

from . import store

EVIDENCE_DIR = "evidence"

VERIFIED, STALE, UNPINNED = "verified", "stale", "unpinned"
FAILING, UNWRITTEN, SKIPPED, UNTESTED = "failing", "unwritten", "skipped", "untested"
STATUSES = (VERIFIED, STALE, UNPINNED, FAILING, UNWRITTEN, SKIPPED, UNTESTED)

STATUS_HELP = {
    VERIFIED: "a test pinned to the current wording passed",
    STALE: "a test passed, but it was pinned to older wording of this criterion",
    UNPINNED: "a test passed, but it has no pin comment, so drift cannot be detected",
    FAILING: "a mapped test failed or errored",
    UNWRITTEN: "the mapped test is still the generated NotImplementedError skeleton",
    SKIPPED: "every mapped test was skipped",
    UNTESTED: "no test result names this criterion",
}

LIMITS = [
    "A passing test proves the test passed, not that it checks what the criterion "
    "says. Read the test before you trust the tick.",
    "Tests are matched to criteria by pin comments or an 'acN' token in the test "
    "name. A test that checks a criterion under another name is invisible here.",
    "Evidence is only as fresh as the results file you pass in.",
]

PIN = re.compile(r"#\s*spec-bench:\s*(AC\d+)\s+fp=([0-9a-f]{6,64})", re.I)
_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test\w*)\s*\(")
_NAME_AC = re.compile(r"(?:^|_)ac(\d+)(?=_|$)", re.I)
_SKELETON = "NotImplementedError"


class EvidenceError(Exception):
    pass


def fingerprint(ac: dict) -> str:
    """Stable 10-hex fingerprint of the parts of a criterion a test depends on."""
    parts = [ac.get("requirement") or ""] + [" ".join(str(ac.get(k, "")).split())
                                             for k in ("given", "when", "then")]
    raw = json.dumps(parts, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def pin_comment(ac: dict) -> str:
    return f"# spec-bench: {ac['id']} fp={fingerprint(ac)}"


# ---------- reading tests and results ----------

def _py_files(paths):
    for p in paths:
        p = pathlib.Path(p)
        if p.is_file() and p.suffix == ".py":
            yield p
        elif p.is_dir():
            yield from sorted(x for x in p.rglob("*.py") if "__pycache__" not in x.parts)
        elif not p.exists():
            raise EvidenceError(f"no such test path: {p}")


def scan_pins(paths) -> dict:
    """{(module_stem, function_name): {AC id: fingerprint}} from pin comments.

    Pins apply to the next `def test...` below them; several pins may stack.
    """
    pins = {}
    for f in _py_files(paths):
        pending = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            m = PIN.search(line)
            if m:
                pending[m.group(1).upper()] = m.group(2).lower()
                continue
            d = _DEF.match(line)
            if d:
                if pending:
                    pins.setdefault((f.stem, d.group(1)), {}).update(pending)
                pending = {}
            elif line.strip() and not line.lstrip().startswith(("#", "@")):
                pending = {}   # a pin must sit directly above its test (decorators allowed)
    return pins


def _first_line(text, limit=200):
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line[:limit]


def parse_junit(path) -> list:
    """[{classname, name, outcome, message}] with outcome passed|failed|error|skipped."""
    path = pathlib.Path(path)
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as e:
        raise EvidenceError(f"cannot read JUnit results {path}: {e}") from e
    out = []
    for tc in root.iter("testcase"):
        outcome, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            el = tc.find(tag)
            if el is not None:
                outcome = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                message = el.get("message") or el.text or ""
                if _SKELETON in (el.text or "") and _SKELETON not in message:
                    message = f"{_SKELETON}: {message}"
                break
        out.append({"classname": tc.get("classname", ""), "name": tc.get("name", ""),
                    "outcome": outcome, "message": _first_line(message)})
    if not out and root.tag not in ("testsuite", "testsuites"):
        raise EvidenceError(f"{path} is not a JUnit XML results file")
    return out


def _base_name(name):
    return name.split("[", 1)[0]


def _pins_for(test, pins):
    func = _base_name(test["name"])
    parts = set(test["classname"].split("."))
    for (stem, fname), acs in pins.items():
        if fname == func and stem in parts:
            return acs
    matches = [acs for (stem, fname), acs in pins.items() if fname == func]
    return matches[0] if len(matches) == 1 else {}


# ---------- evaluation ----------

def _test_label(test):
    mod = test["classname"].rsplit(".", 1)[-1] if test["classname"] else ""
    return f"{mod}::{test['name']}" if mod else test["name"]


def evaluate(spec: dict, tests: list, pins: dict) -> dict:
    """Map tests to criteria and give each criterion one status."""
    current = {ac["id"]: fingerprint(ac) for ac in spec["acceptance"]}
    mapped = {ac_id: [] for ac_id in current}
    orphans, unmapped = [], []
    for t in tests:
        tp = _pins_for(t, pins)
        ids = set(tp) or {f"AC{n}" for n in _NAME_AC.findall(_base_name(t["name"]))}
        if not ids:
            unmapped.append(_test_label(t))
            continue
        for ac_id in sorted(ids, key=_natural):
            entry = {"test": _test_label(t), "outcome": t["outcome"],
                     "message": t["message"], "pin": tp.get(ac_id)}
            if ac_id in mapped:
                mapped[ac_id].append(entry)
            else:
                orphans.append({"criterion": ac_id, **entry})
    criteria = {}
    for ac_id, entries in mapped.items():
        criteria[ac_id] = {"status": _status(entries, current[ac_id]),
                           "fingerprint": current[ac_id], "tests": entries}
    return {"criteria": criteria, "orphans": orphans, "unmapped": sorted(unmapped)}


def _status(entries, fp):
    if not entries:
        return UNTESTED
    outcomes = [e["outcome"] for e in entries]
    if any(o in ("failed", "error") for o in outcomes):
        bad = [e for e in entries if e["outcome"] in ("failed", "error")]
        return UNWRITTEN if all(_SKELETON in e["message"] for e in bad) else FAILING
    if any(o == "skipped" for o in outcomes):
        return SKIPPED
    if any(e["pin"] is not None and e["pin"] != fp for e in entries):
        return STALE
    if any(e["pin"] is None for e in entries):
        return UNPINNED
    return VERIFIED


def requirement_rollup(spec: dict, criteria: dict) -> dict:
    """{R id: status}. verified only if it has criteria and all are verified."""
    by_req = {}
    for ac in spec["acceptance"]:
        by_req.setdefault(ac.get("requirement"), []).append(criteria[ac["id"]]["status"])
    out = {}
    for r in spec["requirements"]:
        sts = by_req.get(r["id"], [])
        if not sts:
            out[r["id"]] = "no criterion"
        elif all(s == VERIFIED for s in sts):
            out[r["id"]] = VERIFIED
        else:
            worst = min(sts, key=lambda s: _RANK[s])
            out[r["id"]] = worst
    return out


# Worst first: a requirement shows its weakest criterion.
_RANK = {FAILING: 0, UNWRITTEN: 1, UNTESTED: 2, SKIPPED: 3, STALE: 4, UNPINNED: 5,
         VERIFIED: 6}


def counts(criteria: dict) -> dict:
    c = {s: 0 for s in STATUSES}
    for v in criteria.values():
        c[v["status"]] += 1
    return c


def _natural(ac_id):
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", ac_id)
    return (m.group(1), int(m.group(2))) if m else (ac_id, 0)


# ---------- persistence ----------

def _dir(ws):
    return pathlib.Path(ws) / EVIDENCE_DIR


def run_files(ws) -> list:
    d = _dir(ws)
    return sorted(d.glob("[0-9][0-9][0-9][0-9].json")) if d.is_dir() else []


def save_run(ws, rev: int, source: str, result: dict) -> int:
    files = run_files(ws)
    n = (int(files[-1].stem) if files else 0) + 1
    record = {"run": n, "at": store.now(), "revision": rev, "source": source, **result}
    store._atomic_write(_dir(ws) / f"{n:04d}.json", store._dump(record))
    return n


def runs(ws) -> list:
    """Readable runs, oldest first. Damaged files are skipped, never deleted."""
    out = []
    for p in run_files(ws):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(r.get("criteria"), dict) and isinstance(r.get("run"), int):
                out.append(r)
        except (ValueError, AttributeError):
            continue
    return out


def latest_run(ws):
    rs = runs(ws)
    return rs[-1] if rs else None


def current_view(spec: dict, run: dict) -> dict:
    """Re-read a saved run against the current spec.

    A criterion whose wording changed since the run becomes stale (if it was
    verified or unpinned there); one added since the run is untested.
    """
    criteria = {}
    for ac in spec["acceptance"]:
        fp = fingerprint(ac)
        old = run["criteria"].get(ac["id"])
        if old is None:
            criteria[ac["id"]] = {"status": UNTESTED, "fingerprint": fp, "tests": [],
                                  "note": f"added after evidence run {run['run']}"}
            continue
        entry = {**old, "fingerprint": fp}
        if old.get("fingerprint") != fp:
            entry["note"] = f"wording changed after evidence run {run['run']}"
            if old["status"] in (VERIFIED, UNPINNED):
                entry["status"] = STALE
        criteria[ac["id"]] = entry
    gone = [{"criterion": k, "test": t["test"], "outcome": t["outcome"],
             "message": t["message"], "pin": t.get("pin")}
            for k, v in run["criteria"].items() if not any(a["id"] == k for a in spec["acceptance"])
            for t in v.get("tests", [])]
    return {"criteria": criteria, "orphans": run.get("orphans", []) + gone,
            "unmapped": run.get("unmapped", [])}


# ---------- text output ----------

def to_text(spec: dict, view: dict, rev: int, run_label: str) -> str:
    crit = view["criteria"]
    c = counts(crit)
    total = len(crit)
    L = [f"Evidence for: {spec['title']} (revision {rev})", run_label,
         f"{c[VERIFIED]} of {total} criteria verified. " +
         ", ".join(f"{c[s]} {s}" for s in STATUSES if s != VERIFIED and c[s]), ""]
    acs = {ac["id"]: ac for ac in spec["acceptance"]}
    for ac_id in sorted(crit, key=_natural):
        v = crit[ac_id]
        L.append(f"  {ac_id:<5} {v['status'].upper():<9} req {acs[ac_id].get('requirement')}"
                 f"  fp={v['fingerprint']}")
        for t in v["tests"]:
            pin = (" pinned to current wording" if t.get("pin") == v["fingerprint"] else
                   f" pinned to fp={t['pin']}" if t.get("pin") else " no pin")
            msg = f": {t['message']}" if t["message"] and t["outcome"] != "passed" else ""
            L.append(f"        {t['outcome']:<7} {t['test']} ({pin.strip()}){msg}")
        if v.get("note"):
            L.append(f"        note: {v['note']}")
    L += ["", "Requirements"]
    for rid, st in requirement_rollup(spec, crit).items():
        L.append(f"  {rid:<5} {st}")
    if view["orphans"]:
        L += ["", "Orphan tests (name a criterion the spec no longer has)"]
        L += [f"  {o['criterion']}: {o['test']} ({o['outcome']})" for o in view["orphans"]]
    if view["unmapped"]:
        L += ["", f"{len(view['unmapped'])} test(s) name no criterion and were ignored."]
    L += ["", "Statuses:"] + [f"  {s:<10} {STATUS_HELP[s]}" for s in STATUSES]
    L += ["", "What evidence cannot prove:"] + [f"  - {x}" for x in LIMITS]
    return "\n".join(L) + "\n"
