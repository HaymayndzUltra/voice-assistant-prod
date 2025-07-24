#!/usr/bin/env python3
"""
Unified Tiered Responder - Cross-Machine Compatible
Handles tiered response logic and routing for the agent system.

This agent provides intelligent response routing based on query complexity,
with instant, fast, and deep processing tiers optimized for different
response time requirements.

Features:
- BaseAgent inheritance for standardized lifecycle management
- Machine-specific configuration (MainPC vs PC2)
- Resource-aware processing with adaptive scaling
- Error handling with SafeExecutor patterns
- Standardized logging and health monitoring
"""
import zmq
import json
from typing import Dict, Any, Callable, List, Optional
import logging
import asyncio
import time
import threading
import psutil
import torch
from collections import deque
import os
from datetime import datetime
from pathlib import Path

# BaseAgent import - REQUIRED for migration
from common.core.base_agent import BaseAgent
from common_utils.error_handling import SafeExecutor

# Standardized utilities
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.logger_util import get_json_logger

# Machine-specific imports with fallback
try:
    from main_pc_code.agents.error_publisher import ErrorPublisher
    MACHINE_TYPE = "MainPC"
except ImportError:
    try:
        from pc2_code.agents.utils.config_loader import Config
        MACHINE_TYPE = "PC2"
    except ImportError:
        MACHINE_TYPE = "Generic"

# Configuration constants with machine-specific defaults
DEFAULT_PORTS = {
    "MainPC": {
        "zmq_pull_port": 5619,
        "zmq_push_port": 5620,
        "health_port": 5621
    },
    "PC2": {
        "zmq_pull_port": 7101,
        "zmq_push_port": 7102,
        "health_port": 7103
    },
    "Generic": {
        "zmq_pull_port": 7100,
        "zmq_push_port": 7101,
        "health_port": 7102
    }
}

MAX_QUEUE_SIZE = 1000
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_RESPONSE_TIME = {
    'instant': 0.1,  # 100ms
    'fast': 1.0,     # 1 second
    'deep': 5.0      # 5 seconds
}

class ResourceManager:
    """Resource management for tiered response processing"""
    
    def __init__(self, machine_type: str = "Generic"):
        self.machine_type = machine_type
        self.cpu_threshold = 80  # percentage
        self.memory_threshold = 85  # percentage
        self.gpu_memory_threshold = 90  # percentage
        self.stats_history = deque(maxlen=60)  # Keep 60 samples (30 minutes at 30s intervals)
        
        # Machine-specific resource thresholds
        if machine_type == "MainPC":
            self.cpu_threshold = 75  # More conservative for MainPC
            self.memory_threshold = 80
        elif machine_type == "PC2":
            self.cpu_threshold = 85  # More aggressive for PC2
            self.memory_threshold = 90
            
    def get_stats(self) -> Dict[str, float]:
        """Get current resource statistics"""
        def get_resource_stats():
            stats = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'timestamp': time.time()
            }
            
            # GPU stats if available
            if torch.cuda.is_available():
                try:
                    stats['gpu_memory_percent'] = (
                        torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()
                    ) * 100
                except Exception:
                    stats['gpu_memory_percent'] = 0
            else:
                stats['gpu_memory_percent'] = 0
                
            return stats
        
        return SafeExecutor.execute_with_fallback(
            get_resource_stats,
            fallback_value={'cpu_percent': 0, 'memory_percent': 0, 'gpu_memory_percent': 0, 'timestamp': time.time()},
            context="get resource statistics",
            expected_exceptions=(psutil.Error, RuntimeError, OSError)
        )
    
    def check_resources(self) -> bool:
        """Check if resources are available for processing"""
        stats = self.get_stats()
        self.stats_history.append(stats)
        
        # Check individual thresholds
        if stats['cpu_percent'] > self.cpu_threshold:
            return False
        if stats['memory_percent'] > self.memory_threshold:
            return False
        if stats.get('gpu_memory_percent', 0) > self.gpu_memory_threshold:
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
        
        if self.stats_history and 'gpu_memory_percent' in self.stats_history[0]:
            avg_stats['gpu_memory_percent'] = sum(s.get('gpu_memory_percent', 0) for s in self.stats_history) / len(self.stats_history)
        
        return avg_stats

class TieredResponder(BaseAgent):
    """
    Unified Tiered Responder with cross-machine compatibility.
    
    Provides intelligent response routing based on query complexity,
    with instant, fast, and deep processing tiers.
    """
    
    def __init__(self, port: int = None, health_check_port: int = None, machine_type: str = None, **kwargs):
        """
        Initialize the Unified Tiered Responder.
        
        Args:
            port: Main service port (optional, will use machine-specific defaults)
            health_check_port: Health check port (optional, defaults to port+1)
            machine_type: Machine type ("MainPC", "PC2", or "Generic")
            **kwargs: Additional configuration parameters
        """
        # Auto-detect machine type if not provided
        self.machine_type = machine_type or MACHINE_TYPE
        
        # Get machine-specific port configuration
        default_ports = DEFAULT_PORTS[self.machine_type]
        
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', f'TieredResponder-{self.machine_type}'),
            port=port or default_ports["zmq_pull_port"],
            health_check_port=health_check_port or default_ports["health_port"],
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Initialize resource manager with machine type
        self.resource_manager = ResourceManager(self.machine_type)
        
        # Initialize error publisher for MainPC compatibility
        if self.machine_type == "MainPC":
            def init_error_publisher():
                return ErrorPublisher()
            self.error_publisher = SafeExecutor.execute_with_fallback(
                init_error_publisher,
                fallback_value=None,
                context="initialize error publisher",
                expected_exceptions=(ImportError, Exception)
            )
        else:
            self.error_publisher = None
        
        # Response queue and statistics
        self.response_queue = deque(maxlen=MAX_QUEUE_SIZE)
        self.response_stats = {
            'instant_responses': 0,
            'fast_responses': 0,
            'deep_responses': 0,
            'total_queries': 0,
            'avg_response_time': 0.0,
            'start_time': time.time(),
            'machine_type': self.machine_type
        }
        
        # Set up tiered response components
        self._setup_tiered_sockets()
        self._setup_tiers()
        self._start_health_monitoring()
        
        self.logger.info("Unified Tiered Responder initialized", extra={
            "machine_type": self.machine_type,
            "port": self.port,
            "health_port": self.health_check_port,
            "component": "initialization"
        })
    
    def _setup_tiered_sockets(self):
        """Set up ZMQ sockets for tiered processing"""
        def setup_sockets():
            # Use BaseAgent's context or create new one
            context = getattr(self, 'context', None) or zmq.Context()
            
            # Pull socket for receiving queries
            self.pull_socket = context.socket(zmq.PULL)
            self.pull_socket.bind(f"tcp://*:{self.port}")
            
            # Push socket for sending responses
            push_port = DEFAULT_PORTS[self.machine_type]["zmq_push_port"]
            self.push_socket = context.socket(zmq.PUSH)
            self.push_socket.bind(f"tcp://*:{push_port}")
            
            return True
        
        SafeExecutor.execute_with_fallback(
            setup_sockets,
            fallback_value=None,
            context="setup tiered sockets",
            expected_exceptions=(zmq.ZMQError, OSError)
        )
    
    def _setup_tiers(self):
        """Configure response tiers with machine-specific optimizations"""
        base_tiers = [
            {
                'name': 'instant',
                'max_response_time': MAX_RESPONSE_TIME['instant'],
                'patterns': [
                    'hello', 'hi', 'yes', 'no', 'ok', 'thanks',
                    'status', 'ping', 'health'
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
        
        # Machine-specific tier adjustments
        if self.machine_type == "PC2":
            # PC2 might have different response time tolerances
            for tier in base_tiers:
                tier['max_response_time'] *= 1.2  # 20% more time allowance
        
        self.tiers = base_tiers
        
        self.logger.info("Response tiers configured", extra={
            "tiers": [tier['name'] for tier in self.tiers],
            "machine_type": self.machine_type,
            "component": "tier_setup"
        })
    
    def _handle_instant_response(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle instant responses (< 100ms)"""
        start_time = time.time()
        
        # Simple pattern matching for instant responses
        query_text = query.get('text', '').lower()
        
        instant_responses = {
            'ping': {'status': 'pong', 'response_time': 0.001},
            'health': {'status': 'healthy', 'machine_type': self.machine_type},
            'status': self.get_status(),
            'hello': {'message': 'Hello! How can I help you?'},
            'hi': {'message': 'Hi there!'},
        }
        
        response = instant_responses.get(query_text, {
            'message': 'I understand this is a simple query.',
            'tier': 'instant'
        })
        
        response_time = time.time() - start_time
        response['response_time'] = response_time
        response['tier'] = 'instant'
        
        self.response_stats['instant_responses'] += 1
        return response
    
    def _handle_fast_response(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fast responses (< 1s)"""
        start_time = time.time()
        
        # Simulate fast processing
        response = {
            'message': f"Fast response to: {query.get('text', 'query')}",
            'tier': 'fast',
            'machine_type': self.machine_type,
            'processed_by': self.name
        }
        
        response_time = time.time() - start_time
        response['response_time'] = response_time
        
        self.response_stats['fast_responses'] += 1
        return response
    
    def _handle_deep_response(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deep responses (< 5s)"""
        start_time = time.time()
        
        # Simulate deeper processing
        time.sleep(0.1)  # Simulate processing time
        
        response = {
            'message': f"Deep analysis of: {query.get('text', 'query')}",
            'tier': 'deep',
            'machine_type': self.machine_type,
            'processed_by': self.name,
            'analysis': {
                'complexity': 'high',
                'resource_usage': self.resource_manager.get_stats()
            }
        }
        
        response_time = time.time() - start_time
        response['response_time'] = response_time
        
        self.response_stats['deep_responses'] += 1
        return response
    
    def _determine_tier(self, query: Dict[str, Any]) -> str:
        """Determine appropriate response tier for query"""
        query_text = query.get('text', '').lower()
        
        for tier in self.tiers:
            for pattern in tier['patterns']:
                if pattern in query_text:
                    return tier['name']
        
        # Default to fast tier
        return 'fast'
    
    def _handle_query(self, query: Dict[str, Any]):
        """Process incoming query with appropriate tier"""
        start_time = time.time()
        
        try:
            # Determine response tier
            tier_name = self._determine_tier(query)
            tier = next(t for t in self.tiers if t['name'] == tier_name)
            
            # Process with appropriate handler
            response = tier['handler'](query)
            response['query_id'] = query.get('id', f"query_{int(time.time())}")
            
            # Send response
            SafeExecutor.execute_with_fallback(
                lambda: self.push_socket.send_json(response, zmq.NOBLOCK),
                fallback_value=None,
                context="send query response",
                expected_exceptions=(zmq.ZMQError, json.JSONEncodeError)
            )
            
            # Update statistics
            self.response_stats['total_queries'] += 1
            total_time = time.time() - start_time
            self.response_stats['avg_response_time'] = (
                (self.response_stats['avg_response_time'] * (self.response_stats['total_queries'] - 1) + total_time)
                / self.response_stats['total_queries']
            )
            
            self.logger.info(f"Query processed", extra={
                "tier": tier_name,
                "response_time": total_time,
                "query_id": response['query_id'],
                "component": "query_processing"
            })
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            
            # Report error using machine-specific method
            if self.error_publisher:
                SafeExecutor.execute_with_fallback(
                    lambda: self.error_publisher.publish_error(
                        error_type="query_processing", 
                        severity="high", 
                        details=str(e)
                    ),
                    fallback_value=None,
                    context="publish query error",
                    expected_exceptions=(Exception,)
                )
            else:
                # Use BaseAgent error reporting
                self.report_error(f"Query processing error: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        uptime = time.time() - self.response_stats['start_time']
        resource_stats = self.resource_manager.get_average_stats()
        
        return {
            'status': 'running',
            'machine_type': self.machine_type,
            'uptime_seconds': uptime,
            'response_stats': self.response_stats.copy(),
            'resource_stats': resource_stats,
            'queue_size': len(self.response_queue),
            'health': 'good' if self.resource_manager.check_resources() else 'degraded',
            'timestamp': datetime.now().isoformat()
        }
    
    def run(self):
        """Main execution loop with BaseAgent integration"""
        self.logger.info(f"Starting Unified Tiered Responder ({self.machine_type})")
        
        # Start response processor thread
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
                    if hasattr(self, 'pull_socket') and self.pull_socket.poll(timeout=1000):
                        try:
                            query = self.pull_socket.recv_json(zmq.NOBLOCK)
                            self._handle_query(query)
                        except zmq.Again:
                            continue
                        except Exception as e:
                            self.logger.error(f"Error receiving query: {e}")
                    
                except Exception as e:
                    self.logger.error(f"Error in response processor: {e}")
                    time.sleep(1)
            
            self.logger.info("Response processor thread stopped")
        
        # Start processing thread
        processor_thread = threading.Thread(target=process_queries, daemon=True)
        processor_thread.start()
        
        # Call BaseAgent's run method for health monitoring and lifecycle
        super().run()

if __name__ == "__main__":
    # Auto-detect machine type and start agent
    responder = TieredResponder()
    try:
        responder.run()
    except KeyboardInterrupt:
        responder.logger.info("Tiered Responder shutting down...")
        responder.shutdown() 