#!/usr/bin/env python3
"""refactor_duplicate_agents.py
Helps identify duplicate agent implementations across MainPC & PC2.
Outputs groups of files that share the same basename (e.g., tiered_responder.py).
"""
from pathlib import Path
from collections import defaultdict

ROOT = Path(".").resolve()


def main():
    files_by_name: dict[str, list[Path]] = defaultdict(list)
    for path in ROOT.rglob("*.py"):
        if "agents" in path.parts:
            files_by_name[path.name].append(path)
    for name, paths in sorted(files_by_name.items()):
        if len(paths) > 1:
            print(f"# Duplicate agent: {name} ({len(paths)} copies)")
            for p in paths:
                print(f"  - {p.relative_to(ROOT)}")
            print()


if __name__ == "__main__":
    main()