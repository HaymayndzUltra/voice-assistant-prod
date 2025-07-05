#!/usr/bin/env python3

"""
MVS Health Checker
-----------------
Checks the health status of all agents in the Minimal Viable System
Upgraded with intelligent health check logic from mainpc_health_checker_subset.py
"""

import os
import sys
import zmq
import json
import time
import yaml
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, cast

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Valid status strings that indicate a healthy agent
VALID_HEALTHY_STATUSES = ["ok", "healthy", "operational", "success", "running"]

# ZMQ timeout (milliseconds) - increased from 500ms to match successful implementation
TIMEOUT = 10000  # 10 seconds - same as in mainpc_health_checker_subset.py

# Debug mode - print more information
DEBUG = True

def debug_print(message):
    """Print debug messages if DEBUG is True."""
    if DEBUG:
        print(f"{BLUE}[DEBUG]{RESET} {message}")

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
main_pc_code_dir = os.path.abspath(os.path.join(script_dir, ".."))
project_root = os.path.abspath(os.path.join(main_pc_code_dir, ".."))

# Load the master map from startup_config.yaml
def load_master_map():
    """Load the master map from startup_config.yaml"""
    debug_print(f"Loading master map from startup_config.yaml")
    
    # Try to load the startup_config.yaml file
    master_map_path = os.path.join(main_pc_code_dir, "config", "startup_config.yaml")
    if not os.path.exists(master_map_path):
        print(f"{RED}Error: Master map not found at {master_map_path}{RESET}")
        return {}
    
    try:
        with open(master_map_path, 'r') as f:
            master_config = yaml.safe_load(f)
            debug_print(f"Master map loaded from {master_map_path}")
            
            # Create a dictionary mapping agent names to script paths
            agent_path_map = {}
            
            # Process all sections of the config that contain agent definitions
            sections = [
                'core_services', 'main_pc_gpu_services', 'emotion_system', 
                'memory_system', 'learning_knowledge', 'planning_execution',
                'tts_services', 'code_generation', 'audio_processing',
                'language_processing', 'vision'
            ]
            
            for section in sections:
                if section in master_config:
                    for agent in master_config[section]:
                        agent_name = agent.get('name')
                        script_path = agent.get('script_path')
                        if agent_name and script_path:
                            agent_path_map[agent_name] = script_path
            
            debug_print(f"Created agent path map with {len(agent_path_map)} entries")
            return agent_path_map
    except Exception as e:
        print(f"{RED}Error loading master map: {e}{RESET}")
        return {}

# Load the master map
agent_path_map = load_master_map()
debug_print(f"Loaded agent path map with {len(agent_path_map)} entries")

# Load the minimal system configuration
try:
    # Try multiple possible locations for the config file
    possible_paths = [
        os.path.join(script_dir, "minimal_system_config_local.yaml"),  # Local config (preferred)
        os.path.join(script_dir, "minimal_system_config.yaml"),  # Same directory as script
        os.path.join(script_dir, "..", "config", "minimal_system_config.yaml"),  # In config directory
        "minimal_system_config.yaml",  # Current working directory
    ]
    
    config_loaded = False
    for config_path in possible_paths:
        debug_print(f"Trying to load config from {os.path.abspath(config_path)}")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            debug_print(f"Config loaded successfully from {config_path}")
            config_loaded = True
            break
    
    if not config_loaded:
        print(f"{RED}Error: Could not find config file in any of these locations:{RESET}")
        for path in possible_paths:
            print(f"  - {os.path.abspath(path)}")
        sys.exit(1)
        
except Exception as e:
    print(f"{RED}Error loading config:{RESET} {e}")
    sys.exit(1)

# Combine core agents and dependencies into a single list
all_agents = []
if 'core_agents' in config:
    all_agents.extend(config['core_agents'])
    debug_print(f"Added {len(config['core_agents'])} core agents")
if 'dependencies' in config:
    all_agents.extend(config['dependencies'])
    debug_print(f"Added {len(config['dependencies'])} dependency agents")

debug_print(f"Total agents to check: {len(all_agents)}")

# Define custom health check configurations for specific agents
# This is the key improvement from mainpc_health_checker_subset.py
custom_health_checks = {
    "CoordinatorAgent": {
        "health_check_port": 26003,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",  # We'll check against VALID_HEALTHY_STATUSES
        "type": "zmq_req"
    },
    "SystemDigitalTwin": {
        "health_check_port": 7121,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",  # We'll check against VALID_HEALTHY_STATUSES
        "type": "http"  # SystemDigitalTwin uses HTTP health check
    },
    "ChainOfThoughtAgent": {
        "health_check_port": 5613,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",  # We'll check against VALID_HEALTHY_STATUSES
        "type": "zmq_req"
    },
    "ModelManagerAgent": {
        "health_check_port": 5571,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",
        "type": "zmq_req"
    },
    "GoTToTAgent": {
        "health_check_port": 7001,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",
        "type": "zmq_req"
    },
    "SelfTrainingOrchestrator": {
        "health_check_port": 5645,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",
        "type": "zmq_req"
    },
    "EmotionEngine": {
        "health_check_port": 5591,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",
        "type": "zmq_req"
    },
    "AudioCapture": {
        "health_check_port": 6576,  # Correct port from minimal_system_config_local.yaml
        "success_key": "status",
        "type": "zmq_req"
    }
    # Add other custom configurations as needed
}

def get_agent_health_check_config(agent_name: str, agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get custom health check configuration for an agent if it exists."""
    # Start with default config
    config = {
        "type": "zmq_req",
        "success_key": "status",
        "success_value": "ok",  # Default value, but we'll use VALID_HEALTHY_STATUSES for validation
        "health_check_port": agent_data.get("port", 0) + 1
    }
    
    # Override with custom config if available
    if agent_name in custom_health_checks:
        config.update(custom_health_checks[agent_name])
    
    # Use health_check_port from params if available (from minimal_system_config_local.yaml)
    if "params" in agent_data and "health_check_port" in agent_data["params"]:
        config["health_check_port"] = agent_data["params"]["health_check_port"]
        debug_print(f"Using health_check_port from params for {agent_name}: {config['health_check_port']}")
    
    # Special case for SystemDigitalTwin which uses HTTP health check
    if agent_name == "SystemDigitalTwin":
        config.update({
            "type": "http",
            "port": config["health_check_port"],
            "endpoint": "/health",
            "success_key": "status",
        })
        debug_print(f"Using HTTP health check for {agent_name} on port {config['port']}")
    
    return config

def check_agent_health(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Check the health of a single agent."""
    if not isinstance(agent, dict):
        debug_print(f"Invalid agent format: {agent}")
        return {
            'name': 'Unknown',
            'status': 'ERROR',
            'message': f'Invalid agent format: {agent}'
        }
        
    name = agent.get('name', 'Unknown')
    port = agent.get('port')
    
    # Get custom health check configuration
    health_check_config = get_agent_health_check_config(name, agent)
    check_type = health_check_config.get("type", "zmq_req")
    success_key = health_check_config.get("success_key", "status")
    success_value = health_check_config.get("success_value", "ok")
    
    # Use custom health check port if specified, otherwise use port+1
    health_check_port = health_check_config.get("health_check_port", port + 1) if port else None
    
    debug_print(f"Checking {name} on port {health_check_port}, expecting {success_key}={success_value}, type={check_type}")
    
    if not port:
        debug_print(f"No port specified for {name}")
        return {
            'name': name,
            'status': 'UNKNOWN',
            'message': 'No port specified'
        }
    
    # Choose the appropriate health check method
    if check_type == "http":
        return _check_http_health(name, health_check_config)
    else:  # Default to ZMQ
        return _check_zmq_health(name, health_check_config)

def _check_zmq_health(name: str, health_check_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check agent health using ZMQ REQ/REP pattern.
    
    Args:
        name: The name of the agent to check
        health_check_config: Configuration for the health check
        
    Returns:
        Dict: Health check result
    """
    port = health_check_config.get("health_check_port")
    request_data = health_check_config.get("request", {"action": "health_check"})
    success_key = health_check_config.get("success_key", "status")
    success_value = health_check_config.get("success_value", "ok")
    
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
    socket.setsockopt(zmq.RCVTIMEO, TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, TIMEOUT)
    
    try:
        # Connect to the agent's health check port - use 127.0.0.1 instead of localhost
        connect_addr = f"tcp://127.0.0.1:{port}"
        debug_print(f"Connecting to {connect_addr}")
        socket.connect(connect_addr)
        
        # Send health check request
        debug_print(f"Sending health check request to {name}: {request_data}")
        socket.send_json(request_data)
        
        # Wait for response with poller for better timeout handling
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        
        if poller.poll(TIMEOUT):
            try:
                response = socket.recv_json()
                debug_print(f"Received response from {name}: {response}")
                
                # Check if response indicates health using custom success criteria
                is_healthy = False
                
                if isinstance(response, dict) and success_key in response:
                    response_value = response[success_key]
                    
                    # Handle string comparison case with flexible validation
                    if isinstance(response_value, str):
                        # Check if the response value matches any of the valid healthy status strings
                        is_healthy = response_value.lower() in [status.lower() for status in VALID_HEALTHY_STATUSES]
                        debug_print(f"String comparison: '{response_value.lower()}' in {[status.lower() for status in VALID_HEALTHY_STATUSES]} = {is_healthy}")
                    # Direct equality comparison for non-string types
                    else:
                        is_healthy = response_value == success_value
                        debug_print(f"Direct comparison: {response_value} == {success_value} = {is_healthy}")
                
                # Also check for a 'ready' key that might indicate health
                if not is_healthy and isinstance(response, dict) and 'ready' in response:
                    is_healthy = bool(response['ready'])
                    debug_print(f"Ready check: {response.get('ready')} = {is_healthy}")
                
                if is_healthy:
                    return {
                        'name': name,
                        'status': 'HEALTHY',
                        'message': response.get('message', 'Agent is healthy') if isinstance(response, dict) else 'Agent is healthy',
                        'details': response
                    }
                else:
                    return {
                        'name': name,
                        'status': 'UNHEALTHY',
                        'message': response.get('message', f'Agent reported unhealthy status: {response}') if isinstance(response, dict) else f'Invalid response format: {response}',
                        'details': response
                    }
            except Exception as e:
                debug_print(f"Error processing response from {name}: {e}")
                return {
                    'name': name,
                    'status': 'ERROR',
                    'message': f'Error processing response: {str(e)}'
                }
        else:
            debug_print(f"Timeout waiting for {name}")
            return {
                'name': name,
                'status': 'TIMEOUT',
                'message': f'No response from agent on port {port}'
            }
    except Exception as e:
        debug_print(f"Error checking {name}: {e}")
        return {
            'name': name,
            'status': 'ERROR',
            'message': f'Error checking agent: {str(e)}'
        }
    finally:
        socket.close()
        context.term()

def _check_http_health(name: str, health_check_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check agent health using HTTP endpoint.
    
    Args:
        name: The name of the agent to check
        health_check_config: Configuration for the health check
        
    Returns:
        Dict: Health check result
    """
    try:
        # Dynamically import requests to avoid dependency issues
        import requests
        
        port = health_check_config.get("port")
        endpoint = health_check_config.get("endpoint", "/health")
        success_key = health_check_config.get("success_key", "status")
        success_value = health_check_config.get("success_value", "healthy")
        
        # Send HTTP request
        url = f"http://localhost:{port}{endpoint}"
        debug_print(f"Sending HTTP health check to {name}: {url}")
        
        response = requests.get(url, timeout=TIMEOUT/1000)  # Convert ms to seconds
        
        if response.status_code == 200:
            data = response.json()
            debug_print(f"Received HTTP health check response from {name}: {data}")
            
            # Check if response indicates health
            is_healthy = False
            
            if success_key in data:
                response_value = data[success_key]
                
                # Handle string comparison case with flexible validation
                if isinstance(response_value, str):
                    # Check if the response value matches any of the valid healthy status strings
                    is_healthy = response_value.lower() in [status.lower() for status in VALID_HEALTHY_STATUSES]
                    debug_print(f"String comparison: '{response_value.lower()}' in {[status.lower() for status in VALID_HEALTHY_STATUSES]} = {is_healthy}")
                # Direct equality comparison for non-string types
                else:
                    is_healthy = response_value == success_value
                    debug_print(f"Direct comparison: {response_value} == {success_value} = {is_healthy}")
            
            # Also check for a 'ready' key that might indicate health
            if not is_healthy and 'ready' in data:
                is_healthy = bool(data['ready'])
                debug_print(f"Ready check: {data.get('ready')} = {is_healthy}")
            
            if is_healthy:
                return {
                    'name': name,
                    'status': 'HEALTHY',
                    'message': data.get('message', 'Agent is healthy'),
                    'details': data
                }
            else:
                return {
                    'name': name,
                    'status': 'UNHEALTHY',
                    'message': data.get('message', f'Agent reported unhealthy status: {data}'),
                    'details': data
                }
        else:
            return {
                'name': name,
                'status': 'UNREACHABLE',
                'message': f'HTTP health check failed: {response.status_code}'
            }
    except ImportError:
        debug_print(f"Requests library not available, skipping HTTP health check for {name}")
        return {
            'name': name,
            'status': 'ERROR',
            'message': 'Requests library not available for HTTP health check'
        }
    except Exception as e:
        debug_print(f"Error checking HTTP health of {name}: {e}")
        return {
            'name': name,
            'status': 'ERROR',
            'message': f'Error checking HTTP health: {str(e)}'
        }

def print_health_status(results: List[Dict[str, Any]]) -> None:
    """Print health status in a nice format."""
    print(f"\n{BOLD}MVS Health Status Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")
    
    # Count statuses
    healthy = sum(1 for r in results if r['status'] == 'HEALTHY')
    unhealthy = sum(1 for r in results if r['status'] == 'UNHEALTHY')
    timeout = sum(1 for r in results if r['status'] == 'TIMEOUT')
    error = sum(1 for r in results if r['status'] == 'ERROR')
    unknown = sum(1 for r in results if r['status'] == 'UNKNOWN')
    
    # Print summary
    print(f"{BOLD}Summary:{RESET}")
    print(f"  Total Agents: {len(results)}")
    print(f"  {GREEN}Healthy: {healthy}{RESET}")
    print(f"  {RED}Unhealthy: {unhealthy}{RESET}")
    print(f"  {YELLOW}Timeout: {timeout}{RESET}")
    print(f"  {RED}Error: {error}{RESET}")
    print(f"  {YELLOW}Unknown: {unknown}{RESET}\n")
    
    # Print details
    print(f"{BOLD}Agent Details:{RESET}")
    print("-" * 80)
    print(f"{'Agent Name':<30} {'Status':<15} {'Message'}")
    print("-" * 80)
    
    for result in sorted(results, key=lambda x: x['name']):
        status = result['status']
        name = result['name']
        message = result['message']
        
        if status == 'HEALTHY':
            color = GREEN
            status_marker = "✅"
        elif status == 'UNHEALTHY':
            color = RED
            status_marker = "❌"
        elif status == 'TIMEOUT':
            color = YELLOW
            status_marker = "⌛"
        elif status == 'ERROR':
            color = RED
            status_marker = "⚠️"
        else:
            color = YELLOW
            status_marker = "?"
        
        print(f"{name:<30} [{status_marker}] {color}{status:<10}{RESET} {message}")
    
    print("-" * 80)
    print("\n")
    
    # Final verdict
    if healthy == len(results):
        print(f"{GREEN}{BOLD}FINAL VERDICT: SUCCESS - All {len(results)} agents are HEALTHY!{RESET}")
    elif healthy > 0:
        print(f"{YELLOW}{BOLD}FINAL VERDICT: PARTIAL SUCCESS - {healthy}/{len(results)} agents are HEALTHY{RESET}")
    else:
        print(f"{RED}{BOLD}FINAL VERDICT: FAILURE - No agents are HEALTHY{RESET}")
    
    print("\n")

def main() -> int:
    print(f"{BLUE}{BOLD}Checking health of MVS agents...{RESET}")
    
    # Use ThreadPoolExecutor to check agents in parallel
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all health check tasks
        future_to_agent = {executor.submit(check_agent_health, agent): agent for agent in all_agents}
        
        # Collect results as they complete
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            try:
                result = future.result()
                results.append(result)
                
                # Print immediate feedback
                status = result['status']
                name = result['name']
                if status == 'HEALTHY':
                    print(f"[{GREEN}✓{RESET}] {name}")
                elif status == 'UNHEALTHY':
                    print(f"[{RED}✗{RESET}] {name} - {result['message']}")
                elif status == 'TIMEOUT':
                    print(f"[{YELLOW}?{RESET}] {name} - No response")
                elif status == 'ERROR':
                    print(f"[{RED}!{RESET}] {name} - {result['message']}")
                else:
                    print(f"[{YELLOW}?{RESET}] {name} - Unknown status")
            except Exception as e:
                name = agent.get('name', 'Unknown') if isinstance(agent, dict) else 'Unknown'
                print(f"[{RED}!{RESET}] {name} - Error: {e}")
                results.append({
                    'name': name,
                    'status': 'ERROR',
                    'message': f'Exception: {str(e)}'
                })
    
    # Print final report
    print_health_status(results)
    
    # Save results to file
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = os.path.join(script_dir, "logs")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"health_report_{timestamp}.json")
        
        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "summary": {
                    "total": len(results),
                    "healthy": sum(1 for r in results if r['status'] == 'HEALTHY'),
                    "unhealthy": sum(1 for r in results if r['status'] == 'UNHEALTHY'),
                    "timeout": sum(1 for r in results if r['status'] == 'TIMEOUT'),
                    "error": sum(1 for r in results if r['status'] == 'ERROR'),
                    "unknown": sum(1 for r in results if r['status'] == 'UNKNOWN')
                }
            }, f, indent=2)
        print(f"Health report saved to {report_path}")
    except Exception as e:
        print(f"{RED}Error saving health report: {e}{RESET}")
    
    # Return exit code based on health
    healthy_count = sum(1 for r in results if r['status'] == 'HEALTHY')
    if healthy_count == len(all_agents):
        return 0
    elif healthy_count > 0:
        return 1
    else:
        return 2

if __name__ == "__main__":
    sys.exit(main())
