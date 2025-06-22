"""
Script to help refactor agents to use the new BaseAgent pattern
"""

import os
import re
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_agent_files() -> List[str]:
    """Find all agent Python files."""
    agent_files = []
    for root, _, files in os.walk('agents'):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                agent_files.append(os.path.join(root, file))
    return agent_files

def refactor_agent_file(file_path: str) -> bool:
    """Refactor a single agent file to use BaseAgent."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Skip if already using BaseAgent
        if 'from src.core.base_agent import BaseAgent' in content:
            logger.info(f"Skipping {file_path} - already using BaseAgent")
            return False
            
        # Get agent name from file name
        agent_name = os.path.splitext(os.path.basename(file_path))[0]
        agent_name = ''.join(word.capitalize() for word in agent_name.split('_'))
        
        # Add BaseAgent import
        content = 'from src.core.base_agent import BaseAgent\n' + content
        
        # Update class definition
        class_pattern = r'class\s+(\w+)(?!.*BaseAgent)'
        content = re.sub(class_pattern, f'class \\1(BaseAgent)', content)
        
        # Update __init__
        init_pattern = r'def\s+__init__\s*\([^)]*\)\s*:'
        new_init = f'def __init__(self, port: int = None, **kwargs):\n        super().__init__(port=port, name="{agent_name}")'
        content = re.sub(init_pattern, new_init, content)
        
        # Add _perform_initialization if not exists
        if '_perform_initialization' not in content:
            init_content = """
    def _perform_initialization(self):
        \"\"\"Initialize agent components.\"\"\"
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
"""
            content += init_content
            
        # Write back to file
        with open(file_path, 'w') as f:
            f.write(content)
            
        logger.info(f"Successfully refactored {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error refactoring {file_path}: {e}")
        return False

def main():
    """Main function to refactor all agents."""
    agent_files = find_agent_files()
    logger.info(f"Found {len(agent_files)} agent files to process")
    
    refactored = 0
    for file_path in agent_files:
        if refactor_agent_file(file_path):
            refactored += 1
            
    logger.info(f"Refactored {refactored} out of {len(agent_files)} agent files")

if __name__ == "__main__":
    main() 