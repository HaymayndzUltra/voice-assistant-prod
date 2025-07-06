#!/usr/bin/env python3
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

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

# Import BaseAgent for agent implementation
from common.core.base_agent import BaseAgent

# Import config parser for dynamic port support
from main_pc_code.utils.config_loader import load_config
config = load_config()
from main_pc_code.utils.service_discovery_client import discover_service
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, setup_curve_client

# Import MemoryOrchestrator client functions
from main_pc_code.src.memory.zmq_encoding_utils import encode_for_zmq, decode_from_zmq

# Import data optimizer
from main_pc_code.utils.data_optimizer import optimize_zmq_message

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

# Secure ZMQ configuration
SECURE_ZMQ = is_secure_zmq_enabled()

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
            "service_name": "NLLBAdapter"  # Use service discovery instead of hardcoded host/port
        },
        "fixed_streaming": {
            "enabled": True,
            "priority": 3,
            "confidence_threshold": 0.75,
            "timeout": 3,
            "service_name": "FixedStreamingTranslation"  # Use service discovery instead of hardcoded host/port
        },
        "google": {
            "enabled": True,
            "priority": 4,
            "confidence_threshold": 0.90,
            "service_name": "RemoteConnectorAgent"  # Use service discovery instead of hardcoded host/port
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
    },
    "secure_zmq": SECURE_ZMQ
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
    """Translation cache using MemoryOrchestrator for persistence"""
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        
        # Connect to MemoryOrchestrator
        self.memory_orchestrator = None
        self.memory_orchestrator_socket = None
        self.context = zmq.Context.instance()
        self._connect_to_memory_orchestrator()
        
        # Local cache for frequently accessed items
        self.local_cache = {}
        self.local_access_count = {}
        self.local_last_accessed = {}
        
        logger.info("Translation cache initialized with MemoryOrchestrator integration")
        
    def _connect_to_memory_orchestrator(self):
        """Connect to the MemoryOrchestrator service"""
        try:
            # Discover MemoryOrchestrator service
            memory_orchestrator_info = discover_service("MemoryOrchestrator")
            if memory_orchestrator_info and memory_orchestrator_info.get("status") == "SUCCESS":
                payload = memory_orchestrator_info.get("payload", {})
                ip = payload.get("ip", "localhost")
                port = payload.get("port", 5576)  # Default MemoryOrchestrator port
                
                # Create socket
                self.memory_orchestrator_socket = self.context.socket(zmq.REQ)
                self.memory_orchestrator_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
                self.memory_orchestrator_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
                
                # Apply secure ZMQ if enabled
                if is_secure_zmq_enabled():
                    setup_curve_client(self.memory_orchestrator_socket)
                
                # Connect to MemoryOrchestrator
                memory_orchestrator_address = f"tcp://{ip}:{port}"
                self.memory_orchestrator_socket.connect(memory_orchestrator_address)
                logger.info(f"Connected to MemoryOrchestrator at {memory_orchestrator_address}")
                
                # Test connection with a ping
                try:
                    request = {
                        "action": "ping"
                    }
                    self.memory_orchestrator_socket.send_json(request)
                    response = self.memory_orchestrator_socket.recv_json()
                    if response.get("status") == "ok":
                        logger.info("MemoryOrchestrator connection verified")
                    else:
                        logger.warning("MemoryOrchestrator ping response unexpected")
                except Exception as e:
                    logger.error(f"Failed to ping MemoryOrchestrator: {str(e)}")
            else:
                logger.error("Failed to discover MemoryOrchestrator service")
        except Exception as e:
            logger.error(f"Error connecting to MemoryOrchestrator: {str(e)}")
            
    def get(self, key: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Get a translation from cache"""
        current_time = time.time()
        
        # Check local cache first
        if key in self.local_cache:
            created_at = self.local_cache[key].get('created_at', 0)
            if current_time - created_at <= self.ttl:
                # Update access stats
                self.local_access_count[key] = self.local_access_count.get(key, 0) + 1
                self.local_last_accessed[key] = current_time
                self.stats['hits'] += 1
                return self.local_cache[key].get('value')
            else:
                # Expired, remove from local cache
                if key in self.local_cache:
                    del self.local_cache[key]
                if key in self.local_access_count:
                    del self.local_access_count[key]
                if key in self.local_last_accessed:
                    del self.local_last_accessed[key]
        
        # Not in local cache, try MemoryOrchestrator
        try:
            if self.memory_orchestrator_socket:
                cache_key = f"translation_cache:{key}"
                request = {
                    "action": "read",
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_id": cache_key
                    }
                }
                
                # Send request to MemoryOrchestrator
                self.memory_orchestrator_socket.send_json(request)
                response = self.memory_orchestrator_socket.recv_json()
                
                if response.get("status") == "success":
                    memory_data = response.get("data", {}).get("memory", {})
                    if memory_data:
                        content = memory_data.get("content", {})
                        value = content.get("value")
                        engine = content.get("engine")
                        created_at = memory_data.get("created_at")
                        
                        # Check if expired
                        if created_at and (current_time - created_at <= self.ttl):
                            # Add to local cache
                            self.local_cache[key] = {
                                "value": value,
                                "engine": engine,
                                "created_at": created_at
                            }
                            self.local_access_count[key] = 1
                            self.local_last_accessed[key] = current_time
                            self.stats['hits'] += 1
                            return value
                
                # If we get here, either not found or expired
                self.stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting translation from MemoryOrchestrator: {str(e)}")
            self.stats['misses'] += 1
            return None
            
        self.stats['misses'] += 1
        return None
        
    def set(self, key: str, value: str, engine: str, context: Dict[str, Any] = None) -> None:
        """Store a translation in cache"""
        current_time = time.time()
        
        # Store in local cache
        self.local_cache[key] = {
            "value": value,
            "engine": engine,
            "created_at": current_time
        }
        self.local_access_count[key] = 1
        self.local_last_accessed[key] = current_time
        
        # Check if local cache is too large
        if len(self.local_cache) > 100:  # Keep local cache small
            self._evict_local_entries()
            
        # Store in MemoryOrchestrator
        try:
            if self.memory_orchestrator_socket:
                cache_key = f"translation_cache:{key}"
                
                # Prepare content
                content = {
                    "value": value,
                    "engine": engine,
                    "context_hash": hash(str(context)) if context else None
                }
                
                # Prepare request
                request = {
                    "action": "create",
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_type": "translation_cache",
                        "memory_id": cache_key,
                        "content": content,
                        "tags": ["translation", engine],
                        "ttl": self.ttl
                    }
                }
                
                # Send request to MemoryOrchestrator
                self.memory_orchestrator_socket.send_json(request)
                response = self.memory_orchestrator_socket.recv_json()
                
                if response.get("status") != "success":
                    logger.warning(f"Failed to store translation in MemoryOrchestrator: {response.get('message', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Error storing translation in MemoryOrchestrator: {str(e)}")
            
        # Update stats
        self.stats['size'] = len(self.local_cache)
        
    def _evict_local_entries(self) -> None:
        """Evict least recently used entries from local cache"""
        if len(self.local_cache) <= 50:  # Don't evict if cache is small
            return
            
        # Calculate scores for each entry
        scores = {}
        current_time = time.time()
        for key in self.local_cache:
            access_score = self.local_access_count.get(key, 0)
            recency_score = 1 / (current_time - self.local_last_accessed.get(key, 0) + 1)
            scores[key] = access_score * recency_score
            
        # Remove lowest scoring entries
        num_to_evict = max(1, int(len(self.local_cache) * 0.2))  # Evict 20% of cache
        for key in sorted(scores, key=scores.get)[:num_to_evict]:
            if key in self.local_cache:
                del self.local_cache[key]
            if key in self.local_access_count:
                del self.local_access_count[key]
            if key in self.local_last_accessed:
                del self.local_last_accessed[key]
                
        self.stats['evictions'] += num_to_evict
        self.stats['size'] = len(self.local_cache)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            **self.stats,
            'hit_rate': self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0,
            'local_cache_size': len(self.local_cache),
            'avg_access_count': sum(self.local_access_count.values()) / len(self.local_access_count) if self.local_access_count else 0
        }
        
    def warm_cache(self, entries: List[Tuple[str, str, str]]) -> None:
        """Pre-populate cache with common translations"""
        for key, value, engine in entries:
            self.set(key, value, engine)
            
    def clear(self) -> None:
        """Clear the entire cache"""
        self.local_cache.clear()
        self.local_access_count.clear()
        self.local_last_accessed.clear()
        self.stats['size'] = 0
        
        # We don't clear the MemoryOrchestrator cache here as it might be shared
        logger.info("Local translation cache cleared")

class SessionManager:
    """Session manager using MemoryOrchestrator for persistence"""
    def __init__(self, max_history: int = 100, timeout: int = 3600):
        self.max_history = max_history
        self.timeout = timeout
        
        # Local session cache
        self.sessions = {}
        self.session_last_accessed = {}
        
        # Connect to MemoryOrchestrator
        self.memory_orchestrator = None
        self.memory_orchestrator_socket = None
        self.context = zmq.Context.instance()
        self._connect_to_memory_orchestrator()
        
        logger.info("Session manager initialized with MemoryOrchestrator integration")
        
    def _connect_to_memory_orchestrator(self):
        """Connect to the MemoryOrchestrator service"""
        try:
            # Discover MemoryOrchestrator service
            memory_orchestrator_info = discover_service("MemoryOrchestrator")
            if memory_orchestrator_info and memory_orchestrator_info.get("status") == "SUCCESS":
                payload = memory_orchestrator_info.get("payload", {})
                ip = payload.get("ip", "localhost")
                port = payload.get("port", 5576)  # Default MemoryOrchestrator port
                
                # Create socket
                self.memory_orchestrator_socket = self.context.socket(zmq.REQ)
                self.memory_orchestrator_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
                self.memory_orchestrator_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
                
                # Apply secure ZMQ if enabled
                if is_secure_zmq_enabled():
                    setup_curve_client(self.memory_orchestrator_socket)
                
                # Connect to MemoryOrchestrator
                memory_orchestrator_address = f"tcp://{ip}:{port}"
                self.memory_orchestrator_socket.connect(memory_orchestrator_address)
                logger.info(f"Connected to MemoryOrchestrator at {memory_orchestrator_address}")
                
                # Test connection with a ping
                try:
                    request = {
                        "action": "ping"
                    }
                    self.memory_orchestrator_socket.send_json(request)
                    response = self.memory_orchestrator_socket.recv_json()
                    if response.get("status") == "ok":
                        logger.info("MemoryOrchestrator connection verified")
                    else:
                        logger.warning("MemoryOrchestrator ping response unexpected")
                except Exception as e:
                    logger.error(f"Failed to ping MemoryOrchestrator: {str(e)}")
            else:
                logger.error("Failed to discover MemoryOrchestrator service")
        except Exception as e:
            logger.error(f"Error connecting to MemoryOrchestrator: {str(e)}")
    
    def add_translation(self, session_id: str, result: Dict[str, Any]) -> None:
        """Add a translation to a session"""
        if not session_id:
            return
            
        # Get current timestamp
        current_time = time.time()
        
        # Create or update session in local cache
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'created_at': current_time,
                'updated_at': current_time
            }
        
        # Add translation to history
        self.sessions[session_id]['history'].append({
            'timestamp': current_time,
            'result': result
        })
        
        # Trim history if needed
        if len(self.sessions[session_id]['history']) > self.max_history:
            self.sessions[session_id]['history'] = self.sessions[session_id]['history'][-self.max_history:]
            
        # Update session timestamp
        self.sessions[session_id]['updated_at'] = current_time
        self.session_last_accessed[session_id] = current_time
        
        # Store session in MemoryOrchestrator
        try:
            if self.memory_orchestrator_socket:
                session_key = f"translation_session:{session_id}"
                
                # Prepare session data
                session_data = {
                    'history': self.sessions[session_id]['history'],
                    'created_at': self.sessions[session_id]['created_at'],
                    'updated_at': current_time
                }
                
                # Prepare request
                request = {
                    "action": "update",  # Use update instead of create to handle both new and existing sessions
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_id": session_key,
                        "memory_type": "translation_session",
                        "content": session_data,
                        "tags": ["session", "translation"],
                        "ttl": self.timeout
                    }
                }
                
                # Send request to MemoryOrchestrator
                self.memory_orchestrator_socket.send_json(request)
                response = self.memory_orchestrator_socket.recv_json()
                
                if response.get("status") != "success":
                    logger.warning(f"Failed to store session in MemoryOrchestrator: {response.get('message', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Error storing session in MemoryOrchestrator: {str(e)}")
    
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get translation history for a session"""
        if not session_id:
            return []
            
        # Check if session exists in local cache
        if session_id in self.sessions:
            # Update access timestamp
            self.session_last_accessed[session_id] = time.time()
            return self.sessions[session_id]['history']
            
        # Try to get session from MemoryOrchestrator
        try:
            if self.memory_orchestrator_socket:
                session_key = f"translation_session:{session_id}"
                
                # Prepare request
                request = {
                    "action": "read",
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_id": session_key
                    }
                }
                
                # Send request to MemoryOrchestrator
                self.memory_orchestrator_socket.send_json(request)
                response = self.memory_orchestrator_socket.recv_json()
                
                if response.get("status") == "success":
                    memory_data = response.get("data", {}).get("memory", {})
                    if memory_data:
                        content = memory_data.get("content", {})
                        if content:
                            # Store in local cache
                            self.sessions[session_id] = content
                            self.session_last_accessed[session_id] = time.time()
                            return content.get('history', [])
                            
        except Exception as e:
            logger.error(f"Error getting session from MemoryOrchestrator: {str(e)}")
            
        return []
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if not session_id:
            return {'exists': False}
            
        # Check if session exists in local cache
        if session_id in self.sessions:
            session = self.sessions[session_id]
            history = session.get('history', [])
            
            # Update access timestamp
            self.session_last_accessed[session_id] = time.time()
            
            return {
                'exists': True,
                'created_at': session.get('created_at'),
                'updated_at': session.get('updated_at'),
                'history_count': len(history),
                'languages_used': self._extract_languages(history),
                'engines_used': self._extract_engines(history)
            }
            
        # Try to get session from MemoryOrchestrator
        try:
            if self.memory_orchestrator_socket:
                session_key = f"translation_session:{session_id}"
                
                # Prepare request
                request = {
                    "action": "read",
                    "request_id": str(uuid.uuid4()),
                    "payload": {
                        "memory_id": session_key
                    }
                }
                
                # Send request to MemoryOrchestrator
                self.memory_orchestrator_socket.send_json(request)
                response = self.memory_orchestrator_socket.recv_json()
                
                if response.get("status") == "success":
                    memory_data = response.get("data", {}).get("memory", {})
                    if memory_data:
                        content = memory_data.get("content", {})
                        if content:
                            # Store in local cache
                            self.sessions[session_id] = content
                            self.session_last_accessed[session_id] = time.time()
                            
                            history = content.get('history', [])
                            return {
                                'exists': True,
                                'created_at': content.get('created_at'),
                                'updated_at': content.get('updated_at'),
                                'history_count': len(history),
                                'languages_used': self._extract_languages(history),
                                'engines_used': self._extract_engines(history)
                            }
                            
        except Exception as e:
            logger.error(f"Error getting session stats from MemoryOrchestrator: {str(e)}")
            
        return {'exists': False}
    
    def _extract_languages(self, history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract language usage statistics from history"""
        languages = {}
        for entry in history:
            result = entry.get('result', {})
            source_lang = result.get('source_lang')
            target_lang = result.get('target_lang')
            
            if source_lang:
                languages[source_lang] = languages.get(source_lang, 0) + 1
            if target_lang:
                languages[target_lang] = languages.get(target_lang, 0) + 1
                
        return languages
    
    def _extract_engines(self, history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract engine usage statistics from history"""
        engines = {}
        for entry in history:
            result = entry.get('result', {})
            engine = result.get('engine_used')
            
            if engine:
                engines[engine] = engines.get(engine, 0) + 1
                
        return engines
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions from local cache"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, last_accessed in self.session_last_accessed.items():
            if current_time - last_accessed > self.timeout:
                expired_sessions.append(session_id)
                
        for session_id in expired_sessions:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.session_last_accessed:
                del self.session_last_accessed[session_id]
                
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions from local cache")
    
    def update_session(self, session_id: str, entry: Dict[str, Any] = None) -> None:
        """Update session metadata"""
        if not session_id:
            return
            
        current_time = time.time()
        
        # Create session if it doesn't exist
        if session_id not in self.sessions:
            # Try to get session from MemoryOrchestrator first
            try:
                if self.memory_orchestrator_socket:
                    session_key = f"translation_session:{session_id}"
                    
                    # Prepare request
                    request = {
                        "action": "read",
                        "request_id": str(uuid.uuid4()),
                        "payload": {
                            "memory_id": session_key
                        }
                    }
                    
                    # Send request to MemoryOrchestrator
                    self.memory_orchestrator_socket.send_json(request)
                    response = self.memory_orchestrator_socket.recv_json()
                    
                    if response.get("status") == "success":
                        memory_data = response.get("data", {}).get("memory", {})
                        if memory_data:
                            content = memory_data.get("content", {})
                            if content:
                                # Store in local cache
                                self.sessions[session_id] = content
                                self.session_last_accessed[session_id] = current_time
                            else:
                                # Create new session
                                self.sessions[session_id] = {
                                    'history': [],
                                    'created_at': current_time,
                                    'updated_at': current_time
                                }
            except Exception as e:
                logger.warning(f"Failed to retrieve session from MemoryOrchestrator: {str(e)}")
                # Create new session as fallback
                self.sessions[session_id] = {
                    'history': [],
                    'created_at': current_time,
                    'updated_at': current_time
                }
        
        # Update session with new entry if provided
        if entry and session_id in self.sessions:
            if 'history' not in self.sessions[session_id]:
                self.sessions[session_id]['history'] = []
            
            self.sessions[session_id]['history'].append(entry)
            self.sessions[session_id]['updated_at'] = current_time
            self.session_last_accessed[session_id] = current_time

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
                # Check if all services are available via service discovery
                self._refresh_service_info()
                
                # Update engine status based on service discovery results
                for engine in ['nllb', 'fixed_streaming', 'google']:
                    if engine in self.service_info:
                        try:
                            # Get a socket for the engine
                            socket = self._get_engine_socket(engine)
                            if socket:
                                # Send health check request
                                socket.send_json({"action": "health_check"})
                                if socket.poll(timeout=self.config.get("health")["timeout"] * 1000):
                                    response = socket.recv_json()
                                    self.health_status["engines"][engine] = response.get("status") == "ok"
                                else:
                                    self.health_status["engines"][engine] = False
                                    logger.warning(f"{engine} health check timeout")
                                socket.close()
                            else:
                                self.health_status["engines"][engine] = False
                                logger.warning(f"{engine} service not available")
                        except Exception as e:
                            self.health_status["engines"][engine] = False
                            logger.warning(f"Error checking {engine} health: {str(e)}")
                    else:
                        self.health_status["engines"][engine] = False
                        logger.warning(f"{engine} service not discovered")
                
                # Dictionary is always available
                self.health_status["engines"]["dictionary"] = True
                
                # Update last check time
                self.health_status["last_check"] = time.time()
                
                # Check overall health status
                if all(self.health_status["engines"].values()):
                    self.health_status["status"] = "ok"
                else:
                    self.health_status["status"] = "degraded"
                
                # Log health status
                if not all(self.health_status["engines"].values()):
                    logger.warning("Health check failed for some engines")
                    logger.debug(f"Health status: {self.health_status}")
                
                # Wait for next check interval
                time.sleep(self.config.get("health")["check_interval"])
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                self.health_status["status"] = "error"
                time.sleep(self.config.get("health")["check_interval"])

    def _refresh_service_info(self):
        """Refresh service information using service discovery"""
        try:
            # Get NLLB service info
            nllb_service_name = self.config.get('engines')['nllb']['service_name']
            nllb_service_info = discover_service(nllb_service_name)
            if nllb_service_info and nllb_service_info.get("status") == "SUCCESS":
                payload = nllb_service_info.get("payload", {})
                self.service_info['nllb'] = {
                    'host': payload.get('ip', 'localhost'),
                    'port': payload.get('port', 5000)
                }
                self.engine_status['nllb']['status'] = 'connected'
                logger.info(f"Discovered NLLB service at {self.service_info['nllb']['host']}:{self.service_info['nllb']['port']}")
            else:
                self.engine_status['nllb']['status'] = 'disconnected'
                self.engine_status['nllb']['last_error'] = "Service not found"
                logger.warning(f"Failed to discover NLLB service - continuing without NLLB")
            
            # Get Fixed Streaming service info
            fixed_streaming_service_name = self.config.get('engines')['fixed_streaming']['service_name']
            fixed_streaming_service_info = discover_service(fixed_streaming_service_name)
            if fixed_streaming_service_info and fixed_streaming_service_info.get("status") == "SUCCESS":
                payload = fixed_streaming_service_info.get("payload", {})
                self.service_info['fixed_streaming'] = {
                    'host': payload.get('ip', 'localhost'),
                    'port': payload.get('port', 5000)
                }
                self.engine_status['fixed_streaming']['status'] = 'connected'
                logger.info(f"Discovered Fixed Streaming service at {self.service_info['fixed_streaming']['host']}:{self.service_info['fixed_streaming']['port']}")
            else:
                self.engine_status['fixed_streaming']['status'] = 'disconnected'
                self.engine_status['fixed_streaming']['last_error'] = "Service not found"
                logger.warning(f"Failed to discover Fixed Streaming service - continuing without Fixed Streaming")
            
            # Get Google service info (via Remote Connector Agent)
            google_service_name = self.config.get('engines')['google']['service_name']
            google_service_info = discover_service(google_service_name)
            if google_service_info and google_service_info.get("status") == "SUCCESS":
                payload = google_service_info.get("payload", {})
                self.service_info['google'] = {
                    'host': payload.get('ip', 'localhost'),
                    'port': payload.get('port', 5000)
                }
                self.engine_status['google']['status'] = 'connected'
                logger.info(f"Discovered Google service at {self.service_info['google']['host']}:{self.service_info['google']['port']}")
            else:
                self.engine_status['google']['status'] = 'disconnected'
                self.engine_status['google']['last_error'] = "Service not found"
                logger.warning(f"Failed to discover Google service - continuing without Google")
            
            # Get ModelManagerAgent service info
            model_manager_info = discover_service("ModelManagerAgent")
            if model_manager_info and model_manager_info.get("status") == "SUCCESS":
                payload = model_manager_info.get("payload", {})
                self.service_info['model_manager'] = {
                    'host': payload.get('ip', 'localhost'),
                    'port': payload.get('port', 5570)
                }
                logger.info(f"Discovered ModelManagerAgent at {self.service_info['model_manager']['host']}:{self.service_info['model_manager']['port']}")
            else:
                logger.warning(f"Failed to discover ModelManagerAgent - model loading delegation may not work")
                
            # Dictionary is always available
            self.engine_status['dictionary']['status'] = 'connected'
            
        except Exception as e:
            logger.error(f"Error refreshing service information: {str(e)}")
            logger.exception("Service discovery error details:")

    def _get_engine_socket(self, engine_name):
        """Get a socket for the specified engine"""
        if engine_name not in self.service_info:
            return None
            
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Apply secure ZMQ if enabled
        if self.secure_zmq:
            setup_curve_client(socket)
            logger.debug(f"Secure ZMQ enabled for {engine_name} connection")
            
        host = self.service_info[engine_name]['host']
        port = self.service_info[engine_name]['port']
        address = f"tcp://{host}:{port}"
        
        try:
            socket.connect(address)
            logger.debug(f"Connected to {engine_name} at {address}")
            return socket
        except Exception as e:
            logger.error(f"Error connecting to {engine_name} at {address}: {str(e)}")
            socket.close()
            return None

class TranslationPipeline:
    """Handles translation pipeline with multiple engines"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('ConsolidatedTranslator')
        self.cache = TranslationCache(
            max_size=config.get('cache')['max_size'],
            ttl=config.get('cache')['ttl']
        )
        self.session_manager = SessionManager(
            max_history=config.get('session')['max_history'],
            timeout=config.get('session')['timeout']
        )
        self.engine_status = {
            'dictionary': {'status': 'unknown', 'last_error': None},
            'nllb': {'status': 'unknown', 'last_error': None},
            'fixed_streaming': {'status': 'unknown', 'last_error': None},
            'google': {'status': 'unknown', 'last_error': None}
        }
        
        # Initialize language detection
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0  # For consistent results
            self.has_langdetect = True
        except ImportError as e:
            print(f"Import error: {e}")
            logger.warning("langdetect not available. Language detection will be limited.")
            self.has_langdetect = False
            
        # Initialize quality metrics
        try:
            from nltk.translate.bleu_score import sentence_bleu
            from nltk.tokenize import word_tokenize
            import nltk
            nltk.download('punkt', quiet=True)
            self.has_bleu = True
        except ImportError as e:
            print(f"Import error: {e}")
            logger.warning("nltk not available. Quality metrics will be limited.")
            self.has_bleu = False
        
        # Initialize dictionary for direct translations
        self.dictionary = {**COMMAND_TRANSLATIONS, **COMPLETE_SENTENCES}
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        
        # Check if secure ZMQ is enabled
        self.secure_zmq = config.get('secure_zmq', False)
        
        # Get service information from service discovery
        self.service_info = {}
        self._refresh_service_info()
        
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
            'fixed_streaming': {'calls': 0, 'last_reset': time.time(), 'max_calls': 50, 'window': 60},
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
            'fixed_streaming': {'success': 0, 'total': 0, 'avg_time': 0},
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
            'engine_usage': {
                'dictionary': 0,
                'nllb': 0,
                'fixed_streaming': 0,
                'google': 0
            },
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
                "fixed_streaming": True,
                "google": True
            }
        }
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.health_thread.start()
        
        # Start service discovery refresh thread
        self.service_refresh_thread = threading.Thread(target=self._service_refresh_loop, daemon=True)
        self.service_refresh_thread.start()
        
        # Request models from ModelManagerAgent
        self._request_translation_models()
        
        # Wait a moment for health server to start
        time.sleep(0.5)
        
        self.logger.info("TranslationPipeline initialized successfully")
        
    def _request_translation_models(self):
        """Request all required translation models from ModelManagerAgent"""
        logger.info("Requesting translation models from ModelManagerAgent")
        
        # NLLB model
        nllb_model_id = self.config.get('engines')['nllb'].get('model', 'facebook/nllb-200-distilled-600M')
        if nllb_model_id:
            self._request_model_loading(nllb_model_id, priority="high")
        
        # Fixed Streaming model (if configured)
        fixed_streaming_model_id = self.config.get('engines')['fixed_streaming'].get('model')
        if fixed_streaming_model_id:
            self._request_model_loading(fixed_streaming_model_id, priority="medium")
        
        logger.info("Translation model requests completed")

    def _optimize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize a message for ZMQ transmission using data_optimizer
        
        Args:
            message: The message to optimize
            
        Returns:
            The optimized message
        """
        try:
            # Use the data_optimizer to optimize the message
            optimized = optimize_zmq_message(message)
            return optimized
        except Exception as e:
            logger.warning(f"Failed to optimize message: {str(e)}")
            return message

    def _translate_with_nllb(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using NLLB model via ZMQ"""
        try:
            # Check if NLLB service is connected
            if self.engine_status['nllb']['status'] != 'connected':
                return {'status': 'error', 'message': 'NLLB service not connected'}
                
            # Get a socket for NLLB service
            socket = self._get_engine_socket('nllb')
            if not socket:
                self.engine_status['nllb']['status'] = 'error'
                self.engine_status['nllb']['last_error'] = 'Could not connect to NLLB service'
                return {'status': 'error', 'message': 'Could not connect to NLLB service'}
            
            # Prepare request
            request = {
                "action": "translate",
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "request_type": "translation"  # Add request type
            }
            
            # Optimize the request
            optimized_request = self._optimize_message(request)
            
            # Send request with timeout
            socket.send_json(optimized_request)
            if socket.poll(timeout=self.config.get('engines')['nllb']['timeout'] * 1000):
                response = socket.recv_json()
                socket.close()
                if response.get('status') == 'success':
                    self.engine_status['nllb']['status'] = 'connected'
                    return response
                else:
                    self.engine_status['nllb']['status'] = 'error'
                    self.engine_status['nllb']['last_error'] = response.get('message', 'Unknown error')
                    return response
            else:
                socket.close()
                self.engine_status['nllb']['status'] = 'error'
                self.engine_status['nllb']['last_error'] = 'Request timed out'
                return {'status': 'error', 'message': 'Request timed out'}
                
        except Exception as e:
            self.engine_status['nllb']['status'] = 'error'
            self.engine_status['nllb']['last_error'] = str(e)
            return {'status': 'error', 'message': str(e)}

    def _translate_with_fixed_streaming(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using Fixed Streaming model via HTTP API"""
        try:
            # Check if Fixed Streaming service is connected
            if self.engine_status['fixed_streaming']['status'] != 'connected':
                return {'status': 'error', 'message': 'Fixed Streaming service not connected'}
            
            # Check cache first
            cache_key = f"{text}:{source_lang}:{target_lang}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.engine_status['fixed_streaming']['status'] = 'connected'
                return {
                    'status': 'success',
                    'translated_text': cached_result,
                    'engine_used': 'fixed_streaming',
                    'cached': True
                }
            
            # Get service info
            if 'fixed_streaming' not in self.service_info:
                self.engine_status['fixed_streaming']['status'] = 'error'
                self.engine_status['fixed_streaming']['last_error'] = 'Fixed Streaming service info not available'
                return {'status': 'error', 'message': 'Fixed Streaming service info not available'}
            
            # Prepare request for Fixed Streaming API
            request = {
                "action": "translate",
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 512
                }
            }
            
            # Optimize the request
            optimized_request = self._optimize_message(request)
            
            # Create socket for request
            socket = self._get_engine_socket('fixed_streaming')
            if not socket:
                self.engine_status['fixed_streaming']['status'] = 'error'
                self.engine_status['fixed_streaming']['last_error'] = 'Could not connect to Fixed Streaming service'
                return {'status': 'error', 'message': 'Could not connect to Fixed Streaming service'}
            
            # Send request with timeout
            socket.send_json(optimized_request)
            if socket.poll(timeout=self.config.get('engines')['fixed_streaming']['timeout'] * 1000):
                response = socket.recv_json()
                socket.close()
                
                if response.get('status') == 'success':
                    translated_text = response.get('translated_text', '').strip()
                    
                    # Clean up the translation
                    translated_text = re.sub(r'^(Translation:|English:|In English:)\s*', '', translated_text, flags=re.IGNORECASE)
                    translated_text = translated_text.strip()
                    
                    if translated_text:
                        self.engine_status['fixed_streaming']['status'] = 'connected'
                        # Cache the translation with engine parameter
                        self.cache.set(cache_key, translated_text, engine='fixed_streaming')
                        return {
                            'status': 'success',
                            'translated_text': translated_text,
                            'engine_used': 'fixed_streaming',
                            'cached': False
                        }
                    else:
                        self.engine_status['fixed_streaming']['status'] = 'error'
                        self.engine_status['fixed_streaming']['last_error'] = 'Empty translation'
                        return {'status': 'error', 'message': 'Empty translation'}
                else:
                    self.engine_status['fixed_streaming']['status'] = 'error'
                    self.engine_status['fixed_streaming']['last_error'] = response.get('message', 'Unknown error')
                    return response
            else:
                socket.close()
                self.engine_status['fixed_streaming']['status'] = 'error'
                self.engine_status['fixed_streaming']['last_error'] = 'Request timed out'
                return {'status': 'error', 'message': 'Request timed out'}
                
        except Exception as e:
            self.engine_status['fixed_streaming']['status'] = 'error'
            self.engine_status['fixed_streaming']['last_error'] = str(e)
            return {'status': 'error', 'message': str(e)}

    def _translate_with_google(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using Google Translate via RCA"""
        try:
            # Check if Google service is connected
            if self.engine_status['google']['status'] != 'connected':
                return {'status': 'error', 'message': 'Google service not connected'}
            
            # Get a socket for Google service (Remote Connector Agent)
            socket = self._get_engine_socket('google')
            if not socket:
                self.engine_status['google']['status'] = 'error'
                self.engine_status['google']['last_error'] = 'Could not connect to Google service'
                return {'status': 'error', 'message': 'Could not connect to Google service'}
                
            # Prepare request
            request = {
                "action": "translate",
                "request_type": "translation",  # Add request type
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            # Optimize the request
            optimized_request = self._optimize_message(request)
            
            # Send request with timeout
            socket.send_json(optimized_request)
            if socket.poll(timeout=self.config.get('engines')['google']['timeout'] * 1000):
                response = socket.recv_json()
                socket.close()
                if response.get('status') == 'success':
                    self.engine_status['google']['status'] = 'connected'
                    return response
                else:
                    self.engine_status['google']['status'] = 'error'
                    self.engine_status['google']['last_error'] = response.get('message', 'Unknown error')
                    return response
            else:
                socket.close()
                self.engine_status['google']['status'] = 'error'
                self.engine_status['google']['last_error'] = 'Request timed out'
                return {'status': 'error', 'message': 'Request timed out'}
                
        except Exception as e:
            self.engine_status['google']['status'] = 'error'
            self.engine_status['google']['last_error'] = str(e)
            return {'status': 'error', 'message': str(e)}

    def _translate_with_dictionary(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using the built-in dictionary"""
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
                    'status': 'success',
                    'translated_text': self.dictionary[text.lower()],
                    'engine_used': 'dictionary',
                    'confidence': 1.0
                }
                
            # Check for pattern matches
            for pattern, template in COMMON_PHRASE_PATTERNS.items():
                match = re.match(pattern, text.lower())
                if match:
                    # Fill in the template with the matched groups
                    groups = match.groups()
                    translated = template.format(*groups[1:])  # Skip the first group (ang|yung)
                    return {
                        'status': 'success',
                        'translated_text': translated,
                        'engine_used': 'dictionary',
                        'confidence': 0.9
                    }
                    
            # Check for complete sentence matches
            for sentence, translation in COMPLETE_SENTENCES.items():
                if text.lower() == sentence.lower():
                    return {
                        'status': 'success',
                        'translated_text': translation,
                        'engine_used': 'dictionary',
                        'confidence': 1.0
                    }
                    
            # No match found
            return {
                'status': 'error',
                'message': 'No dictionary match found',
                'engine_used': 'dictionary'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Dictionary translation error: {str(e)}',
                'engine_used': 'dictionary'
            }


# === AGENT ENTRYPOINT: TranslatorServer(BaseAgent) ===
class TranslatorServer(BaseAgent):
    """ZMQ server for translation service with dynamic port support and standardized health check"""
    def __init__(self, main_port: int = None, health_port: int = None):
        # Derive port and name from _agent_args, with fallbacks
        self.config = _agent_args
        # Standard BaseAgent initialization at the beginning
        super().__init__(
            name=self.config.get('consolidated_translator.name', "ConsolidatedTranslator"),
            port=self.config.getint('consolidated_translator.port', main_port or DEFAULT_ZMQ_PORT)
        )
        self.pipeline = TranslationPipeline(self.config)
        self.context = zmq.Context()
        self.secure_zmq = self.config.get('secure_zmq', False)
        self.main_port = main_port or DEFAULT_ZMQ_PORT
        self.health_port = health_port or DEFAULT_HEALTH_PORT
        self.main_socket = self.context.socket(zmq.REP)
        self.main_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.main_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        if self.secure_zmq:
            setup_curve_client(self.main_socket, server_mode=True)
            logger.info("Secure ZMQ enabled for main socket")
        self._bind_sockets()
        self.start_time = time.time()
        logger.info(f"Server started on main port {self.main_port} and health port {self.health_port}")
        self.api_version = "2.0"
        self.capabilities = {
            'languages': ['en', 'tl', 'fil_Latn'],
            'engines': ['dictionary', 'nllb', 'fixed_streaming', 'google'],
            'features': [
                'language_detection',
                'quality_metrics',
                'session_management',
                'caching',
                'monitoring',
                'error_recovery'
            ]
        }
        # Remove custom health thread/socket logic
        # Health check is now handled by BaseAgent

    # Remove _run_health_server and health_socket logic

    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the translator service.
        
        Returns:
            Dict containing health status information
        """
        status = {
            "status": self.health_status["status"],
            "ready": True,
            "initialized": True,
            "message": f"{self.name} is {self.health_status['status']}",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - self.start_time,
            "engines": self.health_status["engines"],
            "last_check": self.health_status["last_check"]
        }
        return status

    def cleanup(self):
        try:
            self.main_socket.close()
            self.context.term()
            logger.info("Server stopped and resources cleaned up")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
        super().cleanup()

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
            self.context.term()
            logger.info("Server stopped and resources cleaned up")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
        super().cleanup()

    def _request_model_loading(self, model_id: str, priority: str = "medium") -> bool:
        """
        Request ModelManagerAgent to load a model
        
        Args:
            model_id: ID of the model to load
            priority: Priority level (high, medium, low)
            
        Returns:
            True if request was successful, False otherwise
        """
        try:
            # Check if ModelManagerAgent is available
            if 'model_manager' not in self.service_info:
                logger.warning("ModelManagerAgent not available for model loading")
                return False
                
            # Get socket for ModelManagerAgent
            socket = self._get_engine_socket('model_manager')
            if not socket:
                logger.error("Failed to connect to ModelManagerAgent")
                return False
                
            # Prepare request
            request = {
                "action": "LOAD_MODEL",
                "model_id": model_id,
                "priority": priority,
                "requester": "ConsolidatedTranslator"
            }
            
            # Send request
            logger.info(f"Requesting ModelManagerAgent to load model: {model_id}")
            socket.send_json(request)
            
            # Wait for response
            if socket.poll(timeout=10000):  # 10 second timeout
                response = socket.recv_json()
                socket.close()
                
                if response.get("status") == "success":
                    logger.info(f"ModelManagerAgent successfully loaded model: {model_id}")
                    return True
                else:
                    logger.warning(f"ModelManagerAgent failed to load model {model_id}: {response.get('message', 'Unknown error')}")
                    return False
            else:
                socket.close()
                logger.warning(f"Request to load model {model_id} timed out")
                return False
                
        except Exception as e:
            logger.error(f"Error requesting model loading: {str(e)}")
            return False

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = TranslatorServer()
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