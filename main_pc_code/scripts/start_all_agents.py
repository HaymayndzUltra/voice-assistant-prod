#!/usr/bin/env python3
"""
Script to start all required agents
"""
import subprocess
import time
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

# Network Configuration - since we're on Main PC, use localhost
MAIN_PC_IP = "localhost"
PC2_IP = "localhost"  # We're on Main PC

# Agent configuration with file paths and ports
AGENTS = {
    # Main PC Agents
    "TaskRouter": {
        "file": "src/core/task_router.py",
        "port": 5571
    },
    "EnhancedModelRouter": {
        "file": "FORMAINPC/EnhancedModelRouter.py",
        "port": 8570
    },
    "ChainOfThought": {
        "file": "FORMAINPC/ChainOfThoughtAgent.py",
        "port": 5612
    },
    "CognitiveModel": {
        "file": "FORMAINPC/CognitiveModelAgent.py",
        "port": 5600
    },
    "TinyLlama": {
        "file": "FORMAINPC/TinyLlamaServiceEnhanced.py",
        "port": 5615
    },
    
    # PC2 Agents (also on localhost since we're on Main PC)
    "RemoteConnector": {
        "file": "ForPC2/AuthenticationAgent.py",  # Using AuthenticationAgent as RemoteConnector
        "port": 5557
    },
    "ConsolidatedTranslator": {
        "file": "FORMAINPC/consolidated_translator.py",
        "port": 5563
    }
}

def start_agent(name: str, config: Dict) -> Optional[subprocess.Popen]:
    """Start a single agent"""
    try:
        file_path = Path(config["file"])
        if not file_path.exists():
            logger.error(f"Agent file not found: {file_path}")
            return None
            
        cmd = [sys.executable, str(file_path)]
        
        # Start the agent
        logger.info(f"Starting {name} on port {config['port']}...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Give it a moment to start
        time.sleep(1)
        
        if process.poll() is not None:
            # Process terminated
            out, err = process.communicate()
            logger.error(f"Agent {name} failed to start:")
            if out: logger.error(f"stdout: {out}")
            if err: logger.error(f"stderr: {err}")
            return None
            
        return process
        
    except Exception as e:
        logger.error(f"Error starting {name}: {e}")
        return None

def start_all_agents() -> List[subprocess.Popen]:
    """Start all agents in the correct order"""
    running_processes = []
    
    try:
        # Start Main PC agents first
        main_pc_agents = [
            "TaskRouter",
            "EnhancedModelRouter", 
            "ChainOfThought",
            "CognitiveModel",
            "TinyLlama"
        ]
        
        logger.info("\nStarting Main PC agents...")
        for name in main_pc_agents:
            process = start_agent(name, AGENTS[name])
            if process:
                running_processes.append(process)
            time.sleep(2)  # Wait between starts
            
        # Start PC2 agents
        pc2_agents = [
            "RemoteConnector",
            "ConsolidatedTranslator"
        ]
        
        logger.info("\nStarting PC2 agents...")
        for name in pc2_agents:
            process = start_agent(name, AGENTS[name])
            if process:
                running_processes.append(process)
            time.sleep(2)  # Wait between starts
            
        return running_processes
        
    except Exception as e:
        logger.error(f"Error in start_all_agents: {e}")
        # Clean up any running processes
        for process in running_processes:
            try:
                process.terminate()
            except:
                pass
        return []

def monitor_processes(processes: List[subprocess.Popen]):
    """Monitor running processes and log any that terminate"""
    try:
        while True:
            for process in processes:
                if process.poll() is not None:
                    # Process terminated
                    out, err = process.communicate()
                    logger.warning(f"Process terminated unexpectedly!")
                    if out: logger.warning(f"stdout: {out}")
                    if err: logger.warning(f"stderr: {err}")
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("\nShutting down agents...")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

if __name__ == "__main__":
    try:
        # Start all agents
        running_processes = start_all_agents()
        
        if not running_processes:
            logger.error("No agents were started successfully")
            sys.exit(1)
            
        # Monitor the processes
        monitor_processes(running_processes)
        
    except KeyboardInterrupt:
        logger.info("\nStartup interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Ensure we clean up any running processes
        for process in running_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass 