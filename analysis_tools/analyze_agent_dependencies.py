import json
from pathlib import Path
from typing import Dict, Any, List

try:
    import yaml  # Requires PyYAML
except ImportError as exc:
    raise SystemExit("PyYAML is required. Install with `pip install PyYAML`.") from exc

ROOT = Path(__file__).resolve().parent.parent
MAIN_CONFIG = ROOT / "main_pc_code" / "config" / "startup_config.yaml"
PC2_CONFIG = ROOT / "pc2_code" / "config" / "startup_config.yaml"


def _load_yaml(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def _extract_main_agents(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    agent_groups = cfg.get("agent_groups", {})
    agents: List[Dict[str, Any]] = []
    for group_name, group in agent_groups.items():
        if not group:
            # Skip YAML anchors or empty groups
            continue
        if not isinstance(group, dict):
            continue
        for agent_name, spec in group.items():
            if spec is None:
                continue
            agents.append(
                {
                    "name": agent_name,
                    "group": group_name,
                    "script_path": spec.get("script_path"),
                    "port": spec.get("port"),
                    "dependencies": spec.get("dependencies", []),
                    "required": spec.get("required", True),
                }
            )
    return agents


def _extract_pc2_agents(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    services = cfg.get("pc2_services", [])
    agents: List[Dict[str, Any]] = []
    for service in services:
        agents.append(
            {
                "name": service.get("name"),
                "group": "pc2_services",
                "script_path": service.get("script_path"),
                "port": service.get("port"),
                "dependencies": service.get("dependencies", []),
                "required": service.get("required", True),
            }
        )
    return agents


def main() -> None:
    main_cfg = _load_yaml(MAIN_CONFIG)
    pc2_cfg = _load_yaml(PC2_CONFIG)

    summary = {
        "main_pc": {
            "resource_limits": main_cfg.get("global_settings", {}).get("resource_limits", {}),
            "agents": _extract_main_agents(main_cfg),
        },
        "pc2": {
            "resource_limits": pc2_cfg.get("global_settings", {}).get("resource_limits", {}),
            "agents": _extract_pc2_agents(pc2_cfg),
        },
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()