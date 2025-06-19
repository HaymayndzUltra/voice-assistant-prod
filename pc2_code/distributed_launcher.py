"""
Distributed Agent Launcher
Handles launching agents across multiple machines and setting up auto-start on boot.
"""

import os
import sys
import json
import socket
import argparse
import subprocess
import platform
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("distributed_launcher.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DistributedLauncher")

# Check if running in a virtual environment
def is_venv_active():
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def load_config():
    """Load the distributed configuration"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "distributed_config.json")
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Failed to get local IP: {e}")
        return None

def identify_current_machine(config):
    """Identify which machine in the config this is based on IP"""
    local_ip = get_local_ip()
    if not local_ip:
        logger.error("Could not determine local IP address")
        return None
    
    for machine_id, machine_info in config["machines"].items():
        if machine_info["ip"] == local_ip:
            logger.info(f"Identified current machine as: {machine_id} ({machine_info['description']})")
            return machine_id
    
    logger.warning(f"Current machine IP ({local_ip}) not found in config. Using hostname to match.")
    hostname = socket.gethostname()
    
    # Try to match by hostname if IP not found
    for machine_id, machine_info in config["machines"].items():
        if machine_id.lower() in hostname.lower():
            logger.info(f"Matched machine by hostname: {machine_id}")
            return machine_id
    
    logger.error("Could not identify current machine in configuration")
    return None

def setup_autostart(machine_id, config):
    """Set up auto-start on boot for this machine"""
    system = platform.system()
    
    if system == "Windows":
        setup_windows_autostart(machine_id, config)
    elif system == "Linux":
        setup_linux_autostart(machine_id, config)
    else:
        logger.error(f"Unsupported operating system: {system}")

def setup_windows_autostart(machine_id, config):
    """Set up auto-start on Windows using Task Scheduler"""
    try:
        # Create a .bat file for startup
        startup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"start_{machine_id}_agents.bat")
        venv_activate = config["machines"][machine_id]["venv_path"]
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        with open(startup_script, 'w') as f:
            f.write(f"@echo off\n")
            f.write(f"cd /d {project_dir}\n")
            f.write(f"call {venv_activate}\n")
            f.write(f"python distributed_launcher.py --machine {machine_id} --launch\n")
            f.write(f"exit\n")
        
        # Create a scheduled task
        task_name = f"VoiceAssistant_{machine_id}"
        task_cmd = f'schtasks /create /tn "{task_name}" /tr "{startup_script}" /sc onlogon /ru "%USERNAME%" /rl highest /f'
        
        result = subprocess.run(task_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Successfully created startup task: {task_name}")
        else:
            logger.error(f"Failed to create startup task: {result.stderr}")
            logger.info("You may need to run this script as administrator")
            
        # Create a shortcut in the Startup folder as a backup method
        startup_folder = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        shortcut_path = os.path.join(startup_folder, f"VoiceAssistant_{machine_id}.bat")
        
        try:
            with open(shortcut_path, 'w') as f:
                f.write(f"@echo off\n")
                f.write(f"start \"\" \"{startup_script}\"\n")
            logger.info(f"Created startup shortcut at: {shortcut_path}")
        except Exception as e:
            logger.error(f"Failed to create startup shortcut: {e}")
            
    except Exception as e:
        logger.error(f"Error setting up Windows autostart: {e}")

def setup_linux_autostart(machine_id, config):
    """Set up auto-start on Linux using systemd"""
    try:
        # Create a systemd service file
        service_name = f"voice-assistant-{machine_id}.service"
        service_path = os.path.join(os.path.expanduser("~"), ".config", "systemd", "user", service_name)
        
        venv_activate = config["machines"][machine_id]["venv_path"]
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        os.makedirs(os.path.dirname(service_path), exist_ok=True)
        
        with open(service_path, 'w') as f:
            f.write("[Unit]\n")
            f.write(f"Description=Voice Assistant {machine_id} Agents\n")
            f.write("After=network.target\n\n")
            
            f.write("[Service]\n")
            f.write(f"WorkingDirectory={project_dir}\n")
            f.write(f"ExecStart=/bin/bash -c 'source {venv_activate} && python distributed_launcher.py --machine {machine_id} --launch'\n")
            f.write("Restart=always\n")
            f.write("RestartSec=10\n\n")
            
            f.write("[Install]\n")
            f.write("WantedBy=default.target\n")
        
        # Enable and start the service
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", service_name], check=True)
        logger.info(f"Created and enabled systemd service: {service_name}")
        
    except Exception as e:
        logger.error(f"Error setting up Linux autostart: {e}")

def launch_agents(machine_id, config):
    """Launch all agents for this machine"""
    if not is_venv_active():
        logger.warning("Virtual environment is not activated. It's recommended to run in a virtual environment.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            logger.info("Exiting. Please activate your virtual environment and try again.")
            sys.exit(1)
    
    machine_config = config["machines"].get(machine_id)
    if not machine_config:
        logger.error(f"Machine {machine_id} not found in configuration")
        return
    
    agents_to_launch = machine_config.get("agents", [])
    logger.info(f"Launching {len(agents_to_launch)} agents for {machine_id}")
    
    processes = []
    
    try:
        # Start the discovery service first if enabled
        if config.get("discovery_service", {}).get("enabled", False):
            discovery_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents", "discovery_service.py")
            if os.path.exists(discovery_script):
                logger.info("Starting discovery service...")
                discovery_proc = subprocess.Popen(
                    [sys.executable, discovery_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                )
                processes.append(("discovery_service", discovery_proc))
        
        # Start each agent
        for agent_name in agents_to_launch:
            agent_path = None
            
            # Handle special case for dashboard
            if agent_name == "dashboard":
                agent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "dashboard.py")
            else:
                agent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents", f"{agent_name}.py")
            
            if not os.path.exists(agent_path):
                logger.warning(f"Agent file not found: {agent_path}")
                continue
                
            logger.info(f"Starting {agent_name}...")
            proc = subprocess.Popen(
                [sys.executable, agent_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
            )
            processes.append((agent_name, proc))
            
            # Small delay between starting agents to avoid race conditions
            import time
            time.sleep(1)
        
        logger.info(f"All {len(agents_to_launch)} agents started successfully!")
        
        # Keep the launcher running and monitor the processes
        while True:
            time.sleep(1)
            # Check if any process has exited unexpectedly
            for name, proc in processes:
                if proc.poll() is not None:
                    logger.error(f"{name} exited with code {proc.returncode}. Restarting...")
                    # Restart the process
                    if name == "discovery_service":
                        new_proc = subprocess.Popen(
                            [sys.executable, discovery_script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=1,
                            universal_newlines=True,
                        )
                    else:
                        agent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                               "dashboard" if name == "dashboard" else "agents", 
                                               f"{name}.py")
                        new_proc = subprocess.Popen(
                            [sys.executable, agent_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=1,
                            universal_newlines=True,
                        )
                    # Replace the process in the list
                    idx = next((i for i, (n, _) in enumerate(processes) if n == name), None)
                    if idx is not None:
                        processes[idx] = (name, new_proc)
                    
    except KeyboardInterrupt:
        logger.info("\nShutting down all agents...")
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        # Wait for all to exit
        for name, proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        logger.info("All agents stopped.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for name, proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        logger.info("All agents stopped due to error.")

def main():
    parser = argparse.ArgumentParser(description="Distributed Agent Launcher")
    parser.add_argument("--machine", help="Machine ID to use from config")
    parser.add_argument("--setup", action="store_true", help="Set up auto-start on boot")
    parser.add_argument("--launch", action="store_true", help="Launch agents for this machine")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)
    
    # Identify current machine if not specified
    machine_id = args.machine
    if not machine_id:
        machine_id = identify_current_machine(config)
        if not machine_id:
            logger.error("Could not identify current machine. Please specify with --machine")
            sys.exit(1)
    
    # Setup auto-start if requested
    if args.setup:
        setup_autostart(machine_id, config)
    
    # Launch agents if requested
    if args.launch:
        launch_agents(machine_id, config)
    
    # If no action specified, show help
    if not (args.setup or args.launch):
        parser.print_help()

if __name__ == "__main__":
    main()
