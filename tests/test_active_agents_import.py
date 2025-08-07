import importlib.util
import os
import yaml
from pathlib import Path

CONFIG_FILES = [
    Path("main_pc_code/config/startup_config.yaml"),
    Path("pc2_code/config/startup_config.yaml"),
]

AGENT_ENTRIES_KEYS = ["agent_groups", "pc2_services"]


def _import_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_scripts_importable():
    """Ensure every script_path in startup configs exists & is importable."""
    missing_paths = []
    import_failures = []

    for cfg_path in CONFIG_FILES:
        data = yaml.safe_load(cfg_path.read_text())

        # iterate through nested agent dicts (main_pc) or list (pc2)
        if "agent_groups" in data:
            for group in data["agent_groups"].values():
                for name, meta in group.items():
                    script = Path(meta["script_path"])
                    if not script.exists():
                        missing_paths.append(str(script))
                        continue
                    try:
                        _import_from_path(script)
                    except Exception as e:
                        import_failures.append(f"{script}: {e}")
        if "pc2_services" in data:
            for svc in data["pc2_services"]:
                script = Path(svc["script_path"])
                if not script.exists():
                    missing_paths.append(str(script))
                    continue
                try:
                    _import_from_path(script)
                except Exception as e:
                    import_failures.append(f"{script}: {e}")

    assert not missing_paths, f"Missing scripts: {missing_paths}"
    assert not import_failures, f"Import errors: {import_failures}"
