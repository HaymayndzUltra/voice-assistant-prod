#!/usr/bin/env python3
"""
PC2 Tiered Responder - Migrated to BaseAgent
PC2-specific tiered response handling for the distributed agent system.

This agent provides tiered response processing for PC2, optimized for
the PC2 machine environment with instant, fast, and deep processing tiers.
"""
import zmq
import json
from typing import Dict, Any, Callable, List
import logging
import asyncio
import time
from datetime import datetime
import threading

# BaseAgent import - REQUIRED for migration
from common.core.base_agent import BaseAgent

# Standardized utilities
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.logger_util import get_json_logger
from common.utils.path_manager import PathManager

# Constants for PC2 tiered responder
PC2_PULL_PORT = 5619
PC2_PUSH_PORT = 5620
MAX_RESPONSE_TIME = {
    'instant': 0.1,  # 100ms
    'fast': 1.0,     # 1 second
    'deep': 5.0      # 5 seconds
}

class TieredResponder(BaseAgent):
    """
    PC2 Tiered Responder migrated to BaseAgent inheritance.
    
    Provides tiered response processing specifically optimized for PC2,
    with instant, fast, and deep processing tiers for distributed workload.
    """
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        """
        Initialize the PC2 Tiered Responder with BaseAgent inheritance.
        
        Args:
            port: Main service port (optional, will use PC2_PULL_PORT if not provided)
            health_check_port: Health check port (optional, defaults to port+1)
            **kwargs: Additional configuration parameters
        """
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', 'PC2TieredResponder'),
            port=port or PC2_PULL_PORT,
            health_check_port=health_check_port,
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Response statistics for PC2
        self.response_stats = {
            'instant_responses': 0,
            'fast_responses': 0,
            'deep_responses': 0,
            'total_queries': 0,
            'pc2_specific_queries': 0,
            'start_time': time.time()
        }
        
        # Set up PC2 tiered response sockets
        self._setup_pc2_sockets()
        
        # Set up response tiers for PC2
        self._setup_tiers()
        
        # Start background processing
        self._start_response_processor()
        
        self.logger.info(f"{self.name} initialized successfully", extra={
            "port": self.port,
            "health_check_port": self.health_check_port,
            "pull_port": PC2_PULL_PORT,
            "push_port": PC2_PUSH_PORT,
            "machine": "PC2",
            "component": "initialization"
        })
    
    def _setup_pc2_sockets(self):
        """Set up custom ZMQ sockets for PC2 tiered response handling."""
        try:
            # Socket for receiving user queries
            self.pull_socket = self.context.socket(zmq.PULL)
            self.pull_socket.bind(f"tcp://*:{PC2_PULL_PORT}")
            self.logger.info(f"PC2 query receiver socket bound to port {PC2_PULL_PORT}")
            
            # Socket for sending responses
            self.push_socket = self.context.socket(zmq.PUSH)
            self.push_socket.bind(f"tcp://*:{PC2_PUSH_PORT}")
            self.logger.info(f"PC2 response sender socket bound to port {PC2_PUSH_PORT}")
            
        except Exception as e:
            self.logger.error(f"Failed to set up PC2 sockets: {e}")
            raise
        
    def _setup_tiers(self):
        """Set up response tiers with patterns and handlers for PC2"""
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
        
        self.logger.info("PC2 response tiers configured", extra={
            "tiers": [tier['name'] for tier in self.tiers],
            "machine": "PC2",
            "component": "tier_setup"
        })
    
    def _start_response_processor(self):
        """Start background thread for processing queries"""
        def process_queries():
            self.logger.info("PC2 response processor thread started")
            while self.running:
                try:
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
                    self.logger.error(f"Error in PC2 response processor: {e}")
                    time.sleep(1)
            
            self.logger.info("PC2 response processor thread stopped")
        
        self.response_processor_thread = threading.Thread(target=process_queries, daemon=True)
        self.response_processor_thread.start()
    
    def _handle_query(self, query: Dict[str, Any]):
        """Handle incoming query and route to appropriate tier"""
        try:
            text = query.get('text', '').lower()
            self.response_stats['total_queries'] += 1
            
            # Check for PC2-specific patterns
            if self._is_pc2_specific_query(text):
                self.response_stats['pc2_specific_queries'] += 1
            
            self.logger.info("Processing PC2 query", extra={
                "query_text": text[:100] + "..." if len(text) > 100 else text,
                "query_id": query.get('id', 'unknown'),
                "machine": "PC2",
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
            self.logger.error(f"Error handling PC2 query: {e}", extra={
                "query": query,
                "machine": "PC2",
                "component": "query_processing"
            })
    
    def _is_pc2_specific_query(self, text: str) -> bool:
        """Check if query is PC2-specific"""
        pc2_keywords = ['pc2', 'secondary', 'backup', 'distributed', 'remote']
        return any(keyword in text for keyword in pc2_keywords)

    async def _handle_instant_response(self, query: Dict[str, Any], tier_name: str):
        """Handle instant response queries (< 100ms) on PC2"""
        start_time = time.time()
        
        try:
            # Get canned response optimized for PC2
            response = self._get_pc2_canned_response(query['text'])
            
            # Send response immediately
            await self._send_response(query, response, tier_name)
            
            # Update statistics
            response_time = time.time() - start_time
            self.response_stats['instant_responses'] += 1
            
            self.logger.info("PC2 instant response processed", extra={
                "response_time": response_time,
                "tier": tier_name,
                "query_id": query.get('id', 'unknown'),
                "machine": "PC2",
                "component": "instant_response"
            })
            
            # Check if response time exceeded limit
            if response_time > MAX_RESPONSE_TIME['instant']:
                self.logger.warning(f"PC2 instant response exceeded time limit: {response_time:.3f}s")
                
        except Exception as e:
            self.logger.error(f"Error in PC2 instant response: {e}")

    async def _handle_fast_response(self, query: Dict[str, Any], tier_name: str):
        """Handle fast response queries (< 1 second) on PC2"""
        start_time = time.time()
        
        try:
            # PC2-optimized fast processing
            response = self._process_pc2_fast_query(query['text'])
            
            # Send response
            await self._send_response(query, response, tier_name)
            
            # Update statistics
            response_time = time.time() - start_time
            self.response_stats['fast_responses'] += 1
            
            self.logger.info("PC2 fast response processed", extra={
                "response_time": response_time,
                "tier": tier_name,
                "query_id": query.get('id', 'unknown'),
                "machine": "PC2",
                "component": "fast_response"
            })
            
            # Check if response time exceeded limit
            if response_time > MAX_RESPONSE_TIME['fast']:
                self.logger.warning(f"PC2 fast response exceeded time limit: {response_time:.3f}s")
                
        except Exception as e:
            self.logger.error(f"Error in PC2 fast response: {e}")

    async def _handle_deep_response(self, query: Dict[str, Any], tier_name: str):
        """Handle deep response queries (< 5 seconds) on PC2"""
        start_time = time.time()
        
        try:
            # PC2-optimized deep processing
            response = self._process_pc2_deep_query(query['text'])
            
            # Send response
            await self._send_response(query, response, tier_name)
            
            # Update statistics
            response_time = time.time() - start_time
            self.response_stats['deep_responses'] += 1
            
            self.logger.info("PC2 deep response processed", extra={
                "response_time": response_time,
                "tier": tier_name,
                "query_id": query.get('id', 'unknown'),
                "machine": "PC2",
                "component": "deep_response"
            })
            
            # Check if response time exceeded limit
            if response_time > MAX_RESPONSE_TIME['deep']:
                self.logger.warning(f"PC2 deep response exceeded time limit: {response_time:.3f}s")
                
        except Exception as e:
            self.logger.error(f"Error in PC2 deep response: {e}")

    def _get_pc2_canned_response(self, text: str) -> str:
        """Get PC2-specific canned response for instant queries"""
        text_lower = text.lower()
        
        pc2_canned_responses = {
            'hello': "Hello from PC2! How can I assist you today?",
            'hi': "Hi there from PC2! What can I do for you?",
            'kumusta': "Kumusta from PC2! Anong maitutulong ko sa'yo?",
            'kamusta': "Kamusta from PC2! Anong maitutulong ko sa'yo?",
            'thanks': "You're welcome from PC2! Anything else I can help with?",
            'thank you': "You're very welcome from PC2! Happy to help!",
            'salamat': "Walang anuman from PC2! May iba pa ba akong maitutulong?",
            'bye': "Goodbye from PC2! Have a great day!",
            'goodbye': "See you later from PC2! Take care!",
            'paalam': "Paalam from PC2! Ingat ka!"
        }
        
        for keyword, response in pc2_canned_responses.items():
            if keyword in text_lower:
                return response
        
        return "PC2 here - I understand. How can I assist you further?"

    def _process_pc2_fast_query(self, text: str) -> str:
        """Process fast queries with PC2-optimized logic"""
        # Simulate PC2 fast processing
        time.sleep(0.05)  # Slightly faster on PC2
        
        return f"PC2 quick response to: {text[:50]}{'...' if len(text) > 50 else ''}"

    def _process_pc2_deep_query(self, text: str) -> str:
        """Process deep queries with PC2-optimized logic"""
        # Simulate PC2 deep processing
        time.sleep(0.8)  # Slightly faster deep processing on PC2
        
        return f"PC2 detailed analysis of: {text[:100]}{'...' if len(text) > 100 else ''}"

    async def _send_response(self, query: Dict[str, Any], response: str, tier: str):
        """Send response back to the client with PC2 identification"""
        try:
            message = {
                'query_id': query.get('id', 'unknown'),
                'type': 'response',
                'text': response,
                'tier': tier,
                'timestamp': datetime.now().isoformat(),
                'agent': self.name,
                'machine': 'PC2'
            }
            
            self.push_socket.send_json(message)
            
        except Exception as e:
            self.logger.error(f"Error sending PC2 response: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get current PC2 response statistics"""
        uptime = time.time() - self.response_stats['start_time']
        total_responses = (self.response_stats['instant_responses'] + 
                          self.response_stats['fast_responses'] + 
                          self.response_stats['deep_responses'])
        
        return {
            **self.response_stats,
            'uptime_seconds': uptime,
            'total_responses': total_responses,
            'responses_per_minute': (total_responses / uptime) * 60 if uptime > 0 else 0,
            'pc2_query_percentage': (self.response_stats['pc2_specific_queries'] / max(1, self.response_stats['total_queries'])) * 100,
            'machine': 'PC2'
        }

    def run(self):
        """
        Main execution method using BaseAgent's run() framework.
        """
        try:
            self.logger.info(f"Starting {self.name} on PC2")
            
            # Start statistics reporting
            self._start_statistics_reporting()
            
            # Call parent run() method for standard startup
            super().run()
            
        except KeyboardInterrupt:
            self.logger.info("PC2 shutdown requested via KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in {self.name}: {e}")
            raise
        finally:
            self.cleanup()
    
    def _start_statistics_reporting(self):
        """Start periodic statistics reporting for PC2"""
        def stats_reporter():
            while self.running:
                try:
                    stats = self.get_statistics()
                    self.logger.info("PC2 tiered responder statistics", extra={
                        "statistics": stats,
                        "machine": "PC2",
                        "component": "statistics_reporting"
                    })
                    time.sleep(180)  # Report every 3 minutes for PC2
                except Exception as e:
                    self.logger.error(f"Error in PC2 statistics reporting: {e}")
                    time.sleep(30)
        
        self.stats_reporter_thread = threading.Thread(target=stats_reporter, daemon=True)
        self.stats_reporter_thread.start()

    def cleanup(self):
        """
        Cleanup method with custom cleanup logic for PC2 tiered responder.
        """
        try:
            self.logger.info(f"Cleaning up {self.name} on PC2")
            
            # Custom cleanup logic
            if hasattr(self, 'pull_socket'):
                self.pull_socket.close()
            
            if hasattr(self, 'push_socket'):
                self.push_socket.close()
            
            # Call parent cleanup
            super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during PC2 cleanup: {e}")


def main():
    """Main function for backwards compatibility"""
    responder = TieredResponder()
    responder.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run PC2 TieredResponder")
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
