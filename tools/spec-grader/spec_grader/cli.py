"""spec-grade — score a spec for ambiguity and testable-requirement coverage.

Usage:
  spec-grade path/to/spec.md
  spec-grade spec.md --html report.html          # also write an offline report
  spec-grade spec.md --fail-under 80             # exit 1 if the score is lower (for CI)

Fully local. No network, no account, no data leaves your machine.
"""
import argparse
import pathlib
import sys

from . import grade, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="spec-grade", description=__doc__)
    ap.add_argument("spec", help="path to a spec file (markdown or text)")
    ap.add_argument("--html", help="also write a self-contained HTML report here")
    ap.add_argument("--fail-under", type=int, default=None,
                    help="exit nonzero if the score is under this (for CI gates)")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.spec)
    if not path.exists():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    result = grade.grade(path.read_text())

    print(f"Grade: {result['grade']}  ({result['score']}/100)")
    print(report.to_markdown(result, name=path.name))

    if args.html:
        pathlib.Path(args.html).write_text(report.to_html(result, name=path.name))
        print(f"\nWrote {args.html}")

    if args.fail_under is not None and result["score"] < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
