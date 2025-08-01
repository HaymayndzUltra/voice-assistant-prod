#!/usr/bin/env python3
"""
Enhanced agent script path analyzer
Provides detailed statistics and breakdown of agent configurations
"""
import yaml, pathlib, pprint, sys, itertools, json
from collections import defaultdict

files = [
    "main_pc_code/config/startup_config.yaml",
    "pc2_code/config/startup_config.yaml",
]

def load(p):
    with open(p) as f:
        return yaml.safe_load(f)

def analyze_agents():
    results = {}
    stats = {
        'total_agents': 0,
        'main_pc_agents': 0,
        'pc2_agents': 0,
        'script_paths': defaultdict(int),
        'agent_groups': defaultdict(list)
    }
    
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
                            stats['script_paths'][meta["script_path"]] += 1
                            stats['agent_groups'][grp_name].append(name)
        
        # PC2 uses flat list
        if "pc2_services" in cfg:
            for item in cfg["pc2_services"]:
                if isinstance(item, dict) and "name" in item and "script_path" in item:
                    agents[item["name"]] = item["script_path"]
                    stats['script_paths'][item["script_path"]] += 1
        
        results[f] = agents
        
        # Update stats
        if "main_pc_code" in f:
            stats['main_pc_agents'] = len(agents)
        elif "pc2_code" in f:
            stats['pc2_agents'] = len(agents)
    
    stats['total_agents'] = stats['main_pc_agents'] + stats['pc2_agents']
    
    return results, stats

def main():
    results, stats = analyze_agents()
    
    print("=" * 80)
    print("AGENT SCRIPT PATH ANALYSIS")
    print("=" * 80)
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total Agents: {stats['total_agents']}")
    print(f"   MainPC Agents: {stats['main_pc_agents']}")
    print(f"   PC2 Agents: {stats['pc2_agents']}")
    
    print(f"\n📁 AGENT GROUPS (MainPC):")
    for group, agents in stats['agent_groups'].items():
        print(f"   {group}: {len(agents)} agents")
    
    print(f"\n🔄 DUPLICATE SCRIPT PATHS:")
    duplicates = {path: count for path, count in stats['script_paths'].items() if count > 1}
    if duplicates:
        for path, count in duplicates.items():
            print(f"   {path}: used by {count} agents")
    else:
        print("   No duplicate script paths found")
    
    print(f"\n📋 DETAILED BREAKDOWN:")
    for config_file, agents in results.items():
        print(f"\n{config_file}:")
        print("-" * len(config_file))
        for agent_name, script_path in sorted(agents.items()):
            print(f"  {agent_name} → {script_path}")
    
    # Save results to JSON for further analysis
    with open('agent_analysis_results.json', 'w') as f:
        json.dump({
            'results': results,
            'stats': dict(stats),
            'duplicates': dict(duplicates)
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: agent_analysis_results.json")

if __name__ == "__main__":
    main() 