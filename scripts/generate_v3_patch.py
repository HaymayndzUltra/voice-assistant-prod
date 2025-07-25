#!/usr/bin/env python3
"""generate_v3_patch.py

Utility: merge agents from legacy startup_config.yaml files (MainPC + PC2)
into the unified config/startup_config.v3.yaml whilst preserving existing
content.  The script writes the merged file to
   config/startup_config.v3.merged.yaml
and prints a short summary.

Usage:
    python scripts/generate_v3_patch.py

Note: it does NOT overwrite the existing v3 file – apply manually after
inspection.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parent.parent
LEGACY_MAIN = ROOT / "main_pc_code" / "config" / "startup_config.yaml"
LEGACY_PC2 = ROOT / "pc2_code" / "config" / "startup_config.yaml"
V3_FILE = ROOT / "config" / "startup_config.v3.yaml"
OUTPUT = ROOT / "config" / "startup_config.v3.merged.yaml"

def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def merge_agents(v3: Dict[str, Any], legacy_main: Dict[str, Any], legacy_pc2: Dict[str, Any]) -> None:
    """Modify *v3* in-place by adding agents from legacy configs if missing."""
    # Helper to flatten agent dicts
    def extract_agents(group_map: Dict[str, Any]) -> Dict[str, Any]:
        agents: Dict[str, Any] = {}
        for g in group_map.values():
            agents.update(g)
        return agents

    v3_groups = v3.setdefault("agent_groups", {})

    main_agents = extract_agents(legacy_main.get("agent_groups", {}))
    pc2_agents_list = legacy_pc2.get("pc2_services", [])
    pc2_agents = {a["name"] if isinstance(a, dict) else "": a for a in pc2_agents_list if isinstance(a, dict)}

    def add_agent(agent_name: str, agent_cfg: Dict[str, Any], default_group: str):
        if any(agent_name in agents for agents in v3_groups.values()):
            return  # already present
        grp = v3_groups.setdefault(default_group, {})
        grp[agent_name] = agent_cfg

    # --- merge MainPC agents ---
    for name, cfg in main_agents.items():
        add_agent(name, cfg, cfg.get("group", "unclassified_mainpc"))

    # --- merge PC2 agents ---
    for name, cfg in pc2_agents.items():
        add_agent(name, cfg, "pc2_services")


def main() -> None:
    v3 = load_yaml(V3_FILE)
    legacy_main = load_yaml(LEGACY_MAIN)
    legacy_pc2 = load_yaml(LEGACY_PC2)
    merge_agents(v3, legacy_main, legacy_pc2)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(v3, f, sort_keys=False)

    print(f"✅ Merged config written to {OUTPUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()