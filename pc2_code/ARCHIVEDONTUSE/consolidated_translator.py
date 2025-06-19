#!/usr/bin/env python3
"""
Consolidated Primary Translator
- Combines best features from all translator implementations
- Multi-level translation pipeline with fallbacks
- Advanced caching and session management
- Comprehensive error handling and logging
"""
import os
import sys
from pathlib import Path

# Add parent directory to path BEFORE any other imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import time
import zmq
import uuid
import random
import pickle
import logging
import re
import requests
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from collections import deque
from config.system_config import get_config_for_service

# Configure logging
LOG_LEVEL = 'INFO'
LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOGS_DIR / "consolidated_translator.log"

# Enhanced logging format with more details
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ConsolidatedTranslator")

# Constants
ZMQ_PORT = 5563
ZMQ_BIND_ADDRESS = "0.0.0.0"
MAX_SESSION_HISTORY = 10
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

# Configuration
TRANSLATOR_CONFIG = {
    "engines": {
        "dictionary": {
            "enabled": True,
            "priority": 1,
            "confidence_threshold": 0.98
        },
        "nllb": {
            "enabled": True,
            "priority": 2,
            "confidence_threshold": 0.85,
            "model": "facebook/nllb-200-distilled-600M",
            "timeout": 30,
            "port": 5581
        },
        "phi": {
            "enabled": True,
            "priority": 3,
            "confidence_threshold": 0.75,
            "timeout": 3,
            "port": 11434
        },
        "google": {
            "enabled": True,
            "priority": 4,
            "confidence_threshold": 0.90,
            "rca_port": 5557
        }
    },
    "cache": {
        "enabled": True,
        "max_size": 1000,
        "ttl": 3600
    },
    "session": {
        "enabled": True,
        "max_history": 10,
        "timeout": 3600
    }
}

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

# Add startup logging
logger.info("=" * 80)
logger.info("Starting Consolidated Translator Service")
logger.info(f"Log file: {log_file_path}")
logger.info(f"ZMQ Port: {ZMQ_PORT}")
logger.info(f"Bind Address: {ZMQ_BIND_ADDRESS}")
logger.info("=" * 80)

class TranslationCache:
    """Multi-level translation cache with TTL support"""
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.hits = 0
        self.misses = 0
        self.enabled = True
        
    def get(self, key: str) -> Optional[str]:
        """Get translation from cache if not expired"""
        if key in self.cache:
            if time.time() - self.access_times[key] < self.ttl:
                self.hits += 1
                return self.cache[key]['translation']
            else:
                del self.cache[key]
                del self.access_times[key]
        self.misses += 1
        return None
        
    def set(self, key: str, value: str, engine: str) -> None:
        """Set a translation in the cache with engine information"""
        if not self.enabled:
            return
        try:
            self.cache[key] = {
                'translation': value,
                'timestamp': time.time(),
                'engine': engine
            }
            self.access_times[key] = time.time()
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }

class SessionManager:
    """Manages translation sessions and history"""
    def __init__(self, max_history: int = 100, timeout: int = 3600):
        self.sessions = {}
        self.max_history = max_history
        self.timeout = timeout
        self.logger = logging.getLogger('ConsolidatedTranslator')
        
    def add_translation(self, session_id: str, result: Dict[str, Any]) -> None:
        """Add a translation result to session history"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'last_activity': time.time()
            }
            
        # Add original text to history
        history_entry = {
            'text': result['original_text'],
            'translated_text': result.get('translated_text', ''),
            'status': result['status'],
            'engine_used': result['engine_used'],
            'cache_hit': result['cache_hit'],
            'timestamp': time.time()
        }
        
        self.sessions[session_id]['history'].append(history_entry)
        self.sessions[session_id]['last_activity'] = time.time()
        
        # Trim history if needed
        if len(self.sessions[session_id]['history']) > self.max_history:
            self.sessions[session_id]['history'] = self.sessions[session_id]['history'][-self.max_history:]
            
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get translation history for a session"""
        if session_id not in self.sessions:
            return []
            
        # Clean up expired sessions
        self._cleanup_expired_sessions()
        
        return self.sessions[session_id]['history']
        
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions"""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, data in self.sessions.items()
            if current_time - data['last_activity'] > self.timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            self.logger.info(f"Removed expired session: {session_id}")

    def update_session(self, session_id: str, entry: Dict[str, Any] = None) -> None:
        """Update session activity and optionally add a history entry"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'last_activity': time.time()
            }
        self.sessions[session_id]['last_activity'] = time.time()
        if entry is not None:
            self.sessions[session_id]['history'].append(entry)
            # Trim history if needed
            if len(self.sessions[session_id]['history']) > self.max_history:
                self.sessions[session_id]['history'] = self.sessions[session_id]['history'][-self.max_history:]

class TranslationPipeline:
    """Handles translation pipeline with multiple engines"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('ConsolidatedTranslator')
        self.cache = TranslationCache(
            max_size=config['cache']['max_size'],
            ttl=config['cache']['ttl']
        )
        self.session_manager = SessionManager(
            max_history=config['session']['max_history'],
            timeout=config['session']['timeout']
        )
        
        # Initialize dictionary for direct translations
        self.dictionary = {**COMMAND_TRANSLATIONS, **COMPLETE_SENTENCES}
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        self.nllb_socket = self.context.socket(zmq.REQ)
        self.phi_socket = self.context.socket(zmq.REQ)
        self.google_socket = self.context.socket(zmq.REQ)
        
        # Connect to translation services
        try:
            self.nllb_socket.connect(f"tcp://localhost:{config['engines']['nllb']['port']}")
            self.engine_status = {
                'nllb': {'status': 'connected', 'last_error': None},
                'phi': {'status': 'unknown', 'last_error': None},
                'google': {'status': 'unknown', 'last_error': None}
            }
        except Exception as e:
            logger.error(f"Failed to connect to NLLB service: {str(e)}")
            self.engine_status['nllb']['status'] = 'error'
            self.engine_status['nllb']['last_error'] = str(e)
            
        try:
            self.phi_socket.connect(f"tcp://localhost:{config['engines']['phi']['port']}")
            self.engine_status['phi']['status'] = 'connected'
        except Exception as e:
            logger.error(f"Failed to connect to Phi service: {str(e)}")
            self.engine_status['phi']['status'] = 'error'
            self.engine_status['phi']['last_error'] = str(e)
            
        try:
            self.google_socket.connect(f"tcp://localhost:{config['engines']['google']['rca_port']}")
            self.engine_status['google']['status'] = 'connected'
        except Exception as e:
            logger.error(f"Failed to connect to Google service: {str(e)}")
            self.engine_status['google']['status'] = 'error'
            self.engine_status['google']['last_error'] = str(e)
        
        # Start time for uptime tracking
        self.start_time = time.time()
        
        # Language code mapping
        self.language_code_mapping = {
            'fil_Latn': 'tgl_Latn'  # Map Filipino to Tagalog
        }
        
        self.logger.info("TranslationPipeline initialized successfully")
        
    def health_check(self) -> Dict[str, Any]:
        """Return health status of the translation pipeline"""
        uptime = time.time() - self.start_time
        
        return {
            'status': 'healthy',
            'uptime': uptime,
            'cache_stats': self.cache.get_stats(),
            'engines': self.engine_status
        }
        
    def _validate_language_codes(self, source_lang: str, target_lang: str) -> Tuple[bool, Optional[str]]:
        """Validate language codes"""
        # Map language codes if needed
        source_lang = self.language_code_mapping.get(source_lang, source_lang)
        target_lang = self.language_code_mapping.get(target_lang, target_lang)
        
        # Check if language codes are in correct format
        if not re.match(r'^[a-z]{3}_[A-Za-z]{4}$', source_lang) or not re.match(r'^[a-z]{3}_[A-Za-z]{4}$', target_lang):
            return False, "Invalid language code format. Expected format: 'eng_Latn'"
            
        # Check if languages are supported
        supported_langs = ['eng_Latn', 'tgl_Latn', 'ceb_Latn', 'ilo_Latn', 'hil_Latn', 'war_Latn', 'bik_Latn', 'pam_Latn', 'pag_Latn']
        if source_lang not in supported_langs or target_lang not in supported_langs:
            return False, f"Unsupported language code. Supported languages: {', '.join(supported_langs)}"
            
        return True, None
        
    def translate(self, text: str, source_lang: str, target_lang: str, session_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Translate text using multiple engines with fallback"""
        try:
            # Validate language codes
            is_valid, error_msg = self._validate_language_codes(source_lang, target_lang)
            if not is_valid:
                return {
                    "status": "error",
                    "message": error_msg,
                    "engine_used": "none",
                    "cache_hit": False,
                    "session_id": session_id
                }
            
            # Check cache first
            cache_key = f"{text}:{source_lang}:{target_lang}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return {
                    "status": "success",
                    "translated_text": cached_result,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "engine_used": "cache",
                    "cache_hit": True,
                    "session_id": session_id
                }
            
            # Try NLLB first
            try:
                nllb_result = self._translate_with_nllb(text, source_lang, target_lang)
                if nllb_result.get('status') == 'success':
                    translated_text = nllb_result.get('translated_text')
                    self.cache.set(cache_key, translated_text, engine='nllb')
                    return {
                        "status": "success",
                        "translated_text": translated_text,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "engine_used": "nllb",
                        "cache_hit": False,
                        "session_id": session_id
                    }
                else:
                    self.logger.error(f"NLLB translation failed: {nllb_result.get('message')}")
            except Exception as e:
                self.logger.error(f"NLLB translation failed: {str(e)}")
            
            # Try Phi LLM
            try:
                phi_result = self._translate_with_phi(text, source_lang, target_lang)
                if phi_result.get('status') == 'success':
                    translated_text = phi_result.get('translated_text')
                    self.cache.set(cache_key, translated_text, engine='phi')
                    return {
                        "status": "success",
                        "translated_text": translated_text,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "engine_used": "phi",
                        "cache_hit": False,
                        "session_id": session_id
                    }
                else:
                    self.logger.error(f"Phi LLM translation failed: {phi_result.get('message')}")
            except Exception as e:
                self.logger.error(f"Phi LLM translation failed: {str(e)}")
            
            # Try Google Translate
            try:
                google_result = self._translate_with_google(text, source_lang, target_lang)
                if google_result.get('status') == 'success':
                    translated_text = google_result.get('translated_text')
                    self.cache.set(cache_key, translated_text, engine='google')
                    return {
                        "status": "success",
                        "translated_text": translated_text,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "engine_used": "google",
                        "cache_hit": False,
                        "session_id": session_id
                    }
                else:
                    self.logger.error(f"Google translation failed via RCA: {google_result.get('message')}")
            except Exception as e:
                self.logger.error(f"Google translation failed via RCA: {str(e)}")
            
            # Check dictionary for exact matches
            if text.lower() in self.dictionary:
                translated_text = self.dictionary[text.lower()]
                self.cache.set(cache_key, translated_text, engine='dictionary')
                return {
                    "status": "success",
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "engine_used": "dictionary",
                    "cache_hit": False,
                    "session_id": session_id
                }

            # --- BEGIN: Word-by-word and Taglish fallback logic ---
            tagalog_to_english = {
                "buksan": "open",
                "isara": "close",
                "i-save": "save",
                "i-delete": "delete",
                "i-download": "download",
                "i-print": "print",
                "i-maximize": "maximize",
                "i-minimize": "minimize",
                "i-restore": "restore",
                "i-close": "close",
                "i-exit": "exit",
                "i-cancel": "cancel",
                "ang": "the",
                "mo": "you",
                "ito": "this",
                "iyon": "that",
                "na": "",
                "file": "file",
                "document": "document",
                "window": "window",
                "browser": "browser"
            }
            # Taglish detection: if both English and Tagalog words are present
            def is_taglish(text):
                tagalog_words = ["ang", "mo", "ito", "iyan", "iyon", "na", "ng", "sa", "at", "ko", "ba", "si", "ni", "kay"]
                english_words = ["the", "is", "are", "to", "for", "with", "on", "in", "and", "of", "you", "me", "my"]
                t_count = sum(1 for w in tagalog_words if w in text.lower())
                e_count = sum(1 for w in english_words if w in text.lower())
                return t_count > 0 and e_count > 0

            if is_taglish(text):
                # Try word-by-word translation for Taglish
                words = text.lower().split()
                translated_words = []
                for word in words:
                    if word in tagalog_to_english:
                        translated_words.append(tagalog_to_english[word])
                    else:
                        translated_words.append(word)
                translated_text = " ".join(translated_words)
                self.cache.set(cache_key, translated_text, engine='taglish_wordbyword')
                return {
                    "status": "success",
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "engine_used": "taglish_wordbyword",
                    "cache_hit": False,
                    "session_id": session_id
                }
            # Fallback: word-by-word for pure Tagalog
            if source_lang.startswith("tgl") or source_lang == "fil_Latn":
                words = text.lower().split()
                translated_words = []
                for word in words:
                    if word in tagalog_to_english:
                        translated_words.append(tagalog_to_english[word])
                    else:
                        translated_words.append(word)
                translated_text = " ".join(translated_words)
                self.cache.set(cache_key, translated_text, engine='wordbyword')
                return {
                    "status": "success",
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "engine_used": "wordbyword",
                    "cache_hit": False,
                    "session_id": session_id
                }
            # --- END: Word-by-word and Taglish fallback logic ---

            # All engines failed
            self.logger.warning(f"All translation engines failed for {text}")
            return {
                "status": "error",
                "message": "All translation engines failed",
                "engine_used": "none",
                "cache_hit": False,
                "session_id": session_id
            }
            
        except Exception as e:
            self.logger.error(f"Translation failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "engine_used": "none",
                "cache_hit": False,
                "session_id": session_id
            }

    def _translate_with_nllb(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using NLLB model via ZMQ"""
        try:
            # Check if NLLB service is connected
            if self.engine_status['nllb']['status'] != 'connected':
                return {'status': 'error', 'message': 'NLLB service not connected'}
                
            # Prepare request
            request = {
                "action": "translate",
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "request_type": "translation"  # Add request type
            }
            
            # Send request with timeout
            self.nllb_socket.send_json(request)
            if self.nllb_socket.poll(timeout=self.config['engines']['nllb']['timeout'] * 1000):
                response = self.nllb_socket.recv_json()
                if response.get('status') == 'success':
                    self.engine_status['nllb']['status'] = 'connected'
                    return response
                else:
                    self.engine_status['nllb']['status'] = 'error'
                    self.engine_status['nllb']['last_error'] = response.get('message', 'Unknown error')
                    return response
            else:
                self.engine_status['nllb']['status'] = 'error'
                self.engine_status['nllb']['last_error'] = 'Request timed out'
                return {'status': 'error', 'message': 'Request timed out'}
                
        except Exception as e:
            self.engine_status['nllb']['status'] = 'error'
            self.engine_status['nllb']['last_error'] = str(e)
            return {'status': 'error', 'message': str(e)}

    def _translate_with_phi(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using Phi LLM via HTTP API"""
        try:
            # Get Phi LLM service config
            phi_config = get_config_for_service("phi-llm-service-pc2", "pc2")
            if not phi_config:
                self.engine_status['phi']['status'] = 'error'
                self.engine_status['phi']['last_error'] = 'Phi LLM service not configured'
                return {'status': 'error', 'message': 'Phi LLM service not configured'}
            
            # Check cache first
            cache_key = f"{text}:{source_lang}:{target_lang}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.engine_status['phi']['status'] = 'connected'
                return {
                    'status': 'success',
                    'translated_text': cached_result,
                    'engine_used': 'phi',
                    'cached': True
                }
            
            # Prepare request for Ollama API
            request = {
                "model": phi_config['model_path_or_name'],
                "prompt": f"Translate from {source_lang} to {target_lang}: {text}",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 512
                }
            }
            
            # Send request to Ollama API with timeout
            response = requests.post(
                f"http://{phi_config['http_bind_address']}:{phi_config['http_port']}/api/generate",
                json=request,
                timeout=self.config['engines']['phi']['timeout']
            )
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get("response", "").strip()
                
                # Clean up the translation
                translated_text = re.sub(r'^(Translation:|English:|In English:)\s*', '', translated_text, flags=re.IGNORECASE)
                translated_text = translated_text.strip()
                
                if translated_text:
                    self.engine_status['phi']['status'] = 'connected'
                    # Cache the translation with engine parameter
                    self.cache.set(cache_key, translated_text, engine='phi')
                    return {
                        'status': 'success',
                        'translated_text': translated_text,
                        'engine_used': 'phi',
                        'cached': False
                    }
                else:
                    self.engine_status['phi']['status'] = 'error'
                    self.engine_status['phi']['last_error'] = 'Empty translation'
                    return {'status': 'error', 'message': 'Empty translation'}
            else:
                self.engine_status['phi']['status'] = 'error'
                self.engine_status['phi']['last_error'] = f'HTTP error: {response.status_code}'
                return {'status': 'error', 'message': f'HTTP error: {response.status_code}'}
                
        except requests.exceptions.Timeout:
            self.engine_status['phi']['status'] = 'error'
            self.engine_status['phi']['last_error'] = 'Request timed out'
            return {'status': 'error', 'message': 'Request timed out'}
        except requests.exceptions.ConnectionError:
            self.engine_status['phi']['status'] = 'error'
            self.engine_status['phi']['last_error'] = 'Connection error'
            return {'status': 'error', 'message': 'Connection error'}
        except Exception as e:
            self.engine_status['phi']['status'] = 'error'
            self.engine_status['phi']['last_error'] = str(e)
            return {'status': 'error', 'message': str(e)}

    def _translate_with_google(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using Google Translate via RCA"""
        try:
            # Check if Google service is connected
            if self.engine_status['google']['status'] != 'connected':
                return {'status': 'error', 'message': 'Google service not connected'}
                
            # Prepare request
            request = {
                "action": "translate",
                "request_type": "translation",  # Add request type
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            # Send request with timeout
            self.google_socket.send_json(request)
            if self.google_socket.poll(timeout=self.config['engines']['google']['timeout'] * 1000):
                response = self.google_socket.recv_json()
                if response.get('status') == 'success':
                    self.engine_status['google']['status'] = 'connected'
                    return response
                else:
                    self.engine_status['google']['status'] = 'error'
                    self.engine_status['google']['last_error'] = response.get('message', 'Unknown error')
                    return response
            else:
                self.engine_status['google']['status'] = 'error'
                self.engine_status['google']['last_error'] = 'Request timed out'
                return {'status': 'error', 'message': 'Request timed out'}
                
        except Exception as e:
            self.engine_status['google']['status'] = 'error'
            self.engine_status['google']['last_error'] = str(e)
            return {'status': 'error', 'message': str(e)}

class TranslatorServer:
    """ZMQ server for translation service"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pipeline = TranslationPipeline(config)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{ZMQ_PORT}")
        self.start_time = time.time()
        logger.info(f"Server started on port {ZMQ_PORT}")
        
    def run(self):
        """Run the translation server"""
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self._handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'error': str(e)
                })
                
    def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming request"""
        action = message.get('action')
        
        if action == 'translate':
            return self._handle_translate(message)
        elif action == 'health_check':
            return self._handle_health_check()
        else:
            return {
                'status': 'error',
                'error': f'Unknown action: {action}'
            }
            
    def _handle_translate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle translation request"""
        try:
            # Extract parameters
            text = message.get('text', '')
            source_lang = message.get('source_lang', 'tl')
            target_lang = message.get('target_lang', 'en')
            session_id = message.get('session_id')
            options = message.get('options', {})
            
            # Validate parameters
            if not text:
                return {
                    'status': 'error',
                    'error': 'Missing text parameter'
                }
                
            # Get translation
            return self.pipeline.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _handle_health_check(self) -> Dict[str, Any]:
        """Handle health check request"""
        return self.pipeline.health_check()

def main():
    """Main entry point"""
    try:
        # Create and run server
        server = TranslatorServer(TRANSLATOR_CONFIG)
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 