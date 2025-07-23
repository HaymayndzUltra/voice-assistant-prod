#!/usr/bin/env python3
"""legacy_code_audit.py

Scan the repository for potential legacy/conflicting code or configuration
that may break upcoming refactors.  
Outputs findings to a JSON file (default: legacy_report.json) so the CI
Guardrails job can upload it as an artefact or fail the workflow if
critical issues are found.

Key checks implemented (extend as needed):
1. Hard-coded ports (e.g., "tcp://*")
2. Bare or broad exception handlers (``except:`` or ``except Exception``)
3. Deprecated / discouraged APIs (``asyncio.get_event_loop``)
4. Files living outside the approved top-level directories

If the environment variable ``GITHUB_TOKEN`` is present and the flag
``--create-issues`` is passed, the script will automatically create
GitHub issues with label **legacy-conflict** summarising each file’s
problems.

Usage::

    python automation/legacy_code_audit.py \
        --output legacy_report.json --fail-on-critical --create-issues

This file should remain dependency-free (std-lib only) so it runs early
in CI without extra installs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Patterns to flag -----------------------------------------------------------
PATTERNS: List[Tuple[str, str]] = [
    (r"tcp://\*|tcp://127\.0\.0\.1", "Hard-coded TCP wildcard or localhost port"),
    (r"except\s*:\s*$", "Bare except handler"),
    (r"except\s+Exception\s*:\s*$", "Broad 'except Exception' handler"),
    (r"asyncio\.get_event_loop\(", "Deprecated asyncio.get_event_loop API"),
    # Add more regex patterns + descriptions here as needed.
]

APPROVED_TOP_LEVEL_DIRS = {
    "main_pc_code",
    "pc2_code",
    "common_utils",
    "automation",
    "events",
    "linters",
    "config",
    "tests",
    ".github",
}

CRITICAL_TYPES = {
    "Hard-coded TCP wildcard or localhost port",
    "Bare except handler",
}

# GitHub utilities -----------------------------------------------------------

def _run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    """Run command and capture output (helper)."""
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def create_issue(repo: str, title: str, body: str, labels: List[str] | None = None) -> None:
    """Lightweight GitHub issue creator via gh CLI (requires gh installed)."""
    labels_arg = ["--label", ",".join(labels)] if labels else []
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body",
        body,
        *labels_arg,
    ]
    res = _run(cmd)
    if res.returncode != 0:
        print(f"[warning] Failed to create GitHub issue: {res.stderr.strip()}", file=sys.stderr)


# Scanner --------------------------------------------------------------------

def scan_file(path: Path) -> List[Dict[str, str]]:
    """Return list of findings as dicts for a single file."""
    findings: List[Dict[str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        print(f"[warning] Could not read {path}: {exc}", file=sys.stderr)
        return findings

    for regex, desc in PATTERNS:
        pattern = re.compile(regex, re.MULTILINE)
        for match in pattern.finditer(text):
            # Determine 1-based line number
            line_no = text[: match.start()].count("\n") + 1
            snippet = text.splitlines()[line_no - 1].strip()
            findings.append(
                {
                    "line": line_no,
                    "type": desc,
                    "snippet": snippet,
                }
            )
    return findings


def is_outside_approved(path: Path) -> bool:
    """True if file is at a top-level directory that is NOT approved."""
    parts = path.parts
    if len(parts) < 2:
        return False
    return parts[0] not in APPROVED_TOP_LEVEL_DIRS


def walk_repo(root: Path) -> Dict[str, List[Dict[str, str]]]:
    """Traverse repo and collect findings."""
    results: Dict[str, List[Dict[str, str]]] = {}
    for file_path in root.rglob("*.*"):
        if not file_path.is_file():
            continue
        if file_path.suffix in {".py", ".txt", ".md", ".yml", ".yaml", ".ini"}:
            file_findings = scan_file(file_path)
            if is_outside_approved(file_path):
                file_findings.append(
                    {
                        "line": 1,
                        "type": "File located outside approved directories",
                        "snippet": f"Top-level dir: {file_path.parts[0]}",
                    }
                )
            if file_findings:
                results[str(file_path)] = file_findings
    return results


# Main -----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit repo for legacy patterns.")
    parser.add_argument("--output", default="legacy_report.json", help="Path to JSON report file")
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero if critical findings exist",
    )
    parser.add_argument(
        "--create-issues",
        action="store_true",
        help="Automatically create GitHub issues for findings (requires gh CLI & GITHUB_TOKEN)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent  # repo root assumption
    findings_by_file = walk_repo(root)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(findings_by_file, indent=2))
    print(f"[info] Report written to {output_path.relative_to(Path.cwd())}")

    # Summarise
    total_findings = sum(len(v) for v in findings_by_file.values())
    print(f"[summary] {len(findings_by_file)} files with {total_findings} findings.")

    critical = [
        (file, f)
        for file, issues in findings_by_file.items()
        for f in issues
        if f["type"] in CRITICAL_TYPES
    ]
    if critical:
        print(f"[critical] {len(critical)} critical findings detected.", file=sys.stderr)

    # GitHub issue creation
    if args.create_issues and os.getenv("GITHUB_TOKEN"):
        repo = os.getenv("REPO") or "origin"  # fallback; expects REPO env var
        for file, issues in findings_by_file.items():
            body_lines = [f"### Findings in `{file}`\n"]
            for i in issues:
                body_lines.append(f"* Line {i['line']}: **{i['type']}** – `{i['snippet']}`")
            create_issue(repo, f"Legacy conflict: {Path(file).name}", "\n".join(body_lines), ["legacy-conflict"])

    if args.fail_on_critical and critical:
        sys.exit(1)


if __name__ == "__main__":
    main() 