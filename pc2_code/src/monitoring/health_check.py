#!/usr/bin/env python3
"""
Health Check Agent
-----------------
Monitors the health status of all services and agents in the distributed voice assistant system.

Responsibilities:
- Performs health checks on all registered services
- Monitors service availability and response times
- Tracks service uptime and performance metrics
- Provides health status reports to other components
- Alerts when services become unavailable
- Maintains health check history and trends

This agent uses ZMQ REP socket on port 5591 to receive commands and health check requests,
and a PUB socket on port 5592 to broadcast health status updates.
"""

import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
import datetime
from collections import defaultdict, deque
import requests
import socket


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility with fallback
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
from common.env_helpers import get_env
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args = parse_agent_args()
except ImportError:
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = join_path("logs", "health_check_agent.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HealthCheckAgent")

# ZMQ ports
HEALTH_CHECK_PORT = 5591
HEALTH_CHECK_HEALTH_PORT = 5592

# Health check constants
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_DEGRADED = "degraded"
HEALTH_STATUS_UNHEALTHY = "unhealthy"
HEALTH_STATUS_UNKNOWN = "unknown"

class ServiceHealth:
    """Class representing the health status of a service"""
    def __init__(self, service_id: str, service_name: str, host: str, port: int):
        self.service_id = service_id
        self.service_name = service_name
        self.host = host
        self.port = port
        self.status = HEALTH_STATUS_UNKNOWN
        self.last_check = None
        self.response_time = None
        self.error_count = 0
        self.success_count = 0
        self.last_error = None
        self.uptime_start = time.time()
        self.health_history = deque(maxlen=100)
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "host": self.host,
            "port": self.port,
            "status": self.status,
            "last_check": self.last_check,
            "response_time": self.response_time,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "last_error": self.last_error,
            "uptime": time.time() - self.uptime_start,
            "success_rate": self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0.0
        }

class HealthCheckAgent:
    """Main health check agent class"""
    def __init__(self, port=None):
        try:
            # Set up ports
            self.main_port = port if port else HEALTH_CHECK_PORT
            self.health_port = self.main_port + 1
            
            # Initialize ZMQ context and server socket
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.main_port}")
            
            # Initialize PUB socket for health updates
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"HealthCheckAgent PUB socket bound to port {self.health_port}")
            
            # Service registry
            self.services: Dict[str, ServiceHealth] = {}
            self.service_configs: Dict[str, Dict[str, Any]] = {}
            
            # Health check settings
            self.check_interval = 30  # seconds
            self.timeout = 10  # seconds
            self.max_retries = 3
            
            # Monitoring threads
            self.monitor_thread = threading.Thread(target=self.monitor_services_loop, daemon=True)
            self.running = True
            
            logger.info(f"HealthCheckAgent initialized on port {self.main_port}")
        except Exception as e:
            logger.error(f"Failed to initialize HealthCheckAgent: {str(e)}")
            raise

    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'HealthCheckAgent',
            'timestamp': datetime.datetime.now().isoformat(),
            'monitor_thread_alive': self.monitor_thread.is_alive() if hasattr(self, 'monitor_thread') else False,
            'registered_services': len(self.services),
            'port': self.main_port
        }

    def register_service(self, service_id: str, service_name: str, host: str, port: int, 
                        health_check_payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Register a new service for health monitoring."""
        try:
            if service_id in self.services:
                return {'status': 'error', 'message': 'Service already registered'}
            
            service = ServiceHealth(service_id, service_name, host, port)
            self.services[service_id] = service
            
            if health_check_payload:
                self.service_configs[service_id] = health_check_payload
            
            logger.info(f"Registered service: {service_id} ({service_name}) at {host}:{port}")
            return {'status': 'success', 'message': 'Service registered successfully'}
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return {'status': 'error', 'message': str(e)}

    def unregister_service(self, service_id: str) -> Dict[str, Any]:
        """Unregister a service from health monitoring."""
        try:
            if service_id not in self.services:
                return {'status': 'error', 'message': 'Service not registered'}
            
            del self.services[service_id]
            if service_id in self.service_configs:
                del self.service_configs[service_id]
            
            logger.info(f"Unregistered service: {service_id}")
            return {'status': 'success', 'message': 'Service unregistered successfully'}
        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            return {'status': 'error', 'message': str(e)}

    def check_service_health(self, service_id: str) -> Dict[str, Any]:
        """Perform a health check on a specific service."""
        try:
            if service_id not in self.services:
                return {'status': 'error', 'message': 'Service not registered'}
            
            service = self.services[service_id]
            start_time = time.time()
            
            # Try to connect to the service
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((service.host, service.port))
                sock.close()
                
                if result == 0:
                    # Connection successful, try ZMQ health check if payload is configured
                    if service_id in self.service_configs:
                        health_result = self._perform_zmq_health_check(service, self.service_configs[service_id])
                    else:
                        health_result = {'status': 'success', 'message': 'Connection successful'}
                    
                    service.status = HEALTH_STATUS_HEALTHY
                    service.success_count += 1
                    service.last_error = None
                else:
                    health_result = {'status': 'error', 'message': 'Connection failed'}
                    service.status = HEALTH_STATUS_UNHEALTHY
                    service.error_count += 1
                    service.last_error = 'Connection failed'
                
                service.response_time = time.time() - start_time
                service.last_check = time.time()
                
                # Record in history
                service.health_history.append({
                    'timestamp': service.last_check,
                    'status': service.status,
                    'response_time': service.response_time,
                    'error': service.last_error
                })
                
                return {
                    'status': 'success',
                    'service_id': service_id,
                    'health_result': health_result,
                    'service_status': service.to_dict()
                }
                
            except Exception as e:
                service.status = HEALTH_STATUS_UNHEALTHY
                service.error_count += 1
                service.last_error = str(e)
                service.last_check = time.time()
                
                return {
                    'status': 'error',
                    'service_id': service_id,
                    'error': str(e)
                }
                
        except Exception as e:
            logger.error(f"Error checking service health: {e}")
            return {'status': 'error', 'message': str(e)}

    def _perform_zmq_health_check(self, service: ServiceHealth, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform ZMQ-based health check with payload."""
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.settimeout(self.timeout * 1000)  # Convert to milliseconds
            
            socket.connect(f"tcp://{service.host}:{service.port}")
            socket.send_json(payload)
            
            if socket.poll(self.timeout * 1000):
                response = socket.recv_json()
                socket.close()
                context.term()
                return response
            else:
                socket.close()
                context.term()
                return {'status': 'error', 'message': 'Health check timeout'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_all_services_health(self) -> Dict[str, Any]:
        """Get health status of all registered services."""
        try:
            services_status = {}
            for service_id, service in self.services.items():
                services_status[service_id] = service.to_dict()
            
            return {
                'status': 'success',
                'services': services_status,
                'total_services': len(self.services),
                'healthy_services': sum(1 for s in self.services.values() if s.status == HEALTH_STATUS_HEALTHY),
                'unhealthy_services': sum(1 for s in self.services.values() if s.status == HEALTH_STATUS_UNHEALTHY)
            }
        except Exception as e:
            logger.error(f"Error getting all services health: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'health_check':
            return self._health_check()
        elif action == 'register_service':
            return self.register_service(
                request.get('service_id'),
                request.get('service_name'),
                request.get('host'),
                request.get('port'),
                request.get('health_check_payload')
            )
        elif action == 'unregister_service':
            return self.unregister_service(request.get('service_id'))
        elif action == 'check_service':
            return self.check_service_health(request.get('service_id'))
        elif action == 'get_all_services':
            return self.get_all_services_health()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        """Start monitoring and handle requests"""
        logger.info(f"HealthCheckAgent starting on port {self.main_port}")
        
        # Start monitoring thread
        self.monitor_thread.start()
        
        try:
            while self.running:
                try:
                    # Wait for messages with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()

    def monitor_services_loop(self):
        """Background thread for monitoring service health"""
        logger.info("Starting service monitoring loop")
        while self.running:
            try:
                for service_id in list(self.services.keys()):
                    self.check_service_health(service_id)
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in service monitoring loop: {e}")
                time.sleep(self.check_interval)

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up HealthCheckAgent resources...")
        self.running = False
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Cleanup complete")

    def stop(self):
        """Stop the agent gracefully."""
        self.running = False

if __name__ == "__main__":
    # Create and run the Health Check Agent
    agent = HealthCheckAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Health Check Agent interrupted")
    finally:
        agent.cleanup() 