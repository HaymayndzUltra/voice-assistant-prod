#!/usr/bin/env python3
"""test_agents_compile.py
Compile all agent scripts referenced in both MainPC and PC2 startup
configuration files to ensure they are free of syntax errors.  This is a
light-weight sanity test that does **not** start the agents; it merely
runs `compile()` on their source code.

Usage:
  python tools/test_agents_compile.py
"""

from pathlib import Path
import yaml
import sys
import ast

CONFIG_FILES = [
    Path("main_pc_code/config/startup_config.yaml"),
    Path("pc2_code/config/startup_config.yaml")
]

def gather_scripts() -> set[Path]:
    scripts: set[Path] = set()
    for cfg_path in CONFIG_FILES:
        if not cfg_path.exists():
            print(f"⚠️  Config missing: {cfg_path}")
            continue
        data = yaml.safe_load(cfg_path.read_text())

        def _traverse(obj):
            if isinstance(obj, dict):
                if "script_path" in obj:
                    scripts.add(Path(obj["script_path"]))
                for v in obj.values():
                    _traverse(v)
            elif isinstance(obj, list):
                for item in obj:
                    _traverse(item)
        _traverse(data)
    return scripts

def compile_script(path: Path) -> tuple[bool, str]:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, "file not found"
    try:
        ast.parse(source)
        return True, "ok"
    except SyntaxError as e:
        return False, f"syntax error: {e}"
    except Exception as e:
        return False, f"error: {e}"

def main():
    scripts = gather_scripts()
    passed = 0
    failed = []

    for script in sorted(scripts):
        ok, msg = compile_script(script)
        if ok:
            passed += 1
            print(f"✅ {script}")
        else:
            failed.append((script, msg))
            print(f"❌ {script}: {msg}")

    total = len(scripts)
    print("\n===== SUMMARY =====")
    print(f"Total scripts : {total}")
    print(f"Compile passed: {passed}")
    print(f"Failed        : {len(failed)}")
    if failed:
        print("\nFailures:")
        for script, reason in failed:
            print(f"  - {script}: {reason}")
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()