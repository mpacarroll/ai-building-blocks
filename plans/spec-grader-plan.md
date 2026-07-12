# Spec Grader Implementation Plan

> Built with the superpowers `writing-plans` + `test-driven-development` skills. Every task shipped with the RED observed before GREEN.

**Goal:** a local CLI that scores a spec for ambiguity and testable-requirement coverage.

**Architecture:** pure, deterministic modules (ambiguity → requirements → grade → report) behind a thin CLI. No LLM, no network — the whole point is a fast, reproducible, offline check.

**Tech stack:** Python 3.10+, standard library only, `pytest`.

## Global constraints
- Zero dependencies; offline; deterministic (same input → same grade).
- Test-first: no production code without a failing test observed first.

---

### Task 1 — Ambiguity lexicon + detector
`ambiguity.find_ambiguities(text) -> [{line, term, category, why}]`, word-boundaried, case-insensitive, multi-word phrases. Curated lexicon grouped by why each term hurts. ✅ `tests/test_ambiguity.py`

### Task 2 — Requirement extraction
`requirements.extract(text)` — RFC 2119 normative keywords (MUST/SHALL/REQUIRED) and numbered list items count as testable requirements; each is flagged if its line is also ambiguous; numbered items are not double-counted with keywords. ✅ `tests/test_requirements.py`

### Task 3 — Grade
`grade.grade(text)` — deterministic score from ambiguous-requirement ratio and total ambiguity flags; letter grade; a spec with no testable requirements scores 40/F. ✅ `tests/test_grade.py`

### Task 4 — Report + CLI + golden set
`report.to_markdown` / `report.to_html` (self-contained, offline); `spec-grade <file> [--html] [--fail-under N]`. Golden fixtures with hand-computed scores (good=100/A, bad=38/F) guard against regressions. ✅ `tests/test_cli.py`

## Verification
18 pytest tests green; `spec-grade` entry point installs and runs; the HTML report renders with **zero external requests** in a real browser; dogfooded on this repo's own specs (which drove the numbered-requirement improvement in Task 2).
