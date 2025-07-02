#!/usr/bin/env python3
import os
import sys
import py_compile
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# List of critical agent files that must have correct syntax
critical_agents = [
    'main_pc_code/agents/model_manager_agent.py',
    'main_pc_code/agents/streaming_tts_agent.py',
    'main_pc_code/agents/DynamicIdentityAgent.py',
    'main_pc_code/agents/streaming_speech_recognition.py',
    'main_pc_code/agents/coordinator_agent.py',
    'main_pc_code/src/core/task_router.py',
    'main_pc_code/agents/knowledge_base.py',
    'main_pc_code/src/memory/memory_client.py',
    'main_pc_code/src/memory/memory_orchestrator.py',
    'pc2_code/agents/memory_manager.py',
    'pc2_code/agents/tiered_responder.py'
]

def check_syntax(file_path):
    """Check Python syntax for a file."""
    try:
        py_compile.compile(file_path, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def main():
    logging.info(f"Checking syntax for {len(critical_agents)} critical agent files")
    
    errors = []
    
    for file_path in critical_agents:
        if os.path.exists(file_path):
            success, error = check_syntax(file_path)
            if success:
                logging.info(f"✓ {file_path}")
            else:
                logging.error(f"✗ {file_path}: {error}")
                errors.append((file_path, error))
        else:
            logging.warning(f"! {file_path} - File not found")
    
    if errors:
        logging.error(f"Found {len(errors)} files with syntax errors:")
        for file_path, error in errors:
            logging.error(f"  - {file_path}: {error}")
        return 1
    else:
        logging.info("All critical agent files passed syntax check!")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 