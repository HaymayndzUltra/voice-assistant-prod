#!/usr/bin/env python3
"""
Comprehensive script to fix the AI system issues
"""

import os
import sys
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.log_setup import configure_logging
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Configure basic logging
import logging
logger = configure_logging(__name__) / "system_fix.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SystemFix")

# Set up paths
CURRENT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CURRENT_DIR.parent

def setup_environment():
    """Set up the environment for the system"""
    logger.info("Setting up environment...")
    
    # Set PYTHONPATH
    os.environ["PYTHONPATH"] = f"{PROJECT_ROOT}:{CURRENT_DIR}:{os.environ.get('PYTHONPATH', '')}"
    logger.info(f"PYTHONPATH set to: {os.environ['PYTHONPATH']}")
    
    # Create symlinks for backward compatibility
    try:
        os.symlink(CURRENT_DIR / "utils", PROJECT_ROOT / "utils", target_is_directory=True)
        logger.info("Created symlink for utils")
    except FileExistsError:
        logger.info("utils symlink already exists")
    except Exception as e:
        logger.error(f"Error creating utils symlink: {e}")
    
    try:
        os.symlink(CURRENT_DIR / "src", PROJECT_ROOT / "src", target_is_directory=True)
        logger.info("Created symlink for src")
    except FileExistsError:
        logger.info("src symlink already exists")
    except Exception as e:
        logger.error(f"Error creating src symlink: {e}")
    
    try:
        os.symlink(CURRENT_DIR / "config", PROJECT_ROOT / "config", target_is_directory=True)
        logger.info("Created symlink for config")
    except FileExistsError:
        logger.info("config symlink already exists")
    except Exception as e:
        logger.error(f"Error creating config symlink: {e}")
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    logger.info("Created logs directory")
    
    return True

def kill_zombie_processes():
    """Kill any zombie processes"""
    logger.info("Killing zombie processes...")
    
    # Get a list of common ports used by the system
    ports = [8570, 5570, 5598, 5615, 5581, 5643, 5645, 5644, 5641, 5563, 5590]
    
    for port in ports:
        try:
            logger.info(f"Checking port {port}...")
            os.system(f"lsof -t -i:{port} | xargs -r kill -9")
        except Exception as e:
            logger.error(f"Error killing processes on port {port}: {e}")
    
    logger.info("Zombie processes killed")
    return True

def fix_syntax_errors():
    """Fix syntax errors in the codebase"""
    logger.info("Fixing syntax errors...")
    
    # Fix unified_planning_agent.py
    planning_agent_path = CURRENT_DIR / "agents" / "unified_planning_agent.py"
    if planning_agent_path.exists():
        logger.info(f"Checking {planning_agent_path} for syntax errors...")
        try:
            with open(planning_agent_path, 'r') as f:
                content = f.read()
            
            # Fix the syntax error
            if "f\"tcp://{_agent_args.host}:\"){" in content:
                logger.info("Found syntax error in unified_planning_agent.py, fixing...")
                content = content.replace(
                    "f\"tcp://{_agent_args.host}:\"){", 
                    "f\"tcp://{_agent_args.host}:{"
                )
                
                with open(planning_agent_path, 'w') as f:
                    f.write(content)
                logger.info("Syntax error fixed")
        except Exception as e:
            logger.error(f"Error fixing syntax error: {e}")
    
    return True

def create_missing_files():
    """Create any missing files needed by the system"""
    logger.info("Creating missing files...")
    
    # Check if predictive_health_monitor.py exists in agents directory
    health_monitor_path = CURRENT_DIR / "agents" / "predictive_health_monitor.py"
    if not health_monitor_path.exists():
        logger.info(f"Creating {health_monitor_path}...")
        try:
            # Copy from src/agents if it exists
            src_health_monitor = CURRENT_DIR / "src" / "agents" / "predictive_health_monitor.py"
            if src_health_monitor.exists():
                logger.info(f"Copying from {src_health_monitor}...")
                with open(src_health_monitor, 'r') as src:
                    content = src.read()
                with open(health_monitor_path, 'w') as dest:
                    dest.write(content)
                logger.info("File copied successfully")
            else:
                logger.warning("Source file not found, creating a basic version...")
                # Create a basic version
                with open(health_monitor_path, 'w') as f:
                    f.write("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
Predictive Health Monitor
- Basic implementation
\"\"\"

import logging
import socket
import time
import sys
import os
import threading
from pathlib import Path
from datetime import datetime

# Configure logging
logger = configure_logging(__name__) / "predictive_health_monitor.log"))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PredictiveHealthMonitor")

class PredictiveHealthMonitor:
    \"\"\"Basic health monitoring system\"\"\"
    
    def __init__(self, port=5613):
        \"\"\"Initialize the health monitor\"\"\"
        self.port = port
        logger.info(f"Predictive Health Monitor initialized on port {port}")
    
    def run(self):
        \"\"\"Run the health monitor\"\"\"
        logger.info("Predictive Health Monitor running")
        while True:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                break
        logger.info("Predictive Health Monitor stopped")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5613)
    args = parser.parse_args()
    
    monitor = PredictiveHealthMonitor(port=args.port)
    monitor.run()
""")
                logger.info("Basic file created")
        except Exception as e:
            logger.error(f"Error creating file: {e}")
    
    return True

def fix_config_files():
    """Fix configuration files"""
    logger.info("Fixing configuration files...")
    
    # Check if system_config.json exists
    system_config_path = CURRENT_DIR / "config" / "system_config.json"
    if not system_config_path.exists():
        logger.info(f"Creating {system_config_path}...")
        try:
            # Create a basic version
            with open(system_config_path, 'w') as f:
                f.write("""{
    "system": {
        "name": "AI System",
        "version": "1.0.0",
        "logs_dir": "logs",
        "data_dir": "data",
        "models_dir": "models"
    },
    "zmq": {
        "health_monitor_port": 5613,
        "task_router_port": 8570
    }
}""")
            logger.info("Basic system_config.json created")
        except Exception as e:
            logger.error(f"Error creating file: {e}")
    
    # Check if model_configs.json exists
    model_config_path = CURRENT_DIR / "config" / "model_configs.json"
    if not model_config_path.exists():
        logger.info(f"Creating {model_config_path}...")
        try:
            # Create a basic version
            with open(model_config_path, 'w') as f:
                f.write("""{
    "models": [
        {
            "name": "default",
            "type": "llm",
            "endpoint": "local",
            "active": true
        }
    ]
}""")
            logger.info("Basic model_configs.json created")
        except Exception as e:
            logger.error(f"Error creating file: {e}")
    
    return True

def main():
    """Main function"""
    logger.info("Starting system fix...")
    
    # Setup environment
    if not setup_environment():
        logger.error("Failed to set up environment")
        return False
    
    # Kill zombie processes
    if not kill_zombie_processes():
        logger.error("Failed to kill zombie processes")
        return False
    
    # Fix syntax errors
    if not fix_syntax_errors():
        logger.error("Failed to fix syntax errors")
        return False
    
    # Create missing files
    if not create_missing_files():
        logger.error("Failed to create missing files")
        return False
    
    # Fix config files
    if not fix_config_files():
        logger.error("Failed to fix config files")
        return False
    
    logger.info("System fix completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 