#!/usr/bin/env python3
"""
Requirements.txt optimization script for Docker containers
Analyzes Python files to determine actual dependencies and optimizes requirements.txt files
"""
import pathlib
import ast
import re
import json
from collections import defaultdict, Counter
from typing import Set, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Standard library modules (don't need to be in requirements.txt)
STDLIB_MODULES = {
    'os', 'sys', 'json', 'time', 'datetime', 'logging', 'threading', 'multiprocessing',
    'subprocess', 'pathlib', 'collections', 'itertools', 'functools', 'typing',
    'asyncio', 'concurrent', 'queue', 'socket', 'urllib', 'http', 'email',
    'base64', 'hashlib', 'uuid', 're', 'math', 'random', 'string', 'io',
    'csv', 'sqlite3', 'warnings', 'traceback', 'inspect', 'copy', 'pickle',
    'tempfile', 'shutil', 'glob', 'fnmatch', 'argparse', 'configparser'
}

# Mapping from import names to package names
PACKAGE_MAPPING = {
    'cv2': 'opencv-python',
    'PIL': 'Pillow',
    'skimage': 'scikit-image',
    'sklearn': 'scikit-learn', 
    'torch': 'torch',
    'torchvision': 'torchvision',
    'torchaudio': 'torchaudio',
    'transformers': 'transformers',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'matplotlib': 'matplotlib',
    'scipy': 'scipy',
    'requests': 'requests',
    'flask': 'Flask',
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'pydantic': 'pydantic',
    'sqlalchemy': 'SQLAlchemy',
    'zmq': 'pyzmq',
    'redis': 'redis',
    'psutil': 'psutil',
    'docker': 'docker',
    'yaml': 'PyYAML',
    'toml': 'toml',
    'click': 'click',
    'rich': 'rich',
    'tqdm': 'tqdm',
    'websocket': 'websocket-client',
    'aiohttp': 'aiohttp',
    'httpx': 'httpx',
    'boto3': 'boto3',
    'google': 'google-cloud',
    'azure': 'azure',
    'openai': 'openai',
    'anthropic': 'anthropic'
}

def get_imports_from_file(file_path: pathlib.Path) -> Set[str]:
    """Extract import statements from a Python file"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return set()
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Get the top-level module name
                module = alias.name.split('.')[0]
                imports.add(module)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Get the top-level module name
                module = node.module.split('.')[0]
                imports.add(module)
    
    return imports

def get_agent_imports(agent_dir: pathlib.Path) -> Set[str]:
    """Get all imports used by Python files in an agent directory"""
    all_imports = set()
    
    # Check the main agent Python file
    if agent_dir.name.startswith('pc2_'):
        agent_name = agent_dir.name[4:]  # Remove 'pc2_' prefix
        agent_file = ROOT / "pc2_code" / "agents" / f"{agent_name}.py"
    else:
        agent_file = ROOT / "main_pc_code" / "agents" / f"{agent_dir.name}.py"
    
    if agent_file.exists():
        all_imports.update(get_imports_from_file(agent_file))
    
    # Check any Python files in the docker directory itself
    for py_file in agent_dir.rglob("*.py"):
        all_imports.update(get_imports_from_file(py_file))
    
    # Filter out standard library modules and local imports
    external_imports = set()
    for imp in all_imports:
        if imp not in STDLIB_MODULES and not imp.startswith(('main_pc_code', 'pc2_code', 'common')):
            external_imports.add(imp)
    
    return external_imports

def get_package_name(import_name: str) -> str:
    """Convert import name to package name"""
    return PACKAGE_MAPPING.get(import_name, import_name)

def read_requirements(req_file: pathlib.Path) -> List[str]:
    """Read requirements from a requirements.txt file"""
    if not req_file.exists():
        return []
    
    requirements = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            # Remove version constraints for comparison
            package = re.split(r'[>=<~!]', line)[0].strip()
            requirements.append(package)
    
    return requirements

def optimize_requirements_file(agent_dir: pathlib.Path) -> Dict:
    """Optimize requirements.txt for a specific agent"""
    req_file = agent_dir / "requirements.txt"
    
    if not req_file.exists():
        return {"status": "no_requirements_file"}
    
    # Get actual imports used by the agent
    used_imports = get_agent_imports(agent_dir)
    used_packages = {get_package_name(imp) for imp in used_imports}
    
    # Get current requirements
    current_requirements = read_requirements(req_file)
    
    # Find unused requirements
    unused = set(current_requirements) - used_packages
    missing = used_packages - set(current_requirements)
    
    # Create optimized requirements (keep only used packages)
    # Keep some essential packages even if not directly imported
    essential_packages = {'pyzmq', 'redis', 'psutil', 'pydantic'}
    optimized_packages = used_packages | (essential_packages & set(current_requirements))
    
    result = {
        "status": "analyzed",
        "current_count": len(current_requirements),
        "optimized_count": len(optimized_packages),
        "removed": len(unused),
        "unused_packages": list(unused),
        "missing_packages": list(missing),
        "used_imports": list(used_imports),
        "optimized_packages": list(sorted(optimized_packages))
    }
    
    # Write optimized requirements if there are significant changes
    if len(unused) > 2:  # Only optimize if we can remove more than 2 packages
        backup_file = req_file.with_suffix('.txt.backup')
        req_file.rename(backup_file)  # Backup original
        
        with req_file.open('w') as f:
            f.write("# Auto-optimized requirements.txt\n")
            f.write("# Original backed up as requirements.txt.backup\n\n")
            for package in sorted(optimized_packages):
                f.write(f"{package}\n")
        
        result["action"] = "optimized"
    else:
        result["action"] = "no_optimization_needed"
    
    return result

def main():
    """Main function to optimize all requirements.txt files"""
    print("Starting requirements.txt optimization...")
    
    docker_dir = ROOT / "docker"
    results = {}
    
    total_before = 0
    total_after = 0
    total_removed = 0
    
    for agent_dir in docker_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
            continue
        
        req_file = agent_dir / "requirements.txt"
        if not req_file.exists():
            continue
        
        print(f"\nAnalyzing {agent_dir.name}...")
        result = optimize_requirements_file(agent_dir)
        results[agent_dir.name] = result
        
        if result["status"] == "analyzed":
            total_before += result["current_count"]
            total_after += result["optimized_count"]
            total_removed += result["removed"]
            
            print(f"  Current: {result['current_count']} packages")
            print(f"  Optimized: {result['optimized_count']} packages")
            print(f"  Removed: {result['removed']} packages")
            
            if result["action"] == "optimized":
                print(f"  ✓ Optimized requirements.txt")
                if result["unused_packages"]:
                    print(f"    Removed: {', '.join(result['unused_packages'][:5])}")
            else:
                print(f"  - No significant optimization needed")
    
    print(f"\n=== Summary ===")
    print(f"Total packages before: {total_before}")
    print(f"Total packages after: {total_after}")
    print(f"Total packages removed: {total_removed}")
    print(f"Space saved: {total_removed / total_before * 100:.1f}%" if total_before > 0 else "0%")
    
    # Save detailed results
    results_file = ROOT / "scripts" / "requirements_optimization_results.json"
    with results_file.open('w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Detailed results saved to {results_file}")

if __name__ == "__main__":
    main()