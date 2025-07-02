#!/usr/bin/env python3
"""
Add Missing Health Check Methods
-------------------------------
Adds health_check methods to agents that don't have them.
This is required for the test framework to work properly.
"""
import os
import re
import yaml
from pathlib import Path
import ast
import astor

# Standard health check implementation to add
HEALTH_CHECK_TEMPLATE = '''
    def health_check(self):
        """Health check method for agent monitoring."""
        status = {
            "status": "healthy",
            "version": "1.0",
            "uptime": self._get_uptime(),
            "memory_usage": self._get_memory_usage(),
            "message_count": getattr(self, "message_count", 0)
        }
        return status
        
    def _get_uptime(self):
        """Get agent uptime in seconds."""
        import time
        return time.time() - getattr(self, "start_time", time.time())
        
    def _get_memory_usage(self):
        """Get memory usage of this process."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)  # MB
'''

def load_active_agents():
    """Load active agents from startup_config.yaml of MainPC and PC2."""
    project_root = Path(__file__).resolve().parent
    mainpc_config = project_root / 'main_pc_code' / 'config' / 'startup_config.yaml'
    pc2_config = project_root / 'pc2_code' / 'config' / 'startup_config.yaml'
    active_agents = []
    
    for config_path, root_dir in [
        (mainpc_config, project_root / 'main_pc_code'),
        (pc2_config, project_root / 'pc2_code')
    ]:
        if not config_path.exists():
            print(f"Config not found: {config_path}")
            continue
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        if not config or 'agents' not in config:
            continue
            
        for agent_name, agent_config in config['agents'].items():
            if 'script_path' in agent_config:
                script_path = agent_config['script_path']
                full_path = root_dir / script_path
                active_agents.append((agent_name, str(full_path)))
    
    return active_agents

def has_health_check(file_path):
    """Check if a file has a health_check method."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Simple regex check
        if re.search(r'def\s+health_check\s*\(', content):
            return True
            
        # More thorough AST check
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == 'health_check':
                    return True
        except SyntaxError:
            # If there's a syntax error, we'll rely on the regex result
            pass
            
        return False
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
        return False

def add_health_check(file_path):
    """Add a health_check method to the file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find the class definition
        class_match = re.search(r'class\s+(\w+)(?:\(.*?\))?:', content)
        if not class_match:
            print(f"No class definition found in {file_path}")
            return False
            
        # Find the end of the class (last method)
        methods = re.finditer(r'    def\s+(\w+)\s*\(', content)
        last_method_end = None
        
        for method in methods:
            method_name = method.group(1)
            method_start = method.start()
            
            # Find the end of this method (next method or end of file)
            next_method = re.search(r'    def\s+\w+\s*\(', content[method_start + 1:])
            if next_method:
                method_end = method_start + 1 + next_method.start() - 1
            else:
                # Find the end of the class (indentation level change)
                lines = content[method_start:].split('\n')
                method_end = method_start
                for i, line in enumerate(lines):
                    if i > 0 and (not line.strip() or not line.startswith('    ')):
                        method_end += len('\n'.join(lines[:i]))
                        break
                else:
                    method_end = len(content)
                    
            last_method_end = method_end
            
        if last_method_end is None:
            # No methods found, add after class definition
            class_end = class_match.end()
            new_content = content[:class_end] + "\n" + HEALTH_CHECK_TEMPLATE + content[class_end:]
        else:
            # Add after the last method
            new_content = content[:last_method_end] + "\n" + HEALTH_CHECK_TEMPLATE + content[last_method_end:]
            
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        return True
    except Exception as e:
        print(f"Error adding health_check to {file_path}: {e}")
        return False

def main():
    print("Adding missing health_check methods to active agents...")
    active_agents = load_active_agents()
    
    added_count = 0
    already_has_count = 0
    error_count = 0
    
    for agent_name, file_path in active_agents:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            error_count += 1
            continue
            
        if has_health_check(file_path):
            print(f"[ALREADY HAS] {agent_name}: {file_path}")
            already_has_count += 1
            continue
            
        print(f"[ADDING] {agent_name}: {file_path}")
        if add_health_check(file_path):
            added_count += 1
        else:
            error_count += 1
            
    print(f"\nSummary:")
    print(f"- Added health_check to {added_count} agents")
    print(f"- {already_has_count} agents already had health_check")
    print(f"- {error_count} errors encountered")
    
if __name__ == "__main__":
    main() 