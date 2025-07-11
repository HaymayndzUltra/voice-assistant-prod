import zmq
import json
from typing import Dict, Any, Callable, List
import logging
from main_pc_code.agents.error_publisher import ErrorPublisher
from datetime import datetime
import asyncio
import time
import threading
import psutil
import torch
from collections import deque
import os

# Constants
ZMQ_PULL_PORT = 5619
ZMQ_PUSH_PORT = 5620
MAX_QUEUE_SIZE = 1000
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_RESPONSE_TIME = {
    'instant': 0.1,  # 100ms
    'fast': 1.0,     # 1 second
    'deep': 5.0      # 5 seconds
}

class ResourceManager:
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
            stats['gpu_memory_percent'] = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100
            
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
        self._setup_sockets()
        self._setup_tiers()
        self._setup_logging()
        self._setup_health_monitoring()
        self.response_queue = deque(maxlen=MAX_QUEUE_SIZE)
        
    def _setup_sockets(self):
        # Socket for receiving user queries
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(f"tcp://*:{ZMQ_PULL_PORT}")
        
        # Socket for sending responses
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.bind(f"tcp://*:{ZMQ_PUSH_PORT}")
        
        # Socket for health monitoring
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind("tcp://*:5621")
        
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
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/tiered_responder.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TieredResponder')
        # Setup error publisher
        self.error_publisher = ErrorPublisher(self.name)
        
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
                    self.error_publisher.publish_error(error_type="health_monitor", severity="high", details=str(e))
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor_health, daemon=True)
        thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(thread)

    def start(self):
        """Start the tiered responder"""
        self.logger.info("Tiered Responder started")
        # Ensure publisher connection warms up
        time.sleep(0.1)
        self._start_response_processor()
        
    def _start_response_processor(self):
        """Start background thread for processing queries"""
        def process_queries():
            while True:
                try:
                    if not self.resource_manager.check_resources():
                        self.logger.warning("Resource constraints detected, waiting...")
                        time.sleep(1)
                        continue
                        
                    query = self.pull_socket.recv_json()
                    self._handle_query(query)
                except Exception as e:
                    self.logger.error(f"Error processing query: {str(e)}")
                    self.error_publisher.publish_error(error_type="query_processing", severity="high", details=str(e))
                    time.sleep(1)

        thread = threading.Thread(target=process_queries, daemon=True)
        thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(thread)

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
        """Get detailed response from deep model"""
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

def main():
    responder = TieredResponder()
    responder.run()

if __name__ == "__main__":
    main() 