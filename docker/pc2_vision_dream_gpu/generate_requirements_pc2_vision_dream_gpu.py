#!/usr/bin/env python3
"""
Generate requirements for PC2 Vision Dream GPU
Static scan of Python files to auto-detect dependencies
"""

import ast
import os
import sys
from pathlib import Path

def find_imports_in_file(file_path):
    """Extract all imports from a Python file using AST"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        return imports
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set()

def scan_pc2_vision_agents():
    """Scan PC2 vision dream GPU agents for dependencies"""
    workspace = Path("/workspace")
    
    # PC2 vision dream GPU agents
    agent_patterns = [
        "pc2_code/agents/*vision*.py",
        "pc2_code/agents/*dream*.py", 
        "pc2_code/agents/*image*.py",
        "pc2_code/agents/*visual*.py",
        "pc2_code/agents/*face*.py"
    ]
    
    # Also check for any agents mentioned in docker-compose
    compose_file = Path("docker-compose.yml")
    agents_from_compose = []
    
    if compose_file.exists():
        with open(compose_file, 'r') as f:
            content = f.read()
            # Extract agent paths from compose commands
            import re
            matches = re.findall(r'"main_pc_code\.agents\.([^"]+)"', content)
            matches.extend(re.findall(r'"pc2_code\.agents\.([^"]+)"', content))
            for match in matches:
                agent_file = workspace / "pc2_code" / "agents" / f"{match}.py"
                if agent_file.exists():
                    agents_from_compose.append(agent_file)
    
    # Find all agent files
    agent_files = []
    
    # Add agents from compose
    agent_files.extend(agents_from_compose)
    
    # Add pattern-based search
    for pattern in agent_patterns:
        for agent_file in workspace.glob(pattern):
            if agent_file.is_file() and agent_file not in agent_files:
                agent_files.append(agent_file)
    
    # If no specific memory agents found, check all pc2 agents
    if not agent_files:
        pc2_agents_dir = workspace / "pc2_code" / "agents"
        if pc2_agents_dir.exists():
            agent_files = list(pc2_agents_dir.glob("*.py"))
    
    return agent_files

def main():
    print("Analyzing PC2 Vision Dream GPU agents...")
    
    agent_files = scan_pc2_vision_agents()
    all_imports = set()
    
    for agent_file in agent_files:
        print(f"  - {agent_file.relative_to(Path('/workspace'))}")
        imports = find_imports_in_file(agent_file)
        all_imports.update(imports)
    
    # Filter to external packages only
    external_packages = set()
    internal_modules = {'pc2_code', 'main_pc_code', 'common', 'phase1_implementation'}
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'threading', 'logging',
        'pathlib', 'collections', 'typing', 'asyncio', 'sqlite3', 'dataclasses',
        'hashlib', 'uuid', 'pickle', 'socket', 'ssl', 'http', 'urllib', 'email',
        'base64', 'functools', 'itertools', 're', 'math', 'random', 'copy',
        'tempfile', 'shutil', 'subprocess', 'signal', 'gc', 'weakref'
    }
    
    for imp in all_imports:
        if imp not in internal_modules and imp not in stdlib_modules:
            # Map common import names to package names
            package_name = imp
            if imp == 'yaml':
                package_name = 'PyYAML'
            elif imp == 'zmq':
                package_name = 'pyzmq'
            elif imp == 'redis':
                package_name = 'redis'
            elif imp == 'prometheus_client':
                package_name = 'prometheus-client'
            elif imp == 'torch':
                package_name = 'torch==2.1.0'
            
            external_packages.add(package_name)
    
    # Sort packages
    sorted_packages = sorted(external_packages)
    
    # Write requirements.auto.txt
    with open('requirements.auto.txt', 'w') as f:
        for package in sorted_packages:
            f.write(f"{package}\n")
    
    print(f"\n✅ Generated requirements.auto.txt with {len(sorted_packages)} packages:")
    for package in sorted_packages:
        print(f"  - {package}")
    
    print(f"\nFound {len(all_imports)} external imports:")
    for imp in sorted(all_imports - internal_modules - stdlib_modules):
        print(f"  - {imp}")

if __name__ == "__main__":
    main()