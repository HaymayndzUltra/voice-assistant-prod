#!/usr/bin/env python3
"""extract_todos_to_issues.py
Scans the repository for TODO or FIXME comments.
If `GITHUB_TOKEN` and `REPO` ("owner/repo") environment variables are set, it will open issues through the GitHub API.
Otherwise it prints a CSV to stdout.
"""
import os
import re
import csv
import sys
import json
import requests
from pathlib import Path

TODO_RE = re.compile(r"#\s*(TODO|FIXME)[:\s]*(.*)", re.IGNORECASE)


def collect_todos(root: Path):
    for path in root.rglob("*.py"):
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                m = TODO_RE.search(line)
                if m:
                    yield {
                        "file": str(path),
                        "line": i,
                        "text": m.group(2).strip() or "(no text)",
                    }
        except Exception:
            continue


def open_github_issue(repo: str, token: str, todo: dict):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = {
        "title": f"TODO in {Path(todo['file']).name}:{todo['line']}",
        "body": f"Found TODO:\n\n```\n{todo['text']}\n```\n\nFile: `{todo['file']}` line {todo['line']}",
        "labels": ["auto-todo"]
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()


def main():
    root = Path(".").resolve()
    todos = list(collect_todos(root))
    if not todos:
        print("✔ No TODOs found.")
        return

    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("REPO")
    if token and repo:
        for todo in todos:
            open_github_issue(repo, token, todo)
        print(f"Opened {len(todos)} issues in {repo}.")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=["file", "line", "text"])
        writer.writeheader()
        writer.writerows(todos)


if __name__ == "__main__":
    main()