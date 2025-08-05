"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Streaming Language Analyzer Module
Analyzes real-time transcriptions for language (English, Tagalog, Taglish)
"""

import pickle
import logging
from common.utils.log_setup import configure_logging
import re
import time
import json
import threading
import os
from collections import deque
from datetime import datetime
from pathlib import Path
import socket
from typing import Dict, Any

from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from main_pc_code.utils.service_discovery_client import register_service, get_service_address
from main_pc_code.utils.env_loader import get_env
from main_pc_code.utils.network_utils import get_zmq_connection_string
# from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
from main_pc_code.utils import model_client
from common.env_helpers import get_env
from common.utils.path_manager import PathManager

# Parse command line arguments
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Optional fastText language ID
try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    FASTTEXT_AVAILABLE = False

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingLanguageAnalyzer")

# Port configuration from args or defaults
ZMQ_SUB_PORT = int(config.get("streaming_speech_recognition_port", 5576) or 5576)
ZMQ_PUB_PORT = int(config.get("port", 5577) or 5577)
ZMQ_HEALTH_PORT = int(config.get("health_port", 5597) or 5597)
ZMQ_REQUEST_TIMEOUT = int(config.get("zmq_request_timeout", 5000) or 5000)

# Get bind address from environment variables with default to a safe value for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# Secure ZMQ configuration
SECURE_ZMQ = os.environ.get("SECURE_ZMQ", "0") == "1"

# TagaBERTa service configuration - use service discovery
TAGABERT_SERVICE_NAME = "TagaBERTaService"

TAGALOG_WORDS = {
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
}

# Extend lexicon from external file if available
LEXICON_PATH = Path("resources/tagalog_lexicon.txt")
if LEXICON_PATH.exists():
    try:
        extra_words = {w.strip() for w in LEXICON_PATH.read_text(encoding="utf-8").splitlines() if w.strip()}
        TAGALOG_WORDS.update(extra_words)
        logging.getLogger("StreamingLanguageAnalyzer").info(f"Loaded {len(extra_words)} extra Tagalog words from {LEXICON_PATH}")
    except Exception as e:
        logging.getLogger("StreamingLanguageAnalyzer").warning(f"Could not load external lexicon {LEXICON_PATH}: {e}")

def find_available_port(start_port: int, end_port: int, max_attempts: int = 10) -> int:
    """Find an available port within the specified range"""
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find available port in range {start_port}-{end_port}")

class StreamingLanguageAnalyzer(BaseAgent):
    """Streaming Language Analyzer Agent for real-time language detection Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self):
        """Initialize the language analyzer agent"""
        # Standard BaseAgent initialization at the beginning
        super().__init__(
            name='StreamingLanguageAnalyzer',
            port=int(config.get("port", 5577) or 5577)
        )
        
        # Initialize state
        self.start_time = time.time()
        self.processed_streams_count = 0
        self.last_stream_time = 'N/A'
        
        # Initialize metrics tracking
        self.metrics_lock = threading.RLock()
        self.stats = {
            "total_requests": 0,
            "english_count": 0,
            "tagalog_count": 0,
            "taglish_count": 0,
            "processing_times": []
        }
        
        # Use provided port or 


        self.pub_port = self.port if self.port else ZMQ_PUB_PORT
        logger.info(f"Using port {self.pub_port} for publishing")
        
        # Setup sockets
        self.sub_socket = self.context.socket(zmq.SUB)
        if SECURE_ZMQ:
            self.sub_socket = configure_secure_client(self.sub_socket)
            
        # Try to get the speech recognition address from service discovery
        stt_address = get_service_address("StreamingSpeechRecognition")
        if not stt_address:
            # Fall back to configured port
            stt_address = get_zmq_connection_string(ZMQ_SUB_PORT, "localhost")
            
        self.sub_socket.connect(stt_address)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to speech recognition at {stt_address}")
        
        self.pub_socket = self.context.socket(zmq.PUB)
        if SECURE_ZMQ:
            self.pub_socket = configure_secure_server(self.pub_socket)
            
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{BIND_ADDRESS}:{self.pub_port}"
        try:
            self.pub_socket.bind(bind_address)
            logger.info(f"Successfully bound to {bind_address}")
        except Exception as e:
            logger.error(f"Failed to bind to {bind_address}: {e}")
            raise
        
        # Register with service discovery
        self._register_service(self.pub_port)
        
        # Setup health reporting
        self.health_socket = self.context.socket(zmq.PUB)
        if SECURE_ZMQ:
            self.health_socket = configure_secure_client(self.health_socket)
            
        # Try to get the health system address from service discovery
        health_address = get_service_address("HealthMonitor")
        if not health_address:
            # Fall back to configured port
            health_address = get_zmq_connection_string(ZMQ_HEALTH_PORT, "localhost")
            
        try:
            self.health_socket.connect(health_address)
            logger.info(f"Connected to health dashboard at {health_address}")
        except Exception as e:
            logger.warning(f"Could not connect to health dashboard: {e}")
        
        # Setup TagaBERTa connection using service discovery
        self.tagabert_socket = None
        self.tagabert_available = False
        self._connect_to_tagabert()
        
        # Setup TranslationService connection
        self.translation_socket = None
        self.translation_available = False
        self._connect_to_translation_service()
        
        # Optional fastText model
        self.fasttext_available = False
        if FASTTEXT_AVAILABLE:
            try:
                lid_model_path = "resources/taglish_lid.ftz"
                if Path(lid_model_path).exists():
                    self.fasttext_model = fasttext.load_model(lid_model_path)
                    self.fasttext_available = True
                    logger.info(f"Loaded fastText LID model from {lid_model_path}")
            except Exception as e:
                logger.warning(f"Could not load fastText LID model: {e}")
        
        # Statistics tracking
        self.stats = {
            "total_requests": 0,
            "english_count": 0,
            "tagalog_count": 0,
            "taglish_count": 0,
            "whisper_detection_used": 0,
            "ratio_analysis_used": 0,
            "short_phrase_count": 0,
            "tagabert_used": 0,
            "emotion_detected": 0,
            "processing_times": deque(maxlen=50),
            "avg_processing_time": 0,
            "last_update": time.time(),
            "port": self.pub_port,
            "health_port": ZMQ_HEALTH_PORT
        }
        
        # Thread management
        self._running = False
        self._thread = None
        self._health_thread = None
        
        logger.info("Language analyzer initialized successfully")
        
    def _register_service(self, port):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="StreamingLanguageAnalyzer",
                port=port,
                additional_info={
                    "capabilities": ["language_detection", "sentiment_analysis", "streaming"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            
    def _connect_to_tagabert(self):
        """Connect to TagaBERTa service using service discovery"""
        try:
            # Try to get the TagaBERTa address from service discovery
            tagabert_address = get_service_address(TAGABERT_SERVICE_NAME)
            
            if tagabert_address:
                self.tagabert_socket = self.context.socket(zmq.REQ)
                if SECURE_ZMQ:
                    self.tagabert_socket = configure_secure_client(self.tagabert_socket)
                    
                self.tagabert_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.tagabert_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
                self.tagabert_socket.connect(tagabert_address)
                logger.info(f"Connected to TagaBERTa service at {tagabert_address}")
                self.tagabert_available = True
            else:
                # Fall back to default port if service discovery fails
                fallback_address = get_zmq_connection_string(6010, "localhost")
                self.tagabert_socket = self.context.socket(zmq.REQ)
                if SECURE_ZMQ:
                    self.tagabert_socket = configure_secure_client(self.tagabert_socket)
                    
                self.tagabert_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.tagabert_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
                self.tagabert_socket.connect(fallback_address)
                logger.info(f"Connected to TagaBERTa service at fallback address {fallback_address}")
                self.tagabert_available = True
        except Exception as e:
            logger.warning(f"Could not connect to TagaBERTa service: {e}")
            self.tagabert_available = False

    def _connect_to_translation_service(self):
        """Connect to TranslationService using service discovery"""
        try:
            # Try to get the TranslationService address from service discovery
            translation_address = get_service_address("TranslationService")
            
            if translation_address:
                self.translation_socket = self.context.socket(zmq.REQ)
                if SECURE_ZMQ:
                    self.translation_socket = configure_secure_client(self.translation_socket)
                    
                self.translation_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.translation_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
                self.translation_socket.connect(translation_address)
                logger.info(f"Connected to TranslationService at {translation_address}")
                self.translation_available = True
            else:
                logger.warning("TranslationService not found in service discovery, will try alternative connection")
                # Try connecting to default address as fallback
                default_address = get_zmq_connection_string(5595, "localhost")
                try:
                    self.translation_socket = self.context.socket(zmq.REQ)
                    if SECURE_ZMQ:
                        self.translation_socket = configure_secure_client(self.translation_socket)
                    self.translation_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                    self.translation_socket.setsockopt(zmq.RCVTIMEO, 10000)
                    self.translation_socket.connect(default_address)
                    logger.info(f"Connected to TranslationService at {default_address}")
                    self.translation_available = True
                except Exception as fallback_error:
                    logger.error(f"Failed to connect to TranslationService: {fallback_error}")
        except Exception as e:
            logger.error(f"Error connecting to TranslationService: {e}")
            self.translation_available = False

    def _contains_potential_taglish_short_words(self, text):
        """
        Check if short text might contain Tagalog words that need translation.
        Important for short command detection in mixed language contexts.
        """
        # Common Tagalog verbs/words that might appear in short commands
        taglish_indicators = {
            'buksan', 'isara', 'patay', 'bukas', 'para', 'tama', 'sige', 'tigil', 
            'tuloy', 'ulit', 'bilis', 'bagal', 'hinto', 'lakasan', 'hina', 
            'patugtog', 'kanta', 'tugtog', 'kwento', 'usap', 'tignan', 'tingnan'
        }
        
        words = text.lower().split()
        return any(word in taglish_indicators for word in words)
    
    def report_health(self):
        """Report health metrics to the system dashboard"""
        logger.info("Health reporting thread started")
        
        while self._running:
            try:
                # Calculate derived metrics
                current_time = time.time()
                total = self.stats["total_requests"]
                
                # Calculate language distribution
                english_pct = (self.stats["english_count"] / total) * 100 if total > 0 else 0
                tagalog_pct = (self.stats["tagalog_count"] / total) * 100 if total > 0 else 0
                taglish_pct = (self.stats["taglish_count"] / total) * 100 if total > 0 else 0
                
                # Calculate detection method distribution
                whisper_pct = (self.stats["whisper_detection_used"] / total) * 100 if total > 0 else 0
                ratio_pct = (self.stats["ratio_analysis_used"] / total) * 100 if total > 0 else 0
                short_phrase_pct = (self.stats["short_phrase_count"] / total) * 100 if total > 0 else 0
                
                # Calculate average processing time
                if self.stats["processing_times"]:
                    self.stats["avg_processing_time"] = sum(self.stats["processing_times"]) / len(self.stats["processing_times"])
                
                # Update last update timestamp
                self.stats["last_update"] = current_time
                
                # Determine overall status
                status = "online"
                status_reason = "Operating normally"
                
                # Create health data
                health_data = {
                    "status": status,
                    "status_reason": status_reason,
                    "timestamp": current_time,
                    "component": "LanguageAnalyzer",
                    "metrics": {
                        "total_requests": total,
                        "english_percentage": english_pct,
                        "tagalog_percentage": tagalog_pct,
                        "taglish_percentage": taglish_pct,
                        "whisper_detection_percentage": whisper_pct,
                        "ratio_analysis_percentage": ratio_pct,
                        "short_phrase_percentage": short_phrase_pct,
                        "avg_processing_time": self.stats["avg_processing_time"],
                        "english_count": self.stats["english_count"],
                        "tagalog_count": self.stats["tagalog_count"],
                        "taglish_count": self.stats["taglish_count"],
                        "port": self.pub_port,
                        "health_port": ZMQ_HEALTH_PORT
                    }
                }
                
                # Send health data
                try:
                    # Format: "health <component_name> <json_data>"
                    health_message = f"health LanguageAnalyzer {json.dumps(health_data)}"
                    self.health_socket.send_string(health_message)
                    logger.debug(f"Sent health metrics to dashboard: {health_message}")
                except Exception as e:
                    logger.warning(f"Failed to send health metrics: {e}")
                    
                # Also publish metrics for other components to use
                try:
                    metrics_data = {"type": "metrics", "component": "language_analyzer", "data": health_data["metrics"]}
                    self.pub_socket.send(pickle.dumps(metrics_data))
                except Exception as e:
                    logger.warning(f"Failed to publish metrics: {e}")
            
            except Exception as e:
                logger.error(f"Error in health reporting: {e}")
            
            # Report every 5 seconds
            time.sleep(5)
    
    def analyze_tagalog_sentiment(self, text):
        """
        Analyze Tagalog text sentiment using TagaBERTa
        """
        if not self.tagabert_available or not self.tagabert_socket:
            logger.warning("TagaBERTa service not available for sentiment analysis")
            return None
            
        try:
            # Prepare request
            request = {
                "action": "analyze_sentiment",
                "text": text
            }
            # Send request
            if self.tagabert_socket is not None:
                self.tagabert_socket.send_json(request)
            else:
                logger.warning("tagabert_socket is None, cannot send request.")
                return None
            # Get response with timeout
            response = self.tagabert_socket.recv_json()
            if isinstance(response, dict) and response.get("success"):
                self.stats["tagabert_used"] += 1
                sentiment_result = response.get("result", {})
                if isinstance(sentiment_result, dict):
                    logger.info(f"TagaBERTa sentiment: {sentiment_result.get('label')}, score: {sentiment_result.get('score'):.2f}")
                else:
                    logger.info(f"TagaBERTa sentiment: {sentiment_result}")
                return sentiment_result
            else:
                if isinstance(response, dict):
                    logger.warning(f"TagaBERTa service error: {response.get('error')}")
                else:
                    logger.warning(f"TagaBERTa service error: {response}")
                return None
                
        except zmq.error.Again:
            logger.warning("TagaBERTa service timeout")
            return None
        except Exception as e:
            logger.error(f"Error getting TagaBERTa sentiment: {e}")
            return None
    
    def analyze_language(self, text, detected_language=None, whisper_detected_language=None):
        """
        Analyze language and determine language type
        (English, Tagalog, Taglish, etc.)
        
        Args:
            text (str): The text to analyze
            detected_language (str): Optional language code detected by upstream services
            whisper_detected_language (str): Optional language code detected by Whisper
            
        Returns:
            dict: Analysis results containing language type and other metadata
        """
        if not text:
            logger.warning("Empty text received for language analysis")
            return {"language_type": "unknown", "confidence": 0.0}
            
        text = text.strip().lower()
        result = {"original_text": text}
        
        # Check if we have a detected language from Whisper or other source
        if detected_language:
            if detected_language.lower() in ["en", "english"]:
                result["language_type"] = "english"
                result["confidence"] = 0.9
                result["needs_translation"] = False
                with self.metrics_lock:
                    self.stats["english_count"] = self.stats.get("english_count", 0) + 1
                return result
            elif detected_language.lower() in ["tl", "tagalog", "filipino"]:
                result["language_type"] = "tagalog"
                result["confidence"] = 0.85
                result["needs_translation"] = True
                # Add sentiment analysis for Tagalog
                sentiment = self.analyze_tagalog_sentiment(text)
                if sentiment:
                    result["sentiment"] = sentiment
                with self.metrics_lock:
                    self.stats["tagalog_count"] = self.stats.get("tagalog_count", 0) + 1
                return result
        
        # Try TagaBERTa for Tagalog/Taglish classification
        if self.tagabert_available:
            try:
                tagabert_result = self.analyze_tagalog_sentiment(text)
                if tagabert_result:
                    result["sentiment"] = tagabert_result
            except Exception as e:
                logger.error(f"TagaBERTa analysis error: {e}")

        # 1. Heuristic check for Taglish
        tagalog_word_count = 0
        for word in re.findall(r'\b\w+\b', text):
            if word.lower() in TAGALOG_WORDS:
                tagalog_word_count += 1
                
        total_words = len(re.findall(r'\b\w+\b', text))
        tagalog_ratio = tagalog_word_count / total_words if total_words > 0 else 0
        
        # Special check for short texts that might be Taglish greetings
        if total_words <= 5 and tagalog_word_count == 0 and self._contains_potential_taglish_short_words(text):
            result["language_type"] = "taglish"
            result["confidence"] = 0.6
            result["needs_translation"] = True
            with self.metrics_lock:
                self.stats["taglish_count"] = self.stats.get("taglish_count", 0) + 1
            return result
            
        # 2. Use word ratio to determine language
        if tagalog_ratio > 0.4:
            if tagalog_ratio > 0.8:
                result["language_type"] = "tagalog"
                result["confidence"] = min(0.9, tagalog_ratio)
                result["needs_translation"] = True
                with self.metrics_lock:
                    self.stats["tagalog_count"] = self.stats.get("tagalog_count", 0) + 1
            else:
                result["language_type"] = "taglish"
                result["confidence"] = 0.6 + (tagalog_ratio - 0.4) * 0.5  # Scale confidence based on ratio
                result["needs_translation"] = True
                with self.metrics_lock:
                    self.stats["taglish_count"] = self.stats.get("taglish_count", 0) + 1
        else:
            result["language_type"] = "english"
            result["confidence"] = 0.7 + (1 - tagalog_ratio) * 0.3  # Higher confidence for fewer Tagalog words
            result["needs_translation"] = False
            with self.metrics_lock:
                self.stats["english_count"] = self.stats.get("english_count", 0) + 1
                
        # Add metadata
        result["tagalog_words"] = tagalog_word_count
        result["total_words"] = total_words
        result["tagalog_ratio"] = tagalog_ratio
        
        return result

    def analyze_with_llm(self, prompt_text):
        """Use the new model_client to get analysis from the LLM service."""
        try:
            logger.info(f"Sending prompt to model service: {prompt_text[:50]}...")
            response_dict = model_client.generate(prompt=prompt_text, quality="fast")
            
            if response_dict and response_dict.get("status") == "ok":
                analysis_result = response_dict.get("response_text")
                logger.info(f"Received successful analysis from model service")
                return analysis_result
            else:
                error_msg = response_dict.get("message", "Unknown error") if response_dict else "No response"
                logger.error(f"Failed to get analysis from model service: {error_msg}")
                return "Error: Could not analyze."
        except Exception as e:
            logger.error(f"Exception during LLM analysis: {str(e)}")
            return "Error: Could not analyze."

    def start(self):
        """Start the language analyzer"""
        if self._running:
            logger.warning("Language analyzer is already running")
            return
            
        self._running = True
        
        # Start processing thread
        self._thread = threading.Thread(target=self._process_loop)
        self._thread.daemon = True
        self._thread.start()
        
        # Start health reporting thread
        self._health_thread = threading.Thread(target=self.report_health)
        self._health_thread.daemon = True
        self._health_thread.start()
        
        # Call parent's run method to ensure health check thread works
        super().run()
        
        logger.info("Language analyzer started successfully")

    def shutdown(self):
        """Gracefully shut down the language analyzer"""
        logger.info("Shutting down language analyzer...")
        self._running = False
        
        # Wait for threads to complete
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            logger.info("Processing thread joined")
            
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=2.0)
            logger.info("Health thread joined")
            
        # Clean up resources
        self.cleanup()
        logger.info("Language analyzer shutdown complete")

    def cleanup(self):
        """Clean up ZMQ resources to prevent leaks"""
        logger.info("Cleaning up resources")
        try:
            if hasattr(self, 'sub_socket') and self.sub_socket:
                self.sub_
                logger.info("Closed subscription socket")
                
            if hasattr(self, 'pub_socket') and self.pub_socket:
                self.pub_
                logger.info("Closed publisher socket")
                
            if hasattr(self, 'health_socket') and self.health_socket:
                self.health_
                logger.info("Closed health socket")
                
            if hasattr(self, 'tagabert_socket') and self.tagabert_socket:
                self.tagabert_
                logger.info("Closed TagaBERTa socket")
                
            if hasattr(self, 'translation_socket') and self.translation_socket:
                self.translation_
                logger.info("Closed Translation socket")
                
            if hasattr(self, 'context') and self.context:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
                logger.info("Terminated ZMQ context")
                
            logger.info("All resources cleaned up successfully")
            
            # Call parent cleanup to handle BaseAgent resources
            super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _process_loop(self):
        """Main processing loop for language analysis"""
        logger.info("Processing loop started")
        
        while self._running:
            try:
                msg = self.sub_socket.recv(flags=zmq.NOBLOCK)
                print(f"[DEBUG] Analyzer received raw msg: {msg}")
                logger.info(f"[DEBUG] Analyzer received raw msg: {msg}")
                
                # Handle different message formats - string or pickled data
                if msg.startswith(b'TRANSCRIPTION:'):
                    # It's a string message from StreamingSpeechRecognition
                    text_data = msg.decode('utf-8').replace('TRANSCRIPTION: ', '')
                    try:
                        data = json.loads(text_data)
                        text = data.get('text', '')
                        detected_language = data.get('language', None)
                        whisper_detected_language = data.get('language', None)
                    except json.JSONDecodeError:
                        # Simple string format fallback
                        text = text_data
                        detected_language = None
                        whisper_detected_language = None
                else:
                    # Pickled data
                    try:
                        data = pickle.loads(msg)
                        if data.get('type') == 'transcription':
                            text = data.get('transcription', '')
                            detected_language = data.get('detected_language', None)
                            whisper_detected_language = data.get('whisper_detected_language', None)
                        else:
                            # Skip non-transcription messages
                            continue
                    except pickle.UnpicklingError:
                        logger.error("Failed to unpickle message")
                        continue
                
                # Analyze language
                analysis = self.analyze_language(text, detected_language, whisper_detected_language)
                
                # Check if translation is needed
                translated_text = None
                translation_status = None
                if analysis.get('needs_translation', False) and self.translation_available:
                    try:
                        # Request translation from TranslationService
                        source_lang = analysis.get('language_type', 'tl')
                        target_lang = 'en'  # Default target language is English
                        
                        # Map simple language codes to what TranslationService expects
                        source_lang_map = {
                            'tagalog': 'tl',
                            'taglish': 'tl',
                            'english': 'en',
                            'tl': 'tl',
                            'en': 'en'
                        }
                        source_lang = source_lang_map.get(source_lang.lower(), source_lang)
                        
                        # Prepare translation request
                        translation_request = {
                            "text": text,
                            "source_lang": source_lang,
                            "target_lang": target_lang
                        }
                        
                        logger.info(f"Requesting translation: {text} ({source_lang} → {target_lang})")
                        
                        # Send request to TranslationService
                        if self.translation_socket is not None:
                            self.translation_socket.send_json(translation_request)
                            # Wait for response with timeout
                            if self.translation_socket.poll(10000):  # 10 second timeout
                                translation_response = self.translation_socket.recv_json()
                                if isinstance(translation_response, dict) and translation_response.get('status') == 'success':
                                    translated_text = translation_response.get('translation')
                                    translation_status = 'success'
                                    logger.info(f"Translation received: {translated_text}")
                                else:
                                    translation_status = 'error'
                                    logger.error(f"Translation error: {translation_response.get('message') if isinstance(translation_response, dict) else translation_response}")
                            else:
                                translation_status = 'timeout'
                                logger.error("Translation request timed out")
                        else:
                            translation_status = 'error'
                            logger.error("translation_socket is None, cannot send translation request.")
                    except Exception as e:
                        translation_status = 'error'
                        logger.error(f"Error requesting translation: {e}")
                
                # Prepare output with analysis results
                out = {
                    'type': 'language_analysis',
                    'transcription': text,
                    'detected_language': detected_language,
                    'analysis': analysis,
                    'timestamp': time.time(),
                    'has_sentiment': 'sentiment' in analysis,
                    'request_id': data.get('request_id')
                }
                
                # Add translation results if available
                if translated_text:
                    out['translated_text'] = translated_text
                    out['translation_status'] = translation_status
                
                # Send analysis output
                self.pub_socket.send(pickle.dumps(out))
                
                # Update metrics
                self.stats["total_requests"] += 1
                self.processed_streams_count += 1
                self.last_stream_time = datetime.now().isoformat()
                
            except zmq.Again:
                time.sleep(0.05)

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'language_analyzer',
            'components': {
                'tagabert_available': self.tagabert_available,
                'fasttext_available': self.fasttext_available,
                'translation_available': self.translation_available
            },
            'analyzer_status': "streaming",
            'processed_streams_count': self.processed_streams_count,
            'last_stream_time': self.last_stream_time,
            'language_stats': {
                'english_count': self.stats.get('english_count', 0),
                'tagalog_count': self.stats.get('tagalog_count', 0),
                'taglish_count': self.stats.get('taglish_count', 0)
            },
            'uptime': time.time() - self.start_time
        }

# Example usage
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = StreamingLanguageAnalyzer()
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