import redis
import yaml
import sys
import os
import json
import threading
import time
import logging
import psutil
from datetime import timedelta
from typing import Dict, Any, Optional, Union
from pathlib import Path
# ✅ MODERNIZED: Standardized path management using PathManager only  
from common.utils.path_manager import PathManager


# ✅ MODERNIZED: Standardized path management using PathManager only
from common.utils.path_manager import PathManager
from pathlib import Path

# Add project root to path using PathManager (standardized approach)
PROJECT_ROOT = PathManager.get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    

from common.core.base_agent import BaseAgent
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.utils.config_loader import Config
# ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
# Removed: from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
# Now using: self.report_error() method from BaseAgent
from pc2_code.utils.pc2_error_publisher import create_pc2_error_publisher

# Load configuration at the module level
config = Config().get_config()

# Constants
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

class ResourceMonitor:
    """
    ResourceMonitor: Monitors system resources.
    """
    def __init__(self):
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
        
        # PC2 Error Bus Integration (Phase 1.3)
        self.error_publisher = create_pc2_error_publisher("cache_manager")
    def check_resources(self) -> bool:
        """Check if resources are available"""
        stats = self.get_stats()
        return stats['memory_percent'] <= self.memory_threshold

class CacheManager(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()
    
    """
    Centralized cache management service using Redis
    """
    def __init__(self, port: int = 7102, health_port: int = 8102):
        super().__init__(name="CacheManager", port=port, health_check_port=health_port)
        self.start_time = time.time()
        self.logger = logging.getLogger("CacheManager")
        
        # Set up resource monitoring
        self.resource_monitor = ResourceMonitor()
        
        # Load configuration
        self.config = load_config()
        
        # Set up error reporting
        # ✅ MODERNIZED: No setup needed - using BaseAgent's UnifiedErrorHandler
        
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Redis connection error: {e}")
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
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Override BaseAgent's handle_request to process cache requests"""
        return self.process_request(request)
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming cache requests"""
        action = request.get('action', '')
        
        # Handle health check requests
        if action in ['ping', 'health', 'health_check']:
            return self._get_health_status()
        
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache get error: {e}")
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache set error: {e}")
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache delete error: {e}")
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache get error: {e}")
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
                ttl = int(self.cache_config[cache_type]['ttl'].total_seconds()
            elif ttl is None:
                ttl = 3600  # Default 1 hour
            
            self.redis.setex(redis_key, ttl, serialized)
            return {'status': 'success', 'message': 'Cache entry stored'}
        except Exception as e:
            self.logger.error(f"Error putting cache entry: {e}")
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache set error: {e}")
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache delete error: {e}")
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
            # ✅ MODERNIZED: Using BaseAgent's error reporting
            self.report_error(f"Cache flush error: {e}")
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
                # ✅ MODERNIZED: Using BaseAgent's error reporting
                self.report_error(f"Cache maintenance error: {e}")
            
            # Sleep for maintenance interval
            time.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop the service"""
        self.stop_event.set()
        if hasattr(self, 'maintenance_thread') and self.maintenance_thread.is_alive():
            self.maintenance_thread.join(timeout=1.0)
        super().stop()
    
    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        base_status = super()._get_health_status()
        base_status.update({
            "status": "ok" if self.redis_available else "degraded",
            "redis_available": self.redis_available,
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None)
        })
        
        # Add Redis info if available
        if self.redis_available:
            try:
                info = self.redis.info()
                base_status["redis_info"] = {
                    "memory_used": info.get("used_memory_human", "N/A"),
                    "clients_connected": info.get("connected_clients", 0),
                    "uptime": info.get("uptime_in_seconds", 0)
                }
            except Exception as e:
                self.logger.error(f"Error getting Redis info: {e}")
                
        return base_status
    
    def health_check(self):
        """Return the health status of the agent"""
        return self._get_health_status()
    
    def cleanup(self):
        """
        ✅ Gold Standard cleanup with robust try...finally block.
        This guarantees that the parent's critical cleanup (NATS, Redis health)
        is ALWAYS called, even if the child's cleanup steps fail.
        """
        self.logger.info(f"🚀 Starting Gold Standard cleanup for {self.__class__.__name__}...")
        cleanup_errors = []
        
        try:
            # Stop maintenance thread
            self.logger.info("Stopping maintenance thread...")
            self.stop()
            
            # Close Redis connection
            if hasattr(self, 'redis') and self.redis:
                try:
                    self.redis.close()
                    self.logger.info("✅ Redis connection closed")
                except Exception as e:
                    cleanup_errors.append(f"Redis close error: {e}")
                    self.logger.error(f"❌ Error closing Redis connection: {e}")
            
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                try:
                    self.socket.close()
                    self.logger.info("✅ ZMQ socket closed")
                except Exception as e:
                    cleanup_errors.append(f"ZMQ socket close error: {e}")
                    self.logger.warning(f"❌ Error closing ZMQ socket: {e}")
                    
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.term()
                    self.logger.info("✅ ZMQ context terminated")
                except Exception as e:
                    cleanup_errors.append(f"ZMQ context term error: {e}")
                    self.logger.warning(f"❌ Error terminating ZMQ context: {e}")
                    
        except Exception as e:
            cleanup_errors.append(f"General cleanup error: {e}")
            self.logger.error(f"❌ Unexpected error during cleanup: {e}")
            
        finally:
            # ✅ CRITICAL: Always call parent cleanup regardless of errors above
            self.logger.info("Final Step: Calling BaseAgent cleanup (NATS, Health, etc.)...")
            try:
                super().cleanup()
                self.logger.info("✅ BaseAgent cleanup completed successfully")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
                self.logger.error(f"❌ BaseAgent cleanup failed: {e}")
        
        # Report cleanup status
        if cleanup_errors:
            self.logger.warning(f"⚠️ Cleanup for {self.__class__.__name__} finished with {len(cleanup_errors)} error(s):")
            for i, err in enumerate(cleanup_errors):
                self.logger.warning(f"   - Error {i+1}: {err}")
        else:
            self.logger.info(f"✅ Cleanup for {self.__class__.__name__} completed perfectly without any errors.")

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
    config_path = Path(PathManager.get_project_root() / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip(),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = get_mainpc_ip()
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

if __name__ == "__main__":
    main()
