"""spec-bench: turn a rough brief into a buildable, testable spec.

  spec-bench intake DIR brief.md          create a workspace from a messy brief
  spec-bench new DIR --template cli-tool  start from a template instead
  spec-bench check DIR                    contradictions, gaps, open decisions
  spec-bench add / edit / remove / decide / waive / apply   revise (each is a revision)
  spec-bench history DIR | diff DIR 1 3 | revert DIR 2
  spec-bench export DIR --format md|json|html|checklist|pytest [--out FILE]

Fully local: no network, no account, no model calls. Exit codes: 0 ok,
1 a --fail-on gate tripped, 2 usage or workspace error.
"""
import argparse
import json
import pathlib
import sys

from . import checks, diff as diffmod, export, intake as intakemod, model, store, templates


def _err(msg):
    print(msg, file=sys.stderr)


def _load(ws):
    return store.load(ws, warn=_err)


def _save(ws, spec, message):
    rev = store.commit(ws, spec, message)
    print(f"Saved revision {rev}: {message}")
    return rev


# ---------- commands ----------

def cmd_intake(a):
    brief = pathlib.Path(a.brief)
    if not brief.exists():
        raise store.WorkspaceError(f"no such brief: {brief}")
    spec = intakemod.intake(brief.read_text(encoding="utf-8"), title=a.title)
    store.create(a.dir, spec, a.message or f"intake from {brief.name}")
    counts = ", ".join(f"{len(spec[c])} {c.replace('_', '-')}" for c in model.COLLECTIONS
                       if spec[c])
    print(f"Created {a.dir} (revision 1) from {brief.name}: {counts}.")
    print(f"Next: spec-bench check {a.dir}")
    return 0


def cmd_new(a):
    spec = templates.build(a.template, a.title or "Untitled spec")
    store.create(a.dir, spec, a.message or f"new from template {a.template}")
    print(f"Created {a.dir} (revision 1) from template {a.template}.")
    return 0


def cmd_templates(a):
    for name, t in templates.TEMPLATES.items():
        print(f"{name:13} {t['description']}")
    return 0


def _fmt_finding(f):
    tag = " (judgment call)" if f["judgment"] else ""
    out = [f"  {f['rule']} {f['name']}{tag}  [{', '.join(f['targets']) or 'spec'}]",
           f"    {f['message']}", f"    fix: {f['fix']}"]
    if f["waived"]:
        out.append(f"    waived: {f['waiver']}")
    out.append(f"    key: {f['key']}")
    return out


def check_text(spec, rev=None):
    findings = checks.run(spec)
    s = checks.summary(findings)
    lint = export.lint(spec)
    head = f"Spec: {spec['title']}" + (f" (revision {rev})" if rev else "")
    state = "Ready to build" if s["ready"] else "Not ready to build"
    L = [head, f"{state}: {s['blocking']} blocking, {s['warning']} warning, {s['info']} info, "
               f"{s['waived']} waived", ""]
    for sev in (checks.BLOCKING, checks.WARNING, checks.INFO):
        group = [f for f in findings if f["severity"] == sev and not f["waived"]]
        if group:
            L.append(sev.upper())
            for f in group:
                L += _fmt_finding(f)
            L.append("")
    waived = [f for f in findings if f["waived"]]
    if waived:
        L.append("WAIVED")
        for f in waived:
            L += _fmt_finding(f)
        L.append("")
    for w in checks.stale_waivers(spec, findings):
        L.append(f"note: waiver {w['key']} no longer matches a finding; it can be removed.")
    L += [f"Wording lint (Spec Grader): {lint['grade']} ({lint['score']}/100)",
          checks.GRADE_DISCLAIMER, "", "What these checks cannot judge:"]
    L += [f"  - {x}" for x in checks.LIMITS]
    return "\n".join(L), s


def cmd_check(a):
    spec = _load(a.dir)
    rev = store.latest_rev(a.dir)
    if a.json:
        findings = checks.run(spec)
        lint = export.lint(spec)
        print(json.dumps({"revision": rev, "summary": checks.summary(findings),
                          "findings": findings,
                          "lint": {"score": lint["score"], "grade": lint["grade"],
                                   "disclaimer": checks.GRADE_DISCLAIMER},
                          "limits": checks.LIMITS}, indent=2))
        s = checks.summary(findings)
    else:
        text, s = check_text(spec, rev)
        print(text)
    if a.fail_on == "blocking" and s["blocking"]:
        return 1
    if a.fail_on == "warning" and (s["blocking"] or s["warning"]):
        return 1
    return 0


def cmd_show(a):
    print(export.to_markdown(_load(a.dir), store.latest_rev(a.dir)), end="")
    return 0


def _fields_from_args(a, kind):
    f = {}
    if getattr(a, "text", None) is not None:
        f["question" if kind == "decisions" else "text"] = a.text
    if getattr(a, "question", None) is not None:
        f["question"] = a.question
    if getattr(a, "priority", None) is not None:
        f["priority"] = a.priority
    if getattr(a, "depends", None) is not None:
        f["depends_on"] = [d for d in a.depends if d]
    if getattr(a, "option", None) is not None:
        f["options"] = a.option
    if getattr(a, "validation", None) is not None:
        f["validation"] = a.validation
    for k in ("req", "given", "when", "then", "status"):
        v = getattr(a, k, None)
        if v is not None:
            f["requirement" if k == "req" else k] = v
    return f


def cmd_add(a):
    spec = _load(a.dir)
    coll = model.KINDS[a.kind]
    fields = _fields_from_args(a, coll)
    if a.value is not None:
        fields["question" if coll == "decisions" else "text"] = a.value
    item = model.add(spec, coll, fields)
    _save(a.dir, spec, a.message or f"add {item['id']}")
    return 0


def _edit(spec, target, fields):
    if target in ("problem", "title"):
        if "text" not in fields:
            raise model.SpecError(f"edit {target} needs --text")
        spec[target] = fields["text"]
        return
    if model.collection_of(target) == "decisions" and "text" in fields:
        fields["question"] = fields.pop("text")
    model.edit(spec, target, fields)


def cmd_edit(a):
    spec = _load(a.dir)
    coll = None if a.id in ("problem", "title") else model.collection_of(a.id)
    fields = _fields_from_args(a, coll)
    if not fields:
        raise model.SpecError("nothing to change; pass at least one field flag")
    _edit(spec, a.id, fields)
    _save(a.dir, spec, a.message or f"edit {a.id}")
    return 0


def cmd_remove(a):
    spec = _load(a.dir)
    model.remove(spec, a.id)
    _save(a.dir, spec, a.message or f"remove {a.id}")
    return 0


def cmd_decide(a):
    spec = _load(a.dir)
    model.decide(spec, a.id, a.choice, a.rationale or "")
    _save(a.dir, spec, a.message or f"decide {a.id}")
    return 0


def cmd_waive(a):
    spec = _load(a.dir)
    model.waive(spec, a.key, a.reason)
    _save(a.dir, spec, a.message or f"waive {a.key}")
    return 0


def _subst(value, names):
    if isinstance(value, str):
        for k, v in names.items():
            value = value.replace(k, v)
        return value
    if isinstance(value, list):
        return [_subst(v, names) for v in value]
    if isinstance(value, dict):
        return {k: _subst(v, names) for k, v in value.items()}
    return value


def apply_ops(spec, ops):
    """Apply a batch of edits to a copy of `spec`. All or nothing."""
    work = model.clone(spec)
    names = {}
    if not isinstance(ops, list):
        raise model.SpecError("a changes file must be a JSON list of operations")
    for n, op in enumerate(ops, start=1):
        try:
            op = _subst(op, names)
            kind = op.get("op")
            if kind == "add":
                item = model.add(work, model.KINDS[op["kind"]], dict(op.get("fields", {})))
                if op.get("as"):
                    names[op["as"]] = item["id"]
            elif kind == "edit":
                _edit(work, op["id"], dict(op.get("fields", {})))
            elif kind == "remove":
                model.remove(work, op["id"])
            elif kind == "decide":
                model.decide(work, op["id"], op.get("choice", ""), op.get("rationale", ""))
            elif kind == "waive":
                model.waive(work, op["key"], op.get("reason", ""))
            else:
                raise model.SpecError(f"unknown op {kind!r}")
        except KeyError as e:
            raise model.SpecError(f"operation {n}: missing {e}") from e
        except model.SpecError as e:
            raise model.SpecError(f"operation {n}: {e}") from e
    model.validate(work)
    return work


def cmd_apply(a):
    spec = _load(a.dir)
    path = pathlib.Path(a.changes)
    try:
        ops = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise model.SpecError(f"cannot read {path}: {e}") from e
    work = apply_ops(spec, ops)
    _save(a.dir, work, a.message or f"apply {path.name} ({len(ops)} changes)")
    return 0


def cmd_history(a):
    for h in store.history(a.dir):
        print(f"{h['rev']:>4}  {h['at']}  {h['message']}")
    return 0


def cmd_diff(a):
    old = store.read_revision(a.dir, a.a)["spec"]
    new = store.read_revision(a.dir, a.b)["spec"]
    print(diffmod.to_text(diffmod.diff(old, new), a.a, a.b))
    return 0


def cmd_revert(a):
    _load(a.dir)
    entry = store.read_revision(a.dir, a.rev)
    _save(a.dir, entry["spec"], a.message or f"revert to revision {a.rev}")
    return 0


def cmd_export(a):
    spec = _load(a.dir)
    rev = store.latest_rev(a.dir)
    if a.format == "json":
        out = export.to_json(spec)
    elif a.format == "html":
        out = export.to_html(spec, rev, store.history(a.dir))
    else:
        out = export.FORMATS[a.format](spec, rev)
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out, encoding="utf-8")
        print(f"Wrote {p}")
    else:
        print(out, end="")
    return 0


# ---------- parser ----------

def _field_flags(p, kind_flag=True):
    p.add_argument("--text")
    p.add_argument("--question")
    p.add_argument("--priority", choices=model.PRIORITIES)
    p.add_argument("--depends", action="append", metavar="DECISION_ID")
    p.add_argument("--option", action="append")
    p.add_argument("--validation")
    p.add_argument("--req", metavar="REQUIREMENT_ID")
    p.add_argument("--given")
    p.add_argument("--when")
    p.add_argument("--then")
    p.add_argument("--status", choices=("draft", "agreed"))


def build_parser():
    ap = argparse.ArgumentParser(prog="spec-bench", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def sp(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        if name != "templates":
            p.add_argument("dir", help="workspace directory")
        if name in ("intake", "new", "add", "edit", "remove", "decide", "waive", "apply",
                    "revert"):
            p.add_argument("-m", "--message", help="revision message")
        return p

    p = sp("intake", cmd_intake, "create a workspace from a brief")
    p.add_argument("brief")
    p.add_argument("--title")
    p = sp("new", cmd_new, "create a workspace from a template")
    p.add_argument("--template", default="blank", choices=templates.names())
    p.add_argument("--title")
    sp("templates", cmd_templates, "list templates")
    p = sp("check", cmd_check, "run every rule")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-on", choices=("blocking", "warning"))
    sp("show", cmd_show, "print the spec as markdown")
    p = sp("add", cmd_add, "add an item")
    p.add_argument("kind", choices=list(model.KINDS))
    p.add_argument("value", nargs="?", help="text (or question, for a decision)")
    _field_flags(p)
    p = sp("edit", cmd_edit, "change fields on an item (or 'problem' / 'title')")
    p.add_argument("id")
    _field_flags(p)
    p = sp("remove", cmd_remove, "remove an item (its ID is never reused)")
    p.add_argument("id")
    p = sp("decide", cmd_decide, "record a decision")
    p.add_argument("id")
    p.add_argument("--choice", required=True)
    p.add_argument("--rationale")
    p = sp("waive", cmd_waive, "accept a finding with a recorded reason")
    p.add_argument("key")
    p.add_argument("--reason", required=True)
    p = sp("apply", cmd_apply, "apply a JSON list of changes as one revision")
    p.add_argument("changes")
    sp("history", cmd_history, "list revisions")
    p = sp("diff", cmd_diff, "compare two revisions")
    p.add_argument("a", type=int)
    p.add_argument("b", type=int)
    p = sp("revert", cmd_revert, "restore an old revision as a new revision")
    p.add_argument("rev", type=int)
    p = sp("export", cmd_export, "export the spec")
    p.add_argument("--format", required=True, choices=("md", "json", "html", "checklist",
                                                        "pytest"))
    p.add_argument("--out")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (model.SpecError, store.WorkspaceError) as e:
        _err(f"error: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
