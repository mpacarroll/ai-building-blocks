"""The spec data model: a plain JSON document with stable, never-reused IDs.

Kept as dicts (not classes) so the on-disk format is the in-memory format and
anyone can read or hand-edit `spec.json`.
"""
import copy

SCHEMA_VERSION = 1

# collection name -> (ID prefix, label used in reports)
COLLECTIONS = {
    "users": ("U", "Users"),
    "goals": ("G", "Goals"),
    "non_goals": ("N", "Non-goals"),
    "requirements": ("R", "Requirements"),
    "decisions": ("D", "Decisions"),
    "assumptions": ("A", "Assumptions"),
    "constraints": ("C", "Constraints"),
    "acceptance": ("AC", "Acceptance criteria"),
    "unclassified": ("X", "Unclassified intake"),
}

# CLI kind names -> collection
KINDS = {
    "user": "users", "goal": "goals", "non-goal": "non_goals",
    "requirement": "requirements", "decision": "decisions",
    "assumption": "assumptions", "constraint": "constraints",
    "criterion": "acceptance", "unclassified": "unclassified",
}

PRIORITIES = ("must", "should", "could")


class SpecError(ValueError):
    """Raised for invalid specs or invalid edits. The message is user facing."""


def empty_spec(title: str = "Untitled spec") -> dict:
    spec = {"schema": SCHEMA_VERSION, "title": title, "problem": "",
            "counters": {}, "waivers": []}
    for name in COLLECTIONS:
        spec[name] = []
    return spec


def prefix_of(item_id: str) -> str:
    return item_id.rstrip("0123456789")


def collection_of(item_id: str) -> str:
    p = prefix_of(item_id)
    for name, (prefix, _) in COLLECTIONS.items():
        if prefix == p:
            return name
    raise SpecError(f"unknown ID prefix in {item_id!r}")


def next_id(spec: dict, collection: str) -> str:
    prefix = COLLECTIONS[collection][0]
    used = [int(i["id"][len(prefix):]) for i in spec[collection]]
    n = max([spec["counters"].get(prefix, 0)] + used) + 1
    spec["counters"][prefix] = n
    return f"{prefix}{n}"


def find(spec: dict, item_id: str):
    for item in spec.get(collection_of(item_id), []):
        if item["id"] == item_id:
            return item
    return None


def _defaults(collection: str, fields: dict) -> dict:
    item = dict(fields)
    if collection == "requirements":
        item.setdefault("priority", "must")
        item.setdefault("depends_on", [])
        if item["priority"] not in PRIORITIES:
            raise SpecError(f"priority must be one of {', '.join(PRIORITIES)}")
    elif collection == "decisions":
        item.setdefault("options", [])
        item.setdefault("status", "open")
        item.setdefault("choice", None)
        item.setdefault("rationale", None)
    elif collection == "assumptions":
        item.setdefault("validation", None)
    elif collection == "acceptance":
        for k in ("requirement", "given", "when", "then"):
            item.setdefault(k, "")
        item.setdefault("status", "draft")
    if collection == "decisions":
        if not item.get("question"):
            raise SpecError("a decision needs a question")
    elif collection != "acceptance" and not item.get("text"):
        raise SpecError("an item needs text")
    return item


def add(spec: dict, collection: str, fields: dict) -> dict:
    if collection not in COLLECTIONS:
        raise SpecError(f"unknown collection {collection!r}")
    item = _defaults(collection, fields)
    item["id"] = next_id(spec, collection)
    spec[collection].append({"id": item.pop("id"), **item})
    return spec[collection][-1]


def edit(spec: dict, item_id: str, fields: dict) -> dict:
    item = find(spec, item_id)
    if item is None:
        raise SpecError(f"no item {item_id}")
    for k, v in fields.items():
        if k == "id":
            raise SpecError("IDs cannot be changed")
        if k == "priority" and v not in PRIORITIES:
            raise SpecError(f"priority must be one of {', '.join(PRIORITIES)}")
        item[k] = v
    return item


def remove(spec: dict, item_id: str) -> dict:
    coll = collection_of(item_id)
    item = find(spec, item_id)
    if item is None:
        raise SpecError(f"no item {item_id}")
    # Keep the counter so the removed ID is never reused.
    prefix = COLLECTIONS[coll][0]
    n = int(item_id[len(prefix):])
    spec["counters"][prefix] = max(spec["counters"].get(prefix, 0), n)
    spec[coll] = [i for i in spec[coll] if i["id"] != item_id]
    return item


def decide(spec: dict, decision_id: str, choice: str, rationale: str = "") -> dict:
    d = find(spec, decision_id)
    if d is None or collection_of(decision_id) != "decisions":
        raise SpecError(f"no decision {decision_id}")
    if not choice.strip():
        raise SpecError("a decision needs a choice")
    d.update(status="decided", choice=choice.strip(), rationale=rationale.strip() or None)
    return d


def waive(spec: dict, key: str, reason: str) -> dict:
    if not reason.strip():
        raise SpecError("a waiver needs a reason")
    spec["waivers"] = [w for w in spec["waivers"] if w["key"] != key]
    w = {"key": key, "reason": reason.strip()}
    spec["waivers"].append(w)
    return w


def validate(spec) -> None:
    """Raise SpecError if `spec` is not a structurally valid schema-1 spec."""
    if not isinstance(spec, dict):
        raise SpecError("spec is not a JSON object")
    if spec.get("schema") != SCHEMA_VERSION:
        raise SpecError(f"unsupported schema {spec.get('schema')!r}")
    for key in ("title", "problem"):
        if not isinstance(spec.get(key), str):
            raise SpecError(f"{key} must be a string")
    if not isinstance(spec.get("counters"), dict) or not isinstance(spec.get("waivers"), list):
        raise SpecError("counters and waivers are required")
    seen = set()
    for name, (prefix, _) in COLLECTIONS.items():
        items = spec.get(name)
        if not isinstance(items, list):
            raise SpecError(f"{name} must be a list")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise SpecError(f"{name} has an item without an ID")
            if prefix_of(item["id"]) != prefix:
                raise SpecError(f"{item['id']} is in the wrong collection {name}")
            if item["id"] in seen:
                raise SpecError(f"duplicate ID {item['id']}")
            seen.add(item["id"])


def migrate(raw: dict) -> dict:
    """Upgrade an older document to the current schema.

    Schema 0 (or no schema key) is the simple hand-written form: lists of
    plain strings, for example {"title": "X", "requirements": ["...", "..."]}.
    """
    if not isinstance(raw, dict):
        raise SpecError("spec is not a JSON object")
    version = raw.get("schema", 0)
    if version == SCHEMA_VERSION:
        return raw
    if version != 0:
        raise SpecError(f"cannot migrate schema {version!r}; this tool knows 0 and 1")
    spec = empty_spec(str(raw.get("title", "Untitled spec")))
    spec["problem"] = str(raw.get("problem", ""))
    for name in COLLECTIONS:
        for entry in raw.get(name, []) or []:
            if isinstance(entry, str):
                fields = {"question": entry} if name == "decisions" else {"text": entry}
            elif isinstance(entry, dict):
                fields = {k: v for k, v in entry.items() if k != "id"}
            else:
                raise SpecError(f"cannot migrate {name} entry {entry!r}")
            add(spec, name, fields)
    return spec


def clone(spec: dict) -> dict:
    return copy.deepcopy(spec)
