#!/usr/bin/env bash
# Rebuild the lunch poll example from the messy brief to a ready spec, then
# check real test results against it.
# Every output under output/ is regenerated; SPEC_BENCH_NOW pins timestamps so
# the files are byte-identical on every run. Needs pytest for the evidence step;
# set PYTHON to an interpreter that has it if python3 does not.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOL="$(cd "$HERE/../.." && pwd)"
export PYTHONPATH="$TOOL:$TOOL/../spec-grader${PYTHONPATH:+:$PYTHONPATH}"
PY="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1
bench() { "$PY" -m spec_workbench.cli "$@"; }
if ! "$PY" -c "import pytest" 2> /dev/null; then
  echo "error: $PY cannot import pytest, which the evidence step needs." >&2
  echo "Install it (pip install pytest) or set PYTHON to an interpreter that has it." >&2
  exit 2
fi
OUT="${SPEC_BENCH_EXAMPLE_OUT:-$HERE/output}"
WS="$OUT/workspace"
rm -rf "$OUT"
mkdir -p "$OUT"

step() { export SPEC_BENCH_NOW="$1"; }

step 2026-11-09T09:00:00Z
bench intake "$WS" "$HERE/brief.md"
bench check "$WS" > "$OUT/check-r1.txt" || true
bench export "$WS" --format md --out "$OUT/spec-r1.md"
bench export "$WS" --format html --out "$OUT/report-r1.html"

step 2026-11-09T09:30:00Z
bench apply "$WS" "$HERE/r2-decisions.json" -m "Decide open questions, resolve conflicts, sharpen wording"
bench check "$WS" > "$OUT/check-r2.txt" || true

step 2026-11-09T10:00:00Z
bench apply "$WS" "$HERE/r3-criteria.json" -m "Add acceptance criteria for every must requirement"
bench check "$WS" > "$OUT/check-r3.txt"

step 2026-11-09T10:15:00Z
bench apply "$WS" "$HERE/r4-review.json" -m "Sharpen AC7; waive a verb-list false positive on AC10"
bench check "$WS" --fail-on blocking > "$OUT/check-r4.txt"

bench history "$WS" > "$OUT/history.txt"
bench diff "$WS" 1 4 > "$OUT/diff-r1-r4.txt"
bench export "$WS" --format md --out "$OUT/spec-r4.md"
bench export "$WS" --format checklist --out "$OUT/checklist-r4.md"
bench export "$WS" --format pytest --out "$OUT/test_acceptance_skeleton.py"
bench export "$WS" --format html --out "$OUT/report-r4.html"
bench export "$WS" --format json --out "$OUT/spec-r4.json"

# Evidence. evidence/tests/test_acceptance.py was written from the revision 4
# skeleton against a small demo app (evidence/lunch_poll.py). Then the team
# changes the close time, so the AC5 test still passes but no longer proves AC5.
step 2026-11-09T11:00:00Z
bench apply "$WS" "$HERE/r5-change.json" -m "Team asked for 15 minutes; update R5 and AC5"
bench diff "$WS" 4 5 > "$OUT/diff-r4-r5.txt"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
(cd "$HERE/evidence" && "$PY" -m pytest tests -q -p no:cacheprovider \
    --junitxml "$TMP/junit.xml" > /dev/null) || true
bench verify "$WS" --junit "$TMP/junit.xml" --tests "$HERE/evidence/tests" > "$OUT/verify-r5.txt"
bench evidence "$WS" > "$OUT/evidence-runs.txt"
bench export "$WS" --format checklist --out "$OUT/checklist.md"
bench export "$WS" --format html --out "$OUT/report.html"
echo "Done. Open $OUT/report.html"
