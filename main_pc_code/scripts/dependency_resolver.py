#!/usr/bin/env python3
"""
Dependency Resolver for AI System Startup

This script analyzes the startup_config.yaml file and generates a phased startup plan
based on agent dependencies using topological sorting.
"""

import yaml
import os
import sys
from collections import defaultdict, deque
from pathlib import Path
from pprint import pprint


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def load_startup_config():
    """Load the startup configuration from the YAML file."""
    config_path = PathManager.join_path("main_pc_code", PathManager.join_path("config", "startup_config.yaml"))
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading startup configuration: {e}")
        sys.exit(1)

class DependencyResolver:
    def __init__(self, config):
        self.config = config
        self.agents = {}  # name -> agent dict
        self.dependencies = defaultdict(set)  # name -> set of dependency names
        self.dependents = defaultdict(set)  # name -> set of agents that depend on this
        self.extract_agents()
        self.build_dependency_graph()
    
    def extract_agents(self):
        """Extract all agents from the startup configuration."""
        # Process each section in the configuration
        for section_name, section_data in self.config.items():
            if not isinstance(section_data, list):
                continue
                
            for agent in section_data:
                if not isinstance(agent, dict):
                    continue
                    
                # Skip entries without a name or script_path
                if 'name' not in agent or 'script_path' not in agent:
                    continue
                
                name = agent['name']
                self.agents[name] = agent
                
                # Extract dependencies if they exist
                if 'dependencies' in agent:
                    for dep in agent['dependencies']:
                        self.dependencies[name].add(dep)
    
    def build_dependency_graph(self):
        """Build the reverse dependency graph (who depends on whom)."""
        for agent_name, deps in self.dependencies.items():
            for dep in deps:
                self.dependents[dep].add(agent_name)
    
    def topological_sort(self):
        """
        Perform topological sort to determine the dependency levels.
        Returns a list of lists, where each inner list represents a level of agents
        that can be started in parallel.
        """
        # Count incoming edges for each agent
        in_degree = {name: len(deps) for name, deps in self.dependencies.items()}
        
        # Add agents with no explicit dependencies
        for name in self.agents:
            if name not in in_degree:
                in_degree[name] = 0
        
        # Queue of nodes with no incoming edges
        queue = deque([name for name, count in in_degree.items() if count == 0])
        
        result = []
        current_level = []
        
        while queue:
            # Process all nodes at the current level
            level_size = len(queue)
            current_level = []
            
            for _ in range(level_size):
                node = queue.popleft()
                current_level.append(node)
                
                # Reduce in-degree of all dependent nodes
                for dependent in self.dependents[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            result.append(current_level)
        
        # Check for cycles
        if sum(len(level) for level in result) != len(self.agents):
            print("WARNING: Circular dependencies detected!")
            
        return result
    
    def get_agent_details(self, name):
        """Get full details for an agent by name."""
        return self.agents.get(name, {})
    
    def get_startup_phases(self):
        """
        Get the startup phases with full agent details.
        Returns a list of phases, where each phase is a list of agent dictionaries.
        """
        levels = self.topological_sort()
        phases = []
        
        for level_idx, level in enumerate(levels):
            phase = []
            for agent_name in level:
                agent = self.get_agent_details(agent_name)
                # Add phase information
                agent_info = agent.copy()
                agent_info['phase'] = level_idx + 1
                phase.append(agent_info)
            phases.append(phase)
            
        return phases
    
    def get_startup_plan(self):
        """
        Generate a structured startup plan with phases and agent details.
        """
        phases = self.get_startup_phases()
        
        plan = {
            "total_phases": len(phases),
            "total_agents": len(self.agents),
            "phases": []
        }
        
        for phase_idx, phase in enumerate(phases):
            phase_info = {
                "phase": phase_idx + 1,
                "agents": len(phase),
                "agent_list": []
            }
            
            for agent in phase:
                # Include only essential info for the plan
                agent_info = {
                    "name": agent["name"],
                    "script_path": agent["script_path"],
                    "port": agent.get("port"),
                    "dependencies": agent.get("dependencies", []),
                    "required": agent.get("required", False)
                }
                phase_info["agent_list"].append(agent_info)
            
            plan["phases"].append(phase_info)
        
        return plan

def main():
    """Main function."""
    print("Loading startup configuration...")
    config = load_startup_config()
    
    print("Building dependency graph and resolving startup phases...")
    resolver = DependencyResolver(config)
    startup_plan = resolver.get_startup_plan()
    
    print("\nStartup Plan Summary:")
    print(f"Total Phases: {startup_plan['total_phases']}")
    print(f"Total Agents: {startup_plan['total_agents']}")
    
    print("\nDetailed Startup Phases:")
    for phase in startup_plan["phases"]:
        print(f"\nPhase {phase['phase']} ({phase['agents']} agents):")
        for agent in phase["agent_list"]:
            deps = ", ".join(agent.get("dependencies", [])) or "None"
            print(f"  - {agent['name']} (Port: {agent['port']}, Dependencies: {deps})")
    
    return startup_plan

if __name__ == "__main__":
    main() 