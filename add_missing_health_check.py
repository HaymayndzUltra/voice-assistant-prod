#!/usr/bin/env python3
"""
Add missing health_check methods to agent files.
This script identifies Python files that inherit from BaseAgent but are missing
the health_check method, and adds a standard implementation.
"""

import os
import re
import sys
import ast
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Set

# Standard health_check method template
HEALTH_CHECK_TEMPLATE = """
    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }
"""

# Imports needed for health_check method
REQUIRED_IMPORTS = [
    "import time",
    "import psutil",
    "from datetime import datetime, timezone, timedelta, date, time as dt_time, tzinfo",
    "from datetime import utcnow",
]

def extract_imports(file_content: str) -> List[str]:
    """Extract import statements from file content."""
    imports = []
    lines = file_content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            imports.append(line)
    return imports

def has_datetime_utcnow_import(imports: List[str]) -> bool:
    """Check if datetime.utcnow is imported."""
    for imp in imports:
        if "datetime" in imp and "utcnow" in imp:
            return True
    return False

def has_psutil_import(imports: List[str]) -> bool:
    """Check if psutil is imported."""
    for imp in imports:
        if "import psutil" in imp:
            return True
    return False

def has_time_import(imports: List[str]) -> bool:
    """Check if time is imported."""
    for imp in imports:
        if imp == "import time" or imp.startswith("from time "):
            return True
    return False

def add_missing_imports(file_content: str) -> str:
    """Add missing imports needed for health_check method."""
    imports = extract_imports(file_content)
    
    # Check for missing imports
    needs_datetime_utcnow = not has_datetime_utcnow_import(imports)
    needs_psutil = not has_psutil_import(imports)
    needs_time = not has_time_import(imports)
    
    # Find the last import statement
    lines = file_content.splitlines()
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(("import ", "from ")):
            last_import_idx = i
    
    # Insert missing imports after the last import
    if last_import_idx >= 0:
        new_imports = []
        if needs_time:
            new_imports.append("import time")
        if needs_psutil:
            new_imports.append("import psutil")
        if needs_datetime_utcnow:
            new_imports.append("from datetime import datetime")
        
        if new_imports:
            lines.insert(last_import_idx + 1, "\n".join(new_imports))
    
    return "\n".join(lines)

def find_class_end(file_content: str, class_name: str) -> int:
    """Find the end position of a class definition."""
    lines = file_content.splitlines()
    in_class = False
    class_indent = 0
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not in_class and stripped.startswith(f"class {class_name}"):
            in_class = True
            class_indent = len(line) - len(stripped)
        elif in_class:
            if line.strip() and len(line) - len(line.lstrip()) <= class_indent:
                # Found a line with same or less indentation than the class definition
                return i
    
    # If we reach here, the class extends to the end of the file
    return len(lines)

def add_health_check_method(file_path: str) -> bool:
    """Add health_check method to a file if it's missing."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the file to find classes that inherit from BaseAgent
        tree = ast.parse(content)
        agent_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    
                    if base_name == "BaseAgent":
                        agent_classes.append(node.name)
        
        if not agent_classes:
            print(f"No BaseAgent classes found in {file_path}")
            return False
        
        # Check if health_check method already exists
        has_health_check = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "health_check":
                has_health_check = True
                break
        
        if has_health_check:
            print(f"health_check method already exists in {file_path}")
            return False
        
        # Add the health_check method to the end of the class
        lines = content.splitlines()
        class_end = find_class_end(content, agent_classes[0])
        
        # Add the health_check method
        lines.insert(class_end, HEALTH_CHECK_TEMPLATE)
        
        # Add missing imports
        new_content = add_missing_imports("\n".join(lines))
        
        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Added health_check method to {file_path}")
        return True
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def find_agent_files(directory: str) -> List[str]:
    """Find all Python files that might be agent files."""
    agent_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                # Simple heuristic: check if the file contains 'Agent' in the name
                # or if it's in an 'agents' directory
                if ('agent' in file.lower() or 
                    'agents' in os.path.basename(root).lower() or
                    'src/core' in os.path.join(root, file).lower()):
                    agent_files.append(file_path)
    return agent_files

def main():
    parser = argparse.ArgumentParser(description='Add missing health_check methods to agent files')
    parser.add_argument('--directory', '-d', default='.', help='Directory to search for agent files')
    parser.add_argument('--file', '-f', help='Process a specific file')
    args = parser.parse_args()
    
    if args.file:
        file_path = os.path.abspath(args.file)
        if os.path.isfile(file_path):
            add_health_check_method(file_path)
        else:
            print(f"File not found: {file_path}")
    else:
        directory = os.path.abspath(args.directory)
        print(f"Searching for agent files in {directory}")
        
        agent_files = find_agent_files(directory)
        print(f"Found {len(agent_files)} potential agent files")
        
        fixed_count = 0
        for file_path in agent_files:
            if add_health_check_method(file_path):
                fixed_count += 1
        
        print(f"Added health_check method to {fixed_count} files")

if __name__ == "__main__":
    main() 