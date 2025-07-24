#!/usr/bin/env python3
"""coverage_enforcer.py
Runs pytest with coverage; fails if total < --min (default 50).
Requires pytest & pytest-cov.
"""
import subprocess
import argparse
import sys


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--min", type=float, default=50.0, help="Minimum coverage percentage")
    p.add_argument("--args", nargs=argparse.REMAINDER, help="Additional pytest args")
    args = p.parse_args(argv)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=.",
        "--cov-report=term-missing",
    ] + (args.args or [])
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)

    # Parse coverage from last line of output saved in .coverage (cov plugin prints to stdout too)
    # Simplistic: run `coverage report -m` and parse total.
    proc = subprocess.run(["coverage", "report"], capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        if line.strip().startswith("TOTAL"):
            parts = line.split()
            percent = float(parts[-1].rstrip("%"))
            print(f"Total coverage: {percent}%")
            if percent < args.min:
                print(f"❌ Coverage {percent}% < {args.min}%")
                sys.exit(1)
            break


if __name__ == "__main__":
    main(sys.argv[1:])