#!/usr/bin/env python3
"""
PC2 Agents Compliance Fixer
---------------------------
Automatically fixes compliance issues in PC2 agents according to architectural standards.

This script:
1. Reads agents from pc2_code/config/startup_config.yaml
2. Adds BaseAgent inheritance
3. Adds proper super().__init__ calls
4. Implements _get_health_status method
5. Converts config_parser to config_loader
6. Standardizes __main__ block
7. Generates a compliance report
"""

import os
import re
import sys
import shutil
import yaml
import ast
from pathlib import Path
import logging
from typing import Dict, List, Set, Tuple, Optional
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pc2_compliance_fixer")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'
PC2_CODEBASE_ROOT = PROJECT_ROOT / 'pc2_code'
PC2_AGENTS_ROOT = PROJECT_ROOT / 'pc2_code' / 'agents'

def create_backup(file_path: Path) -> Path:
    """Create a backup of a file before modifying it."""
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    return backup_path

def gather_agents_from_config(config_path):
    """Gather agents from startup_config.yaml."""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    agents = []
    
    # Process all sections in the config file
    for section_name, section_data in config.items():
        if isinstance(section_data, list):
            for agent in section_data:
                if isinstance(agent, dict) and 'script_path' in agent:
                    agent_name = agent.get('name', os.path.basename(agent['script_path']).split('.')[0])
                    agents.append({
                        'name': agent_name,
                        'script_path': agent['script_path']
                    })
    
    return agents

def add_base_agent_import(content: str) -> str:
    """Add BaseAgent import if it's missing."""
    if 'from main_pc_code.src.core.base_agent import BaseAgent' not in content:
        import_line = 'from main_pc_code.src.core.base_agent import BaseAgent'
        
        # Find a good place to add the import
        import_section_match = re.search(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
        if import_section_match:
            # Add after the last import
            imports = re.findall(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
            last_import = imports[-1]
            last_import_pos = content.find(last_import) + len(last_import)
            content = content[:last_import_pos] + '\n' + import_line + content[last_import_pos:]
        else:
            # If no imports found, add at the top after any comments/docstrings
            first_code_line = re.search(r'^(?:\s*#.*|\s*""".*?"""|[^\n]+)$', content, re.MULTILINE)
            if first_code_line:
                content = content[:first_code_line.end()] + '\n\n' + import_line + content[first_code_line.end():]
            else:
                content = import_line + '\n' + content
    
    return content

def add_config_loader_import(content: str) -> str:
    """Replace config_parser with config_loader."""
    # Remove config_parser import if exists
    content = re.sub(
        r'from\s+(?:main_pc_code\.)?utils\.config_parser\s+import\s+parse_agent_args\n?',
        '',
        content
    )
    
    # Add config_loader import if not already present
    if 'from main_pc_code.utils.config_loader import load_config' not in content:
        import_line = 'from main_pc_code.utils.config_loader import load_config'
        
        # Find a good place to add the import
        import_section_match = re.search(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
        if import_section_match:
            # Add after the last import
            imports = re.findall(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
            last_import = imports[-1]
            last_import_pos = content.find(last_import) + len(last_import)
            content = content[:last_import_pos] + '\n' + import_line + content[last_import_pos:]
        else:
            # If no imports found, add at the top after any comments/docstrings
            first_code_line = re.search(r'^(?:\s*#.*|\s*""".*?"""|[^\n]+)$', content, re.MULTILINE)
            if first_code_line:
                content = content[:first_code_line.end()] + '\n\n' + import_line + content[first_code_line.end():]
            else:
                content = import_line + '\n' + content
    
    # Add config at module level
    if 'config = load_config()' not in content:
        # Find the last import
        imports = re.findall(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
        if imports:
            last_import = imports[-1]
            last_import_pos = content.find(last_import) + len(last_import)
            content = content[:last_import_pos] + '\n\n# Load configuration at the module level\nconfig = load_config()' + content[last_import_pos:]
    
    # Replace usage of config_parser
    content = re.sub(
        r'_agent_args\s*=\s*parse_agent_args\(\)',
        '# Config is loaded at the module level',
        content
    )
    
    # Replace references to _agent_args
    content = re.sub(
        r'_agent_args\.(\w+)',
        r'config.get("\1")',
        content
    )
    
    content = re.sub(
        r'getattr\(_agent_args,\s*[\'"](\w+)[\'"],\s*([^)]+)\)',
        r'config.get("\1", \2)',
        content
    )
    
    return content

def add_base_agent_inheritance(content: str) -> str:
    """Add BaseAgent inheritance to the main class."""
    class_match = re.search(r'class\s+(\w+)(?:\([\w,\s.]*\))?\s*:', content)
    if class_match:
        class_name = class_match.group(1)
        # Check if the class already inherits from BaseAgent
        if f"class {class_name}(BaseAgent)" not in content:
            content = re.sub(
                r'class\s+' + class_name + r'(?:\([\w,\s.]*\))?\s*:',
                f"class {class_name}(BaseAgent):",
                content
            )
    return content

def add_super_init(content: str) -> str:
    """Add super().__init__ call to __init__ method."""
    # Find the class name
    class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseAgent\s*\)\s*:', content)
    if not class_match:
        return content
    
    class_name = class_match.group(1)
    
    # Find the __init__ method
    init_match = re.search(r'def\s+__init__\s*\(self(?:,\s*[^)]*)\)\s*:', content)
    if init_match:
        # Check if super().__init__ is already called
        init_block_start = init_match.end()
        next_def = content.find('def ', init_block_start)
        if next_def == -1:
            next_def = len(content)
        
        init_block = content[init_block_start:next_def]
        
        if 'super().__init__' not in init_block:
            # Extract parameters from __init__
            init_params = re.search(r'def\s+__init__\s*\(self(?:,\s*([^)]*))?\)\s*:', content)
            params = init_params.group(1) if init_params and init_params.group(1) else ''
            
            # Parse parameters to extract port and name
            port_param = re.search(r'port\s*(?::\s*\w+)?\s*=\s*(\d+)', params)
            port_value = port_param.group(1) if port_param else 'None'
            
            # Find first line of method body
            method_body_start = re.search(r'def\s+__init__.*?:\s*(?:\n\s+|$)', content)
            if method_body_start:
                pos = method_body_start.end()
                indentation = re.search(r'(\s+)', content[pos:]).group(1) if re.search(r'(\s+)', content[pos:]) else '    '
                
                # Add super().__init__ call
                super_init_line = f"{indentation}super().__init__(name=\"{class_name}\", port={port_value})\n"
                content = content[:pos] + super_init_line + content[pos:]
    else:
        # If no __init__ found, add one
        indentation = '    '  # Default indentation
        pos = class_match.end()
        
        # Find the correct indentation from other methods
        other_method = re.search(r'(\s+)def\s+\w+', content[pos:])
        if other_method:
            indentation = other_method.group(1)
        
        # Add __init__ method
        init_method = f"\n{indentation}def __init__(self, port: int = None):\n"
        init_method += f"{indentation}    super().__init__(name=\"{class_name}\", port=port)\n"
        init_method += f"{indentation}    self.start_time = time.time()\n"
        
        content = content[:pos] + init_method + content[pos:]
        
        # Also make sure time is imported
        if 'import time' not in content:
            content = add_time_import(content)
    
    return content

def add_time_import(content: str) -> str:
    """Add time import if not present."""
    if 'import time' not in content:
        # Find a good place to add the import
        import_section_match = re.search(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
        if import_section_match:
            # Add after the first import
            first_import = import_section_match.group(1)
            first_import_pos = content.find(first_import) + len(first_import)
            content = content[:first_import_pos] + '\nimport time' + content[first_import_pos:]
        else:
            # If no imports found, add at the top after any comments/docstrings
            first_code_line = re.search(r'^(?:\s*#.*|\s*""".*?"""|[^\n]+)$', content, re.MULTILINE)
            if first_code_line:
                content = content[:first_code_line.end()] + '\nimport time' + content[first_code_line.end():]
            else:
                content = 'import time\n' + content
    
    return content

def add_health_status_method(content: str) -> str:
    """Add _get_health_status method if missing."""
    if '_get_health_status' not in content:
        # Find the class and its indentation level
        class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseAgent\s*\)\s*:', content)
        if not class_match:
            return content
        
        # Find the end of the class
        class_name = class_match.group(1)
        class_start = class_match.start()
        
        # Find the indentation of methods in the class
        method_match = re.search(r'(\s+)def\s+\w+\s*\(', content[class_start:])
        if not method_match:
            indentation = '    '  # Default indentation
        else:
            indentation = method_match.group(1)
        
        # Find where to insert the method
        # Look for the last method in the class
        methods = list(re.finditer(r'(\s+)def\s+(\w+)\s*\(', content))
        if methods:
            last_method = methods[-1]
            last_method_name = last_method.group(2)
            
            # Find the end of the last method
            last_method_pos = last_method.start()
            next_method_match = re.search(r'^\s+def\s+\w+\s*\(', content[last_method_pos + 1:], re.MULTILINE)
            if next_method_match:
                # There's another method, insert before it
                next_method_pos = next_method_match.start() + last_method_pos + 1
                insert_pos = next_method_pos
            else:
                # This is the last method, find where it ends
                # Go to the end of the file or the next class
                next_class = content.find('class ', last_method_pos + 1)
                if next_class == -1:
                    insert_pos = len(content)
                else:
                    insert_pos = next_class
        else:
            # No methods found, insert after the class declaration
            insert_pos = class_match.end()
            
        # Create the health status method
        health_method = f"\n{indentation}def _get_health_status(self) -> dict:\n"
        health_method += f"{indentation}    \"\"\"Return health status information.\"\"\"\n"
        health_method += f"{indentation}    base_status = super()._get_health_status()\n"
        health_method += f"{indentation}    # Add any additional health information specific to {class_name}\n"
        health_method += f"{indentation}    base_status.update({{\n"
        health_method += f"{indentation}        'service': '{class_name}',\n"
        health_method += f"{indentation}        'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,\n"
        health_method += f"{indentation}        'additional_info': {{}}\n"
        health_method += f"{indentation}    }})\n"
        health_method += f"{indentation}    return base_status\n"
        
        content = content[:insert_pos] + health_method + content[insert_pos:]
        
        # Also make sure time is imported
        content = add_time_import(content)
    
    return content

def add_cleanup_method(content: str) -> str:
    """Add cleanup method if missing."""
    if 'def cleanup(' not in content:
        # Find the class and its indentation level
        class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseAgent\s*\)\s*:', content)
        if not class_match:
            return content
        
        # Find the indentation of methods in the class
        method_match = re.search(r'(\s+)def\s+\w+\s*\(', content[class_match.start():])
        if not method_match:
            indentation = '    '  # Default indentation
        else:
            indentation = method_match.group(1)
        
        # Find where to insert the method (end of the class)
        methods = list(re.finditer(r'(\s+)def\s+(\w+)\s*\(', content))
        if methods:
            last_method = methods[-1]
            last_method_name = last_method.group(2)
            
            # Find the end of the last method
            last_method_pos = last_method.start()
            next_method_match = re.search(r'^\s+def\s+\w+\s*\(', content[last_method_pos + 1:], re.MULTILINE)
            if next_method_match:
                next_method_pos = next_method_match.start() + last_method_pos + 1
                insert_pos = next_method_pos
            else:
                next_class = content.find('class ', last_method_pos + 1)
                if next_class == -1:
                    insert_pos = len(content)
                else:
                    insert_pos = next_class
        else:
            insert_pos = class_match.end()
            
        # Create the cleanup method
        cleanup_method = f"\n{indentation}def cleanup(self):\n"
        cleanup_method += f"{indentation}    \"\"\"Clean up resources before shutdown.\"\"\"\n"
        cleanup_method += f"{indentation}    logger.info(\"Cleaning up resources...\")\n"
        cleanup_method += f"{indentation}    # Add specific cleanup code here\n"
        cleanup_method += f"{indentation}    super().cleanup()\n"
        
        content = content[:insert_pos] + cleanup_method + content[insert_pos:]
    
    return content

def standardize_main_block(content: str) -> str:
    """Standardize __main__ block according to the template."""
    # Check if there's already a __main__ block
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', content)
    
    # Find the class name
    class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseAgent\s*\)\s*:', content)
    if not class_match:
        return content
    
    class_name = class_match.group(1)
    
    # Create a standardized __main__ block
    main_block = "\n\nif __name__ == \"__main__\":\n"
    main_block += "    # Standardized main execution block\n"
    main_block += "    agent = None\n"
    main_block += "    try:\n"
    main_block += f"        agent = {class_name}()\n"
    main_block += "        agent.run()\n"
    main_block += "    except KeyboardInterrupt:\n"
    main_block += "        print(f\"Shutting down {agent.name if agent else 'agent'}...\")\n"
    main_block += "    except Exception as e:\n"
    main_block += "        import traceback\n"
    main_block += "        print(f\"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}\")\n"
    main_block += "        traceback.print_exc()\n"
    main_block += "    finally:\n"
    main_block += "        if agent and hasattr(agent, 'cleanup'):\n"
    main_block += "            print(f\"Cleaning up {agent.name}...\")\n"
    main_block += "            agent.cleanup()"
    
    if main_block_match:
        # Replace the existing main block
        main_block_start = main_block_match.start()
        
        # Find where the main block ends (could be end of file or next top-level statement)
        indentation = re.search(r'(\s+)', content[main_block_match.end():]).group(1) if re.search(r'(\s+)', content[main_block_match.end():]) else ''
        next_top_level = re.search(r'\n(?!\s)', content[main_block_match.end():])
        if next_top_level:
            main_block_end = main_block_match.end() + next_top_level.start()
        else:
            main_block_end = len(content)
        
        content = content[:main_block_start] + main_block + content[main_block_end:]
    else:
        # Add main block at the end
        content = content.rstrip() + main_block
    
    return content

def add_run_method(content: str) -> str:
    """Add run method if missing."""
    if 'def run(' not in content:
        # Find the class and its indentation level
        class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseAgent\s*\)\s*:', content)
        if not class_match:
            return content
        
        # Find the indentation of methods in the class
        method_match = re.search(r'(\s+)def\s+\w+\s*\(', content[class_match.start():])
        if not method_match:
            indentation = '    '  # Default indentation
        else:
            indentation = method_match.group(1)
        
        # Find where to insert the method (before cleanup method)
        cleanup_match = re.search(r'(\s+)def\s+cleanup\s*\(', content)
        if cleanup_match:
            insert_pos = cleanup_match.start()
        else:
            # Insert at the end of the class
            methods = list(re.finditer(r'(\s+)def\s+(\w+)\s*\(', content))
            if methods:
                last_method = methods[-1]
                last_method_pos = last_method.start()
                next_method_match = re.search(r'^\s+def\s+\w+\s*\(', content[last_method_pos + 1:], re.MULTILINE)
                if next_method_match:
                    next_method_pos = next_method_match.start() + last_method_pos + 1
                    insert_pos = next_method_pos
                else:
                    next_class = content.find('class ', last_method_pos + 1)
                    if next_class == -1:
                        insert_pos = len(content)
                    else:
                        insert_pos = next_class
            else:
                insert_pos = class_match.end()
        
        # Create the run method
        run_method = f"\n{indentation}def run(self):\n"
        run_method += f"{indentation}    \"\"\"Run the agent's main loop.\"\"\"\n"
        run_method += f"{indentation}    logger.info(f\"Starting {{self.__class__.__name__}} on port {{self.port}}\")\n"
        run_method += f"{indentation}    # Main loop implementation\n"
        run_method += f"{indentation}    try:\n"
        run_method += f"{indentation}        while True:\n"
        run_method += f"{indentation}            # Your main processing logic here\n"
        run_method += f"{indentation}            pass\n"
        run_method += f"{indentation}    except KeyboardInterrupt:\n"
        run_method += f"{indentation}        logger.info(\"Keyboard interrupt received, shutting down...\")\n"
        run_method += f"{indentation}    except Exception as e:\n"
        run_method += f"{indentation}        logger.error(f\"Error in main loop: {{e}}\")\n"
        run_method += f"{indentation}        raise\n"
        
        content = content[:insert_pos] + run_method + content[insert_pos:]
    
    return content

def fix_agent_compliance(agent: dict) -> bool:
    """Fix compliance issues in an agent file."""
    rel_path = agent['script_path']
    abs_path = (PC2_CODEBASE_ROOT / rel_path).resolve()
    
    if not abs_path.exists():
        logger.error(f"File not found: {abs_path}")
        return False
    
    try:
        # Create backup
        backup_path = create_backup(abs_path)
        
        # Read the file
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply fixes
        content = add_base_agent_import(content)
        content = add_config_loader_import(content)
        content = add_base_agent_inheritance(content)
        content = add_super_init(content)
        content = add_health_status_method(content)
        content = add_cleanup_method(content)
        content = add_run_method(content)
        content = standardize_main_block(content)
        
        # Write the updated content
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully fixed compliance for {abs_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing compliance for {abs_path}: {e}")
        return False

def main():
    """Main function to fix compliance for all PC2 agents."""
    # Get agents from config
    try:
        agents = gather_agents_from_config(PC2_CONFIG_PATH)
        logger.info(f"Found {len(agents)} agents in PC2 config")
    except Exception as e:
        logger.error(f"Error loading PC2 config: {e}")
        return 1
    
    if not agents:
        logger.error("No agents found in PC2 config")
        return 1
    
    # Fix compliance for each agent
    success_count = 0
    for agent in agents:
        if fix_agent_compliance(agent):
            success_count += 1
    
    logger.info(f"Successfully fixed compliance for {success_count}/{len(agents)} agents")
    
    # Run compliance check to verify
    print("\nRunning compliance check...")
    os.system(f"python3 {PROJECT_ROOT}/scripts/enhanced_system_audit.py")
    
    return 0 if success_count == len(agents) else 1

if __name__ == "__main__":
    sys.exit(main()) 