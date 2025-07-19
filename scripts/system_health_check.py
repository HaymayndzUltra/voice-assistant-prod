#!/usr/bin/env python3
"""
System Health Check
-----------------
Comprehensive health check script that uses SystemDigitalTwin
to check the health of all registered agents in the system.
"""

import os
import sys
import zmq
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from common.env_helpers import get_env

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities
try:
    from common_utils.env_loader import get_ip, addr
    from common_utils.zmq_helper import create_socket, safe_socket_send, safe_socket_recv
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SystemHealthCheck")

# Default SystemDigitalTwin port
SDT_PORT = 7120
SDT_HEALTH_PORT = 8100

def get_system_digital_twin_address(host: str = None) -> str:
    """
    Get the address of the SystemDigitalTwin service.
    
    Args:
        host: Optional host override
        
    Returns:
        str: ZMQ address of SystemDigitalTwin
    """
    if USE_COMMON_UTILS:
        try:
            return addr("SystemDigitalTwin", "main_pc")
        except Exception as e:
            logger.warning(f"Failed to get SystemDigitalTwin address from common_utils: {e}")
    
    # Fall back to default
    host = host or os.environ.get("MAIN_PC_IP", get_env("BIND_ADDRESS", "0.0.0.0"))
    return f"tcp://{host}:{SDT_PORT}"

def check_system_digital_twin_health(host: str = None, port: int = SDT_HEALTH_PORT, timeout: int = 5000) -> bool:
    """
    Check if SystemDigitalTwin is healthy.
    
    Args:
        host: Host of SystemDigitalTwin
        port: Health check port of SystemDigitalTwin
        timeout: Timeout in milliseconds
        
    Returns:
        bool: True if health check passed, False otherwise
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    socket.setsockopt(zmq.LINGER, 0)
    
    try:
        # Connect to SystemDigitalTwin health port
        host = host or os.environ.get("MAIN_PC_IP", get_env("BIND_ADDRESS", "0.0.0.0"))
        address = f"tcp://{host}:{port}"
        logger.info(f"Connecting to SystemDigitalTwin health check at {address}")
        socket.connect(address)
        
        # Send health check request
        request = {"action": "health_check"}
        logger.info("Sending health check request to SystemDigitalTwin")
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        logger.info(f"SystemDigitalTwin health status: {response.get('status', 'unknown')}")
        
        # Check response
        if response.get("status") == "success":
            logger.info("SystemDigitalTwin health check passed!")
            return True
        else:
            logger.error(f"SystemDigitalTwin health check failed: {response}")
            return False
            
    except zmq.Again:
        logger.error(f"Timeout waiting for response from SystemDigitalTwin at {host}:{port}")
        return False
    except Exception as e:
        logger.error(f"Error checking SystemDigitalTwin health: {e}")
        return False
    finally:
        socket.close()
        context.term()

def get_registered_agents(host: str = None, port: int = SDT_PORT, timeout: int = 5000) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Get list of registered agents from SystemDigitalTwin.
    
    Args:
        host: Host of SystemDigitalTwin
        port: Port of SystemDigitalTwin
        timeout: Timeout in milliseconds
        
    Returns:
        Tuple[bool, List[Dict[str, Any]]]: (success, list of agents)
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    socket.setsockopt(zmq.LINGER, 0)
    
    try:
        # Connect to SystemDigitalTwin
        address = get_system_digital_twin_address(host)
        logger.info(f"Connecting to SystemDigitalTwin at {address}")
        socket.connect(address)
        
        # Send list agents request
        request = {"action": "list_agents"}
        logger.info("Requesting list of registered agents")
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        
        # Check response
        if response.get("status") == "success":
            agents = response.get("agents", [])
            logger.info(f"Retrieved {len(agents)} registered agents")
            return True, agents
        else:
            logger.error(f"Failed to get registered agents: {response.get('message', 'Unknown error')}")
            return False, []
            
    except zmq.Again:
        logger.error(f"Timeout waiting for response from SystemDigitalTwin")
        return False, []
    except Exception as e:
        logger.error(f"Error getting registered agents: {e}")
        return False, []
    finally:
        socket.close()
        context.term()

def check_agent_health(agent: Dict[str, Any], timeout: int = 5000) -> Dict[str, Any]:
    """
    Check health of a specific agent.
    
    Args:
        agent: Agent information dictionary
        timeout: Timeout in milliseconds
        
    Returns:
        Dict[str, Any]: Health check result
    """
    result = {
        "name": agent.get("name", "Unknown"),
        "location": agent.get("location", "Unknown"),
        "status": "unknown",
        "health_check_supported": False,
        "response": None,
        "error": None
    }
    
    # Check if agent has health check port
    health_port = agent.get("health_check_port")
    if not health_port:
        additional_info = agent.get("additional_info", {})
        if isinstance(additional_info, dict):
            health_port = additional_info.get("health_check_port")
    
    if not health_port:
        result["status"] = "no_health_port"
        result["error"] = "No health check port available"
        return result
        
    # Get agent host
    host = agent.get("ip", get_env("BIND_ADDRESS", "0.0.0.0"))
    if host == "0.0.0.0":
        # Use location to determine host
        location = agent.get("location", "").lower()
        if location == "pc2":
            host = os.environ.get("PC2_IP", get_env("BIND_ADDRESS", "0.0.0.0"))
        else:
            host = os.environ.get("MAIN_PC_IP", get_env("BIND_ADDRESS", "0.0.0.0"))
    
    # Connect to agent health port
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    socket.setsockopt(zmq.LINGER, 0)
    
    try:
        # Connect to agent health port
        address = f"tcp://{host}:{health_port}"
        logger.debug(f"Connecting to {agent.get('name')} health check at {address}")
        socket.connect(address)
        
        # Send health check request
        request = {"action": "health_check"}
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        
        # Update result
        result["health_check_supported"] = True
        result["response"] = response
        
        # Check response
        if response.get("status") in ["success", "ok"]:
            result["status"] = "healthy"
        else:
            result["status"] = "unhealthy"
            result["error"] = response.get("message", "Unknown error")
            
    except zmq.Again:
        result["status"] = "timeout"
        result["error"] = f"Timeout waiting for response from {host}:{health_port}"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    finally:
        socket.close()
        context.term()
        
    return result

def check_all_agents_health(host: str = None, timeout: int = 5000) -> Dict[str, Any]:
    """
    Check health of all registered agents.
    
    Args:
        host: Host of SystemDigitalTwin
        timeout: Timeout in milliseconds
        
    Returns:
        Dict[str, Any]: Health check results
    """
    results = {
        "timestamp": time.time(),
        "system_digital_twin_healthy": False,
        "total_agents": 0,
        "healthy_agents": 0,
        "unhealthy_agents": 0,
        "unreachable_agents": 0,
        "agents": []
    }
    
    # First check if SystemDigitalTwin is healthy
    sdt_healthy = check_system_digital_twin_health(host, SDT_HEALTH_PORT, timeout)
    results["system_digital_twin_healthy"] = sdt_healthy
    
    if not sdt_healthy:
        logger.error("SystemDigitalTwin is not healthy, cannot proceed with agent health checks")
        return results
        
    # Get list of registered agents
    success, agents = get_registered_agents(host, SDT_PORT, timeout)
    if not success:
        logger.error("Failed to get list of registered agents")
        return results
        
    # Update total agents
    results["total_agents"] = len(agents)
    
    # Check health of each agent
    for agent in agents:
        logger.info(f"Checking health of {agent.get('name')} at {agent.get('location')}")
        health_result = check_agent_health(agent, timeout)
        results["agents"].append(health_result)
        
        # Update counters
        if health_result["status"] == "healthy":
            results["healthy_agents"] += 1
        elif health_result["status"] in ["timeout", "error", "no_health_port"]:
            results["unreachable_agents"] += 1
        else:
            results["unhealthy_agents"] += 1
    
    return results

def print_health_check_results(results: Dict[str, Any]) -> None:
    """
    Print health check results in a readable format.
    
    Args:
        results: Health check results
    """
    print("\n" + "=" * 80)
    print(f"SYSTEM HEALTH CHECK RESULTS")
    print("=" * 80)
    
    # Print summary
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['timestamp']))}")
    print(f"SystemDigitalTwin: {'✅ HEALTHY' if results['system_digital_twin_healthy'] else '❌ UNHEALTHY'}")
    print(f"Total Agents: {results['total_agents']}")
    print(f"Healthy Agents: {results['healthy_agents']}")
    print(f"Unhealthy Agents: {results['unhealthy_agents']}")
    print(f"Unreachable Agents: {results['unreachable_agents']}")
    print("-" * 80)
    
    # Print agent results
    print(f"{'AGENT':<30} {'LOCATION':<10} {'STATUS':<15} {'ERROR':<25}")
    print("-" * 80)
    
    for agent in results["agents"]:
        name = agent["name"]
        location = agent["location"]
        status = agent["status"]
        error = agent.get("error", "")
        
        # Format status with emoji
        if status == "healthy":
            status_str = "✅ HEALTHY"
        elif status == "unhealthy":
            status_str = "❌ UNHEALTHY"
        elif status == "timeout":
            status_str = "⏱️ TIMEOUT"
        elif status == "error":
            status_str = "❗ ERROR"
        elif status == "no_health_port":
            status_str = "❓ NO HEALTH PORT"
        else:
            status_str = "❔ UNKNOWN"
            
        print(f"{name:<30} {location:<10} {status_str:<15} {error[:25]}")
    
    print("=" * 80)
    
    # Print overall status
    if results["healthy_agents"] == results["total_agents"]:
        print("✅ ALL AGENTS HEALTHY")
    elif results["healthy_agents"] > 0:
        print(f"⚠️ PARTIAL HEALTH: {results['healthy_agents']}/{results['total_agents']} agents healthy")
    else:
        print("❌ ALL AGENTS UNHEALTHY")
    
    print("=" * 80)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="System Health Check")
    parser.add_argument("--host", help="Host of SystemDigitalTwin")
    parser.add_argument("--timeout", type=int, default=5000, help="Timeout in milliseconds")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--use-env", action="store_true", help="Use environment variables for host")
    args = parser.parse_args()
    
    # Use environment variables if requested
    host = args.host
    if args.use_env:
        host = os.environ.get("MAIN_PC_IP")
        logger.info(f"Using host from environment: {host}")
    
    # Check health of all agents
    results = check_all_agents_health(host, args.timeout)
    
    # Print results
    print_health_check_results(results)
    
    # Save results to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Return exit code based on results
    return 0 if results["healthy_agents"] == results["total_agents"] else 1

if __name__ == "__main__":
    sys.exit(main()) 