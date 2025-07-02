"""
Streaming Language Analyzer Module
Analyzes real-time transcriptions for language (English, Tagalog, Taglish)
"""

import zmq
import pickle
import logging
import re
import time
import json
import threading
import os
import psutil
from collections import deque
from datetime import datetime
from pathlib import Path
import requests
import socket
from typing import Dict, Optional, Any

from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import register_service, get_service_address
from main_pc_code.utils.env_loader import get_env
from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server

# Parse command line arguments
config = load_config()

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
    """Streaming Language Analyzer Agent for real-time language detection"""
    
    def __init__(self):
        """Initialize the language analyzer agent"""
        # Standard BaseAgent initialization at the beginning
        self.config = _agent_args
        super().__init__(
            name=getattr(self.config, 'name', 'StreamingLanguageAnalyzer'),
            port=getattr(self.config, 'port', None)
        )
        
        # Initialize state
        self.start_time = time.time()
        self.processed_streams_count = 0
        self.last_stream_time = 'N/A'
        
        # Use provided port or default
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
            stt_address = f"tcp://localhost:{ZMQ_SUB_PORT}"
            
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
            health_address = f"tcp://localhost:{ZMQ_HEALTH_PORT}"
            
        try:
            self.health_socket.connect(health_address)
            logger.info(f"Connected to health dashboard at {health_address}")
        except Exception as e:
            logger.warning(f"Could not connect to health dashboard: {e}")
        
        # Setup TagaBERTa connection using service discovery
        self.tagabert_socket = None
        self.tagabert_available = False
        self._connect_to_tagabert()
        
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
                fallback_address = f"tcp://localhost:6010"
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
            self.tagabert_socket.send_json(request)
            
            # Get response with timeout
            response = self.tagabert_socket.recv_json()
            
            if response.get("success"):
                self.stats["tagabert_used"] += 1
                sentiment_result = response.get("result", {})
                logger.info(f"TagaBERTa sentiment: {sentiment_result.get('label')}, score: {sentiment_result.get('score'):.2f}")
                return sentiment_result
            else:
                logger.warning(f"TagaBERTa service error: {response.get('error')}")
                return None
                
        except zmq.error.Again:
            logger.warning("TagaBERTa service timeout")
            return None
        except Exception as e:
            logger.error(f"Error getting TagaBERTa sentiment: {e}")
            return None
    
    def analyze_language(self, text, detected_language=None, whisper_detected_language=None):
        """
        Enhanced language analysis with improved thresholds and Whisper integration.
        Patched for testing: skips Tagaberta and all network calls.
        """
        start_time = time.time()
        # Patch: Always skip Tagaberta and network calls
        sentiment_analysis = None
        # First try using the most reliable detector: Whisper's detection
        if whisper_detected_language and whisper_detected_language in ['tl', 'fil']:
            logger.info(f"Using Whisper's language detection: {whisper_detected_language}")
            self.stats["whisper_detection_used"] += 1
            self.stats["tagalog_count"] += 1
            processing_time = time.time() - start_time
            self.stats["processing_times"].append(processing_time)
            result = {
                'language_type': 'tagalog',
                'tagalog_ratio': 0.9,
                'needs_translation': True,
                'detection_source': 'whisper',
                'processing_time': processing_time
            }
            return result
        if whisper_detected_language and whisper_detected_language == 'en':
            pass
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return {'language_type': 'unknown', 'tagalog_ratio': 0.0, 'needs_translation': False}
        tagalog_count = sum(1 for w in words if w in TAGALOG_WORDS)
        tagalog_ratio = tagalog_count / len(words)
        if tagalog_ratio > 0.75:
            language_type = 'tagalog'
            needs_translation = True
        elif tagalog_ratio > 0.25:
            language_type = 'taglish'
            needs_translation = True
        else:
            language_type = 'english'
            needs_translation = False
        if len(words) <= 2 and language_type == 'english' and self._contains_potential_taglish_short_words(text):
            logger.info(f"Reclassifying short phrase as potentially Taglish: '{text}'")
            language_type = 'taglish'
            needs_translation = True
        if detected_language in ['tl', 'fil'] and tagalog_ratio < 0.5:
            logger.info(f"Using Whisper's detection over ratio analysis for '{text}'")
            language_type = 'tagalog'
            needs_translation = True
        if language_type == 'english':
            self.stats["english_count"] += 1
        elif language_type == 'tagalog':
            self.stats["tagalog_count"] += 1
        elif language_type == 'taglish':
            self.stats["taglish_count"] += 1
        self.stats["ratio_analysis_used"] += 1
        if len(words) <= 2:
            self.stats["short_phrase_count"] += 1
        processing_time = time.time() - start_time
        self.stats["processing_times"].append(processing_time)
        logger.info(f"Language: {language_type}, Tagalog ratio: {tagalog_ratio:.2f}, Needs translation: {needs_translation}")
        # Patch: skip sentiment analysis
        result = {
            'language_type': language_type,
            'tagalog_ratio': tagalog_ratio, 
            'needs_translation': needs_translation,
            'word_count': len(words),
            'detection_source': 'ratio_analysis',
            'processing_time': processing_time
        }
        return result

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
                self.sub_socket.close()
                logger.info("Closed subscription socket")
                
            if hasattr(self, 'pub_socket') and self.pub_socket:
                self.pub_socket.close()
                logger.info("Closed publisher socket")
                
            if hasattr(self, 'health_socket') and self.health_socket:
                self.health_socket.close()
                logger.info("Closed health socket")
                
            if hasattr(self, 'tagabert_socket') and self.tagabert_socket:
                self.tagabert_socket.close()
                logger.info("Closed TagaBERTa socket")
                
            if hasattr(self, 'context') and self.context:
                self.context.term()
                logger.info("Terminated ZMQ context")
                
            logger.info("All resources cleaned up successfully")
            
            # Call parent cleanup
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
                data = pickle.loads(msg)
                if data.get('type') == 'transcription':
                    text = data.get('transcription', '')
                    detected_language = data.get('detected_language', None)
                    whisper_detected_language = data.get('whisper_detected_language', None)
                    analysis = self.analyze_language(text, detected_language, whisper_detected_language)
                    out = {
                        'type': 'language_analysis',
                        'transcription': text,
                        'detected_language': detected_language,
                        'analysis': analysis,
                        'timestamp': time.time(),
                        'has_sentiment': 'sentiment' in analysis,
                        'request_id': data.get('request_id')
                    }
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
                'fasttext_available': self.fasttext_available
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