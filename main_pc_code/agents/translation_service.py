import logging
import zmq
import time
import uuid
import json
import re
import os
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pybreaker
from common.core.base_agent import BaseAgent
from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server

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
    """Centralized manager for all ZMQ socket connections to external services."""
    
    def __init__(self, agent):
        """Initialize the connection manager.
        
        Args:
            agent: The parent agent instance
        """
        self.agent = agent
        self.logger = agent.logger
        self.context = agent.context
        self.sockets = {}  # Dictionary to hold all active sockets
        self.secure_zmq = is_secure_zmq_enabled()
        self.logger.info("ConnectionManager initialized")
    
    def _create_socket(self, service_name):
        """Create a ZMQ socket for a given service.
        
        Args:
            service_name: The name of the service to connect to
            
        Returns:
            The connected socket or None if connection failed
        """
        try:
            # Discover the service's address
            agent_info = self.agent.discover_agent(service_name)
            if not agent_info:
                self.logger.error(f"Could not discover {service_name}.")
                return None
                
            port = agent_info['port']
            # Determine target IP based on service
            target_ip = "localhost"
            if service_name == "RemoteConnectorAgent":
                target_ip = self.agent.get_config("pc2_ip", "localhost")
                
            # Create socket
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5-second timeout
            
            # Apply CurveZMQ security if enabled
            if self.secure_zmq:
                self.logger.info(f"Applying CurveZMQ security to {service_name} socket")
                configure_secure_client(socket)
            
            # Connect socket
            socket.connect(f"tcp://{target_ip}:{port}")
            self.logger.info(f"Connected to {service_name} at {target_ip}:{port}")
            return socket
        
        except Exception as e:
            self.logger.error(f"Failed to initialize socket for {service_name}: {e}")
            return None
    
    def get_socket(self, service_name):
        """Get a socket for a given service, creating it if it doesn't exist.
        
        Args:
            service_name: The name of the service to connect to
            
        Returns:
            The connected socket or None if connection failed
        """
        if not service_name:
            return None
            
        # Return existing socket if it exists
        if service_name in self.sockets:
            return self.sockets[service_name]
            
        # Create new socket
        socket = self._create_socket(service_name)
        if socket:
            self.sockets[service_name] = socket
        return socket
    
    def reset_socket(self, service_name):
        """Reset a socket connection after an error or timeout.
        
        Args:
            service_name: The name of the service to reset
        """
        try:
            if service_name in self.sockets:
                self.sockets[service_name].close()
                del self.sockets[service_name]
            self.logger.info(f"Socket for {service_name} has been reset")
        except Exception as e:
            self.logger.error(f"Error resetting socket for {service_name}: {e}")
    
    def cleanup(self):
        """Close all sockets and clean up resources."""
        for service_name, socket in list(self.sockets.items()):
            try:
                socket.close()
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
            # Get socket from connection manager
            socket = self.connection_manager.get_socket(self.target_agent_name)
            if not socket:
                self.logger.error(f"Failed to get socket for {self.target_agent_name}")
                return None
                
            text = payload.get('text', '')
            timeout = self.timeout_manager.calculate_timeout(text)
            self.logger.info(f"Sending request to {self.target_agent_name} with timeout {timeout} ms: {payload}")
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
    def __init__(self, agent):
        self.agent = agent
        self.logger = agent.logger
        self.cache = {}
        self.timestamps = {}
        self.max_size = 1000
        self.ttl = 3600
        self.connection_manager = agent.connection_manager
        # Initialize circuit breaker for memory reads
        self.mem_read_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)

    @pybreaker.CircuitBreakerError
    def get(self, key: str) -> Optional[str]:
        hashed_key = self._hash_key(key)
        if hashed_key in self.cache:
            if time.time() - self.timestamps[hashed_key] > self.ttl:
                del self.cache[hashed_key]
                del self.timestamps[hashed_key]
                return None
            return self.cache[hashed_key]
        
        # Not in local cache, try MemoryOrchestrator
        try:
            # Use circuit breaker to protect against remote service failures
            return self.mem_read_breaker.call(self._read_from_memory, hashed_key)
        except pybreaker.CircuitBreakerError:
            self.logger.warning("Circuit open for MemoryOrchestrator, skipping read.")
            return None
        except Exception as e:
            self.logger.error(f"Error getting translation from MemoryOrchestrator: {e}")
            return None
    
    def _read_from_memory(self, hashed_key):
        """Protected method to read from memory orchestrator"""
        socket = self.connection_manager.get_socket("MemoryOrchestrator")
        if socket:
            cache_key = f"translation_cache:{hashed_key}"
            request = {
                "action": "read",
                "request_id": str(uuid.uuid4()),
                "payload": {"memory_id": cache_key}
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
                        value = content.get("value")
                        created_at = memory_data.get("created_at")
                        if created_at and (time.time() - created_at <= self.ttl):
                            self.cache[hashed_key] = value
                            self.timestamps[hashed_key] = created_at
                            return value
        return None

    def set(self, key: str, value: str):
        hashed_key = self._hash_key(key)
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        self.cache[hashed_key] = value
        self.timestamps[hashed_key] = time.time()
        
        # Submit the task to thread pool for async execution
        self.agent.memory_executor.submit(self._persist_entry_async, hashed_key, value)
    
    def _persist_entry_async(self, hashed_key, value):
        """Asynchronously persist cache entry to MemoryOrchestrator"""
        try:
            socket = self.connection_manager.get_socket("MemoryOrchestrator")
            if socket:
                cache_key = f"translation_cache:{hashed_key}"
                content = {"value": value}
                request = {
                    "action": "create",
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_type": "translation_cache",
                        "memory_id": cache_key,
                        "content": content,
                        "tags": ["translation"],
                        "ttl": self.ttl
                    }
                }
                socket.send_json(request)
                
                poller = zmq.Poller()
                poller.register(socket, zmq.POLLIN)
                
                if poller.poll(5000):  # 5 second timeout
                    socket.recv_json()
        except Exception as e:
            self.logger.error(f"Error storing translation in MemoryOrchestrator: {e}")

    def clear(self):
        """Clear the cache."""
        self.cache = {}
        self.timestamps = {}
        self.logger.info("Translation cache cleared")
    
    def _hash_key(self, key: str) -> str:
        """Hash a cache key using SHA-256."""
        return hashlib.sha256(key.encode('utf-8')).hexdigest()
        
    def generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate a unique cache key for a translation request."""
        return f"{text}:{source_lang}:{target_lang}"

# --- Refactor SessionManager for persistent storage ---
class SessionManager:
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
        # Initialize circuit breaker for memory reads
        self.mem_read_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)

    def update_session(self, session_id: str, entry: Dict[str, Any] = None) -> None:
        if not session_id:
            return
        current_time = time.time()
        if session_id not in self.sessions:
            # Try to get session from MemoryOrchestrator
            try:
                # Use circuit breaker to protect against remote service failures
                session_data = self.mem_read_breaker.call(self._read_session_from_memory, session_id)
                if session_data:
                    self.sessions[session_id] = session_data
                    self.session_last_accessed[session_id] = current_time
                else:
                    self.sessions[session_id] = {
                        'history': [],
                        'created_at': current_time,
                        'updated_at': current_time
                    }
            except pybreaker.CircuitBreakerError:
                self.logger.warning("Circuit open for MemoryOrchestrator, skipping session read.")
                self.sessions[session_id] = {
                    'history': [],
                    'created_at': current_time,
                    'updated_at': current_time
                }
            except Exception as e:
                self.logger.warning(f"Failed to retrieve session from MemoryOrchestrator: {e}")
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
        except Exception as e:
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
    """Manages translation engines and implements the fallback chain."""
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
    """Unified translation service that orchestrates all translation requests and fallback logic."""
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
        
    def _setup_sockets(self):
        """Set up ZMQ sockets with CurveZMQ security if enabled."""
        self.socket = self.context.socket(zmq.REP)
        
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
        """Process a translation request."""
        try:
            # Check cache first
            cache_key = self.cache.generate_key(text, source_lang or "auto", target_lang)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info("Cache hit for translation request")
                result = {
                    "status": "success",
                    "translation": cached_result,
                    "engine_used": "cache",
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "text": text
                }
                
                # Add to session history if session_id provided
                if session_id:
                    self.session_manager.add_translation(session_id, result)
                    
                return result
            
            # Detect language if not provided
            if not source_lang or source_lang == "auto":
                self.logger.info("Detecting language...")
                source_lang = self.language_detector.detect_language(text)
                self.logger.info(f"Detected language: {source_lang}")
            
            # Skip translation if source and target languages are the same
            if source_lang == target_lang:
                self.logger.info("Source and target languages are the same, skipping translation")
                result = {
                    "status": "success",
                    "translation": text,
                    "engine_used": "none",
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "text": text
                }
                
                # Add to session history if session_id provided
                if session_id:
                    self.session_manager.add_translation(session_id, result)
                    
                return result
            
            # Translate
            self.logger.info(f"Translating from {source_lang} to {target_lang}...")
            translation_result = self.engine_manager.translate(text, source_lang, target_lang)
            
            # Process result
            if translation_result.get("status") == "success":
                # Cache successful translation
                self.cache.set(cache_key, translation_result.get("translation"))
                
                # Create result
                result = {
                    "status": "success",
                    "translation": translation_result.get("translation"),
                    "engine_used": translation_result.get("engine_used"),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "text": text
                }
                
                # Add to session history if session_id provided
                if session_id:
                    self.session_manager.add_translation(session_id, result)
                    
                return result
            else:
                # Translation failed
                return {
                    "status": "error",
                    "message": translation_result.get("message", "Translation failed"),
                    "engine_used": translation_result.get("engine_used"),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "text": text
                }
                
        except Exception as e:
            self.logger.error(f"Error processing translation: {e}")
            return {
                "status": "error",
                "message": f"Translation processing error: {str(e)}",
                "source_lang": source_lang,
                "target_lang": target_lang,
                "text": text
            }
    
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
            
    def _get_health_status(self):
        """Get the current health status of the agent."""
        # Get the base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health metrics
        try:
            # Add metrics to base status
            base_status.update({
                "agent_specific_metrics": {
                    "language_detector": {
                        "langdetect_available": self.language_detector.has_langdetect,
                        "fasttext_available": self.language_detector.has_fasttext,
                        "tagabert_available": self.language_detector.tagabert_available
                    },
                    "cache": {
                        "size": len(self.cache.cache),
                        "max_size": self.cache.max_size
                    },
                    "session_manager": {
                        "active_sessions": len(self.session_manager.sessions)
                    },
                    "engine_manager": {
                        "engines": list(self.engine_manager.engines.keys()),
                        "fallback_order": self.engine_manager.fallback_order
                    }
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error collecting health metrics: {e}")
            base_status.update({"health_metrics_error": str(e)})
        
        return base_status

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