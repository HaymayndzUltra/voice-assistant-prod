#!/usr/bin/env python3
"""
Validate the unified startup configuration
Checks for circular dependencies, missing scripts, port conflicts, etc.
"""

import os
import sys
import yaml
from collections import defaultdict
from pathlib import Path

def load_config(config_path: str) -> dict:
    """Load and parse the YAML configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def extract_agents(config: dict) -> dict:
    """Extract all agents from the configuration"""
    agents = {}
    
    if 'agent_groups' not in config:
        print("ERROR: No agent_groups found in configuration")
        return agents
        
    for group_name, group_agents in config['agent_groups'].items():
        for agent_name, agent_config in group_agents.items():
            agents[agent_name] = {
                **agent_config,
                'group': group_name,
                'name': agent_name
            }
            
    return agents

def check_circular_dependencies(agents: dict) -> list:
    """Check for circular dependencies using DFS"""
    def has_cycle_dfs(node, visited, rec_stack, graph):
        visited[node] = True
        rec_stack[node] = True
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle_dfs(neighbor, visited, rec_stack, graph):
                    return True
            elif rec_stack.get(neighbor, False):
                return True
                
        rec_stack[node] = False
        return False
    
    # Build dependency graph
    graph = defaultdict(list)
    for agent_name, agent_config in agents.items():
        for dep in agent_config.get('dependencies', []):
            if dep in agents:
                graph[agent_name].append(dep)
    
    # Check for cycles
    visited = {}
    rec_stack = {}
    cycles = []
    
    for agent in agents:
        if agent not in visited:
            if has_cycle_dfs(agent, visited, rec_stack, graph):
                cycles.append(agent)
                
    return cycles

def check_missing_scripts(agents: dict) -> list:
    """Check for missing script files"""
    missing = []
    
    for agent_name, agent_config in agents.items():
        script_path = agent_config.get('script_path', '')
        if script_path and not os.path.exists(script_path):
            missing.append((agent_name, script_path))
            
    return missing

def check_port_conflicts(agents: dict) -> list:
    """Check for port conflicts"""
    port_usage = defaultdict(list)
    health_port_usage = defaultdict(list)
    
    for agent_name, agent_config in agents.items():
        # Handle port substitution
        port = str(agent_config.get('port', ''))
        health_port = str(agent_config.get('health_check_port', ''))
        
        # Simple substitution for validation
        if '${PORT_OFFSET}' in port:
            port = port.replace('${PORT_OFFSET}+', '').replace('${PORT_OFFSET}', '0')
        if '${PORT_OFFSET}' in health_port:
            health_port = health_port.replace('${PORT_OFFSET}+', '').replace('${PORT_OFFSET}', '0')
            
        if port and port.isdigit():
            port_usage[int(port)].append(agent_name)
        if health_port and health_port.isdigit():
            health_port_usage[int(health_port)].append(agent_name)
    
    conflicts = []
    for port, agents_list in port_usage.items():
        if len(agents_list) > 1:
            conflicts.append(('port', port, agents_list))
            
    for port, agents_list in health_port_usage.items():
        if len(agents_list) > 1:
            conflicts.append(('health_port', port, agents_list))
            
    return conflicts

def check_missing_dependencies(agents: dict) -> list:
    """Check for dependencies that don't exist in the configuration"""
    missing_deps = []
    
    for agent_name, agent_config in agents.items():
        for dep in agent_config.get('dependencies', []):
            if dep not in agents:
                missing_deps.append((agent_name, dep))
                
    return missing_deps

def generate_startup_order(agents: dict) -> list:
    """Generate the startup order based on dependencies"""
    from collections import deque
    
    # Build adjacency list and in-degree count
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    
    # Initialize all agents
    for agent_name in agents:
        in_degree[agent_name] = 0
        
    # Build dependency graph
    for agent_name, agent_config in agents.items():
        dependencies = agent_config.get('dependencies', [])
        for dep in dependencies:
            if dep in agents:
                graph[dep].append(agent_name)
                in_degree[agent_name] += 1
                
    # Kahn's algorithm for topological sort
    queue = deque([agent for agent in agents if in_degree[agent] == 0])
    sorted_agents = []
    
    while queue:
        agent = queue.popleft()
        sorted_agents.append(agent)
        
        for neighbor in graph[agent]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    return sorted_agents

def main():
    config_path = "config/unified_startup.yaml"
    
    print("=== UNIFIED SYSTEM CONFIGURATION VALIDATION ===\n")
    
    # Load configuration
    try:
        config = load_config(config_path)
        print(f"✓ Successfully loaded configuration from {config_path}")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return 1
        
    # Extract agents
    agents = extract_agents(config)
    print(f"✓ Found {len(agents)} agents in configuration")
    
    # Count by group
    groups = defaultdict(int)
    for agent_config in agents.values():
        groups[agent_config['group']] += 1
        
    print("\nAgent distribution by group:")
    for group, count in sorted(groups.items()):
        print(f"  - {group}: {count} agents")
    
    # Check for issues
    print("\n=== VALIDATION CHECKS ===")
    
    # 1. Circular dependencies
    cycles = check_circular_dependencies(agents)
    if cycles:
        print(f"\n✗ CIRCULAR DEPENDENCIES detected involving: {cycles}")
    else:
        print("\n✓ No circular dependencies found")
        
    # 2. Missing scripts
    missing_scripts = check_missing_scripts(agents)
    if missing_scripts:
        print(f"\n✗ MISSING SCRIPTS ({len(missing_scripts)}):")
        for agent_name, script_path in missing_scripts[:10]:  # Show first 10
            print(f"  - {agent_name}: {script_path}")
        if len(missing_scripts) > 10:
            print(f"  ... and {len(missing_scripts) - 10} more")
    else:
        print("\n✓ All script paths exist")
        
    # 3. Port conflicts
    conflicts = check_port_conflicts(agents)
    if conflicts:
        print(f"\n✗ PORT CONFLICTS ({len(conflicts)}):")
        for port_type, port, agents_list in conflicts:
            print(f"  - {port_type} {port}: {', '.join(agents_list)}")
    else:
        print("\n✓ No port conflicts detected")
        
    # 4. Missing dependencies
    missing_deps = check_missing_dependencies(agents)
    if missing_deps:
        print(f"\n✗ MISSING DEPENDENCIES ({len(missing_deps)}):")
        for agent, dep in missing_deps:
            print(f"  - {agent} depends on missing agent: {dep}")
    else:
        print("\n✓ All dependencies exist")
        
    # 5. Generate startup order
    print("\n=== STARTUP ORDER ===")
    startup_order = generate_startup_order(agents)
    
    if len(startup_order) != len(agents):
        print(f"\n✗ WARNING: Only {len(startup_order)} of {len(agents)} agents in startup order")
        print("  This indicates circular dependencies!")
    else:
        print("\nAgents will start in this order:")
        current_stage = None
        for i, agent_name in enumerate(startup_order, 1):
            agent_stage = agents[agent_name]['group']
            if agent_stage != current_stage:
                current_stage = agent_stage
                print(f"\n[{current_stage}]")
            print(f"  {i:2d}. {agent_name}")
            
    # Summary
    print("\n=== SUMMARY ===")
    total_issues = len(cycles) + len(missing_scripts) + len(conflicts) + len(missing_deps)
    
    if total_issues == 0:
        print("✓ Configuration validation PASSED - ready for deployment!")
        return 0
    else:
        print(f"✗ Configuration has {total_issues} issues that need to be resolved")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 