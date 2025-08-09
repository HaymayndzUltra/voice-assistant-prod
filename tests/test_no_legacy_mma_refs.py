from pathlib import Path

FORBIDDEN_SUBSTRINGS = [
    "RequestCoordinator",
    "model_manager_port",
    "MODEL_MANAGER_HOST",
    "model_status_pub_port",
]

ACTIVE_DIRS = [
    "main_pc_code/agents",
    "main_pc_code/services",
    "pc2_code/agents",
    "services",
]

EXEMPT_DIRS = [
    "backups",
    "archive",
    "backups/unused_import_cleanup",
    "main_pc_code/agents/_trash_",
]


def test_no_legacy_mma_refs():
    root = Path("/workspace")
    problems = []
    for rel in ACTIVE_DIRS:
        p = root / rel
        if not p.exists():
            continue
        for file in p.rglob("*.py"):
            if any(str(file).startswith(str(root / ex)) for ex in EXEMPT_DIRS):
                continue
            text = file.read_text(encoding="utf-8", errors="ignore")
            for bad in FORBIDDEN_SUBSTRINGS:
                if bad in text:
                    problems.append(f"{file} contains deprecated reference '{bad}'")
    assert not problems, "\n" + "\n".join(problems)