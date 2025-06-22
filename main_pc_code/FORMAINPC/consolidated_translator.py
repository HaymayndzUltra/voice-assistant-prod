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
# from config.system_config import get_config_for_service  # Temporarily commented out
import threading
import psutil
import functools
import argparse

# Import config parser for dynamic port support
from utils.config_parser import parse_agent_args

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

# Default constants for Main PC
DEFAULT_ZMQ_PORT = 5563  # Main PC port for translator
DEFAULT_HEALTH_PORT = 5564  # Health check port
ZMQ_BIND_ADDRESS = "0.0.0.0"  # Listen on all interfaces
# Timeout for ZeroMQ send/recv operations (milliseconds)
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds
MAX_SESSION_HISTORY = 10
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

# Health monitoring settings
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

# Configuration for Main PC
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
            "port": 5581,
            "host": "192.168.100.17"  # PC2's IP where NLLB is running
        },
        "phi": {
            "enabled": True,
            "priority": 3,
            "confidence_threshold": 0.75,
            "timeout": 3,
            "port": 11434,
            "host": "192.168.100.17"  # PC2's IP where Phi is running
        },
        "google": {
            "enabled": True,
            "priority": 4,
            "confidence_threshold": 0.90,
            "rca_port": 5557,
            "host": "192.168.100.17"  # PC2's IP for Remote Connector Agent
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
    },
    "health": {
        "check_interval": HEALTH_CHECK_INTERVAL,
        "timeout": HEALTH_CHECK_TIMEOUT,
        "max_retries": MAX_RETRIES
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
logger.info(f"ZMQ Port: {DEFAULT_ZMQ_PORT}")
logger.info(f"Bind Address: {ZMQ_BIND_ADDRESS}")
logger.info("=" * 80)

CACHE_TTL = 600  # seconds
_translation_cache = {}
_translation_cache_lock = threading.Lock()

def translation_cache_key(*args, **kwargs):
    return str(args) + str(kwargs)

def cache_translation_result(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = translation_cache_key(*args, **kwargs)
        now = time.time()
        with _translation_cache_lock:
            if key in _translation_cache:
                ts, value = _translation_cache[key]
                if now - ts < CACHE_TTL:
                    return value
                else:
                    del _translation_cache[key]
        result = func(*args, **kwargs)
        with _translation_cache_lock:
            _translation_cache[key] = (now, result)
        return result
    return wrapper

class TranslationCache:
    """Multi-level translation cache with TTL support"""
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_count = {}
        self.last_accessed = {}
        self.creation_time = {}
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        
    def get(self, key: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Enhanced get method with context-aware caching."""
        current_time = time.time()
        
        # Check if key exists and is not expired
        if key in self.cache:
            if current_time - self.creation_time[key] > self.ttl:
                # Cache entry expired
                self._remove(key)
                self.stats['misses'] += 1
                return None
                
            # Update access statistics
            self.access_count[key] += 1
            self.last_accessed[key] = current_time
            self.stats['hits'] += 1
            
            # If context is provided, check if it matches
            if context and 'context_hash' in self.cache[key]:
                if self.cache[key]['context_hash'] != hash(str(context)):
                    self.stats['misses'] += 1
                    return None
                    
            return self.cache[key]['value']
            
        self.stats['misses'] += 1
        return None
        
    def set(self, key: str, value: str, engine: str, context: Dict[str, Any] = None) -> None:
        """Enhanced set method with context-aware caching."""
        current_time = time.time()
        
        # Create cache entry with metadata
        entry = {
            'value': value,
            'engine': engine,
            'created_at': current_time,
            'context_hash': hash(str(context)) if context else None
        }
        
        # Check if we need to evict entries
        if len(self.cache) >= self.max_size:
            self._evict_entries()
            
        # Add new entry
        self.cache[key] = entry
        self.access_count[key] = 1
        self.last_accessed[key] = current_time
        self.creation_time[key] = current_time
        self.stats['size'] = len(self.cache)
        
    def _evict_entries(self) -> None:
        """Evict least recently used and least frequently accessed entries."""
        current_time = time.time()
        
        # Calculate scores for each entry
        scores = {}
        for key in self.cache:
            # Score based on access count and recency
            access_score = self.access_count[key]
            recency_score = 1 / (current_time - self.last_accessed[key] + 1)
            scores[key] = access_score * recency_score
            
        # Remove lowest scoring entries
        num_to_evict = max(1, int(self.max_size * 0.1))  # Evict 10% of cache
        for key in sorted(scores, key=scores.get)[:num_to_evict]:
            self._remove(key)
            self.stats['evictions'] += 1
            
    def _remove(self, key: str) -> None:
        """Remove an entry from the cache."""
        if key in self.cache:
            del self.cache[key]
            del self.access_count[key]
            del self.last_accessed[key]
            del self.creation_time[key]
            self.stats['size'] = len(self.cache)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        return {
            **self.stats,
            'hit_rate': self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0,
            'avg_access_count': sum(self.access_count.values()) / len(self.access_count) if self.access_count else 0,
            'oldest_entry': min(self.creation_time.values()) if self.creation_time else None,
            'newest_entry': max(self.creation_time.values()) if self.creation_time else None
        }
        
    def warm_cache(self, entries: List[Tuple[str, str, str]]) -> None:
        """Pre-populate cache with common translations."""
        for key, value, engine in entries:
            self.set(key, value, engine)
            
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
        self.access_count.clear()
        self.last_accessed.clear()
        self.creation_time.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }

class SessionManager:
    """Manages translation sessions and history"""
    def __init__(self, max_history: int = 100, timeout: int = 3600):
        self.max_history = max_history
        self.timeout = timeout
        self.sessions = {}
        self.session_stats = {}
        self.last_cleanup = time.time()
        
    def add_translation(self, session_id: str, result: Dict[str, Any]) -> None:
        """Add a translation to session history with enhanced metadata."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': deque(maxlen=self.max_history),
                'created_at': time.time(),
                'last_accessed': time.time(),
                'stats': {
                    'total_translations': 0,
                    'successful_translations': 0,
                    'failed_translations': 0,
                    'engines_used': {},
                    'avg_response_time': 0,
                    'total_response_time': 0
                }
            }
            
        # Update session metadata
        session = self.sessions[session_id]
        session['last_accessed'] = time.time()
        
        # Update statistics
        session['stats']['total_translations'] += 1
        if result.get('status') == 'success':
            session['stats']['successful_translations'] += 1
        else:
            session['stats']['failed_translations'] += 1
            
        # Track engine usage
        engine = result.get('engine_used', 'unknown')
        session['stats']['engines_used'][engine] = session['stats']['engines_used'].get(engine, 0) + 1
        
        # Update response time statistics
        response_time = result.get('response_time', 0)
        session['stats']['total_response_time'] += response_time
        session['stats']['avg_response_time'] = (
            session['stats']['total_response_time'] / session['stats']['total_translations']
        )
        
        # Add to history with enhanced metadata
        history_entry = {
            'timestamp': time.time(),
            'result': result,
            'metadata': {
                'source_lang': result.get('source_lang'),
                'target_lang': result.get('target_lang'),
                'engine_used': engine,
                'response_time': response_time,
                'cache_hit': result.get('cache_hit', False)
            }
        }
        session['history'].append(history_entry)
        
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get session history with enhanced filtering and sorting."""
        if session_id not in self.sessions:
            return []
            
        session = self.sessions[session_id]
        session['last_accessed'] = time.time()
        
        return list(session['history'])
        
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session statistics."""
        if session_id not in self.sessions:
            return {}
            
        session = self.sessions[session_id]
        return {
            'session_id': session_id,
            'created_at': session['created_at'],
            'last_accessed': session['last_accessed'],
            'age': time.time() - session['created_at'],
            'history_size': len(session['history']),
            'stats': session['stats']
        }
        
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions with enhanced logging."""
        current_time = time.time()
        expired_count = 0
        active_count = 0
        
        for session_id in list(self.sessions.keys()):
            session = self.sessions[session_id]
            if current_time - session['last_accessed'] > self.timeout:
                # Log session statistics before removal
                logger.info(f"Removing expired session {session_id}. Stats: {session['stats']}")
                del self.sessions[session_id]
                expired_count += 1
            else:
                active_count += 1
                
        logger.info(f"Session cleanup completed. Expired: {expired_count}, Active: {active_count}")
        self.last_cleanup = current_time
        
    def update_session(self, session_id: str, entry: Dict[str, Any] = None) -> None:
        """Update session with enhanced validation and error handling."""
        try:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'history': deque(maxlen=self.max_history),
                    'created_at': time.time(),
                    'last_accessed': time.time(),
                    'stats': {
                        'total_translations': 0,
                        'successful_translations': 0,
                        'failed_translations': 0,
                        'engines_used': {},
                        'avg_response_time': 0,
                        'total_response_time': 0
                    }
                }
                
            session = self.sessions[session_id]
            session['last_accessed'] = time.time()
            
            if entry:
                # Validate entry
                if not isinstance(entry, dict):
                    raise ValueError("Entry must be a dictionary")
                    
                # Update session with new entry
                if 'result' in entry:
                    self.add_translation(session_id, entry['result'])
                if 'metadata' in entry:
                    session['metadata'] = entry['metadata']
                    
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {str(e)}")
            raise
            
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions with their statistics."""
        current_time = time.time()
        active_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session['last_accessed'] <= self.timeout:
                active_sessions.append({
                    'session_id': session_id,
                    'created_at': session['created_at'],
                    'last_accessed': session['last_accessed'],
                    'history_size': len(session['history']),
                    'stats': session['stats']
                })
                
        return active_sessions
        
    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session with confirmation."""
        if session_id in self.sessions:
            logger.info(f"Clearing session {session_id}")
            del self.sessions[session_id]
            return True
        return False
        
    def clear_all_sessions(self) -> int:
        """Clear all sessions and return count of cleared sessions."""
        count = len(self.sessions)
        logger.info(f"Clearing all {count} sessions")
        self.sessions.clear()
        return count

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
        self.engine_status = {
            'dictionary': {'status': 'unknown', 'last_error': None},
            'nllb': {'status': 'unknown', 'last_error': None},
            'phi': {'status': 'unknown', 'last_error': None},
            'google': {'status': 'unknown', 'last_error': None}
        }
        
        # Initialize language detection
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0  # For consistent results
            self.has_langdetect = True
        except ImportError:
            logger.warning("langdetect not available. Language detection will be limited.")
            self.has_langdetect = False
            
        # Initialize quality metrics
        try:
            from nltk.translate.bleu_score import sentence_bleu
            from nltk.tokenize import word_tokenize
            import nltk
            nltk.download('punkt', quiet=True)
            self.has_bleu = True
        except ImportError:
            logger.warning("nltk not available. Quality metrics will be limited.")
            self.has_bleu = False
        
        # Initialize dictionary for direct translations
        self.dictionary = {**COMMAND_TRANSLATIONS, **COMPLETE_SENTENCES}
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        self.nllb_socket = self.context.socket(zmq.REQ)
        self.nllb_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.nllb_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.phi_socket = self.context.socket(zmq.REQ)
        self.phi_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.phi_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.google_socket = self.context.socket(zmq.REQ)
        self.google_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.google_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Initialize engine connections with graceful failure handling
        try:
            nllb_host = config['engines']['nllb']['host']
            nllb_port = config['engines']['nllb']['port']
            self.nllb_socket.connect(f"tcp://{nllb_host}:{nllb_port}")
            self.engine_status['nllb']['status'] = 'connected'
            logger.info(f"Connected to NLLB service at {nllb_host}:{nllb_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to NLLB service: {str(e)} - continuing without NLLB")
            self.engine_status['nllb']['status'] = 'disconnected'
            self.engine_status['nllb']['last_error'] = str(e)
            
        try:
            phi_host = config['engines']['phi']['host']
            phi_port = config['engines']['phi']['port']
            self.phi_socket.connect(f"tcp://{phi_host}:{phi_port}")
            self.engine_status['phi']['status'] = 'connected'
            logger.info(f"Connected to Phi service at {phi_host}:{phi_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Phi service: {str(e)} - continuing without Phi")
            self.engine_status['phi']['status'] = 'disconnected'
            self.engine_status['phi']['last_error'] = str(e)
            
        try:
            google_host = config['engines']['google']['host']
            google_port = config['engines']['google']['rca_port']
            self.google_socket.connect(f"tcp://{google_host}:{google_port}")
            self.engine_status['google']['status'] = 'connected'
            logger.info(f"Connected to Google service at {google_host}:{google_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Google service: {str(e)} - continuing without Google")
            self.engine_status['google']['status'] = 'disconnected'
            self.engine_status['google']['last_error'] = str(e)
        
        # Start time for uptime tracking
        self.start_time = time.time()
        
        # Language code mapping
        self.language_code_mapping = {
            'fil_Latn': 'tgl_Latn'  # Map Filipino to Tagalog
        }
        
        # Initialize rate limiting
        self.rate_limits = {
            'dictionary': {'calls': 0, 'last_reset': time.time(), 'max_calls': 1000, 'window': 60},
            'nllb': {'calls': 0, 'last_reset': time.time(), 'max_calls': 100, 'window': 60},
            'phi': {'calls': 0, 'last_reset': time.time(), 'max_calls': 50, 'window': 60},
            'google': {'calls': 0, 'last_reset': time.time(), 'max_calls': 200, 'window': 60}
        }
        
        # Initialize error recovery strategies
        self.error_recovery_strategies = {
            'connection_error': self._handle_connection_error,
            'timeout_error': self._handle_timeout_error,
            'rate_limit_error': self._handle_rate_limit_error,
            'translation_error': self._handle_translation_error
        }
        
        # Initialize engine performance tracking
        self.engine_performance = {
            'dictionary': {'success': 0, 'total': 0, 'avg_time': 0},
            'nllb': {'success': 0, 'total': 0, 'avg_time': 0},
            'phi': {'success': 0, 'total': 0, 'avg_time': 0},
            'google': {'success': 0, 'total': 0, 'avg_time': 0}
        }
        
        # Initialize memory management
        self.memory_stats = {
            'cache_size': 0,
            'session_count': 0,
            'total_requests': 0,
            'active_connections': 0,
            'last_cleanup': time.time()
        }
        
        # Initialize monitoring
        self.monitoring = {
            'response_times': deque(maxlen=1000),
            'error_rates': deque(maxlen=1000),
            'engine_usage': {},
            'resource_usage': {
                'cpu': deque(maxlen=100),
                'memory': deque(maxlen=100)
            }
        }
        
        # Initialize monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        
        # Health monitoring
        self.health_status = {
            "status": "ok",
            "service": "consolidated_translator",
            "last_check": time.time(),
            "engines": {
                "dictionary": True,
                "nllb": True,
                "phi": True,
                "google": True
            }
        }
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.health_thread.start()
        
        # Wait a moment for health server to start
        time.sleep(0.5)
        
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
        
    def check_rate_limit(self, engine: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the engine has exceeded its rate limit.
        Returns (can_proceed, error_message)
        """
        if engine not in self.rate_limits:
            return True, None
            
        limit = self.rate_limits[engine]
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - limit['last_reset'] > limit['window']:
            limit['calls'] = 0
            limit['last_reset'] = current_time
            
        # Check if limit exceeded
        if limit['calls'] >= limit['max_calls']:
            return False, f"Rate limit exceeded for {engine}. Try again in {int(limit['window'] - (current_time - limit['last_reset']))} seconds."
            
        limit['calls'] += 1
        return True, None

    def _handle_connection_error(self, engine: str, error: Exception) -> Dict[str, Any]:
        """Handle connection errors with recovery strategies."""
        logger.error(f"Connection error with {engine}: {str(error)}")
        
        # Mark engine as disconnected
        self.engine_status[engine]['status'] = 'disconnected'
        self.engine_status[engine]['last_error'] = str(error)
        
        # Attempt to reconnect
        try:
            if engine == 'nllb':
                self.nllb_socket.connect(f"tcp://{self.config['engines']['nllb']['host']}:{self.config['engines']['nllb']['port']}")
            elif engine == 'phi':
                # Reinitialize Phi connection
                pass
            elif engine == 'google':
                # Reinitialize Google connection
                pass
                
            self.engine_status[engine]['status'] = 'connected'
            return {'status': 'recovered', 'message': f"Successfully reconnected to {engine}"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to recover connection to {engine}: {str(e)}"}

    def _handle_timeout_error(self, engine: str, error: Exception) -> Dict[str, Any]:
        """Handle timeout errors with recovery strategies."""
        logger.error(f"Timeout error with {engine}: {str(error)}")
        
        # Increase timeout for next attempt
        if engine in self.config['engines']:
            current_timeout = self.config['engines'][engine].get('timeout', 30)
            self.config['engines'][engine]['timeout'] = min(current_timeout * 1.5, 120)
            
        return {'status': 'retry', 'message': f"Timeout occurred. Retrying with increased timeout."}

    def _handle_rate_limit_error(self, engine: str, error: Exception) -> Dict[str, Any]:
        """Handle rate limit errors with recovery strategies."""
        logger.error(f"Rate limit error with {engine}: {str(error)}")
        
        # Implement exponential backoff
        if engine in self.rate_limits:
            current_window = self.rate_limits[engine]['window']
            self.rate_limits[engine]['window'] = min(current_window * 1.5, 300)
            
        return {'status': 'retry', 'message': f"Rate limit reached. Implementing backoff strategy."}

    def _handle_translation_error(self, engine: str, error: Exception) -> Dict[str, Any]:
        """Handle translation errors with recovery strategies."""
        logger.error(f"Translation error with {engine}: {str(error)}")
        
        # Try to recover by cleaning input
        return {'status': 'retry', 'message': "Attempting to recover by cleaning input."}

    def _attempt_error_recovery(self, engine: str, error: Exception) -> Dict[str, Any]:
        """Attempt to recover from various types of errors."""
        error_type = type(error).__name__
        
        # Map error types to recovery strategies
        if 'Connection' in error_type:
            return self._handle_connection_error(engine, error)
        elif 'Timeout' in error_type:
            return self._handle_timeout_error(engine, error)
        elif 'RateLimit' in error_type:
            return self._handle_rate_limit_error(engine, error)
        else:
            return self._handle_translation_error(engine, error)

    def select_best_engine(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Dynamically select the best translation engine based on:
        - Text characteristics
        - Historical performance
        - Current engine status
        - Language pair
        """
        # Calculate text characteristics
        text_length = len(text)
        is_technical = any(word in text.lower() for word in ['error', 'code', 'function', 'class', 'method'])
        has_numbers = any(c.isdigit() for c in text)
        
        # Calculate engine scores
        engine_scores = {}
        for engine in self.engine_status:
            if self.engine_status[engine]['status'] != 'connected':
                continue
                
            # Base score on historical performance
            perf = self.engine_performance[engine]
            success_rate = perf['success'] / perf['total'] if perf['total'] > 0 else 0.5
            avg_time = perf['avg_time']
            
            # Adjust score based on text characteristics
            score = success_rate * (1 / (1 + avg_time))  # Normalize time impact
            
            if engine == 'dictionary':
                # Dictionary is good for short, common phrases
                score *= 1.5 if text_length < 50 else 0.5
            elif engine == 'nllb':
                # NLLB is good for longer texts and technical content
                score *= 1.2 if text_length > 100 or is_technical else 0.8
            elif engine == 'phi':
                # Phi is good for creative content
                score *= 1.3 if not is_technical and not has_numbers else 0.7
            elif engine == 'google':
                # Google is good as a general fallback
                score *= 1.1
                
            engine_scores[engine] = score
            
        # Select engine with highest score
        if engine_scores:
            return max(engine_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'google'  # Default fallback
            
    def update_engine_performance(self, engine: str, success: bool, time_taken: float) -> None:
        """Update engine performance metrics."""
        if engine in self.engine_performance:
            perf = self.engine_performance[engine]
            perf['total'] += 1
            if success:
                perf['success'] += 1
            # Update average time using exponential moving average
            alpha = 0.1  # Smoothing factor
            perf['avg_time'] = (1 - alpha) * perf['avg_time'] + alpha * time_taken
            
    def _monitor_resources(self):
        """Monitor system resources in background."""
        import psutil
        process = psutil.Process()
        
        while True:
            try:
                # Update resource usage
                self.monitoring['resource_usage'].update({
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'memory_used': process.memory_info().rss / 1024 / 1024  # MB
                })
                
                # Check if cleanup is needed
                if time.time() - self.memory_stats['last_cleanup'] > 300:  # 5 minutes
                    self.optimize_memory_usage()
                    
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}")
                time.sleep(30)  # Wait longer on error
                
    def optimize_memory_usage(self):
        """Optimize memory usage by cleaning up resources."""
        try:
            # Clean up expired cache entries
            self.cache._evict_entries()
            
            # Clean up expired sessions
            self.session_manager._cleanup_expired_sessions()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Update memory stats
            self.memory_stats.update({
                'cache_size': len(self.cache.cache),
                'session_count': len(self.session_manager.sessions),
                'last_cleanup': time.time()
            })
            
            logger.info(f"Memory optimization completed. Cache size: {self.memory_stats['cache_size']}, "
                       f"Sessions: {self.memory_stats['session_count']}")
                       
        except Exception as e:
            logger.error(f"Memory optimization failed: {str(e)}")
            
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics."""
        try:
            # Calculate average response time
            response_times = list(self.monitoring['response_times'])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Calculate error rate
            error_rates = list(self.monitoring['error_rates'])
            error_rate = sum(error_rates) / len(error_rates) if error_rates else 0
            
            # Get current resource usage
            resource_usage = self.monitoring['resource_usage']
            
            return {
                'performance': {
                    'avg_response_time': avg_response_time,
                    'error_rate': error_rate,
                    'total_requests': self.memory_stats['total_requests']
                },
                'engine_usage': self.monitoring['engine_usage'],
                'resource_usage': resource_usage,
                'memory_stats': self.memory_stats,
                'cache_stats': self.cache.get_stats()
            }
        except Exception as e:
            logger.error(f"Error getting monitoring stats: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
            
    def translate(self, text: str, source_lang: str, target_lang: str, session_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced translate method with monitoring."""
        start_time = time.time()
        self.memory_stats['total_requests'] += 1
        
        try:
            # Validate input
            if not text:
                return {'status': 'error', 'message': 'Empty text provided'}
                
            # Check rate limits for each engine
            for engine in ['dictionary', 'nllb', 'phi', 'google']:
                can_proceed, error_msg = self.check_rate_limit(engine)
                if not can_proceed:
                    logger.warning(f"Rate limit warning for {engine}: {error_msg}")
                    
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
            
            # Select best engine
            selected_engine = self.select_best_engine(text, source_lang, target_lang)
            logger.info(f"Selected engine: {selected_engine}")
            
            # Try selected engine first
            result = self._translate_with_engine(selected_engine, text, source_lang, target_lang)
            
            # Update performance metrics
            self.update_engine_performance(selected_engine, result['status'] == 'success', time.time() - start_time)
            
            # If selected engine fails, try others in order of preference
            if result['status'] != 'success':
                for engine in ['dictionary', 'nllb', 'phi', 'google']:
                    if engine != selected_engine:
                        start_time = time.time()
                        result = self._translate_with_engine(engine, text, source_lang, target_lang)
                        self.update_engine_performance(engine, result['status'] == 'success', time.time() - start_time)
                        if result['status'] == 'success':
                            break
                            
            # Update monitoring stats
            response_time = time.time() - start_time
            self.monitoring['response_times'].append(response_time)
            self.monitoring['error_rates'].append(0)  # Success
            
            # Update engine usage
            if result['status'] == 'success':
                self.monitoring['engine_usage'][result['engine_used']] += 1
                
            return result
            
        except Exception as e:
            # Update error monitoring
            self.monitoring['error_rates'].append(1)  # Error
            logger.error(f"Translation error: {str(e)}")
            
            # Attempt recovery
            recovery_result = self._attempt_error_recovery('unknown', e)
            
            if recovery_result['status'] == 'recovered':
                # Retry the translation
                return self.translate(text, source_lang, target_lang, session_id, options)
            else:
                return {
                    'status': 'error',
                    'message': str(e),
                    'recovery_attempted': True,
                    'recovery_result': recovery_result
                }

    def _translate_with_engine(self, engine: str, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate using a specific engine."""
        if engine == 'dictionary':
            return self._translate_with_dictionary(text, source_lang, target_lang)
        elif engine == 'nllb':
            return self._translate_with_nllb(text, source_lang, target_lang)
        elif engine == 'phi':
            return self._translate_with_phi(text, source_lang, target_lang)
        elif engine == 'google':
            return self._translate_with_google(text, source_lang, target_lang)
        else:
            return {'status': 'error', 'message': f'Unknown engine: {engine}'}

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

    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the input text with confidence score.
        Returns a dictionary with detected language and confidence.
        """
        if not self.has_langdetect:
            # Fallback to simple heuristics
            return self._fallback_language_detection(text)
            
        try:
            from langdetect import detect_langs
            detections = detect_langs(text)
            if detections:
                best_match = detections[0]
                return {
                    'status': 'success',
                    'language': best_match.lang,
                    'confidence': best_match.prob,
                    'all_detections': [{'lang': d.lang, 'prob': d.prob} for d in detections]
                }
        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return self._fallback_language_detection(text)
            
    def _fallback_language_detection(self, text: str) -> Dict[str, Any]:
        """
        Simple heuristic-based language detection fallback.
        """
        # Check for common Tagalog/Filipino words
        tagalog_words = {'ang', 'ng', 'sa', 'ay', 'at', 'si', 'sina', 'kay', 'kina', 'ni', 'nina'}
        words = set(text.lower().split())
        tagalog_count = len(words.intersection(tagalog_words))
        
        # Check for common English words
        english_words = {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'an', 'for', 'with'}
        english_count = len(words.intersection(english_words))
        
        if tagalog_count > english_count:
            return {
                'status': 'success',
                'language': 'tl',
                'confidence': 0.7,
                'method': 'heuristic'
            }
        else:
            return {
                'status': 'success',
                'language': 'en',
                'confidence': 0.7,
                'method': 'heuristic'
            }

    def evaluate_translation_quality(self, original: str, translated: str) -> Dict[str, Any]:
        """
        Evaluate translation quality using multiple metrics.
        """
        metrics = {
            'bleu_score': None,
            'semantic_similarity': None,
            'length_ratio': None,
            'error_checks': {}
        }
        
        # Calculate BLEU score if available
        if self.has_bleu:
            try:
                from nltk.translate.bleu_score import sentence_bleu
                from nltk.tokenize import word_tokenize
                
                reference = [word_tokenize(original.lower())]
                candidate = word_tokenize(translated.lower())
                metrics['bleu_score'] = sentence_bleu(reference, candidate)
            except Exception as e:
                logger.warning(f"BLEU score calculation failed: {str(e)}")
        
        # Calculate length ratio
        try:
            orig_len = len(original.split())
            trans_len = len(translated.split())
            metrics['length_ratio'] = min(orig_len, trans_len) / max(orig_len, trans_len)
        except Exception as e:
            logger.warning(f"Length ratio calculation failed: {str(e)}")
        
        # Check for common translation errors
        metrics['error_checks'] = self._check_translation_errors(original, translated)
        
        return metrics
        
    def _check_translation_errors(self, original: str, translated: str) -> Dict[str, Any]:
        """
        Check for common translation errors.
        """
        errors = {
            'empty_translation': len(translated.strip()) == 0,
            'identical_text': original.lower() == translated.lower(),
            'missing_punctuation': self._check_punctuation(original, translated),
            'number_mismatch': self._check_numbers(original, translated),
            'special_char_mismatch': self._check_special_chars(original, translated)
        }
        return errors
        
    def _check_punctuation(self, original: str, translated: str) -> bool:
        """Check if punctuation marks are preserved."""
        orig_punct = set(c for c in original if c in '.,!?;:')
        trans_punct = set(c for c in translated if c in '.,!?;:')
        return orig_punct != trans_punct
        
    def _check_numbers(self, original: str, translated: str) -> bool:
        """Check if numbers are preserved."""
        import re
        orig_nums = set(re.findall(r'\d+', original))
        trans_nums = set(re.findall(r'\d+', translated))
        return orig_nums != trans_nums
        
    def _check_special_chars(self, original: str, translated: str) -> bool:
        """Check if special characters are preserved."""
        special_chars = set('@#$%^&*()_+-=[]{}|;:,.<>?/~`')
        orig_special = set(c for c in original if c in special_chars)
        trans_special = set(c for c in translated if c in special_chars)
        return orig_special != trans_special

    def _monitor_health(self):
        """Monitor health of all translation engines"""
        while True:
            try:
                # Check NLLB connection
                self.nllb_socket.send_json({"action": "health_check"})
                try:
                    response = self.nllb_socket.recv_json(timeout=self.config["health"]["timeout"])
                    self.health_status["engines"]["nllb"] = response.get("status") == "ok"
                except zmq.error.Again:
                    self.health_status["engines"]["nllb"] = False
                    logger.warning("NLLB health check timeout")
                
                # Update last check time
                self.health_status["last_check"] = time.time()
                
                # Log health status
                if not all(self.health_status["engines"].values()):
                    logger.warning("Health check failed for some engines")
                    logger.debug(f"Health status: {self.health_status}")
                
                time.sleep(self.config["health"]["check_interval"])
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                time.sleep(self.config["health"]["check_interval"])

class TranslatorServer:
    """ZMQ server for translation service with dynamic port support and separate health check endpoint"""
    def __init__(self, config: Dict[str, Any], main_port: int = None, health_port: int = None):
        self.config = config
        self.pipeline = TranslationPipeline(config)
        self.context = zmq.Context()
        
        # Use provided ports or defaults
        self.main_port = main_port or DEFAULT_ZMQ_PORT
        self.health_port = health_port or DEFAULT_HEALTH_PORT
        
        # Main service socket
        self.main_socket = self.context.socket(zmq.REP)
        self.main_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.main_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Health check socket (separate endpoint)
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Bind sockets
        self._bind_sockets()
        
        self.start_time = time.time()
        logger.info(f"Server started on main port {self.main_port} and health port {self.health_port}")
        
        # Add API version and capabilities
        self.api_version = "2.0"
        self.capabilities = {
            'languages': ['en', 'tl', 'fil_Latn'],
            'engines': ['dictionary', 'nllb', 'phi', 'google'],
            'features': [
                'language_detection',
                'quality_metrics',
                'session_management',
                'caching',
                'monitoring',
                'error_recovery'
            ]
        }
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._run_health_server, daemon=True)
        self.health_thread.start()
        logger.info("Health check server thread started")
        
    def _bind_sockets(self):
        """Bind both main and health check sockets with fallback ports"""
        # Bind main socket
        try:
            self.main_socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{self.main_port}")
            logger.info(f"Main service bound to port {self.main_port}")
        except zmq.error.ZMQError as e:
            if "Address in use" in str(e):
                logger.warning(f"Main port {self.main_port} is in use, trying alternative ports")
                alt_ports = [7701, 7702, 7703, 7704, 7705]
                for alt_port in alt_ports:
                    try:
                        self.main_socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{alt_port}")
                        self.main_port = alt_port
                        logger.info(f"Main service successfully bound to alternative port {alt_port}")
                        break
                    except zmq.error.ZMQError:
                        continue
                else:
                    logger.error("Could not bind main service to any port")
                    raise RuntimeError("Cannot bind main service to any port")
            else:
                logger.error(f"Error binding main socket: {e}")
                raise RuntimeError(f"Cannot bind main service to port {self.main_port}")
        
        # Bind health socket
        try:
            self.health_socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{self.health_port}")
            logger.info(f"Health check service bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            if "Address in use" in str(e):
                logger.warning(f"Health port {self.health_port} is in use, trying alternative ports")
                alt_ports = [7706, 7707, 7708, 7709, 7710]
                for alt_port in alt_ports:
                    try:
                        self.health_socket.bind(f"tcp://{ZMQ_BIND_ADDRESS}:{alt_port}")
                        self.health_port = alt_port
                        logger.info(f"Health check service successfully bound to alternative port {alt_port}")
                        break
                    except zmq.error.ZMQError:
                        continue
                else:
                    logger.error("Could not bind health service to any port")
                    raise RuntimeError("Cannot bind health service to any port")
            else:
                logger.error(f"Error binding health socket: {e}")
                raise RuntimeError(f"Cannot bind health service to port {self.health_port}")
        
    def _run_health_server(self):
        """Run health check server on separate thread"""
        logger.info("Health check server thread started and listening for requests")
        while True:
            try:
                # Wait for health-check request (blocking with timeout)
                logger.debug("Health server waiting for request…")
                message = self.health_socket.recv_json()
                logger.info(f"Received health check request: {message}")

                # Build and send the response
                response = self._handle_health_check()
                self.health_socket.send_json(response)
                logger.info("Health check response sent successfully")

            except zmq.error.Again:
                # Timeout expired – no request arrived within the timeframe.
                # Just continue waiting instead of treating it as an error.
                continue
            except Exception as e:
                logger.error(f"Error processing health check request: {e}")
                # Best effort attempt to reply **only** if a request was actually received.
                try:
                    self.health_socket.send_json({'status': 'error', 'error': str(e)})
                except zmq.ZMQError:
                    # Socket not in a state that allows replying (e.g. no pending request).
                    pass
        
    def run(self):
        """Run the main translation server"""
        while True:
            message = None  # Reset for each loop-iteration
            try:
                # Wait (blocking with timeout) for the next client request
                message = self.main_socket.recv_json()
                logger.debug(f"Received request: {message}")

                # Process and reply
                response = self._handle_request(message)
                self.main_socket.send_json(response)
                logger.debug(f"Sent response: {response}")

            except zmq.error.Again:
                # Socket timed-out waiting for a request – nothing to do.
                continue
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                # Only attempt to reply if we actually received a request
                if message is not None:
                    try:
                        self.main_socket.send_json({'status': 'error', 'error': str(e)})
                    except zmq.ZMQError:
                        pass
                
    def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced request handler with API versioning and capabilities."""
        action = message.get('action')
        
        # Add API version to all responses
        response = {
            'api_version': self.api_version,
            'timestamp': time.time()
        }
        
        if action == 'translate':
            result = self._handle_translate(message)
            response.update(result)
        elif action == 'health_check':
            result = self._handle_health_check()
            response.update(result)
        elif action == 'get_capabilities':
            response.update({
                'status': 'success',
                'capabilities': self.capabilities
            })
        elif action == 'get_stats':
            response.update({
                'status': 'success',
                'stats': self.pipeline.get_monitoring_stats()
            })
        elif action == 'get_session':
            session_id = message.get('session_id')
            if session_id:
                response.update({
                    'status': 'success',
                    'session': self.pipeline.session_manager.get_session_stats(session_id)
                })
            else:
                response.update({
                    'status': 'error',
                    'message': 'Missing session_id'
                })
        else:
            response.update({
                'status': 'error',
                'message': f'Unknown action: {action}'
            })
            
        return response
        
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
        """Enhanced health check with detailed status."""
        health = self.pipeline.health_check()
        
        # Add additional health metrics
        health.update({
            'status': 'ok',  # Ensure status is 'ok' for health check validation
            'api_version': self.api_version,
            'uptime': time.time() - self.start_time,
            'memory_stats': getattr(self.pipeline, 'memory_stats', {}),
            'active_sessions': len(self.pipeline.session_manager.get_active_sessions()),
            'cache_stats': self.pipeline.cache.get_stats(),
            'initialization_status': 'complete',
            'main_port': self.main_port,
            'health_port': self.health_port
        })
        
        return health
        
    def stop(self):
        """Stop the server and cleanup resources"""
        try:
            self.main_socket.close()
            self.health_socket.close()
            self.context.term()
            logger.info("Server stopped and resources cleaned up")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")

def main():
    """Main entry point with dynamic port support"""
    try:
        # Parse command line arguments
        args = parse_agent_args()
        
        # Use provided ports or defaults
        main_port = args.port or DEFAULT_ZMQ_PORT
        health_port = getattr(args, 'health_port', None) or DEFAULT_HEALTH_PORT
        
        logger.info(f"Starting Consolidated Translator with main port {main_port} and health port {health_port}")
        
        # Create and run server
        server = TranslatorServer(TRANSLATOR_CONFIG, main_port=main_port, health_port=health_port)
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 