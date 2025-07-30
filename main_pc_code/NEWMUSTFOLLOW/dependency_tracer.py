#!/usr/bin/env python3
"""
MainPC Docker Build Context Dependency Tracer

This script analyzes the active agents defined in startup_config.yaml
and recursively traces their dependencies to generate a definitive list
of directories required for the MainPC Docker build.
"""

import os
import ast
import yaml
import sys
from pathlib import Path
from collections import deque, defaultdict

# Root directory of the repository
REPO_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract all import statements from a Python file."""
    
    def __init__(self):
        self.imports = set()
        
    def visit_Import(self, node):
        for name in node.names:
            self.imports.add(name.name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            # For relative imports, we need to handle the dots
            if node.level > 0:
                self.imports.add('.' * node.level + (node.module or ''))
            else:
                self.imports.add(node.module)
        self.generic_visit(node)


def parse_yaml_config(config_path):
    """Parse the startup configuration YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not config:
            print(f"Warning: Empty or invalid YAML file: {config_path}")
            return {}
        return config
    except Exception as e:
        print(f"Error parsing YAML file {config_path}: {e}")
        return {}


def extract_agent_paths(config):
    """Extract all active agent script paths from the config."""
    agent_paths = []
    
    # Process all agent groups
    for group_name, group_agents in config.get('agent_groups', {}).items():
        if not group_agents:  # Skip if group_agents is None
            continue
        for agent_name, agent_info in group_agents.items():
            # Skip commented out agents
            if isinstance(agent_info, dict) and 'script_path' in agent_info:
                agent_paths.append(agent_info['script_path'])
    
    return agent_paths


def resolve_import_to_file_path(import_name, current_file, visited_paths):
    """
    Resolve an import statement to an actual file path.
    Handles both absolute and relative imports.
    """
    # Skip standard library and third-party imports
    if import_name.split('.')[0] in sys.builtin_module_names:
        return None
        
    current_dir = os.path.dirname(current_file)
    
    # Handle relative imports
    if import_name.startswith('.'):
        dots = 0
        while import_name.startswith('.'):
            dots += 1
            import_name = import_name[1:]
        
        # Navigate up the directory tree based on dot count
        parent_dir = current_dir
        for _ in range(dots - 1):
            parent_dir = os.path.dirname(parent_dir)
            
        # Construct the relative path
        if import_name:
            import_path = os.path.join(parent_dir, import_name.replace('.', os.path.sep))
        else:
            import_path = parent_dir
    else:
        # Handle absolute imports
        # First try as a direct path from repo root
        import_path = os.path.join(REPO_ROOT, import_name.replace('.', os.path.sep))
        
        # If that doesn't exist, try common module paths
        if not (os.path.exists(import_path + '.py') or os.path.exists(os.path.join(import_path, '__init__.py'))):
            for base_dir in ['common', 'src', 'utils', 'main_pc_code', 'pc2_code']:
                test_path = os.path.join(REPO_ROOT, base_dir, import_name.replace('.', os.path.sep))
                if os.path.exists(test_path + '.py') or os.path.exists(os.path.join(test_path, '__init__.py')):
                    import_path = test_path
                    break
    
    # Check if it's a .py file or a directory with __init__.py
    if os.path.exists(import_path + '.py'):
        return import_path + '.py'
    elif os.path.exists(os.path.join(import_path, '__init__.py')):
        return os.path.join(import_path, '__init__.py')
    
    # Try to find the module in common locations
    for ext in ['.py', '/__init__.py']:
        for base_dir in ['', 'common', 'src', 'utils', 'main_pc_code', 'pc2_code']:
            test_path = os.path.join(REPO_ROOT, base_dir, import_name.replace('.', os.path.sep) + ext)
            if os.path.exists(test_path):
                return test_path
    
    return None


def extract_imports_from_file(file_path):
    """Extract all import statements from a Python file using AST or fallback to regex."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
            visitor = ImportVisitor()
            visitor.visit(tree)
            return visitor.imports
        except SyntaxError as e:
            # Fallback to regex-based import extraction
            print(f"AST parsing error in {file_path}: {e}. Using regex fallback.")
            return extract_imports_with_regex(source)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return set()


def extract_imports_with_regex(source_code):
    """Extract imports using regex as a fallback when AST parsing fails."""
    import re
    imports = set()
    
    # Match 'import x' and 'import x as y' patterns
    import_pattern = re.compile(r'^\s*import\s+([\w\.]+)(?:\s+as\s+\w+)?', re.MULTILINE)
    for match in import_pattern.finditer(source_code):
        imports.add(match.group(1).strip())
    
    # Match 'from x import y' patterns
    from_import_pattern = re.compile(r'^\s*from\s+([\.\w]+)\s+import', re.MULTILINE)
    for match in from_import_pattern.finditer(source_code):
        imports.add(match.group(1).strip())
    
    return imports


def trace_dependencies(agent_paths):
    """
    Recursively trace dependencies for all agent scripts.
    Returns a set of all required file paths.
    """
    required_files = set()
    visited_paths = set()
    queue = deque(os.path.join(REPO_ROOT, path) for path in agent_paths)
    
    while queue:
        current_file = queue.popleft()
        
        if current_file in visited_paths or not os.path.exists(current_file):
            continue
            
        visited_paths.add(current_file)
        required_files.add(current_file)
        
        # Extract imports from this file
        imports = extract_imports_from_file(current_file)
        
        # Resolve each import to a file path and add to queue
        for import_name in imports:
            resolved_path = resolve_import_to_file_path(import_name, current_file, visited_paths)
            if resolved_path and resolved_path not in visited_paths:
                queue.append(resolved_path)
    
    return required_files


def get_required_directories(file_paths):
    """
    Derive the minimal set of directories required based on the file paths.
    Returns a set of directory paths relative to the repo root.
    """
    # Group files by directory
    dir_files = defaultdict(list)
    for file_path in file_paths:
        rel_path = os.path.relpath(file_path, REPO_ROOT)
        dir_path = os.path.dirname(rel_path)
        dir_files[dir_path].append(rel_path)
    
    # Find common parent directories
    required_dirs = set()
    
    # First, add top-level directories that must be included in full
    top_level_dirs = {
        'common', 
        'src', 
        'utils', 
        'common_utils',
        'main_pc_code/config', 
        'main_pc_code/agents', 
        'main_pc_code/services', 
        'main_pc_code/FORMAINPC',
        'main_pc_code/integration',
        'main_pc_code/src',
    }
    
    # Add all directories that contain files
    for dir_path in sorted(dir_files.keys()):
        # Skip empty directories
        if not dir_path:
            continue
            
        # Check if this is a subdirectory of a top-level directory
        is_top_level_subdir = False
        for top_dir in top_level_dirs:
            if dir_path == top_dir or dir_path.startswith(top_dir + '/'):
                required_dirs.add(top_dir)
                is_top_level_subdir = True
                break
                
        if not is_top_level_subdir:
            # Add this directory
            required_dirs.add(dir_path)
            
            # Also add parent directories if they're not already included
            parts = dir_path.split('/')
            for i in range(1, len(parts)):
                parent = '/'.join(parts[:i])
                if parent and parent not in required_dirs:
                    required_dirs.add(parent)
    
    return required_dirs


def generate_report(agent_paths, required_directories):
    """Generate a report of the dependency analysis."""
    report = "# Final MainPC Build Context Report\n\n"
    
    report += "## Active Agent Scripts Analyzed\n\n"
    for path in sorted(agent_paths):
        report += f"- {path}\n"
    
    report += "\n## Required Directories for Docker Build\n\n"
    for directory in sorted(required_directories):
        report += f"- {directory}\n"
    
    return report


def main():
    """Main function to run the dependency analysis."""
    config_path = os.path.join(REPO_ROOT, 'main_pc_code/config/startup_config.yaml')
    
    print(f"Parsing config file: {config_path}")
    config = parse_yaml_config(config_path)
    
    print("Extracting agent paths...")
    agent_paths = extract_agent_paths(config)
    print(f"Found {len(agent_paths)} active agent scripts")
    
    print("Tracing dependencies...")
    required_files = trace_dependencies(agent_paths)
    print(f"Found {len(required_files)} required files")
    
    print("Determining required directories...")
    required_dirs = get_required_directories(required_files)
    print(f"Found {len(required_dirs)} required directories")
    
    report = generate_report(agent_paths, required_dirs)
    
    # Save the report to a file
    report_path = os.path.join(REPO_ROOT, 'main_pc_code/NEWMUSTFOLLOW/documents/CASCADE/mainpc_build_context_report.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Report saved to: {report_path}")
    
    # Update the sonnet3.7.md file
    sonnet_path = os.path.join(REPO_ROOT, 'main_pc_code/NEWMUSTFOLLOW/documents/CASCADE/sonnet3.7.md')
    with open(sonnet_path, 'a') as f:
        f.write("\n\n## Operation: Build Lean MainPC Docker Environment\n\n")
        f.write("### Task: Generate Definitive MainPC Build Context via Active Agent Dependency Tracing\n\n")
        f.write("Completed dependency analysis of all active agents in the MainPC system. ")
        f.write("The analysis traced dependencies recursively starting from the active agents ")
        f.write("defined in `main_pc_code/config/startup_config.yaml`.\n\n")
        f.write("The full report has been saved to: `main_pc_code/NEWMUSTFOLLOW/documents/CASCADE/mainpc_build_context_report.md`\n\n")
        f.write("#### Summary of Results:\n")
        f.write(f"- Analyzed {len(agent_paths)} active agent scripts\n")
        f.write(f"- Identified {len(required_files)} required files\n")
        f.write(f"- Determined {len(required_dirs)} required directories for the Docker build\n\n")
        f.write("```\n")
        f.write("# Required Directories for MainPC Docker Build\n")
        for directory in sorted(required_dirs):
            f.write(f"{directory}\n")
        f.write("```\n")


if __name__ == "__main__":
    main() 