import os
import re
import yaml
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
# Patterns that indicate direct model loading we want to forbid
FORBIDDEN_PATTERNS = [
    re.compile(r"from_pretrained\(")
]

# Allow-list of file or directory prefixes (relative to repo root) that
# are grandfathered in and *temporarily* allowed to keep legacy loaders.
# IMPORTANT: Any *new* file must NOT appear in this list.
ALLOWED_PATH_PREFIXES = [
    join_path("main_pc_code", "agents/model_manager_agent.py"),
    join_path("main_pc_code", "agents/gguf_model_manager.py"),
    join_path("main_pc_code", "agents/_trash_"),  # legacy trash dir
    join_path("main_pc_code", "agents/_archive/"),  # historical archive
    join_path("main_pc_code", "src/analysis/"),  # research utilities
]

REPO_ROOT = Path(__file__).resolve().parents[1]  # up to project root
SCAN_ROOT = REPO_ROOT / "main_pc_code"


def is_allowed(path: Path) -> bool:
    """Return True if the file path starts with any allowed prefix."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(rel.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def check_legacy_models_flag() -> bool:
    """Check if ENABLE_LEGACY_MODELS flag is enabled in llm_config.yaml."""
    try:
        llm_config_path = REPO_ROOT / "config" / "llm_config.yaml"
        if not llm_config_path.exists():
            return False
        
        with open(llm_config_path, 'r') as f:
            llm_config = yaml.safe_load(f)
        
        return llm_config.get('global_flags', {}).get('ENABLE_LEGACY_MODELS', False)
    except Exception:
        return False


def test_no_stray_from_pretrained_calls():
    """Fail if forbidden patterns appear outside the allow-list."""
    # Check if legacy models are enabled
    legacy_models_enabled = check_legacy_models_flag()
    
    # If legacy models are enabled, skip the test
    if legacy_models_enabled:
        print("ENABLE_LEGACY_MODELS flag is set to True, skipping direct model loading check")
        return
    
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
            + "\n\nDirect model loading is disabled (ENABLE_LEGACY_MODELS=False). "
            + "Use model_client instead."
        ) 