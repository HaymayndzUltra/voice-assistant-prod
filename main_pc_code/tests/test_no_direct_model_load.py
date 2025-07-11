import os
import re
from pathlib import Path

# Patterns that indicate direct model loading we want to forbid
FORBIDDEN_PATTERNS = [
    re.compile(r"from_pretrained\(")
]

# Allow-list of file or directory prefixes (relative to repo root) that
# are grandfathered in and *temporarily* allowed to keep legacy loaders.
# IMPORTANT: Any *new* file must NOT appear in this list.
ALLOWED_PATH_PREFIXES = [
    "main_pc_code/agents/model_manager_agent.py",
    "main_pc_code/agents/gguf_model_manager.py",
    "main_pc_code/agents/_trash_",  # legacy trash dir
    "main_pc_code/agents/_archive/",  # historical archive
    "main_pc_code/FORMAINPC/",  # legacy fine-tuning scripts
    "main_pc_code/src/analysis/",  # research utilities
]

REPO_ROOT = Path(__file__).resolve().parents[1]  # up to project root
SCAN_ROOT = REPO_ROOT / "main_pc_code"


def is_allowed(path: Path) -> bool:
    """Return True if the file path starts with any allowed prefix."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(rel.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def test_no_stray_from_pretrained_calls():
    """Fail if forbidden patterns appear outside the allow-list."""
    violations = []

    for file_path in SCAN_ROOT.rglob("*.py"):
        # Skip explicitly allowed files / dirs
        if is_allowed(file_path):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            # Binary or unreadable file – ignore
            continue

        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                violations.append(file_path)
                break  # no need to check other patterns for this file

    if violations:
        formatted = "\n".join(str(v.relative_to(REPO_ROOT)) for v in violations)
        raise AssertionError(
            "Found disallowed direct model-loading calls in the following files:\n"
            + formatted
        ) 