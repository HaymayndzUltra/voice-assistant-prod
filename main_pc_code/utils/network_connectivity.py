#!/usr/bin/env python3
"""
Network Connectivity Utilities

This module provides functions to test connectivity between MainPC and PC2,
and verify that all required ports are accessible.
"""

import socket
import logging
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Add project root to Python path
project_root = Path(os.path.abspath(__file__)).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main_pc_code.utils.network_utils import load_network_config, get_mainpc_address, get_pc2_address

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a port is open on a remote host.
    
    Args:
        host: The hostname or IP address to check
        port: The port number to check
        timeout: Timeout in seconds
        
    Returns:
        bool: True if the port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port {port} on {host}: {e}")
        return False

def ping_host(host: str, count: int = 3) -> Tuple[bool, Optional[float]]:
    """
    Ping a host to check if it's reachable.
    
    Args:
        host: The hostname or IP address to ping
        count: Number of ping packets to send
        
    Returns:
        Tuple[bool, Optional[float]]: (Success, Average RTT in ms)
    """
    try:
        # Use the appropriate ping command for the platform
        if os.name == 'nt':  # Windows
            cmd = ['ping', '-n', str(count), host]
        else:  # Unix/Linux/Mac
            cmd = ['ping', '-c', str(count), host]
            
        # Run the ping command and capture output
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = proc.communicate()
        
        if proc.returncode == 0:
            # Try to extract average RTT
            if os.name == 'nt':  # Windows
                for line in stdout.splitlines():
                    if 'Average' in line:
                        parts = line.split('=')
                        if len(parts) >= 2:
                            return True, float(parts[1].strip().split('ms')[0])
            else:  # Unix/Linux/Mac
                for line in stdout.splitlines():
                    if 'avg' in line:
                        parts = line.split('=')
                        if len(parts) >= 2:
                            avg_part = parts[1].split('/')[1]
                            return True, float(avg_part)
            
            # If RTT extraction failed, just return success
            return True, None
        else:
            return False, None
            
    except Exception as e:
        logger.error(f"Error pinging host {host}: {e}")
        return False, None

def check_connectivity(verbose: bool = True) -> Dict[str, Any]:
    """
    Check connectivity between MainPC and PC2.
    
    Args:
        verbose: Whether to print connectivity information
        
    Returns:
        Dict with connectivity status information
    """
    results = {
        "mainpc": {"reachable": False, "rtt_ms": None, "open_ports": {}},
        "pc2": {"reachable": False, "rtt_ms": None, "open_ports": {}},
    }
    
    # Load network configuration
    config = load_network_config()
    if not config:
        logger.error("Failed to load network configuration")
        return results
    
    # Get IP addresses from config
    mainpc_ip = config.get('main_pc_ip', '')
    pc2_ip = config.get('pc2_ip', '')
    
    if not mainpc_ip or not pc2_ip:
        logger.error("Missing IP addresses in network configuration")
        return results
        
    # Check basic connectivity with ping
    if verbose:
        print(f"Checking connectivity to MainPC ({mainpc_ip})...")
    mainpc_reachable, mainpc_rtt = ping_host(mainpc_ip)
    results["mainpc"]["reachable"] = mainpc_reachable
    results["mainpc"]["rtt_ms"] = mainpc_rtt
    
    if verbose:
        print(f"Checking connectivity to PC2 ({pc2_ip})...")
    pc2_reachable, pc2_rtt = ping_host(pc2_ip)
    results["pc2"]["reachable"] = pc2_reachable
    results["pc2"]["rtt_ms"] = pc2_rtt
    
    # Check important ports
    key_services = {
        "mainpc": {
            "system_digital_twin": config.get("ports", {}).get("system_digital_twin", 7120),
            "health_check": config.get("ports", {}).get("health_check", 8100)
        },
        "pc2": {
            "unified_memory_reasoning": config.get("ports", {}).get("unified_memory_reasoning", 7230)
        }
    }
    
    if verbose and mainpc_reachable:
        print(f"Checking key service ports on MainPC...")
    
    for service, port in key_services["mainpc"].items():
        port_open = check_port_open(mainpc_ip, port)
        results["mainpc"]["open_ports"][service] = port_open
        if verbose and mainpc_reachable:
            status = "OPEN" if port_open else "CLOSED"
            print(f"  - Port {port} ({service}): {status}")
    
    if verbose and pc2_reachable:
        print(f"Checking key service ports on PC2...")
    
    for service, port in key_services["pc2"].items():
        port_open = check_port_open(pc2_ip, port)
        results["pc2"]["open_ports"][service] = port_open
        if verbose and pc2_reachable:
            status = "OPEN" if port_open else "CLOSED"
            print(f"  - Port {port} ({service}): {status}")
            
    # Print summary
    if verbose:
        print("\nConnectivity Summary:")
        print(f"MainPC ({mainpc_ip}): {'✓ REACHABLE' if mainpc_reachable else '✗ UNREACHABLE'}")
        if mainpc_rtt:
            print(f"  - Average RTT: {mainpc_rtt:.2f} ms")
        print(f"PC2 ({pc2_ip}): {'✓ REACHABLE' if pc2_reachable else '✗ UNREACHABLE'}")
        if pc2_rtt:
            print(f"  - Average RTT: {pc2_rtt:.2f} ms")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Check network connectivity between MainPC and PC2")
    parser.add_argument("-q", "--quiet", action="store_true", help="Disable verbose output")
    parser.add_argument("-t", "--test", action="store_true", help="Run quick test of direct connections")
    
    args = parser.parse_args()
    
    if args.test:
        # Test getting addresses
        print(f"MainPC SDT address: {get_mainpc_address()}")
        print(f"PC2 UMR address: {get_pc2_address()}")
        sys.exit(0)
        
    # Check connectivity
    results = check_connectivity(verbose=not args.quiet)
    
    # Exit with appropriate status code for scripting
    if results["mainpc"]["reachable"] and results["pc2"]["reachable"]:
        sys.exit(0)
    else:
        sys.exit(1) 