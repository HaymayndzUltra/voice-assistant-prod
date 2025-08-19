#!/usr/bin/env python3
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


REPO_ROOT = Path("/workspace").resolve()
REPORT_DIR = REPO_ROOT / ".cleanup-report"

PASS_MAX = 5
SOFT_THRESHOLD = 50

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

BACKUP_NAME_PATTERNS = [r"~$", r"\.old$", r"\.orig$"]


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(args, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_report_dir() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def git_fetch() -> None:
    run_cmd(["git", "fetch", "origin", "--prune"])


def create_pass_branch(pass_index: int, base_ref: str) -> str:
    branch = f"cursor/auto-cleanup-pass-{pass_index:02d}"
    # checkout branch at base_ref
    run_cmd(["git", "checkout", "-B", branch, base_ref])
    return branch


def get_head_commit() -> str:
    code, out, _ = run_cmd(["git", "rev-parse", "HEAD"])
    return out.strip() if code == 0 else "unknown"


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


def keeplist_match(rel: str, keeplist: List[str]) -> Optional[str]:
    # Return matching rule if any, else None
    for rule in keeplist:
        if rel == rule.strip("/"):
            return rule
        if rule.endswith("/") and rel.startswith(rule.rstrip("/")):
            return rule
        if Path(rel).match(rule):
            return rule
        if rule and rule in rel:
            return rule
    return None


def ensure_soft_review() -> None:
    soft_review = REPORT_DIR / "soft_review.txt"
    if soft_review.exists():
        return
    generate_scan()


def generate_scan() -> None:
    run_cmd(["python3", str(REPO_ROOT / "tools/cleanup_scan.py")])


def parse_soft_review(path: Path) -> List[str]:
    items: List[str] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.rstrip()
        if not s:
            continue
        if "\t" in s:
            rel = s.split("\t")[0].strip()
        else:
            m = re.match(r"^(?P<path>.*?)\s+\d+$", s)
            rel = m.group("path").strip() if m else s.strip()
        if not rel:
            continue
        if rel.endswith("| cat") or rel.startswith("sed "):
            continue
        items.append(rel)
    return items


def is_under_safe_dir(rel_posix: str) -> bool:
    low = ("/" + rel_posix.strip("/")).lower()
    if any(tok in low for tok in SAFE_DIR_TOKENS):
        return True
    segments = [seg for seg in rel_posix.replace("\\", "/").split("/") if seg]
    return any(seg in SAFE_DIR_NAMES for seg in segments)


def string_is_safe(rel: str) -> bool:
    if is_under_safe_dir(rel):
        return True
    name_lower = Path(rel).name.lower()
    for ext in SAFE_FILE_EXT_ALWAYS:
        if name_lower.endswith(ext):
            return True
    for pat in BACKUP_NAME_PATTERNS:
        if re.search(pat, name_lower):
            return True
    return False


def promote_to_hard_from_soft(soft_items: List[str], keeplist: List[str]) -> Tuple[List[str], Dict[str, str]]:
    safe_paths: List[str] = []
    kept_by_keeplist: Dict[str, str] = {}
    for rel in soft_items:
        if not rel:
            continue
        keep_rule = keeplist_match(rel, keeplist)
        if keep_rule:
            kept_by_keeplist[rel] = keep_rule
            continue
        if string_is_safe(rel):
            safe_paths.append(rel)
    # de-dup and sort
    safe_paths = sorted(set(safe_paths))
    return safe_paths, kept_by_keeplist


def write_hard_delete(paths: List[str]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORT_DIR / "hard_delete.txt").open("w", encoding="utf-8") as f:
        for rel in paths:
            f.write(rel + "\n")


def write_existence_check(paths: List[str]) -> Tuple[List[Path], List[str]]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    existing_abs: List[Path] = []
    lines: List[str] = []
    for rel in paths:
        p = (REPO_ROOT / rel).resolve()
        if p.exists():
            lines.append(f"EXISTS\t{rel}")
            existing_abs.append(p)
        else:
            lines.append(f"MISSING\t{rel}")
    (REPORT_DIR / "existence_check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return existing_abs, [ln for ln in lines if ln.startswith("MISSING\t")]


def is_safe_dir_abs(p: Path) -> bool:
    if p.is_file():
        return False
    rel = p.relative_to(REPO_ROOT).as_posix()
    if any(seg in SAFE_DIR_NAMES for seg in Path(rel).parts):
        return True
    return is_under_safe_dir(rel)


def is_safe_file_abs(p: Path) -> bool:
    if p.is_dir():
        return False
    rel = p.relative_to(REPO_ROOT).as_posix()
    if is_under_safe_dir(rel):
        return True
    name_lower = p.name.lower()
    for ext in SAFE_FILE_EXT_ALWAYS:
        if name_lower.endswith(ext):
            return True
    for pat in BACKUP_NAME_PATTERNS:
        if re.search(pat, name_lower):
            return True
    return False


def delete_existing(existing_abs: List[Path]) -> Tuple[int, int, List[str]]:
    files_deleted = 0
    dirs_deleted = 0
    deleted_rel: List[str] = []
    # Delete files first, then dirs
    files = [p for p in existing_abs if p.is_file()]
    dirs = [p for p in existing_abs if p.is_dir()]
    for p in files:
        try:
            if is_safe_file_abs(p):
                p.unlink(missing_ok=True)
                files_deleted += 1
                deleted_rel.append(p.relative_to(REPO_ROOT).as_posix())
        except Exception:
            pass
    for p in dirs:
        try:
            if is_safe_dir_abs(p):
                shutil.rmtree(p)
                dirs_deleted += 1
                deleted_rel.append(p.relative_to(REPO_ROOT).as_posix())
        except Exception:
            pass
    return files_deleted, dirs_deleted, deleted_rel


def commit_with_reports(pass_index: int, files_deleted: int, dirs_deleted: int, message_suffix: str = "") -> bool:
    # Stage report files and deletions
    run_cmd(["git", "add", "-A"])
    code, status_out, _ = run_cmd(["git", "status", "--porcelain"])
    if not status_out.strip():
        return False
    msg = (
        f"chore(cleanup-pass-{pass_index:02d}): delete safe cache/log/build artifacts "
        f"(files={files_deleted}, dirs={dirs_deleted})"
    )
    if message_suffix:
        msg = f"{msg} — {message_suffix}"
    run_cmd(["git", "commit", "-m", msg])
    # Diff preview
    code, show_out, _ = run_cmd(["git", "--no-pager", "show", "--stat", "--oneline", "HEAD"])
    header = f"\n===== PASS {pass_index:02d} @ {get_head_commit()} =====\n"
    prev_path = REPORT_DIR / "commit_diff_preview.txt"
    prev = prev_path.read_text(encoding="utf-8") if prev_path.exists() else ""
    prev_path.write_text(prev + header + show_out + "\n", encoding="utf-8")
    return True


def summarize_validation(keeplist: List[str], kept_by_keeplist: Dict[str, str], hard_paths: List[str], deleted_rel: List[str]) -> None:
    lines: List[str] = []
    lines.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Keeplist rules: {len(keeplist)}")
    lines.append(f"Hard delete entries: {len(hard_paths)}")
    lines.append(f"Actually deleted: {len(deleted_rel)}")
    lines.append("")
    lines.append("Keeplist hits (blocked from deletion):")
    for path, rule in sorted(kept_by_keeplist.items()):
        lines.append(f"- {path} (rule: {rule})")
    (REPORT_DIR / "validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_summary(hard_paths: List[str], files_deleted: int, dirs_deleted: int) -> None:
    lines: List[str] = []
    lines.append(f"Hard-delete list size: {len(hard_paths)}")
    lines.append(f"Actually deleted — files: {files_deleted}, dirs: {dirs_deleted}")
    (REPORT_DIR / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def count_soft_review() -> int:
    p = REPORT_DIR / "soft_review.txt"
    if not p.exists():
        return 0
    return sum(1 for _ in p.read_text(encoding="utf-8", errors="ignore").splitlines() if _.strip())


def final_report(kept_by_keeplist: Dict[str, str], all_deleted: List[str]) -> None:
    soft_list = parse_soft_review(REPORT_DIR / "soft_review.txt")
    lines: List[str] = []
    lines.append("# Automated Cleanup Final Report")
    lines.append("")
    lines.append("## SAFE_DELETE (already removed)")
    for rel in sorted(set(all_deleted)):
        lines.append(f"- {rel}")
    lines.append("")
    lines.append("## KEEP (honoring keeplist)")
    for rel, rule in sorted(kept_by_keeplist.items()):
        lines.append(f"- {rel} — kept due to keeplist rule: {rule}")
    lines.append("")
    lines.append("## MANUAL_REVIEW (remaining from latest soft_review)")
    for rel in soft_list:
        lines.append(f"- {rel}")
    (REPO_ROOT / "final_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def orchestrate() -> None:
    ensure_report_dir()
    git_fetch()

    base_ref = "origin/main"
    last_branch = ""
    all_deleted: List[str] = []
    kept_agg: Dict[str, str] = {}

    for i in range(1, PASS_MAX + 1):
        branch = create_pass_branch(i, base_ref if i == 1 else last_branch)

        # Step 2: ensure scan
        ensure_soft_review()

        # Step 3: promote to hard, honor keeplist
        keeplist = load_keeplist()
        soft_items = parse_soft_review(REPORT_DIR / "soft_review.txt")
        hard_paths, kept_by_keeplist = promote_to_hard_from_soft(soft_items, keeplist)
        kept_agg.update(kept_by_keeplist)
        write_hard_delete(hard_paths)

        # Step 4: existence check and delete
        existing_abs, missing_lines = write_existence_check(hard_paths)
        files_deleted, dirs_deleted, deleted_rel = delete_existing(existing_abs)
        all_deleted.extend(deleted_rel)

        # Step 5: commit & reports
        summarize_validation(keeplist, kept_by_keeplist, hard_paths, deleted_rel)
        summarize_summary(hard_paths, files_deleted, dirs_deleted)
        committed = commit_with_reports(i, files_deleted, dirs_deleted)

        # Stop condition handler: retry once if 0 deletions
        if files_deleted == 0 and dirs_deleted == 0:
            # regenerate lists and retry once for this pass
            generate_scan()
            # Rebuild hard list
            soft_items = parse_soft_review(REPORT_DIR / "soft_review.txt")
            hard_paths, kept_by_keeplist = promote_to_hard_from_soft(soft_items, keeplist)
            kept_agg.update(kept_by_keeplist)
            write_hard_delete(hard_paths)
            existing_abs, _ = write_existence_check(hard_paths)
            files_deleted, dirs_deleted, deleted_rel = delete_existing(existing_abs)
            all_deleted.extend(deleted_rel)
            summarize_validation(keeplist, kept_by_keeplist, hard_paths, deleted_rel)
            summarize_summary(hard_paths, files_deleted, dirs_deleted)
            committed = commit_with_reports(i, files_deleted, dirs_deleted, message_suffix="retry") or committed

        # Step 6: rescan & loop decision
        generate_scan()
        soft_count = count_soft_review()

        last_branch = branch
        if soft_count < SOFT_THRESHOLD:
            break

    # Step 7: finalization branch
    final_branch = "cursor/final-cleanup-ready"
    run_cmd(["git", "checkout", "-B", final_branch, last_branch or base_ref])
    final_report(kept_agg, all_deleted)
    run_cmd(["git", "add", "-A"])
    code, status_out, _ = run_cmd(["git", "status", "--porcelain"])
    if status_out.strip():
        run_cmd(["git", "commit", "-m", "chore(cleanup): attach final_report and reports"])
        # append final commit preview
        code, show_out, _ = run_cmd(["git", "--no-pager", "show", "--stat", "--oneline", "HEAD"])
        prev_path = REPORT_DIR / "commit_diff_preview.txt"
        prev = prev_path.read_text(encoding="utf-8") if prev_path.exists() else ""
        prev_path.write_text(prev + "\n===== FINAL REPORT =====\n" + show_out + "\n", encoding="utf-8")

    # Optional: try to push the final branch (non-destructive to main)
    run_cmd(["git", "push", "-u", "origin", final_branch])

    # Print summary for caller
    print(f"LAST_BRANCH={last_branch}")
    print(f"FINAL_BRANCH={final_branch}")
    print(f"SOFT_REVIEW_COUNT={count_soft_review()}")
    print(f"DELETED_TOTAL={len(set(all_deleted))}")


if __name__ == "__main__":
    orchestrate()

