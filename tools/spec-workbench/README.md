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
Other commands: `new --template blank|cli-tool|web-feature|api-endpoint`, `templates`, `show`, `remove`, `waive KEY --reason`, `history`, `revert N`. Gate a CI job with `check --fail-on blocking` (exit 1). Exit code 2 means a usage, workspace or evidence error.

## From ready spec to proof
A ready spec is a plan. Evidence says which criteria a real, current test has passed.
```
spec-bench export my-spec --format pytest --out tests/test_acceptance.py   # one failing test per criterion
# write the tests, keeping each "# spec-bench: AC3 fp=..." pin comment above its test
pytest tests --junitxml results.xml
spec-bench verify my-spec --junit results.xml --tests tests       # saves evidence run 1
spec-bench evidence my-spec                 # list runs; "evidence my-spec 1" re-reads run 1 against today's spec
spec-bench verify my-spec --junit results.xml --tests tests --fail-on unverified   # CI gate
```
Each criterion gets exactly one status:

| Status | Meaning |
|---|---|
| verified | a test pinned to the criterion's current wording passed |
| stale | a test passed, but it was written against older wording of the criterion |
| unpinned | a test passed, but its pin comment is missing, so drift cannot be detected |
| failing | a mapped test failed or errored |
| unwritten | the mapped test is still the generated `NotImplementedError` skeleton |
| skipped | every mapped test was skipped |
| untested | no test result names the criterion |

The pin is a fingerprint of the criterion's requirement, given, when and then. Edit the criterion and its old test still passes, but `verify` reports it stale until someone updates the test and its pin. The checklist and HTML exports tick only verified criteria and name the test behind each tick. A passing test proves the test passed, not that it checks what the criterion says, so read the test before you trust the tick.

## Try the example
```
examples/team-lunch-poll/walkthrough.sh
```
The script starts from a deliberately messy [brief](examples/team-lunch-poll/brief.md) and makes five revisions, then checks real test results against the spec. It needs `pytest`; set `PYTHON` to an interpreter that has it if `python3` does not. The results are committed in [examples/team-lunch-poll/output](examples/team-lunch-poll/output/):

| Revision | What happened | Blocking | Spec Grader |
|---|---|---|---|
| 1 | Intake from the brief | 15 | B (86) |
| 2 | Decisions recorded, conflicts resolved, wording sharpened | 10 | A (100) |
| 3 | Acceptance criteria added | 0 (2 warnings) | A (100) |
| 4 | One vague criterion fixed, one false positive waived | 0 | A (100) |
| 5 | The team changes the close time from 10 to 15 minutes | 0 | A (100) |

Between revisions 4 and 5, someone built a small [demo app](examples/team-lunch-poll/evidence/lunch_poll.py) and wrote [tests](examples/team-lunch-poll/evidence/tests/test_acceptance.py) from the revision 4 skeleton. The [evidence run](examples/team-lunch-poll/output/verify-r5.txt) against revision 5 shows 5 of 10 criteria verified. AC5's test still passes, but it checks the old 10 minute close, so AC5 is stale. AC9's test lost its pin (unpinned). AC10 catches a real bug (failing). AC2 and AC7 need a browser and are still skeletons (unwritten). The spec is "ready to build" at every one of these steps, and is still only half proven.

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
`DIR/spec.json` holds the current spec, plain JSON you can read. `DIR/history/0001.json` and the files after it record every revision, and none is ever deleted. `DIR/evidence/0001.json` and on record each `verify` run: the revision, each criterion's fingerprint, and every test outcome. Writes go to a temporary file and are then renamed into place. If `spec.json` is damaged, or still holds an older revision because a save was interrupted, the next command moves it to `spec.json.corrupt-N` and restores the latest good revision. A hand edit that matches no revision is kept. Older hand-written files that are just lists of strings are migrated automatically. Set `SPEC_BENCH_NOW` to pin timestamps for reproducible output.

## Tests
```
python3 -m pytest -q
```
Built spec first: [spec](../../specs/spec-workbench.md), [plan](../../plans/spec-workbench-plan.md). Made by Mick. MIT licensed.
