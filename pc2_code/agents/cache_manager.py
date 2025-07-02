import redis
import yaml
import sys
import os
import json
from datetime import datetime, timede

# Add the project's pc2_code directory to the Python path
import sys
import os
from pathlib import Path
PC2_CODE_DIR = Path(__file__).resolve().parent.parent
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

lta
from typing import Dict, Any, Optional, List, Union
import hashlib
import logging
import psutil
import zmq
import threading
import time
from pathlib import Path
from collections import defaultdict


from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

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

class ResourceMonitor(BaseAgent):
    def __init__(self):
        super().__init__(name="ResourceMonitor", port=None)
        self.memory_threshold = 80  # percentage
        self.last_check = time.time()
        self.stats_history = []
        
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
    def __init__(self, redis_host=REDIS_HOST, redis_port=REDIS_PORT, db=REDIS_DB, port: int = 7102):
        super().__init__(name="CacheManager", port=port)
        self.start_time = time.time()
        self.running = True
        self.request_count = 0
        self.main_pc_connections = {}
        logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")
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
            }
        }
        self.cache_stats = defaultdict(lambda: {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        })
        self.resource_monitor = ResourceMonitor()
        self._setup_logging()
        try:
            self.redis = redis.Redis(host=redis_host, port=redis_port, db=db)
            # Test connection
            self.redis.ping()
            self.redis_available = True
        except Exception as e:
            self.logger.error(f"Redis connection error: {e}")
            self.redis_available = False
        # Setup monitoring threads after all attributes are initialized
        self._setup_health_monitoring()
        self._setup_cache_cleanup()

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_DIR / 'cache_manager.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('CacheManager')

    def _setup_health_monitoring(self):
        """Setup health monitoring thread"""
        def monitor_health():
            context = zmq.Context()
            socket = context.socket(zmq.PUB)
            socket.bind(f"tcp://*:{HEALTH_PORT}")
            
            while True:
                try:
                    stats = self.resource_monitor.get_stats()
                    cache_stats = self._get_cache_stats()
                    health_status = {
                        'status': 'ok' if self.resource_monitor.check_resources() else 'degraded',
                        'stats': stats,
                        'cache_stats': cache_stats,
                        'timestamp': datetime.now().isoformat()
                    }
                    socket.send_json(health_status)
                    time.sleep(HEALTH_CHECK_INTERVAL)
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {str(e)}")
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor_health, daemon=True)
        thread.start()

    def _setup_cache_cleanup(self):
        """Setup periodic cache cleanup"""
        def cleanup_cache():
            while True:
                try:
                    self._cleanup_expired_entries()
                    self._enforce_size_limits()
                    time.sleep(CACHE_CLEANUP_INTERVAL)
                except Exception as e:
                    self.logger.error(f"Cache cleanup error: {str(e)}")
                    time.sleep(60)
                    
        thread = threading.Thread(target=cleanup_cache, daemon=True)
        thread.start()

    def _generate_cache_key(self, cache_type: str, data: Any) -> str:
        """Generate a unique cache key based on data and type"""
        key_data = json.dumps({
            'type': cache_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }, sort_keys=True)
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get current cache statistics"""
        return dict(self.cache_stats)

    def _cleanup_expired_entries(self):
        """Clean up expired cache entries"""
        for cache_type, config in self.cache_config.items():
            pattern = f"cache:{cache_type}:*"
            for key in self.redis.scan_iter(match=pattern):
                if not self.redis.ttl(key):
                    self.redis.delete(key)
                    self.cache_stats[cache_type]['evictions'] += 1

    def _enforce_size_limits(self):
        """Enforce size limits for each cache type"""
        for cache_type, config in self.cache_config.items():
            pattern = f"cache:{cache_type}:*"
            keys = list(self.redis.scan_iter(match=pattern))
            
            if len(keys) > config.get('max_size'):
                # Remove oldest entries
                keys_to_remove = keys[:-config.get('max_size')]
                for key in keys_to_remove:
                    self.redis.delete(key)
                    self.cache_stats[cache_type]['evictions'] += 1

    def cache_nlu_result(self, user_input: str, intent: str, entities: Dict[str, Any]) -> None:
        """Cache NLU processing results"""
        if not self.resource_monitor.check_resources():
            self.logger.warning("Resource constraints detected, skipping cache")
            return
        if not getattr(self, 'redis_available', True):
            self.logger.warning("Redis unavailable, skipping cache")
            return
            
        cache_key = self._generate_cache_key('nlu_results', user_input)
        cache_data = {
            'intent': intent,
            'entities': entities,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.redis.setex(
                cache_key,
                self.cache_config.get('nlu_results')['ttl'],
                json.dumps(cache_data)
            )
            self.cache_stats['nlu_results']['size'] += 1
        except Exception as e:
            self.logger.error(f"Error caching NLU result: {str(e)}")

    def get_cached_nlu_result(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Get cached NLU results"""
        cache_key = self._generate_cache_key('nlu_results', user_input)
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                self.cache_stats['nlu_results']['hits'] += 1
                return json.loads(cached_data)
            self.cache_stats['nlu_results']['misses'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached NLU result: {str(e)}")
            return None

    def cache_model_decision(self, task_type: str, model_id: str) -> None:
        """Cache model router decisions"""
        if not self.resource_monitor.check_resources():
            self.logger.warning("Resource constraints detected, skipping cache")
            return
            
        cache_key = self._generate_cache_key('model_decisions', task_type)
        cache_data = {
            'model_id': model_id,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.redis.setex(
                cache_key,
                self.cache_config.get('model_decisions')['ttl'],
                json.dumps(cache_data)
            )
            self.cache_stats['model_decisions']['size'] += 1
        except Exception as e:
            self.logger.error(f"Error caching model decision: {str(e)}")

    def get_cached_model_decision(self, task_type: str) -> Optional[str]:
        """Get cached model decision"""
        cache_key = self._generate_cache_key('model_decisions', task_type)
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                self.cache_stats['model_decisions']['hits'] += 1
                return json.loads(cached_data)['model_id']
            self.cache_stats['model_decisions']['misses'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached model decision: {str(e)}")
            return None

    def cache_context_summary(self, session_id: str, summary: str) -> None:
        """Cache context summaries"""
        if not self.resource_monitor.check_resources():
            self.logger.warning("Resource constraints detected, skipping cache")
            return
            
        cache_key = self._generate_cache_key('context_summaries', session_id)
        cache_data = {
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.redis.setex(
                cache_key,
                self.cache_config.get('context_summaries')['ttl'],
                json.dumps(cache_data)
            )
            self.cache_stats['context_summaries']['size'] += 1
        except Exception as e:
            self.logger.error(f"Error caching context summary: {str(e)}")

    def get_cached_context_summary(self, session_id: str) -> Optional[str]:
        """Get cached context summary"""
        cache_key = self._generate_cache_key('context_summaries', session_id)
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                self.cache_stats['context_summaries']['hits'] += 1
                return json.loads(cached_data)['summary']
            self.cache_stats['context_summaries']['misses'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached context summary: {str(e)}")
            return None

    def cache_tool_response(self, tool_name: str, response: Any) -> None:
        """Cache tool responses"""
        if not self.resource_monitor.check_resources():
            self.logger.warning("Resource constraints detected, skipping cache")
            return
            
        cache_key = self._generate_cache_key('tool_responses', tool_name)
        cache_data = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.redis.setex(
                cache_key,
                self.cache_config.get('tool_responses')['ttl'],
                json.dumps(cache_data)
            )
            self.cache_stats['tool_responses']['size'] += 1
        except Exception as e:
            self.logger.error(f"Error caching tool response: {str(e)}")

    def get_cached_tool_response(self, tool_name: str) -> Optional[Any]:
        """Get cached tool response"""
        cache_key = self._generate_cache_key('tool_responses', tool_name)
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                self.cache_stats['tool_responses']['hits'] += 1
                return json.loads(cached_data)['response']
            self.cache_stats['tool_responses']['misses'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached tool response: {str(e)}")
            return None

    def invalidate_cache(self, cache_type: str, data: Any) -> None:
        """Invalidate specific cache entry"""
        cache_key = self._generate_cache_key(cache_type, data)
        try:
            self.redis.delete(cache_key)
            if cache_type in self.cache_stats:
                self.cache_stats[cache_type]['size'] = max(0, self.cache_stats[cache_type]['size'] - 1)
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {str(e)}")

    def clear_all_cache(self) -> None:
        """Clear all cache entries"""
        try:
            self.redis.flushdb()
            for cache_type in self.cache_stats:
                self.cache_stats[cache_type]['size'] = 0
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")

    def run(self):
        """Run the cache manager"""
        self.logger.info("Cache Manager started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Cache Manager shutting down...")

    def _get_health_status(self):
        base_status = super()._get_health_status()
        base_status.update({
            'service': 'CacheManager',
            'uptime': time.time() - self.start_time
        })
        return base_status

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

if __name__ == "__main__":
    main()
