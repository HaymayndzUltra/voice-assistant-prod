import redis
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import hashlib
import logging
import psutil
import zmq
import threading
import time
from pathlib import Path
from collections import defaultdict
from common.config_manager import get_service_ip, get_service_url, get_redis_url


from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env


# Load configuration at the module level
config = load_config()# Constants
${SECRET_PLACEHOLDER} 'localhost'
${SECRET_PLACEHOLDER} 6379
${SECRET_PLACEHOLDER} 0
HEALTH_PORT = 5618
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_CACHE_SIZE = 1000  # Maximum number of cache entries
CACHE_CLEANUP_INTERVAL = 300  # 5 minutes

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class ResourceMonitor(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self):
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

class CacheManager:
    def __init__(self, redis_host=${SECRET_PLACEHOLDER}
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
            
            if len(keys) > config['max_size']:
                # Remove oldest entries
                keys_to_remove = keys[:-config['max_size']]
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
                self.cache_config['nlu_results']['ttl'],
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
                self.cache_config['model_decisions']['ttl'],
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
                self.cache_config['context_summaries']['ttl'],
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
                self.cache_config['tool_responses']['ttl'],
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


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to ResourceMonitor

        base_status.update({

            'service': 'ResourceMonitor',

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
    cache_manager = CacheManager()
    cache_manager.run()



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ResourceMonitor()
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
