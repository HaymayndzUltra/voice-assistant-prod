#!/usr/bin/env python3
"""legacy_config_diff.py

Utility to detect mismatches or duplicates between existing configuration
files and the new central registries (e.g., `config/ports.yaml`).  The
script focuses on YAML files but can be extended.

Current checks implemented:
1. Duplicate port numbers in `config/ports.yaml`.
2. Missing required keys (port, purpose, owner) per entry.
3. If a secondary file is provided via `--legacy-file`, ensures all
   entries exist in the primary registry.

Exit code is non-zero when critical issues are found if
`--fail-on-critical` is passed.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    print("[warning] PyYAML not installed; skipping config diff.")
    sys.exit(0)


REQUIRED_KEYS = {"port", "purpose", "owner"}
CRITICAL_ISSUES: List[str] = []


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_duplicate_ports(entries: List[Dict[str, Any]], source: str) -> None:
    port_counts = Counter(entry.get("port") for entry in entries)
    dups = [p for p, count in port_counts.items() if count > 1]
    if dups:
        CRITICAL_ISSUES.extend([f"Duplicate port {p} in {source}" for p in dups])


def check_required_fields(entries: List[Dict[str, Any]], source: str) -> None:
    for idx, entry in enumerate(entries, start=1):
        missing = REQUIRED_KEYS - entry.keys()
        if missing:
            CRITICAL_ISSUES.append(
                f"Entry {idx} in {source} missing keys: {', '.join(sorted(missing))}"
            )


def compare_legacy(primary_entries: List[Dict[str, Any]], legacy_entries: List[Dict[str, Any]]) -> None:
    primary_ports = {e["port"] for e in primary_entries}
    for entry in legacy_entries:
        if entry["port"] not in primary_ports:
            CRITICAL_ISSUES.append(
                f"Legacy config entry port {entry['port']} not present in primary registry"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare legacy config with new registry.")
    parser.add_argument(
        "--primary-file",
        default="config/ports.yaml",
        help="Path to the primary registry YAML (default: config/ports.yaml)",
    )
    parser.add_argument(
        "--legacy-file",
        help="Optional legacy YAML config to compare against the primary registry",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero when critical issues are detected",
    )
    args = parser.parse_args()

    primary_path = Path(args.primary_file)
    if not primary_path.exists():
        print(f"[error] Primary file {primary_path} not found.")
        sys.exit(1 if args.fail_on_critical else 0)

    primary_entries = load_yaml(primary_path) or []
    if not isinstance(primary_entries, list):
        print(f"[error] Expected list in {primary_path}")
        sys.exit(1)

    check_duplicate_ports(primary_entries, str(primary_path))
    check_required_fields(primary_entries, str(primary_path))

    if args.legacy_file:
        legacy_path = Path(args.legacy_file)
        if not legacy_path.exists():
            print(f"[error] Legacy file {legacy_path} not found.")
        else:
            legacy_entries = load_yaml(legacy_path) or []
            compare_legacy(primary_entries, legacy_entries)

    if CRITICAL_ISSUES:
        print("[critical] Config mismatches detected:")
        for issue in CRITICAL_ISSUES:
            print(f"  - {issue}")
        if args.fail_on_critical:
            sys.exit(1)
    else:
        print("[info] No critical config issues found.")


if __name__ == "__main__":
    main() 