#!/usr/bin/env python3
"""check_port_conflicts.py
Detects duplicate hard-coded TCP ports across the codebase.
1. Walk *.py files looking for literal "tcp://" strings with numeric ports.
2. Emits a table of port → files.
3. Returns exit code 1 if any port is referenced by > `--max-count` files (default 1).

Usage:
    python check_port_conflicts.py [--root <path>] [--max-count 1]
"""
import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

PORT_RE = re.compile(r"tcp://[^:\"]+:([0-9]{3,6})")


def scan_ports(root: Path) -> dict[str, set[Path]]:
    mapping: dict[str, set[Path]] = defaultdict(set)
    for py_file in root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in PORT_RE.finditer(text):
            mapping[match.group(1)].add(py_file)
    return mapping


def main(argv: list[str]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root to scan")
    parser.add_argument("--max-count", type=int, default=1, help="Max allowed occurrences per port")
    args = parser.parse_args(argv)
    mapping = scan_ports(Path(args.root).resolve())
    duplicates = {p: files for p, files in mapping.items() if len(files) > args.max_count}
    if duplicates:
        print("Duplicate ports detected:")
        for port, files in duplicates.items():
            print(f"  {port}: {len(files)} files")
            for f in files:
                print(f"    - {f.relative_to(Path(args.root))}")
        sys.exit(1)
    else:
        print("✔ No port conflicts detected.")


if __name__ == "__main__":
    main(sys.argv[1:])