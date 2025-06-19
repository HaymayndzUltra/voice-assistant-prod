#!/usr/bin/env python3
"""
System Launcher for Voice Assistant
-----------------------------------
Launches all active agents in the correct order with proper dependency management
Last Updated: 2025-06-06
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/launcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SystemLauncher')

# Agent groups and their dependencies based on latest SOT
AGENT_GROUPS = {
    "core_models": {
        "agents": [
            {"name": "TinyLlama Service", "script": "tinyllama_service_enhanced.py", "port": 5615}
        ],
        "dependencies": []
    },
    "memory": {
        "agents": [
            {"name": "Memory Agent", "script": "memory.py", "port": 5590},
            {"name": "Memory Agent Health", "script": "memory.py", "port": 5598},
            {"name": "Contextual Memory", "script": "contextual_memory_agent.py", "port": 5596},
            {"name": "Digital Twin", "script": "digital_twin_agent.py", "port": 5597},
            {"name": "Error Pattern Memory", "script": "error_pattern_memory.py", "port": 5611},
            {"name": "Context Summarizer", "script": "context_summarizer.py", "port": 5610}
        ],
        "dependencies": ["core_models"]
    },
    "core_processing": {
        "agents": [
            {"name": "Remote Connector", "script": "remote_connector_agent.py", "port": 5557},
            {"name": "Unified Web Agent", "script": "unified_web_agent.py", "port": 8001}
        ],
        "dependencies": ["core_models"]
    },
    "specialized": {
        "agents": [
            {"name": "Self-Healing", "script": "self_healing_agent.py", "port": 5614, "pub_port": 5616}
        ],
        "dependencies": ["core_processing"]
    }
}

class SystemLauncher:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = True
        
        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received, stopping all agents...")
        self.running = False
        self.stop_all_agents()
        sys.exit(0)
    
    def start_agent(self, agent_info: dict) -> bool:
        """Start a single agent"""
        try:
            name = agent_info["name"]
            script = agent_info["script"]
            port = agent_info.get("port")
            pub_port = agent_info.get("pub_port")
            args = agent_info.get("args", "")
            
            # Build command
            cmd = f"python agents/{script}"
            if port:
                cmd += f" --port={port}"
            if pub_port:
                cmd += f" --pub_port={pub_port}"
            if args:
                cmd += f" {args}"
            
            # Start process
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=open(f"logs/{name.lower().replace(' ', '_')}.log", "w"),
                stderr=subprocess.STDOUT
            )
            
            self.processes[name] = process
            logger.info(f"Started {name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {name}: {str(e)}")
            return False
    
    def start_group(self, group_name: str) -> bool:
        """Start all agents in a group"""
        group = AGENT_GROUPS[group_name]
        
        # Check dependencies
        for dep in group["dependencies"]:
            if not self.check_group_running(dep):
                logger.error(f"Cannot start {group_name} - dependency {dep} not running")
                return False
        
        # Start each agent in the group
        success = True
        for agent in group["agents"]:
            if not self.start_agent(agent):
                success = False
                break
            time.sleep(2)  # Wait between agents
        
        return success
    
    def check_group_running(self, group_name: str) -> bool:
        """Check if all agents in a group are running"""
        group = AGENT_GROUPS[group_name]
        return all(agent["name"] in self.processes and 
                  self.processes[agent["name"]].poll() is None 
                  for agent in group["agents"])
    
    def stop_all_agents(self):
        """Stop all running agents"""
        for name, process in self.processes.items():
            if process.poll() is None:
                logger.info(f"Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    def run(self):
        """Main launcher function"""
        logger.info("Starting Voice Assistant System...")
        
        try:
            # Start groups in order
            for group_name in AGENT_GROUPS:
                logger.info(f"Starting {group_name} group...")
                if not self.start_group(group_name):
                    logger.error(f"Failed to start {group_name} group")
                    self.stop_all_agents()
                    return
                time.sleep(5)  # Wait between groups
            
            logger.info("All agents started successfully")
            
            # Monitor processes
            while self.running:
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        logger.error(f"{name} has stopped unexpectedly")
                        self.running = False
                        break
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in launcher: {str(e)}")
        finally:
            self.stop_all_agents()
            logger.info("System shutdown complete")

if __name__ == "__main__":
    launcher = SystemLauncher()
    launcher.run() 