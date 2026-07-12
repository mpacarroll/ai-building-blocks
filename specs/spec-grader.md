# Spec: Bootcamp Exercise Grader (agent harness)

*This document is itself course material: students read a production SDD spec that runs their own grading. It is also a future SaaS candidate ("spec grader" API).*

## Intent
Grade every bootcamp exercise within 24 hours with consistent, rubric-traced feedback, escalating only genuinely ambiguous cases to the instructor (cap: top/bottom deciles + explicit escalations).

## Inputs
- Student submission (markdown spec, test suite, annotated transcript, or artifact repo — per module).
- Module rubric (versioned YAML: criteria, weights, machine-verifiable checks, exemplar anchors).

## Behavior (per module type)
1. **Spec submissions (M1–M3, M6, M8):** an implementation agent attempts to build from the spec with clarifying-questions logging ON. Every question it would need to ask = one ambiguity. Trace-coverage check: each requirement must cite evidence. Output: ambiguity list, coverage %, rubric scores with quoted justification.
2. **Test-design submissions (M4):** run the student's acceptance suite against N reference implementations (1 correct, k flawed with known defect labels). Score = defects caught / k, false-alarm penalty. Output: caught/missed table.
3. **Evaluation submissions (M5, M8 peer review):** compare student's verdict + method against the known ground truth; grade the method quality, not just the verdict.

## Quality gates
- Deterministic re-run: same submission grades within ±5% (temperature pinned, rubric-anchored).
- Every score line must quote the submission — no unanchored judgments.
- Escalation triggers: rubric confidence < threshold, student dispute, score in top/bottom decile.
- Feedback tone: specific, kind, actionable; never sarcastic (it represents the brand).

## Non-goals (v1)
No plagiarism detection, no live-session grading, no auto-certification decisions (instructor signs completions).

## Verification
Golden set: 10 seeded submissions per module with known scores; harness must reproduce them before each cohort opens.
