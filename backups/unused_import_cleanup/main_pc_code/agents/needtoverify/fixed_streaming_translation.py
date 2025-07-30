from common.core.base_agent import BaseAgent
"""
Enhanced Fixed Streaming Translation Agent with Intelligent Fallback
Acts as a customer service interface for the main translator, handling translation requests
and managing communication between the main system and PC2's translation service.
Includes intelligent multi-layer fallback system and advanced performance monitoring.
"""

import zmq
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
from common.env_helpers import get_env

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).parent.parent, 'logs', str(PathManager.get_logs_dir() / "fixed_translation.log")))
    ]
)
logger = logging.getLogger("FixedStreamingTranslation")

# Configuration flags
ENABLE_FALLBACKS = True
ENABLE_GOOGLE_TRANSLATE_FALLBACK = True
ENABLE_LOCAL_PATTERN_FALLBACK = True
ENABLE_EMERGENCY_FALLBACK = True
ENABLE_CACHING = True
ENABLE_PERFORMANCE_MONITORING = True

# PC2 Translator configuration
PC2_IP = get_pc2_ip()
PC2_TRANSLATOR_PORT = 5563
PC2_TRANSLATOR_ADDRESS = f"tcp://{PC2_IP}:{PC2_TRANSLATOR_PORT}"
PC2_PERFORMANCE_PORT = 5632

# Cache configuration
CACHE_SIZE = 1000
CACHE_TTL = 3600  # 1 hour

class PerformanceMonitor(BaseAgent):
    """Monitors and tracks performance metrics for translation services."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FixedStreamingTranslation")
        self.service_latencies = defaultdict(list)
        self.service_errors = defaultdict(int)
        self.service_successes = defaultdict(int)
        self.lock = threading.Lock()
        self.max_history = 100  # Keep last 100 measurements
        self._running = False
        self._thread = None
    
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
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(f"tcp://{PC2_IP}:{PC2_PERFORMANCE_PORT}")
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        
        while self._running:
            try:
                if socket.poll(1000, zmq.POLLIN):
                    data = socket.recv_json()
                    self._update_metrics(data)
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                time.sleep(1)
        
        socket.close()
        context.term()
    
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
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FixedStreamingTranslation")
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached translation if not expired."""
        with self.lock:
            if key in self.cache:
                if time.time() - self.timestamps[key] < self.ttl:
                    return self.cache[key]
                else:
                    # Remove expired entry
                    del self.cache[key]
                    del self.timestamps[key]
            return None
    
    def set(self, key: str, value: str):
        """Set translation in cache with timestamp."""
        with self.lock:
            # Remove oldest entry if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.timestamps.items(), key=lambda x: x[1])[0]
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached translations."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

class AdvancedTimeoutManager(BaseAgent):
    """Manages adaptive timeouts based on text length and historical performance."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FixedStreamingTranslation")
        self.base_timeout = 5000  # 5 seconds base timeout
        self.max_timeout = 30000  # 30 seconds maximum timeout
        self.timeout_history = {}
        self.lock = threading.Lock()
        self.learning_rate = 0.1
        self.min_samples = 5
    
    def calculate_timeout(self, text: str) -> int:
        """Calculate adaptive timeout based on text length and history."""
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
    
    def record_response_time(self, text: str, response_time: float):
        """Record response time for learning."""
        with self.lock:
            char_count = len(text)
            if char_count not in self.timeout_history:
                self.timeout_history[char_count] = []
            
            # Keep only recent samples
            self.timeout_history[char_count] = self.timeout_history[char_count][-100:]
            self.timeout_history[char_count].append(response_time)
    
    def get_timeout_stats(self) -> Dict:
        """Get timeout statistics."""
        with self.lock:
            stats = {}
            for char_count, times in self.timeout_history.items():
                if len(times) >= self.min_samples:
                    stats[char_count] = {
                        "mean": np.mean(times),
                        "std": np.std(times),
                        "samples": len(times)
                    }
            return stats

class PerformanceMetrics(BaseAgent):
    """Tracks performance metrics for translation operations."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FixedStreamingTranslation")
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_time = 0
        self.fallback_usage = {
            "pc2": 0,
            "google": 0,
            "local": 0,
            "emergency": 0
        }
        self.error_counts = {}
        self.response_times = []
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def record_request(self, success: bool, time_taken: float, fallback_type: Optional[str] = None, error: Optional[str] = None):
        """Record a translation request."""
        with self.lock:
            self.total_requests += 1
            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                if error:
                    self.error_counts[error] = self.error_counts.get(error, 0) + 1
            
            self.total_time += time_taken
            self.response_times.append(time_taken)
            
            # Keep only recent response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            if fallback_type:
                self.fallback_usage[fallback_type] += 1
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                "total_requests": self.total_requests,
                "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
                "average_time": self.total_time / self.total_requests if self.total_requests > 0 else 0,
                "fallback_usage": self.fallback_usage.copy(),
                "error_counts": self.error_counts.copy(),
                "response_time_stats": {
                    "mean": np.mean(self.response_times) if self.response_times else 0,
                    "std": np.std(self.response_times) if self.response_times else 0,
                    "p95": np.percentile(self.response_times, 95) if self.response_times else 0
                },
                "uptime": uptime,
                "requests_per_second": self.total_requests / uptime if uptime > 0 else 0
            }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.__init__()

class FixedStreamingTranslation(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FixedStreamingTranslation")
        """Initialize the Enhanced Fixed Streaming Translation agent."""
        self.context = zmq.Context()
        
        # Main translation service connection (PC2)
        self.translation_socket = self.context.socket(zmq.REQ)
        self.translation_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.translation_socket.connect(PC2_TRANSLATOR_ADDRESS)
        
        # Health monitoring
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5569")  # Unified System Agent port
        
        # Request queue for handling multiple translation requests
        self.request_queue = []
        self.queue_lock = threading.Lock()
        
        # Initialize managers
        self.timeout_manager = AdvancedTimeoutManager()
        self.metrics = PerformanceMetrics()
        self.cache = TranslationCache() if ENABLE_CACHING else None
        self.google_translator = GoogleTranslator() if ENABLE_GOOGLE_TRANSLATE_FALLBACK else None
        self.performance_monitor = PerformanceMonitor() if ENABLE_PERFORMANCE_MONITORING else None
        
        # Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Start processing
        self._running = False
        self._thread = None
        self.start()
        
        logger.info("Enhanced Fixed Streaming Translation initialized")
    
    def start(self):
        """Start the translation process."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self.process_text_loop)
        self._thread.daemon = True
        self._thread.start()
        
        if self.performance_monitor:
            self.performance_monitor.start()
            
        logger.info("Translation process started")
    
    def shutdown(self):
        """Shutdown the translation process."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        if self.performance_monitor:
            self.performance_monitor.stop()
        self.cleanup()
        logger.info("Translation process shutdown complete")
    
    def join(self, timeout=None):
        """Wait for the processing thread to complete."""
        if self._thread:
            self._thread.join(timeout=timeout)
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'translation_socket'):
                self.translation_socket.close()
            if hasattr(self, 'health_socket'):
                self.health_socket.close()
            if hasattr(self, 'context'):
                self.context.term()
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def process_text_loop(self):
        """Main processing loop for translation requests."""
        while self._running:
            try:
                # Process queued requests
                with self.queue_lock:
                    if self.request_queue:
                        request = self.request_queue.pop(0)
                        self.thread_pool.submit(self._process_translation_request, request)
                
                # Send health update
                self._send_health_update()
                
                time.sleep(0.1)  # Prevent CPU overuse
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(1)  # Wait before retrying
    
    def _process_translation_request(self, request: Dict):
        """Process a single translation request with intelligent fallback mechanisms."""
        start_time = time.time()
        success = False
        fallback_type = None
        error = None
        
        try:
            # Check cache first if enabled
            if ENABLE_CACHING:
                cache_key = self._generate_cache_key(request)
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.info("Cache hit for translation request")
                    return {
                        "success": True,
                        "translated_text": cached_result,
                        "method": "cache"
                    }
            
            # Get best performing service
            primary_service = self.performance_monitor.get_best_service() if self.performance_monitor else 'nllb'
            logger.info(f"Selected primary service: {primary_service}")
            
            # Try primary service first
            result = self._try_pc2_translation(request, primary_service)
            if result["success"]:
                success = True
                fallback_type = primary_service
            else:
                error = result.get("error")
                # Try fallbacks if enabled
                if ENABLE_FALLBACKS:
                    # Try other services in order of performance
                    services = ['nllb', 'phi', 'google']
                    services.remove(primary_service)  # Remove primary service from fallback list
                    
                    for service in services:
                        if not success:
                            result = self._try_pc2_translation(request, service)
                            if result["success"]:
                                success = True
                                fallback_type = service
                                break
                    
                    if not success and ENABLE_LOCAL_PATTERN_FALLBACK:
                        result = self._try_local_translation(request)
                        if result["success"]:
                            success = True
                            fallback_type = "local"
                    
                    if not success and ENABLE_EMERGENCY_FALLBACK:
                        result = self._try_emergency_translation(request)
                        if result["success"]:
                            success = True
                            fallback_type = "emergency"
            
            # Record metrics
            elapsed_time = time.time() - start_time
            self.metrics.record_request(success, elapsed_time, fallback_type, error)
            
            # Cache successful result if enabled
            if success and ENABLE_CACHING:
                self.cache.set(cache_key, result["translated_text"])
            
            # Log result
            if success:
                logger.info(f"Translation successful using {'fallback: ' + fallback_type if fallback_type else 'PC2'}")
            else:
                logger.error(f"All translation methods failed: {error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing translation request: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_cache_key(self, request: Dict) -> str:
        """Generate a unique cache key for a translation request."""
        return f"{request['text']}:{request['source_language']}:{request['target_language']}"
    
    def _try_pc2_translation(self, request: Dict, service: str = 'nllb') -> Dict:
        """Try translation using PC2 Translator with specified service."""
        try:
            # Calculate timeout
            timeout = self.timeout_manager.calculate_timeout(request["text"])
            self.translation_socket.setsockopt(zmq.RCVTIMEO, timeout)
            
            # Add service specification to request
            request['service'] = service
            
            # Send request
            self.translation_socket.send_json(request)
            
            # Wait for response
            if self.translation_socket.poll(timeout, zmq.POLLIN):
                response = self.translation_socket.recv_json()
                if response.get("status") == "success":
                    return {
                        "success": True,
                        "translated_text": response.get("translated_text"),
                        "method": service
                    }
            
            return {"success": False, "error": f"{service} translation failed"}
            
        except Exception as e:
            logger.error(f"{service} translation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _try_google_translation(self, request: Dict) -> Dict:
        """Try translation using Google Translate API."""
        try:
            if not self.google_translator:
                return {"success": False, "error": "Google translator not initialized"}
            
            result = self.google_translator.translate(
                request["text"],
                src=request["source_language"],
                dest=request["target_language"]
            )
            
            return {
                "success": True,
                "translated_text": result.text,
                "method": "google"
            }
            
        except Exception as e:
            logger.error(f"Google translation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _try_local_translation(self, request: Dict) -> Dict:
        """Try translation using local pattern matching."""
        try:
            # Simple pattern-based translation (example)
            patterns = {
                "kumusta": "how are you",
                "salamat": "thank you",
                "magandang umaga": "good morning",
                "magandang hapon": "good afternoon",
                "magandang gabi": "good evening",
                "paalam": "goodbye",
                "sige": "okay",
                "hindi": "no",
                "oo": "yes",
                "paki": "please",
                "salamat po": "thank you (polite)",
                "walang anuman": "you're welcome",
                "pasensya na": "sorry",
                "ingat": "take care",
                "mabuhay": "long live"
            }
            
            text = request["text"].lower()
            for pattern, translation in patterns.items():
                if pattern in text:
                    return {
                        "success": True,
                        "translated_text": translation,
                        "method": "local"
                    }
            
            return {"success": False, "error": "No matching patterns found"}
            
        except Exception as e:
            logger.error(f"Local translation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _try_emergency_translation(self, request: Dict) -> Dict:
        """Try emergency word-by-word translation."""
        try:
            # Simple word-by-word translation (example)
            word_map = {
                "kumusta": "how",
                "ka": "are",
                "salamat": "thank",
                "po": "you",
                "magandang": "good",
                "umaga": "morning",
                "hapon": "afternoon",
                "gabi": "evening",
                "paalam": "goodbye",
                "sige": "okay",
                "hindi": "no",
                "oo": "yes",
                "paki": "please",
                "walang": "no",
                "anuman": "problem",
                "pasensya": "sorry",
                "na": "already",
                "ingat": "care",
                "mabuhay": "live"
            }
            
            words = request["text"].lower().split()
            translated_words = []
            
            for word in words:
                translated_word = word_map.get(word, word)
                translated_words.append(translated_word)
            
            return {
                "success": True,
                "translated_text": " ".join(translated_words),
                "method": "emergency"
            }
            
        except Exception as e:
            logger.error(f"Emergency translation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_health_update(self):
        """Send health status update to Unified System Agent."""
        try:
            health_data = {
                "status": "healthy",
                "queue_size": len(self.request_queue),
                "metrics": self.metrics.get_metrics(),
                "timeout_stats": self.timeout_manager.get_timeout_stats(),
                "performance_stats": self.performance_monitor.get_service_stats() if self.performance_monitor else {},
                "timestamp": time.time()
            }
            self.health_socket.send_json(health_data)
        except Exception as e:
            logger.error(f"Failed to send health update: {e}")
    
    def translate_text(self, text: str, source_lang: str = "en", target_lang: str = "tl") -> Dict:
        """Queue a text for translation."""
        try:
            request = {
                "text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "timestamp": time.time()
            }
            
            with self.queue_lock:
                self.request_queue.append(request)
            
            logger.info(f"Queued translation request: {text[:50]}...")
            return {"status": "queued", "message": "Translation request queued successfully"}
            
        except Exception as e:
            logger.error(f"Error queueing translation request: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_queue_status(self) -> Dict:
        """Get the current status of the translation queue."""
        with self.queue_lock:
            return {
                "queue_size": len(self.request_queue),
                "status": "running" if self._running else "stopped",
                "metrics": self.metrics.get_metrics(),
                "timeout_stats": self.timeout_manager.get_timeout_stats(),
                "performance_stats": self.performance_monitor.get_service_stats() if self.performance_monitor else {}
            }

if __name__ == "__main__":
    try:
        translator = FixedStreamingTranslation()
        logger.info("Enhanced Fixed Streaming Translation service started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Enhanced Fixed Streaming Translation service...")
        translator.shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if 'translator' in locals():
            translator.shutdown() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise