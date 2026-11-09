# Spec: Spec Workbench

## Intent
Turn a rough idea into a structured spec that an implementer can build from without guessing. The workbench exposes contradictions and missing decisions, tracks every revision, and produces testable acceptance criteria. It extends Spec Grader: the grader judges wording, the workbench manages the whole spec.

## Users
- A builder (product, design or engineering background) who has a messy brief and wants a buildable spec.
- An AI coding agent that receives the exported spec and checklist.

## Non-goals (v1)
- No LLM calls, no network, no accounts. Every check is rule based and deterministic.
- No judgment on whether the product is worth building. The tool checks structure and wording only.
- No multi-user editing or merge of concurrent edits.

## Data model
A spec is a JSON document with schema version 1 and these collections, each item carrying a stable ID that is never reused: users (U), goals (G), non-goals (N), requirements (R, with priority must, should or could and an optional `depends_on` list of decision IDs), decisions (D, with question, options, status open or decided, choice and rationale), assumptions (A, with an optional validation plan), constraints (C), acceptance criteria (AC, linked to one requirement, with given, when, then and status draft or agreed), unclassified intake lines (X), and waivers (finding key plus reason). Intake items keep the source line number and text.

## Requirements
1. `spec-bench intake DIR BRIEF` MUST read a markdown or text brief and create a workspace in DIR with revision 1.
2. Intake MUST classify each brief sentence into exactly one collection using documented cue words, and MUST place sentences it cannot classify into `unclassified` instead of dropping them.
3. Intake MUST record the source line number and original text on every item it creates.
4. Intake MUST honor section headings (for example "Out of scope", "Open questions", "Assumptions") over sentence cue words.
5. `spec-bench check DIR` MUST run every rule in the rule table below and print each finding with its rule ID, severity, target item IDs and a suggested fix.
6. A spec MUST be reported "ready to build" only when it has zero unwaived blocking findings.
7. The check output MUST print the Spec Grader lint score of the exported markdown and MUST state that a numeric grade is not proof of success.
8. The check output MUST list what the rules cannot judge.
9. Every mutating command (`add`, `edit`, `remove`, `decide`, `waive`, `apply`, `revert`) MUST write a new numbered revision with a message and a timestamp.
10. `spec-bench diff DIR A B` MUST list added, removed and changed items between two revisions and MUST list findings resolved and introduced between them.
11. `spec-bench revert DIR N` MUST restore revision N as a new revision and MUST NOT delete history.
12. If `spec.json` is unreadable or fails validation, `load` MUST move it aside to `spec.json.corrupt-N`, restore the latest valid revision, and print a warning naming both files.
13. Writes MUST be atomic (write to a temporary file, then rename) so an interrupted write never leaves a partial `spec.json`.
14. `spec-bench export` MUST support formats `md`, `json`, `html`, `checklist` and `pytest`. The HTML report MUST load zero external resources.
15. The `pytest` export MUST generate one test per acceptance criterion that fails with `NotImplementedError` until a human writes it, so an empty skeleton never passes.
16. `spec-bench new DIR --template NAME` MUST create a workspace from one of the templates `blank`, `cli-tool`, `web-feature`, `api-endpoint`.
17. `spec-bench waive DIR KEY --reason TEXT` MUST suppress one finding by key, and the report MUST still show the waived finding with its reason.
18. The same spec MUST produce byte-identical check output on every run when `SPEC_BENCH_NOW` is set.

## Rule table
| Rule | Severity | Fires when |
|---|---|---|
| WB001 ambiguous-wording | blocking for must, else warning | a requirement or criterion contains a Spec Grader lexicon term |
| WB002 missing-criterion | blocking for must, warning for should | a requirement has no acceptance criterion |
| WB003 incomplete-criterion | blocking | a criterion is missing given, when or then |
| WB004 unobservable-outcome | warning (judgment) | a criterion's then clause has no number, quoted text or observable verb |
| WB005 open-decision | blocking if a requirement depends on it, else warning | a decision is open |
| WB006 nongoal-conflict | blocking (warning if the overlap is one word) | every core word of a non-goal appears in a requirement |
| WB007 bound-conflict | blocking if bounds cannot both hold, warning if they differ | two items set numeric limits on the same subject and unit dimension |
| WB008 polarity-conflict | blocking | one requirement affirms what another negates |
| WB009 duplicate | warning | two requirements share 80 percent or more of their words |
| WB010 compound | warning (judgment) | a requirement contains two or more modal verbs |
| WB011 missing-section | warning (blocking if no requirements) | problem, users, goals or non-goals is empty |
| WB012 unvalidated-assumption | warning | an assumption has no validation plan |
| WB013 dangling-reference | blocking | a criterion or `depends_on` names an ID that does not exist |
| WB014 unclassified | info | intake left a line unclassified |

## Verification
- Unit tests per module plus a golden walkthrough: the lunch poll example brief MUST produce the committed findings at revision 1 and zero blocking findings at revision 3.
- The HTML report is checked for zero `http://`, `https://` and `src=` strings.
