#!/usr/bin/env python3

"""
MVS Health Checker
-----------------
Checks the health status of all agents in the Minimal Viable System
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

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Load the minimal system configuration - use local copy
config_path = "minimal_system_config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Combine core agents and dependencies into a single list
all_agents = []
if 'core_agents' in config:
    all_agents.extend(config['core_agents'])
if 'dependencies' in config:
    all_agents.extend(config['dependencies'])

# ZMQ timeout (milliseconds)
TIMEOUT = 2000  # 2 seconds

def check_agent_health(agent):
    """Check the health of a single agent."""
    name = agent.get('name')
    port = agent.get('port')
    health_check_port = agent.get('health_check_port', port + 1)
    
    if not port:
        return {
            'name': name,
            'status': 'UNKNOWN',
            'message': 'No port specified'
        }
    
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, TIMEOUT)
    
    try:
        # Connect to the agent's health check port
        socket.connect(f"tcp://localhost:{health_check_port}")
        
        # Send health check request
        socket.send_json({"action": "health_check"})
        
        # Wait for response
        response = socket.recv_json()
        
        # Check if the response indicates the agent is healthy
        status = response.get('status', 'UNKNOWN').lower()
        if status in ['ok', 'healthy']:
            return {
                'name': name,
                'status': 'HEALTHY',
                'message': response.get('message', 'Agent is healthy'),
                'details': response
            }
        else:
            return {
                'name': name,
                'status': 'UNHEALTHY',
                'message': response.get('message', 'Agent reported unhealthy status'),
                'details': response
            }
    except zmq.error.Again:
        return {
            'name': name,
            'status': 'TIMEOUT',
            'message': f'No response from agent on port {health_check_port}'
        }
    except Exception as e:
        return {
            'name': name,
            'status': 'ERROR',
            'message': f'Error checking agent: {str(e)}'
        }
    finally:
        socket.close()
        context.term()

def print_health_status(results):
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
    for result in sorted(results, key=lambda x: x['name']):
        status = result['status']
        if status == 'HEALTHY':
            color = GREEN
        elif status == 'UNHEALTHY':
            color = RED
        elif status == 'TIMEOUT':
            color = YELLOW
        elif status == 'ERROR':
            color = RED
        else:
            color = YELLOW
        
        print(f"  {result['name']}: {color}{status}{RESET} - {result['message']}")
    
    print("\n")

def main():
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
                print(f"[{RED}!{RESET}] {agent.get('name')} - Error: {e}")
                results.append({
                    'name': agent.get('name'),
                    'status': 'ERROR',
                    'message': f'Exception: {str(e)}'
                })
    
    # Print final report
    print_health_status(results)
    
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