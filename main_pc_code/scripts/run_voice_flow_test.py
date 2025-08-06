#!/usr/bin/env python3
"""
Voice Command Flow Test Runner

This script starts all necessary agents for the voice command flow test
and then runs the end-to-end test.
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import logging
from pathlib import Path

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
from common.utils.log_setup import configure_logging

# Add project root to path
current_path = Path(__file__).resolve().parent
project_root = current_path.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'logs', str(PathManager.get_logs_dir() / "voice_flow_test_runner.log")))
    ]
)
logger = logging.getLogger("VoiceFlowTestRunner")

# List of agents required for the test
REQUIRED_AGENTS = [
    {
        "name": "SystemDigitalTwin",
        "module": "main_pc_code.agents.system_digital_twin",
        "required": True,
        "startup_time": 3  # seconds to wait after starting
    },
    {
        "name": "StreamingSpeechRecognition",
        "module": "main_pc_code.agents.streaming_speech_recognition",
        "required": True,
        "startup_time": 2
    },
    {
        "name": "TaskRouter",
        "module": "main_pc_code.agents.task_router",
        "required": True,
        "startup_time": 2
    },
    {
        "name": "Responder",
        "module": "main_pc_code.agents.responder",
        "required": True,
        "startup_time": 2
    },
    {
        "name": "TTSConnector",
        "module": "main_pc_code.agents.tts_connector",
        "required": True,
        "startup_time": 2
    },
    {
        "name": "TTSAgent",
        "module": "main_pc_code.agents.tts_agent",
        "required": False,  # Optional, as we simulate the output
        "startup_time": 2
    }
]

# Global variables to track processes
agent_processes = {}

def start_agent(agent_info):
    """
    Start an agent process.
    
    Args:
        agent_info: Dictionary with agent information
        
    Returns:
        Process object if started successfully, None otherwise
    """
    try:
        logger.info(f"Starting agent: {agent_info['name']}")
        
        # Create log file path
        log_file = os.path.join(project_root, 'logs', f"{agent_info['namestr(PathManager.get_logs_dir() / "].lower()}_test.log"))
        
        # Start the process
        cmd = [sys.executable, "-m", agent_info["module"]]
        
        process = subprocess.Popen(
            cmd,
            stdout=open(log_file, 'w'),
            stderr=subprocess.STDOUT,
            env=dict(os.environ, FORCE_LOCAL_SDT="1")  # Ensure local SDT mode
        )
        
        # Wait for startup time
        logger.info(f"Waiting {agent_info['startup_time']} seconds for {agent_info['name']} to initialize...")
        time.sleep(agent_info['startup_time'])
        
        # Check if process is still running
        if process.poll() is None:
            logger.info(f"Agent {agent_info['name']} started successfully (PID: {process.pid})")
            return process
        else:
            logger.error(f"Agent {agent_info['name']} failed to start (Exit code: {process.returncode})")
            return None
    except Exception as e:
        logger.error(f"Failed to start {agent_info['name']}: {e}")
        return None

def stop_agents():
    """
    Stop all agent processes.
    """
    logger.info("Stopping all agent processes...")
    
    for name, process in agent_processes.items():
        try:
            if process and process.poll() is None:
                logger.info(f"Stopping {name} (PID: {process.pid})...")
                process.send_signal(signal.SIGTERM)
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")
    
    # Give agents time to clean up
    time.sleep(2)
    
    # Force kill any remaining processes
    for name, process in agent_processes.items():
        try:
            if process and process.poll() is None:
                logger.warning(f"Force stopping {name} (PID: {process.pid})...")
                process.kill()
        except Exception as e:
            logger.error(f"Error force stopping {name}: {e}")

def run_test(debug=False):
    """
    Run the voice command flow test.
    
    Args:
        debug: Whether to enable debug logging
    
    Returns:
        True if test passed, False otherwise
    """
    logger.info("Running voice command flow test...")
    
    try:
        # Build command
        cmd = [sys.executable, "-m", "main_pc_code.tests.test_voice_command_flow"]
        
        if debug:
            cmd.append("--debug")
        
        # Run the test
        result = subprocess.run(cmd, cwd=project_root)
        
        if result.returncode == 0:
            logger.info("Voice command flow test PASSED")
            return True
        else:
            logger.error(f"Voice command flow test FAILED (Exit code: {result.returncode})")
            return False
    except Exception as e:
        logger.error(f"Error running voice command flow test: {e}")
        return False

def main():
    """
    Main function.
    """
    parser = argparse.ArgumentParser(description="Voice Command Flow Test Runner")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--skip-agent-start", action="store_true", help="Skip starting agents (assume they're already running)")
    args = parser.parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Start agents if not skipped
        if not args.skip_agent_start:
            logger.info("Starting required agents...")
            
            # Start agents in order
            for agent_info in REQUIRED_AGENTS:
                process = start_agent(agent_info)
                
                if process:
                    agent_processes[agent_info["name"]] = process
                elif agent_info["required"]:
                    logger.error(f"Failed to start required agent {agent_info['name']}. Aborting.")
                    stop_agents()
                    return 1
            
            logger.info("All required agents started successfully")
        else:
            logger.info("Skipping agent startup - assuming agents already running")
        
        # Run the test
        test_success = run_test(debug=args.debug)
        
        # Stop agents if we started them
        if not args.skip_agent_start:
            stop_agents()
        
        # Return appropriate exit code
        return 0 if test_success else 1
    
    except KeyboardInterrupt:
        logger.info("Test runner interrupted")
        stop_agents()
        return 1
    except Exception as e:
        logger.error(f"Error in test runner: {e}")
        stop_agents()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 