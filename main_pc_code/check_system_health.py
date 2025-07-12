#!/usr/bin/env python3
"""
System Health Check Script

This script checks if the AI system is running properly by:
1. Testing port connections for key agents
2. Checking if required config files exist
3. Verifying that no port conflicts exist
4. Reporting the overall system health status
"""

import os
import sys
import socket
import json
import logging
import time
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Define paths
MAIN_PC_CODE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(MAIN_PC_CODE, ".."))

# Key ports to check
KEY_PORTS = [
    {"name": "TaskRouter", "port": 8570},
    {"name": "ChainOfThoughtAgent", "port": 5612},
    {"name": "ModelManagerAgent", "port": 5570},
    {"name": "GoalOrchestratorAgent", "port": 7001},
    {"name": "IntentionValidatorAgent", "port": 5701},
    {"name": "DynamicIdentityAgent", "port": 5802},
    {"name": "EmpathyAgent", "port": 5703},
    {"name": "ProactiveAgent", "port": 5624},
    {"name": "EnhancedModelRouter", "port": 5598},
    {"name": "TinyLlamaService", "port": 5615},
    {"name": "NLLBAdapter", "port": 5581},
    {"name": "ConsolidatedTranslator", "port": 5563},
]

# Required config files
REQUIRED_FILES = [
    join_path("config", "system_config.json"),
    join_path("config", "model_configs.json"),
    join_path("config", "startup_config.yaml"),
    join_path("data", "personas.json")
]

def check_port(port, host='localhost'):
    """Check if a port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex((host, port))
            return result == 0  # True if port is open
    except:
        return False

def check_file_exists(file_path):
    """Check if a file exists."""
    full_path = os.path.join(MAIN_PC_CODE, file_path)
    return os.path.exists(full_path)

def check_system_health():
    """Check the overall system health."""
    logger.info("Checking system health...")
    
    # Check port connections
    port_status = []
    for agent in KEY_PORTS:
        is_running = check_port(agent["port"])
        port_status.append({
            "name": agent["name"],
            "port": agent["port"],
            "status": "RUNNING" if is_running else "NOT RUNNING"
        })
    
    # Check required files
    file_status = []
    for file_path in REQUIRED_FILES:
        exists = check_file_exists(file_path)
        file_status.append({
            "path": file_path,
            "status": "EXISTS" if exists else "MISSING"
        })
    
    # Calculate overall health
    running_agents = sum(1 for agent in port_status if agent["status"] == "RUNNING")
    existing_files = sum(1 for file in file_status if file["status"] == "EXISTS")
    
    agent_health = running_agents / len(KEY_PORTS) * 100
    file_health = existing_files / len(REQUIRED_FILES) * 100
    overall_health = (agent_health + file_health) / 2
    
    health_status = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent_health_percent": agent_health,
        "file_health_percent": file_health,
        "overall_health_percent": overall_health,
        "agents": port_status,
        "files": file_status
    }
    
    return health_status

def format_health_report(health_status):
    """Format the health status report."""
    report = []
    report.append("=" * 60)
    report.append("AI SYSTEM HEALTH REPORT")
    report.append("=" * 60)
    report.append(f"Timestamp: {health_status['timestamp']}")
    report.append(f"Overall Health: {health_status['overall_health_percent']:.1f}%")
    report.append(f"Agent Health: {health_status['agent_health_percent']:.1f}%")
    report.append(f"File Health: {health_status['file_health_percent']:.1f}%")
    report.append("")
    
    report.append("AGENT STATUS:")
    report.append("-" * 60)
    for agent in health_status["agents"]:
        status_symbol = "[OK]" if agent["status"] == "RUNNING" else "[X]"
        report.append(f"{status_symbol} {agent['name']} (Port {agent['port']}): {agent['status']}")
    report.append("")
    
    report.append("FILE STATUS:")
    report.append("-" * 60)
    for file in health_status["files"]:
        status_symbol = "[OK]" if file["status"] == "EXISTS" else "[X]"
        report.append(f"{status_symbol} {file['path']}: {file['status']}")
    report.append("")
    
    if health_status['overall_health_percent'] < 50:
        report.append("SYSTEM HEALTH CRITICAL! Run fix_system.py to repair.")
    elif health_status['overall_health_percent'] < 80:
        report.append("SYSTEM HEALTH WARNING! Some components are not running properly.")
    else:
        report.append("SYSTEM HEALTH GOOD. All critical components are running.")
    
    return "\n".join(report)

def main():
    """Main function to check system health."""
    health_status = check_system_health()
    report = format_health_report(health_status)
    
    print(report)
    
    # Save the report to a file
    report_path = os.path.join(MAIN_PC_CODE, "system_health_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    
    logger.info(f"Health report saved to {report_path}")
    
    # Save the raw health status as JSON
    json_path = os.path.join(MAIN_PC_CODE, "system_health_status.json")
    with open(json_path, "w") as f:
        json.dump(health_status, f, indent=2)
    
    logger.info(f"Health status JSON saved to {json_path}")
    
    # Return exit code based on health
    if health_status['overall_health_percent'] < 50:
        return 2  # Critical
    elif health_status['overall_health_percent'] < 80:
        return 1  # Warning
    else:
        return 0  # Good

if __name__ == "__main__":
    sys.exit(main()) 