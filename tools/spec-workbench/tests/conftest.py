"""Make the sibling spec-grader package importable without installing it."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRADER = ROOT.parent / "spec-grader"
for p in (ROOT, GRADER):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
