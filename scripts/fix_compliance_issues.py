#!/usr/bin/env python3
"""
Fix compliance issues script - systematically resolves all violations found by harden_audit.py
"""
import pathlib
import re
import ast
import json
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Forbidden patterns to fix
FORBIDDEN_PATTERNS = {
    "sys.path.insert": re.compile(r"sys\.path\.insert.*?\n"),
    "logging.basicConfig": re.compile(r"logging\.basicConfig.*?\n")
}

# Required imports to add
REQUIRED_IMPORTS = {
    "env_standardizer": "from common.utils.env_standardizer import get_env",
    "base_agent": "from common.core.base_agent import BaseAgent",
    "log_setup": "from common.utils.log_setup import configure_logging",
}

ERROR_PUBLISHER_IMPORTS = {
    "pc2": "from pc2_code.utils.pc2_error_publisher import PC2ErrorPublisher",
    "main": "from main_pc_code.agents.error_publisher import ErrorPublisher"
}

def fix_forbidden_patterns(file_path: pathlib.Path) -> bool:
    """Remove forbidden patterns from a file"""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    original_content = content
    
    # Remove sys.path.insert lines
    content = FORBIDDEN_PATTERNS["sys.path.insert"].sub("", content)
    
    # Replace logging.basicConfig with proper log_setup
    if "logging.basicConfig" in content:
        # Add log_setup import if not present
        if "from common.utils.log_setup import configure_logging" not in content:
            # Find existing imports section
            lines = content.split('\n')
            import_line_idx = -1
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_line_idx = i
            
            if import_line_idx >= 0:
                lines.insert(import_line_idx + 1, "from common.utils.log_setup import configure_logging")
                content = '\n'.join(lines)
        
        # Replace logging.basicConfig calls
        content = re.sub(
            r'logging\.basicConfig\([^)]*\)',
            'logger = configure_logging(__name__)',
            content
        )
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False

def get_missing_imports(file_path: pathlib.Path, agent_side: str) -> list:
    """Check which required imports are missing from a file"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []
    
    # Get all imports
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    
    missing = []
    
    # Check required imports
    for key, import_path in REQUIRED_IMPORTS.items():
        module_name = import_path.split(' import ')[0].replace('from ', '')
        if module_name not in imports:
            missing.append(import_path)
    
    # Check error publisher
    error_pub_import = ERROR_PUBLISHER_IMPORTS[agent_side]
    error_pub_module = error_pub_import.split(' import ')[0].replace('from ', '')
    if error_pub_module not in imports:
        missing.append(error_pub_import)
    
    return missing

def add_missing_imports(file_path: pathlib.Path, missing_imports: list) -> bool:
    """Add missing imports to a file"""
    if not missing_imports:
        return False
        
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    
    # Find the best place to insert imports (after existing imports)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and insert_idx > 0:
            break
    
    # Insert missing imports
    for import_stmt in missing_imports:
        lines.insert(insert_idx, import_stmt)
        insert_idx += 1
    
    file_path.write_text('\n'.join(lines), encoding='utf-8')
    return True

def fix_agent_file(agent_file: pathlib.Path, agent_side: str):
    """Fix a single agent file"""
    print(f"Fixing {agent_file}...")
    
    # Fix forbidden patterns
    patterns_fixed = fix_forbidden_patterns(agent_file)
    
    # Add missing imports
    missing_imports = get_missing_imports(agent_file, agent_side)
    imports_added = add_missing_imports(agent_file, missing_imports)
    
    if patterns_fixed or imports_added:
        print(f"  ✓ Fixed patterns: {patterns_fixed}, Added imports: {imports_added}")
    else:
        print(f"  - No changes needed")

def main():
    """Main function to fix all compliance issues"""
    print("Starting compliance fix...")
    
    # Get all docker agent directories
    docker_dir = ROOT / "docker"
    
    for agent_dir in docker_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
            continue
            
        # Determine agent side and find python file
        if agent_dir.name.startswith('pc2_'):
            # PC2 agent
            agent_name = agent_dir.name[4:]  # Remove 'pc2_' prefix
            py_file = ROOT / "pc2_code" / "agents" / f"{agent_name}.py"
            agent_side = "pc2"
        else:
            # Main PC agent
            py_file = ROOT / "main_pc_code" / "agents" / f"{agent_dir.name}.py"
            agent_side = "main"
        
        if py_file.exists():
            fix_agent_file(py_file, agent_side)
    
    print("Compliance fix completed!")

if __name__ == "__main__":
    main()