"""
Language and Translation Coordinator Agent
Combines language analysis and translation functionality into a single, efficient agent.
Handles streaming text input, language detection, and intelligent translation with fallback mechanisms.
"""

import zmq
import json
import logging
import time
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import os
import sys
import re
from googletrans import Translator as GoogleTranslator
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import langdetect
from langdetect import DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import psutil

# Add project root to the Python path to allow for absolute imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import with canonical paths
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_parser import parse_agent_args

# Parse agent arguments at module level with canonical import
_agent_args = parse_agent_args()

# Optional fastText language ID
try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(PROJECT_ROOT, 'logs', 'language_translation_coordinator.log'))
    ]
)
logger = logging.getLogger("LanguageTranslationCoordinator")

# Configuration flags
ENABLE_FALLBACKS = True
ENABLE_GOOGLE_TRANSLATE_FALLBACK = True
ENABLE_LOCAL_PATTERN_FALLBACK = True
ENABLE_EMERGENCY_FALLBACK = True
ENABLE_CACHING = True
ENABLE_PERFORMANCE_MONITORING = True

# Network configuration
PC2_IP = getattr(_agent_args, 'host', 'localhost')  # Temporarily changed for local testing
PC2_TRANSLATOR_PORT = 5563
PC2_TRANSLATOR_ADDRESS = f"tcp://{PC2_IP}:{PC2_TRANSLATOR_PORT}"
PC2_PERFORMANCE_PORT = 5632  # Performance monitoring port (as configured in startup_config.yaml)
WHISPER_ASR_PORT = 6580  # Port for Whisper ASR (as configured in startup_config.yaml)
TTS_CONNECTOR_PORT = 5582  # Port for TTS connector (as configured in startup_config.yaml)
TAGABERT_SERVICE_PORT = 6010  # Port for TagaBERTa service
TAGABERT_SERVICE_ADDRESS = f"tcp://{PC2_IP}:{TAGABERT_SERVICE_PORT}"

# Cache configuration
CACHE_SIZE = 1000
CACHE_TTL = 3600  # 1 hour

# Language detection configuration
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'tl': 'Tagalog',
    'fil': 'Filipino',
    'ceb': 'Cebuano',
    'ilo': 'Ilocano',
    'hil': 'Hiligaynon',
    'war': 'Waray',
    'bik': 'Bikol',
    'pam': 'Kapampangan',
    'pag': 'Pangasinan'
}

# Expanded Tagalog words list, similar to streaming_language_analyzer
TAGALOG_WORDS_SET = {
    'ako', 'ikaw', 'siya', 'kami', 'tayo', 'kayo', 'sila',
    'ang', 'ng', 'sa', 'na', 'at', 'ay', 'mga',
    'hindi', 'oo', 'puwede', 'pwede', 'gusto', 'ayaw',
    'ito', 'iyan', 'iyon', 'dito', 'diyan', 'doon',
    'sino', 'ano', 'saan', 'kailan', 'bakit', 'paano',
    'mahal', 'salamat', 'pasensya', 'maganda', 'mabuti',
    'naman', 'lang', 'po', 'ba', 'raw', 'daw', 'muna',
    'kung', 'kapag', 'dahil', 'kasi', 'para', 'upang',
    'walang', 'maraming', 'konting', 'lahat',
    'umaga', 'tanghali', 'hapon', 'gabi',
    'ngayon', 'kanina', 'bukas', 'kahapon',
    'alam', 'kita', 'natin', 'niya', 'nila',
    # Added from streaming_language_analyzer common short words
    'buksan', 'isara', 'patay', 'bukas', 'tama', 'sige', 'tigil',
    'tuloy', 'ulit', 'bilis', 'bagal', 'hinto', 'lakasan', 'hina',
    'patugtog', 'kanta', 'tugtog', 'kwento', 'usap', 'tignan', 'tingnan'
}

# FastText model path
FASTTEXT_MODEL_PATH = "resources/taglish_lid.ftz"

# Tagalog lexicon path
TAGALOG_LEXICON_PATH = "resources/tagalog_lexicon.txt"

class PerformanceMonitor:
    """Monitors and tracks performance metrics for translation services."""
    
    def __init__(self, **kwargs):
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

class TranslationCache:
    """Cache for translation results."""
    
    def __init__(self, **kwargs):
        self.cache = {}
        self.timestamps = {}
        self.max_size = CACHE_SIZE
        self.ttl = CACHE_TTL
    
    def get(self, key: str) -> Optional[str]:
        """Get a cached translation result."""
        if key not in self.cache:
            return None
            
        # Check if entry has expired
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
            
        return self.cache[key]
    
    def set(self, key: str, value: str):
        """Store a translation result in the cache."""
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
            
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self):
        """Clear the cache."""
        self.cache = {}
        self.timestamps = {}

class AdvancedTimeoutManager:
    """Manages dynamic timeouts for translation requests."""
    
    def __init__(self, **kwargs):
        self.timeouts = {}
        self.response_times = defaultdict(list)
        self.max_history = 20
        self.default_timeout = 5000  # 5 seconds
        self.max_timeout = 15000  # 15 seconds
    
    def calculate_timeout(self, text: str) -> int:
        """Calculate an appropriate timeout for a translation request."""
        # Simple heuristic: longer text needs more time
        text_length = len(text)
        
        if text_length < 10:
            base_timeout = 2000  # 2 seconds for very short text
        elif text_length < 50:
            base_timeout = 5000  # 5 seconds for short text
        elif text_length < 200:
            base_timeout = 8000  # 8 seconds for medium text
        else:
            base_timeout = 12000  # 12 seconds for long text
            
        # Adjust based on historical response times if available
        key = self._get_length_bucket(text_length)
        if key in self.timeouts:
            return min(int(self.timeouts[key] * 1.5), self.max_timeout)  # Add 50% margin
            
        return base_timeout
    
    def record_response_time(self, text: str, response_time: float):
        """Record the response time for a translation request."""
        key = self._get_length_bucket(len(text))
        
        self.response_times[key].append(response_time)
        if len(self.response_times[key]) > self.max_history:
            self.response_times[key].pop(0)
            
        # Update timeout based on 95th percentile of response times
        if self.response_times[key]:
            self.timeouts[key] = np.percentile(self.response_times[key], 95)
    
    def _get_length_bucket(self, length: int) -> str:
        """Get a bucket key for text length."""
        if length < 10:
            return "tiny"
        elif length < 50:
            return "small"
        elif length < 200:
            return "medium"
        else:
            return "large"
    
    def get_timeout_stats(self) -> Dict:
        """Get timeout statistics."""
        return {
            "timeouts": dict(self.timeouts),
            "response_times": {k: list(v) for k, v in self.response_times.items()}
        }

class PerformanceMetrics:
    """Tracks performance metrics for the translation service."""
    
    def __init__(self, **kwargs):
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.fallback_counts = defaultdict(int)
        self.total_time = 0
        self.min_time = float('inf')
        self.max_time = 0
        self.errors = defaultdict(int)
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def record_request(self, success: bool, time_taken: float, fallback_type: Optional[str] = None, error: Optional[str] = None):
        """Record metrics for a translation request."""
        with self.lock:
            self.request_count += 1
            
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
                
            if fallback_type:
                self.fallback_counts[fallback_type] += 1
                
            if error:
                self.errors[error] += 1
                
            self.total_time += time_taken
            self.min_time = min(self.min_time, time_taken)
            self.max_time = max(self.max_time, time_taken)
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics."""
        with self.lock:
            uptime = time.time() - self.start_time
            
            return {
                "request_count": self.request_count,
                "success_rate": self.success_count / self.request_count if self.request_count > 0 else 0,
                "avg_time": self.total_time / self.request_count if self.request_count > 0 else 0,
                "min_time": self.min_time if self.min_time != float('inf') else 0,
                "max_time": self.max_time,
                "requests_per_second": self.request_count / uptime if uptime > 0 else 0,
                "fallback_counts": dict(self.fallback_counts),
                "error_counts": dict(self.errors),
                "uptime_seconds": uptime
            }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.__init__()

class LanguageAndTranslationCoordinator(BaseAgent):
    def __init__(self):
        """Initialize the Language and Translation Coordinator agent."""
        # Call BaseAgent's __init__ first with proper arguments
        super().__init__(name="LanguageAndTranslationCoordinator")
        
        # Get configuration from agent args
        self.port = int(getattr(_agent_args, 'port', 5710))
        self.bind_address = getattr(_agent_args, 'bind_address', '<BIND_ADDR>')
        self.zmq_timeout = int(getattr(_agent_args, 'zmq_request_timeout', 5000))
        
        # Initialize components as regular classes, not BaseAgent subclasses
        self.performance_monitor = PerformanceMonitor()
        self.translation_cache = TranslationCache()
        self.timeout_manager = AdvancedTimeoutManager()
        self.metrics = PerformanceMetrics()
        
        # Initialize state
        self._running = False
        self._thread = None
        self.start_time = time.time()
        
        # Initialize ZMQ context and sockets
        self.zmq_context = zmq.Context()
        self._init_sockets()
        
        # Initialize language detection
        DetectorFactory.seed = 0  # For reproducible results
        
        # Load FastText model if available
        self.fasttext_model = None
        if FASTTEXT_AVAILABLE and os.path.exists(FASTTEXT_MODEL_PATH):
            try:
                self.fasttext_model = fasttext.load_model(FASTTEXT_MODEL_PATH)
                logger.info(f"Loaded FastText model from {FASTTEXT_MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to load FastText model: {e}")
        
        # Load Tagalog lexicon if available
        self.tagalog_lexicon = set(TAGALOG_WORDS_SET)  # Start with the built-in set
        if os.path.exists(TAGALOG_LEXICON_PATH):
            try:
                with open(TAGALOG_LEXICON_PATH, 'r', encoding='utf-8') as f:
                    self.tagalog_lexicon.update(line.strip().lower() for line in f if line.strip())
                logger.info(f"Loaded {len(self.tagalog_lexicon)} Tagalog words from lexicon")
            except Exception as e:
                logger.error(f"Failed to load Tagalog lexicon: {e}")
        
        # Initialize Google Translate
        self.google_translator = None
        if ENABLE_GOOGLE_TRANSLATE_FALLBACK:
            try:
                self.google_translator = GoogleTranslator()
                logger.info("Initialized Google Translator")
            except Exception as e:
                logger.error(f"Failed to initialize Google Translator: {e}")
        
        # Start performance monitoring
        if ENABLE_PERFORMANCE_MONITORING:
            self.performance_monitor.start()
            
        logger.info("Language and Translation Coordinator initialized")

    def _get_health_status(self):
        """Get the current health status of the agent.
        
        Returns:
            dict: A dictionary containing health status information
        """
        # Basic health check logic
        is_healthy = self._running
        
        # Check ZMQ socket health
        zmq_healthy = hasattr(self, 'sub_socket') and self.sub_socket is not None and \
                      hasattr(self, 'pub_socket') and self.pub_socket is not None
        if not zmq_healthy:
            is_healthy = False
        
        # Get metrics
        metrics = self.metrics.get_metrics() if hasattr(self, 'metrics') else {}
        
        status_report = {
            "status": "healthy" if is_healthy else "unhealthy",
            "agent_name": "LanguageAndTranslationCoordinator",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
            "details": {
                "running": getattr(self, '_running', False),
                "zmq_socket_healthy": zmq_healthy,
                "performance_metrics": metrics,
                "fasttext_model_loaded": self.fasttext_model is not None,
                "google_translator_available": self.google_translator is not None
            }
        }
        
        return status_report

# Add standardized __main__ block
if __name__ == "__main__":
    agent = None
    try:
        agent = LanguageAndTranslationCoordinator()
        agent.run()
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()