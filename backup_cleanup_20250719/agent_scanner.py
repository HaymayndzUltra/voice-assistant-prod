#!/usr/bin/env python3
"""
Agent Scanner
------------
Scans the startup_config.yaml files to discover all agents, their dependencies,
and generates a complete dependency graph. Also identifies missing configurations.
"""

import os
import sys
import yaml
import json
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'
MAIN_PC_CONFIG_PATH = MAIN_PC_CODE / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PC2_CODE / 'config' / 'startup_config.yaml'

# Output paths
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
GRAPH_OUTPUT = OUTPUT_DIR / 'agent_dependency_graph.png'
REPORT_OUTPUT = OUTPUT_DIR / 'agent_report.json'
MISSING_CONFIG_OUTPUT = OUTPUT_DIR / 'missing_config.yaml'

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class AgentInfo:
    """Class to store information about an agent."""
    def __init__(self, name: str, file_path: str, host: str, port: int, health_port: Optional[int] = None):
        self.name = name
        self.file_path = file_path
        self.host = host
        self.port = port
        self.health_port = health_port
        self.dependencies: List[str] = []
        self.required: bool = False
        self.params: Dict[str, Any] = {}
        self.source_config: str = ""  # 'mainpc' or 'pc2'
        self.source_section: str = ""  # Section in the config file

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'file_path': self.file_path,
            'host': self.host,
            'port': self.port,
            'health_port': self.health_port,
            'dependencies': self.dependencies,
            'required': self.required,
            'params': self.params,
            'source_config': self.source_config,
            'source_section': self.source_section
        }

class AgentScanner:
    """Scanner for discovering agents from startup_config.yaml files."""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.dependency_graph = nx.DiGraph()
        self.mainpc_config = {}
        self.pc2_config = {}
        
    def scan_configs(self):
        """Scan the startup_config.yaml files for agents."""
        print("Scanning startup_config.yaml files for agents...")
        
        # Load MainPC config
        if MAIN_PC_CONFIG_PATH.exists():
            self._load_config(MAIN_PC_CONFIG_PATH, 'mainpc')
        else:
            print(f"Warning: MainPC config not found at {MAIN_PC_CONFIG_PATH}")
        
        # Load PC2 config
        if PC2_CONFIG_PATH.exists():
            self._load_config(PC2_CONFIG_PATH, 'pc2')
        else:
            print(f"Warning: PC2 config not found at {PC2_CONFIG_PATH}")
        
        # Build dependency graph
        self._build_dependency_graph()
        
        print(f"Found {len(self.agents)} agents in the config files.")
    
    def _load_config(self, config_path: Path, config_type: str):
        """Load a startup_config.yaml file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if config_type == 'mainpc':
                self.mainpc_config = config
                self._extract_agents_from_mainpc_config(config)
            else:
                self.pc2_config = config
                self._extract_agents_from_pc2_config(config)
                
        except Exception as e:
            print(f"Error loading {config_type} config: {e}")
    
    def _extract_agents_from_mainpc_config(self, config: Dict[str, Any]):
        """Extract agents from MainPC config."""
        # Process each section that contains agents
        for section_name, section_data in config.items():
            # Skip non-agent sections
            if not isinstance(section_data, list):
                continue
                
            # Process agents in this section
            for agent_data in section_data:
                if not isinstance(agent_data, dict) or 'name' not in agent_data:
                    continue
                    
                name = agent_data.get('name')
                if name is None:
                    continue
                    
                script_path = agent_data.get('script_path', '')
                host = agent_data.get('host', '0.0.0.0')
                port = agent_data.get('port', 0)
                health_port = agent_data.get('health_check_port')
                
                # Create agent info
                agent_info = AgentInfo(
                    name=name,
                    file_path=script_path,
                    host=host,
                    port=port,
                    health_port=health_port
                )
                
                # Add additional info
                agent_info.dependencies = agent_data.get('dependencies', [])
                agent_info.required = agent_data.get('required', False)
                agent_info.params = agent_data.get('params', {}) or {}
                agent_info.source_config = 'mainpc'
                agent_info.source_section = section_name
                
                # Add to agents dictionary
                self.agents[name] = agent_info
    
    def _extract_agents_from_pc2_config(self, config: Dict[str, Any]):
        """Extract agents from PC2 config."""
        # PC2 config has a different structure
        pc2_services = config.get('pc2_services', [])
        
        for agent_data in pc2_services:
            if not isinstance(agent_data, dict) or 'name' not in agent_data:
                continue
                
            name = agent_data.get('name')
            if name is None:
                continue
                
            script_path = agent_data.get('script_path', '')
            host = agent_data.get('host', '0.0.0.0')
            port = agent_data.get('port', 0)
            health_port = agent_data.get('health_check_port')
            
            # Create agent info
            agent_info = AgentInfo(
                name=name,
                file_path=script_path,
                host=host,
                port=port,
                health_port=health_port
            )
            
            # Add additional info
            agent_info.dependencies = agent_data.get('dependencies', [])
            agent_info.required = agent_data.get('required', False)
            agent_info.params = agent_data.get('params', {}) or {}
            agent_info.source_config = 'pc2'
            agent_info.source_section = 'pc2_services'
            
            # Add to agents dictionary
            self.agents[name] = agent_info
    
    def _build_dependency_graph(self):
        """Build the dependency graph."""
        print("Building dependency graph...")
        
        # Add nodes
        for agent_name in self.agents:
            self.dependency_graph.add_node(agent_name)
        
        # Add edges
        for agent_name, agent_info in self.agents.items():
            for dependency in agent_info.dependencies:
                if dependency in self.agents:
                    self.dependency_graph.add_edge(agent_name, dependency)
                else:
                    print(f"Warning: Agent {agent_name} depends on {dependency}, but {dependency} is not defined in any config.")
    
    def check_for_issues(self):
        """Check for issues in the agent configurations."""
        print("Checking for issues...")
        
        issues = []
        
        # Check for duplicate ports
        port_map = {}
        for agent_name, agent_info in self.agents.items():
            if agent_info.port in port_map:
                issues.append(f"Duplicate port {agent_info.port} used by {agent_name} and {port_map[agent_info.port]}")
            else:
                port_map[agent_info.port] = agent_name
                
        # Check for duplicate health ports
        health_port_map = {}
        for agent_name, agent_info in self.agents.items():
            if agent_info.health_port and agent_info.health_port in health_port_map:
                issues.append(f"Duplicate health port {agent_info.health_port} used by {agent_name} and {health_port_map[agent_info.health_port]}")
            elif agent_info.health_port:
                health_port_map[agent_info.health_port] = agent_name
        
        # Check for circular dependencies
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            for cycle in cycles:
                issues.append(f"Circular dependency detected: {' -> '.join(cycle)} -> {cycle[0]}")
        except nx.NetworkXNoCycle:
            pass
        
        # Check for missing dependencies
        for agent_name, agent_info in self.agents.items():
            for dependency in agent_info.dependencies:
                if dependency not in self.agents:
                    issues.append(f"Agent {agent_name} depends on {dependency}, but {dependency} is not defined in any config.")
        
        # Check for script path existence
        for agent_name, agent_info in self.agents.items():
            if agent_info.source_config == 'mainpc':
                full_path = MAIN_PC_CODE / agent_info.file_path
            else:
                full_path = PC2_CODE / agent_info.file_path
                
            if not full_path.exists():
                issues.append(f"Script path for agent {agent_name} does not exist: {agent_info.file_path}")
        
        return issues
    
    def generate_dependency_graph(self):
        """Generate a visualization of the dependency graph."""
        print("Generating dependency graph...")
        
        plt.figure(figsize=(20, 15))
        
        # Use different colors for MainPC and PC2 agents
        mainpc_nodes = [name for name, info in self.agents.items() if info.source_config == 'mainpc']
        pc2_nodes = [name for name, info in self.agents.items() if info.source_config == 'pc2']
        
        # Use hierarchical layout for better visualization
        pos = nx.spring_layout(self.dependency_graph, seed=42)
        
        # Draw MainPC nodes
        nx.draw_networkx_nodes(
            self.dependency_graph, 
            pos, 
            nodelist=mainpc_nodes,
            node_color='lightblue', 
            node_size=500,
            label='MainPC Agents'
        )
        
        # Draw PC2 nodes
        nx.draw_networkx_nodes(
            self.dependency_graph, 
            pos, 
            nodelist=pc2_nodes,
            node_color='lightgreen', 
            node_size=500,
            label='PC2 Agents'
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            self.dependency_graph, 
            pos, 
            edge_color='gray', 
            arrows=True
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            self.dependency_graph, 
            pos, 
            font_size=10
        )
        
        plt.legend()
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(GRAPH_OUTPUT, format='png', dpi=300)
        print(f"Dependency graph saved to {GRAPH_OUTPUT}")
    
    def generate_report(self):
        """Generate a detailed report of all agents."""
        print("Generating agent report...")
        
        # Count agents by source
        mainpc_count = sum(1 for info in self.agents.values() if info.source_config == 'mainpc')
        pc2_count = sum(1 for info in self.agents.values() if info.source_config == 'pc2')
        
        # Count agents by section
        section_counts = {}
        for info in self.agents.values():
            section = f"{info.source_config}:{info.source_section}"
            section_counts[section] = section_counts.get(section, 0) + 1
        
        # Check for issues
        issues = self.check_for_issues()
        
        report = {
            'total_agents': len(self.agents),
            'mainpc_agents': mainpc_count,
            'pc2_agents': pc2_count,
            'section_counts': section_counts,
            'issues': issues,
            'agents': {name: info.to_dict() for name, info in self.agents.items()}
        }
        
        # Save report
        with open(REPORT_OUTPUT, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Agent report saved to {REPORT_OUTPUT}")
        
        # Print summary
        print("\n=== Agent Scanner Summary ===")
        print(f"Total agents found: {len(self.agents)}")
        print(f"MainPC agents: {mainpc_count}")
        print(f"PC2 agents: {pc2_count}")
        print(f"Issues found: {len(issues)}")
        
        # Print issues
        if issues:
            print("\nIssues:")
            for issue in issues:
                print(f"  - {issue}")
        
        print(f"\nDependency graph saved to: {GRAPH_OUTPUT}")
        print(f"Detailed report saved to: {REPORT_OUTPUT}")

def main():
    """Main function."""
    print("=== Agent Scanner ===")
    
    scanner = AgentScanner()
    scanner.scan_configs()
    scanner.generate_dependency_graph()
    scanner.generate_report()
    
    print("\nAgent scanning complete!")

if __name__ == "__main__":
    main() 