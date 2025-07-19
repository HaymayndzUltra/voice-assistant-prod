#!/usr/bin/env python3
import os
import sys
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# List of files with syntax errors to fix
files_to_fix = {
    'main_pc_code/agents/model_manager_agent.py': {
        'error_type': 'assignment_to_function_call',
        'line': 662,
        'old': "self.vram_management_config.get('vram_budget_percentage') = 80",
        'new': "self.vram_budget_percentage = 80  # Fixed assignment to function call"
    },
    'main_pc_code/agents/streaming_tts_agent.py': {
        'error_type': 'incomplete_import',
        'line': 2,
        'old': "from main_pc_code.utils.config_loader i",
        'new': "from main_pc_code.utils.config_loader import load_config"
    },
    'main_pc_code/agents/llm_runtime_tools.py': {
        'error_type': 'invalid_inheritance',
        'line': 543,
        'old': "class TelemetryDashboardHandler(BaseAgent)(http.server.SimpleHTTPRequestHandler):",
        'new': "class TelemetryDashboardHandler(BaseAgent, http.server.SimpleHTTPRequestHandler):"
    },
    'main_pc_code/agents/plugin_manager.py': {
        'error_type': 'invalid_inheritance',
        'line': 22,
        'old': "class PluginEventHandler(BaseAgent)(FileSystemEventHandler):",
        'new': "class PluginEventHandler(BaseAgent, FileSystemEventHandler):"
    },
    'main_pc_code/agents/vram_manager copy.py': {
        'error_type': 'invalid_import',
        'line': 10,
        'old': "from dataclasses import dataclass from(BaseAgent) collections import OrderedDict, defaultdict",
        'new': "from dataclasses import dataclass\nfrom collections import OrderedDict, defaultdict"
    }
}

def fix_file(file_path, error_info):
    """Fix syntax errors in a file."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Different fix strategies based on error type
        if error_info['error_type'] == 'assignment_to_function_call':
            content = content.replace(error_info['old'], error_info['new'])
        elif error_info['error_type'] == 'incomplete_import':
            content = content.replace(error_info['old'], error_info['new'])
        elif error_info['error_type'] == 'invalid_inheritance':
            content = content.replace(error_info['old'], error_info['new'])
        elif error_info['error_type'] == 'invalid_import':
            content = content.replace(error_info['old'], error_info['new'])
        
        # Write the fixed content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info(f"Fixed {file_path}")
        return True
    
    except Exception as e:
        logging.error(f"Error fixing {file_path}: {str(e)}")
        return False

def main():
    """Main function to fix syntax errors in files."""
    logging.info("Starting syntax error fixes...")
    
    success_count = 0
    error_count = 0
    
    for file_path, error_info in files_to_fix.items():
        if fix_file(file_path, error_info):
            success_count += 1
        else:
            error_count += 1
    
    logging.info(f"Completed fixing syntax errors. Success: {success_count}, Errors: {error_count}")
    
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 