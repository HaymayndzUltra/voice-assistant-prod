#!/usr/bin/env python3
"""
Add missing _get_health_status methods to agent files.
This script adds the standard _get_health_status method to the specified agent files.
"""

import os
import re
import sys
import ast
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Set

# Standard _get_health_status method template
GET_HEALTH_STATUS_TEMPLATE = """
    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}
"""

def extract_imports(file_content: str) -> List[str]:
    """Extract import statements from file content."""
    imports = []
    lines = file_content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            imports.append(line)
    return imports

def has_time_import(imports: List[str]) -> bool:
    """Check if time is imported."""
    for imp in imports:
        if imp == "import time" or imp.startswith("from time "):
            return True
    return False

def add_missing_imports(file_content: str) -> str:
    """Add missing imports needed for _get_health_status method."""
    imports = extract_imports(file_content)

    # Check for missing imports
    needs_time = not has_time_import(imports)

    # Find the last import statement
    lines = file_content.splitlines()
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(("import ", "from ")):
            last_import_idx = i

    # Insert missing imports after the last import
    if last_import_idx >= 0 and needs_time:
        lines.insert(last_import_idx + 1, "import time")

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

def has_get_health_status_method(file_content: str) -> bool:
    """Check if the file already has a _get_health_status method."""
    pattern = r"def\s+_get_health_status\s*\("
    return bool(re.search(pattern, file_content))

def update_get_health_status_method(file_content: str) -> str:
    """Update an existing _get_health_status method to match the standard format."""
    pattern = r"(def\s+_get_health_status\s*\([^)]*\):)[\s\S]*?(?=\n\s*def|\n\s*$|\Z)"
    return re.sub(pattern, r"\1" + GET_HEALTH_STATUS_TEMPLATE.strip().split("def _get_health_status(self):")[1], file_content)

def add_get_health_status_method(file_path: str) -> bool:
    """Add _get_health_status method to a file if it's missing."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if _get_health_status method already exists
        if has_get_health_status_method(content):
            print(f"Updating _get_health_status method in {file_path}")
            content = update_get_health_status_method(content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        # Parse the file to find the main agent class
        tree = ast.parse(content)
        agent_class = None

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
                        agent_class = node.name
                        break
                if agent_class:
                    break

        if not agent_class:
            print(f"No BaseAgent class found in {file_path}")
            return False

        # Add missing imports if needed
        content = add_missing_imports(content)

        # Add the _get_health_status method to the end of the class
        lines = content.splitlines()
        class_end = find_class_end(content, agent_class)

        # Add the _get_health_status method
        lines.insert(class_end, GET_HEALTH_STATUS_TEMPLATE)

        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        print(f"Added _get_health_status method to {file_path}")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_target_files(target_files: List[str]) -> List[str]:
    """Process the target files and add _get_health_status method."""
    modified_files = []
    for file_path in target_files:
        if add_get_health_status_method(file_path):
            modified_files.append(file_path)
    return modified_files

def main():
    """TODO: Add description for main."""
    parser = argparse.ArgumentParser(description='Add _get_health_status methods to agent files')
    parser.add_argument('--files', '-f', nargs='+', help='List of files to process')
    args = parser.parse_args()

    # Default target files for Batch 2
    default_target_files = [
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/mood_tracker_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_planning_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/MultiAgentSwarmManager.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_connector.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_cache.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_tts_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_interrupt_handler.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/code_generator_agent.py"
    ]

    target_files = args.files if args.files else default_target_files

    print(f"Processing {len(target_files)} target files...")
    modified_files = process_target_files(target_files)

    print(f"\nSummary: Added or updated _get_health_status method in {len(modified_files)} files")
    if modified_files:
        print("\nModified files:")
        for file in modified_files:
            print(f"  - {file}")

    # Show an example implementation
    if modified_files:
        example_file = modified_files[0]
        print(f"\nExample implementation from {example_file}:")
        print(GET_HEALTH_STATUS_TEMPLATE)

if __name__ == "__main__":
    main()
