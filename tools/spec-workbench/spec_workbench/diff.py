"""Compare two revisions: item changes plus which findings were resolved or
introduced."""
from . import checks, model

_IGNORED_FIELDS = {"source"}


def diff(old: dict, new: dict) -> dict:
    out = {"fields": [], "added": [], "removed": [], "changed": []}
    for key in ("title", "problem"):
        if old.get(key) != new.get(key):
            out["fields"].append({"field": key, "old": old.get(key), "new": new.get(key)})
    for coll in model.COLLECTIONS:
        a = {i["id"]: i for i in old.get(coll, [])}
        b = {i["id"]: i for i in new.get(coll, [])}
        for item_id in b.keys() - a.keys():
            out["added"].append(b[item_id])
        for item_id in a.keys() - b.keys():
            out["removed"].append(a[item_id])
        for item_id in a.keys() & b.keys():
            changes = {}
            for k in (a[item_id].keys() | b[item_id].keys()) - _IGNORED_FIELDS:
                if a[item_id].get(k) != b[item_id].get(k):
                    changes[k] = {"old": a[item_id].get(k), "new": b[item_id].get(k)}
            if changes:
                out["changed"].append({"id": item_id, "changes": changes})
    for k in ("added", "removed"):
        out[k].sort(key=lambda i: _sort_key(i["id"]))
    out["changed"].sort(key=lambda c: _sort_key(c["id"]))

    fa = {f["key"]: f for f in checks.run(old) if not f["waived"]}
    fb = {f["key"]: f for f in checks.run(new) if not f["waived"]}
    order = lambda f: (f["rule"], [_sort_key(t) for t in f["targets"]])  # noqa: E731
    out["resolved"] = sorted((fa[k] for k in fa.keys() - fb.keys()), key=order)
    out["introduced"] = sorted((fb[k] for k in fb.keys() - fa.keys()), key=order)
    return out


def _sort_key(item_id):
    prefix = item_id.rstrip("0123456789")
    num = item_id[len(prefix):]
    return (prefix, int(num) if num else 0)


def _short(item):
    return item.get("text") or item.get("question") or (
        f"{item.get('requirement')}: given {item.get('given')}, when {item.get('when')}, "
        f"then {item.get('then')}")


def to_text(d: dict, a: int, b: int) -> str:
    lines = [f"Changes from revision {a} to revision {b}"]
    for f in d["fields"]:
        lines.append(f"  ~ {f['field']}: {f['old']!r} -> {f['new']!r}")
    for i in d["added"]:
        lines.append(f"  + {i['id']}: {_short(i)}")
    for i in d["removed"]:
        lines.append(f"  - {i['id']}: {_short(i)}")
    for c in d["changed"]:
        for k, v in sorted(c["changes"].items()):
            lines.append(f"  ~ {c['id']}.{k}: {v['old']!r} -> {v['new']!r}")
    if len(lines) == 1:
        lines.append("  (no item changes)")
    lines.append(f"Findings resolved: {len(d['resolved'])}")
    for f in d["resolved"]:
        lines.append(f"  [fixed] {f['key']} {f['message']}")
    lines.append(f"Findings introduced: {len(d['introduced'])}")
    for f in d["introduced"]:
        lines.append(f"  [new]   {f['key']} {f['message']}")
    return "\n".join(lines)
