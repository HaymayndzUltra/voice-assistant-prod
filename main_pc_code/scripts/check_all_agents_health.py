#!/usr/bin/env python3
"""
System-wide Agent Health Check Script

This script communicates with the SystemDigitalTwin agent to get the health status
of all registered agents across both MainPC and PC2. It provides a human-readable report
of the health status of each agent.
"""

import os
import sys
import zmq
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- CONFIGURATION ---
SDT_HOST = "127.0.0.1"  # Local host for MainPC
SDT_PORT = 7120  # Port of the SystemDigitalTwin agent
CONNECTION_TIMEOUT_S = 10  # Timeout for connection
SECURE_ZMQ = os.environ.get("SECURE_ZMQ", "0") == "1"  # Check if secure ZMQ is enabled
# ---------------------

# ANSI color codes for terminal output
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "PURPLE": "\033[95m",
    "CYAN": "\033[96m",
    "BOLD": "\033[1m",
    "END": "\033[0m"
}

def format_status(status: str) -> str:
    """Format agent status with color."""
    if status == "HEALTHY":
        return f"{COLORS['GREEN']}{status}{COLORS['END']}"
    elif status == "UNHEALTHY":
        return f"{COLORS['RED']}{status}{COLORS['END']}"
    elif status == "NO_RESPONSE":
        return f"{COLORS['YELLOW']}{status}{COLORS['END']}"
    return f"{COLORS['YELLOW']}{status}{COLORS['END']}"

def connect_to_sdt() -> Optional[zmq.Socket]:
    """Connect to the SystemDigitalTwin agent."""
    try:
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, CONNECTION_TIMEOUT_S * 1000)
        socket.setsockopt(zmq.SNDTIMEO, CONNECTION_TIMEOUT_S * 1000)
        
        # Configure secure ZMQ if enabled
        if SECURE_ZMQ:
            try:
                from src.network.secure_zmq import configure_secure_client
                socket = configure_secure_client(socket)
                print(f"{COLORS['BLUE']}Using secure ZMQ connection{COLORS['END']}")
            except ImportError:
                print(f"{COLORS['YELLOW']}Warning: Could not import secure ZMQ module, using standard ZMQ{COLORS['END']}")
        
        target_address = f"tcp://{SDT_HOST}:{SDT_PORT}"
        print(f"Connecting to SystemDigitalTwin at {target_address}...")
        socket.connect(target_address)
        return socket
    except Exception as e:
        print(f"{COLORS['RED']}Error connecting to SystemDigitalTwin: {e}{COLORS['END']}")
        return None

def check_system_health() -> bool:
    """
    Connect to the SystemDigitalTwin and request a full system health report.
    
    Returns:
        True if successful, False otherwise
    """
    socket = connect_to_sdt()
    if not socket:
        return False
    
    try:
        print(f"Requesting health status from all agents...")
        socket.send_string("GET_ALL_STATUS")
        
        print(f"Waiting for response (timeout: {CONNECTION_TIMEOUT_S}s)...")
        try:
            response = socket.recv_json()
            print_health_report(response)
            return True
        except zmq.error.Again:
            print(f"{COLORS['RED']}Timeout waiting for response from SystemDigitalTwin{COLORS['END']}")
            return False
        except Exception as e:
            print(f"{COLORS['RED']}Error receiving response: {e}{COLORS['END']}")
            return False
    finally:
        socket.close()
        zmq.Context.instance().term()

def print_health_report(agents: Dict[str, Any]) -> None:
    """Print a formatted health report."""
    print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{'AI SYSTEM HEALTH REPORT':^80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not agents:
        print(f"{COLORS['YELLOW']}No agents registered with SystemDigitalTwin{COLORS['END']}")
        return
    
    # Separate agents by location
    mainpc_agents = {}
    pc2_agents = {}
    unknown_agents = {}
    
    for name, info in agents.items():
        location = info.get("location", "Unknown").upper()
        if location == "MAINPC":
            mainpc_agents[name] = info
        elif location == "PC2":
            pc2_agents[name] = info
        else:
            unknown_agents[name] = info
    
    # Print summary
    total_agents = len(agents)
    total_healthy = sum(1 for info in agents.values() if info.get("status") == "HEALTHY")
    
    print(f"{COLORS['BOLD']}SUMMARY:{COLORS['END']}")
    print(f"  Total Agents: {total_agents}")
    print(f"  Healthy Agents: {total_healthy} ({total_healthy/total_agents*100:.1f}%)")
    print(f"  MainPC Agents: {len(mainpc_agents)}")
    print(f"  PC2 Agents: {len(pc2_agents)}")
    print(f"  Unknown Location: {len(unknown_agents)}\n")
    
    # Print MainPC agents
    if mainpc_agents:
        print(f"{COLORS['BOLD']}MAINPC AGENTS:{COLORS['END']}")
        _print_agent_list(mainpc_agents)
    
    # Print PC2 agents
    if pc2_agents:
        print(f"\n{COLORS['BOLD']}PC2 AGENTS:{COLORS['END']}")
        _print_agent_list(pc2_agents)
    
    # Print unknown location agents
    if unknown_agents:
        print(f"\n{COLORS['BOLD']}UNKNOWN LOCATION AGENTS:{COLORS['END']}")
        _print_agent_list(unknown_agents)
    
    print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")

def _print_agent_list(agents: Dict[str, Any]) -> None:
    """Print a list of agents with their status."""
    for name, info in sorted(agents.items()):
        status = format_status(info.get("status", "UNKNOWN"))
        last_seen = info.get("last_seen", "N/A")
        # Format datetime to be more readable if it's an ISO format
        try:
            if "T" in last_seen and "." in last_seen:
                dt = datetime.fromisoformat(last_seen)
                last_seen = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
        
        print(f"  {COLORS['BOLD']}{name:<30}{COLORS['END']} | Status: {status:<20} | Last Seen: {last_seen}")

def register_example_agents(count: int = 5) -> None:
    """
    Register some example agents for testing.
    
    Args:
        count: Number of example agents to register
    """
    socket = connect_to_sdt()
    if not socket:
        return
    
    try:
        for i in range(1, count+1):
            # Determine location and status for variety
            location = "MainPC" if i % 2 == 0 else "PC2"
            status = "HEALTHY" if i % 3 != 0 else "UNHEALTHY"
            if i % 5 == 0:
                status = "NO_RESPONSE"
            
            agent_name = f"ExampleAgent{i}"
            request = {
                "action": "register_agent",
                "agent_name": agent_name,
                "location": location,
                "status": status
            }
            
            print(f"Registering {agent_name} at {location} with status {status}...")
            socket.send_json(request)
            
            try:
                response = socket.recv_json()
                if response.get("status") == "success":
                    print(f"Successfully registered {agent_name}")
                else:
                    print(f"Error registering {agent_name}: {response.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error receiving response for {agent_name}: {e}")
    finally:
        socket.close()
        zmq.Context.instance().term()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Check the health of all system agents")
    parser.add_argument("--register-examples", action="store_true", 
                      help="Register example agents for testing")
    parser.add_argument("--count", type=int, default=5,
                      help="Number of example agents to register")
    
    args = parser.parse_args()
    
    if args.register_examples:
        register_example_agents(args.count)
    
    success = check_system_health()
    sys.exit(0 if success else 1) 