#!/usr/bin/env python3
"""
patch_dockerfiles.py
====================
Scans all Dockerfiles under AI_System_Monorepo/docker and injects a shared base-layer
that installs `AI_System_Monorepo/requirements.common.txt` to maximise layer caching.

Patch logic (idempotent):
1. If the Dockerfile already contains the marker `# -- common-req-layer`, skip.
2. Otherwise, inject the following snippet **after the first FROM line**::

    # -- common-req-layer (auto-generated)
    ARG COMMON_REQ=/home/haymayndz/AI_System_Monorepo/requirements.common.txt
    COPY ${COMMON_REQ} /tmp/
    RUN pip install --no-cache-dir -r /tmp/requirements.common.txt

3. Save the modified Dockerfile in-place, creating a timestamped backup
   alongside (e.g. `Dockerfile.bak.20250806T123000`).

Usage::

    python3 scripts/patch_dockerfiles.py  # dry-run summary
    python3 scripts/patch_dockerfiles.py --apply  # actually write changes

Requirements: Python ≥3.8
"""
from __future__ import annotations
import argparse, datetime as _dt, hashlib, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKER_DIR = ROOT / "docker"
WORKSPACE_PATH = "/home/haymayndz/AI_System_Monorepo"
MARKER = "# -- common-req-layer"
INJECT_SNIPPET = f"""{MARKER}
ARG COMMON_REQ={WORKSPACE_PATH}/requirements.common.txt
COPY ${{COMMON_REQ}} /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.common.txt
"""


def patch_dockerfile(path: Path, apply: bool = False) -> bool:
    txt = path.read_text()
    if MARKER in txt:
        return False  # already patched
    lines = txt.splitlines()
    # find first FROM instruction
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith("from "):
            inject_idx = idx + 1
            break
    else:
        print(f"⚠️  No FROM found in {path}, skipping", file=sys.stderr)
        return False
    new_lines = lines[:inject_idx] + [INJECT_SNIPPET.rstrip()] + lines[inject_idx:]
    if apply:
        backup = path.with_suffix(path.suffix + f".bak.{_dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}")
        path.rename(backup)
        path.write_text("\n".join(new_lines) + "\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="Patch Dockerfiles for shared requirements layer")
    parser.add_argument("--apply", action="store_true", help="Write changes instead of dry-run")
    args = parser.parse_args()

    modified = 0
    for dockerfile in DOCKER_DIR.rglob("Dockerfile"):
        if patch_dockerfile(dockerfile, apply=args.apply):
            modified += 1
            action = "Patched" if args.apply else "Would patch"
            print(f"{action}: {dockerfile}")
    print(f"{'Modified' if args.apply else 'Would modify'} {modified} Dockerfiles")


if __name__ == "__main__":
    main()
