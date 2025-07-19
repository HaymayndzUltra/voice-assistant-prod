#!/usr/bin/env python3
"""
Standardize configuration loading for agent files.
This script implements the refactoring logic for configuration standardization (C6, C7, C8, C9).
"""

import os
import re
import sys
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set

def extract_imports(file_content: str) -> List[str]:
    """Extract import statements from file content."""
    imports = []
    lines = file_content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            imports.append(line)
    return imports

def has_parse_agent_args_import(imports: List[str]) -> bool:
    """Check if parse_agent_args is imported."""
    for imp in imports:
        if "parse_agent_args" in imp:
            return True
    return False

def has_module_level_agent_args(file_content: str) -> bool:
    """Check if _agent_args is defined at the module level."""
    pattern = r"^_agent_args\s*=\s*parse_agent_args\(\)"
    return bool(re.search(pattern, file_content, re.MULTILINE))

def find_class_definition(file_content: str) -> Optional[Tuple[str, int, int]]:
    """Find the main agent class that inherits from BaseAgent."""
    try:
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Look for classes that inherit from BaseAgent
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    
                    if base_name == "BaseAgent":
                        # Return class name and line number
                        return node.name, node.lineno, node.end_lineno
        return None
    except SyntaxError:
        # If there's a syntax error, try a regex approach
        class_pattern = r"class\s+(\w+)\s*\(.*BaseAgent.*\):"
        match = re.search(class_pattern, file_content)
        if match:
            class_name = match.group(1)
            lines = file_content.splitlines()
            for i, line in enumerate(lines):
                if f"class {class_name}" in line and "BaseAgent" in line:
                    return class_name, i + 1, None
        return None

def find_init_method(file_content: str, class_name: str) -> Optional[Tuple[int, int]]:
    """Find the __init__ method in the class."""
    pattern = rf"(\s+)def __init__\s*\(self[^)]*\):"
    match = re.search(pattern, file_content)
    if match:
        # Find the end of the method
        indent = match.group(1)
        start_line = file_content[:match.start()].count('\n') + 1
        lines = file_content.splitlines()[start_line:]
        end_line = start_line
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(indent):
                end_line += i
                break
            if i == len(lines) - 1:
                end_line += i + 1
        return start_line, end_line
    return None

def standardize_config_loading(file_path: str) -> bool:
    """Standardize configuration loading in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Step 1: Canonicalize parse_agent_args import
        imports = extract_imports(content)
        has_parse_args_import = has_parse_agent_args_import(imports)
        
        # Replace old import or add new import
        if has_parse_args_import:
            # Replace old import with canonical import
            content = re.sub(
                r"from\s+utils\.config_parser\s+import\s+parse_agent_args",
                "from main_pc_code.utils.config_parser import parse_agent_args",
                content
            )
        else:
            # Add canonical import after the last import
            last_import_idx = -1
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")):
                    last_import_idx = i
            
            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, "from main_pc_code.utils.config_parser import parse_agent_args")
                content = "\n".join(lines)
        
        # Step 2: Add module-level _agent_args call if missing
        if not has_module_level_agent_args(content):
            # Find a good place to insert it (after imports)
            lines = content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")):
                    insert_idx = i + 1
            
            # Skip empty lines
            while insert_idx < len(lines) and not lines[insert_idx].strip():
                insert_idx += 1
            
            lines.insert(insert_idx, "_agent_args = parse_agent_args()")
            lines.insert(insert_idx + 1, "")  # Add a blank line after
            content = "\n".join(lines)
        
        # Step 3: Find the main agent class
        class_info = find_class_definition(content)
        if not class_info:
            print(f"No BaseAgent class found in {file_path}")
            return False
        
        class_name, _, _ = class_info
        
        # Step 4: Find and modify the __init__ method
        init_info = find_init_method(content, class_name)
        if not init_info:
            print(f"No __init__ method found in {class_name} class in {file_path}")
            return False
        
        # Extract the __init__ method
        start_line, end_line = init_info
        lines = content.splitlines()
        init_lines = lines[start_line-1:end_line]
        
        # Parse the __init__ signature
        init_signature = init_lines[0]
        
        # Check if __init__ already has port and name parameters
        has_port_param = re.search(r"__init__\s*\([^)]*\bport\b", init_signature)
        has_name_param = re.search(r"__init__\s*\([^)]*\bname\b", init_signature)
        
        # Create new __init__ signature
        if "**kwargs" in init_signature:
            # Keep existing signature with kwargs
            new_signature = init_signature
        else:
            # Add port, name, and **kwargs to signature
            if "self" in init_signature and ")" in init_signature:
                new_signature = init_signature.replace("self", "self, port: int = None, name: str = None, **kwargs")
            else:
                # Fallback if we can't parse the signature correctly
                indent = re.match(r"\s*", init_signature).group(0)
                new_signature = f"{indent}def __init__(self, port: int = None, name: str = None, **kwargs):"
        
        # Create new init body with standardized config loading
        indent = re.match(r"\s*", init_lines[0]).group(0)
        new_init_body = []
        
        # Add agent_port and agent_name from _agent_args
        new_init_body.append(new_signature)
        new_init_body.append(f"{indent}    agent_port = _agent_args.get('port', 5000) if port is None else port")
        new_init_body.append(f"{indent}    agent_name = _agent_args.get('name', '{class_name}') if name is None else name")
        new_init_body.append(f"{indent}    super().__init__(port=agent_port, name=agent_name)")
        
        # Add the rest of the init body, skipping the old super().__init__ call
        skip_next_line = False
        for i, line in enumerate(init_lines[1:], 1):
            if skip_next_line:
                skip_next_line = False
                continue
                
            # Skip existing super().__init__ calls
            if "super().__init__" in line:
                skip_next_line = True
                continue
                
            new_init_body.append(line)
        
        # Replace the old __init__ with the new one
        new_content = (
            "\n".join(lines[:start_line-1]) + 
            "\n" + 
            "\n".join(new_init_body) + 
            "\n" + 
            "\n".join(lines[end_line:])
        )
        
        # Remove any import argparse if present
        new_content = re.sub(r"import\s+argparse\s*", "", new_content)
        new_content = re.sub(r"from\s+argparse\s+import[^\\n]*", "", new_content)
        
        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Standardized configuration loading in {file_path}")
        return True
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_target_files(target_files: List[str]) -> List[str]:
    """Process the target files and standardize configuration loading."""
    modified_files = []
    for file_path in target_files:
        if standardize_config_loading(file_path):
            modified_files.append(file_path)
    return modified_files

def main():
    parser = argparse.ArgumentParser(description='Standardize configuration loading in agent files')
    parser.add_argument('--files', '-f', nargs='+', help='List of files to process')
    args = parser.parse_args()
    
    # Default target files for Batch 1
    default_target_files = [
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/NLLBAdapter.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/LearningAdjusterAgent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/LocalFineTunerAgent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/CognitiveModelAgent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/model_manager_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_optimizer_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/coordinator_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/GoalOrchestratorAgent.py"
    ]
    
    target_files = args.files if args.files else default_target_files
    
    print(f"Processing {len(target_files)} target files...")
    modified_files = process_target_files(target_files)
    
    print(f"\nSummary: Standardized configuration loading in {len(modified_files)} files")
    if modified_files:
        print("\nModified files:")
        for file in modified_files:
            print(f"  - {file}")

if __name__ == "__main__":
    main() 