#!/usr/bin/env python3
"""
Cross-Machine Registration Test

This script tests the cross-machine registration and communication flow:
1. Verify if SystemDigitalTwin is running on MainPC
2. Check if UnifiedMemoryReasoningAgent is registered with SystemDigitalTwin
3. Discover UnifiedMemoryReasoningAgent via SystemDigitalTwin
4. Send a test message to UnifiedMemoryReasoningAgent and verify the response

Usage:
    python -m main_pc_code.tests.test_cross_machine_registration

Prerequisites:
    - SystemDigitalTwin must be running on MainPC
    - UnifiedMemoryReasoningAgent must be running on PC2
    - PC2 IP must be correctly configured in network_config.yaml
    - ZMQ certificates must be in place for secure communication
"""

import os
import sys
import zmq
import time
import json
import logging
import unittest
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import service discovery client and network utilities
from main_pc_code.utils.service_discovery_client import discover_service
from main_pc_code.utils.network_utils import load_network_config
from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CrossMachineTest')

# Constants
SDT_HOST = "localhost"  # SystemDigitalTwin is local on MainPC
SDT_PORT = 7120
PC2_AGENT_NAME = "UnifiedMemoryReasoningAgent"

class TestCrossMachineFlow(unittest.TestCase):
    """Test cross-machine registration and communication flow."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        logger.info("Setting up cross-machine test environment...")
        
        # Load network configuration to get PC2's IP
        cls.network_config = load_network_config()
        if cls.network_config:
            cls.pc2_ip = cls.network_config.get('pc2_ip')
            if not cls.pc2_ip:
                raise Exception("PC2 IP not found in network_config.yaml. Please configure it.")
            logger.info(f"PC2 IP from configuration: {cls.pc2_ip}")
        else:
            raise Exception("Could not load network_config.yaml.")
            
        # Check if secure ZMQ is enabled
        cls.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        logger.info(f"Secure ZMQ is {'enabled' if cls.secure_zmq else 'disabled'}")
        
        # If secure ZMQ is enabled, initialize the authenticator
        if cls.secure_zmq:
            start_auth()
        
        print("\n--- Cross-Machine Test Environment Setup ---")
        print(f"PC2 IP: {cls.pc2_ip}")
        print("Ensure SystemDigitalTwin is running on MainPC.")
        print(f"Ensure {PC2_AGENT_NAME} is running on PC2.")
        print("-------------------------------------------\n")
        
    def test_01_sdt_health_check(self):
        """Test if SystemDigitalTwin is running and healthy."""
        logger.info("Step 1: Testing if SystemDigitalTwin is running...")
        
        # Create ZMQ context and socket
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds timeout
        
        # Configure socket with CURVE security if enabled
        if self.secure_zmq:
            socket = configure_secure_client(socket)
        
        # Connect to SystemDigitalTwin
        socket.connect(f"tcp://{SDT_HOST}:{SDT_PORT}")
        
        # Send health check request
        logger.info("Sending health check request to SystemDigitalTwin...")
        socket.send_json({"action": "health_check"})
        
        # Wait for response
        try:
            response = socket.recv_json()
            logger.info(f"Received health check response: {response}")
            
            # Assert that the response contains expected fields
            self.assertIsNotNone(response)
            self.assertEqual(response.get('agent'), 'SystemDigitalTwin')
            self.assertEqual(response.get('status'), 'success')
            
            print("SystemDigitalTwin health check: PASSED")
            
        except zmq.error.Again:
            self.fail("SystemDigitalTwin health check timed out. Is the agent running?")
        finally:
            socket.close()
    
    def test_02_discover_pc2_agent(self):
        """Test discovering the PC2 agent via SystemDigitalTwin."""
        logger.info(f"Step 2: Attempting to discover {PC2_AGENT_NAME} via SystemDigitalTwin...")
        
        # Use service discovery client to find PC2 agent
        discovery_response = discover_service(PC2_AGENT_NAME)
        logger.info(f"Discovery response: {discovery_response}")
        
        # Check if the discovery was successful
        self.assertEqual(discovery_response.get("status"), "SUCCESS", 
                         f"Failed to discover {PC2_AGENT_NAME}: {discovery_response.get('message')}")
        
        # Extract and validate agent info
        pc2_agent_info = discovery_response.get("payload")
        self.assertIsNotNone(pc2_agent_info, "Discovery payload is empty.")
        self.assertEqual(pc2_agent_info.get("name"), PC2_AGENT_NAME)
        self.assertEqual(pc2_agent_info.get("location"), "PC2")
        
        # Store agent info for the next test
        self.pc2_agent_info = pc2_agent_info
        
        # Get the agent's address
        agent_address = f"tcp://{pc2_agent_info['ip']}:{pc2_agent_info['port']}"
        print(f"Successfully discovered {PC2_AGENT_NAME} at {agent_address}")
    
    def test_03_communicate_with_pc2_agent(self):
        """Test direct communication with the PC2 agent."""
        logger.info(f"Step 3: Testing direct communication with {PC2_AGENT_NAME}...")
        
        # Ensure we have agent info from the previous test
        if not hasattr(self, 'pc2_agent_info'):
            self.fail("PC2 agent info not available. Discovery test must run first.")
        
        # Extract agent address information
        pc2_agent_ip = self.pc2_agent_info.get('ip')
        pc2_agent_port = self.pc2_agent_info.get('port')
        pc2_agent_address = f"tcp://{pc2_agent_ip}:{pc2_agent_port}"
        logger.info(f"Connecting to {PC2_AGENT_NAME} at {pc2_agent_address}")
        
        # Create ZMQ context and socket
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds timeout
        
        # Configure socket with CURVE security if enabled
        if self.secure_zmq:
            socket = configure_secure_client(socket)
        
        # Connect to PC2 agent
        socket.connect(pc2_agent_address)
        
        # Create test message
        test_message = {
            "command": "TEST_PING",
            "data": "Hello from MainPC Cross-Machine Test!",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"Sending test message: {test_message}")
        
        # Send test message
        try:
            socket.send_json(test_message)
            
            # Wait for response
            response = socket.recv_json()
            logger.info(f"Received response: {response}")
            
            # Validate response
            self.assertIsNotNone(response)
            self.assertEqual(response.get("status"), "SUCCESS")
            self.assertIn("data", response)
            self.assertIn("echo", response.get("data", {}))
            self.assertEqual(response.get("data", {}).get("echo"), test_message.get("data"))
            
            print(f"Communication with {PC2_AGENT_NAME}: PASSED")
            print(f"Response data: {response.get('data')}")
            
        except zmq.error.Again:
            self.fail(f"Communication with {PC2_AGENT_NAME} timed out.")
        finally:
            socket.close()
            context.term()

if __name__ == '__main__':
    # Display test information
    print("\n===================================================")
    print("Cross-Machine Registration and Communication Test")
    print("===================================================")
    print("This test verifies:")
    print("1. SystemDigitalTwin is running on MainPC")
    print("2. UnifiedMemoryReasoningAgent is registered with SystemDigitalTwin")
    print("3. We can discover UnifiedMemoryReasoningAgent via SystemDigitalTwin")
    print("4. We can communicate directly with UnifiedMemoryReasoningAgent")
    print("\nPREREQUISITES:")
    print("- SystemDigitalTwin must be running on MainPC")
    print("- UnifiedMemoryReasoningAgent must be running on PC2")
    print("- network_config.yaml must contain the correct PC2 IP")
    print("- ZMQ certificates must be in place if using secure ZMQ")
    print("===================================================\n")
    
    # Run the tests
    unittest.main() 