#!/usr/bin/env python3
"""
Phase 3 - Batch 2 Configuration Standardization Script
This script refactors 10 agent files to standardize configuration loading.
"""

import os
import re
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Target files for refactoring
TARGET_FILES = [
    "main_pc_code/agents/IntentionValidatorAgent.py",
    "main_pc_code/agents/DynamicIdentityAgent.py",
    "main_pc_code/agents/EmpathyAgent.py",
    "main_pc_code/agents/ProactiveAgent.py",
    "main_pc_code/agents/nlu_agent.py",
    "main_pc_code/agents/advanced_command_handler.py",
    "main_pc_code/agents/chitchat_agent.py",
    "main_pc_code/agents/feedback_handler.py",
    "main_pc_code/agents/responder.py",
    "main_pc_code/agents/streaming_language_analyzer.py",
]

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak"
    try:
        with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        return True
    except Exception as e:
        logger.error(f"Failed to create backup for {file_path}: {e}")
        return False

def standardize_imports(content):
    """Standardize imports for parse_agent_args."""
    # Remove import argparse if present
    content = re.sub(r'import\s+argparse\s*\n', '', content)
    
    # Check for existing parse_agent_args import
    if 'from main_pc_code.utils.config_parser import parse_agent_args' in content:
        pass  # Already has the correct import
    elif 'from utils.config_parser import parse_agent_args' in content:
        # Replace with canonical import
        content = content.replace(
            'from utils.config_parser import parse_agent_args',
            'from main_pc_code.utils.config_parser import parse_agent_args'
        )
    elif 'from utils.config_loader import parse_agent_args' in content:
        # Replace with canonical import
        content = content.replace(
            'from utils.config_loader import parse_agent_args',
            'from main_pc_code.utils.config_parser import parse_agent_args'
        )
    else:
        # Add the import after BaseAgent import or at the top of imports
        base_agent_import = 'from src.core.base_agent import BaseAgent'
        if base_agent_import in content:
            content = content.replace(
                base_agent_import,
                f"{base_agent_import}\nfrom main_pc_code.utils.config_parser import parse_agent_args"
            )
        else:
            # Find a good spot to add the import
            import_section = re.search(r'import\s+.*?\n\n', content, re.DOTALL)
            if import_section:
                end_of_imports = import_section.end()
                content = (
                    content[:end_of_imports] + 
                    "from main_pc_code.utils.config_parser import parse_agent_args\n\n" + 
                    content[end_of_imports:]
                )
            else:
                # Add after the first import
                first_import = re.search(r'import\s+.*?\n', content)
                if first_import:
                    end_of_first_import = first_import.end()
                    content = (
                        content[:end_of_first_import] + 
                        "\nfrom main_pc_code.utils.config_parser import parse_agent_args\n" + 
                        content[end_of_first_import:]
                    )
                else:
                    # Add at the top if no imports found
                    content = "from main_pc_code.utils.config_parser import parse_agent_args\n\n" + content
    
    return content

def add_agent_args_call(content):
    """Add _agent_args = parse_agent_args() at module level if not present."""
    if '_agent_args = parse_agent_args()' in content:
        return content  # Already has the call
    
    # Check for other variants
    if 'args = parse_agent_args()' in content:
        # Replace with standardized name
        content = content.replace('args = parse_agent_args()', '_agent_args = parse_agent_args()')
    else:
        # Add after the imports section
        import_section = re.search(r'import\s+.*?\n\n', content, re.DOTALL)
        if import_section:
            end_of_imports = import_section.end()
            content = (
                content[:end_of_imports] + 
                "_agent_args = parse_agent_args()\n\n" + 
                content[end_of_imports:]
            )
        else:
            # Add after parse_agent_args import
            parse_import = re.search(r'from.*?parse_agent_args.*?\n', content)
            if parse_import:
                end_of_import = parse_import.end()
                content = (
                    content[:end_of_import] + 
                    "\n_agent_args = parse_agent_args()\n" + 
                    content[end_of_import:]
                )
            else:
                # Add at the top if no suitable location found
                content = "from main_pc_code.utils.config_parser import parse_agent_args\n_agent_args = parse_agent_args()\n\n" + content
    
    return content

def standardize_init_method(content, class_name):
    """Standardize the __init__ method to use _agent_args for port and name."""
    # Find the class definition
    class_pattern = rf'class\s+{class_name}\s*\(.*?\):'
    class_match = re.search(class_pattern, content)
    if not class_match:
        logger.warning(f"Could not find class {class_name} definition")
        return content
    
    # Find the __init__ method
    init_pattern = r'def\s+__init__\s*\(self,\s*(.*?)\):'
    init_match = re.search(init_pattern, content[class_match.end():])
    if not init_match:
        logger.warning(f"Could not find __init__ method in {class_name}")
        return content
    
    # Extract the current parameters
    init_params = init_match.group(1)
    init_start = class_match.end() + init_match.start()
    init_end = class_match.end() + init_match.end()
    
    # Create standardized parameters
    if 'port' in init_params and 'name' in init_params:
        # Already has port and name, just add **kwargs if needed
        if '**kwargs' not in init_params:
            standardized_params = init_params + ', **kwargs'
        else:
            standardized_params = init_params
    elif 'port' in init_params:
        # Has port but not name
        if '**kwargs' in init_params:
            standardized_params = init_params.replace('**kwargs', 'name: str = None, **kwargs')
        else:
            standardized_params = init_params + ', name: str = None, **kwargs'
    elif 'name' in init_params:
        # Has name but not port
        if '**kwargs' in init_params:
            standardized_params = init_params.replace('**kwargs', 'port: int = None, **kwargs')
        else:
            standardized_params = init_params + ', port: int = None, **kwargs'
    else:
        # Has neither port nor name
        standardized_params = 'port: int = None, name: str = None, **kwargs'
    
    # Update the method signature
    content = (
        content[:init_start] + 
        f"def __init__(self, {standardized_params}):" + 
        content[init_end:]
    )
    
    # Find the method body
    method_body_start = init_end
    method_body_pattern = r'def\s+\w+\s*\('
    next_method = re.search(method_body_pattern, content[method_body_start:])
    method_body_end = next_method.start() + method_body_start if next_method else len(content)
    method_body = content[method_body_start:method_body_end]
    
    # Check if super().__init__ is called
    super_init_pattern = r'super\(\)\.__init__\s*\((.*?)\)'
    super_init_match = re.search(super_init_pattern, method_body)
    
    # Prepare the standardized super().__init__ call
    agent_port_line = f"agent_port = getattr(_agent_args, 'port', 5000) if port is None else port"
    agent_name_line = f"agent_name = getattr(_agent_args, 'name', '{class_name}') if name is None else name"
    super_init_call = f"super().__init__(port=agent_port, name=agent_name)"
    
    if super_init_match:
        # Replace existing super().__init__ call
        method_body = re.sub(
            super_init_pattern,
            lambda m: f"{agent_port_line}\n        {agent_name_line}\n        {super_init_call}",
            method_body,
            count=1
        )
    else:
        # Add super().__init__ call at the beginning of the method body
        indentation = re.search(r'^(\s+)', method_body)
        indent = indentation.group(1) if indentation else '        '
        method_body = re.sub(
            r'(\s*)(.*?)(\n)',
            f"\\1{agent_port_line}\\3\\1{agent_name_line}\\3\\1{super_init_call}\\3\\1\\2\\3",
            method_body,
            count=1
        )
    
    # Update the content with the modified method body
    content = content[:method_body_start] + method_body + content[method_body_end:]
    
    return content

def refactor_file(file_path):
    """Apply all refactoring steps to a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Extract class name from file path
        file_name = os.path.basename(file_path)
        class_name = os.path.splitext(file_name)[0]
        
        # Handle special cases for class names
        if class_name.endswith('_agent'):
            class_name = class_name.replace('_', ' ').title().replace(' ', '')
        elif file_name == 'nlu_agent.py':
            class_name = 'NLUAgent'
        elif file_name == 'advanced_command_handler.py':
            class_name = 'AdvancedCommandHandler'
        
        # Apply refactoring steps
        content = standardize_imports(content)
        content = add_agent_args_call(content)
        content = standardize_init_method(content, class_name)
        
        # Write the refactored content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"Failed to refactor {file_path}: {e}")
        return False

def main():
    """Main function to refactor all target files."""
    logger.info("Starting Phase 3 - Batch 2 Configuration Standardization")
    
    # Track results
    results = {
        "success": [],
        "failure": []
    }
    
    # Process each target file
    for file_path in TARGET_FILES:
        full_path = os.path.join(os.getcwd(), file_path)
        if not os.path.exists(full_path):
            logger.warning(f"File not found: {full_path}")
            results["failure"].append(file_path)
            continue
        
        logger.info(f"Processing {file_path}")
        
        # Create backup
        if backup_file(full_path):
            # Apply refactoring
            if refactor_file(full_path):
                logger.info(f"Successfully refactored {file_path}")
                results["success"].append(file_path)
            else:
                logger.error(f"Failed to refactor {file_path}")
                results["failure"].append(file_path)
        else:
            results["failure"].append(file_path)
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("Phase 3 - Batch 2 Configuration Standardization Summary")
    logger.info("="*50)
    logger.info(f"Total files processed: {len(TARGET_FILES)}")
    logger.info(f"Successfully refactored: {len(results['success'])}")
    logger.info(f"Failed to refactor: {len(results['failure'])}")
    
    if results["success"]:
        logger.info("\nSuccessfully refactored files:")
        for file in results["success"]:
            logger.info(f"  - {file}")
    
    if results["failure"]:
        logger.info("\nFailed to refactor files:")
        for file in results["failure"]:
            logger.info(f"  - {file}")

if __name__ == "__main__":
    main() 