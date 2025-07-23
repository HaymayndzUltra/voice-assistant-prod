#!/usr/bin/env python3
"""create_issue_from_backup_scanner.py
Scans for *backup* or _trash_ files that pollute the repo; optionally opens GitHub issues.
"""
import os
import re
import sys
from pathlib import Path
import requests

PATTERN = re.compile(r".*(backup|_trash_).*")


def find_backup_files(root: Path):
    for path in root.rglob("*.py"):
        if PATTERN.search(str(path)):
            yield path


def open_issue(repo: str, token: str, paths):
    url = f"https://api.github.com/repos/{repo}/issues"
    body = "\n".join(f"* {p}" for p in paths)
    data = {"title": "Remove legacy backup files", "body": body, "labels": ["cleanup"]}
    r = requests.post(url, json=data, headers={"Authorization": f"token {token}"})
    r.raise_for_status()


def main():
    root = Path(".")
    backups = list(find_backup_files(root))
    if not backups:
        print("✔ No backup files detected.")
        return
    print("Found backup files:")
    for p in backups:
        print("  ", p)
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("REPO")
    if token and repo:
        open_issue(repo, token, backups)
        print("GitHub issue created.")
    else:
        print("Set GITHUB_TOKEN and REPO env vars to auto-open an issue.")


if __name__ == "__main__":
    main()