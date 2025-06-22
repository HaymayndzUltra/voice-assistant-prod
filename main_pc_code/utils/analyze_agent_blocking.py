#!/usr/bin/env python3
"""Analyze agent scripts to detect potential blocking calls before their health
service or main loop becomes active. Outputs a Markdown table summarizing
results.

Heuristics based; not perfect but good enough for triage.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "startup_config.yaml"

# Patterns that likely indicate the start of main loop / health activation
ACTIVATION_PATTERNS = [
    re.compile(r"\.run\("),            # Flask/FastAPI/etc.
    re.compile(r"\.start\("),          # agent.start()
    re.compile(r"while\s+True"),        # infinite loop
    re.compile(r"socket\.bind\("),    # raw sockets
    re.compile(r"app\.loop\("),        # generic loop call
]

# Patterns considered blocking if they occur BEFORE activation
BLOCKING_PATTERNS = [
    re.compile(r"connect\("),
    re.compile(r"bind\("),
    re.compile(r"load_model"),
    re.compile(r"TTS\("),
    re.compile(r"time\.sleep\((?:[2-9]|[1-9]\\d)"),  # sleep >=2 sec
    re.compile(r"while\s+True"),
]


def main():
    if not CONFIG_PATH.exists():
        print(f"Cannot find {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    agents = config.get("main_pc_agents", [])

    md_lines = []
    md_lines.append("| Agent Script | Health Service Activation Line | Potential Blocking Calls (before activation) |")
    md_lines.append("|-------------|---------------------------------|----------------------------------------------|")

    total_agents = 0
    agents_with_blocking = 0

    for agent in agents:
        script_path = PROJECT_ROOT / agent["script_path"]
        if not script_path.exists():
            md_lines.append(f"| {script_path} | File not found | - |")
            continue

        lines = script_path.read_text(encoding="utf-8", errors="ignore").splitlines()

        # Locate __main__ block
        try:
            main_idx = next(i for i, l in enumerate(lines) if "__name__" in l and "__main__" in l)
        except StopIteration:
            md_lines.append(f"| {script_path} | Not Found | - |")
            continue

        activation_idx = None
        activation_line = "Not Found"
        for i in range(main_idx, len(lines)):
            l = lines[i]
            if any(p.search(l) for p in ACTIVATION_PATTERNS):
                activation_idx = i
                activation_line = f"L{i+1}: {l.strip()}"
                break

        # Scan for blocking lines before activation
        blocking_calls = []
        search_end = activation_idx if activation_idx is not None else len(lines)
        for i in range(main_idx, search_end):
            l = lines[i]
            if any(p.search(l) for p in BLOCKING_PATTERNS):
                blocking_calls.append(f"L{i+1}: {l.strip()}")

        if blocking_calls:
            agents_with_blocking += 1
        total_agents += 1

        blocking_md = "<br>".join(blocking_calls) if blocking_calls else "-"
        md_lines.append(f"| {script_path} | {activation_line} | {blocking_md} |")

    # Summary
    md_lines.append("\n**Summary:** "
                    f"{agents_with_blocking} of {total_agents} agents contain potential blocking calls "
                    "before their health service activation line.")

    print("\n".join(md_lines))


if __name__ == "__main__":
    main()
