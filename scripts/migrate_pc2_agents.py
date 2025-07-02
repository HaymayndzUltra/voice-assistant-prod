#!/usr/bin/env python3
"""
PC2 Agent Migration Script
-------------------------
This script migrates agents from PC2 to the main repository while ensuring they follow
architectural standards:
1. Proper BaseAgent inheritance
2. Standardized super().__init__() calls
3. Implementation of _get_health_status method
4. Correct config loader usage (not parser)
5. Standardized __main__ block

The script preserves all business logic and functionality while making the agents compliant.
"""

import os
import re
import sys
import shutil
import argparse
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Configure paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'

# Templates
INIT_TEMPLATE = """    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="{agent_name}")
        {original_init_content}
"""

GET_HEALTH_STATUS_TEMPLATE = """    def _get_health_status(self):
        # Overrides the base method to add agent-specific health metrics
        base_status = super()._get_health_status()
        specific_metrics = {{
            "{agent_type}_status": "active",
            "processed_items": getattr(self, 'processed_items', 0),
            "last_activity_time": getattr(self, 'last_activity_time', 'N/A')
        }}
        base_status.update(specific_metrics)
        return base_status
"""

MAIN_BLOCK_TEMPLATE = """
if __name__ == "__main__":
    agent = None
    try:
        agent = {agent_class}()
        agent.run()
    except KeyboardInterrupt:
        print("Agent interrupted by user")
    except Exception as e:
        print(f"Error running agent: {{e}}")
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
"""

CONFIG_LOADER_IMPORT = "from agents.utils.config_loader import load_config"
CONFIG_LOADER_USAGE = "config = load_config()"
BASE_AGENT_IMPORT = "from src.core.base_agent import BaseAgent"

def parse_args():
    parser = argparse.ArgumentParser(description="Migrate PC2 agents to main repository with architectural compliance")
    parser.add_argument("--agent", help="Specific agent file to migrate (relative to pc2_code/agents)")
    parser.add_argument("--all", action="store_true", help="Migrate all agents")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--output-dir", default=str(MAIN_PC_CODE / 'agents'), 
                       help="Output directory for migrated agents")
    return parser.parse_args()

def find_all_agents() -> List[Path]:
    """Find all Python files in the PC2 agents directory"""
    agents = []
    for root, _, files in os.walk(PC2_CODE / 'agents'):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                agents.append(Path(root) / file)
    return agents

def extract_class_name(source_code: str) -> Optional[str]:
    """Extract the main agent class name from source code"""
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Skip helper classes (usually smaller)
                if len(node.body) > 5:
                    return node.name
        return None
    except Exception as e:
        print(f"Error parsing source code: {e}")
        return None

def extract_original_init_content(source_code: str) -> str:
    """Extract the content of the __init__ method excluding the signature"""
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name == '__init__':
                        # Find the first statement after the method definition
                        if method.body:
                            # Get the source lines for the method body
                            method_source = ast.get_source_segment(source_code, method)
                            if method_source:
                                # Split by lines and remove the method signature
                                lines = method_source.split('\n')
                                # Skip the first line (def __init__...)
                                body_lines = lines[1:]
                                # Remove common indentation
                                if body_lines:
                                    # Find the indentation of the first non-empty line
                                    for line in body_lines:
                                        if line.strip():
                                            indentation = len(line) - len(line.lstrip())
                                            break
                                    else:
                                        indentation = 0
                                    
                                    # Remove that indentation from all lines
                                    body_lines = [line[indentation:] if line.strip() else line for line in body_lines]
                                    
                                    # Skip any existing super().__init__ calls
                                    filtered_lines = []
                                    for line in body_lines:
                                        if not re.search(r'super\(\)\.\_\_init\_\_', line):
                                            filtered_lines.append(line)
                                    
                                    return '\n        '.join(filtered_lines)
        return ""
    except Exception as e:
        print(f"Error extracting __init__ content: {e}")
        return ""

def add_base_agent_inheritance(source_code: str, class_name: str) -> str:
    """Add BaseAgent inheritance to the main class"""
    pattern = rf'class\s+{class_name}\s*\('
    if re.search(pattern, source_code):
        # Class already has inheritance
        return re.sub(pattern, f'class {class_name}(BaseAgent, ', source_code)
    else:
        # Class has no inheritance
        pattern = rf'class\s+{class_name}\s*:'
        return re.sub(pattern, f'class {class_name}(BaseAgent):', source_code)

def add_imports(source_code: str) -> str:
    """Add necessary imports if they don't exist"""
    result = source_code
    
    # Add BaseAgent import if it doesn't exist
    if BASE_AGENT_IMPORT not in result:
        # Find the last import statement
        import_matches = list(re.finditer(r'^(?:import|from)\s+.+$', result, re.MULTILINE))
        if import_matches:
            last_import = import_matches[-1]
            result = (
                result[:last_import.end()] + 
                f"\n{BASE_AGENT_IMPORT}" + 
                result[last_import.end():]
            )
        else:
            # No imports found, add at the beginning after any comments/docstrings
            docstring_end = re.search(r'^""".*?"""', result, re.MULTILINE | re.DOTALL)
            if docstring_end:
                pos = docstring_end.end()
                result = result[:pos] + f"\n\n{BASE_AGENT_IMPORT}" + result[pos:]
            else:
                result = f"{BASE_AGENT_IMPORT}\n\n" + result
    
    # Add config loader import and usage if they don't exist
    if CONFIG_LOADER_IMPORT not in result:
        import_matches = list(re.finditer(r'^(?:import|from)\s+.+$', result, re.MULTILINE))
        if import_matches:
            last_import = import_matches[-1]
            result = (
                result[:last_import.end()] + 
                f"\n{CONFIG_LOADER_IMPORT}" + 
                result[last_import.end():]
            )
        else:
            # No imports found, add after BaseAgent import
            base_agent_pos = result.find(BASE_AGENT_IMPORT)
            if base_agent_pos >= 0:
                pos = base_agent_pos + len(BASE_AGENT_IMPORT)
                result = result[:pos] + f"\n{CONFIG_LOADER_IMPORT}" + result[pos:]
            else:
                docstring_end = re.search(r'^""".*?"""', result, re.MULTILINE | re.DOTALL)
                if docstring_end:
                    pos = docstring_end.end()
                    result = result[:pos] + f"\n\n{CONFIG_LOADER_IMPORT}" + result[pos:]
                else:
                    result = f"{CONFIG_LOADER_IMPORT}\n\n" + result
    
    # Add config loader usage if it doesn't exist
    if CONFIG_LOADER_USAGE not in result:
        # Add after imports but before class definitions
        class_match = re.search(r'^class\s+', result, re.MULTILINE)
        if class_match:
            pos = class_match.start()
            result = result[:pos] + f"{CONFIG_LOADER_USAGE}\n\n" + result[pos:]
        else:
            # No class found, add after imports
            import_matches = list(re.finditer(r'^(?:import|from)\s+.+$', result, re.MULTILINE))
            if import_matches:
                last_import = import_matches[-1]
                result = (
                    result[:last_import.end()] + 
                    f"\n\n{CONFIG_LOADER_USAGE}\n" + 
                    result[last_import.end():]
                )
    
    return result

def replace_init_method(source_code: str, class_name: str, agent_name: str) -> str:
    """Replace the __init__ method with a compliant version that preserves original functionality"""
    original_init_content = extract_original_init_content(source_code)
    
    # Create pattern to match the entire __init__ method
    init_pattern = re.compile(
        rf'(\s+)def\s+__init__\s*\([^)]*\)\s*:(.*?)(?=\n\1\w+|$)',
        re.DOTALL
    )
    
    # Format the new init method
    formatted_agent_name = agent_name.replace('_', ' ').title().replace(' ', '')
    new_init = INIT_TEMPLATE.format(
        agent_name=formatted_agent_name,
        original_init_content=original_init_content
    )
    
    # Find the class definition
    class_match = re.search(rf'class\s+{class_name}\s*(?:\([^)]*\))?\s*:', source_code)
    if not class_match:
        return source_code
    
    # Find the indentation level of the class
    class_end = class_match.end()
    next_line_start = source_code.find('\n', class_end) + 1
    if next_line_start >= len(source_code):
        return source_code
    
    indentation = ''
    for char in source_code[next_line_start:]:
        if char in (' ', '\t'):
            indentation += char
        else:
            break
    
    # Replace the init method
    result = init_pattern.sub(
        lambda m: f"{indentation}def __init__(self, port: int = None, **kwargs):\n"
                 f"{indentation}    super().__init__(port=port, name=\"{formatted_agent_name}\")\n"
                 f"{original_init_content}",
        source_code
    )
    
    return result

def add_health_status_method(source_code: str, class_name: str, agent_name: str) -> str:
    """Add _get_health_status method if it doesn't exist"""
    # Check if _get_health_status already exists
    if re.search(r'def\s+_get_health_status\s*\(', source_code):
        return source_code
    
    # Find the class definition
    class_match = re.search(rf'class\s+{class_name}\s*(?:\([^)]*\))?\s*:', source_code)
    if not class_match:
        return source_code
    
    # Find the end of the class (last method)
    class_methods = list(re.finditer(r'(\s+)def\s+\w+\s*\(', source_code))
    if not class_methods:
        return source_code
    
    last_method = class_methods[-1]
    last_method_indentation = last_method.group(1)
    
    # Find the end of the last method
    last_method_end = source_code.find('\n' + last_method_indentation + 'def', last_method.end())
    if last_method_end == -1:
        # No more methods, find the end of the class
        next_class = re.search(r'\nclass\s+', source_code[last_method.end():])
        if next_class:
            last_method_end = last_method.end() + next_class.start()
        else:
            # No more classes, assume it's the end of the file
            last_method_end = len(source_code)
    
    # Find the end of the last method's body
    method_body_pattern = re.compile(r'(\s+)def\s+\w+\s*\([^)]*\)\s*:(.*?)(?=\n\1\w+|$)', re.DOTALL)
    method_match = method_body_pattern.search(source_code, last_method.start(), last_method_end)
    if not method_match:
        return source_code
    
    method_end = method_match.end()
    
    # Format the health status method
    agent_type = agent_name.split('_')[0] if '_' in agent_name else agent_name
    health_status_method = GET_HEALTH_STATUS_TEMPLATE.format(agent_type=agent_type)
    
    # Insert the health status method
    result = (
        source_code[:method_end] + 
        "\n\n" + last_method_indentation + health_status_method.replace('\n', '\n' + last_method_indentation) + 
        source_code[method_end:]
    )
    
    return result

def replace_main_block(source_code: str, class_name: str) -> str:
    """Replace the __main__ block with a compliant version"""
    # Check if there's an existing __main__ block
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', source_code)
    if not main_block_match:
        # No main block, add one at the end
        new_main_block = MAIN_BLOCK_TEMPLATE.format(agent_class=class_name)
        return source_code + "\n" + new_main_block
    
    # Find the end of the main block
    main_block_start = main_block_match.start()
    next_top_level = re.search(r'\n[^\s]', source_code[main_block_start:])
    if next_top_level:
        main_block_end = main_block_start + next_top_level.start()
    else:
        main_block_end = len(source_code)
    
    # Replace the main block
    new_main_block = MAIN_BLOCK_TEMPLATE.format(agent_class=class_name)
    result = source_code[:main_block_start] + new_main_block + source_code[main_block_end:]
    
    return result

def migrate_agent(agent_path: Path, output_dir: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """Migrate a single agent to be architecturally compliant while preserving functionality"""
    try:
        print(f"Processing {agent_path.relative_to(PC2_CODE)}...")
        
        # Read the source code
        with open(agent_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Extract the agent name and class name
        agent_name = agent_path.stem
        class_name = extract_class_name(source_code)
        if not class_name:
            return False, f"Could not extract class name from {agent_path}"
        
        print(f"  - Found main class: {class_name}")
        
        # Apply transformations
        source_code = add_imports(source_code)
        source_code = add_base_agent_inheritance(source_code, class_name)
        source_code = replace_init_method(source_code, class_name, agent_name)
        source_code = add_health_status_method(source_code, class_name, agent_name)
        source_code = replace_main_block(source_code, class_name)
        
        # Determine the output path
        rel_path = agent_path.relative_to(PC2_CODE / 'agents')
        output_path = output_dir / rel_path
        
        # Create the output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not dry_run:
            # Write the transformed code
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(source_code)
            print(f"  - Migrated to {output_path}")
        else:
            print(f"  - Would migrate to {output_path} (dry run)")
        
        return True, f"Successfully migrated {agent_path.name}"
    except Exception as e:
        return False, f"Error migrating {agent_path.name}: {e}"

def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    
    if not args.agent and not args.all:
        print("Error: Either specify an agent with --agent or use --all to migrate all agents")
        sys.exit(1)
    
    if args.agent:
        # Migrate a single agent
        agent_path = PC2_CODE / 'agents' / args.agent
        if not agent_path.exists():
            print(f"Error: Agent file {agent_path} not found")
            sys.exit(1)
        
        success, message = migrate_agent(agent_path, output_dir, args.dry_run)
        print(message)
        sys.exit(0 if success else 1)
    
    if args.all:
        # Migrate all agents
        agents = find_all_agents()
        print(f"Found {len(agents)} agents to migrate")
        
        results = []
        for agent_path in agents:
            success, message = migrate_agent(agent_path, output_dir, args.dry_run)
            results.append((success, message))
        
        # Print summary
        print("\nMigration Summary:")
        print("-----------------")
        successful = sum(1 for success, _ in results if success)
        print(f"Successfully migrated: {successful}/{len(results)}")
        
        if len(results) - successful > 0:
            print("\nFailed migrations:")
            for success, message in results:
                if not success:
                    print(f"  - {message}")
        
        sys.exit(0 if successful == len(results) else 1)

if __name__ == "__main__":
    main() 