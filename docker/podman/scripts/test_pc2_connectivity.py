#!/usr/bin/env python3
"""
Test script to verify connectivity between MainPC and PC2 containers.
This script tests ZMQ connections to PC2 services from MainPC containers.
"""

import os
import sys
import yaml
import json
import time
import socket
import logging
import argparse
import zmq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pc2_connectivity_test")

def load_network_config():
    """Load the network configuration."""
    config_path = "/app/config/network_config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load network config: {e}")
        return None

def load_pc2_services_config():
    """Load the PC2 services configuration."""
    config_path = "/app/main_pc_code/config/pc2_services.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load PC2 services config: {e}")
        return None

def check_tcp_port(host, port, timeout=2):
    """Check if a TCP port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking TCP port {host}:{port}: {e}")
        return False

def test_zmq_req_rep(host, port, timeout=2):
    """Test a ZMQ REQ-REP connection."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)
    
    try:
        socket.connect(f"tcp://{host}:{port}")
        socket.send_json({"action": "ping"})
        response = socket.recv_json()
        logger.info(f"ZMQ REQ-REP test successful for {host}:{port}: {response}")
        return True
    except Exception as e:
        logger.error(f"ZMQ REQ-REP test failed for {host}:{port}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def test_zmq_pub_sub(host, port, timeout=2):
    """Test a ZMQ PUB-SUB connection."""
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    
    try:
        socket.connect(f"tcp://{host}:{port}")
        # We can only verify that the connection doesn't throw an error
        # since we can't guarantee a message will be published during our test
        logger.info(f"ZMQ PUB-SUB connection successful for {host}:{port}")
        return True
    except Exception as e:
        logger.error(f"ZMQ PUB-SUB connection failed for {host}:{port}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def test_memory_orchestrator_connection(host, port):
    """Test connection to Memory Orchestrator Service."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 seconds
    socket.setsockopt(zmq.SNDTIMEO, 3000)  # 3 seconds
    
    try:
        socket.connect(f"tcp://{host}:{port}")
        request = {
            "action": "status",
            "request_id": "test-" + str(int(time.time()))
        }
        socket.send_json(request)
        response = socket.recv_json()
        
        if response.get("status") == "ok":
            logger.info(f"Memory Orchestrator connection successful: {response}")
            return True
        else:
            logger.error(f"Memory Orchestrator returned error: {response}")
            return False
    except Exception as e:
        logger.error(f"Memory Orchestrator connection failed: {e}")
        return False
    finally:
        socket.close()
        context.term()

def test_unified_memory_reasoning_connection(host, port):
    """Test connection to Unified Memory Reasoning Agent."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 seconds
    socket.setsockopt(zmq.SNDTIMEO, 3000)  # 3 seconds
    
    try:
        socket.connect(f"tcp://{host}:{port}")
        request = {
            "action": "health_check",
            "request_id": "test-" + str(int(time.time()))
        }
        socket.send_json(request)
        response = socket.recv_json()
        
        if response.get("status") == "ok":
            logger.info(f"Unified Memory Reasoning connection successful: {response}")
            return True
        else:
            logger.error(f"Unified Memory Reasoning returned error: {response}")
            return False
    except Exception as e:
        logger.error(f"Unified Memory Reasoning connection failed: {e}")
        return False
    finally:
        socket.close()
        context.term()

def main():
    """Main entry point for the PC2 connectivity test script."""
    parser = argparse.ArgumentParser(description='Test PC2 connectivity')
    parser.add_argument('--pc2-ip', type=str, help='PC2 IP address (overrides config)')
    args = parser.parse_args()
    
    # Load configurations
    network_config = load_network_config()
    pc2_services_config = load_pc2_services_config()
    
    if not network_config or not pc2_services_config:
        logger.error("Failed to load required configurations")
        sys.exit(1)
    
    # Get PC2 IP address
    pc2_ip = args.pc2_ip if args.pc2_ip else network_config.get("pc2", {}).get("ip")
    if not pc2_ip:
        logger.error("PC2 IP address not found in config and not provided as argument")
        sys.exit(1)
    
    logger.info(f"Testing connectivity to PC2 at {pc2_ip}")
    
    # Test connectivity to each PC2 service
    success_count = 0
    total_tests = 0
    
    for service_name, service_config in pc2_services_config.items():
        port = service_config.get("port")
        if not port:
            logger.warning(f"No port defined for service {service_name}, skipping")
            continue
        
        total_tests += 1
        logger.info(f"Testing TCP connectivity to {service_name} at {pc2_ip}:{port}")
        
        if check_tcp_port(pc2_ip, port):
            logger.info(f"TCP port {port} is open for {service_name}")
            
            # Test ZMQ connectivity based on service type
            if service_name == "MemoryOrchestratorService":
                if test_memory_orchestrator_connection(pc2_ip, port):
                    success_count += 1
            elif service_name == "UnifiedMemoryReasoningAgent":
                if test_unified_memory_reasoning_connection(pc2_ip, port):
                    success_count += 1
            else:
                # Default to REQ-REP test
                if test_zmq_req_rep(pc2_ip, port):
                    success_count += 1
        else:
            logger.error(f"TCP port {port} is closed for {service_name}")
    
    # Print summary
    logger.info(f"Connectivity test complete: {success_count}/{total_tests} services are accessible")
    
    if success_count == total_tests:
        logger.info("All PC2 services are accessible!")
        sys.exit(0)
    else:
        logger.error(f"{total_tests - success_count} PC2 services are not accessible")
        sys.exit(1)

if __name__ == "__main__":
    main() 