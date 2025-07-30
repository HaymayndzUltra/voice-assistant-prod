#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
End-to-End Test for Voice Command Flow

This script simulates a basic voice command input on MainPC and verifies the successful
flow of data through the entire processing chain: 
AudioCapture → StreamingSpeechRecognition → TaskRouter → Responder → TTS
"""

import os
import sys
import zmq
import json
import time
import logging
import threading
import argparse
import unittest
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add project root to path to ensure imports work correctly
current_path = Path(__file__).resolve().parent
project_root = current_path.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import service discovery client for agent discovery
from main_pc_code.utils.service_discovery_client import discover_service, get_service_address
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'logs', str(PathManager.get_logs_dir() / "voice_command_flow_test.log")))
    ]
)
logger = logging.getLogger("VoiceCommandFlowTest")

# Default timeouts
DISCOVERY_TIMEOUT = 5000  # 5 seconds for service discovery
REQUEST_TIMEOUT = 10000   # 10 seconds for requests
FLOW_TIMEOUT = 30000      # 30 seconds for the entire flow

# Default ports (from port_registry.csv, will be overridden by service discovery)
SPEECH_RECOGNITION_PORT = 6580  # StreamingSpeechRecognition PUB port
TASK_ROUTER_PORT = 8570         # TaskRouter REP port
TTS_PORT = 5562                # TTS agent REP port

class TestVoiceCommandFlow(unittest.TestCase):
    """
    End-to-End test for the voice command flow through the agent network.
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Perform one-time setup before all tests.
        This setup discovers all the required agents.
        """
        logger.info("Setting up voice command flow test...")
        cls.context = zmq.Context.instance()
        
        # Discover agent addresses using service discovery if available
        cls.agent_addresses = cls._discover_agents()
        
        # Report discovered agents
        for agent, info in cls.agent_addresses.items():
            if info:
                logger.info(f"Discovered {agent} at {info.get('address', 'unknown address')}")
            else:
                logger.warning(f"Could not discover {agent}")
    
    @classmethod
    def _discover_agents(cls) -> Dict[str, Dict[str, Any]]:
        """
        Discover all required agents using service discovery.
        
        Returns:
            Dictionary of agent names to their discovery information
        """
        agents = {
            "StreamingSpeechRecognition": None,
            "TaskRouter": None,
            "Responder": None,
            "TTSConnector": None,
            "SystemDigitalTwin": None
        }
        
        try:
            # Try service discovery
            for agent_name in agents.keys():
                response = discover_service(agent_name)
                if response.get("status") == "SUCCESS" and "payload" in response:
                    service_info = response["payload"]
                    address = f"tcp://{service_info.get('ip', 'localhost')}:{service_info.get('port', '0')}"
                    agents[agent_name] = {
                        "info": service_info,
                        "address": address
                    }
                    logger.info(f"Successfully discovered {agent_name} at {address}")
                else:
                    logger.warning(f"Could not discover {agent_name} via service discovery")
        except Exception as e:
            logger.error(f"Service discovery error: {e}")
        
        # For any agents not discovered, fall back to default ports
        if not agents["StreamingSpeechRecognition"]:
            agents["StreamingSpeechRecognition"] = {
                "address": f"tcp://localhost:{SPEECH_RECOGNITION_PORT}",
                "info": {"port": SPEECH_RECOGNITION_PORT}
            }
            logger.warning(f"Using default address for StreamingSpeechRecognition: {agents['StreamingSpeechRecognition']['address']}")
            
        if not agents["TaskRouter"]:
            agents["TaskRouter"] = {
                "address": f"tcp://localhost:{TASK_ROUTER_PORT}",
                "info": {"port": TASK_ROUTER_PORT}
            }
            logger.warning(f"Using default address for TaskRouter: {agents['TaskRouter']['address']}")
            
        if not agents["TTSConnector"]:
            agents["TTSConnector"] = {
                "address": f"tcp://localhost:{TTS_PORT}",
                "info": {"port": TTS_PORT}
            }
            logger.warning(f"Using default address for TTS: {agents['TTSConnector']['address']}")
            
        return agents
    
    def setUp(self):
        """
        Set up test resources before each test.
        """
        # Create sockets to send and receive messages in the flow
        
        # Socket to send simulated speech recognition output
        self.speech_pub_socket = self.context.socket(zmq.PUB)
        self.speech_pub_socket.bind(ff"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:6599")  # Test-specific port for publishing
        logger.info(f"Bound speech simulation socket to tcp://127.0.0.1:6599")
        
        # Socket to request task routing
        self.task_router_socket = self.context.socket(zmq.REQ)
        self.task_router_socket.setsockopt(zmq.RCVTIMEO, REQUEST_TIMEOUT)
        self.task_router_socket.setsockopt(zmq.SNDTIMEO, REQUEST_TIMEOUT)
        task_router_address = self.agent_addresses.get("TaskRouter", {}).get("address", f"tcp://localhost:{TASK_ROUTER_PORT}")
        self.task_router_socket.connect(task_router_address)
        logger.info(f"Connected to TaskRouter at {task_router_address}")
        
        # Socket to subscribe to TTS output
        self.tts_sub_socket = self.context.socket(zmq.SUB)
        tts_address = self.agent_addresses.get("TTSConnector", {}).get("address", f"tcp://localhost:{TTS_PORT}")
        self.tts_sub_socket.connect(tts_address)
        self.tts_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"Subscribed to TTS at {tts_address}")
        
        # Store received response
        self.final_response = None
        self.response_received = threading.Event()
    
    def tearDown(self):
        """
        Clean up resources after each test.
        """
        if hasattr(self, 'speech_pub_socket'):
            self.speech_pub_socket.close()
        
        if hasattr(self, 'task_router_socket'):
            self.task_router_socket.close()
        
        if hasattr(self, 'tts_sub_socket'):
            self.tts_sub_socket.close()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up class-level resources.
        """
        # Clean up ZMQ context
        if hasattr(cls, 'context'):
            cls.context.term()

    def _listen_for_tts_output(self, timeout=FLOW_TIMEOUT):
        """
        Background thread to listen for TTS output.
        
        Args:
            timeout: Timeout in milliseconds
        """
        logger.info(f"Starting TTS output listener with {timeout}ms timeout")
        poller = zmq.Poller()
        poller.register(self.tts_sub_socket, zmq.POLLIN)
        
        start_time = time.time()
        timeout_sec = timeout / 1000
        
        while time.time() - start_time < timeout_sec:
            try:
                events = dict(poller.poll(timeout=1000))  # 1 second poll intervals
                
                if self.tts_sub_socket in events:
                    # Receive message from TTS output
                    message = self.tts_sub_socket.recv_string()
                    logger.info(f"Received TTS output: {message[:100]}...")
                    
                    # Store the response
                    self.final_response = message
                    self.response_received.set()
                    return
            except KeyboardInterrupt:
                logger.warning("TTS listener interrupted")
                return
            except Exception as e:
                logger.error(f"Error in TTS listener: {e}")
        
        logger.warning(f"TTS listener timed out after {timeout}ms")
                
    def test_basic_voice_command_flow(self):
        """
        Test a basic voice command through the full agent flow.
        """
        test_command = "What is the weather like today?"
        expected_keywords = ["weather", "today"]
        
        # Start background listener for TTS output
        tts_listener = threading.Thread(target=self._listen_for_tts_output)
        tts_listener.daemon = True
        tts_listener.start()
        
        # Give the listener a moment to initialize
        time.sleep(0.5)
        
        logger.info(f"\n--- Testing Voice Command Flow: '{test_command}' ---")
        start_time = time.time()
        
        # Step 1: Send simulated speech recognition output
        transcript = {
            "text": test_command.strip(),
            "confidence": 0.95,
            "language": "en",
            "language_confidence": 0.99,
            "timestamp": time.time()
        }
        
        try:
            # The StreamingSpeechRecognition agent publishes transcriptions with a prefix
            self.speech_pub_socket.send_string(f"TRANSCRIPTION: {json.dumps(transcript)}")
            logger.info(f"Sent simulated speech recognition output: {transcript}")
        except Exception as e:
            logger.error(f"Error sending speech recognition output: {e}")
            self.fail(f"Failed to send speech recognition output: {e}")
        
        # Step 2: Wait for the TTS response
        logger.info("Waiting for TTS response...")
        self.response_received.wait(timeout=FLOW_TIMEOUT/1000)
        
        # Calculate latency
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Verify the response
        self.assertIsNotNone(self.final_response, "Did not receive a TTS response")
        
        # Check expected keywords if we have a response
        if self.final_response:
            logger.info(f"Received response: {self.final_response[:100]}...")
            response_text = self.final_response.lower()
            
            for keyword in expected_keywords:
                self.assertIn(keyword.lower(), response_text, f"Expected keyword '{keyword}' not found in response")
        
        logger.info(f"Total flow latency: {latency_ms:.2f} ms")
        logger.info(f"Voice command flow test {'PASSED' if self.final_response else 'FAILED'}")

    def test_direct_task_routing(self):
        """
        Test direct interaction with the task router.
        This provides a more isolated test of the task routing component.
        """
        test_command = "What's the weather forecast?"
        
        try:
            # Create request for task router
            request = {
                "task_type": "weather_query",
                "content": test_command,
                "language": "en",
                "priority": "normal"
            }
            
            start_time = time.time()
            self.task_router_socket.send_json(request)
            logger.info(f"Sent request to TaskRouter: {request}")
            
            # Wait for response
            response = self.task_router_socket.recv_json()
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Received TaskRouter response: {response}")
            logger.info(f"TaskRouter latency: {latency_ms:.2f} ms")
            
            # Basic validation
            self.assertIsNotNone(response, "TaskRouter returned no response")
            self.assertIn("status", response, "TaskRouter response missing 'status' field")
            
        except zmq.error.Again:
            logger.error("TaskRouter request timed out")
            self.fail("TaskRouter request timed out")
        except Exception as e:
            logger.error(f"Error in TaskRouter test: {e}")
            self.fail(f"TaskRouter test failed: {e}")

def main():
    """
    Main function for command-line execution.
    """
    parser = argparse.ArgumentParser(description='End-to-End Voice Command Flow Test')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == '__main__':
    main() 