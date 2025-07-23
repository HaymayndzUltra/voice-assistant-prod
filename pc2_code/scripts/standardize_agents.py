#!/usr/bin/env python3
"""
PC2 Agents Standardization Script

This script standardizes PC2 agents by:
1. Fixing import patterns for config loading
2. Updating error_bus implementations
3. Standardizing health check patterns
4. Ensuring proper agent initialization

Usage:
    python standardize_agents.py [--dry-run] [--agent <agent_file>]
"""

import os
import sys
import re
import glob
import argparse
import logging
import time  # Import time for health check template
from pathlib import Path
from typing import Dict, List, Set, Optional, Union, Any, Tuple


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Add the project's pc2_code directory to the Python path
PC2_CODE_DIR = get_main_pc_code()
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", "standardize_agents.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StandardizeAgents")

# Templates for standardization
ERROR_BUS_TEMPLATE = """
        self.error_bus = setup_error_reporting(self)
"""

# Define the health check template differently to avoid docstring issues
HEALTH_CHECK_TEMPLATE = (
    '\n    def _get_health_status(self) -> Dict[str, Any]:\n'
    '        """\n'
    '        Get the health status of the agent.\n'
    '        \n'
    '        Returns:\n'
    '            Dict[str, Any]: Health status information\n'
    '        """\n'
    '        return {\n'
    '            "status": "ok",\n'
    '            "uptime": time.time() - self.start_time,\n'
    '            "name": self.name,\n'
    '            "version": getattr(self, "version", "1.0.0"),\n'
    '            "port": self.port,\n'
    '            "health_port": getattr(self, "health_port", None),\n'
    '            "error_reporting": bool(getattr(self, "error_bus", None))\n'
    '        }\n'
)

IMPORT_TEMPLATE = """
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
"""

def find_agents(base_dir: Optional[str] = None) -> List[str]:
    """
    Find all Python files that could be agents in the PC2 codebase.
    
    Args:
        base_dir: Base directory to search
        
    Returns:
        List of file paths to potential agent files
    """
    if base_dir is None:
        base_dir = os.path.join(PC2_CODE_DIR, "agents")
        
    agent_files = []
    
    # Find all Python files in agents directory and subdirectories
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                file_path = os.path.join(root, file)
                # Check if the file contains a class that inherits from BaseAgent
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "BaseAgent" in content and "class" in content:
                            agent_files.append(file_path)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
    
    return agent_files

def parse_agent_file(file_path: str) -> Dict[str, Any]:
    """
    Parse an agent file to extract information needed for standardization.
    
    Args:
        file_path: Path to the agent file
        
    Returns:
        Dictionary of agent information
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract class name (assuming first class in file is the agent)
        class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseAgent\s*\)', content)
        class_name = class_match.group(1) if class_match else None
        
        # Check for error_bus_port usage
        has_error_bus = "error_bus_port" in content
        
        # Check for _get_health_status method
        has_health_status = "_get_health_status" in content
        
        # Check for config import patterns
        config_import_patterns = [
            r'from\s+pc2_code\.utils\.config_loader\s+import',
            r'from\s+pc2_code\.agents\.utils\.config_loader\s+import',
            r'from\s+.*\.config_loader\s+import'
        ]
        has_config_import = any(re.search(pattern, content) for pattern in config_import_patterns)
        
        # Check for parse_agent_args usage
        has_parse_args = "parse_agent_args" in content
        
        # Check for error_bus template import
        has_error_bus_template = "error_bus_template" in content
        
        return {
            "file_path": file_path,
            "class_name": class_name,
            "has_error_bus": has_error_bus,
            "has_health_status": has_health_status,
            "has_config_import": has_config_import,
            "has_parse_args": has_parse_args,
            "has_error_bus_template": has_error_bus_template,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return {
            "file_path": file_path,
            "class_name": None,
            "has_error_bus": False,
            "has_health_status": False,
            "has_config_import": False,
            "has_parse_args": False,
            "has_error_bus_template": False,
            "content": ""
        }

def standardize_agent(agent_info: Dict[str, Any], dry_run: bool = False) -> str:
    """
    Standardize an agent file.
    
    Args:
        agent_info: Agent information from parse_agent_file
        dry_run: If True, don't write changes to disk
        
    Returns:
        Modified file content
    """
    file_path = agent_info["file_path"]
    content = agent_info["content"]
    class_name = agent_info["class_name"]
    
    logger.info(f"Standardizing {os.path.basename(file_path)} ({class_name})")
    
    # Step 1: Fix imports
    if not agent_info["has_config_import"] or not agent_info["has_parse_args"]:
        logger.info(f"Adding/fixing config imports in {file_path}")
        
        # Find the last import line
        import_lines = re.findall(r'^import.*$|^from.*$', content, re.MULTILINE)
        if import_lines:
            last_import = import_lines[-1]
            last_import_pos = content.find(last_import) + len(last_import)
            
            # Insert our imports after the last import
            content = (
                content[:last_import_pos] + 
                "\n\n# Standard imports for PC2 agents" +
                IMPORT_TEMPLATE +
                content[last_import_pos:]
            )
    
    # Step 2: Add parse_agent_args if missing
    if not agent_info["has_parse_args"]:
        logger.info(f"Adding parse_agent_args to {file_path}")
        # Find class definition
        class_match = re.search(f'class\\s+{class_name}\\s*\\(\\s*BaseAgent\\s*\\):\\s*', content)
        if class_match:
            class_def_end = class_match.end()
            # Add _agent_args right after the class definition
            content = (
                content[:class_def_end] + 
                "\n    # Parse agent arguments\n    _agent_args = parse_agent_args()" +
                content[class_def_end:]
            )
    
    # Step 3: Fix error_bus implementation
    if agent_info["has_error_bus"] and not agent_info["has_error_bus_template"]:
        logger.info(f"Fixing error_bus implementation in {file_path}")
        
        # Find and remove old error_bus implementation
        old_error_bus = re.search(
            r'\s+self\.error_bus_port\s*=\s*\d+\s*\n\s+self\.error_bus_host\s*=.*\n\s+self\.error_bus_endpoint\s*=.*\n\s+self\.error_bus_pub\s*=.*\n\s+self\.error_bus_pub\.connect.*\n',
            content
        )
        
        if old_error_bus:
            # Replace with new implementation
            content = content.replace(old_error_bus.group(0), ERROR_BUS_TEMPLATE)
    
    # Step 4: Add health status method if missing
    if not agent_info["has_health_status"]:
        logger.info(f"Adding health status method to {file_path}")
        
        # Find the end of the class definition
        class_end = content.rfind("if __name__ == \"__main__\":")
        if class_end == -1:
            class_end = len(content)
        
        # Add health status method before the end of the class
        content = content[:class_end] + HEALTH_CHECK_TEMPLATE + content[class_end:]
    
    # Write the modified content back to the file
    if not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated {file_path}")
        except Exception as e:
            logger.error(f"Error writing to {file_path}: {e}")
    else:
        logger.info(f"Would update {file_path} (dry run)")
    
    return content

def check_agent_dependencies(startup_config_path: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Check agent dependencies from the startup_config.yaml file.
    
    Args:
        startup_config_path: Path to startup_config.yaml
        
    Returns:
        Dictionary mapping agent names to their dependencies
    """
    if startup_config_path is None:
        startup_config_path = get_file_path("main_pc_config", "startup_config.yaml")
    
    try:
        import yaml
        with open(startup_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        dependencies = {}
        
        # Process PC2 services
        for service in config.get("pc2_services", []):
            name = service.get("name")
            deps = service.get("dependencies", [])
            dependencies[name] = deps
        
        # Check for circular dependencies
        circular_deps = find_circular_dependencies(dependencies)
        if circular_deps:
            logger.warning("Circular dependencies detected:")
            for circular in circular_deps:
                logger.warning(f"  {' -> '.join(circular)}")
        
        return dependencies
    except Exception as e:
        logger.error(f"Error reading startup config: {e}")
        return {}

def find_circular_dependencies(dependencies: Dict[str, List[str]]) -> List[List[str]]:
    """
    Find circular dependencies in the dependency graph.
    
    Args:
        dependencies: Dictionary mapping agent names to their dependencies
        
    Returns:
        List of circular dependency chains
    """
    circular_deps = []
    
    def dfs(node: str, path: Optional[List[str]] = None, visited: Optional[Set[str]] = None) -> None:
        if path is None:
            path = []
        if visited is None:
            visited = set()
            
        if node in path:
            # Found a cycle
            cycle_start = path.index(node)
            circular_deps.append(path[cycle_start:] + [node])
            return
            
        if node in visited:
            return
            
        visited.add(node)
        path.append(node)
        
        for dep in dependencies.get(node, []):
            dfs(dep, path.copy(), visited)
    
    for node in dependencies:
        dfs(node)
    
    return circular_deps

def find_redundant_agents(startup_config_path: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Find agents that might be redundant based on naming or functionality.
    
    Args:
        startup_config_path: Path to startup_config.yaml
        
    Returns:
        List of potentially redundant agents as tuples of (agent1, agent2)
    """
    if startup_config_path is None:
        startup_config_path = get_file_path("main_pc_config", "startup_config.yaml")
    
    try:
        import yaml
        with open(startup_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get all agent names
        agent_names = [service.get("name") for service in config.get("pc2_services", [])]
        
        # Find similar agent names
        redundant = []
        for i, name1 in enumerate(agent_names):
            if not name1:
                continue
            for name2 in agent_names[i+1:]:
                if not name2:
                    continue
                # Check for similar names (e.g., "Agent" vs "AgentService")
                if (name1 in name2 or name2 in name1) and name1 != name2:
                    redundant.append((name1, name2))
        
        return redundant
    except Exception as e:
        logger.error(f"Error finding redundant agents: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Standardize PC2 agents")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes to disk")
    parser.add_argument("--agent", help="Path to a specific agent file to standardize")
    parser.add_argument("--check-dependencies", action="store_true", help="Check for circular dependencies")
    parser.add_argument("--find-redundant", action="store_true", help="Find potentially redundant agents")
    args = parser.parse_args()
    
    # Check dependencies if requested
    if args.check_dependencies:
        logger.info("Checking agent dependencies...")
        dependencies = check_agent_dependencies()
        logger.info(f"Found {len(dependencies)} agents with dependencies")
        
    # Find redundant agents if requested
    if args.find_redundant:
        logger.info("Finding potentially redundant agents...")
        redundant = find_redundant_agents()
        if redundant:
            logger.info("Potentially redundant agents:")
            for name1, name2 in redundant:
                logger.info(f"  {name1} and {name2}")
        else:
            logger.info("No potentially redundant agents found")
    
    # Standardize all agents or a specific one
    if args.agent:
        agent_files = [args.agent]
    else:
        agent_files = find_agents()
    
    logger.info(f"Found {len(agent_files)} agent files to standardize")
    
    for file_path in agent_files:
        agent_info = parse_agent_file(file_path)
        if agent_info["class_name"]:
            standardize_agent(agent_info, args.dry_run)
        else:
            logger.warning(f"No BaseAgent class found in {file_path}")

if __name__ == "__main__":
    main() 