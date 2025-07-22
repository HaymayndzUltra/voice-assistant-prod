#!/usr/bin/env python3
"""
Tiered Responder - Migrated to BaseAgent
Handles tiered response logic and routing for the agent system.

This agent provides intelligent response routing based on query complexity,
with instant, fast, and deep processing tiers optimized for different
response time requirements.
"""
import zmq
import json
from typing import Dict, Any, Callable, List
import logging
import asyncio
import time
import threading
import psutil
import torch
from collections import deque
import os
from datetime import datetime

# BaseAgent import - REQUIRED for migration
from common.core.base_agent import BaseAgent

# Standardized utilities
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.logger_util import get_json_logger
from common.utils.path_env import get_path, join_path, get_file_path

# Import error publisher for compatibility
from main_pc_code.agents.error_publisher import ErrorPublisher

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
    """Resource management for tiered response processing"""
    
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
                stats['gpu_memory_percent'] = (torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()) * 100
            except:
                stats['gpu_memory_percent'] = 0
            
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
            avg_stats['gpu_memory_percent'] = sum(s.get('gpu_memory_percent', 0) for s in self.stats_history) / len(self.stats_history)
        
        return avg_stats

class TieredResponder(BaseAgent):
    """
    Tiered Responder migrated to BaseAgent inheritance.
    
    Provides intelligent response routing based on query complexity,
    with instant, fast, and deep processing tiers.
    """
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        """
        Initialize the Tiered Responder with BaseAgent inheritance.
        
        Args:
            port: Main service port (optional, will use ZMQ_PULL_PORT if not provided)
            health_check_port: Health check port (optional, defaults to port+1)
            **kwargs: Additional configuration parameters
        """
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', 'TieredResponder'),
            port=port or ZMQ_PULL_PORT,
            health_check_port=health_check_port,
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Initialize resource manager
        self.resource_manager = ResourceManager()
        
        # Initialize error publisher for compatibility
        self.error_publisher = ErrorPublisher()
        
        # Response queue and statistics
        self.response_queue = deque(maxlen=MAX_QUEUE_SIZE)
        self.response_stats = {
            'instant_responses': 0,
            'fast_responses': 0,
            'deep_responses': 0,
            'total_queries': 0,
            'avg_response_time': 0.0,
            'start_time': time.time()
        }
        
        # Set up tiered response sockets
        self._setup_tiered_sockets()
        
        # Set up response tiers
        self._setup_tiers()
        
        # Start background processing
        self._start_response_processor()
        
        self.logger.info(f"{self.name} initialized successfully", extra={
            "port": self.port,
            "health_check_port": self.health_check_port,
            "pull_port": ZMQ_PULL_PORT,
            "push_port": ZMQ_PUSH_PORT,
            "component": "initialization"
        })
    
    def _setup_tiered_sockets(self):
        """Set up custom ZMQ sockets for tiered response handling."""
        try:
            # Socket for receiving user queries
            self.pull_socket = self.context.socket(zmq.PULL)
            self.pull_socket.bind(f"tcp://*:{ZMQ_PULL_PORT}")
            self.logger.info(f"Query receiver socket bound to port {ZMQ_PULL_PORT}")
            
            # Socket for sending responses
            self.push_socket = self.context.socket(zmq.PUSH)
            self.push_socket.bind(f"tcp://*:{ZMQ_PUSH_PORT}")
            self.logger.info(f"Response sender socket bound to port {ZMQ_PUSH_PORT}")
            
        except Exception as e:
            self.logger.error(f"Failed to set up tiered sockets: {e}")
            raise
        
    def _setup_tiers(self):
        """Set up response tiers with patterns and handlers"""
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
        
        self.logger.info("Response tiers configured", extra={
            "tiers": [tier['name'] for tier in self.tiers],
            "component": "tier_setup"
        })
    
    def _start_response_processor(self):
        """Start background thread for processing queries"""
        def process_queries():
            self.logger.info("Response processor thread started")
            while self.running:
                try:
                    # Check resource availability
                    if not self.resource_manager.check_resources():
                        self.logger.warning("Resource constraints detected, waiting...")
                        time.sleep(1)
                        continue
                    
                    # Check for incoming queries with timeout
                    if self.pull_socket.poll(timeout=1000):  # 1 second timeout
                        try:
                            query = self.pull_socket.recv_json(zmq.NOBLOCK)
                            self._handle_query(query)
                        except zmq.Again:
                            continue
                        except Exception as e:
                            self.logger.error(f"Error receiving query: {e}")
                    
                except Exception as e:
                    self.logger.error(f"Error in response processor: {e}")
                    self.error_publisher.publish_error(
                        error_type="query_processing", 
                        severity="high", 
                        details=str(e)
                    )
                    time.sleep(1)
            
            self.logger.info("Response processor thread stopped")
        
        self.response_processor_thread = threading.Thread(target=process_queries, daemon=True)
        self.response_processor_thread.start()
    
    def _handle_query(self, query: Dict[str, Any]):
        """Handle incoming query and route to appropriate tier"""
        try:
            text = query.get('text', '').lower()
            self.response_stats['total_queries'] += 1
            
            self.logger.info("Processing query", extra={
                "query_text": text[:100] + "..." if len(text) > 100 else text,
                "query_id": query.get('id', 'unknown'),
                "component": "query_processing"
            })
            
            # Check tier patterns and route accordingly
            for tier in self.tiers:
                if any(pattern in text for pattern in tier['patterns']):
                    asyncio.run(tier['handler'](query, tier['name']))
                    return
            
            # If no pattern matches, default to deep analysis
            asyncio.run(self._handle_deep_response(query, 'deep'))
            
        except Exception as e:
            self.logger.error(f"Error handling query: {e}", extra={
                "query": query,
                "component": "query_processing"
            })

    async def _handle_instant_response(self, query: Dict[str, Any], tier_name: str):
        """Handle instant response queries (< 100ms)"""
        start_time = time.time()
        
        try:
            # Get canned response
            response = self._get_canned_response(query['text'])
            
            # Send response immediately
            await self._send_response(query, response, tier_name)
            
            # Update statistics
            response_time = time.time() - start_time
            self.response_stats['instant_responses'] += 1
            
            self.logger.info("Instant response processed", extra={
                "response_time": response_time,
                "tier": tier_name,
                "query_id": query.get('id', 'unknown'),
                "component": "instant_response"
            })
            
            # Check if response time exceeded limit
            if response_time > MAX_RESPONSE_TIME['instant']:
                self.logger.warning(f"Instant response exceeded time limit: {response_time:.3f}s")
                
        except Exception as e:
            self.logger.error(f"Error in instant response: {e}")

    async def _handle_fast_response(self, query: Dict[str, Any], tier_name: str):
        """Handle fast response queries (< 1 second)"""
        start_time = time.time()
        
        try:
            # Quick processing logic
            response = self._process_fast_query(query['text'])
            
            # Send response
            await self._send_response(query, response, tier_name)
            
            # Update statistics
            response_time = time.time() - start_time
            self.response_stats['fast_responses'] += 1
            
            self.logger.info("Fast response processed", extra={
                "response_time": response_time,
                "tier": tier_name,
                "query_id": query.get('id', 'unknown'),
                "component": "fast_response"
            })
            
            # Check if response time exceeded limit
            if response_time > MAX_RESPONSE_TIME['fast']:
                self.logger.warning(f"Fast response exceeded time limit: {response_time:.3f}s")
                
        except Exception as e:
            self.logger.error(f"Error in fast response: {e}")

    async def _handle_deep_response(self, query: Dict[str, Any], tier_name: str):
        """Handle deep response queries (< 5 seconds)"""
        start_time = time.time()
        
        try:
            # Complex processing logic
            response = self._process_deep_query(query['text'])
            
            # Send response
            await self._send_response(query, response, tier_name)
            
            # Update statistics
            response_time = time.time() - start_time
            self.response_stats['deep_responses'] += 1
            
            self.logger.info("Deep response processed", extra={
                "response_time": response_time,
                "tier": tier_name,
                "query_id": query.get('id', 'unknown'),
                "component": "deep_response"
            })
            
            # Check if response time exceeded limit
            if response_time > MAX_RESPONSE_TIME['deep']:
                self.logger.warning(f"Deep response exceeded time limit: {response_time:.3f}s")
                
        except Exception as e:
            self.logger.error(f"Error in deep response: {e}")

    def _get_canned_response(self, text: str) -> str:
        """Get canned response for instant queries"""
        text_lower = text.lower()
        
        canned_responses = {
            'hello': "Hello! How can I help you today?",
            'hi': "Hi there! What can I do for you?",
            'kumusta': "Kumusta! Anong maitutulong ko sa'yo?",
            'kamusta': "Kamusta! Anong maitutulong ko sa'yo?",
            'thanks': "You're welcome! Is there anything else I can help with?",
            'thank you': "You're very welcome! Happy to help!",
            'salamat': "Walang anuman! May iba pa ba akong maitutulong?",
            'bye': "Goodbye! Have a great day!",
            'goodbye': "See you later! Take care!",
            'paalam': "Paalam! Ingat ka!"
        }
        
        for keyword, response in canned_responses.items():
            if keyword in text_lower:
                return response
        
        return "I understand. How can I assist you further?"

    def _process_fast_query(self, text: str) -> str:
        """Process fast queries with simple logic"""
        # Simulate fast processing
        time.sleep(0.1)  # Small delay for realistic processing
        
        return f"Quick response to: {text[:50]}{'...' if len(text) > 50 else ''}"

    def _process_deep_query(self, text: str) -> str:
        """Process deep queries with complex logic"""
        # Simulate deep processing
        time.sleep(1)  # Longer delay for complex processing
        
        return f"Detailed analysis of: {text[:100]}{'...' if len(text) > 100 else ''}"

    async def _send_response(self, query: Dict[str, Any], response: str, tier: str):
        """Send response back to the client"""
        try:
            message = {
                'query_id': query.get('id', 'unknown'),
                'type': 'response',
                'text': response,
                'tier': tier,
                'timestamp': datetime.now().isoformat(),
                'agent': self.name
            }
            
            self.push_socket.send_json(message)
            
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get current response statistics"""
        uptime = time.time() - self.response_stats['start_time']
        total_responses = (self.response_stats['instant_responses'] + 
                          self.response_stats['fast_responses'] + 
                          self.response_stats['deep_responses'])
        
        return {
            **self.response_stats,
            'uptime_seconds': uptime,
            'total_responses': total_responses,
            'responses_per_minute': (total_responses / uptime) * 60 if uptime > 0 else 0,
            'resource_stats': self.resource_manager.get_average_stats()
        }

    def run(self):
        """
        Main execution method using BaseAgent's run() framework.
        """
        try:
            self.logger.info(f"Starting {self.name}")
            
            # Start statistics reporting
            self._start_statistics_reporting()
            
            # Call parent run() method for standard startup
            super().run()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested via KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in {self.name}: {e}")
            raise
        finally:
            self.cleanup()
    
    def _start_statistics_reporting(self):
        """Start periodic statistics reporting"""
        def stats_reporter():
            while self.running:
                try:
                    stats = self.get_statistics()
                    self.logger.info("Tiered responder statistics", extra={
                        "statistics": stats,
                        "component": "statistics_reporting"
                    })
                    time.sleep(120)  # Report every 2 minutes
                except Exception as e:
                    self.logger.error(f"Error in statistics reporting: {e}")
                    time.sleep(30)
        
        self.stats_reporter_thread = threading.Thread(target=stats_reporter, daemon=True)
        self.stats_reporter_thread.start()

    def cleanup(self):
        """
        Cleanup method with custom cleanup logic for tiered responder.
        """
        try:
            self.logger.info(f"Cleaning up {self.name}")
            
            # Custom cleanup logic
            if hasattr(self, 'pull_socket'):
                self.pull_socket.close()
            
            if hasattr(self, 'push_socket'):
                self.push_socket.close()
            
            # Call parent cleanup
            super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


def main():
    """Main function for backwards compatibility"""
    responder = TieredResponder()
    responder.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run TieredResponder")
    parser.add_argument('--port', type=int, help='Main service port')
    parser.add_argument('--health-port', type=int, help='Health check port')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Create and run agent
    responder = TieredResponder(
        port=args.port,
        health_check_port=args.health_port
    )
    
    responder.run() 