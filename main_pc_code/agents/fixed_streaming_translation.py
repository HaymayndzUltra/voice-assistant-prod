from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Enhanced Fixed Streaming Translation Agent with Intelligent Fallback
Acts as a customer service interface for the main translator, handling translation requests
and managing communication between the main system and PC2's translation service.
Includes intelligent multi-layer fallback system and advanced performance monitoring.
"""

from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import logging
import time
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import os
import re
from googletrans import Translator as GoogleTranslator
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from common.config_manager import load_unified_config
import psutil

# Load configuration at module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).parent.parent, 'logs', 'fixed_translation.log'))
    ]
)
logger = logging.getLogger("FixedStreamingTranslation")

# Configuration flags - load from config with fallbacks
ENABLE_FALLBACKS = config.get("enable_fallbacks", True)
ENABLE_GOOGLE_TRANSLATE_FALLBACK = config.get("enable_google_translate_fallback", True)
ENABLE_LOCAL_PATTERN_FALLBACK = config.get("enable_local_pattern_fallback", True)
ENABLE_EMERGENCY_FALLBACK = config.get("enable_emergency_fallback", True)
ENABLE_CACHING = config.get("enable_caching", True)
ENABLE_PERFORMANCE_MONITORING = config.get("enable_performance_monitoring", True)

# PC2 Translator configuration
PC2_IP = config.get("pc2_ip", get_service_ip("pc2"))
PC2_TRANSLATOR_PORT = config.get("pc2_translator_port", 5563)
PC2_TRANSLATOR_ADDRESS = f"tcp://{PC2_IP}:{PC2_TRANSLATOR_PORT}"
PC2_PERFORMANCE_PORT = config.get("pc2_performance_port", 5632)

# Cache configuration
CACHE_SIZE = config.get("cache_size", 1000)
CACHE_TTL = config.get("cache_ttl", 3600)  # 1 hour

# ZMQ timeout configuration
ZMQ_REQUEST_TIMEOUT = config.get("zmq_request_timeout", 5000)  # 5 seconds

class PerformanceMonitor(BaseAgent):
    """Monitors and tracks performance metrics for translation services."""
    
    def __init__(self, port: int = 5584, **kwargs):
        super().__init__(port=port, name="FixedStreamingTranslation")
        self.service_latencies = defaultdict(list)
        self.service_errors = defaultdict(int)
        self.service_successes = defaultdict(int)
        self.lock = threading.Lock()
        self.max_history = 100  # Keep last 100 measurements
        self._running = False
        self._thread = None
        
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        
        logger.info("PerformanceMonitor initialized")
    
    def start(self):
        """Start the performance monitoring thread."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop)
        self._thread.daemon = True
        self._thread.start()
        logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop the performance monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        context = None  # Using pool
        socket = get_sub_socket(endpoint).socket
        socket.connect(f"tcp://{PC2_IP}:{PC2_PERFORMANCE_PORT}")
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        
        while self._running:
            try:
                if socket.poll(1000, zmq.POLLIN):
                    data = socket.recv_json()
                    if isinstance(data, dict):
                        self._update_metrics(data)
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                self.report_error(f"Error in performance monitoring: {e}")
                time.sleep(1)
    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)
    
    def _update_metrics(self, data: Dict):
        """Update performance metrics from received data."""
        with self.lock:
            service = data.get('service')
            if not service:
                return
                
            latency = data.get('latency')
            if latency:
                self.service_latencies[service].append(latency)
                if len(self.service_latencies[service]) > self.max_history:
                    self.service_latencies[service].pop(0)
            
            if data.get('status') == 'success':
                self.service_successes[service] += 1
            else:
                self.service_errors[service] += 1
    
    def get_best_service(self) -> str:
        """Get the service with the best performance."""
        with self.lock:
            best_service = None
            best_latency = float('inf')
            
            for service, latencies in self.service_latencies.items():
                if not latencies:
                    continue
                    
                # Calculate weighted average (recent latencies have more weight)
                weights = np.linspace(0.5, 1.0, len(latencies))
                avg_latency = np.average(latencies, weights=weights)
                
                # Adjust for error rate
                total_requests = self.service_successes[service] + self.service_errors[service]
                if total_requests > 0:
                    error_rate = self.service_errors[service] / total_requests
                    avg_latency *= (1 + error_rate)  # Penalize services with high error rates
                
                if avg_latency < best_latency:
                    best_latency = avg_latency
                    best_service = service
            
            return best_service or 'nllb'  # Default to NLLB if no data
    
    def get_service_stats(self) -> Dict:
        """Get performance statistics for all services."""
        with self.lock:
            stats = {}
            for service in set(self.service_latencies.keys()) | set(self.service_successes.keys()):
                latencies = self.service_latencies[service]
                stats[service] = {
                    'avg_latency': np.mean(latencies) if latencies else float('inf'),
                    'success_rate': self.service_successes[service] / (self.service_successes[service] + self.service_errors[service]) if (self.service_successes[service] + self.service_errors[service]) > 0 else 0,
                    'total_requests': self.service_successes[service] + self.service_errors[service]
                }
            return stats

class TranslationCache(BaseAgent):
    """Thread-safe cache for translations with TTL."""
    
    def __init__(self, port: int = 5585, max_size: int = CACHE_SIZE, ttl: int = CACHE_TTL, **kwargs):
        port = port if port else config.get("translation_cache_port", 5585)
        super().__init__(port=port, name="TranslationCache")
        self.max_size = max_size if max_size else config.get("cache_size", CACHE_SIZE)
        self.ttl = ttl if ttl else config.get("cache_ttl", CACHE_TTL)
        self.cache = {}
        self.timestamps = {}
        self.lock = threading.Lock()
        
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        
        logger.info(f"TranslationCache initialized with size {self.max_size} and TTL {self.ttl}s")
    
    def get(self, key: str) -> Optional[str]:
        """Get cached translation if not expired."""
        try:
            with self.lock:
                if key in self.cache:
                    if time.time() - self.timestamps[key] < self.ttl:
                        return self.cache[key]
                    else:
                        # Remove expired entry
                        del self.cache[key]
                        del self.timestamps[key]
                return None
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            self.report_error(f"Error getting from cache: {e}")
            return None
    
    def set(self, key: str, value: str):
        """Set translation in cache with timestamp."""
        try:
            with self.lock:
                # Remove oldest entry if cache is full
                if len(self.cache) >= self.max_size:
                    oldest_key = min(self.timestamps.items(), key=lambda x: x[1])[0]
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
                
                self.cache[key] = value
                self.timestamps[key] = time.time()
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            self.report_error(f"Error setting cache: {e}")
    
    def clear(self):
        """Clear all cached translations."""
        try:
            with self.lock:
                self.cache.clear()
                self.timestamps.clear()
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            self.report_error(f"Error clearing cache: {e}")
    
    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)
    
    def cleanup(self):
        """Cleanup resources when shutting down."""
        logger.info("Cleaning up TranslationCache")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus connection")
            except Exception as e:
                logger.error(f"Error closing error bus connection: {e}")
        
        # Call BaseAgent's cleanup method
        super().cleanup()

class AdvancedTimeoutManager(BaseAgent):
    """Manages adaptive timeouts based on text length and historical performance."""
    
    def __init__(self, port: int = 5586, **kwargs):
        port = port if port else config.get("timeout_manager_port", 5586)
        super().__init__(port=port, name="AdvancedTimeoutManager")
        self.base_timeout = config.get("base_timeout", 5000)  # 5 seconds base timeout
        self.max_timeout = config.get("max_timeout", 30000)  # 30 seconds maximum timeout
        self.timeout_history = {}
        self.lock = threading.Lock()
        self.learning_rate = config.get("learning_rate", 0.1)
        self.min_samples = config.get("min_samples", 5)
        
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        
        logger.info(f"AdvancedTimeoutManager initialized with base={self.base_timeout}ms, max={self.max_timeout}ms")
    
    def calculate_timeout(self, text: str) -> int:
        """Calculate adaptive timeout based on text length and history."""
        try:
            with self.lock:
                char_count = len(text)
                
                # Base timeout calculation
                base_timeout = self.base_timeout + min(char_count * 20, self.max_timeout - self.base_timeout)
                
                # Adjust based on history if we have enough samples
                if char_count in self.timeout_history and len(self.timeout_history[char_count]) >= self.min_samples:
                    avg_response_time = np.mean(self.timeout_history[char_count])
                    std_response_time = np.std(self.timeout_history[char_count])
                    
                    # Add buffer based on standard deviation
                    timeout = base_timeout + (std_response_time * 2)
                else:
                    timeout = base_timeout
                
                return int(min(timeout, self.max_timeout))
        except Exception as e:
            logger.error(f"Error calculating timeout: {e}")
            self.report_error(f"Error calculating timeout: {e}")
            return self.base_timeout  # Return base timeout as fallback
    
    def record_response_time(self, text: str, response_time: float):
        """Record response time for learning."""
        try:
            with self.lock:
                char_count = len(text)
                if char_count not in self.timeout_history:
                    self.timeout_history[char_count] = []
                
                self.timeout_history[char_count].append(response_time)
                
                # Keep a limited history to adapt to changing conditions
                if len(self.timeout_history[char_count]) > 50:
                    self.timeout_history[char_count].pop(0)
        except Exception as e:
            logger.error(f"Error recording response time: {e}")
            self.report_error(f"Error recording response time: {e}")
    
    def get_timeout_stats(self) -> Dict:
        """Get timeout statistics."""
        with self.lock:
            stats = {
                "base_timeout": self.base_timeout,
                "max_timeout": self.max_timeout,
                "history_count": len(self.timeout_history),
                "sample_counts": {k: len(v) for k, v in self.timeout_history.items()}
            }
            return stats
    
    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)
    
    def cleanup(self):
        """Cleanup resources when shutting down."""
        logger.info("Cleaning up AdvancedTimeoutManager")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus connection")
            except Exception as e:
                logger.error(f"Error closing error bus connection: {e}")
        
        # Call BaseAgent's cleanup method
        super().cleanup()

class PerformanceMetrics(BaseAgent):
    """Tracks performance metrics for the translation service."""
    
    def __init__(self, port: int = 5587, **kwargs):
        port = port if port else config.get("performance_metrics_port", 5587)
        super().__init__(port=port, name="PerformanceMetrics")
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.fallback_counts = defaultdict(int)
        self.response_times = []
        self.lock = threading.Lock()
        self.start_time = datetime.utcnow()
        
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        
        logger.info("PerformanceMetrics initialized")
    
    def record_request(self, success: bool, time_taken: float, fallback_type: Optional[str] = None, error: Optional[str] = None):
        """Record a translation request and its outcome."""
        try:
            with self.lock:
                self.request_count += 1
                if success:
                    self.success_count += 1
                else:
                    self.error_count += 1
                    if error:
                        self.report_error(f"Translation error: {error}")
                
                if fallback_type:
                    self.fallback_counts[fallback_type] += 1
                
                self.response_times.append(time_taken)
                # Keep only the last 1000 response times
                if len(self.response_times) > 1000:
                    self.response_times = self.response_times[-1000:]
        except Exception as e:
            logger.error(f"Error recording metrics: {e}")
            self.report_error(f"Error recording metrics: {e}")
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics."""
        with self.lock:
            total = self.success_count + self.error_count
            success_rate = self.success_count / total if total > 0 else 0
            
            avg_response_time = np.mean(self.response_times) if self.response_times else 0
            p95_response_time = np.percentile(self.response_times, 95) if len(self.response_times) >= 20 else None
            
            return {
                "request_count": self.request_count,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "fallback_counts": dict(self.fallback_counts),
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
            }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.request_count = 0
            self.success_count = 0
            self.error_count = 0
            self.fallback_counts = defaultdict(int)
            self.response_times = []
            self.start_time = datetime.utcnow()
    
    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)
    
    def cleanup(self):
        """Cleanup resources when shutting down."""
        logger.info("Cleaning up PerformanceMetrics")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus connection")
            except Exception as e:
                logger.error(f"Error closing error bus connection: {e}")
        
        # Call BaseAgent's cleanup method
        super().cleanup()

class FixedStreamingTranslation(BaseAgent):
    """Main translation agent with fallback mechanisms."""
    
    def __init__(self, port: int = 5584, **kwargs):
        port = port if port else config.get("fixed_streaming_translation_port", 5584)
        health_check_port = config.get("fixed_streaming_translation_health_port", 6584)
        super().__init__(port=port, name="FixedStreamingTranslation", health_check_port=health_check_port)
        
        # Initialize components
        self.performance_monitor = PerformanceMonitor()
        self.translation_cache = TranslationCache()
        self.timeout_manager = AdvancedTimeoutManager()
        self.performance_metrics = PerformanceMetrics()
        
        # Initialize request queue and processing thread
        self.request_queue = []
        self.queue_lock = threading.Lock()
        self.processing_thread = None
        self.running = False
        
        # PC2 connection settings
        self.pc2_ip = config.get("pc2_ip", PC2_IP)
        self.pc2_translator_port = config.get("pc2_translator_port", PC2_TRANSLATOR_PORT)
        self.pc2_translator_address = f"tcp://{self.pc2_ip}:{self.pc2_translator_port}"
        
        # Initialize Google Translate fallback
        self.google_translator = None
        if ENABLE_GOOGLE_TRANSLATE_FALLBACK:
            try:
                self.google_translator = GoogleTranslator()
                logger.info("Google Translate fallback initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Translate fallback: {e}")
                self.report_error(f"Failed to initialize Google Translate fallback: {e}")
        
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        
        # Health check thread
        self.health_thread = None
        self.last_health_update = time.time()
        
        logger.info(f"FixedStreamingTranslation initialized on port {port}")
    
    def start(self):
        """Start the translation service and its components."""
        if self.running:
            return
        
        self.running = True
        
        # Start components
        self.performance_monitor.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_text_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._send_health_update)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        logger.info("FixedStreamingTranslation service started")
    
    def shutdown(self):
        """Shutdown the translation service."""
        logger.info("Shutting down FixedStreamingTranslation service")
        self.running = False
        
        # Stop components
        self.performance_monitor.stop()
        
        # Wait for threads to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        if self.health_thread:
            self.health_thread.join(timeout=2.0)
    
    def join(self, timeout=None):
        """Wait for processing thread to finish."""
        if self.processing_thread:
            self.processing_thread.join(timeout=timeout)
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up FixedStreamingTranslation")
        
        # Shutdown service
        self.shutdown()
        
        # Clean up components
        if hasattr(self, 'performance_monitor'):
            self.performance_monitor.cleanup()
        
        if hasattr(self, 'translation_cache'):
            self.translation_cache.cleanup()
        
        if hasattr(self, 'timeout_manager'):
            self.timeout_manager.cleanup()
        
        if hasattr(self, 'performance_metrics'):
            self.performance_metrics.cleanup()
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus connection")
            except Exception as e:
                logger.error(f"Error closing error bus connection: {e}")
        
        # Call BaseAgent's cleanup method
        super().cleanup()
    
    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)
    
    def _get_health_status(self):
        """Get health status including component statuses."""
        base_status = super()._get_health_status()
        
        # Add component metrics
        try:
            translation_metrics = self.performance_metrics.get_metrics()
            queue_status = self.get_queue_status()

            # Ping PC2 translator dependency
            pc2_reachable = False
            try:
                context = None  # Using pool
                sock = context.socket(zmq.REQ)
                sock.setsockopt(zmq.LINGER, 0)
                sock.setsockopt(zmq.RCVTIMEO, 2000)
                sock.setsockopt(zmq.SNDTIMEO, 2000)
                sock.connect(self.pc2_translator_address)
                sock.send_json({"action": "health"})
                if sock.poll(2000, zmq.POLLIN):
                    resp = sock.recv_json()
                    pc2_reachable = resp.get("status") in ["ok", "healthy", "HEALTHY", "success"]
            except Exception as _:
                pc2_reachable = False
            finally:
                try:
                    sock.close()  # type: ignore
                    context.term()  # type: ignore
                except Exception:
                    pass

            base_status.update({
                "translation_metrics": translation_metrics,
                "queue_status": queue_status,
                "pc2_translator_reachable": pc2_reachable,
                "components": {
                    "performance_monitor": "running" if getattr(self.performance_monitor, '_running', False) else "stopped",
                    "cache_size": len(getattr(self.translation_cache, 'cache', {})),
                    "google_translate_available": self.google_translator is not None
                }
            })
            if not pc2_reachable:
                base_status["status"] = "degraded"
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            self.report_error(f"Error getting health status: {e}")
        
        return base_status
    
    def health_check(self):
        """Perform a health check and return status."""
        try:
            # Basic health check logic
            is_healthy = True
            
            # Check components
            if not getattr(self, 'running', False):
                is_healthy = False
            
            # Component checks
            if not getattr(self.performance_monitor, '_running', False):
                is_healthy = False
            
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "performance_monitor": getattr(self.performance_monitor, '_running', False),
                    "cache": len(getattr(self.translation_cache, 'cache', {})),
                    "google_translate": self.google_translator is not None
                },
                "queue": len(self.request_queue),
                "system_metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent
                }
            }
            
            return status_report
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": str(e)
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = FixedStreamingTranslation()
        agent.start()
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