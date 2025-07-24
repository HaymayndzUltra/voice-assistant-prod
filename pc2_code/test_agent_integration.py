#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test Agent Integration
----------------------
This script tests the integration between all updated components in the voice assistant system:
1. Enhanced Model Router (EMR) - port 7602
2. Model Manager Agent (MMA) - port 5556
3. Remote Connector Agent (RCA) - port 5557
4. Chain of Thought Agent (CoT) - port 5612
5. Contextual Memory Agent - port 5596

It sends test requests and tracks the flow of communication through the system.
"""
import zmq
import json
import time
import logging
import sys
import os
from pathlib import Path
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("TestIntegration")

# EMR discovered port (dynamic port allocation)
EMR_PORT = 7602  # This was auto-selected when we started the EMR

class IntegrationTester:
    def __init__(self):
        # Set up ZMQ context
        self.context = zmq.Context()
        
        # Connect to Enhanced Model Router
        self.emr_socket = self.context.socket(zmq.REQ)
        self.emr_socket.connect(f"tcp://localhost:{EMR_PORT}")
        logger.info(f"Connected to Enhanced Model Router on port {EMR_PORT}")
        
    def test_simple_request(self):
        """Test a simple request to EMR"""
        logger.info("Sending simple request to EMR...")
        
        # Create a test request
        request = {
            "request": "process_task",
            "text": "Explain the benefits of distributed agent architecture",
            "source": "test_integration",
            "request_id": f"test_{time.time()}",
            "type": "general"  # This should trigger task type detection in EMR
        }
        
        # Send request to EMR
        self.emr_socket.send_string(json.dumps(request))
        logger.info("Request sent to EMR, waiting for response...")
        
        # Set timeout
        poller = zmq.Poller()
        poller.register(self.emr_socket, zmq.POLLIN)
        
        if poller.poll(30000):  # 30 second timeout
            # Receive response
            response = self.emr_socket.recv_string()
            response_data = json.loads(response)
            
            logger.info("Received response from EMR")
            logger.info(f"Status: {response_data.get('status')}")
            logger.info(f"Model used: {response_data.get('model_used')}")
            
            # Print truncated response
            response_text = response_data.get('response', '')
            logger.info(f"Response (truncated): {response_text[:100]}...")
            
            return response_data
        else:
            logger.error("Timeout waiting for EMR response")
            return None
    
    def test_complex_code_request(self):
        """Test a complex code request that should trigger Chain of Thought"""
        logger.info("Sending complex code request to EMR...")
        
        # Create a test request
        request = {
            "request": "process_task",
            "text": "Write a Python function that implements a binary search tree with insert, delete, and search operations. Include comprehensive error handling and type annotations.",
            "source": "test_integration",
            "request_id": f"test_code_{time.time()}",
            "type": "code",
            "use_chain_of_thought": True  # Explicitly request Chain of Thought
        }
        
        # Send request to EMR
        self.emr_socket.send_string(json.dumps(request))
        logger.info("Complex code request sent to EMR, waiting for response...")
        
        # Set timeout
        poller = zmq.Poller()
        poller.register(self.emr_socket, zmq.POLLIN)
        
        if poller.poll(60000):  # 60 second timeout for this complex request
            # Receive response
            response = self.emr_socket.recv_string()
            response_data = json.loads(response)
            
            logger.info("Received response for complex code request from EMR")
            logger.info(f"Status: {response_data.get('status')}")
            logger.info(f"Model used: {response_data.get('model_used')}")
            
            # Print truncated response
            response_text = response_data.get('response', '')
            logger.info(f"Response (truncated): {response_text[:100]}...")
            
            return response_data
        else:
            logger.error("Timeout waiting for EMR response to complex code request")
            return None
    
    def cleanup(self):
        """Clean up ZMQ resources"""
        logger.info("Cleaning up resources...")
        self.emr_socket.close()
        self.context.term()
        logger.info("Test complete")

def main():
    tester = IntegrationTester()
    
    try:
        # Test 1: Simple request
        logger.info("===== TEST 1: SIMPLE REQUEST =====")
        simple_result = tester.test_simple_request()
        if simple_result:
            logger.info("Simple request test completed successfully")
        else:
            logger.error("Simple request test failed")
        
        # Wait a bit between tests
        logger.info("Waiting 5 seconds before next test...")
        time.sleep(5)
        
        # Test 2: Complex code request
        logger.info("===== TEST 2: COMPLEX CODE REQUEST WITH CHAIN OF THOUGHT =====")
        complex_result = tester.test_complex_code_request()
        if complex_result:
            logger.info("Complex code request test completed successfully")
        else:
            logger.error("Complex code request test failed")
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()
