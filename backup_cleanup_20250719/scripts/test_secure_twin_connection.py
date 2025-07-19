#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test Script for Secure Communication between SystemDigitalTwin and UnifiedMemoryReasoningAgent

This script runs both components in the same process to test secure ZMQ communication
without network connectivity issues.
"""

import os
import sys
import json
import time
import logging
import threading
import zmq
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the SystemDigitalTwin and UnifiedMemoryReasoningAgent
from main_pc_code.agents.system_digital_twin import SystemDigitalTwin
from pc2_code.agents.UnifiedMemoryReasoningAgent import UnifiedMemoryReasoningAgent
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("TestSecureTwinConnection")

class TestSecureConnection:
    def __init__(self, use_secure_zmq: bool = False):
        """Initialize the test."""
        self.use_secure_zmq = use_secure_zmq
        if self.use_secure_zmq:
            os.environ["SECURE_ZMQ"] = "1"
            logger.info("Secure ZMQ enabled")
        else:
            os.environ["SECURE_ZMQ"] = "0"
            logger.info("Secure ZMQ disabled")
            
        # Override configuration for local testing
        os.environ["MAINPC_IP"] = "localhost"
        os.environ["PC2_IP"] = "localhost"
        os.environ["SYSTEM_DIGITAL_TWIN_PORT"] = "7120"
        os.environ["UNIFIED_MEMORY_REASONING_PORT"] = "7230"
        
        # Threads for running agents
        self.sdt_thread = None
        self.umr_thread = None
        
        # Agent instances
        self.sdt = None
        self.umr = None
        
    def start_system_digital_twin(self):
        """Start the SystemDigitalTwin agent."""
        try:
            logger.info("Starting SystemDigitalTwin agent...")
            self.sdt = SystemDigitalTwin()
            self.sdt.run()
        except Exception as e:
            logger.error(f"Error in SystemDigitalTwin: {e}")
        finally:
            logger.info("SystemDigitalTwin agent stopped")
            
    def start_unified_memory_reasoning_agent(self):
        """Start the UnifiedMemoryReasoningAgent."""
        try:
            logger.info("Starting UnifiedMemoryReasoningAgent...")
            self.umr = UnifiedMemoryReasoningAgent()
            self.umr.start()
        except Exception as e:
            logger.error(f"Error in UnifiedMemoryReasoningAgent: {e}")
        finally:
            logger.info("UnifiedMemoryReasoningAgent stopped")
            
    def start_agents(self):
        """Start both agents in separate threads."""
        # Start SystemDigitalTwin in a separate thread
        self.sdt_thread = threading.Thread(target=self.start_system_digital_twin)
        self.sdt_thread.daemon = True
        self.sdt_thread.start()
        
        # Wait for SystemDigitalTwin to start
        time.sleep(2)
        
        # Start UnifiedMemoryReasoningAgent in a separate thread
        self.umr_thread = threading.Thread(target=self.start_unified_memory_reasoning_agent)
        self.umr_thread.daemon = True
        self.umr_thread.start()
        
        logger.info("Both agents started")
        
    def check_system_health(self):
        """Connect to the SystemDigitalTwin and check health status."""
        # Create a ZMQ socket
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        
        # Configure secure ZMQ if enabled
        if self.use_secure_zmq:
            try:
                from main_pc_code.src.network.secure_zmq import configure_secure_client
                socket = configure_secure_client(socket)
                logger.info("Using secure ZMQ connection for health check")
            except Exception as e:
                logger.error(f"Error configuring secure ZMQ: {e}")
        
        # Connect to SystemDigitalTwin
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:7120")
        
        # Send health check request
        logger.info("Sending health check request...")
        socket.send_string("GET_ALL_STATUS")
        
        # Wait for response
        try:
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            response = socket.recv_json()
            logger.info(f"Received response: {json.dumps(response, indent=2)}")
            
            # Check if UnifiedMemoryReasoningAgent is registered
            if "UnifiedMemoryReasoningAgent" in response:
                logger.info("UnifiedMemoryReasoningAgent successfully registered with SystemDigitalTwin!")
                umr_status = response["UnifiedMemoryReasoningAgent"].get("status", "UNKNOWN")
                logger.info(f"UMR Status: {umr_status}")
            else:
                logger.warning("UnifiedMemoryReasoningAgent not registered with SystemDigitalTwin")
                
            return True
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return False
        finally:
            socket.close()
    
    def run_test(self):
        """Run the test."""
        try:
            # Start the agents
            self.start_agents()
            
            # Wait for agents to initialize
            logger.info("Waiting for agents to initialize...")
            time.sleep(5)
            
            # Check system health
            logger.info("Checking system health...")
            success = self.check_system_health()
            
            if success:
                logger.info("Test completed successfully!")
            else:
                logger.error("Test failed!")
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        except Exception as e:
            logger.error(f"Error in test: {e}")
        finally:
            logger.info("Test complete")
            
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test secure communication between SystemDigitalTwin and UnifiedMemoryReasoningAgent")
    parser.add_argument("--secure", action="store_true", help="Enable secure ZMQ")
    
    args = parser.parse_args()
    
    # Print test information
    print("=" * 80)
    print("TEST SECURE COMMUNICATION: SystemDigitalTwin <-> UnifiedMemoryReasoningAgent")
    print("=" * 80)
    print(f"Secure ZMQ: {'ENABLED' if args.secure else 'DISABLED'}")
    print(f"Certificate Directory: {project_root / 'certificates'}")
    print("=" * 80)
    
    # Create and run the test
    test = TestSecureConnection(use_secure_zmq=args.secure)
    test.run_test() 