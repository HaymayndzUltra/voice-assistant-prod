import redis
import yaml
import sys
import os
import json
from datetime import datetime, timedelta

# Add the project's pc2_code directory to the Python path
import sys
import os
from pathlib import Path
PC2_CODE_DIR = Path(__file__).resolve().parent.parent
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

from typing import Dict, Any, Optional, List, Union
import hashlib
import logging
import psutil
import zmq
import threading
import time
from pathlib import Path
from collections import defaultdict


from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Load configuration at the module level
config = Config().get_config()# Constants
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
HEALTH_PORT = 5618
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_CACHE_SIZE = 1000  # Maximum number of cache entries
CACHE_CLEANUP_INTERVAL = 300  # 5 minutes

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("CacheManager")

class ResourceMonitor(
    """
    ResourceMonitor:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """BaseAgent):
    def __init__(self):
        super().__init__(name="ResourceMonitor", port=None)
        self.memory_threshold = 80  # percentage
        self.last_check = time.time()
        self.stats_history = []
        self.error_bus = setup_error_reporting(self)
def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        stats = {
            'memory_percent': psutil.virtual_memory().percent,
            'timestamp': time.time()
        }
        self.stats_history.append(stats)
        return stats
        
    def check_resources(self) -> bool:
        """Check if resources are available"""
        stats = self.get_stats()
        return stats['memory_percent'] <= self.memory_threshold



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
class CacheManager(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()"""
    Centralized cache management service using Redis
    """
    def __init__(self, port: int = 7102, health_port: int = 8102):
        super().__init__(name="CacheManager", port=port, health_check_port=health_port)
        self.logger = logging.getLogger("CacheManager")
        
        # Redis connection
        try:
            self.redis = redis.Redis(
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', 6379)),
                password=os.environ.get('REDIS_PASSWORD', None),
                decode_responses=False  # Keep as bytes for compatibility
            )
            self.redis.ping()  # Test connection
            self.logger.info("Connected to Redis server")
            self.redis_available = True
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self.redis_available = False
        
        # Cache configuration - TTL and priorities
        self.cache_config = {
            'nlu_results': {
                'ttl': timedelta(minutes=5),
                'max_size': 1000,
                'priority': 'high'
            },
            'model_decisions': {
                'ttl': timedelta(minutes=10),
                'max_size': 500,
                'priority': 'high'
            },
            'context_summaries': {
                'ttl': timedelta(hours=1),
                'max_size': 200,
                'priority': 'medium'
            },
            'tool_responses': {
                'ttl': timedelta(minutes=15),
                'max_size': 1000,
                'priority': 'low'
            },
            'memory': {
                'ttl': timedelta(hours=12),  # Memory cache has longer TTL
                'max_size': 5000,
                'priority': 'high'
            }
        }
        
        # Start background maintenance thread
        self.stop_event = threading.Event()
        self.maintenance_thread = threading.Thread(target=self._run_maintenance, daemon=True)
        self.maintenance_thread.start()
    
    def run(self):
        """Main service loop"""
        self.logger.info("CacheManager service started")
        super().run()  # Use BaseAgent's request loop
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming cache requests"""
        action = request.get('action', '')
        
        # Handle health check requests
        if action in ['ping', 'health', 'health_check']:
            return {'status': 'success', 'message': 'CacheManager is healthy'}
        
        # Memory-specific cache operations
        if action == 'get_cached_memory':
            memory_id = request.get('memory_id')
            if not memory_id:
                return {'status': 'error', 'message': 'Missing memory_id parameter'}
            return self.get_cached_memory(memory_id)
            
        elif action == 'cache_memory':
            memory_id = request.get('memory_id')
            data = request.get('data')
            ttl = request.get('ttl', 3600)  # Default 1 hour TTL
            if not memory_id or data is None:
                return {'status': 'error', 'message': 'Missing required parameters'}
            return self.cache_memory(memory_id, data, ttl)
            
        elif action == 'invalidate_memory_cache':
            memory_id = request.get('memory_id')
            if not memory_id:
                return {'status': 'error', 'message': 'Missing memory_id parameter'}
            return self.invalidate_memory_cache(memory_id)
        
        # General cache operations
        elif action == 'get':
            cache_type = request.get('cache_type', '')
            key = request.get('key', '')
            if not cache_type or not key:
                return {'status': 'error', 'message': 'Missing cache_type or key parameter'}
            return self.get_cache_entry(cache_type, key)
            
        elif action == 'put':
            cache_type = request.get('cache_type', '')
            key = request.get('key', '')
            value = request.get('value')
            ttl = request.get('ttl')
            if not cache_type or not key or value is None:
                return {'status': 'error', 'message': 'Missing required parameters'}
            return self.put_cache_entry(cache_type, key, value, ttl)
            
        elif action == 'invalidate':
            cache_type = request.get('cache_type', '')
            key = request.get('key', '')
            if not cache_type or not key:
                return {'status': 'error', 'message': 'Missing cache_type or key parameter'}
            return self.invalidate_cache_entry(cache_type, key)
            
        elif action == 'flush':
            cache_type = request.get('cache_type', '')
            if not cache_type:
                return {'status': 'error', 'message': 'Missing cache_type parameter'}
            return self.flush_cache(cache_type)
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def get_cached_memory(self, memory_id: Union[int, str]) -> Dict[str, Any]:
        """Get a memory from the cache"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            key = f"memory:{memory_id}"
            data = self.redis.get(key)
            if data:
                return {'status': 'success', 'data': json.loads(data)}
            return {'status': 'error', 'message': 'Cache miss', 'data': None}
        except Exception as e:
            self.logger.error(f"Error getting memory from cache: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def cache_memory(self, memory_id: Union[int, str], data: Dict[str, Any], ttl: int = 3600) -> Dict[str, Any]:
        """Cache a memory"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            key = f"memory:{memory_id}"
            serialized = json.dumps(data)
            self.redis.setex(key, ttl, serialized)
            return {'status': 'success', 'message': 'Memory cached successfully'}
        except Exception as e:
            self.logger.error(f"Error caching memory: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def invalidate_memory_cache(self, memory_id: Union[int, str]) -> Dict[str, Any]:
        """Invalidate a memory in the cache"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            key = f"memory:{memory_id}"
            deleted = self.redis.delete(key)
            if deleted:
                return {'status': 'success', 'message': 'Memory cache entry invalidated'}
            return {'status': 'success', 'message': 'Memory cache entry not found'}
        except Exception as e:
            self.logger.error(f"Error invalidating memory cache: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_cache_entry(self, cache_type: str, key: str) -> Dict[str, Any]:
        """Get an entry from the cache"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            redis_key = f"{cache_type}:{key}"
            data = self.redis.get(redis_key)
            if data:
                return {'status': 'success', 'data': json.loads(data)}
            return {'status': 'error', 'message': 'Cache miss', 'data': None}
        except Exception as e:
            self.logger.error(f"Error getting cache entry: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def put_cache_entry(self, cache_type: str, key: str, value: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Put an entry in the cache"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            redis_key = f"{cache_type}:{key}"
            serialized = json.dumps(value)
            
            # Use configured TTL if not specified
            if ttl is None and cache_type in self.cache_config:
                ttl = int(self.cache_config[cache_type]['ttl'].total_seconds())
            elif ttl is None:
                ttl = 3600  # Default 1 hour
            
            self.redis.setex(redis_key, ttl, serialized)
            return {'status': 'success', 'message': 'Cache entry stored'}
        except Exception as e:
            self.logger.error(f"Error putting cache entry: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def invalidate_cache_entry(self, cache_type: str, key: str) -> Dict[str, Any]:
        """Invalidate a cache entry"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            redis_key = f"{cache_type}:{key}"
            deleted = self.redis.delete(redis_key)
            if deleted:
                return {'status': 'success', 'message': 'Cache entry invalidated'}
            return {'status': 'success', 'message': 'Cache entry not found'}
        except Exception as e:
            self.logger.error(f"Error invalidating cache entry: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def flush_cache(self, cache_type: str) -> Dict[str, Any]:
        """Flush all entries of a specific cache type"""
        if not self.redis_available:
            return {'status': 'error', 'message': 'Redis is not available'}
        
        try:
            pattern = f"{cache_type}:*"
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = self.redis.scan(cursor, pattern, 100)
                if keys:
                    deleted_count += self.redis.delete(*keys)
                if cursor == 0:
                    break
            
            return {'status': 'success', 'message': f'Flushed {deleted_count} cache entries'}
        except Exception as e:
            self.logger.error(f"Error flushing cache: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _run_maintenance(self):
        """Background thread for cache maintenance"""
        while not self.stop_event.is_set():
            try:
                # Perform maintenance tasks here (e.g., cleanup, stats collection)
                if self.redis_available:
                    # Log cache stats periodically
                    info = self.redis.info()
                    self.logger.debug(f"Redis memory used: {info.get('used_memory_human', 'N/A')}")
                    
                    # TODO: Implement more sophisticated cache eviction policies
                    # based on priority and access patterns if needed
            except Exception as e:
                self.logger.error(f"Error in cache maintenance: {e}")
            
            # Sleep for maintenance interval
            time.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop the service"""
        self.stop_event.set()
        if hasattr(self, 'maintenance_thread') and self.maintenance_thread.is_alive():
            self.maintenance_thread.join(timeout=1.0)
        super().stop()

class CacheManagerHealth:
    def __init__(self, port=7102):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.running = True
    def start(self):
        print(f"Starting CacheManagerHealth on port {self.port}")
        self.socket.bind(f"tcp://*:{self.port}")
        while self.running:
            try:
                request = self.socket.recv_json()
                if request.get('action') == 'health_check':
                    response = {'status': 'ok', 'service': 'CacheManager', 'port': self.port, 'timestamp': time.time()}
                else:
                    response = {'status': 'unknown_action', 'message': f"Unknown action: {request.get('action', 'none')}"}
                self.socket.send_json(response)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    def stop(self):
        self.running = False
        self.socket.close()
        self.context.term()

def main():
    agent = None
    try:
        agent = CacheManager()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
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
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")


    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None))
        }
if __name__ == "__main__":
    main()
