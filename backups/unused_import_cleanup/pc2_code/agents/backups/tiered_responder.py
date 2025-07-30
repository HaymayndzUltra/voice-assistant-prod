import zmq
import json
from typing import Dict, Any, Callable, List
import logging
from datetime import datetime
import asyncio
import time
import threading
import psutil
import torch
from collections import deque
import os
import sys
from pathlib import Path

# Constants
ZMQ_PULL_PORT = 7110
ZMQ_PUSH_PORT = 7111
ZMQ_HEALTH_PORT = 7112
MAX_QUEUE_SIZE = 1000
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_RESPONSE_TIME = {
    'instant': 0.1,  # 100ms
    'fast': 1.0,     # 1 second
    'deep': 5.0      # 5 seconds
}

# Setup logging directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class ResourceManager(BaseAgent):

    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port: int = None):

        super().__init__(name="ResourceManager", port=port)

        self.start_time = time.time()

    def __init__(self):
        self.cpu_threshold = 80  # percentage
        self.memory_threshold = 80  # percentage
        self.gpu_threshold = 80  # percentage if available
        self.last_check = time.time()
        self.stats_history = deque(maxlen=100)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        stats = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'timestamp': time.time()
        }
        
        # Add GPU stats if available
        if torch.cuda.is_available():
            try:
                max_memory = torch.cuda.max_memory_allocated()
                if max_memory > 0:
                    stats['gpu_memory_percent'] = torch.cuda.memory_allocated() / max_memory * 100
                else:
                    stats['gpu_memory_percent'] = 0.0
            except Exception:
                stats['gpu_memory_percent'] = 0.0
            
        self.stats_history.append(stats)
        return stats
        
    def check_resources(self) -> bool:
        """Check if resources are available for processing"""
        stats = self.get_stats()
        
        if stats['cpu_percent'] > self.cpu_threshold:
            return False
            
        if stats['memory_percent'] > self.memory_threshold:
            return False
            
        if 'gpu_memory_percent' in stats and stats['gpu_memory_percent'] > self.gpu_threshold:
            return False
            
        return True
        
    def get_average_stats(self) -> Dict[str, float]:
        """Get average resource usage over time"""
        if not self.stats_history:
            return {}
            
        avg_stats = {
            'cpu_percent': sum(s['cpu_percent'] for s in self.stats_history) / len(self.stats_history),
            'memory_percent': sum(s['memory_percent'] for s in self.stats_history) / len(self.stats_history)
        }
        
        if 'gpu_memory_percent' in self.stats_history[0]:
            avg_stats['gpu_memory_percent'] = sum(s['gpu_memory_percent'] for s in self.stats_history) / len(self.stats_history)
            
        return avg_stats

class TieredResponder:
    def __init__(self):
        self.context = zmq.Context()
        self.resource_manager = ResourceManager()
        self.response_queue = deque(maxlen=MAX_QUEUE_SIZE)
        self._setup_sockets()
        self._setup_tiers()
        self._setup_logging()
        self._setup_health_monitoring()
        
    def _setup_sockets(self):
        # Socket for receiving user queries and health checks
        self.pull_socket = self.context.socket(zmq.REP)  # Changed to REP to handle requests
        self.pull_socket.bind(f"tcp://*:{ZMQ_PULL_PORT}")
        
        # Socket for sending responses
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.bind(f"tcp://*:{ZMQ_PUSH_PORT}")
        
        # Socket for health monitoring
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind(f"tcp://*:{ZMQ_HEALTH_PORT}")
        
    def _setup_tiers(self):
        self.tiers = [
            {
                'name': 'instant',
                'max_response_time': MAX_RESPONSE_TIME['instant'],
                'patterns': [
                    'hello', 'hi', 'kumusta', 'kamusta', 
                    'thanks', 'thank you', 'salamat',
                    'bye', 'goodbye', 'paalam'
                ],
                'handler': self._handle_instant_response
            },
            {
                'name': 'fast',
                'max_response_time': MAX_RESPONSE_TIME['fast'],
                'patterns': [
                    'what is', 'who is', 'when is',
                    'how to', 'how do i', 'can you',
                    'tell me about'
                ],
                'handler': self._handle_fast_response
            },
            {
                'name': 'deep',
                'max_response_time': MAX_RESPONSE_TIME['deep'],
                'patterns': [
                    'plan', 'analyze', 'write', 'create',
                    'design', 'build', 'explain deeply',
                    'give me a detailed'
                ],
                'handler': self._handle_deep_response
            }
        ]
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_DIR / str(PathManager.get_logs_dir() / "tiered_responder.log")),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TieredResponder')
        
    def _setup_health_monitoring(self):
        """Setup health monitoring thread"""
        def monitor_health():
            while True:
                try:
                    stats = self.resource_manager.get_stats()
                    health_status = {
                        'status': 'ok' if self.resource_manager.check_resources() else 'degraded',
                        'stats': stats,
                        'queue_size': len(self.response_queue),
                        'timestamp': datetime.now().isoformat()
                    }
                    self.health_socket.send_json(health_status)
                    time.sleep(HEALTH_CHECK_INTERVAL)
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {str(e)}")
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor_health, daemon=True)
        thread.start()

    def start(self):
        """Start the tiered responder"""
        self.logger.info("Tiered Responder started")
        self._start_response_processor()
        
    def _start_response_processor(self):
        """Start background thread for processing queries and health checks"""
        def process_requests():
            while True:
                try:
                    if not self.resource_manager.check_resources():
                        self.logger.warning("Resource constraints detected, waiting...")
                        time.sleep(1)
                        continue
                        
                    # Receive request
                    request = self.pull_socket.recv_json()
                    
                    # Check if it's a health check request
                    if request.get('action') == 'health_check':
                        self._handle_health_check(request)
                    else:
                        # Handle regular query
                        self._handle_query(request)
                        
                except Exception as e:
                    self.logger.error(f"Error processing request: {str(e)}")
                    time.sleep(1)

        thread = threading.Thread(target=process_requests, daemon=True)
        thread.start()

    def _handle_query(self, query: Dict[str, Any]):
        """Handle incoming query and route to appropriate tier"""
        text = query.get('text', '').lower()
        
        # Check instant response patterns first
        for tier in self.tiers:
            if any(pattern in text for pattern in tier['patterns']):
                asyncio.run(tier['handler'](query, tier['name']))
                return
        
        # If no pattern matches, default to deep analysis
        asyncio.run(self._handle_deep_response(query, 'deep'))

    async def _handle_instant_response(self, query: Dict[str, Any], tier_name: str):
        """Handle instant response queries"""
        start_time = time.time()
        
        # Get canned response
        response = self._get_canned_response(query['text'])
        
        # Send response immediately
        await self._send_response(query, response, tier_name)
        
        # Log response time
        response_time = time.time() - start_time
        self.logger.info(f"Instant response time: {response_time:.3f}s")
        
        # Check if response time exceeded limit
        if response_time > MAX_RESPONSE_TIME['instant']:
            self.logger.warning(f"Instant response exceeded time limit: {response_time:.3f}s")

    async def _handle_fast_response(self, query: Dict[str, Any], tier_name: str):
        """Handle fast response queries"""
        start_time = time.time()
        
        # Check resources before processing
        if not self.resource_manager.check_resources():
            await self._send_thinking_message(query)
            time.sleep(0.5)  # Give resources time to free up
            
        # Use fast local model
        response = await self._get_fast_model_response(query['text'])
        
        # Send response
        await self._send_response(query, response, tier_name)
        
        # Log response time
        response_time = time.time() - start_time
        self.logger.info(f"Fast response time: {response_time:.3f}s")
        
        # Check if response time exceeded limit
        if response_time > MAX_RESPONSE_TIME['fast']:
            self.logger.warning(f"Fast response exceeded time limit: {response_time:.3f}s")

    async def _handle_deep_response(self, query: Dict[str, Any], tier_name: str):
        """Handle deep analysis queries"""
        start_time = time.time()
        
        # Send thinking message first
        await self._send_thinking_message(query)
        
        # Check resources before processing
        if not self.resource_manager.check_resources():
            await self._send_thinking_message(query, "Resources are constrained, please wait...")
            time.sleep(1)  # Give resources time to free up
            
        # Get detailed response
        response = await self._get_deep_model_response(query['text'])
        
        # Send final response
        await self._send_response(query, response, tier_name)
        
        # Log response time
        response_time = time.time() - start_time
        self.logger.info(f"Deep response time: {response_time:.3f}s")
        
        # Check if response time exceeded limit
        if response_time > MAX_RESPONSE_TIME['deep']:
            self.logger.warning(f"Deep response exceeded time limit: {response_time:.3f}s")

    def _get_canned_response(self, text: str) -> str:
        """Get pre-defined responses for instant queries"""
        responses = {
            'hello': "Hi there! How can I assist you today?",
            'hi': "Hello! What can I help you with?",
            'kumusta': "Kamusta! Paano kita matutulungan ngayon?",
            'thanks': "You're welcome! Is there anything else I can help with?",
            'bye': "Goodbye! Have a great day!"
        }
        
        # Get base word (hello -> hello, hi -> hi)
        base_word = text.split()[0].lower()
        return responses.get(base_word, "I'm here to help! What would you like to know?")

    async def _get_fast_model_response(self, text: str) -> str:
        """Get response from fast local model"""
        # Simulate model response
        return f"Fast response to: {text}"

    async def _get_deep_model_response(self, text: str) -> str:
        """Get detailed response from deep 
from main_pc_code.src.core.base_agent import BaseAgentmodel
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Load configuration at the module level
config = load_config()"""
        # Simulate model response
        return f"Detailed analysis of: {text}"

    async def _send_thinking_message(self, query: Dict[str, Any], message: str = None):
        """Send thinking message for deep queries"""
        if message is None:
            message = "Let me think about that for a moment..."
            
        message = {
            'type': 'thinking',
            'text': message,
            'timestamp': datetime.now().isoformat()
        }
        self.push_socket.send_json(message)

    async def _send_response(self, query: Dict[str, Any], response: str, tier: str):
        """Send final response with tier information"""
        message = {
            'type': 'response',
            'text': response,
            'tier': tier,
            'timestamp': datetime.now().isoformat()
        }
        self.push_socket.send_json(message)

    def _handle_health_check(self, request: Dict[str, Any]):
        """Handle health check requests"""
        try:
            stats = self.resource_manager.get_stats()
            health_status = {
                'status': 'ok' if self.resource_manager.check_resources() else 'degraded',
                'service': 'TieredResponder',
                'stats': stats,
                'queue_size': len(self.response_queue),
                'timestamp': datetime.now().isoformat()
            }
            self.pull_socket.send_json(health_status)
        except Exception as e:
            self.logger.error(f"Error handling health check: {str(e)}")
            error_response = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.pull_socket.send_json(error_response)

    def run(self):
        """Start the tiered responder"""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Tiered Responder shutting down...")
        finally:
            self.pull_socket.close()
            self.push_socket.close()
            self.health_socket.close()



    def _get_health_status(self) -> dict:


        """Return health status information."""


        base_status = super()._get_health_status()


        # Add any additional health information specific to ResourceManager


        base_status.update({


            'service': 'ResourceManager',


            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,


            'additional_info': {}


        })


        return base_status



    def cleanup(self):


        """Clean up resources before shutdown."""


        logger.info("Cleaning up resources...")


        # Add specific cleanup code here


        super().cleanup()

def main():
    responder = TieredResponder()
    responder.run()



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ResourceManager()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()
