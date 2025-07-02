#!/usr/bin/env python
"""Utility to refactor main-PC agent scripts to use utils.config_parser.

It will:
1. Load `config/startup_config.yaml` and collect all `script_path` entries in
   `main_pc_agents` except `src/core/task_router.py`.
2. For each file it will:
   • Ensure `from utils.config_parser import parse_agent_args` is imported near
     the top (after standard libs / __future__ imports).
   • Insert a single global `_agent_args = parse_agent_args()` right after the
     imports.
   • Replace occurrences of literals like `tcp://localhost:<port>` or
     `"localhost"` host strings with formatted strings that reference the
     parsed args. This is done heuristically via regex.
   • Replace any `*_PORT = <int>` constant which matches the agent's own port
     (as per YAML) with `int(getattr(_agent_args, "port", <default>))`.

Run once from project root:
    python utils/bulk_refactor_agents.py --dry-run   # show changes
    python utils/bulk_refactor_agents.py --apply     # write changes in-place

You can re-run safely; it skips files already containing the import line.
"""
import argparse
import re
import sys
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = PROJECT_ROOT / "config" / "startup_config.yaml"

IMPORT_LINE = "from utils.config_parser import parse_agent_args"
ARGS_LINE = "_agent_args = parse_agent_args()"
TASK_ROUTER_PATH = "src/core/task_router.py"

HOST_RE = re.compile(r"(?<![\w])\"localhost\"|\'localhost\'")
PORT_CONST_RE = re.compile(r"^(\w*_PORT)\s*=\s*(\d+)")
TCP_CONST_RE = re.compile(r"tcp://localhost:(\d+)")


def refactor_file(path: Path, own_port: int, dry_run: bool):
    try:
        text = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        # Fallback with latin-1 and replace errors to handle non-utf8 files gracefully
        text = path.read_text(encoding="latin-1", errors="replace").splitlines()
    modified = False

    # 1. insert import if missing
    if not any(IMPORT_LINE in line for line in text):
        # find last import line index
        try:
            idx = max(i for i, l in enumerate(text) if l.startswith("import") or l.startswith("from "))
        except ValueError:
            idx = 0
        text.insert(idx + 1, IMPORT_LINE)
        modified = True

    # 2. insert args line if missing
    if not any(ARGS_LINE in line for line in text):
        # place after imports block
        idx = max(i for i, l in enumerate(text) if IMPORT_LINE in l)
        text.insert(idx + 1, ARGS_LINE)
        modified = True

    # 3. replace localhost in tcp strings
    for i, line in enumerate(text):
        if "tcp://localhost" in line:
            text[i] = line.replace("tcp://localhost:", 'f"tcp://{_agent_args.host}:")')
            modified = True
        # plain localhost tokens
        if HOST_RE.search(line):
            text[i] = HOST_RE.sub('_agent_args.host', line)
            modified = True
        # tcp string literal inside f""
        m = TCP_CONST_RE.search(line)
        if m:
            port = m.group(1)
            text[i] = TCP_CONST_RE.sub(f'f"tcp://{{_agent_args.host}}:{port}"', line)
            modified = True

        # port constants
        pc = PORT_CONST_RE.match(line)
        if pc and int(pc.group(2)) == own_port:
            const_name = pc.group(1)
            text[i] = f"{const_name} = int(getattr(_agent_args, 'port', {own_port}))"
            modified = True

    if modified and not dry_run:
        path.write_text("\n".join(text), encoding="utf-8")
    return modified


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write changes instead of dry run")
    args = ap.parse_args()
    dry_run = not args.apply

    data = yaml.safe_load(YAML_PATH.read_text())
    modified_files = []
    for agent in data.get("main_pc_agents", []):
        script = agent["script_path"]
        if script == TASK_ROUTER_PATH:
            continue
        path = PROJECT_ROOT / script
        if not path.exists():
            print(f"[WARN] {script} not found, skipping")
            continue
        changed = refactor_file(path, agent["port"], dry_run)
        if changed:
            modified_files.append(script)

    if dry_run:
        print("=== Dry-run complete. Files that would be modified: ===")
    else:
        print("=== Refactor complete. Files modified: ===")
    for f in modified_files:
        print(" -", f)

    print(f"Total: {len(modified_files)} files {'would be' if dry_run else ''} modified")


if __name__ == "__main__":
    main()
