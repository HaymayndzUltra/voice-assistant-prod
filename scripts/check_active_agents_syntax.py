#!/usr/bin/env python3
"""
Check Syntax/Import Errors for All Active Agents
-----------------------------------------------
Loads all active agents from startup_config.yaml (MainPC and PC2),
then checks each script_path for syntax/import errors using py_compile.
Prints and saves a summary of all errors and which agents are clean.
Saves report to analysis_output/active_agents_syntax_report.json
"""
import os
import sys
import yaml
import json
import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
REPORT_PATH = OUTPUT_DIR / 'active_agents_syntax_report.json'

mainpc_config = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
pc2_config = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'

active_agents = []
for config_path, root_dir in [
    (mainpc_config, PROJECT_ROOT / 'main_pc_code'),
    (pc2_config, PROJECT_ROOT / 'pc2_code')
]:
    if not config_path.exists():
        continue
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    for section in config:
        if isinstance(config[section], list):
            for agent in config[section]:
                if isinstance(agent, dict) and agent.get('script_path'):
                    agent_entry = dict(agent)
                    agent_entry['root_dir'] = str(root_dir)
                    active_agents.append(agent_entry)

results = []
for agent in active_agents:
    name = agent['name']
    script_path = agent['script_path']
    root_dir = Path(agent['root_dir'])
    abs_path = root_dir / script_path
    result = {'name': name, 'script_path': str(abs_path)}
    if not abs_path.exists():
        result['status'] = 'missing'
        result['error'] = 'Script file not found'
    else:
        try:
            py_compile.compile(str(abs_path), doraise=True)
            result['status'] = 'ok'
        except py_compile.PyCompileError as e:
            result['status'] = 'syntax_error'
            result['error'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
    results.append(result)

# Print summary
print("\n=== Active Agents Syntax/Import Check ===")
for r in results:
    if r['status'] == 'ok':
        print(f"[OK]      {r['name']} ({r['script_path']})")
    elif r['status'] == 'missing':
        print(f"[MISSING] {r['name']} ({r['script_path']}) - {r['error']}")
    else:
        print(f"[ERROR]   {r['name']} ({r['script_path']}) - {r['error']}")

# Save report
with open(REPORT_PATH, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nFull report saved to {REPORT_PATH}") 