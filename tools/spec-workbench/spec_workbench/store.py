"""Workspace persistence: a directory holding the current spec and its full
revision history.

  DIR/spec.json            the current spec (always equal to the latest revision)
  DIR/history/0001.json    {rev, at, message, spec} for every revision, never deleted

Writes are atomic (temp file + os.replace). If spec.json is unreadable or
invalid, `load` moves it aside and restores the latest valid revision.
"""
import datetime
import json
import os
import pathlib
import tempfile

from . import model

SPEC_FILE = "spec.json"
HISTORY_DIR = "history"


class WorkspaceError(Exception):
    pass


def now() -> str:
    fixed = os.environ.get("SPEC_BENCH_NOW")
    if fixed:
        return fixed
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write(path: pathlib.Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def history_files(ws) -> list:
    d = pathlib.Path(ws) / HISTORY_DIR
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("[0-9][0-9][0-9][0-9].json"))


def exists(ws) -> bool:
    ws = pathlib.Path(ws)
    return (ws / SPEC_FILE).exists() or bool(history_files(ws))


def create(ws, spec: dict, message: str) -> int:
    ws = pathlib.Path(ws)
    if exists(ws):
        raise WorkspaceError(f"{ws} already holds a spec workspace")
    model.validate(spec)
    return commit(ws, spec, message)


def commit(ws, spec: dict, message: str) -> int:
    """Record `spec` as a new revision and make it current. Returns the revision."""
    ws = pathlib.Path(ws)
    model.validate(spec)
    files = history_files(ws)
    rev = (int(files[-1].stem) if files else 0) + 1
    entry = {"rev": rev, "at": now(), "message": message or "(no message)", "spec": spec}
    # History first: if we crash between the two writes, load() recovers from it.
    _atomic_write(ws / HISTORY_DIR / f"{rev:04d}.json", _dump(entry))
    _atomic_write(ws / SPEC_FILE, _dump(spec))
    return rev


def read_revision(ws, rev: int) -> dict:
    path = pathlib.Path(ws) / HISTORY_DIR / f"{int(rev):04d}.json"
    if not path.exists():
        raise WorkspaceError(f"no revision {rev} in {ws}")
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
        model.validate(entry["spec"])
    except (ValueError, KeyError, TypeError, model.SpecError) as e:
        raise WorkspaceError(f"revision {rev} is damaged: {e}") from e
    return entry


def history(ws) -> list:
    """[{rev, at, message}] for readable revisions, oldest first."""
    out = []
    for p in history_files(ws):
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
            out.append({"rev": entry["rev"], "at": entry["at"], "message": entry["message"]})
        except (ValueError, KeyError, TypeError):
            out.append({"rev": int(p.stem), "at": "?", "message": "(damaged revision file)"})
    return out


def latest_rev(ws) -> int:
    files = history_files(ws)
    return int(files[-1].stem) if files else 0


def load(ws, warn=None) -> dict:
    """Load the current spec, recovering from a corrupt spec.json.

    `warn` is called with a message when recovery happens.
    """
    ws = pathlib.Path(ws)
    path = ws / SPEC_FILE
    if not exists(ws):
        raise WorkspaceError(f"{ws} is not a spec workspace (run spec-bench intake or new)")
    problem = None
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            spec = model.migrate(raw)
            model.validate(spec)
            return spec
        except (ValueError, model.SpecError) as e:
            problem = str(e)
    else:
        problem = "spec.json is missing"
    for p in reversed(history_files(ws)):
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
            spec = entry["spec"]
            model.validate(spec)
        except (ValueError, KeyError, TypeError, model.SpecError):
            continue
        moved = None
        if path.exists():
            n = 1
            while (ws / f"{SPEC_FILE}.corrupt-{n}").exists():
                n += 1
            moved = ws / f"{SPEC_FILE}.corrupt-{n}"
            os.replace(path, moved)
        _atomic_write(path, _dump(spec))
        if warn:
            where = f"moved the bad file to {moved.name}" if moved else "it was missing"
            warn(f"warning: {SPEC_FILE} could not be used ({problem}); {where} and "
                 f"restored revision {entry['rev']} from {HISTORY_DIR}/{p.name}.")
        return spec
    raise WorkspaceError(f"{SPEC_FILE} is unusable ({problem}) and no valid revision exists")
