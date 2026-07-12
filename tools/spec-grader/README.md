# Spec Grader

Grade a spec before you build from it. Point it at a markdown or text spec and it scores two things that decide whether an implementer (human or AI) can build without guessing:

1. **Ambiguity** — the weasel words that force a question ("fast", "user-friendly", "as needed", "gracefully", "TBD"). Each flag says which line and why it hurts.
2. **Testable requirements** — the normative statements (MUST / SHALL / REQUIRED) and numbered requirement items an implementer can actually verify against.

**Runs entirely on your machine. No account, no network, no data leaves your computer.**

## Install
```
pipx install spec-grader     # recommended
# or: pip install spec-grader
```

## Use
```
spec-grade my-spec.md                    # print the grade + findings
spec-grade my-spec.md --html report.html # also write a self-contained report
spec-grade my-spec.md --fail-under 80    # exit nonzero for a CI gate
```

## How the grade works
Deterministic and documented, so a grade is reproducible and arguable — never a black box:
- **penalty for ambiguous requirements** = 50 × (ambiguous requirements ÷ total requirements)
- **penalty for ambiguous prose** = min(30, 2 × total ambiguity flags)
- **score** = 100 − both penalties (floored at 0); a spec with no testable requirements scores 40 (there is nothing binding to build to)
- **grade**: 90+ A, 80+ B, 70+ C, 60+ D, else F

## Why this exists
This is the "zero-edit spec" discipline as a tool: a spec good enough that an agent implements it with no clarifying questions. Every ambiguity flag is a question you would otherwise get mid-build. It grew out of a bootcamp grader ([spec](../../specs/spec-grader.md)); the deterministic linter here is v1, and an LLM-backed "try to build it and log the questions" pass is the documented v2.

## Honest notes
- The lexicon is curated, not exhaustive — it catches the common offenders, not every possible vagueness. Judgment still matters.
- Numbered list items are treated as requirements, which fits most specs but will over-count a numbered list that is really just steps.

Built spec-first, test-first. Made by Mick. [Who's Mick? →](../../README.md) · MIT licensed.
