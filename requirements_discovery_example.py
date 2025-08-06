#!/usr/bin/env python3
"""
Requirements Discovery Example Script
Shows background agent how to analyze and generate complete requirements.txt files
"""

import os
import ast
import subprocess
import sys
from pathlib import Path
from typing import Set, Dict, List
import re

def analyze_imports_in_file(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file using AST"""
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get top-level package name
                    pkg_name = alias.name.split('.')[0]
                    imports.add(pkg_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get top-level package name
                    pkg_name = node.module.split('.')[0]
                    imports.add(pkg_name)
                    
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        
    return imports

def find_agent_files(agent_dir: Path) -> List[Path]:
    """Find all Python files in an agent directory"""
    python_files = []
    
    if agent_dir.exists():
        for file_path in agent_dir.rglob("*.py"):
            # Skip __pycache__ and .git directories
            if "__pycache__" not in str(file_path) and ".git" not in str(file_path):
                python_files.append(file_path)
                
    return python_files

def get_standard_library_modules() -> Set[str]:
    """Get set of Python standard library modules"""
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'logging', 'threading',
        'queue', 'collections', 'itertools', 'functools', 'operator',
        'pathlib', 'subprocess', 'argparse', 'configparser', 'urllib',
        'http', 'socket', 'ssl', 'hashlib', 'uuid', 'random', 'math',
        'statistics', 're', 'string', 'textwrap', 'unicodedata',
        'struct', 'codecs', 'io', 'tempfile', 'shutil', 'glob',
        'pickle', 'sqlite3', 'csv', 'xml', 'html', 'email',
        'asyncio', 'concurrent', 'multiprocessing', 'ctypes',
        'typing', 'dataclasses', 'enum', 'abc', 'copy', 'weakref'
    }
    return stdlib_modules

def filter_third_party_packages(imports: Set[str]) -> Set[str]:
    """Filter out standard library modules and local imports"""
    stdlib = get_standard_library_modules()
    local_modules = {'main_pc_code', 'pc2_code', 'common', 'cleanup', 'scripts'}
    
    third_party = set()
    for pkg in imports:
        if pkg not in stdlib and pkg not in local_modules:
            # Map common package names to PyPI names
            pkg_mapping = {
                'cv2': 'opencv-python',
                'sklearn': 'scikit-learn',
                'PIL': 'Pillow',
                'yaml': 'PyYAML',
                'zmq': 'pyzmq',
                'torch': 'torch',
                'transformers': 'transformers',
                'whisper': 'openai-whisper',
                'numpy': 'numpy',
                'pandas': 'pandas',
                'requests': 'requests',
                'fastapi': 'fastapi',
                'uvicorn': 'uvicorn',
                'pydantic': 'pydantic',
                'redis': 'redis',
                'sqlalchemy': 'SQLAlchemy'
            }
            
            pypi_name = pkg_mapping.get(pkg, pkg)
            third_party.add(pypi_name)
            
    return third_party

def generate_requirements_txt(agent_name: str, packages: Set[str]) -> str:
    """Generate requirements.txt content for an agent"""
    sorted_packages = sorted(packages)
    
    content = f"# Requirements for {agent_name}\n"
    content += f"# Generated automatically - verify versions\n\n"
    
    for package in sorted_packages:
        # Add version constraints for critical packages
        if package in ['torch', 'transformers', 'numpy', 'fastapi']:
            content += f"{package}>=1.0.0\n"
        else:
            content += f"{package}\n"
            
    return content

def analyze_agent_requirements(agent_path: Path) -> Dict[str, any]:
    """Complete requirements analysis for a single agent"""
    result = {
        'agent_name': agent_path.name,
        'python_files': [],
        'imports': set(),
        'third_party_packages': set(),
        'existing_requirements': None,
        'missing_requirements': set()
    }
    
    # Find all Python files
    result['python_files'] = find_agent_files(agent_path)
    print(f"Found {len(result['python_files'])} Python files in {agent_path.name}")
    
    # Analyze imports
    for py_file in result['python_files']:
        file_imports = analyze_imports_in_file(py_file)
        result['imports'].update(file_imports)
    
    # Filter third-party packages
    result['third_party_packages'] = filter_third_party_packages(result['imports'])
    
    # Check existing requirements.txt
    req_file = agent_path / "requirements.txt"
    if req_file.exists():
        with open(req_file, 'r') as f:
            content = f.read()
        result['existing_requirements'] = content
        
        # Parse existing packages
        existing_packages = set()
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove version constraints
                pkg_name = re.split(r'[>=<!=]', line)[0].strip()
                existing_packages.add(pkg_name)
        
        # Find missing packages
        result['missing_requirements'] = result['third_party_packages'] - existing_packages
    else:
        result['missing_requirements'] = result['third_party_packages']
    
    return result

def main():
    """Example usage for requirements discovery"""
    
    # Example: Analyze docker directory
    docker_dir = Path("./docker")
    
    if not docker_dir.exists():
        print("Docker directory not found. Run this from project root.")
        return
    
    print("🔍 REQUIREMENTS DISCOVERY ANALYSIS")
    print("=" * 50)
    
    total_agents = 0
    agents_with_missing_requirements = 0
    all_third_party_packages = set()
    
    for agent_dir in docker_dir.iterdir():
        if agent_dir.is_dir():
            total_agents += 1
            print(f"\n📦 Analyzing {agent_dir.name}...")
            
            analysis = analyze_agent_requirements(agent_dir)
            
            print(f"   Imports found: {len(analysis['imports'])}")
            print(f"   Third-party packages: {len(analysis['third_party_packages'])}")
            print(f"   Missing requirements: {len(analysis['missing_requirements'])}")
            
            if analysis['missing_requirements']:
                agents_with_missing_requirements += 1
                print(f"   ⚠️  Missing packages: {', '.join(sorted(analysis['missing_requirements']))}")
                
                # Generate requirements.txt if missing
                if not (agent_dir / "requirements.txt").exists():
                    req_content = generate_requirements_txt(
                        analysis['agent_name'], 
                        analysis['third_party_packages']
                    )
                    
                    print(f"   ✅ Generated requirements.txt for {agent_dir.name}")
                    # Uncomment to actually write the file:
                    # with open(agent_dir / "requirements.txt", 'w') as f:
                    #     f.write(req_content)
            
            all_third_party_packages.update(analysis['third_party_packages'])
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total agents analyzed: {total_agents}")
    print(f"   Agents with missing requirements: {agents_with_missing_requirements}")
    print(f"   Total unique packages across system: {len(all_third_party_packages)}")
    print(f"   Most common packages: {', '.join(sorted(list(all_third_party_packages))[:10])}")

if __name__ == "__main__":
    main()