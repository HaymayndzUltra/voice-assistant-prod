import logging
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import time
import uuid
import json
import re
import os
import random
import hashlib
import zmq
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from src.agents.mainpc.request_coordinator import CircuitBreaker
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from common.config_manager import load_unified_config
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager

sys.path.insert(0, str(PathManager.get_project_root()))
# Try importing optional dependencies
try:
    import langdetect
    from langdetect import detect
    from langdetect.lang_detect_exception import LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    
try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False

# Ito ang FINAL at PINAHUSAY na bersyon ng Translation Service.
# Pinagsasama nito ang lahat ng translation-related features sa isang,
# central, modular, at robust na ahente.

# Helper function for ZMQ security
def is_secure_zmq_enabled() -> bool:
    """Check if secure ZMQ should be enabled.
    
    Returns:
        bool: True if secure ZMQ is enabled, False otherwise
    """
    # In production, this would check environment variables or config
    return False

# --- Translation Dictionaries from consolidated_translator.py ---
# Translation Dictionary
COMMAND_TRANSLATIONS = {
    # Common file operations
    "buksan": "open",
    "isara": "close",
    "i-save": "save",
    "i-open": "open",
    "gumawa": "create",
    "gawa": "create",
    "magsave": "save",
    "magbukas": "open",
    "buksan mo": "open",
    "isara mo": "close",
    "i-close": "close",
    "i-download": "download",
    "i-upload": "upload",
    "tanggalin": "remove",
    "alisin": "remove",
    "i-delete": "delete",
    "burahin": "delete",
    "i-rename": "rename",
    "palitan ng pangalan": "rename",
    
    # System operations
    "i-restart": "restart",
    "i-reboot": "reboot",
    "i-shutdown": "shutdown",
    "patayin": "shutdown",
    "i-start": "start",
    "simulan": "start",
    "i-stop": "stop",
    "ihinto": "stop",
    "i-pause": "pause",
    "i-update": "update", 
    "i-upgrade": "upgrade",
    "i-install": "install",
    "mag-install": "install",
    
    # Data & network operations
    "i-backup": "backup",
    "mag-backup": "backup",
    "i-restore": "restore",
    "i-connect": "connect",
    "i-disconnect": "disconnect",
    "kumonekta": "connect",
    "makipag-ugnay": "connect",
    "i-transfer": "transfer",
    "ilipat": "transfer",
    "i-copy": "copy", 
    "kopyahin": "copy",
    "i-move": "move",
    "ilipat": "move",
    
    # Programming & development
    "i-debug": "debug",
    "ayusin": "fix",
    "i-fix": "fix",
    "i-test": "test",
    "subukan": "test",
    "i-compile": "compile",
    "i-build": "build",
    "i-deploy": "deploy",
    "i-run": "run",
    "patakbuhin": "run",
    "i-execute": "execute",
    "i-push": "push",
    "i-pull": "pull",
    "i-commit": "commit",
    "i-merge": "merge",
    "i-checkout": "checkout",
    "i-branch": "branch",
    
    # Web operations
    "i-refresh": "refresh",
    "i-reload": "reload",
    "i-browse": "browse",
    "mag-browse": "browse",
    "magsearch": "search",
    "hanapin": "search",
    "i-download": "download",
    
    # Common objects
    "file": "file",
    "folder": "folder",
    "direktori": "directory",
    "directory": "directory",
    "website": "website",
    "webpage": "webpage",
    "database": "database",
    "server": "server",
    "system": "system",
    "programa": "program",
    "application": "application",
    "app": "app",
    
    # Modifiers
    "bago": "new",
    "luma": "old", 
    "lahat": "all",
    "ito": "this",
    "iyan": "that",
    "na ito": "this",
    "na iyan": "that",
    "kasalukuyan": "current",
    "mabilis": "quick",
    "mabagal": "slow",
    
    # Prepositions
    "sa": "in", 
    "mula sa": "from",
    "para sa": "for",
    "tungkol sa": "about",
    
    # Articles and connectors
    "ang": "the",
    "mga": "the",
    "at": "and",
    "o": "or",
    "kung": "if",
    "kapag": "when",
    "pagkatapos": "after",
    "bago": "before",
    "habang": "while",
    "para": "for",
    "dahil": "because",
    "kaya": "so",
    
    # Pronouns
    "ako": "I",
    "ko": "I",
    "ikaw": "you",
    "mo": "you",
    "siya": "he/she",
    "niya": "his/her",
    "kami": "we",
    "tayo": "we",
    "namin": "our",
    "natin": "our",
    "sila": "they",
    "nila": "their",
    
    # Common phrases
    "pakiusap": "please",
    "paki": "please",
    "salamat": "thank you",
    "oo": "yes",
    "hindi": "no",
    "ngayon": "now",
    "mamaya": "later",
    "kahapon": "yesterday",
    "bukas": "tomorrow",
    "dito": "here",
    "diyan": "there",
    "malapit": "near",
    "malayo": "far",
    
    # Basic test phrases
    "hello": "kamusta",
    "hello world": "kamusta mundo",
    "good morning": "magandang umaga",
    "good afternoon": "magandang hapon",
    "good evening": "magandang gabi",
    "how are you": "kamusta ka",
    "i am fine": "mabuti naman ako",
    "thank you very much": "maraming salamat",
    "you're welcome": "walang anuman",
    "excuse me": "pasensya na",
    "i'm sorry": "pasensya na po",
    "goodbye": "paalam",
    "see you later": "kita tayo mamaya",
    "nice to meet you": "kinagagalak kitang makilala",
    "my name is": "ang pangalan ko ay",
    
    # Time expressions
    "umaga": "morning",
    "tanghali": "noon",
    "hapon": "afternoon",
    "gabi": "evening",
    "araw": "day",
    "linggo": "week",
    "buwan": "month",
    "taon": "year",
    
    # Questions
    "ano": "what",
    "sino": "who",
    "kailan": "when",
    "saan": "where",
    "bakit": "why",
    "paano": "how",
}

# Common Sentence Patterns
COMMON_PHRASE_PATTERNS = {
    "buksan mo (ang|yung) (.+?)": "open the {}",
    "isara mo (ang|yung) (.+?)": "close the {}",
    "i-save mo (ang|yung) (.+?)": "save the {}",
    "i-delete mo (ang|yung) (.+?)": "delete the {}",
    "i-check mo (ang|yung|kung) (.+?)": "check the {}",
    "tignan mo (ang|yung) (.+?)": "look at the {}",
    "hanapin mo (ang|yung) (.+?)": "find the {}",
    "gumawa ka ng (.+?)": "create a {}",
    "alisin mo (ang|yung) (.+?)": "remove the {}",
    "ilipat mo (ang|yung) (.+?) sa (.+?)": "move the {} to {}",
    "i-run mo (ang|yung) (.+?)": "run the {}",
    "i-execute mo (ang|yung) (.+?)": "execute the {}",
    "i-install mo (ang|yung) (.+?)": "install the {}",
    "i-update mo (ang|yung) (.+?)": "update the {}",
    "i-restart mo (ang|yung) (.+?)": "restart the {}",
    "i-compile mo (ang|yung) (.+?)": "compile the {}",
    "i-edit mo (ang|yung) (.+?)": "edit the {}",
    "ano (ang|yung) (.+?)": "what is the {}",
    "saan (ang|yung) (.+?)": "where is the {}",
    "kailan (ang|yung) (.+?)": "when is the {}",
    "bakit (ang|yung) (.+?)": "why is the {}",
    "paano (ang|yung) (.+?)": "how is the {}",
    "magsearch ka ng (.+?)": "search for {}",
}

# Complete Sentence Translations
COMPLETE_SENTENCES = {
    "buksan mo ang file na ito": "open this file",
    "isara mo ang window": "close the window",
    "i-save mo ang document": "save the document",
    "i-check mo kung may updates": "check if there are updates",
    "i-restart mo ang computer": "restart the computer",
    "gumawa ka ng bagong folder": "create a new folder",
    "buksan mo ang browser": "open the browser",
    "i-close mo ang application": "close the application",
    "i-download mo ang file": "download the file",
    "i-delete mo ang temporary files": "delete the temporary files",
    "mag-log out ka": "log out",
    "mag-search ka ng": "search for",
}

# Expanded Tagalog words list from language_and_translation_coordinator.py
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

# TagaBERTa service configuration
TAGABERT_SERVICE_PORT = 6010
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds

# --- Add AdvancedTimeoutManager (from legacy) ---
import numpy as np
from collections import defaultdict
from common.env_helpers import get_env

class AdvancedTimeoutManager:
    """Manages dynamic timeouts for translation requests."""
    def __init__(self, **kwargs):
        self.timeouts = {}
        self.response_times = defaultdict(list)
        self.max_history = 20
        self.default_timeout = 5000  # 5 seconds
        self.max_timeout = 15000  # 15 seconds

    def calculate_timeout(self, text: str) -> int:
        text_length = len(text)
        if text_length < 10:
            base_timeout = 2000
        elif text_length < 50:
            base_timeout = 5000
        elif text_length < 200:
            base_timeout = 8000
        else:
            base_timeout = 12000
        key = self._get_length_bucket(text_length)
        if key in self.timeouts:
            return min(int(self.timeouts[key] * 1.5), self.max_timeout)
        return base_timeout

    def record_response_time(self, text: str, response_time: float):
        key = self._get_length_bucket(len(text))
        self.response_times[key].append(response_time)
        if len(self.response_times[key]) > self.max_history:
            self.response_times[key].pop(0)
        if self.response_times[key]:
            self.timeouts[key] = np.percentile(self.response_times[key], 95)

    def _get_length_bucket(self, length: int) -> str:
        if length < 10:
            return "tiny"
        elif length < 50:
            return "small"
        elif length < 200:
            return "medium"
        else:
            return "large"

# --- Connection Management System ---
class ConnectionManager:
    """
    Manages ZMQ connections to various services with circuit breaker integration.
    
    This class handles:
    - Creating and maintaining connections to multiple services
    - Automatic reconnection
    - Socket configuration
    - Error handling with circuit breakers
    """
    
    def __init__(self, agent):
        """Initialize connection manager with reference to parent agent"""
        self.agent = agent
        self.logger = agent.logger
        self.sockets = {}
        self.addresses = {}
        
    def _create_socket(self, service_name):
        """
        Create a ZMQ socket for the specified service
        
        Args:
            service_name: Name of the service to connect to
        
        Returns:
            Configured ZMQ socket or None if creation failed
        """
        try:
            # Try to get the service address
            service_address = self.agent.get_service_address(service_name)
            if not service_address:
                self.logger.warning(f"Could not find address for {service_name}")
                return None
                
            # Create socket
            socket = self.agent.context.socket(zmq.REQ)
            
            # Configure socket
            if is_secure_zmq_enabled():
                socket = configure_secure_client(socket)
            
            # Set timeouts
            socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 seconds send timeout
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds receive timeout
            socket.setsockopt(zmq.LINGER, 0)       # Don't wait for pending messages on close
            
            # Connect
            socket.connect(service_address)
            self.addresses[service_name] = service_address
            self.logger.info(f"Connected to {service_name} at {service_address}")
            
            return socket
        except Exception as e:
            self.logger.error(f"Error creating socket for {service_name}: {e}")
            return None
        
    def get_socket(self, service_name):
        """
        Get or create a socket for the specified service
        
        Args:
            service_name: Name of the service to connect to
            
        Returns:
            ZMQ socket or None if not available
        """
        # Check if we already have a socket
        if service_name in self.sockets and self.sockets[service_name]:
            return self.sockets[service_name]
            
        # No socket, create new one
        socket = self._create_socket(service_name)
        if socket:
            self.sockets[service_name] = socket
            
        return socket
        
    def reset_socket(self, service_name):
        """
        Reset the connection to a service by closing and recreating the socket
        
        Args:
            service_name: Name of the service to reconnect to
            
        Returns:
            New ZMQ socket or None if reset failed
        """
        if service_name in self.sockets and self.sockets[service_name]:
            try:
                self.sockets[service_name].close()
            except Exception as e:
                self.logger.warning(f"Error closing socket for {service_name}: {e}")
                
        # Create new socket
        socket = self._create_socket(service_name)
        if socket:
            self.sockets[service_name] = socket
        else:
            # If socket creation failed, remove from sockets dict
            if service_name in self.sockets:
                self.sockets.pop(service_name)
                
        return self.sockets.get(service_name)
    
    def cleanup(self):
        """Close all sockets and clean up resources."""
        for service_name, socket in list(self.sockets.items()):
            try:
                self.logger.info(f"Socket for {service_name} closed")
            except Exception as e:
                self.logger.error(f"Error closing socket for {service_name}: {e}")
        self.sockets = {}

# --- Standard Engine Interface ---
class BaseEngineClient:
    def __init__(self, agent, engine_name, target_agent_name, connection_manager=None, timeout_manager=None):
        self.agent = agent
        self.engine_name = engine_name
        self.target_agent_name = target_agent_name
        self.logger = self.agent.logger
        self.connection_manager = connection_manager
        self.timeout_manager = timeout_manager or AdvancedTimeoutManager()
        
    def _send_request(self, payload):
        """Sends a request to the target agent and handles the response."""
        if not self.target_agent_name:
            self.logger.error("No target agent specified for this engine client.")
            return None
            
        try:
            text = payload.get('text', '')
            timeout = self.timeout_manager.calculate_timeout(text)
            self.logger.info(f"Sending request to {self.target_agent_name} with timeout {timeout} ms: {payload}")
            
            # Use agent's resilient send request if available
            if hasattr(self.agent, '_resilient_send_request'):
                response = self.agent._resilient_send_request(self.target_agent_name, payload)
                if response:
                    # We don't have actual elapsed time with _resilient_send_request
                    # but we can still log the response
                    self.logger.info(f"Received response from {self.target_agent_name} via resilient request")
                    return response
                return None
            
            # Fall back to direct socket communication if _resilient_send_request not available
            socket = self.connection_manager.get_socket(self.target_agent_name)
            if not socket:
                self.logger.error(f"Failed to get socket for {self.target_agent_name}")
                return None
                
            socket.send_string(json.dumps(payload))
            
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            start_time = time.time()
            if poller.poll(timeout):  # Poll with calculated timeout
                response = socket.recv_json()
                elapsed = (time.time() - start_time) * 1000
                self.timeout_manager.record_response_time(text, elapsed)
                self.logger.info(f"Received response from {self.target_agent_name}: {response}")
                return response
            else:
                self.logger.error(f"Timeout waiting for response from {self.target_agent_name}")
                self.connection_manager.reset_socket(self.target_agent_name)
                return None
        except Exception as e:
            self.logger.error(f"Error communicating with {self.target_agent_name}: {e}")
            self.connection_manager.reset_socket(self.target_agent_name)
            return None
    
    def translate(self, text, source_lang, target_lang):
        """This method must be implemented by subclasses."""
        raise NotImplementedError
        
    def cleanup(self):
        """Clean up resources."""
        # No resources to clean up as socket management is handled by ConnectionManager
        pass

class NLLBEngineClient(BaseEngineClient):
    def __init__(self, agent, connection_manager=None):
        super().__init__(agent, engine_name='nllb', target_agent_name='NLLBAdapter', connection_manager=connection_manager)

    def translate(self, text, source_lang, target_lang):
        payload = {'text': text, 'source_lang': source_lang, 'target_lang': target_lang, 'action': 'translate'}
        return self._send_request(payload)

class StreamingEngineClient(BaseEngineClient):
    def __init__(self, agent, connection_manager=None):
        super().__init__(agent, engine_name='streaming', target_agent_name='FixedStreamingTranslation', connection_manager=connection_manager)

    def translate(self, text, source_lang, target_lang):
        payload = {'text': text, 'source_lang': source_lang, 'target_lang': target_lang}
        return self._send_request(payload)

class RemoteGoogleEngineClient(BaseEngineClient):
    def __init__(self, agent, connection_manager=None):
        super().__init__(agent, engine_name='google_remote', target_agent_name='RemoteConnectorAgent', connection_manager=connection_manager)

    def translate(self, text, source_lang, target_lang):
        payload = {
            'model': 'google_translate',
            'data': {
                'text': text,
                'source_language': source_lang,
                'target_language': target_lang
            }
        }
        return self._send_request(payload)

# New Dictionary Engine Client
class DictionaryEngineClient(BaseEngineClient):
    def __init__(self, agent):
        super().__init__(agent, engine_name='dictionary', target_agent_name=None)
        self.dictionary = COMMAND_TRANSLATIONS
        self.patterns = COMMON_PHRASE_PATTERNS
        self.sentences = COMPLETE_SENTENCES
        self.logger.info("Dictionary Engine Client initialized with local dictionaries")

    def translate(self, text, source_lang, target_lang):
        """Translate text using the built-in dictionary (no ZMQ request needed)"""
        try:
            # Only support Filipino to English or English to Filipino
            if not ((source_lang.startswith('tl') or source_lang.startswith('fil')) and target_lang.startswith('en')) and \
               not (source_lang.startswith('en') and (target_lang.startswith('tl') or target_lang.startswith('fil'))):
                return {
                    'status': 'error',
                    'message': 'Dictionary only supports Filipino <-> English translation'
                }
                
            # Check if the exact text is in the dictionary
            if text.lower() in self.dictionary:
                return {
                    'translation': self.dictionary[text.lower()],
                    'engine_used': 'dictionary',
                    'confidence': 1.0,
                    'status': 'success'
                }
                
            # Check for pattern matches
            for pattern, template in self.patterns.items():
                match = re.match(pattern, text.lower())
                if match:
                    # Fill in the template with the matched groups
                    groups = match.groups()
                    translated = template.format(*groups[1:])  # Skip the first group (ang|yung)
                    return {
                        'translation': translated,
                        'engine_used': 'dictionary',
                        'confidence': 0.9,
                        'status': 'success'
                    }
                    
            # Check for complete sentence matches
            for sentence, translation in self.sentences.items():
                if text.lower() == sentence.lower():
                    return {
                        'translation': translation,
                        'engine_used': 'dictionary',
                        'confidence': 1.0,
                        'status': 'success'
                    }
                    
            # No match found
            return {
                'status': 'error',
                'message': 'No dictionary match found',
                'engine_used': 'dictionary'
            }
            
        except Exception as e:
            self.logger.error(f"Dictionary translation error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Dictionary translation error: {str(e)}',
                'engine_used': 'dictionary'
            }

# --- Internal Modules (Placeholders) ---
class LanguageDetector:
    """
    Handles multi-layered, advanced language detection.
    
    Ito ang module na responsible sa pag-detect ng wika ng input text.
    Gumagamit ito ng multiple detection methods (langdetect, fastText, TagaBERTa)
    para sa mas accurate na detection, lalo na para sa Taglish text.
    """
    def __init__(self, agent):
        self.agent = agent
        self.logger = agent.logger
        self.context = agent.context
        self.connection_manager = agent.connection_manager
        
        # Initialize language detection components
        self.has_langdetect = False
        self.has_fasttext = False
        self.fasttext_model = None
        self.tagabert_available = False
        self.tagalog_lexicon = set(TAGALOG_WORDS_SET)
        
        # Initialize langdetect
        try:
            import langdetect
            from langdetect import DetectorFactory
            from langdetect.lang_detect_exception import LangDetectException
            DetectorFactory.seed = 0  # For reproducible results
            self.langdetect = langdetect
            self.LangDetectException = LangDetectException
            self.has_langdetect = True
            self.logger.info("Initialized langdetect for language detection")
        except ImportError:
            self.logger.warning("langdetect not available. Language detection will be limited.")
        
        # Initialize fastText if available
        try:
            import fasttext
            self.has_fasttext = True
            if os.path.exists(FASTTEXT_MODEL_PATH):
                try:
                    self.fasttext_model = fasttext.load_model(FASTTEXT_MODEL_PATH)
                    self.logger.info(f"Loaded FastText model from {FASTTEXT_MODEL_PATH}")
                except Exception as e:
                    self.logger.error(f"Failed to load FastText model: {e}")
            else:
                self.logger.warning(f"FastText model not found at {FASTTEXT_MODEL_PATH}")
        except ImportError:
            self.logger.warning("fasttext not available. Language detection will be limited.")
        
        # Load Tagalog lexicon if available
        if os.path.exists(TAGALOG_LEXICON_PATH):
            try:
                with open(TAGALOG_LEXICON_PATH, 'r', encoding='utf-8') as f:
                    self.tagalog_lexicon.update(line.strip().lower() for line in f if line.strip())
                self.logger.info(f"Loaded {len(self.tagalog_lexicon)} Tagalog words from lexicon")
            except Exception as e:
                self.logger.error(f"Failed to load Tagalog lexicon: {e}")
        
        # Test TagaBERTa service connection
        try:
            pc2_ip = agent.get_config("pc2_ip", "localhost")
            self.tagabert_available = self._test_tagabert_connection()
        except Exception as e:
            self.logger.warning(f"Failed to test TagaBERTa service connection: {e}")
            self.tagabert_available = False

    def _test_tagabert_connection(self):
        """Test connection to TagaBERTa service using ConnectionManager."""
        try:
            socket = self.connection_manager.get_socket("TagaBERTaService")
            if not socket:
                self.logger.warning("Failed to get socket for TagaBERTaService")
                return False
                
            # Test connection
            socket.send_json({
                "action": "ping", 
                "timestamp": time.time()
            })
            
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            if poller.poll(3000):  # 3 second timeout
                response = socket.recv_json()
                if response and response.get("status") == "ok":
                    self.logger.info("TagaBERTa service is responsive")
                    return True
                else:
                    self.logger.warning(f"TagaBERTa service responded with non-ok status: {response}")
                    return False
            else:
                self.logger.warning("TagaBERTa service timed out")
                self.connection_manager.reset_socket("TagaBERTaService")
                return False
        except Exception as e:
            self.logger.warning(f"Error testing TagaBERTa service: {e}")
            return False

    def _is_taglish_candidate(self, text: str, langdetect_code: str, langdetect_confidence: float) -> bool:
        """Check if text is a candidate for more specific Taglish detection."""
        text_lower = text.lower()
        words = text_lower.split()
        
        if langdetect_code in ['en', 'tl']:
            # If langdetect is somewhat confident it's en or tl, it's a candidate
            if langdetect_confidence > 0.5:
                return True
            # If low confidence, but contains Tagalog words, it's a candidate
            if any(word in self.tagalog_lexicon for word in words):
                return True
        # If langdetect identified other languages but Tagalog words are present
        elif any(word in self.tagalog_lexicon for word in words):
            return True
        
        return False

    def detect_language(self, text: str) -> str:
        """Detect the language of the input text, with refined Taglish/Tagalog detection."""
        if not text.strip():
            self.logger.info("Empty text received for language detection, defaulting to 'unknown'.")
            return 'unknown'

        detected_lang_code = 'en'  # Default
        text_lower = text.lower()

        # Step 1: Initial detection with langdetect
        if self.has_langdetect:
            try:
                langdetect_results = self.langdetect.detect_langs(text_lower)
                primary_lang_obj = langdetect_results[0]
                ld_lang_code = primary_lang_obj.lang
                ld_confidence = primary_lang_obj.prob
                
                self.logger.info(f"langdetect: Initial detection '{ld_lang_code}' (conf: {ld_confidence:.2f}) for: '{text[:50]}...'")
                detected_lang_code = ld_lang_code
                
            except Exception as e:
                self.logger.warning(f"langdetect failed for: '{text[:50]}...'. Proceeding with other methods. Error: {e}")
                ld_lang_code = 'unknown'
                ld_confidence = 0.0
        else:
            ld_lang_code = 'unknown'
            ld_confidence = 0.0

        # Step 2: Refine with fastText if available and it's a Taglish candidate
        is_candidate_for_refinement = self._is_taglish_candidate(text_lower, ld_lang_code, ld_confidence)
        
        if self.has_fasttext and self.fasttext_model and is_candidate_for_refinement:
            try:
                # fastText expects a single line of text
                predictions = self.fasttext_model.predict(text_lower.replace('\n', ' '), k=1)
                ft_lang_code = predictions[0][0].replace('__label__', '')
                ft_confidence = predictions[1][0]
                
                self.logger.info(f"fastText: Detected '{ft_lang_code}' (conf: {ft_confidence:.2f})")
                
                # Trust fastText more for 'tl' and 'en' if confidence is high, or if it identifies 'taglish'
                if ft_lang_code in ['en', 'tl', 'taglish'] and ft_confidence > 0.6:
                    detected_lang_code = ft_lang_code
                elif ft_lang_code == 'tl' and detected_lang_code == 'en' and ft_confidence > 0.4:
                    # Re-evaluate if langdetect said en but fastText says tl
                    detected_lang_code = 'tl'
            except Exception as e:
                self.logger.warning(f"fastText prediction failed: {e}")

        # Step 3: Further refine with TagaBERTa if available and still ambiguous or Tagalog/Taglish suspected
        if self.tagabert_available and detected_lang_code in ['en', 'tl', 'taglish', 'unknown']:
            try:
                request_payload = {"action": "analyze_language", "text": text_lower}
                socket = self.connection_manager.get_socket("TagaBERTaService")
                socket.send_json(request_payload)
                
                if socket.poll(1000, zmq.POLLIN):  # Wait 1 sec for TagaBERTa
                    response = socket.recv_json()
                    tb_lang_code = response.get('language')
                    tb_confidence = response.get('confidence', 0.0)
                    
                    self.logger.info(f"TagaBERTa: Detected '{tb_lang_code}' (conf: {tb_confidence:.2f})")
                    
                    if tb_lang_code and tb_confidence > 0.7:  # Trust TagaBERTa if highly confident
                        detected_lang_code = tb_lang_code
                else:
                    self.logger.warning("TagaBERTa service timed out during language analysis.")
                    
                    # Re-establish connection for next time if timeout
                    self.connection_manager.reset_socket("TagaBERTaService")
            except Exception as e:
                self.logger.error(f"Error communicating with TagaBERTa service: {e}")
                
                # Attempt to gracefully handle socket error
                try:
                    if socket:
                        self.connection_manager.reset_socket("TagaBERTaService")
                except Exception as se_conn:
                    self.logger.error(f"Failed to re-establish TagaBERTa connection: {se_conn}")
                    self.tagabert_available = False  # Mark as unavailable if re-connection fails

        # Step 4: Final check using lexicon for 'tl' or 'taglish'
        # If detected_lang_code is still 'en' but contains many Tagalog words, consider it 'taglish'
        if detected_lang_code == 'en':
            words = text_lower.split()
            tagalog_word_count = sum(1 for word in words if word in self.tagalog_lexicon)
            
            if len(words) > 0 and (tagalog_word_count / len(words)) > 0.3:  # If more than 30% words are Tagalog
                self.logger.info(f"Lexicon override: Detected 'en' but found {tagalog_word_count}/{len(words)} Tagalog words. Classifying as 'taglish'.")
                detected_lang_code = 'taglish'
            elif len(words) <= 5 and tagalog_word_count >= 1 and (tagalog_word_count / len(words)) >= 0.2:  # For very short phrases
                self.logger.info(f"Lexicon override (short phrase): Detected 'en' but found {tagalog_word_count}/{len(words)} Tagalog words. Classifying as 'taglish'.")
                detected_lang_code = 'taglish'

        # Normalize 'fil' (Filipino) or 'taglish' to 'tl' if that's what downstream services expect for Tagalog
        if detected_lang_code in ['fil', 'taglish']:
            self.logger.info(f"Normalizing '{detected_lang_code}' to 'tl' for translation purposes.")
            detected_lang_code = 'tl'
        
        # Ensure we always return a valid code, default to 'en' if all else fails and it's unknown
        if detected_lang_code == 'unknown' or not detected_lang_code:
            self.logger.info("Language detection inconclusive, defaulting to 'en'.")
            detected_lang_code = 'en'

        # Step 5: Return the detected language
        self.logger.info(f"Final language detection result: {detected_lang_code}")
        return detected_lang_code

# --- Refactor TranslationCache for persistent storage ---
class TranslationCache:
    """
    Enhanced caching system for translations with tiered storage:
    - In-memory LRU cache for fastest access to common translations
    - File-based persistent cache for less common but still valuable translations
    - Automatic cache entry expiration
    - Metrics tracking for cache hits/misses
    - Memory usage monitoring to prevent excessive RAM consumption
    """
    
    def __init__(self, agent):
        """Initialize the translation cache with both in-memory and persistent storage"""
        self.agent = agent
        self.logger = logging.getLogger(f"{self.agent.name}.TranslationCache")
        
        # Configure cache sizes and expiration
        self.memory_cache_max_size = 10000  # Maximum number of in-memory cache entries
        self.memory_cache_max_bytes = 20 * 1024 * 1024  # 20 MB max memory usage
        self.disk_cache_max_entries = 100000  # Maximum number of disk cache entries
        self.cache_entry_ttl = 7 * 24 * 60 * 60  # 7 days in seconds
        
        # Initialize in-memory cache using an OrderedDict for LRU behavior
        self.memory_cache = {}
        self.memory_cache_access_order = []
        self.estimated_memory_usage = 0
        
        # Initialize disk cache
        self.cache_dir = PathManager.get_project_root() / "cache" / "translation_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics = {
            "memory_hits": 0,
            "disk_hits": 0, 
            "misses": 0,
            "memory_entries": 0,
            "disk_entries": 0,
            "memory_bytes": 0,
            "evictions": 0,
            "writes": 0
        }
        
        # Cache maintenance
        self._load_cache_stats()
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        # Load existing cache stats
        try:
            self._cleanup_expired_entries()
        except Exception as e:
            self.logger.warning(f"Error during initial cache cleanup: {e}")
    
    def get(self, key: str) -> Optional[str]:
        """
        Get a cached translation.
        
        Args:
            key: Cache key, typically a hash of text+source_lang+target_lang
            
        Returns:
            The cached translation or None if not found
        """
        # First, try memory cache (fastest)
        hashed_key = self._hash_key(key)
        
        # Check memory cache first (fastest)
        if hashed_key in self.memory_cache:
            entry = self.memory_cache[hashed_key]
            
            # Check if expired
            if time.time() - entry['timestamp'] > self.cache_entry_ttl:
                # Expired, remove from memory cache
                self._remove_from_memory_cache(hashed_key)
                self.metrics["evictions"] += 1
                self.metrics["memory_entries"] -= 1
                self.metrics["misses"] += 1
                return None
                
            # Update access order for LRU
            self._update_access_order(hashed_key)
            
            # Update metrics
            self.metrics["memory_hits"] += 1
            
            # Return cached translation
            return entry['value']
            
        # Not in memory cache, try disk cache
        disk_value = self._read_from_memory(hashed_key)
        if disk_value:
            # Found in disk cache, add to memory cache for faster future access
            self._add_to_memory_cache(hashed_key, disk_value)
            
            # Update metrics
            self.metrics["disk_hits"] += 1
            
            return disk_value
        
        # Not found in any cache
        self.metrics["misses"] += 1
        return None
        
    def _read_from_memory(self, hashed_key):
        """
        Read a cached translation from disk
        
        Args:
            hashed_key: Hashed cache key
            
        Returns:
            The cached translation or None if not found
        """
        try:
            cache_file = self.cache_dir / f"{hashed_key}.json"
            if not cache_file.exists():
                return None
                
            # Read and parse cache entry
            with open(cache_file, 'r') as f:
                entry = json.load(f)
                
            # Check if expired
            if time.time() - entry['timestamp'] > self.cache_entry_ttl:
                # Expired, remove cache file
                cache_file.unlink(missing_ok=True)
                self.metrics["disk_entries"] -= 1
                return None
                
            return entry['value']
        except Exception as e:
            self.logger.warning(f"Error reading from disk cache: {e}")
            return None
            
    def _add_to_memory_cache(self, hashed_key, value):
        """
        Add an entry to the memory cache with LRU eviction if needed
        
        Args:
            hashed_key: Hashed cache key
            value: Value to cache
        """
        # Estimate memory size of this entry
        entry_size = len(hashed_key) + len(value) * 2  # Rough estimate
        
        # Check if we need to evict entries to stay under memory limit
        while (len(self.memory_cache) >= self.memory_cache_max_size or 
               self.estimated_memory_usage + entry_size > self.memory_cache_max_bytes):
            if not self.memory_cache_access_order:
                break
                
            # Evict least recently used entry
            lru_key = self.memory_cache_access_order[0]
            lru_entry = self.memory_cache[lru_key]
            lru_size = len(lru_key) + len(lru_entry['value']) * 2
            
            # Remove from memory cache
            self._remove_from_memory_cache(lru_key)
            self.metrics["evictions"] += 1
        
        # Add new entry
        self.memory_cache[hashed_key] = {
            'value': value,
            'timestamp': time.time()
        }
        self.memory_cache_access_order.append(hashed_key)
        
        # Update estimated memory usage
        self.estimated_memory_usage += entry_size
        self.metrics["memory_bytes"] = self.estimated_memory_usage
        self.metrics["memory_entries"] += 1
        
    def _update_access_order(self, hashed_key):
        """Update LRU access order for a cache key"""
        if hashed_key in self.memory_cache_access_order:
            self.memory_cache_access_order.remove(hashed_key)
        self.memory_cache_access_order.append(hashed_key)
        
    def _remove_from_memory_cache(self, hashed_key):
        """Remove an entry from memory cache"""
        if hashed_key in self.memory_cache:
            entry = self.memory_cache[hashed_key]
            entry_size = len(hashed_key) + len(entry['value']) * 2
            
            # Remove from cache and access order
            del self.memory_cache[hashed_key]
            if hashed_key in self.memory_cache_access_order:
                self.memory_cache_access_order.remove(hashed_key)
                
            # Update estimated memory usage
            self.estimated_memory_usage -= entry_size
            self.metrics["memory_bytes"] = self.estimated_memory_usage
    
    def set(self, key: str, value: str):
        """
        Set a cached translation
        
        Args:
            key: Cache key, typically a hash of text+source_lang+target_lang
            value: Translation to cache
        """
        hashed_key = self._hash_key(key)
        
        # Add to memory cache
        self._add_to_memory_cache(hashed_key, value)
        
        # Persist to disk cache asynchronously
        self.thread_pool.submit(self._persist_entry_async, hashed_key, value)
        self.metrics["writes"] += 1
        
    def _persist_entry_async(self, hashed_key, value):
        """
        Persist a cache entry to disk asynchronously
        
        Args:
            hashed_key: Hashed cache key
            value: Value to cache
        """
        try:
            # Create cache entry
            cache_entry = {
                'value': value,
                'timestamp': time.time()
            }
            
            # Write to disk
            cache_file = self.cache_dir / f"{hashed_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(cache_entry, f)
                
            # Update metrics
            self.metrics["disk_entries"] += 1
            
            # Periodically clean up expired entries
            if random.random() < 0.05:  # 5% chance on each write
                self.thread_pool.submit(self._cleanup_expired_entries)
        except Exception as e:
            self.logger.warning(f"Error persisting to disk cache: {e}")
            
    def _cleanup_expired_entries(self):
        """Clean up expired cache entries"""
        try:
            # Get all cache files
            cache_files = list(self.cache_dir.glob("*.json"))
            
            # Randomly sample a subset of files to check (for efficiency)
            sample_size = min(100, len(cache_files))
            files_to_check = random.sample(cache_files, sample_size) if len(cache_files) > sample_size else cache_files
            
            # Check each file
            now = time.time()
            for cache_file in files_to_check:
                try:
                    with open(cache_file, 'r') as f:
                        entry = json.load(f)
                        
                    # Check if expired
                    if now - entry['timestamp'] > self.cache_entry_ttl:
                        # Remove expired file
                        cache_file.unlink(missing_ok=True)
                        self.metrics["disk_entries"] -= 1
                except Exception as e:
                    # File might be corrupted, remove it
                    self.logger.warning(f"Error checking cache file {cache_file}: {e}")
                    try:
                        cache_file.unlink(missing_ok=True)
                    except:
                        pass
        except Exception as e:
            self.logger.warning(f"Error during cache cleanup: {e}")
            
    def _load_cache_stats(self):
        """Load cache statistics"""
        try:
            # Count disk entries
            cache_files = list(self.cache_dir.glob("*.json"))
            self.metrics["disk_entries"] = len(cache_files)
        except Exception as e:
            self.logger.warning(f"Error loading cache stats: {e}")
        
    def clear(self):
        """Clear the entire cache"""
        # Clear memory cache
        self.memory_cache.clear()
        self.memory_cache_access_order.clear()
        self.estimated_memory_usage = 0
        
        # Clear disk cache
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink(missing_ok=True)
        except Exception as e:
            self.logger.warning(f"Error clearing disk cache: {e}")
            
        # Reset metrics
        self.metrics["memory_hits"] = 0
        self.metrics["disk_hits"] = 0
        self.metrics["misses"] = 0
        self.metrics["memory_entries"] = 0
        self.metrics["disk_entries"] = 0
        self.metrics["memory_bytes"] = 0
        self.metrics["evictions"] = 0
        self.metrics["writes"] = 0
        
    def _hash_key(self, key: str) -> str:
        """Hash a key for storage"""
        return hashlib.md5(key.encode('utf-8')).hexdigest()
        
    def generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate a cache key from text and language pair"""
        # Normalize text to prevent near-duplicate cache entries
        normalized_text = re.sub(r'\s+', ' ', text.strip().lower())
        return f"{source_lang}:{target_lang}:{normalized_text}"
        
    def get_metrics(self):
        """Get cache metrics"""
        # Calculate hit rate
        total_requests = self.metrics["memory_hits"] + self.metrics["disk_hits"] + self.metrics["misses"]
        hit_rate = (self.metrics["memory_hits"] + self.metrics["disk_hits"]) / total_requests if total_requests > 0 else 0
        memory_hit_rate = self.metrics["memory_hits"] / total_requests if total_requests > 0 else 0
        
        # Create a copy of metrics to avoid modifying the original
        result_metrics = dict(self.metrics)
        
        # Add calculated metrics separately
        result_metrics["hit_rate"] = f"{hit_rate:.2%}"
        result_metrics["memory_hit_rate"] = f"{memory_hit_rate:.2%}"
        result_metrics["memory_usage_mb"] = f"{self.metrics['memory_bytes'] / (1024 * 1024):.2f} MB"
        
        return result_metrics

# --- Refactor SessionManager for persistent storage ---
class SessionManager:
    """
    Manages translation sessions and history.
    
    Nag-iimplement ito ng session management para sa translation requests,
    na nagbibigay-daan sa pag-track ng translation history at context.
    
    Gumagamit ito ng MemoryOrchestrator para sa persistent storage ng sessions,
    at may circuit breaker protection para sa mga failures.
    """
    def __init__(self, agent):
        self.agent = agent
        self.logger = agent.logger
        self.sessions = {}
        self.session_last_accessed = {}
        self.max_history = 100
        self.session_timeout = 3600
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 300
        self.connection_manager = agent.connection_manager

    def update_session(self, session_id: str, entry: Dict[str, Any] = None) -> None:
        if not session_id:
            return
        current_time = time.time()
        if session_id not in self.sessions:
            # Try to get session from MemoryOrchestrator
            cb = self.agent.circuit_breakers.get("MemoryOrchestrator")
            session_data = None
            
            if cb and cb.allow_request():
                try:
                    session_data = self._read_session_from_memory(session_id)
                    cb.record_success()
                except Exception as e:
                    cb.record_failure()
                    self.logger.warning(f"Failed to retrieve session from MemoryOrchestrator: {e}")
            
            if session_data:
                self.sessions[session_id] = session_data
                self.session_last_accessed[session_id] = current_time
            else:
                self.sessions[session_id] = {
                    'history': [],
                    'created_at': current_time,
                    'updated_at': current_time
                }
                
        if entry and session_id in self.sessions:
            if 'history' not in self.sessions[session_id]:
                self.sessions[session_id]['history'] = []
            self.sessions[session_id]['history'].append(entry)
            self.sessions[session_id]['updated_at'] = current_time
            
            # Trim history if it's too long
            if len(self.sessions[session_id]['history']) > self.max_history:
                self.sessions[session_id]['history'] = self.sessions[session_id]['history'][-self.max_history:]
                
            # Submit the task to thread pool for async execution
            self.agent.memory_executor.submit(self._persist_session_async, session_id, self.sessions[session_id])
                
        # Update access time
        self.session_last_accessed[session_id] = current_time

    def _read_session_from_memory(self, session_id):
        """Protected method to read session from memory orchestrator"""
        socket = self.connection_manager.get_socket("MemoryOrchestrator")
        if socket:
            session_key = f"translation_session:{session_id}"
            request = {
                "action": "read",
                "request_id": str(uuid.uuid4()),
                "payload": {"memory_id": session_key}
            }
            socket.send_json(request)
            
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            if poller.poll(5000):  # 5 second timeout
                response = socket.recv_json()
                if response.get("status") == "success":
                    memory_data = response.get("data", {}).get("memory", {})
                    if memory_data:
                        content = memory_data.get("content", {})
                        if content:
                            return content
        return None
    
    def _persist_session_async(self, session_id, session_data):
        """Asynchronously persist session to MemoryOrchestrator"""
        cb = self.agent.circuit_breakers.get("MemoryOrchestrator")
        if not cb or not cb.allow_request():
            self.logger.warning("Circuit open for MemoryOrchestrator, skipping session persistence")
            return
            
        try:
            socket = self.connection_manager.get_socket("MemoryOrchestrator")
            if socket:
                session_key = f"translation_session:{session_id}"
                request = {
                    "action": "upsert",
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_type": "translation_session",
                        "memory_id": session_key,
                        "content": session_data,
                        "tags": ["translation", "session"],
                        "ttl": self.session_timeout
                    }
                }
                socket.send_json(request)
                
                poller = zmq.Poller()
                poller.register(socket, zmq.POLLIN)
                
                if poller.poll(5000):  # 5 second timeout
                    socket.recv_json()
                    cb.record_success()
                else:
                    cb.record_failure()
                    self.logger.warning("Timeout persisting session to MemoryOrchestrator")
        except Exception as e:
            cb.record_failure()
            self.logger.error(f"Failed to update session in MemoryOrchestrator: {e}")
        
    def add_translation(self, session_id: str, result: Dict[str, Any]) -> None:
        """Add a translation result to a session's history."""
        if not session_id:
            return
            
        # Create entry with timestamp
        entry = {
            'translation': result.get('translation', ''),
            'source_lang': result.get('source_lang', 'unknown'),
            'target_lang': result.get('target_lang', 'unknown'),
            'engine_used': result.get('engine_used', 'unknown'),
            'text': result.get('text', ''),
            'timestamp': time.time()
        }
        
        # Update session
        self.update_session(session_id, entry)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get a session by ID."""
        if not session_id or session_id not in self.sessions:
            return {'history': []}
            
        # Update access time
        self.session_last_accessed[session_id] = time.time()
        return self.sessions[session_id]

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions periodically."""
        current_time = time.time()
        
        # Only run cleanup periodically
        if current_time - self.last_cleanup_time < self.cleanup_interval:
            return
            
        self.last_cleanup_time = current_time
        
        # Find expired sessions
        expired_sessions = []
        for session_id, last_accessed in self.session_last_accessed.items():
            if current_time - last_accessed > self.session_timeout:
                expired_sessions.append(session_id)
                
        # Remove expired sessions
        for session_id in expired_sessions:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.session_last_accessed:
                del self.session_last_accessed[session_id]
                
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired translation sessions")

# --- Move LocalPatternEngineClient and EmergencyWordEngineClient definitions before EngineManager ---
class LocalPatternEngineClient(BaseEngineClient):
    def __init__(self, agent, connection_manager=None):
        super().__init__(agent, engine_name='local_pattern', target_agent_name=None, connection_manager=connection_manager)
        self.patterns = COMMON_PHRASE_PATTERNS
        
    def translate(self, text, source_lang, target_lang):
        """Translate text using pattern matching (no ZMQ request needed)"""
        # Only handle Filipino/Tagalog to English or vice versa
        if not ((source_lang.startswith('tl') or source_lang.startswith('fil')) and target_lang.startswith('en')) and \
           not (source_lang.startswith('en') and (target_lang.startswith('tl') or target_lang.startswith('fil'))):
            return {
                'status': 'error',
                'message': 'Pattern matching only supports Filipino <-> English translation'
            }
            
        try:
            # Check for pattern matches
            text_lower = text.lower()
            for pattern, template in self.patterns.items():
                match = re.match(pattern, text_lower)
                if match:
                    groups = match.groups()
                    if len(groups) > 1:
                        translated = template.format(*groups[1:])
                    else:
                        translated = template
                        
                    return {
                        'status': 'success',
                        'translation': translated,
                        'engine_used': 'local_pattern',
                        'confidence': 0.8
                    }
            return {
                'status': 'error',
                'message': 'No pattern match found'
            }
        except Exception as e:
            self.logger.error(f"Pattern matching error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Pattern matching error: {str(e)}',
                'engine_used': 'local_pattern'
            }

class EmergencyWordEngineClient(BaseEngineClient):
    def __init__(self, agent, connection_manager=None):
        super().__init__(agent, engine_name='emergency_word', target_agent_name=None, connection_manager=connection_manager)
        self.dictionary = COMMAND_TRANSLATIONS
        
    def translate(self, text, source_lang, target_lang):
        """Emergency word-by-word translation (last resort)"""
        try:
            # Only support Filipino to English or English to Filipino
            if not ((source_lang.startswith('tl') or source_lang.startswith('fil')) and target_lang.startswith('en')) and \
               not (source_lang.startswith('en') and (target_lang.startswith('tl') or target_lang.startswith('fil'))):
                return {
                    'status': 'error',
                    'message': 'Emergency translation only supports Filipino <-> English'
                }
                
            # Split text into words
            words = text.lower().split()
            translated_words = []
            
            # Translate word by word
            for word in words:
                # Check dictionary
                if word in self.dictionary:
                    translated_words.append(self.dictionary[word])
                else:
                    # Keep original if not found
                    translated_words.append(word)
            
            translated_text = " ".join(translated_words)
            
            return {
                'status': 'success',
                'translation': translated_text,
                'engine_used': 'emergency_word',
                'confidence': 0.5
            }
                
        except Exception as e:
            self.logger.error(f"Emergency translation error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Emergency translation error: {str(e)}',
                'engine_used': 'emergency_word'
            }

# --- In EngineManager, ensure LocalPatternEngineClient and EmergencyWordEngineClient are defined before use ---
class EngineManager:
    """
    Manages translation engines and implements the fallback chain.
    
    Ito ang central component na namamahala sa lahat ng translation engines
    at nagpapatupad ng fallback chain kapag may failures sa translation.
    
    Fallback order:
    1. Dictionary (local)
    2. NLLB (neural machine translation)
    3. Streaming (real-time translation)
    4. Google Remote (external API)
    5. Local Pattern (pattern matching)
    6. Emergency Word (word-by-word translation)
    """
    def __init__(self, agent, connection_manager=None, timeout_manager=None):
        self.agent = agent
        self.logger = agent.logger
        self.engines = {}
        self.connection_manager = connection_manager or agent.connection_manager
        self.timeout_manager = timeout_manager or AdvancedTimeoutManager()
        
        # Initialize engines
        self.engines['dictionary'] = DictionaryEngineClient(agent)
        self.engines['nllb'] = NLLBEngineClient(agent, connection_manager=self.connection_manager)
        self.engines['streaming'] = StreamingEngineClient(agent, connection_manager=self.connection_manager)
        self.engines['google_remote'] = RemoteGoogleEngineClient(agent, connection_manager=self.connection_manager)
        self.engines['local_pattern'] = LocalPatternEngineClient(agent, connection_manager=self.connection_manager)
        self.engines['emergency_word'] = EmergencyWordEngineClient(agent, connection_manager=self.connection_manager)
        self.fallback_order = ['dictionary', 'nllb', 'streaming', 'google_remote', 'local_pattern', 'emergency_word']
        self.logger.info(f"Engine Manager initialized with fallback order: {self.fallback_order}")
        
    def translate(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using the configured engines with fallback."""
        start_time = time.time()
        
        # Try each engine in fallback order
        for engine_name in self.fallback_order:
            self.logger.info(f"Attempting translation with engine: {engine_name}")
            engine = self.engines.get(engine_name)
            if engine is None:
                self.logger.error(f"Engine '{engine_name}' is not configured in EngineManager.")
                continue
            
            try:
                response = engine.translate(text, source_lang, target_lang)
                
                # Check if translation was successful
                if response and response.get('status') == 'success':
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Translation successful using {engine_name} in {elapsed_time:.2f}s")
                    
                    # Add engine info to response
                    response['engine_used'] = engine_name
                    response['translation_time'] = elapsed_time
                    
                    return response
                    
            except Exception as e:
                self.logger.error(f"Error using {engine_name} engine: {e}")
                
        # If all engines failed
        self.logger.error("All translation engines failed")
        return {
            'status': 'error',
            'message': 'All translation engines failed',
            'engine_used': None,
            'translation': None
        }

class TranslationService(BaseAgent):
    """
    Unified translation service that orchestrates all translation requests and fallback logic.
    
    Ito ang central translation service na sumusunod sa Phase4 architecture plan.
    Pinagsasama nito ang lahat ng translation-related features sa isang
    modular, robust, at fault-tolerant na service.
    
    Key features:
    - Modular architecture (language detection, caching, engines, sessions)
    - Circuit breaker pattern para sa fault tolerance
    - Persistent caching at session management
    - Sophisticated fallback mechanisms
    - Advanced language detection, lalo na para sa Taglish
    """
    def __init__(self):
        """Initialize the Translation Service agent."""
        # Set required properties before calling super().__init__
        self.name = "TranslationService"
        self.port = 5595  # Default port
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=self.name, port=self.port)
        
        # Check if secure ZMQ is enabled
        self.secure_zmq = is_secure_zmq_enabled()
        
        # Initialize thread pool for asynchronous memory operations
        self.memory_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix='PC2MemoryWriter')
        
        # Initialize connection manager first
        self.connection_manager = ConnectionManager(self)
        
        # Initialize circuit breakers for downstream services
        self.downstream_services = ["MemoryOrchestrator", "NLLBAdapter", "RemoteConnectorAgent"]
        self.circuit_breakers = {}
        self._init_circuit_breakers()
        
        # Initialize modular components
        self.timeout_manager = AdvancedTimeoutManager()
        self.language_detector = LanguageDetector(self)
        self.cache = TranslationCache(self)
        self.session_manager = SessionManager(self)
        self.engine_manager = EngineManager(self, timeout_manager=self.timeout_manager)
        
        # Initialize state
        self.running = True
        
        # Set up ZMQ socket
        self._setup_sockets()
        
        # Register with digital twin
        self._register_with_digital_twin()
        
        self.logger.info("Translation Service initialized")
        
    def _init_circuit_breakers(self):
        """
        Initialize circuit breakers for all connected services
        Circuit breakers prevent cascading failures by stopping requests to failing services
        """
        self.circuit_breakers = {}
        
        # Circuit breaker for main services
        main_services = [
            "NLLBEngine", 
            "GoogleTranslateEngine",
            "StreamingEngine",
            "TagaBERTaService",
            "LanguageDetector",
            "EmergencyWordEngine"
        ]
        
        # Create circuit breakers for all services with different thresholds
        for service in main_services:
            # Critical services need more sensitive circuit breakers
            if service in ["NLLBEngine", "GoogleTranslateEngine"]:
                # More sensitive thresholds for critical services
                self.circuit_breakers[service] = CircuitBreaker(
                    name=service,
                    failure_threshold=3,  # Break after 3 failures
                    reset_timeout=60,     # Wait 60 seconds before retrying
                    half_open_timeout=10  # Allow one test request after 10 seconds
                )
            else:
                # Standard thresholds for other services
                self.circuit_breakers[service] = CircuitBreaker(
                    name=service,
                    failure_threshold=5,  # Break after 5 failures
                    reset_timeout=30,     # Wait 30 seconds before retrying
                    half_open_timeout=5   # Allow one test request after 5 seconds
                )
        
        # Log circuit breakers initialization
        self.logger.info(f"Initialized {len(self.circuit_breakers)} circuit breakers for translation services")
        
    def _get_fallback_translation(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """
        Provide fallback translation when primary methods fail
        Uses multiple layers of fallback:
        1. Dictionary-based translation for common words/phrases
        2. Pattern-based simple translation for basic sentences
        3. Emergency word-by-word translation for last resort
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Dictionary with translation result or error
        """
        self.logger.warning(f"Using fallback translation for {text[:30]}...")
        
        # Check if we have a circuit breaker for DictionaryEngine
        dict_cb = self.circuit_breakers.get("EmergencyWordEngine")
        if dict_cb and not dict_cb.allow_request():
            # Even the emergency engine is failing, return an error
            self.logger.error("All translation engines have failed including fallbacks")
            return {
                "status": "error",
                "message": "All translation engines have failed",
                "translation": None,
                "engine": "none"
            }
            
        try:
            # Try dictionary-based translation first (for common phrases)
            for engine_client in [self.engine_manager.local_pattern_engine, self.engine_manager.emergency_word_engine]:
                if engine_client:
                    try:
                        # Apply the translation
                        result = engine_client.translate(text, source_lang, target_lang)
                        
                        if result.get("status") == "success" and result.get("translation"):
                            # Update the circuit breaker
                            if dict_cb:
                                dict_cb.record_success()
                                
                            return {
                                "status": "success",
                                "message": "Fallback translation completed",
                                "translation": result.get("translation"),
                                "engine": "fallback",
                                "quality": "low",
                                "fallback_used": True
                            }
                    except Exception as e:
                        self.logger.error(f"Error in fallback translation: {e}")
                        if dict_cb:
                            dict_cb.record_failure()
            
            # If we get here, all fallbacks failed
            return {
                "status": "error",
                "message": "All translation engines have failed",
                "translation": None,
                "engine": "none"
            }
        except Exception as e:
            if dict_cb:
                dict_cb.record_failure()
            self.logger.error(f"Error in _get_fallback_translation: {e}")
            return {
                "status": "error", 
                "message": f"Fallback translation error: {str(e)}",
                "translation": None,
                "engine": "none"
            }
    
    def _resilient_send_request(self, agent_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A resilient method to send requests using Circuit Breakers."""
        cb = self.circuit_breakers.get(agent_name)
        if not cb or not cb.allow_request():
            self.logger.warning(f"Request to {agent_name} blocked by open circuit or missing CB.")
            return None
        try:
            response = self.send_request_to_agent(agent_name, request, timeout=15000)  # 15 second timeout
            cb.record_success()
            return response
        except Exception as e:
            cb.record_failure()
            self.logger.error(f"Failed to communicate with {agent_name}: {e}")
            return None
    
    def send_request_to_agent(self, agent_name: str, request: Dict[str, Any], timeout: int = 5000) -> Optional[Dict[str, Any]]:
        """Send a request to another agent using ZMQ REQ socket.
        
        Args:
            agent_name: Name of the target agent
            request: Request payload
            timeout: Request timeout in milliseconds
            
        Returns:
            Response from the agent or None if request failed
        """
        socket = self.connection_manager.get_socket(agent_name)
        if not socket:
            self.logger.error(f"Failed to get socket for {agent_name}")
            return None
            
        try:
            # Send request
            socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            if poller.poll(timeout):
                response = socket.recv_json()
                return response
            else:
                self.logger.error(f"Timeout waiting for response from {agent_name}")
                self.connection_manager.reset_socket(agent_name)
                return None
        except Exception as e:
            self.logger.error(f"Error communicating with {agent_name}: {e}")
            self.connection_manager.reset_socket(agent_name)
            return None
    
    def _setup_sockets(self):
        """Set up ZMQ sockets with CurveZMQ security if enabled."""
        self.socket = get_rep_socket(self.endpoint).socket
        
        # Apply CurveZMQ security if enabled
        if self.secure_zmq:
            self.logger.info("Applying CurveZMQ security to main socket")
            configure_secure_server(self.socket)
            
        self.socket.bind(f"tcp://*:{self.port}")
        self.logger.info(f"Translation Service bound to port {self.port}")
        
    def _register_with_digital_twin(self):
        """Register this agent with the SystemDigitalTwin."""
        try:
            # This is handled by BaseAgent, but we log it for clarity
            self.logger.info("Registered with SystemDigitalTwin")
        except Exception as e:
            self.logger.error(f"Failed to register with SystemDigitalTwin: {e}")
            
    def run(self):
        """Main processing loop."""
        self.logger.info("Translation Service running")
        
        while self.running:
            try:
                # Wait for request
                self.logger.info("Waiting for translation request...")
                msg = self.socket.recv_json()
                self.logger.info(f"Received request: {msg}")
                if not isinstance(msg, dict):
                    raise ValueError("Malformed request: expected a JSON object (dict)")
                
                text = msg.get("text")
                target_lang = msg.get("target_lang")
                session_id = msg.get("session_id")
                source_lang = msg.get("source_lang")

                # Ensure required fields are present and are strings
                if not isinstance(text, str) or not isinstance(target_lang, str):
                    raise ValueError("Request must include 'text' and 'target_lang' as strings.")
                if source_lang is not None and not isinstance(source_lang, str):
                    source_lang = str(source_lang)
                if session_id is not None and not isinstance(session_id, str):
                    session_id = str(session_id)
                
                # Process request
                response = self._process_translation(text, target_lang, source_lang, session_id)
                
                # Send response
                self.socket.send_json(response)
                
                # Clean up expired sessions periodically
                self.session_manager.cleanup_expired_sessions()
                
            except ValueError as e:
                # Handle validation errors
                self.logger.error(f"Validation error: {e}")
                self.socket.send_json({
                    "status": "error",
                    "message": str(e)
                })
            except Exception as e:
                # Handle unexpected errors
                self.logger.error(f"Error processing request: {e}")
                self.socket.send_json({
                    "status": "error",
                    "message": f"Internal server error: {str(e)}"
                })
                
    def _process_translation(self, text: str, target_lang: str, source_lang: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Process a translation request with enhanced error handling, caching, and fallbacks.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code (optional)
            session_id: Session identifier (optional)
            
        Returns:
            Dictionary with translation result
        """
        start_time = time.time()
        
        try:
            # Input validation
            if not text or not text.strip():
                error_result = {
                    "status": "error",
                    "message": "Empty text provided",
                    "translation": None,
                    "engine": None
                }
                self._update_metrics(start_time, error_result, text, source_lang, target_lang)
                return error_result
                
            if not target_lang:
                error_result = {
                    "status": "error",
                    "message": "Target language not specified",
                    "translation": None,
                    "engine": None
                }
                self._update_metrics(start_time, error_result, text, source_lang, target_lang)
                return error_result
                
            # Text preprocessing - normalize whitespace
            text = text.strip()
                
            # Detect source language if not provided
            if not source_lang:
                try:
                    source_lang = self.language_detector.detect_language(text)
                    self.logger.info(f"Detected language: {source_lang}")
                except Exception as e:
                    self.logger.error(f"Language detection failed: {e}")
                    source_lang = "en"  # Default to English
                    
            # Check if the translation is necessary
            if source_lang == target_lang:
                result = {
                    "status": "success",
                    "message": "No translation needed (same languages)",
                    "translation": text,
                    "engine": "none",
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                }
                self._update_metrics(start_time, result, text, source_lang, target_lang)
                return result
                
            # Check cache first
            cache_key = self.translation_cache.generate_key(text, source_lang, target_lang)
            cached_translation = self.translation_cache.get(cache_key)
            
            if cached_translation:
                self.logger.info(f"Cache hit for {source_lang}->{target_lang}")
                result = {
                    "status": "success",
                    "message": "Translation retrieved from cache",
                    "translation": cached_translation,
                    "engine": "cache",
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "cached": True
                }
                self._update_metrics(start_time, result, text, source_lang, target_lang)
                return result
                
            # Not in cache, perform translation
            try:
                # Use the engine manager to select the best engine and perform translation
                translation_result = self.engine_manager.translate(text, source_lang, target_lang)
                
                # Handle successful translation
                if translation_result.get("status") == "success" and translation_result.get("translation"):
                    # Cache the successful translation
                    self.translation_cache.set(cache_key, translation_result["translation"])
                    
                    # Update session history if session_id provided
                    if session_id:
                        self.session_manager.add_translation(session_id, {
                            "original_text": text,
                            "translated_text": translation_result["translation"],
                            "source_lang": source_lang,
                            "target_lang": target_lang,
                            "engine": translation_result.get("engine", "unknown"),
                            "timestamp": time.time()
                        })
                        
                    # Update metrics and return result
                    self._update_metrics(start_time, translation_result, text, source_lang, target_lang)
                    return translation_result
                else:
                    # Translation failed, try fallback
                    self.logger.warning(f"Primary translation failed: {translation_result.get('message')}")
                    fallback_result = self._get_fallback_translation(text, source_lang, target_lang)
                    
                    # If fallback succeeded, cache the result
                    if fallback_result.get("status") == "success" and fallback_result.get("translation"):
                        self.translation_cache.set(cache_key, fallback_result["translation"])
                        
                        # Update session history if session_id provided
                        if session_id:
                            self.session_manager.add_translation(session_id, {
                                "original_text": text,
                                "translated_text": fallback_result["translation"],
                                "source_lang": source_lang,
                                "target_lang": target_lang,
                                "engine": "fallback",
                                "timestamp": time.time()
                            })
                    
                    # Update metrics and return fallback result
                    self._update_metrics(start_time, fallback_result, text, source_lang, target_lang)
                    return fallback_result
                    
            except Exception as e:
                self.logger.error(f"Translation failed with error: {e}")
                fallback_result = self._get_fallback_translation(text, source_lang, target_lang)
                self._update_metrics(start_time, fallback_result, text, source_lang, target_lang)
                return fallback_result
                
        except Exception as e:
            # Unexpected error in translation process
            error_message = f"Unexpected error in translation process: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            
            # Try emergency fallback as a last resort
            try:
                emergency_result = self._get_fallback_translation(text, source_lang or "en", target_lang)
                self._update_metrics(start_time, emergency_result, text, source_lang, target_lang)
                return emergency_result
            except:
                # All translation options have failed
                error_result = {
                    "status": "error",
                    "message": error_message,
                    "translation": None,
                    "engine": "none"
                }
                self._update_metrics(start_time, error_result, text, source_lang, target_lang)
                return error_result
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            # Clean up engine clients
            for engine_name, engine in self.engine_manager.engines.items():
                if hasattr(engine, 'cleanup'):
                    try:
                        engine.cleanup()
                    except Exception as e:
                        self.logger.error(f"Error cleaning up engine {engine_name}: {e}")
            
            # Clean up connections managed by ConnectionManager
            if hasattr(self, 'connection_manager') and self.connection_manager:
                try:
                    self.connection_manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up connection manager: {e}")
            
            # Ensure all pending memory writes are completed
            if hasattr(self, 'memory_executor'):
                try:
                    self.logger.info("Shutting down memory executor thread pool...")
                    self.memory_executor.shutdown(wait=True)
                    self.logger.info("Memory executor thread pool shutdown complete.")
                except Exception as e:
                    self.logger.error(f"Error shutting down memory executor: {e}")
                        
            self.running = False
            self.logger.info("Translation Service stopped")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            
    def _report_error(self, error_message: str, error_type: str, severity: ErrorSeverity, **additional_data):
        """
        Report an error to the error bus.
        
        Ito ang method para sa pag-report ng errors sa distributed error bus
        na sumusunod sa Phase3 error management architecture.
        
        Args:
            error_message: Human-readable error message
            error_type: Type of error (e.g., "translation_failure")
            severity: Error severity level from ErrorSeverity enum
            **additional_data: Additional context data about the error
        """
        try:
            # Check if UnifiedErrorAgent is in the circuit breakers
            if "UnifiedErrorAgent" not in self.circuit_breakers:
                self.circuit_breakers["UnifiedErrorAgent"] = CircuitBreaker(name="UnifiedErrorAgent")
            
            cb = self.circuit_breakers.get("UnifiedErrorAgent")
            if not cb or not cb.allow_request():
                self.logger.warning("Circuit open for UnifiedErrorAgent, skipping error report")
                return
                
            error_data = {
                "agent": self.name,
                "timestamp": time.time(),
                "error_type": error_type,
                "message": error_message,
                "severity": severity.value,
                "context": additional_data
            }
            
            # Try to send error to UnifiedErrorAgent
            socket = self.connection_manager.get_socket("UnifiedErrorAgent")
            if socket:
                socket.send_json({
                    "action": "report_error",
                    "error_data": error_data
                })
                
                poller = zmq.Poller()
                poller.register(socket, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    response = socket.recv_json()
                    if response.get("status") == "success":
                        cb.record_success()
                    else:
                        cb.record_failure()
                else:
                    cb.record_failure()
                    self.logger.warning("Timeout reporting error to UnifiedErrorAgent")
            else:
                self.logger.warning("Could not get socket for UnifiedErrorAgent")
        except Exception as e:
            self.logger.error(f"Failed to report error: {e}")
            if cb:
                cb.record_failure()
    
    def _get_health_status(self):
        """
        Get detailed health status and metrics for the TranslationService
        
        Returns:
            Dict with health status and detailed metrics
        """
        base_health = super()._get_health_status()
        
        try:
            # Calculate uptime
            uptime_seconds = time.time() - self.start_time
            uptime_str = f"{int(uptime_seconds // 86400)}d {int((uptime_seconds % 86400) // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"
            
            # Get circuit breaker status
            circuit_status = {}
            for name, cb in self.circuit_breakers.items():
                circuit_status[name] = cb.get_status()
            
            # Get cache metrics
            cache_metrics = {}
            if hasattr(self, 'translation_cache') and self.translation_cache:
                cache_metrics = self.translation_cache.get_metrics()
            
            # Get engine usage metrics
            if hasattr(self, 'engine_manager') and self.engine_manager and hasattr(self.engine_manager, 'metrics'):
                engine_metrics = self.engine_manager.metrics
            else:
                engine_metrics = {}
                
            # Compile all metrics
            detailed_metrics = {
                "uptime": uptime_str,
                "total_requests": self.metrics.get("total_requests", 0),
                "successful_translations": self.metrics.get("successful_translations", 0),
                "failed_translations": self.metrics.get("failed_translations", 0),
                "average_latency_ms": self.metrics.get("average_latency_ms", 0),
                "success_rate": f"{(self.metrics.get('successful_translations', 0) / max(1, self.metrics.get('total_requests', 1))) * 100:.1f}%",
                "fallback_used_count": self.metrics.get("fallback_used", 0),
                "language_distribution": self.metrics.get("language_distribution", {}),
                "engine_usage": engine_metrics.get("engine_usage", {}),
                "circuit_breakers": circuit_status,
                "cache": cache_metrics,
                "last_error": self.metrics.get("last_error", "None")
            }
            
            # Add detailed metrics to base health status
            base_health["metrics"] = detailed_metrics
            
            # Update overall status based on circuit breaker states
            open_circuits = [name for name, status in circuit_status.items() if status.get("state") == "open"]
            if open_circuits:
                base_health["status"] = "degraded"
                base_health["warnings"] = [f"Circuit open for: {', '.join(open_circuits)}"]
                
            return base_health
            
        except Exception as e:
            self.logger.error(f"Error generating health status: {e}")
            base_health["status"] = "warning"
            base_health["warnings"] = [f"Error generating detailed health metrics: {str(e)}"]
            return base_health
            
    def _update_metrics(self, start_time, result, text, source_lang, target_lang):
        """
        Update metrics after a translation operation
        
        Args:
            start_time: Time when translation started
            result: Translation result
            text: Original text
            source_lang: Source language code
            target_lang: Target language code
        """
        # Calculate processing time
        processing_time = time.time() - start_time
        processing_time_ms = int(processing_time * 1000)
        
        # Initialize metrics if needed
        if not hasattr(self, 'metrics'):
            self.metrics = {
                "total_requests": 0,
                "successful_translations": 0,
                "failed_translations": 0,
                "total_latency_ms": 0,
                "average_latency_ms": 0,
                "fallback_used": 0,
                "language_distribution": {},
                "last_error": None,
                "last_request_time": time.time()
            }
            
        # Update request count
        self.metrics["total_requests"] = self.metrics.get("total_requests", 0) + 1
        
        # Update language distribution
        lang_pair = f"{source_lang}->{target_lang}"
        if "language_distribution" not in self.metrics:
            self.metrics["language_distribution"] = {}
        if lang_pair not in self.metrics["language_distribution"]:
            self.metrics["language_distribution"][lang_pair] = 0
        self.metrics["language_distribution"][lang_pair] += 1
        
        # Update success/failure metrics
        if result.get("status") == "success":
            self.metrics["successful_translations"] = self.metrics.get("successful_translations", 0) + 1
            
            # Update latency metrics
            self.metrics["total_latency_ms"] = self.metrics.get("total_latency_ms", 0) + processing_time_ms
            self.metrics["average_latency_ms"] = self.metrics["total_latency_ms"] / self.metrics["successful_translations"]
            
            # Check if fallback was used
            if result.get("fallback_used"):
                self.metrics["fallback_used"] = self.metrics.get("fallback_used", 0) + 1
        else:
            self.metrics["failed_translations"] = self.metrics.get("failed_translations", 0) + 1
            self.metrics["last_error"] = result.get("message", "Unknown error")
            
        # Update last request time
        self.metrics["last_request_time"] = time.time()

# Add standardized __main__ block
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = TranslationService()
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