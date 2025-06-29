#!/usr/bin/env python3
"""
Fix health_check methods in all agent files.
This script:
1. Adds missing health_check methods to files that don't have them
2. Fixes indentation of existing health_check methods
"""

import os
import re
import sys
import ast
import argparse
from pathlib import Path
from typing import Dict, Any

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

# Improved health_check method template that integrates with BaseAgent's _get_health_status
IMPROVED_HEALTH_CHECK_TEMPLATE = """
    def _get_health_status(self) -> Dict[str, Any]:
        '''
        Get the current health status of the agent.
        '''
        # Get base status from parent class
        status = super()._get_health_status()
        
        try:
            # Add agent-specific health checks
            is_healthy = True  # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here
            # For example, check if required connections are alive
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False
            
            # Update status with agent-specific information
            status.update({
                "status": "ok" if is_healthy else "error",
                "ready": is_healthy,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {}  # Add your agent-specific metrics here
            })
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            status.update({
                "status": "error",
                "ready": False,
                "error": str(e)
            })
            
        return status
        
    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        # This method is for compatibility with the health check validation script
        return self._get_health_status()
"""

def add_missing_imports(content):
    """Add missing imports needed for health_check method."""
    # Check for missing imports
    needs_datetime = "from datetime import datetime" not in content
    needs_psutil = "import psutil" not in content
    needs_time = "import time" not in content
    
    # Add missing imports
    if needs_time or needs_psutil or needs_datetime:
        # Find a good place to add imports
        lines = content.splitlines()
        last_import_idx = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                last_import_idx = i
        
        if last_import_idx >= 0:
            new_imports = []
            if needs_time:
                new_imports.append("import time")
            if needs_psutil:
                new_imports.append("import psutil")
            if needs_datetime:
                new_imports.append("from datetime import datetime")
            
            if new_imports:
                # Insert new imports after the last import
                lines.insert(last_import_idx + 1, "\n".join(new_imports))
                return "\n".join(lines)
    
    return content

def fix_health_check_method(file_path):
    """Fix or add health_check method in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the file has a health_check method or _get_health_status method
        has_health_check = re.search(r'def\s+health_check\s*\(\s*self\s*\)', content) is not None
        has_get_health_status = re.search(r'def\s+_get_health_status\s*\(\s*self\s*\)', content) is not None
        
        # Parse the file to find classes that inherit from BaseAgent
        try:
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
        except SyntaxError:
            print(f"Syntax error in {file_path}, skipping AST parsing")
            # If we can't parse the file, try to find BaseAgent inheritance using regex
            agent_class_match = re.search(r'class\s+(\w+)\s*\(\s*(?:.*?\.)?BaseAgent\s*(?:,|\))', content)
            if agent_class_match:
                agent_classes = [agent_class_match.group(1)]
            else:
                print(f"Could not find BaseAgent class in {file_path}")
                return False
        
        if has_health_check or has_get_health_status:
            # Fix indentation of existing health_check method
            pattern = re.compile(r'(\s*)def\s+(?:health_check|_get_health_status)\s*\(\s*self\s*\):(?:\s*(?:\'\'\'|""")[\s\S]*?(?:\'\'\'|"""))?\s*(.*?)(?=\n\s*def|\n\s*if\s+__name__|\Z)', re.DOTALL)
            match = pattern.search(content)
            
            if match:
                current_indent = match.group(1)
                if current_indent != "    ":
                    # Indentation is wrong, fix it
                    proper_health_check = IMPROVED_HEALTH_CHECK_TEMPLATE.strip()
                    new_content = pattern.sub(proper_health_check, content)
                    new_content = add_missing_imports(new_content)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print(f"Fixed health_check indentation in {file_path}")
                    return True
                else:
                    print(f"health_check method already has correct indentation in {file_path}")
                    return False
            else:
                print(f"Could not find health_check method in {file_path} despite regex match")
                return False
        else:
            # Add health_check method to the end of the class
            class_end_pattern = re.compile(f"class\\s+{agent_classes[0]}.*?\\n(\\s*)(?=\\n\\s*(?:def|class|if\\s+__name__|$))", re.DOTALL)
            match = class_end_pattern.search(content)
            
            if match:
                # Add health_check method
                new_content = add_missing_imports(content)
                new_content = class_end_pattern.sub(f"class {agent_classes[0]}\\1{IMPROVED_HEALTH_CHECK_TEMPLATE}\\1", new_content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"Added health_check method to {file_path}")
                return True
            else:
                print(f"Could not find end of class {agent_classes[0]} in {file_path}")
                return False
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def find_agent_files(directory):
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
    parser = argparse.ArgumentParser(description='Fix health_check methods in agent files')
    parser.add_argument('--directory', '-d', default='.', help='Directory to search for agent files')
    parser.add_argument('--file', '-f', help='Process a specific file')
    parser.add_argument('--missing-files', '-m', help='File containing list of files missing health_check method')
    args = parser.parse_args()
    
    if args.file:
        file_path = os.path.abspath(args.file)
        if os.path.isfile(file_path):
            fix_health_check_method(file_path)
        else:
            print(f"File not found: {file_path}")
    elif args.missing_files:
        with open(args.missing_files, 'r') as f:
            missing_files = [line.strip() for line in f if line.strip()]
        
        fixed_count = 0
        for file_path in missing_files:
            if fix_health_check_method(file_path):
                fixed_count += 1
        
        print(f"Fixed {fixed_count} out of {len(missing_files)} files")
    else:
        directory = os.path.abspath(args.directory)
        print(f"Searching for agent files in {directory}")
        
        agent_files = find_agent_files(directory)
        print(f"Found {len(agent_files)} potential agent files")
        
        fixed_count = 0
        for file_path in agent_files:
            if fix_health_check_method(file_path):
                fixed_count += 1
        
        print(f"Fixed {fixed_count} files")

if __name__ == "__main__":
    main() 