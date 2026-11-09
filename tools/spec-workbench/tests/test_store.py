import json

import pytest

from spec_workbench import model, store


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setenv("SPEC_BENCH_NOW", "2026-11-09T09:00:00Z")


def make(ws):
    s = model.empty_spec("T")
    model.add(s, "requirements", {"text": "It must run."})
    store.create(ws, s, "first")
    return s


def test_commit_writes_history_and_current(tmp_path):
    s = make(tmp_path)
    model.add(s, "requirements", {"text": "It must stop."})
    assert store.commit(tmp_path, s, "second") == 2
    assert [h["message"] for h in store.history(tmp_path)] == ["first", "second"]
    assert store.load(tmp_path) == s
    assert store.read_revision(tmp_path, 1)["spec"]["requirements"][-1]["id"] == "R1"
    assert store.history(tmp_path)[0]["at"] == "2026-11-09T09:00:00Z"


def test_create_refuses_existing_workspace(tmp_path):
    make(tmp_path)
    with pytest.raises(store.WorkspaceError):
        make(tmp_path)


def test_load_refuses_non_workspace(tmp_path):
    with pytest.raises(store.WorkspaceError):
        store.load(tmp_path)


def test_corrupt_spec_is_moved_aside_and_latest_revision_restored(tmp_path):
    s = make(tmp_path)
    (tmp_path / "spec.json").write_text('{"schema": 1, "title": ')   # truncated write
    warnings = []
    assert store.load(tmp_path, warn=warnings.append) == s
    assert (tmp_path / "spec.json.corrupt-1").exists()
    assert "corrupt-1" in warnings[0] and "revision 1" in warnings[0]
    (tmp_path / "spec.json").write_text("[]")                      # valid JSON, invalid spec
    store.load(tmp_path, warn=warnings.append)
    assert (tmp_path / "spec.json.corrupt-2").exists()


def test_recovery_skips_damaged_revisions_and_handles_missing_spec(tmp_path):
    s = make(tmp_path)
    s2 = model.clone(s)
    model.add(s2, "requirements", {"text": "It must stop."})
    store.commit(tmp_path, s2, "second")
    (tmp_path / "history" / "0002.json").write_text("garbage")
    (tmp_path / "spec.json").unlink()
    warnings = []
    assert store.load(tmp_path, warn=warnings.append) == s
    assert "missing" in warnings[0]
    with pytest.raises(store.WorkspaceError):
        store.read_revision(tmp_path, 2)
    assert store.history(tmp_path)[1]["message"] == "(damaged revision file)"


def test_unrecoverable_workspace_raises(tmp_path):
    make(tmp_path)
    (tmp_path / "spec.json").write_text("nope")
    (tmp_path / "history" / "0001.json").write_text("nope")
    with pytest.raises(store.WorkspaceError):
        store.load(tmp_path)


def test_atomic_write_leaves_old_file_on_failure(tmp_path, monkeypatch):
    s = make(tmp_path)
    before = (tmp_path / "spec.json").read_text()

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(store.os, "replace", boom)
    with pytest.raises(OSError):
        store._atomic_write(tmp_path / "spec.json", "partial")
    assert (tmp_path / "spec.json").read_text() == before
    assert not list(tmp_path.glob(".spec.json.*.tmp"))
    assert json.loads(before) == s


def test_load_migrates_schema_zero_file(tmp_path):
    make(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps({"title": "Old", "requirements": ["It must run."]}))
    spec = store.load(tmp_path)
    assert spec["schema"] == 1 and spec["requirements"][0]["id"] == "R1"


def test_interrupted_save_does_not_resurrect_an_older_revision(tmp_path):
    # commit() writes history first; a crash before spec.json is written leaves
    # spec.json one revision behind. Loading must restore the newest revision,
    # or the next commit drops it and reuses its IDs.
    s = make(tmp_path)
    model.add(s, "requirements", {"text": "It must stop."})
    store.commit(tmp_path, s, "second")
    old = store.read_revision(tmp_path, 1)["spec"]
    (tmp_path / store.SPEC_FILE).write_text(json.dumps(old))
    warnings = []
    loaded = store.load(tmp_path, warn=warnings.append)
    assert [r["id"] for r in loaded["requirements"]] == ["R1", "R2"]
    assert "interrupted" in warnings[0]
    assert model.next_id(loaded, "requirements") == "R3"


def test_hand_edit_that_matches_no_revision_is_kept(tmp_path):
    make(tmp_path)
    raw = json.loads((tmp_path / store.SPEC_FILE).read_text())
    raw["requirements"].append({"id": "R7", "text": "Hand added."})  # no priority
    (tmp_path / store.SPEC_FILE).write_text(json.dumps(raw))
    warnings = []
    loaded = store.load(tmp_path, warn=warnings.append)
    assert warnings == []
    assert model.find(loaded, "R7")["priority"] == "must"   # default filled in


def test_hand_edit_with_a_broken_item_is_moved_aside_not_crashed(tmp_path):
    make(tmp_path)
    raw = json.loads((tmp_path / store.SPEC_FILE).read_text())
    raw["requirements"].append({"id": "R7"})
    (tmp_path / store.SPEC_FILE).write_text(json.dumps(raw))
    warnings = []
    loaded = store.load(tmp_path, warn=warnings.append)
    assert [r["id"] for r in loaded["requirements"]] == ["R1"]
    assert "R7: text" in warnings[0]
    assert (tmp_path / "spec.json.corrupt-1").exists()
