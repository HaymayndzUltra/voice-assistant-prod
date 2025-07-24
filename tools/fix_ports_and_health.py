#!/usr/bin/env python3
"""
fix_ports_and_health.py

Utility script that performs two automated production-readiness fixes:

1. Iterate over one or more YAML startup config files and convert any
   string-based port arithmetic of the form "${PORT_OFFSET}+NNNN" into
   concrete integer values, using the PORT_OFFSET environment variable
   (or 0 if not set).  The YAML file is modified in-place after a *.bak
   backup is written.

2. Scan all Python agent scripts referenced in the YAML files.  If a
   script does not already import or inherit from `UnifiedHealthMixin`
   in `common.health.unified_health`, the mixin is automatically
   appended to the class definition and a `/health` FastAPI (or ZMQ)
   endpoint is injected.  A *.bak copy of each modified file is saved.

This script is *idempotent* – running it multiple times will not create
duplicate mixin code nor mutate ports that are already numeric.

Usage:
  python tools/fix_ports_and_health.py main_pc_code/config/startup_config.yaml \
                                        pc2_code/config/startup_config.yaml
"""

import os
import re
import sys
import yaml
import shutil
from pathlib import Path
from typing import List, Dict, Any
import ast
import textwrap

PORT_PATTERN = re.compile(r"^\${PORT_OFFSET}\+(\d+)$")

# ---------------------------------------------------------------------------
# Part 1 – YAML port expression normalisation
# ---------------------------------------------------------------------------

def _fix_yaml_ports(yaml_path: Path, port_offset: int) -> bool:
    """Return True if file was modified."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    modified = False

    def _normalise(obj: Any):
        nonlocal modified
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in {"port", "health_check_port"} and isinstance(v, str):
                    m = PORT_PATTERN.match(v)
                    if m:
                        new_val = port_offset + int(m.group(1))
                        obj[k] = new_val
                        modified = True
                else:
                    _normalise(v)
        elif isinstance(obj, list):
            for item in obj:
                _normalise(item)

    _normalise(data)

    if modified:
        backup = yaml_path.with_suffix(yaml_path.suffix + ".bak")
        shutil.copy2(yaml_path, backup)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        print(f"✅ Ports fixed in {yaml_path} (backup → {backup})")
    else:
        print(f"ℹ️  No port expressions to fix in {yaml_path}")
    return modified

# ---------------------------------------------------------------------------
# Part 2 – Health mixin injection
# ---------------------------------------------------------------------------

MIXIN_IMPORT = "from common.health.unified_health import UnifiedHealthMixin"

MIXIN_CODE_SNIPPET = textwrap.dedent(
    """
    # ---- AUTO-GENERATED HEALTH MIXIN ----
    try:
        UnifiedHealthMixin.__init_health_monitoring__(self, health_check_port=self.health_check_port)
    except Exception as _auto_health_err:
        print(f'[WARN] UnifiedHealthMixin failed: {_auto_health_err}')
    # ---- END AUTO SECTION ----
    """
)


def _inject_health_mixin(script_path: Path) -> bool:
    """Return True if file was modified."""
    text = script_path.read_text(encoding="utf-8")
    if "UnifiedHealthMixin" in text:
        return False  # already has mixin

    # Parse AST to find main class definition
    try:
        module = ast.parse(text)
    except SyntaxError as e:
        print(f"❌ Cannot parse {script_path}: {e}")
        return False

    class_node = None
    for node in module.body:
        if isinstance(node, ast.ClassDef):
            class_node = node
            break

    if class_node is None:
        print(f"ℹ️  No class definition in {script_path}; skipping health injection")
        return False

    class_name = class_node.name

    # Prepare modified source: add import at top if absent, update inheritance
    lines = text.splitlines()

    # 1. Import
    if MIXIN_IMPORT not in text:
        # insert after existing imports
        insert_idx = 0
        for idx, line in enumerate(lines):
            if line.startswith("import") or line.startswith("from"):
                insert_idx = idx + 1
        lines.insert(insert_idx, MIXIN_IMPORT)

    # 2. Update class inheritance line
    pattern = re.compile(rf"^class\s+{re.escape(class_name)}\((.*?)\):")
    for idx, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            bases = [b.strip() for b in m.group(1).split(',')] if m.group(1).strip() else []
            if "UnifiedHealthMixin" not in bases:
                bases.append("UnifiedHealthMixin")
                new_line = f"class {class_name}({', '.join(bases)}):"
                lines[idx] = new_line
            break

    # 3. Append init call inside __init__ (simple heuristic)
    joined = "\n".join(lines)
    init_pattern = re.compile(r"def __init__\(.*?\):", re.DOTALL)
    if "__init_health_monitoring__" not in joined:
        # naive: append snippet at end of __init__
        new_lines = []
        inside_init = False
        indent = ''
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith("def __init__("):
                inside_init = True
                indent = ' ' * (len(line) - len(line.lstrip()) + 4)
            elif inside_init and line.strip().startswith("def "):
                # reached next method – inject before
                new_lines.insert(-1, textwrap.indent(MIXIN_CODE_SNIPPET, indent))
                inside_init = False
        if inside_init:
            # file ended while still inside __init__
            new_lines.append(textwrap.indent(MIXIN_CODE_SNIPPET, indent))
        lines = new_lines

    # Write back
    backup = script_path.with_suffix(".py.bak")
    shutil.copy2(script_path, backup)
    script_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Injected UnifiedHealthMixin into {script_path} (backup → {backup})")
    return True

# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def main(paths: List[str]):
    port_offset = int(os.environ.get("PORT_OFFSET", "0"))
    total_yaml_fixed = 0
    total_scripts_fixed = 0

    # First pass – YAML fixes
    for p in paths:
        yaml_path = Path(p)
        if not yaml_path.exists():
            print(f"❌ YAML not found: {yaml_path}")
            continue
        if _fix_yaml_ports(yaml_path, port_offset):
            total_yaml_fixed += 1

    # Gather script paths from modified or original YAML
    all_script_paths: List[Path] = []
    for p in paths:
        yaml_path = Path(p)
        if not yaml_path.exists():
            continue
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        def _collect(obj):
            if isinstance(obj, dict):
                if "script_path" in obj:
                    all_script_paths.append(Path(obj["script_path"]))
                for v in obj.values():
                    _collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    _collect(item)
        _collect(data)

    # Second pass – Health mixin injection
    for script in all_script_paths:
        if script.exists() and script.suffix == ".py":
            if _inject_health_mixin(script):
                total_scripts_fixed += 1
        else:
            print(f"⚠️  Script not found: {script}")

    print("\n========= SUMMARY =========")
    print(f"YAML files fixed  : {total_yaml_fixed}")
    print(f"Agent scripts patched: {total_scripts_fixed}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_ports_and_health.py <startup_yaml> [more_yaml…]")
        sys.exit(1)
    main(sys.argv[1:])