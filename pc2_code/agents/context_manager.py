import zmq
from typing import Dict, Any, Optional
import yaml
import json
import logging
import threading
import time
import sys
import os
import numpy as np
from collections import deque
import re
from datetime import datetime
from pc2_code.agents.utils.config_loader import Config


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = Config().get_config()
logger = logging.getLogger(__name__)

class ContextManager(BaseAgent):
    """
    ContextManager:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, min_size=5, max_size=20, initial_size=10):
        super().__init__(name="ContextManager", port=None)

        # Record start time for uptime calculation
        self.start_time = time.time()

        # Initialize agent state
        self.running = True
        self.request_count = 0

        # Set up connection to main PC if needed
        self.main_pc_connections = {}

        logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")
        self.min_size = min_size
        self.max_size = max_size
        self.current_size = initial_size
        self.context_window = deque(maxlen=self.current_size)
        self.importance_scores = {}
        self.importance_threshold = 0.5
        self.speaker_contexts = {}
        self.important_keywords = [
            'remember', "don't forget", 'important', 'critical', 'essential',
            'alalahanin', 'tandaan', 'mahalaga', 'importante', 'kailangan'
        ]
        logger.info(f"[ContextManager] Initialized with size range {min_size}-{max_size}, current: {initial_size}")

    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def add_to_context(self, text, speaker=None, metadata=None):
        if not text:
            return
        timestamp = time.time()
        importance = self._calculate_importance(text)
        context_item = {
            'text': text,
            'timestamp': timestamp,
            'speaker': speaker,
            'importance': importance,
            'metadata': metadata or {}
        }
        self.context_window.append(context_item)
        self.importance_scores[text] = importance
        if speaker:
            if speaker not in self.speaker_contexts:
                self.speaker_contexts[speaker] = deque(maxlen=self.max_size)
            self.speaker_contexts[speaker].append(context_item)
        self._adjust_context_size()
        logger.debug(f"[ContextManager] Added to context: '{text[:30]}...' (Score: {importance:.2f})")

    def get_context(self, speaker=None, max_items=None):
        if speaker and speaker in self.speaker_contexts:
            context = list(self.speaker_contexts[speaker])
        else:
            context = list(self.context_window)
        context.sort(key=lambda x: (x['importance'], x['timestamp']), reverse=True)
        if max_items:
            context = context[:max_items]
        return context

    def get_context_text(self, speaker=None, max_items=None):
        context = self.get_context(speaker, max_items)
        formatted_items = []
        for item in context:
            speaker_prefix = f"[{item['speaker']}]: " if item['speaker'] else ""
            formatted_items.append(f"{speaker_prefix}{item['text']}")
        return "\n".join(formatted_items)

    def clear_context(self, speaker=None):
        if speaker:
            if speaker in self.speaker_contexts:
                self.speaker_contexts[speaker].clear()
                logger.info(f"[ContextManager] Cleared context for speaker: {speaker}")
        else:
            self.context_window.clear()
            self.importance_scores.clear()
            logger.info("[ContextManager] Cleared all context")

    def _calculate_importance(self, text):
        importance = 0.5
        for keyword in self.important_keywords:
            if keyword.lower() in text.lower():
                importance += 0.2
                break
        if '?' in text:
            importance += 0.1
        command_patterns = [
            r'\b(please|paki|pakiusap)\b',
            r'\b(can you|could you|would you)\b',
            r'\b(i want|i need|i would like)\b',
            r'\b(gusto ko|kailangan ko)\b'
        ]
        for pattern in command_patterns:
            if re.search(pattern, text.lower()):
                importance += 0.1
                break
        if len(text.split()) > 15:
            importance += 0.1
        return min(1.0, max(0.0, importance))

    def _adjust_context_size(self):
        avg_importance = np.mean(list(self.importance_scores.values())) if self.importance_scores else 0.5
        if avg_importance > 0.7:
            target_size = min(self.max_size, self.current_size + 2)
        elif avg_importance < 0.3:
            target_size = max(self.min_size, self.current_size - 1)
        else:
            return
        if target_size != self.current_size:
            new_context = deque(self.context_window, maxlen=target_size)
            self.context_window = new_context
            self.current_size = target_size
            logger.info(f"[ContextManager] Adjusted context size to {target_size} (avg importance: {avg_importance:.2f})")

    def prune_context(self):
        if len(self.context_window) < self.current_size:
            return
        items_to_remove = []
        for item in self.context_window:
            if item['importance'] < self.importance_threshold:
                items_to_remove.append(item)
        max_to_remove = max(1, self.current_size // 4)
        for item in items_to_remove[:max_to_remove]:
            self.context_window.remove(item)
            if item['text'] in self.importance_scores:
                del self.importance_scores[item['text']]
        if items_to_remove:
            logger.debug(f"[ContextManager] Pruned {len(items_to_remove[:max_to_remove])} low-importance items")

    def connect_to_main_pc_service(self, service_name: str):
        """
        Connect to a service on the main PC using the network configuration.
        
        Args:
            service_name: Name of the service in the network config ports section
        
        Returns:
            ZMQ socket connected to the service
        """
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}
            
        if service_name not in network_config.get("ports", {}):
            logger.error(f"Service {service_name} not found in network configuration")
            return None
            
        port = network_config.get("ports")[service_name]
        
        # Create a new socket for this connection
        socket = self.context.socket(zmq.REQ)
        
        # Connect to the service
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        
        # Store the connection
        self.main_pc_connections[service_name] = socket
        
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket

class ContextManagerAgent:
    def __init__(self, port=7111, health_port=7112):
        self.port = port
        self.health_port = health_port
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        self._setup_sockets()
        self._start_health_check()
        self.manager = ContextManager()
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        logger.info(f"ContextManagerAgent starting on port {port} (health: {health_port})")

    def _setup_sockets(self):
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"ContextManagerAgent main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {str(e)}")
            raise
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check endpoint on port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check to port {self.health_port}: {str(e)}")
            raise

    def _start_health_check(self):
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if isinstance(request, dict) and request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'ContextManager',
                            'initialization_status': 'complete' if self.initialized else 'in_progress',
                            'port': self.port,
                            'health_port': self.health_port,
                            'timestamp': datetime.now().isoformat()
                        }
                        if self.initialization_error:
                            response['initialization_error'] = str(self.initialization_error)
                    else:
                        response = {
                            'status': 'unknown_action',
                            'message': f"Unknown action: {request.get('action', 'none') if isinstance(request, dict) else 'none'}"
                        }
                    self.health_socket.send_json(response)
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                    time.sleep(1)
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()

    def _initialize_background(self):
        try:
            # Simulate any heavy initialization if needed
            time.sleep(1)
            self.initialized = True
            logger.info("ContextManagerAgent initialization completed")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"ContextManagerAgent initialization failed: {str(e)}")

    def handle_request(self, request: dict) -> dict:
        if not isinstance(request, dict):
            return {'status': 'error', 'message': 'Invalid request format'}
        action = request.get('action')
        if action == 'add_to_context':
            self.manager.add_to_context(
                text=request.get('text'),
                speaker=request.get('speaker'),
                metadata=request.get('metadata')
            )
            return {'status': 'success', 'message': 'Added to context'}
        elif action == 'get_context':
            context = self.manager.get_context(
                speaker=request.get('speaker'),
                max_items=request.get('max_items')
            )
            return {'status': 'success', 'context': context}
        elif action == 'get_context_text':
            text = self.manager.get_context_text(
                speaker=request.get('speaker'),
                max_items=request.get('max_items')
            )
            return {'status': 'success', 'context_text': text}
        elif action == 'clear_context':
            self.manager.clear_context(speaker=request.get('speaker'))
            return {'status': 'success', 'message': 'Context cleared'}
        elif action == 'prune_context':
            self.manager.prune_context()
            return {'status': 'success', 'message': 'Context pruned'}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info("Starting ContextManagerAgent main loop")
        while True:
            try:
                if self.socket.poll(1000) > 0:
                    request = self.socket.recv_json()
                    if isinstance(request, dict):
                        response = self.handle_request(request)
                    else:
                        response = {'status': 'error', 'message': 'Invalid request format'}
                    self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)

    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to ContextManager

        base_status.update({

            'service': 'ContextManager',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()

    def shutdown(self):
        self.socket.close()
        self.health_socket.close()
        self.context.term()
        logger.info("ContextManagerAgent shutdown complete")







if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = ContextManager()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = join_path("config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config() if 'load_network_config' in globals() else {}

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16") if isinstance(network_config, dict) else "192.168.100.16"
PC2_IP = network_config.get("pc2_ip", "192.168.100.17") if isinstance(network_config, dict) else "192.168.100.17"
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0") if isinstance(network_config, dict) else "0.0.0.0"
