#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


REPO_ROOT = Path("/workspace").resolve()
REPORT_DIR = REPO_ROOT / ".cleanup-report"
SOFT_REVIEW = REPORT_DIR / "soft_review.txt"
HARD_DELETE = REPORT_DIR / "hard_delete.txt"
BRANCH_NAME = "cursor/auto-delete-reviewed-files"


SAFE_DIR_TOKENS = [
    "/build/",
    "/dist/",
    "/out/",
    "/target/",
    "/__pycache__/",
    "/node_modules/",
    "/.pytest_cache/",
    "/.mypy_cache/",
    "/.ruff_cache/",
    "/.cache/",
    "/logs/",
]

SAFE_DIR_NAMES = {
    "build",
    "dist",
    "out",
    "target",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "logs",
}

SAFE_FILE_EXT_ALWAYS = {
    # always safe regardless of location
    ".log",
    ".tmp",
    ".bak",
    ".swp",
    ".swo",
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".tsbuildinfo",
}

SAFE_FILE_EXT_IF_UNDER_SAFE_DIR = {
    # safe only when under a safe dir (cache/build/output)
    ".so",
    ".a",
    ".dll",
    ".exe",
    ".map",
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".7z",
}

BACKUP_NAME_PATTERNS = [
    r"~$",
    r"\.old$",
    r"\.orig$",
]


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(args, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


def parse_soft_review(path: Path) -> List[Tuple[Path, int]]:
    items: List[Tuple[Path, int]] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        # Expect format: "path\tScore"
        parts = s.split("\t")
        rel = parts[0]
        score = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else -1
        p = (REPO_ROOT / rel).resolve()
        items.append((p, score))
    return items


def is_under_safe_dir(rel_posix: str) -> bool:
    low = ("/" + rel_posix.strip("/")).lower()
    return any(tok in low for tok in SAFE_DIR_TOKENS)


def is_safe_dir(path: Path) -> bool:
    # directory itself is safe iff it's a known cache/build/logs path by name or token
    if path.is_file():
        return False
    rel = path.relative_to(REPO_ROOT).as_posix()
    if path.name in SAFE_DIR_NAMES:
        return True
    return is_under_safe_dir(rel)


def is_safe_file(path: Path) -> bool:
    if path.is_dir():
        return False
    name_lower = path.name.lower()
    rel = path.relative_to(REPO_ROOT).as_posix()
    # Always safe extensions anywhere
    for ext in SAFE_FILE_EXT_ALWAYS:
        if name_lower.endswith(ext):
            return True
    # Backup-like names
    for pat in BACKUP_NAME_PATTERNS:
        if re.search(pat, name_lower):
            return True
    # Under safe dir with artifact-ish extension
    if is_under_safe_dir(rel):
        for ext in SAFE_FILE_EXT_IF_UNDER_SAFE_DIR:
            if name_lower.endswith(ext):
                return True
    return False


def select_safe(items: List[Tuple[Path, int]]) -> List[Path]:
    selected: List[Path] = []
    for p, _ in items:
        try:
            if not p.exists():
                continue
            if p == REPORT_DIR or REPORT_DIR in p.parents:
                continue
            if any(seg == ".git" for seg in p.parts):
                continue
            if p.is_dir():
                if is_safe_dir(p):
                    selected.append(p)
            else:
                if is_safe_file(p):
                    selected.append(p)
        except Exception:
            continue
    # Sort by path length descending so files inside dirs are first to avoid issues, but we'll use shutil.rmtree anyway
    selected = sorted(set(selected), key=lambda x: (x.is_file(), x.as_posix()))
    return selected


def ensure_branch(branch: str) -> None:
    code, out, _ = run_cmd(["git", "rev-parse", "--verify", branch])
    if code == 0:
        run_cmd(["git", "checkout", branch])
        return
    run_cmd(["git", "checkout", "-b", branch])


def delete_paths(paths: Iterable[Path]) -> Tuple[int, int]:
    files = 0
    dirs = 0
    for p in paths:
        try:
            if p.is_dir():
                shutil.rmtree(p)
                dirs += 1
            else:
                p.unlink(missing_ok=True)
                files += 1
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"WARN: failed to delete {p}: {e}")
    return files, dirs


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    soft_items = parse_soft_review(SOFT_REVIEW)
    safe = select_safe(soft_items)

    # Write hard_delete.txt (paths only)
    with HARD_DELETE.open("w", encoding="utf-8") as f:
        for p in safe:
            f.write(p.relative_to(REPO_ROOT).as_posix() + "\n")

    # Create/switch to branch and apply deletions
    ensure_branch(BRANCH_NAME)

    # Make sure report dir exists on branch
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    files_deleted, dirs_deleted = delete_paths(safe)

    # Stage report and deletions
    run_cmd(["git", "add", ".cleanup-report/hard_delete.txt"])
    # Stage deletions (use "git add -A" to catch removals)
    run_cmd(["git", "add", "-A"])

    # Commit if there are changes
    code, out, _ = run_cmd(["git", "status", "--porcelain"])
    if out.strip():
        msg = f"chore(cleanup): auto-delete reviewed cache/log/build artifacts (files={files_deleted}, dirs={dirs_deleted})"
        run_cmd(["git", "commit", "-m", msg])
        # Diff preview: show one-line and stat
        run_cmd(["git", "--no-pager", "show", "--stat", "--oneline", "HEAD", "|", "cat"])  # won't actually pipe via run_cmd
        # Instead, just print the diff preview here
        c1, show_out, _ = run_cmd(["git", "--no-pager", "show", "--stat", "--oneline", "HEAD"])
        print(show_out)
        # Save preview too
        (REPORT_DIR / "commit_diff_preview.txt").write_text(show_out, encoding="utf-8")
    else:
        print("No changes to commit.")

    # Print summary counts for the caller
    print(f"safe_to_delete_count={len(safe)}")
    print(f"files_deleted={files_deleted}")
    print(f"dirs_deleted={dirs_deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

