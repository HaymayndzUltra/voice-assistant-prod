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


def parse_soft_review(path: Path) -> List[Tuple[str, int]]:
    items: List[Tuple[str, int]] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.rstrip()
        if not s:
            continue
        # Accept either tab-delimited or whitespace-delimited with trailing integer score
        rel: str = ""
        score: int = -1
        if "\t" in s:
            parts = s.split("\t")
            rel = parts[0].strip()
            if len(parts) > 1 and parts[1].strip().isdigit():
                score = int(parts[1].strip())
        else:
            m = re.match(r"^(?P<path>.*?)\s+(?P<score>\d+)$", s)
            if m:
                rel = m.group("path").strip()
                score = int(m.group("score"))
            else:
                rel = s.strip()
        if not rel:
            continue
        # Normalize accidental command echoes in file (defensive)
        if rel.endswith("| cat") or rel.startswith("sed "):
            continue
        items.append((rel, score))
    return items


def is_under_safe_dir(rel_posix: str) -> bool:
    low = ("/" + rel_posix.strip("/")).lower()
    # token presence
    if any(tok in low for tok in SAFE_DIR_TOKENS):
        return True
    # segment-based presence (handles trailing end like .../__pycache__)
    segments = [seg for seg in rel_posix.replace("\\", "/").split("/") if seg]
    return any(seg in SAFE_DIR_NAMES for seg in segments)


def is_safe_dir(path: Path) -> bool:
    # directory itself is safe iff it's a known cache/build/logs path by name or token
    if path.is_file():
        return False
    rel = path.relative_to(REPO_ROOT).as_posix()
    # If any segment is a safe dir name → safe
    if any(seg in SAFE_DIR_NAMES for seg in Path(rel).parts):
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
    # Under safe dir → consider safe even without special ext (e.g., node_modules/*)
    if is_under_safe_dir(rel):
        for ext in SAFE_FILE_EXT_IF_UNDER_SAFE_DIR:
            if name_lower.endswith(ext):
                return True
        # also allow any file under known cache dirs
        return True
    return False


def load_keeplist() -> List[str]:
    candidates = [REPO_ROOT / "keeplist.txt", REPO_ROOT / ".keeplist", REPO_ROOT / "KEEP.txt"]
    for p in candidates:
        if p.exists():
            lines: List[str] = []
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                lines.append(s)
            return lines
    return []


def in_keeplist(path: Path, keeplist: List[str]) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    for rule in keeplist:
        if rel == rule.strip("/"):
            return True
        if rule.endswith("/") and rel.startswith(rule.rstrip("/")):
            return True
        if Path(rel).match(rule):
            return True
        if rule and rule in rel:
            return True
    return False


def path_string_is_safe(rel: str) -> bool:
    low = rel.strip()
    if not low:
        return False
    # Under safe dir by tokens/segments
    if is_under_safe_dir(rel):
        return True
    # Always safe extensions anywhere
    name_lower = Path(rel).name.lower()
    for ext in SAFE_FILE_EXT_ALWAYS:
        if name_lower.endswith(ext):
            return True
    # Backup-like names
    for pat in BACKUP_NAME_PATTERNS:
        if re.search(pat, name_lower):
            return True
    return False


def select_safe(items: List[Tuple[str, int]]) -> Tuple[List[str], List[Path]]:
    safe_strings: List[str] = []
    existing_selected: List[Path] = []
    keeplist = load_keeplist()
    for rel, _ in items:
        try:
            if not rel:
                continue
            # Skip report dir entries
            if rel.startswith(".cleanup-report/"):
                continue
            # Guard keeplist
            p_abs = (REPO_ROOT / rel).resolve()
            if in_keeplist(p_abs, keeplist):
                continue
            if path_string_is_safe(rel):
                safe_strings.append(rel)
                # Track existing entries for deletion
                if p_abs.exists():
                    if p_abs == REPORT_DIR or REPORT_DIR in p_abs.parents:
                        continue
                    if any(seg == ".git" for seg in p_abs.parts):
                        continue
                    if p_abs.is_dir():
                        if is_safe_dir(p_abs):
                            existing_selected.append(p_abs)
                    else:
                        if is_safe_file(p_abs):
                            existing_selected.append(p_abs)
        except Exception:
            continue
    # De-dup and stable sort
    safe_strings = sorted(set(safe_strings))
    existing_selected = sorted(set(existing_selected), key=lambda x: (x.as_posix().count("/"), x.is_file(), x.as_posix()))
    return safe_strings, existing_selected


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
    safe_strings, safe_existing = select_safe(soft_items)

    # Write hard_delete.txt (paths only)
    with HARD_DELETE.open("w", encoding="utf-8") as f:
        for rel in safe_strings:
            f.write(rel + "\n")

    # Create/switch to branch and apply deletions
    ensure_branch(BRANCH_NAME)

    # Make sure report dir exists on branch
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    files_deleted, dirs_deleted = delete_paths(safe_existing)

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
    print(f"safe_to_delete_count={len(safe_strings)}")
    print(f"files_deleted={files_deleted}")
    print(f"dirs_deleted={dirs_deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

