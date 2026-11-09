"""Golden test: the committed lunch-poll example must regenerate byte for byte,
and its readiness story must hold (blocked at r1 and r2, ready at r3 and r4)."""
import os
import pathlib
import subprocess
import sys

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "team-lunch-poll"


def _files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts)


def test_walkthrough_regenerates_committed_outputs(tmp_path):
    out = tmp_path / "output"
    subprocess.run(["bash", str(EX / "walkthrough.sh")], check=True, capture_output=True,
                   env={"PATH": os.environ["PATH"], "SPEC_BENCH_EXAMPLE_OUT": str(out),
                        "PYTHON": sys.executable})
    committed = EX / "output"
    assert _files(committed) == _files(out)
    for name in _files(committed):
        assert (out / name).read_bytes() == (committed / name).read_bytes(), name


def test_readiness_story():
    first = lambda n: (EX / "output" / f"check-r{n}.txt").read_text().splitlines()[1]  # noqa
    assert first(1).startswith("Not ready to build: 15 blocking")
    assert first(2).startswith("Not ready to build: 10 blocking")
    assert first(3).startswith("Ready to build: 0 blocking, 2 warning")
    assert first(4) == "Ready to build: 0 blocking, 0 warning, 0 info, 1 waived"
    r2 = (EX / "output" / "check-r2.txt").read_text()
    assert "Spec Grader): A (100/100)" in r2   # a perfect grade on a spec that is not ready
