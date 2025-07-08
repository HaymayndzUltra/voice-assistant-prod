#!/usr/bin/env python3
"""
Agent Discovery Script

This script helps discover all active agents in the AI system by:
1. Scanning the codebase for BaseAgent implementations
2. Checking for running processes that match agent patterns
3. Analyzing import relationships between files
4. Generating a comprehensive report of all agents

Usage:
    python discover_active_agents.py [--output OUTPUT_FILE] [--scan-dirs DIRS]
"""

import os
import sys
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
import importlib.util

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Default directories to scan
DEFAULT_SCAN_DIRS = [
    "main_pc_code/agents",
    "main_pc_code/src",
    "pc2_code/agents",
    "pc2_code/src"
]

# Agent patterns to look for
AGENT_PATTERNS = [
    r"class\s+(\w+)(?:\(.*?BaseAgent.*?\)|.*?BaseAgent.*?\))",  # Class inheriting from BaseAgent
    r"class\s+(\w+)Agent\s*\(",  # Classes with "Agent" in the name
    r"class\s+(\w+)Service\s*\("  # Classes with "Service" in the name
]

# Patterns for files to exclude
EXCLUDE_PATTERNS = [
    r".*_test\.py$",
    r".*test_.*\.py$",
    r".*_archive/.*",
    r".*/archive/.*",
    r".*/backups/.*",
    r".*/_trash.*",
    r".*/needtoverify/.*"
]

# Words that indicate the class is not an actual agent
NON_AGENT_KEYWORDS = [
    "abstract", "base", "mock", "test", "fake", "dummy", "stub", "helper", "util", "common"
]

def should_exclude_file(file_path: str) -> bool:
    """Check if a file should be excluded based on patterns."""
    for pattern in EXCLUDE_PATTERNS:
        if re.match(pattern, file_path):
            return True
    return False

def find_python_files(directories: List[str]) -> List[str]:
    """Find all Python files in the specified directories."""
    python_files = []
    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            print(f"Warning: Directory {directory} does not exist")
            continue
        
        for file_path in dir_path.glob("**/*.py"):
            file_str = str(file_path)
            if not any(part.startswith('_') for part in file_path.parts) and not should_exclude_file(file_str):
                python_files.append(file_str)
    
    return python_files

def is_real_agent(class_name: str, file_content: str) -> bool:
    """Determine if a class is likely a real agent."""
    # Check if the class name contains any non-agent keywords
    if any(keyword.lower() in class_name.lower() for keyword in NON_AGENT_KEYWORDS):
        return False
    
    # Check if the class is abstract
    if re.search(rf"class\s+{class_name}\s*\([^)]*\):\s*(?:#.*\n\s*)*?[^#\n]*?@abstractmethod", file_content, re.DOTALL):
        return False
    
    # Check if the class is actually implemented (has methods, not just pass)
    class_match = re.search(rf"class\s+{class_name}\s*\(.*?\):(.*?)(?:class|\Z)", file_content, re.DOTALL)
    if class_match:
        class_body = class_match.group(1)
        # If class body only contains pass or docstrings, it's likely not a real agent
        if re.search(r"^\s*(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")?\s*pass\s*$", class_body, re.DOTALL):
            return False
        
        # Check if the class has actual methods
        if not re.search(r"def\s+\w+\s*\(", class_body):
            return False
    
    return True

def extract_agent_info_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Extract agent information from a Python file."""
    agents = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract agent class names
        agent_classes = set()
        for pattern in AGENT_PATTERNS:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                class_name = match.group(1)
                if is_real_agent(class_name, content):
                    agent_classes.add(class_name)
        
        # Extract port information
        port_pattern = r'(?:port|self\.port)\s*=\s*(\d+)'
        port_matches = re.findall(port_pattern, content)
        ports = [int(port) for port in port_matches]
        
        # Extract health check port information
        health_port_pattern = r'(?:health_port|health_check_port|self\.health_port)\s*=\s*(\d+)'
        health_port_matches = re.findall(health_port_pattern, content)
        health_ports = [int(port) for port in health_port_matches]
        
        # Check for error bus integration
        has_error_bus = "error_bus_pub" in content and "error_bus_endpoint" in content
        
        # Check for zmq usage
        uses_zmq = "zmq" in content or "ZMQ" in content
        
        # Check for dependencies
        dependency_pattern = r'dependencies\s*=\s*\[(.*?)\]'
        dependency_matches = re.findall(dependency_pattern, content)
        dependencies = []
        if dependency_matches:
            for match in dependency_matches:
                deps = re.findall(r'[\'"](\w+)[\'"]', match)
                dependencies.extend(deps)
        
        # Create agent entries
        for agent_class in agent_classes:
            agent_info = {
                "name": agent_class,
                "file_path": file_path,
                "ports": ports,
                "health_ports": health_ports,
                "has_error_bus": has_error_bus,
                "uses_zmq": uses_zmq,
                "dependencies": dependencies,
                "machine": "main_pc" if "main_pc_code" in file_path else "pc2" if "pc2_code" in file_path else "unknown"
            }
            agents.append(agent_info)
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return agents

def find_running_agents() -> List[Dict[str, Any]]:
    """Find running agents by checking process list."""
    running_agents = []
    
    try:
        # Get list of Python processes
        result = subprocess.run(
            ["ps", "-ef"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error getting process list: {result.stderr}")
            return running_agents
        
        # Parse output
        for line in result.stdout.splitlines():
            if "python" in line and ("agent" in line.lower() or "service" in line.lower()):
                parts = line.split()
                if len(parts) >= 8:
                    pid = parts[1]
                    cmd = " ".join(parts[7:])
                    
                    # Extract agent name from command
                    agent_name = None
                    for part in cmd.split("/"):
                        if part.endswith(".py"):
                            agent_name = part[:-3]
                            break
                    
                    if agent_name:
                        running_agents.append({
                            "name": agent_name,
                            "pid": pid,
                            "command": cmd,
                            "status": "running"
                        })
    
    except Exception as e:
        print(f"Error finding running agents: {e}")
    
    return running_agents

def analyze_import_relationships(python_files: List[str]) -> Dict[str, Set[str]]:
    """Analyze import relationships between files."""
    imports = {}
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract imported modules
            import_pattern = r'(?:from|import)\s+([\w\.]+)'
            import_matches = re.findall(import_pattern, content)
            
            # Store imports for this file
            imports[file_path] = set(import_matches)
        
        except Exception as e:
            print(f"Error analyzing imports in {file_path}: {e}")
    
    return imports

def find_config_references(python_files: List[str]) -> Dict[str, List[str]]:
    """Find references to configuration files."""
    config_refs = {}
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for config file references
            config_pattern = r'(?:config_path|yaml\.(?:safe_)?load|json\.load).*?[\'"]([^\'"]*/[^\'"]*(?:config|conf)[^\'"]*\.(?:yaml|yml|json))[\'"]'
            config_matches = re.findall(config_pattern, content)
            
            if config_matches:
                config_refs[file_path] = config_matches
        
        except Exception as e:
            print(f"Error finding config references in {file_path}: {e}")
    
    return config_refs

def find_startup_config_files() -> List[str]:
    """Find all startup configuration files in the project."""
    startup_configs = []
    
    for pattern in ["**/startup_config*.yaml", "**/startup_config*.yml", "**/source_of_truth*.yaml", "**/source_of_truth*.yml"]:
        for file_path in project_root.glob(pattern):
            startup_configs.append(str(file_path))
    
    return startup_configs

def extract_agents_from_config(config_file: str) -> List[Dict[str, Any]]:
    """Extract agent information from a configuration file."""
    import yaml
    agents = []
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check different possible structures
        if isinstance(config, dict):
            # Look for agent lists in the config
            for key, value in config.items():
                if isinstance(value, list) and key not in ["settings", "environment", "resource_limits", "volumes", "health_checks", "network"]:
                    for item in value:
                        if isinstance(item, dict) and ("name" in item) and ("script" in item or "script_path" in item):
                            script = item.get("script") or item.get("script_path")
                            agent_info = {
                                "name": item["name"],
                                "script": script,
                                "port": item.get("port"),
                                "health_port": item.get("health_port") or item.get("health_check_port"),
                                "dependencies": item.get("dependencies", []),
                                "critical": item.get("critical", item.get("required", False)),
                                "config_file": config_file
                            }
                            agents.append(agent_info)
            
            # Check for pc2_services structure
            if "pc2_services" in config and isinstance(config["pc2_services"], list):
                for item in config["pc2_services"]:
                    if isinstance(item, dict) and "name" in item:
                        script = item.get("script_path")
                        agent_info = {
                            "name": item["name"],
                            "script": script,
                            "port": item.get("port"),
                            "health_port": item.get("health_check_port"),
                            "dependencies": item.get("dependencies", []),
                            "critical": item.get("required", False),
                            "config_file": config_file
                        }
                        agents.append(agent_info)
    
    except Exception as e:
        print(f"Error extracting agents from {config_file}: {e}")
    
    return agents

def normalize_agent_name(name: str) -> str:
    """Normalize agent name for deduplication."""
    # Remove common suffixes
    name = re.sub(r'(Agent|Service)$', '', name)
    # Convert to lowercase
    return name.lower()

def deduplicate_agents(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate agents based on normalized names and file paths."""
    unique_agents = {}
    
    for agent in agents:
        # Create a unique key based on normalized name and file path
        name = agent["name"]
        norm_name = normalize_agent_name(name)
        file_path = agent.get("file_path", "")
        
        # Skip if the agent is in a test file or archive directory
        if file_path and should_exclude_file(file_path):
            continue
            
        # Use normalized name as key for deduplication
        if norm_name not in unique_agents:
            unique_agents[norm_name] = agent
        else:
            # If we already have this agent, merge the information
            existing = unique_agents[norm_name]
            
            # Keep the original name if it ends with Agent or Service
            if name.endswith(("Agent", "Service")) and not existing["name"].endswith(("Agent", "Service")):
                existing["name"] = name
            
            # Merge file paths
            if "file_path" in agent and "file_path" in existing:
                if isinstance(existing["file_paths"], list):
                    if agent["file_path"] not in existing["file_paths"]:
                        existing["file_paths"].append(agent["file_path"])
                else:
                    existing["file_paths"] = [existing["file_path"], agent["file_path"]]
                    del existing["file_path"]
            
            # Merge ports
            existing["ports"] = list(set(existing["ports"] + agent["ports"]))
            
            # Merge health ports
            existing["health_ports"] = list(set(existing["health_ports"] + agent["health_ports"]))
            
            # Merge error bus status
            existing["has_error_bus"] = existing["has_error_bus"] or agent["has_error_bus"]
            
            # Merge dependencies
            existing["dependencies"] = list(set(existing["dependencies"] + agent["dependencies"]))
            
            # Merge machines
            if "machine" in agent:
                if "machines" in existing:
                    if agent["machine"] not in existing["machines"]:
                        existing["machines"].append(agent["machine"])
                else:
                    existing["machines"] = [existing["machine"], agent["machine"]]
                    if "machine" in existing:
                        del existing["machine"]
    
    # Convert back to list
    return list(unique_agents.values())

def main():
    parser = argparse.ArgumentParser(description="Discover active agents in the AI system")
    parser.add_argument("--output", default="active_agents_report.json", help="Output file for the agent report")
    parser.add_argument("--scan-dirs", nargs="+", default=DEFAULT_SCAN_DIRS, help="Directories to scan for agents")
    args = parser.parse_args()
    
    print(f"Scanning directories: {args.scan_dirs}")
    
    # Find all Python files
    python_files = find_python_files(args.scan_dirs)
    print(f"Found {len(python_files)} Python files")
    
    # Extract agent information from files
    agents = []
    for file_path in python_files:
        agents.extend(extract_agent_info_from_file(file_path))
    
    # Deduplicate agents from code
    agents = deduplicate_agents(agents)
    print(f"Found {len(agents)} potential agents in code")
    
    # Find running agents
    running_agents = find_running_agents()
    print(f"Found {len(running_agents)} running agents")
    
    # Analyze import relationships
    imports = analyze_import_relationships(python_files)
    print(f"Analyzed import relationships for {len(imports)} files")
    
    # Find config references
    config_refs = find_config_references(python_files)
    print(f"Found config references in {len(config_refs)} files")
    
    # Find startup config files
    startup_configs = find_startup_config_files()
    print(f"Found {len(startup_configs)} startup configuration files")
    
    # Extract agents from config files
    config_agents = []
    for config_file in startup_configs:
        config_agents.extend(extract_agents_from_config(config_file))
    print(f"Found {len(config_agents)} agents in configuration files")
    
    # Combine all information
    all_agents = {}
    
    # First, add agents from code
    for agent in agents:
        name = agent["name"]
        if name not in all_agents:
            all_agents[name] = {
                "name": name,
                "file_paths": [agent["file_path"]] if "file_path" in agent else agent.get("file_paths", []),
                "ports": set(agent["ports"]),
                "health_ports": set(agent["health_ports"]),
                "has_error_bus": agent["has_error_bus"],
                "dependencies": set(agent["dependencies"]),
                "machines": [agent["machine"]] if "machine" in agent else agent.get("machines", []),
                "in_config_files": [],
                "running": False
            }
        else:
            # Merge information
            if "file_path" in agent:
                all_agents[name]["file_paths"].append(agent["file_path"])
            elif "file_paths" in agent:
                all_agents[name]["file_paths"].extend(agent["file_paths"])
            
            all_agents[name]["ports"].update(agent["ports"])
            all_agents[name]["health_ports"].update(agent["health_ports"])
            all_agents[name]["has_error_bus"] |= agent["has_error_bus"]
            all_agents[name]["dependencies"].update(agent["dependencies"])
            
            if "machine" in agent and agent["machine"] not in all_agents[name]["machines"]:
                all_agents[name]["machines"].append(agent["machine"])
            elif "machines" in agent:
                for machine in agent["machines"]:
                    if machine not in all_agents[name]["machines"]:
                        all_agents[name]["machines"].append(machine)
    
    # Add config information
    for agent in config_agents:
        name = agent["name"]
        if name not in all_agents:
            all_agents[name] = {
                "name": name,
                "file_paths": [],
                "ports": set(),
                "health_ports": set(),
                "has_error_bus": False,
                "dependencies": set(),
                "machines": [],
                "in_config_files": [agent["config_file"]],
                "running": False
            }
        else:
            all_agents[name]["in_config_files"].append(agent["config_file"])
        
        if agent["script"]:
            script_path = os.path.join(project_root, agent["script"])
            if os.path.exists(script_path) and script_path not in all_agents[name]["file_paths"]:
                all_agents[name]["file_paths"].append(script_path)
        
        if agent["port"]:
            all_agents[name]["ports"].add(agent["port"])
        
        if agent["health_port"]:
            all_agents[name]["health_ports"].add(agent["health_port"])
        
        all_agents[name]["dependencies"].update(agent["dependencies"])
    
    # Add running information
    for agent in running_agents:
        name = agent["name"]
        if name in all_agents:
            all_agents[name]["running"] = True
        else:
            # Try to find a match by checking if the agent name is contained in any known agent
            for known_name in all_agents.keys():
                if name.lower() in known_name.lower() or known_name.lower() in name.lower():
                    all_agents[known_name]["running"] = True
                    break
    
    # Remove duplicate file paths
    for name, agent in all_agents.items():
        agent["file_paths"] = list(dict.fromkeys(agent["file_paths"]))
    
    # Convert sets to lists for JSON serialization
    for name, agent in all_agents.items():
        agent["ports"] = sorted(list(agent["ports"]))
        agent["health_ports"] = sorted(list(agent["health_ports"]))
        agent["dependencies"] = sorted(list(agent["dependencies"]))
    
    # Generate report
    report = {
        "total_agents": len(all_agents),
        "agents_with_error_bus": sum(1 for agent in all_agents.values() if agent["has_error_bus"]),
        "running_agents": sum(1 for agent in all_agents.values() if agent["running"]),
        "agents": list(all_agents.values())
    }
    
    # Write report to file
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to {args.output}")
    print(f"Total agents found: {report['total_agents']}")
    print(f"Agents with error bus integration: {report['agents_with_error_bus']}")
    print(f"Running agents: {report['running_agents']}")
    
    # Print summary of agents by machine
    main_pc_agents = sum(1 for agent in all_agents.values() if "main_pc" in agent["machines"])
    pc2_agents = sum(1 for agent in all_agents.values() if "pc2" in agent["machines"])
    print(f"Main PC agents: {main_pc_agents}")
    print(f"PC2 agents: {pc2_agents}")

if __name__ == "__main__":
    main() 