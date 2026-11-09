# Spec Workbench Implementation Plan

**Goal:** a local CLI that turns a rough brief into a structured, revisioned spec with rule-based checks and testable acceptance criteria. The spec is [specs/spec-workbench.md](../specs/spec-workbench.md).

**Architecture:** pure modules behind a thin CLI. `model` (schema, IDs, edits, migration), `intake` (brief to draft spec), `checks` (rules WB001 to WB014), `store` (atomic writes, history, recovery), `diff`, `export` (md, json, checklist, pytest, html) and `templates`. The tool reuses `spec_grader.ambiguity` and `spec_grader.grade` instead of copying them.

**Tech stack:** Python 3.10+, standard library plus the sibling `spec-grader` package, `pytest`.

## Tasks
1. Data model with stable IDs that are never reused, validation and schema 0 to 1 migration. `tests/test_model.py`
2. Intake: cue-word classification in a fixed order, section-heading overrides, source lines, and a requirement plus decision split for "X, A or B?". `tests/test_intake.py`
3. Checks: the 14 rules, waivers, stale-waiver notes, a ready state and natural sort order. `tests/test_checks.py`
4. Store: atomic writes, numbered history, recovery from a corrupt or missing file, and skipping damaged revisions. `tests/test_store.py`
5. Diff and exports: item and finding deltas, a self-contained HTML report, and a pytest skeleton that fails until someone writes it. `tests/test_diff_export.py`
6. CLI: every command, the all-or-nothing `apply`, gate exit codes and recovery through the CLI. `tests/test_cli.py`
7. Golden example: the lunch poll walkthrough regenerates the committed outputs byte for byte. `tests/test_walkthrough.py`

## Slice 2: evidence
8. Fingerprints and pin comments in the pytest export. `tests/test_evidence.py`
9. JUnit parsing, pin scanning, one status per criterion, orphans, requirement roll-up. `tests/test_evidence.py`
10. Numbered evidence runs, re-reading an old run against the current spec, `verify` and `evidence` commands with gates. `tests/test_evidence.py`
11. Checklist ticks and an HTML evidence section from the latest run. `tests/test_evidence.py`
12. Golden example continues to revision 5 with a demo app and tests written from the revision 4 skeleton. `tests/test_walkthrough.py`

## Verification
- `python3 -m pytest -q` in `tools/spec-workbench`: 58 tests pass.
- `spec-bench` installs from a clean virtual environment.
- Playwright renders the HTML report at phone and desktop widths, in light and dark mode, with no horizontal scroll and zero external requests.
