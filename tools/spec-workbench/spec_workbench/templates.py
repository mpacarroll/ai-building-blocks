"""Reusable starting points. A template seeds the questions a spec of that kind
must answer, as open decisions, so `check` keeps asking until they are decided.
Templates never invent requirements."""
from . import model

TEMPLATES = {
    "blank": {
        "description": "Empty spec with every section.",
        "decisions": [],
        "assumptions": [],
    },
    "cli-tool": {
        "description": "A command-line tool: inputs, outputs, exit codes, offline behavior.",
        "decisions": [
            ("What exact commands and flags does the tool accept?", []),
            ("What does it print on success, and in what format?", ["plain text", "JSON"]),
            ("Which exit code means which failure?", []),
            ("Does it need the network?", ["never", "optional", "required"]),
        ],
        "assumptions": ["Users run it on macOS, Linux and Windows."],
    },
    "web-feature": {
        "description": "A user-facing web feature: states, permissions, empty and error views.",
        "decisions": [
            ("Who can see and use this feature?", []),
            ("What does the screen show when there is no data yet?", []),
            ("What does the user see when a save fails?", []),
            ("Which screen widths must it support?", ["phone", "tablet", "desktop"]),
        ],
        "assumptions": ["Users are signed in when they reach this feature."],
    },
    "api-endpoint": {
        "description": "An HTTP endpoint: request, response, errors, limits.",
        "decisions": [
            ("What is the method and path?", []),
            ("What is the exact request and response body?", []),
            ("Which status codes are returned for which errors?", []),
            ("What is the rate limit per client?", []),
            ("Who is allowed to call it, and how are they authenticated?", []),
        ],
        "assumptions": ["Callers retry on a 5xx response."],
    },
}


def names() -> list:
    return list(TEMPLATES)


def build(name: str, title: str) -> dict:
    if name not in TEMPLATES:
        raise model.SpecError(f"unknown template {name!r}; choose from {', '.join(TEMPLATES)}")
    t = TEMPLATES[name]
    spec = model.empty_spec(title)
    for question, options in t["decisions"]:
        model.add(spec, "decisions", {"question": question, "options": list(options),
                                      "source": {"template": name}})
    for text in t["assumptions"]:
        model.add(spec, "assumptions", {"text": text, "source": {"template": name}})
    return spec
