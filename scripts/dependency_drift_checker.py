#!/usr/bin/env python3
"""dependency_drift_checker.py
Compare dependency versions across requirements files in the monorepo.
By default compares main_pc_code/requirements.txt vs pc2_code/requirements.txt.
Exits 1 if drift detected unless --allow-drift is set.
"""
import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

REQ_RE = re.compile(r"^([A-Za-z0-9_.-]+)([<>=!~].*)?$")


def parse_req(path: Path) -> dict[str, str]:
    pkg_versions = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = REQ_RE.match(line)
        if m:
            pkg = m.group(1).lower()
            spec = m.group(2) or ""
            pkg_versions[pkg] = spec
    return pkg_versions


def main(argv: list[str]):
    p = argparse.ArgumentParser()
    p.add_argument("--files", nargs="*", default=[
        "main_pc_code/requirements.txt",
        "pc2_code/requirements.txt",
    ])
    p.add_argument("--allow-drift", action="store_true")
    args = p.parse_args(argv)

    pkg_map: defaultdict[str, dict[str, str]] = defaultdict(dict)
    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"⚠ requirements file missing: {path}")
            continue
        for pkg, spec in parse_req(path).items():
            pkg_map[pkg][path.name] = spec

    drift = {pkg: specs for pkg, specs in pkg_map.items() if len(set(specs.values())) > 1}
    if drift:
        print("Dependency drift detected:\n")
        for pkg, specs in sorted(drift.items()):
            print(f"{pkg}:")
            for file, spec in specs.items():
                print(f"  {file}: {spec or '(unconstrained)'}")
        if not args.allow_drift:
            sys.exit(1)
    else:
        print("✔ No dependency drift found.")


if __name__ == "__main__":
    main(sys.argv[1:])