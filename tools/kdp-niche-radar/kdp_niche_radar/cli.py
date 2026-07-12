"""radar CLI — glue the pipeline: license gate -> expand -> fetch -> score -> report.

Usage:
  radar "<niche phrase>" [--out DIR] [--key LICENSE] [--limit N]
  radar --compare a.json b.json

License key comes from --key or the RADAR_LICENSE env var. All work is local;
the only network calls are the polite Amazon fetches and the one license check.
"""
import argparse
import json
import os
import pathlib
import sys
import time

from . import suggest, fetch, score, report, license as lic

PRODUCT = "kdp-niche-radar"


def _run(seed: str, out: pathlib.Path, key: str, limit: int) -> int:
    out.mkdir(parents=True, exist_ok=True)
    if not lic.verify(key, PRODUCT, out / "license.json", now=time.time()):
        print(f"A valid license is required. Buy one at: {lic.PURCHASE_URL}", file=sys.stderr)
        return 2

    keywords = suggest.expand_seeds(seed, limit=limit)
    rows = []
    for position, (kw, breadth) in enumerate(keywords, start=1):
        row = fetch.fetch_keyword(kw)
        row["breadth"] = breadth
        row["position"] = position
        rows.append(row)
    scored = score.score_keywords(rows)

    (out / "report.html").write_text(report.render(scored, seed))
    (out / "run.json").write_text(json.dumps({"seed": seed, "results": scored}, indent=2))
    golden = sum(1 for r in scored if r.get("golden"))
    failed = sum(1 for r in scored if not r.get("ok"))
    print(f"Wrote {out/'report.html'} — {len(scored)} keywords, {golden} golden"
          + (f", {failed} skipped (fetch failed)" if failed else ""))
    return 0


def _compare(path_a: str, path_b: str) -> int:
    run_a = json.loads(pathlib.Path(path_a).read_text())
    run_b = json.loads(pathlib.Path(path_b).read_text())
    diff = report.compare(run_a, run_b)
    print(json.dumps(diff, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="radar", description=__doc__)
    ap.add_argument("seed", nargs="?", help="niche phrase to research")
    ap.add_argument("--out", default=".", help="output directory (default: current dir)")
    ap.add_argument("--key", default=None, help="Gumroad license key (or set RADAR_LICENSE)")
    ap.add_argument("--limit", type=int, default=30, help="max keywords (default 30)")
    ap.add_argument("--compare", nargs=2, metavar=("A.json", "B.json"),
                    help="diff two saved runs instead of researching")
    args = ap.parse_args(argv)

    if args.compare:
        return _compare(*args.compare)
    if not args.seed:
        ap.error("a niche phrase is required (or use --compare)")
    key = args.key or os.environ.get("RADAR_LICENSE", "")
    return _run(args.seed, pathlib.Path(args.out), key, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
