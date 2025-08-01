#!/usr/bin/env python3
"""
Quick verifier – extracts agent ⇨ script_path pairs from both startup_config.yaml
Run from repo root:  `python3 parser_poc.py`
"""
import yaml, pathlib, pprint, sys, itertools, json
files = [
    "main_pc_code/config/startup_config.yaml",
    "pc2_code/config/startup_config.yaml",
]
def load(p):
    with open(p) as f:
        return yaml.safe_load(f)

out = {}
for f in files:
    cfg = load(f)
    agents = {}
    # MainPC uses nested groups
    if "agent_groups" in cfg:
        for grp_name, grp in cfg["agent_groups"].items():
            if grp is not None and isinstance(grp, dict):
                for name, meta in grp.items():
                    if isinstance(meta, dict) and "script_path" in meta:
                        agents[name] = meta["script_path"]
    # PC2 uses flat list
    if "pc2_services" in cfg:
        for item in cfg["pc2_services"]:
            if isinstance(item, dict) and "name" in item and "script_path" in item:
                agents[item["name"]] = item["script_path"]
    out[f] = agents
pprint.pp(out, width=140) 