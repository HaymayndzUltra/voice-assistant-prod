#!/usr/bin/env python3
import csv, argparse, subprocess, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="commentout_candidates.csv", help="Path to commentout_candidates.csv")
    ap.add_argument("--apply", action="store_true", help="Execute yq commands (write changes)")
    ap.add_argument("--dry-run", action="store_true", help="Print only (no changes). Default if not --apply.")
    args = ap.parse_args()

    path = Path(args.csv)
    if not path.exists():
        print(f"ERROR: CSV not found: {path}", file=sys.stderr); sys.exit(2)

    cmds = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if "yq_suggest" not in r.fieldnames:
            print("ERROR: CSV missing yq_suggest column.", file=sys.stderr); sys.exit(2)
        for row in r:
            cmd = (row.get("yq_suggest") or "").strip()
            if cmd: cmds.append(cmd)

    if not cmds:
        print("No yq suggestions found. Nothing to do."); return

    # Always print commands
    for cmd in cmds: print(cmd)

    if args.apply and not args.dry_run:
        print("\n--- Executing commands ---", flush=True)
        for i, cmd in enumerate(cmds, 1):
            print(f"[{i}/{len(cmds)}] {cmd}")
            rc = subprocess.call(cmd, shell=True)
            if rc != 0:
                print(f"WARNING: command returned {rc}: {cmd}", file=sys.stderr)

if __name__ == "__main__":
    main()