#!/usr/bin/env python3
import json
import os
import random
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


REPO_ROOT = Path("/workspace").resolve()
REPORT_DIR = REPO_ROOT / ".cleanup-report"


JUNK_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "out",
    "target",
    "tmp",
    "temp",
    "logs",
    "coverage",
    ".coverage",
    ".tox",
    ".cleanup-report",
}

JUNK_FILE_EXTENSIONS = {
    # Python
    ".pyc",
    ".pyo",
    ".pyd",
    ".whl",
    ".egg",
    ".egg-info",
    ".pytest_cache",
    # JS/TS
    ".map",
    ".tsbuildinfo",
    # Java/JVM
    ".class",
    ".jar",
    ".war",
    # C/C++/Rust/Go
    ".o",
    ".so",
    ".a",
    ".rlib",
    ".dSYM",
    ".dll",
    ".exe",
    # Archives and bundle artefacts
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".7z",
    # Misc/logs
    ".log",
    ".tmp",
    ".bak",
    ".swp",
    ".swo",
    ".ds_store",
}

SEARCH_EXCLUDE_DIRS = {
    ".git",
    ".cleanup-report",
    "node_modules",
    "dist",
    "build",
    "out",
    "target",
    ".venv",
    "venv",
    "models",
    "data",
    "logs",
}

SIZE_LARGE_BYTES = 5 * 1024 * 1024  # 5MB


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(args, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


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


def is_path_in_keeplist(path: Path, keeplist: List[str]) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    for rule in keeplist:
        # Exact match
        if rel == rule.strip("/"):
            return True
        # Prefix directory match
        if rule.endswith("/") and rel.startswith(rule.rstrip("/")):
            return True
        # Glob match
        if Path(rel).match(rule):
            return True
        # Substring safeguard (last resort; strict)
        if rule and rule in rel:
            return True
    return False


def list_all_paths(root: Path) -> List[Path]:
    paths: List[Path] = []
    for base, dirnames, filenames in os.walk(root, topdown=True):
        # Prune heavy or irrelevant dirs from traversal? We still want to include them as candidates.
        # To include them in results without deep walk, we keep directory itself but avoid diving deep when extremely large.
        # However, here we keep traversal but skip .git and report dir.
        pruned: List[str] = []
        for d in list(dirnames):
            if d in {".git", ".cleanup-report"}:
                pruned.append(d)
        for d in pruned:
            dirnames.remove(d)

        base_path = Path(base)
        # Add directories (excluding root itself)
        if base_path != root:
            paths.append(base_path)
        for f in filenames:
            paths.append(base_path / f)
    return paths


def path_is_tracked(path: Path) -> bool:
    code, out, _ = run_cmd(["git", "ls-files", "--error-unmatch", path.relative_to(REPO_ROOT).as_posix()])
    return code == 0


def path_is_ignored(path: Path) -> bool:
    code, _, _ = run_cmd(["git", "check-ignore", "-q", path.relative_to(REPO_ROOT).as_posix()])
    return code == 0


def check_git_untracked_or_ignored(path: Path) -> Tuple[bool, str]:
    tracked = path_is_tracked(path)
    ignored = path_is_ignored(path)
    passed = (not tracked) or ignored
    reason = f"tracked={tracked}, ignored={ignored}"
    return passed, reason


def check_junk_pattern(path: Path) -> Tuple[bool, str]:
    rel = path.relative_to(REPO_ROOT)
    parts = set(rel.parts)
    # Directory names
    if any(p in JUNK_DIR_NAMES for p in parts):
        return True, "matched junk directory name"
    # File extension
    if path.is_file():
        lower = path.name.lower()
        for ext in JUNK_FILE_EXTENSIONS:
            if lower.endswith(ext):
                return True, f"extension {ext}"
        # Backup/swap like names
        if re.search(r"(~$|^\.?#|\.bak$|\.old$|\.orig$|^backup$|^~)", lower):
            return True, "backup/temp filename pattern"
    # Common cache/build subtree indicators
    if any(token in rel.as_posix().lower() for token in ["/build/", "/dist/", "/out/", "/target/", "/__pycache__/", "/node_modules/"]):
        return True, "cache/build path token"
    return False, "no junk pattern"


def is_text_file(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(512)
        if b"\x00" in chunk:
            return False
        # Heuristic: treat small binary signatures as binary
        if chunk.startswith(b"\x7fELF"):
            return False
        return True
    except Exception:
        return False


def grep_search_terms(terms: List[str], exclude_paths: List[Path]) -> bool:
    # Return True if any term is found in repo text files. We avoid path-specific excludes
    # to keep behavior simple and robust.
    if not terms:
        return False
    exclude_args: List[str] = []
    for d in SEARCH_EXCLUDE_DIRS:
        exclude_args += ["--exclude-dir", d]
    # Build combined regex (escape terms)
    safe_terms = [re.escape(t) for t in terms if t]
    if not safe_terms:
        return False
    pattern = "|".join(safe_terms)
    cmd = [
        "grep",
        "-RInE",
        pattern,
        ".",
    ] + exclude_args
    code, out, _ = run_cmd(cmd)
    return code == 0 and bool(out.strip())


def check_no_references(path: Path) -> Tuple[bool, str]:
    # Search for filename and stem across repo (excluding heavy dirs). We do not exclude the
    # file itself to avoid complex path logic; self-reference is rare.
    name = path.name
    stem = path.stem if path.is_file() else path.name
    found = grep_search_terms([name, stem], [])
    return (not found), ("no refs found" if not found else "references detected in repo search")


def check_build_artifact_hint(path: Path) -> Tuple[bool, str]:
    # Hint that this is build/cache/artifact rather than source
    if path.is_dir():
        # directory with junk dir name or typical build dir names
        if path.name in JUNK_DIR_NAMES:
            return True, "dir name indicates cache/build"
        sub = path.relative_to(REPO_ROOT).as_posix().lower()
        if any(t in sub for t in ["build/", "dist/", "out/", "target/", "__pycache__/", "node_modules/"]):
            return True, "dir path indicates build/cache"
        return False, "no build/cache dir hint"
    # files: extension match or inside cache/build dirs
    lower = path.name.lower()
    for ext in JUNK_FILE_EXTENSIONS:
        if lower.endswith(ext):
            return True, f"file extension {ext} indicates artifact"
    rel = path.relative_to(REPO_ROOT).as_posix().lower()
    if any(t in rel for t in ["/build/", "/dist/", "/out/", "/target/", "/__pycache__/", "/node_modules/"]):
        return True, "path under cache/build tree"
    return False, "no artifact hint"


def check_not_executable_source(path: Path) -> Tuple[bool, str]:
    # Pass if it is NOT an executable source (i.e., no shebang/ELF, not in src/scripts except cache)
    if path.is_dir():
        # Conservative: if directory suggests src/scripts and not cache, consider potentially executable sources exist → fail
        rel = path.relative_to(REPO_ROOT).as_posix().lower()
        if any(seg in {"src", "script", "scripts", "bin"} for seg in path.parts):
            if not any(tok in rel for tok in ["__pycache__", "build", "dist", "node_modules", "out", "target"]):
                return False, "directory likely holds executable sources"
        return True, "directory not an executable-source path"
    # Files
    try:
        st = path.stat()
        is_executable_mode = bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except Exception:
        is_executable_mode = False
    try:
        with path.open("rb") as f:
            head = f.read(4)
            f.seek(0)
            line = f.readline()
        if head.startswith(b"\x7fELF"):
            return False, "ELF binary"
        if line.startswith(b"#!"):
            return False, "has shebang"
    except Exception:
        pass
    rel = path.relative_to(REPO_ROOT).as_posix().lower()
    if any(seg in rel.split("/") for seg in ["src", "script", "scripts", "bin"]):
        if not any(tok in rel for tok in ["__pycache__", "build", "dist", "node_modules", "out", "target"]):
            # even if not executable-bit/shebang, treat as potential source → fail
            return False, "under src/scripts path"
    if is_executable_mode:
        return False, "executable file mode"
    return True, "not an executable source"


def human_readable_size(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def check_size_volatility_hint(path: Path) -> Tuple[bool, str]:
    # Pass if >5MB and under cache/build tree
    try:
        total_size = 0
        if path.is_file():
            total_size = path.stat().st_size
        else:
            for base, _, files in os.walk(path):
                for f in files:
                    fp = Path(base) / f
                    try:
                        total_size += fp.stat().st_size
                    except Exception:
                        pass
    except Exception:
        total_size = 0
    rel = path.relative_to(REPO_ROOT).as_posix().lower()
    under_cache = any(t in rel for t in ["/build/", "/dist/", "/out/", "/target/", "/__pycache__/", "/node_modules/", ".cache/"])
    passed = (total_size >= SIZE_LARGE_BYTES) and under_cache
    return passed, f"size={human_readable_size(total_size)}, under_cache={under_cache}"


def compute_checks(path: Path) -> Tuple[Dict[str, Dict[str, object]], int]:
    checks: Dict[str, Dict[str, object]] = {}
    c1, r1 = check_git_untracked_or_ignored(path)
    checks["git_untracked_or_ignored"] = {"pass": c1, "detail": r1}

    c2, r2 = check_junk_pattern(path)
    checks["junk_pattern_match"] = {"pass": c2, "detail": r2}

    c3, r3 = check_no_references(path)
    checks["no_references_in_codebase"] = {"pass": c3, "detail": r3}

    c4, r4 = check_build_artifact_hint(path)
    checks["artifact_hint"] = {"pass": c4, "detail": r4}

    c5, r5 = check_not_executable_source(path)
    checks["not_executable_source"] = {"pass": c5, "detail": r5}

    c6, r6 = check_size_volatility_hint(path)
    checks["size_volatility_hint"] = {"pass": c6, "detail": r6}

    score = sum(1 for k in checks.values() if k["pass"])
    return checks, score


def get_git_head() -> str:
    code, out, _ = run_cmd(["git", "rev-parse", "HEAD"])
    return (out.strip() if code == 0 else "unknown")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    keeplist = load_keeplist()
    all_paths = list_all_paths(REPO_ROOT)

    # Filter only filesystem entries (skip sockets, etc.) and siblings of report dir
    candidates: List[Path] = []
    for p in all_paths:
        try:
            if not p.exists():
                continue
            # Exclude report dir
            if REPORT_DIR in p.parents or p == REPORT_DIR:
                continue
            # Exclude .git directory
            if any(seg == ".git" for seg in p.parts):
                continue
            candidates.append(p)
        except Exception:
            continue

    evidence: List[Dict[str, object]] = []
    hard_delete: List[Tuple[Path, int]] = []
    soft_review: List[Tuple[Path, int]] = []

    for path in candidates:
        # Skip items explicitly in keeplist
        if is_path_in_keeplist(path, keeplist):
            continue

        checks, score = compute_checks(path)
        try:
            size_bytes = 0
            if path.is_file():
                size_bytes = path.stat().st_size
            else:
                for base, _, files in os.walk(path):
                    for f in files:
                        fp = Path(base) / f
                        try:
                            size_bytes += fp.stat().st_size
                        except Exception:
                            pass
        except Exception:
            size_bytes = 0

        evidence.append(
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "is_dir": path.is_dir(),
                "size_bytes": size_bytes,
                "score": score,
                "checks": checks,
            }
        )

        if score >= 5:
            hard_delete.append((path, score))
        elif 3 <= score <= 4:
            soft_review.append((path, score))

    # Sort outputs
    hard_delete.sort(key=lambda t: (t[0].is_file(), t[0].as_posix()))
    soft_review.sort(key=lambda t: (t[0].is_file(), t[0].as_posix()))

    # Write evidence.json
    evidence_sorted = sorted(evidence, key=lambda e: (e["score"], e["path"]))
    (REPORT_DIR / "evidence.json").write_text(
        json.dumps({"generated_at": datetime.utcnow().isoformat() + "Z", "git_head": get_git_head(), "items": evidence_sorted}, indent=2),
        encoding="utf-8",
    )

    # Write hard_delete.txt and soft_review.txt
    with (REPORT_DIR / "hard_delete.txt").open("w", encoding="utf-8") as f:
        for p, score in hard_delete:
            f.write(f"{p.relative_to(REPO_ROOT).as_posix()}\t{score}\n")
    with (REPORT_DIR / "soft_review.txt").open("w", encoding="utf-8") as f:
        for p, score in soft_review:
            f.write(f"{p.relative_to(REPO_ROOT).as_posix()}\t{score}\n")

    # SUMMARY.md
    hard_delete_set = {p.relative_to(REPO_ROOT).as_posix(): score for p, score in hard_delete}
    # Top 20 largest hard-delete entries
    size_by_path: Dict[str, int] = {}
    for e in evidence:
        p = e["path"]
        if p in hard_delete_set:
            size_by_path[p] = int(e.get("size_bytes", 0))
    top20 = sorted(size_by_path.items(), key=lambda kv: kv[1], reverse=True)[:20]

    summary_lines: List[str] = []
    summary_lines.append(f"Git HEAD: {get_git_head()}")
    summary_lines.append(f"Hard-delete candidates: {len(hard_delete)}")
    summary_lines.append(f"Soft-review candidates: {len(soft_review)}")
    summary_lines.append("")
    summary_lines.append("Top 20 largest hard-delete entries:")
    for path_str, sz in top20:
        summary_lines.append(f"- {path_str} — {human_readable_size(sz)}")
    (REPORT_DIR / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    # predelete_preview.md
    preview_lines: List[str] = []
    preview_lines.append("# Pre-Delete Preview")
    preview_lines.append("")
    preview_lines.append("Path | Score | Passed Checks | Failed Checks")
    preview_lines.append("---|---:|---|---")
    checks_by_path: Dict[str, Dict[str, Dict[str, object]]] = {e["path"]: e["checks"] for e in evidence}
    for p, score in hard_delete:
        rel = p.relative_to(REPO_ROOT).as_posix()
        checks = checks_by_path.get(rel, {})
        passed = [k for k, v in checks.items() if v.get("pass")]
        failed = [k for k, v in checks.items() if not v.get("pass")]
        preview_lines.append(f"{rel} | {score} | {', '.join(passed)} | {', '.join(failed)}")
    (REPORT_DIR / "predelete_preview.md").write_text("\n".join(preview_lines) + "\n", encoding="utf-8")

    # validation.md
    rng = random.Random()
    rng.seed(get_git_head())  # deterministic sampling across the same commit
    hard_paths = [p.relative_to(REPO_ROOT).as_posix() for p, _ in hard_delete]
    bad_scored = sum(1 for e in evidence if e["path"] in hard_paths and int(e["score"]) < 5)
    sample_k = min(10, len(hard_paths))
    samples = rng.sample(hard_paths, sample_k) if sample_k > 0 else []
    items_by_path: Dict[str, Dict[str, object]] = {e["path"]: e for e in evidence}
    lines: List[str] = []
    lines.append("# Validation")
    lines.append("")
    lines.append(f"Hard-delete entries with score <5: {bad_scored}")
    lines.append("")
    lines.append("## Sampled hard-delete items (deterministic, 10 or fewer)")
    for sp in samples:
        itm = items_by_path[sp]
        lines.append("")
        lines.append(f"- {sp}")
        lines.append(f"  - score: {itm['score']}")
        # show check results succinctly
        check_pairs = [f"{k}:{'✔' if v['pass'] else '✖'}" for k, v in itm["checks"].items()]
        lines.append(f"  - checks: {', '.join(check_pairs)}")
    # keeplist confirmation
    lines.append("")
    lines.append("## Keeplist preservation")
    if keeplist:
        lines.append("Keeplist rules detected. Confirming none appear in hard_delete or soft_review results.")
        bad_keeplist_hits: List[str] = []
        all_out = set(hard_paths + [p.relative_to(REPO_ROOT).as_posix() for p, _ in soft_review])
        for rule in keeplist:
            for outp in list(all_out):
                if Path(outp).match(rule) or outp.startswith(rule.strip("/")) or rule in outp:
                    bad_keeplist_hits.append(f"rule={rule} -> hit={outp}")
        if bad_keeplist_hits:
            lines.append("WARNING: Some keeplist rules matched outputs:")
            for h in bad_keeplist_hits:
                lines.append(f"- {h}")
        else:
            lines.append("Confirmed: No keeplist entries were included in outputs.")
    else:
        lines.append("No keeplist found.")
    (REPORT_DIR / "validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Print counts to stdout as final requirement
    print(len(hard_delete))
    print(len(soft_review))
    return 0


if __name__ == "__main__":
    sys.exit(main())

