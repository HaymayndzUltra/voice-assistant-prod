#!/usr/bin/env python3
"""dep_freeze_compare.py

Compare current Python environment package versions against a baseline
freeze file (e.g., main branch) and report drifts.

Steps:
1. Capture current environment using `pip list --format=freeze`.
2. Load baseline requirement list (default: requirements_main.txt).
3. Report added, removed, or version-changed packages.

Exit code 1 if drift detected and `--fail-on-drift` flag is provided.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict


def pip_freeze() -> Dict[str, str]:
    result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=freeze"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print("[error] Failed to run pip list", file=sys.stderr)
        sys.exit(1)
    packages: Dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "==" in line:
            pkg, ver = line.strip().split("==", 1)
            packages[pkg.lower()] = ver
    return packages


def load_baseline(path: Path) -> Dict[str, str]:
    if not path.exists():
        print(f"[warning] Baseline file {path} not found. Assuming empty baseline.")
        return {}
    baseline: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "==" in line and not line.startswith("#"):
            pkg, ver = line.strip().split("==", 1)
            baseline[pkg.lower()] = ver
    return baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect dependency drift versus a baseline freeze file.")
    parser.add_argument("--baseline", default="requirements_main.txt", help="Path to baseline requirements freeze file")
    parser.add_argument("--fail-on-drift", action="store_true", help="Exit with status 1 if drift found")
    args = parser.parse_args()

    current = pip_freeze()
    baseline = load_baseline(Path(args.baseline))

    added = {pkg: ver for pkg, ver in current.items() if pkg not in baseline}
    removed = {pkg: ver for pkg, ver in baseline.items() if pkg not in current}
    changed = {
        pkg: (baseline[pkg], current[pkg])
        for pkg in current.keys() & baseline.keys()
        if baseline[pkg] != current[pkg]
    }

    if not (added or removed or changed):
        print("[info] No dependency drift detected.")
    else:
        print("[drift] Dependency differences detected:")
        if added:
            print("  + Added:")
            for pkg, ver in added.items():
                print(f"    - {pkg}=={ver}")
        if removed:
            print("  - Removed:")
            for pkg, ver in removed.items():
                print(f"    - {pkg}=={ver}")
        if changed:
            print("  * Version changed:")
            for pkg, (old, new) in changed.items():
                print(f"    - {pkg}: {old} → {new}")
        if args.fail_on_drift:
            sys.exit(1)


if __name__ == "__main__":
    main() 