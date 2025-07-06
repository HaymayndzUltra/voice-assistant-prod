"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

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
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Parse agent arguments at module level with canonical import
config = load_config()

# Optional fastText language ID
try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
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
PC2_IP = config.get("host", 'localhost')  # Temporarily changed for local testing
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
        self.service_latencies = 

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
defaultdict(list)
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















    
    def shutdown(self):

    
            """Shutdown the coordinator."""

    
            self._running = False

    
            if self._thread:

    
                self._thread.join(timeout=5.0)

    
            if self.performance_monitor:

    
                self.performance_monitor.stop()

    
            self.cleanup()

    
            logger.info("Shutdown complete")

    
    def process_loop(self):

    
            """Main processing loop."""

    
            while self._running:

    
                try:

    
                    # Check for input from Whisper ASR

    
                    if self.input_socket.poll(1000, zmq.POLLIN):

    
                        try:

    
                            # First try to receive as string (common format from ASR)

    
                            message_str = self.input_socket.recv_string()
                        

    
                            # Check if it's a JSON error message

    
                            if message_str.startswith('{"status":"error"'):

    
                                error_data = json.loads(message_str)

    
                                if error_data.get("status") == "error":

    
                                    # Log the received error

    
                                    logger.error(f"Received error from {error_data.get('source_agent', 'unknown')}: {error_data.get('message')}")

    
                                    # Handle specific error types if needed

    
                                    if error_data.get("error_type") in ["TranscriptionError", "ModelInferenceError"]:

    
                                        logger.error(f"Upstream transcription error: {error_data.get('message')}")

    
                                        # Could implement specific recovery strategies here if needed

    
                                    continue
                        

    
                            # If not an error, check if it's a transcription message

    
                            if message_str.startswith("TRANSCRIPTION:"):

    
                                # Extract the JSON part

    
                                json_str = message_str[14:].strip()

    
                                try:

    
                                    data = json.loads(json_str)

    
                                    self.thread_pool.submit(self._process_text, data)

    
                                except json.JSONDecodeError:

    
                                    logger.error(f"Failed to parse transcription JSON: {json_str[:100]}...")

    
                            else:

    
                                # Try to parse as direct JSON

    
                                try:

    
                                    data = json.loads(message_str)

    
                                    self.thread_pool.submit(self._process_text, data)

    
                                except json.JSONDecodeError:

    
                                    logger.error(f"Received unrecognized message format: {message_str[:100]}...")

    
                        except zmq.Again:

    
                            pass  # No message available

    
                        except Exception as e:

    
                            logger.error(f"Error processing incoming message: {str(e)}")

    
                            # Log but continue processing
                

    
                    # Send health update

    
                    self._send_health_update()
                

    
                    time.sleep(0.1)  # Prevent CPU overuse
                

    
                except Exception as e:

    
                    logger.error(f"Error in processing loop: {e}")

    
                    time.sleep(1)

    
    def join(self, timeout=None):

    
            """Wait for the processing thread to complete."""

    
            if self._thread:

    
                self._thread.join(timeout=timeout)

    
    def get_status(self) -> Dict:

    
            """Get the current status of the coordinator."""

    
            return {

    
                "status": "running" if self._running else "stopped",

    
                "metrics": self.metrics.get_metrics(),

    
                "timeout_stats": self.timeout_manager.get_timeout_stats(),

    
                "performance_stats": self.performance_monitor.get_service_stats() if self.performance_monitor else {}

    
            }

    
    def _try_pc2_translation(self, text: str, source_lang: str, target_lang: str, service: str = 'nllb') -> Dict:

    
            """Try translation using PC2 Translator with specified service."""

    
            try:

    
                # Calculate timeout

    
                timeout = self.timeout_manager.calculate_timeout(text)

    
                self.translation_socket.setsockopt(zmq.RCVTIMEO, timeout)
            

    
                # Prepare request

    
                request = {

    
                    "text": text,

    
                    "source_language": source_lang,

    
                    "target_language": target_lang,

    
                    "service": service,

    
                    "timestamp": time.time()

    
                }
            

    
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

    
    def _try_local_translation(self, text: str, source_lang: str, target_lang: str) -> Dict:

    
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
            

    
                text_lower = text.lower()

    
                for pattern, translation in patterns.items():

    
                    if pattern in text_lower:

    
                        return {

    
                            "success": True,

    
                            "translated_text": translation,

    
                            "method": "local"

    
                        }
            

    
                return {"success": False, "error": "No matching patterns found"}
            

    
            except Exception as e:

    
                logger.error(f"Local translation error: {e}")

    
                return {"success": False, "error": str(e)}

    
    def _try_google_translation(self, text: str, source_lang: str, target_lang: str) -> Dict:

    
            """Try translation using Google Translate API."""

    
            try:

    
                if not self.google_translator:

    
                    return {"success": False, "error": "Google translator not initialized"}
            

    
                result = self.google_translator.translate(

    
                    text,

    
                    src=source_lang,

    
                    dest=target_lang

    
                )
            

    
                return {

    
                    "success": True,

    
                    "translated_text": result.text,

    
                    "method": "google"

    
                }
            

    
            except Exception as e:

    
                logger.error(f"Google translation error: {e}")

    
                return {"success": False, "error": str(e)}

    
    def _try_emergency_translation(self, text: str, source_lang: str, target_lang: str) -> Dict:

    
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
            

    
                words = text.lower().split()

    
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

    
    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> Dict:

    
            """Translate text with intelligent fallback mechanisms."""

    
            start_time = time.time()

    
            success = False

    
            fallback_type = None

    
            error = None
        

    
            try:

    
                # Check cache first if enabled

    
                if ENABLE_CACHING:

    
                    cache_key = self._generate_cache_key(text, source_lang, target_lang)

    
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

    
                result = self._try_pc2_translation(text, source_lang, target_lang, primary_service)

    
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

    
                                result = self._try_pc2_translation(text, source_lang, target_lang, service)

    
                                if result["success"]:

    
                                    success = True

    
                                    fallback_type = service

    
                                    break
                    

    
                        if not success and ENABLE_LOCAL_PATTERN_FALLBACK:

    
                            result = self._try_local_translation(text, source_lang, target_lang)

    
                            if result["success"]:

    
                                success = True

    
                                fallback_type = "local"
                    

    
                        if not success and ENABLE_EMERGENCY_FALLBACK:

    
                            result = self._try_emergency_translation(text, source_lang, target_lang)

    
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

    
    def _send_health_update(self):

    
            """Send health status update to Unified System Agent."""

    
            try:

    
                health_data = {

    
                    "status": "healthy",

    
                    "metrics": self.metrics.get_metrics(),

    
                    "timeout_stats": self.timeout_manager.get_timeout_stats(),

    
                    "performance_stats": self.performance_monitor.get_service_stats() if self.performance_monitor else {},

    
                    "timestamp": time.time()

    
                }

    
                self.health_socket.send_json(health_data)

    
            except Exception as e:

    
                logger.error(f"Failed to send health update: {e}")

    
    def _process_text(self, data: Dict):

    
            """Process incoming text with language detection and translation."""

    
            try:

    
                text = data.get("transcript") 

    
                if text is None:

    
                    text = data.get("text") 

    
                if not text:

    
                    return
            

    
                # Detect language

    
                detected_lang = self._detect_language(text)

    
                logger.info(f"Detected language: {detected_lang}")
            

    
                # Determine if translation is needed

    
                if detected_lang != 'en':

    
                    # Translation needed

    
                    translation_result = self._translate_text(text, detected_lang, 'en')

    
                    if translation_result["success"]:

    
                        # Send translated text to TTS

    
                        self.output_socket.send_json({

    
                            "text": translation_result["translated_text"],

    
                            "language": "en",

    
                            "timestamp": time.time()

    
                        })

    
                    else:

    
                        logger.error(f"Translation failed: {translation_result.get('error')}")

    
                else:

    
                    # No translation needed, forward to TTS

    
                    self.output_socket.send_json({

    
                        "text": text,

    
                        "language": "en",

    
                        "timestamp": time.time()

    
                    })
            

    
            except Exception as e:

    
                logger.error(f"Error processing text: {e}")

    
    def _is_taglish_candidate(self, text: str, langdetect_code: str, langdetect_confidence: float) -> bool:

    
            """Check if text is a candidate for more specific Taglish detection."""

    
            text_lower = text.lower()

    
            words = text_lower.split()

    
            word_count = len(words)


    
            if langdetect_code in ['en', 'tl']:

    
                # If langdetect is somewhat confident it's en or tl, it's a candidate

    
                if langdetect_confidence > 0.5: 

    
                    return True

    
                # If low confidence, but contains Tagalog words, it's a candidate

    
                if any(word in TAGALOG_WORDS_SET for word in words):

    
                    return True

    
            # If langdetect identified other languages but Tagalog words are present

    
            elif any(word in TAGALOG_WORDS_SET for word in words):

    
                return True

    
            return False

    
    def _generate_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:

    
            """Generate a unique cache key for a translation request."""

    
            return f"{text}:{source_lang}:{target_lang}"

    
    def _detect_language(self, text: str) -> str:

    
            """Detect the language of the input text, with refined Taglish/Tagalog detection."""

    
            if not text.strip():

    
                logger.info("Empty text received for language detection, defaulting to 'unknown'.")

    
                return 'unknown'


    
            detected_lang_code = 'en' # Default

    
            text_lower = text.lower()


    
            # Step 1: Initial detection with langdetect

    
            try:

    
                langdetect_results = langdetect.detect_langs(text_lower)

    
                primary_lang_obj = langdetect_results[0]

    
                ld_lang_code = primary_lang_obj.lang

    
                ld_confidence = primary_lang_obj.prob

    
                logger.info(f"langdetect: Initial detection '{ld_lang_code}' (conf: {ld_confidence:.2f}) for: '{text[:50]}...' ")

    
                detected_lang_code = ld_lang_code

    
            except LangDetectException:

    
                logger.warning(f"langdetect failed for: '{text[:50]}...'. Proceeding with other methods.")

    
                # If langdetect fails, we rely on subsequent methods, especially for short texts

    
                ld_lang_code = 'unknown'

    
                ld_confidence = 0.0

    
            except Exception as e:

    
                logger.error(f"Unexpected error in langdetect for '{text[:50]}...': {e}")

    
                ld_lang_code = 'unknown'

    
                ld_confidence = 0.0


    
            # Step 2: Refine with fastText if available and it's a Taglish candidate

    
            is_candidate_for_refinement = self._is_taglish_candidate(text_lower, ld_lang_code, ld_confidence)
        

    
            if self.fasttext_model and is_candidate_for_refinement:

    
                try:

    
                    # fastText expects a single line of text

    
                    predictions = self.fasttext_model.predict(text_lower.replace('\n', ' '), k=1)

    
                    ft_lang_code = predictions[0][0].replace('__label__', '')

    
                    ft_confidence = predictions[1][0]

    
                    logger.info(f"fastText: Detected '{ft_lang_code}' (conf: {ft_confidence:.2f})")

    
                    # Trust fastText more for 'tl' and 'en' if confidence is high, or if it identifies 'taglish'

    
                    if ft_lang_code in ['en', 'tl', 'taglish'] and ft_confidence > 0.6:

    
                        detected_lang_code = ft_lang_code

    
                    elif ft_lang_code == 'tl' and detected_lang_code == 'en' and ft_confidence > 0.4: # Re-evaluate if langdetect said en but fastText says tl

    
                        detected_lang_code = 'tl'

    
                except Exception as e:

    
                    logger.warning(f"fastText prediction failed: {e}") 


    
            # Step 3: Further refine with TagaBERTa if available and still ambiguous or Tagalog/Taglish suspected

    
            if self.tagabert_available and self.tagabert_socket and is_candidate_for_refinement and detected_lang_code in ['en', 'tl', 'taglish', 'unknown']:

    
                try:

    
                    request_payload = {"action": "analyze_language", "text": text_lower}

    
                    self.tagabert_socket.send_json(request_payload)

    
                    if self.tagabert_socket.poll(1000, zmq.POLLIN): # Wait 1 sec for TagaBERTa

    
                        response = self.tagabert_socket.recv_json()

    
                        tb_lang_code = response.get('language')

    
                        tb_confidence = response.get('confidence', 0.0)

    
                        logger.info(f"TagaBERTa: Detected '{tb_lang_code}' (conf: {tb_confidence:.2f})")

    
                        if tb_lang_code and tb_confidence > 0.7: # Trust TagaBERTa if highly confident

    
                            detected_lang_code = tb_lang_code

    
                    else:

    
                        logger.warning("TagaBERTa service timed out during language analysis.")

    
                        # Re-establish connection for next time if timeout

    
                        self.tagabert_socket.close()

    
                        self.tagabert_socket = self.context.socket(zmq.REQ)

    
                        self.tagabert_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)

    
                        self.tagabert_socket.setsockopt(zmq.RCVTIMEO, 1000)

    
                        self.tagabert_socket.setsockopt(zmq.LINGER, 0)

    
                        self.tagabert_socket.connect(TAGABERT_SERVICE_ADDRESS)

    
                except Exception as e:

    
                    logger.error(f"Error communicating with TagaBERTa service: {e}")

    
                    # Attempt to gracefully handle socket error

    
                    try:

    
                        if self.tagabert_socket:

    
                            self.tagabert_socket.close()

    
                        self.tagabert_socket = self.context.socket(zmq.REQ)

    
                        self.tagabert_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)

    
                        self.tagabert_socket.setsockopt(zmq.RCVTIMEO, 1000)

    
                        self.tagabert_socket.setsockopt(zmq.LINGER, 0)

    
                        self.tagabert_socket.connect(TAGABERT_SERVICE_ADDRESS)

    
                    except Exception as se_conn:

    
                        logger.error(f"Failed to re-establish TagaBERTa connection: {se_conn}")

    
                        self.tagabert_available = False # Mark as unavailable if re-connection fails

    
                        self.tagabert_socket = None


    
            # Step 4: Final check using lexicon for 'tl' or 'taglish'

    
            # If detected_lang_code is still 'en' but contains many Tagalog words, consider it 'taglish'

    
            if detected_lang_code == 'en':

    
                words = text_lower.split()

    
                tagalog_word_count = sum(1 for word in words if word in TAGALOG_WORDS_SET or word in self.tagalog_lexicon)

    
                if len(words) > 0 and (tagalog_word_count / len(words)) > 0.3: # If more than 30% words are Tagalog

    
                    logger.info(f"Lexicon override: Detected 'en' but found {tagalog_word_count}/{len(words)} Tagalog words. Classifying as 'taglish'.")

    
                    detected_lang_code = 'taglish'

    
                elif len(words) <= 5 and tagalog_word_count >=1 and (tagalog_word_count / len(words)) >= 0.2: # For very short phrases, 1 or 2 tagalog words might make it taglish

    
                     logger.info(f"Lexicon override (short phrase): Detected 'en' but found {tagalog_word_count}/{len(words)} Tagalog words. Classifying as 'taglish'.")

    
                     detected_lang_code = 'taglish'


    
            # Normalize 'fil' (Filipino) or 'taglish' to 'tl' if that's what downstream services expect for Tagalog

    
            if detected_lang_code in ['fil', 'taglish']:

    
                logger.info(f"Normalizing '{detected_lang_code}' to 'tl' for translation purposes.")

    
                detected_lang_code = 'tl'
        

    
            # Ensure we always return a valid code, default to 'en' if all else fails and it's unknown

    
            if detected_lang_code == 'unknown' or not detected_lang_code:

    
                logger.info("Language detection inconclusive, defaulting to 'en'.")

    
                detected_lang_code = 'en'


    
            logger.info(f"Final detected language: '{detected_lang_code}' for text: '{text[:50]}...' ")

    
            return detected_lang_code

    def __init__(self):
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

class LanguageAndTranslationCoordinator(
    """
    LanguageAndTranslationCoordinator:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """BaseAgent):
    def __init__(self):
        """Initialize the Language and Translation Coordinator agent."""
        # Set required properties before calling super().__init__
        self.name = "LanguageAndTranslationCoordinator"
        self.port = int(config.get("port", 5710))
        self.start_time = time.time()
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=self.name, port=self.port)
        
        # Get additional configuration from agent args
        self.bind_address = config.get("bind_address", '<BIND_ADDR>')
        self.zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Initialize components as regular classes, not BaseAgent subclasses
        self.performance_monitor = PerformanceMonitor() if ENABLE_PERFORMANCE_MONITORING else None
        self.translation_cache = TranslationCache() if ENABLE_CACHING else None
        self.timeout_manager = AdvancedTimeoutManager()
        self.metrics = PerformanceMetrics()
        
        # Initialize state
        self._running = False
        self._thread = None
        
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
        
        # Initialize and verify TagaBERTa service connection
        self.tagabert_socket = None
        try:
            self.tagabert_socket = self.zmq_context.socket(zmq.REQ)
            self.tagabert_socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
            self.tagabert_socket.connect(TAGABERT_SERVICE_ADDRESS)
            logger.info(f"Connected to TagaBERTa service at {TAGABERT_SERVICE_ADDRESS}")
            
            # Test connection
            self.tagabert_socket.send_json({
                "action": "ping", 
                "timestamp": datetime.now().isoformat()
            })
            response = self.tagabert_socket.recv_json()
            
            if response.get("status") == "ok":
                logger.info("TagaBERTa service is responsive")
            else:
                logger.warning(f"TagaBERTa service responded with non-ok status: {response}")
        except Exception as e:
            logger.warning(f"Failed to initialize TagaBERTa service connection: {e}")
            if self.tagabert_socket:
                self.tagabert_socket.close()
                self.tagabert_socket = None
        
        # Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Start performance monitoring
        if self.performance_monitor:
            self.performance_monitor.start()
        
        # Start processing
        self.start()
            
        logger.info("Language and Translation Coordinator initialized")
        
    def _get_health_status(self):
        """Get the current health status of the agent.
        
        This method overrides the BaseAgent._get_health_status method to add
        agent-specific health information.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information
        """
        # Get the base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health metrics
        try:
            # Check if running
            is_running = getattr(self, '_running', False)
            
            # Check ZMQ socket health
            zmq_healthy = hasattr(self, 'sub_socket') and self.sub_socket is not None and \
                          hasattr(self, 'pub_socket') and self.pub_socket is not None
            
            # Get metrics
            metrics = self.metrics.get_metrics() if hasattr(self, 'metrics') else {}
            
            # Add metrics to base status
            base_status.update({
                "agent_specific_metrics": {
                    "running": is_running,
                    "zmq_socket_healthy": zmq_healthy,
                    "performance_metrics": metrics,
                    "fasttext_model_loaded": self.fasttext_model is not None,
                    "google_translator_available": self.google_translator is not None,
                    "tagabert_socket_available": self.tagabert_socket is not None
                }
            })
            
        except Exception as e:
            logger.error(f"Error collecting health metrics: {e}")
            base_status.update({"health_metrics_error": str(e)})
        
        return base_status

# Add standardized __main__ block
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = LanguageAndTranslationCoordinator()
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