# Spec Workbench

Turn a messy brief into a spec an implementer can build from without guessing. The workbench pulls the brief apart into requirements, decisions, assumptions and non-goals. It flags contradictions and open decisions, keeps every revision, and turns acceptance criteria into a test checklist and a pytest skeleton.

Spec Grader checks how a spec is worded. The workbench manages the whole spec. It uses Spec Grader's lexicon for ambiguity, and every check prints the Spec Grader score next to the findings.

**Runs entirely on your machine. No account, no network, no model calls.**

## Install
```
pip install ../spec-grader .      # from this folder; installs the spec-bench command
```

## The loop
```
spec-bench intake my-spec brief.md          # revision 1: every sentence classified, with its line number
spec-bench check my-spec                    # contradictions, gaps, open decisions
spec-bench decide my-spec D1 --choice email --rationale "everyone has a work address"
spec-bench edit my-spec R2 --text "A voter must cast a vote in at most 2 taps."
spec-bench add my-spec criterion --req R2 --given "an open poll" --when "a voter taps a place" --then "the page shows \"Vote saved\""
spec-bench apply my-spec changes.json -m "review notes"   # many edits, one revision, all or nothing
spec-bench diff my-spec 1 4                 # what changed and which findings it fixed
spec-bench export my-spec --format html --out report.html  # also md, json, checklist, pytest
```
Other commands: `new --template blank|cli-tool|web-feature|api-endpoint`, `templates`, `show`, `remove`, `waive KEY --reason`, `history`, `revert N`. Gate a CI job with `check --fail-on blocking` (exit 1). Exit code 2 means a usage or workspace error.

## Try the example
```
examples/team-lunch-poll/walkthrough.sh
```
The script starts from a deliberately messy [brief](examples/team-lunch-poll/brief.md) and makes four revisions. The results are committed in [examples/team-lunch-poll/output](examples/team-lunch-poll/output/):

| Revision | What happened | Blocking | Spec Grader |
|---|---|---|---|
| 1 | Intake from the brief | 15 | B (86) |
| 2 | Decisions recorded, conflicts resolved, wording sharpened | 10 | A (100) |
| 3 | Acceptance criteria added | 0 (2 warnings) | A (100) |
| 4 | One vague criterion fixed, one false positive waived | 0 | A (100) |

Revision 2 scores a perfect 100 but is not ready to build, because no requirement has a test yet. **A numeric grade is never proof of success.**

## What it checks
Fourteen rules, WB001 to WB014, are listed in the [spec](../../specs/spec-workbench.md#rule-table). They cover ambiguous wording, missing or incomplete criteria, outcomes nobody can observe, open decisions, requirements that break a non-goal, numeric limits that cannot both hold, opposite requirements, duplicates, compound requirements, missing sections, assumptions with no validation plan, dangling IDs and lines intake could not classify. A spec is "ready to build" only when no blocking finding is left unwaived.

Findings marked "judgment call" are heuristics. If one is wrong, waive it by key with a reason. The waiver stays in the report, so a reviewer can disagree with it.

## What it cannot judge
- Whether this is the right product, or whether users want it.
- Contradictions that need domain knowledge. In the example, "votes are anonymous" versus "the organizer sees who voted" was caught by a person and recorded as decision D3.
- Whether a criterion is enough, only whether it is complete and observable.
- Ambiguity outside the curated lexicon, plus feasibility, effort, security and legal risk.

## Workspace format
`DIR/spec.json` holds the current spec, plain JSON you can read. `DIR/history/0001.json` and the files after it record every revision, and none is ever deleted. Writes go to a temporary file and are then renamed into place. If `spec.json` is damaged, the next command moves it to `spec.json.corrupt-N` and restores the latest good revision. Older hand-written files that are just lists of strings are migrated automatically. Set `SPEC_BENCH_NOW` to pin timestamps for reproducible output.

## Tests
```
python3 -m pytest -q
```
Built spec first: [spec](../../specs/spec-workbench.md), [plan](../../plans/spec-workbench-plan.md). Made by Mick. MIT licensed.
