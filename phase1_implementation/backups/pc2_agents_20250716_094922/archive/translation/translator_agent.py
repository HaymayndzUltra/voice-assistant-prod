"""
Translator Agent - PC2 Enhanced Version
- Translates commands from Filipino to English
- Sits between listener and Enhanced Model Router
- Uses tiered translation approach with multiple fallbacks
- Maintains command context and session history
- Includes health monitoring endpoints
- Features enhanced Taglish detection and error recovery
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
import requests
import urllib.parse
import uuid
import socket
import random
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import re
from collections import deque

# --- Advanced normalization from translator_fixed.py ---
def normalize_text(text: str) -> str:
    """Basic text normalization with safety checks (from fixed agent)"""
    if text is None:
        logger.warning("normalize_text received None input, returning empty string")
        return ""
    try:
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\bi[-\s]', "i-", text)
        text = text.replace("i-on", "i-turn on")
        text = text.replace("i-off", "i-turn off")
        return text
    except Exception as e:
        logger.error(f"Error in normalize_text: {str(e)}")
        return text if isinstance(text, str) else ""

def normalize_text_for_cache(text: str) -> str:
    """Enhanced normalization for cache key generation (from fixed agent)"""
    if text is None:
        logger.warning("normalize_text_for_cache received None input, returning empty string")
        return ""
    text = normalize_text(text)
    text = text.lower()
    text = re.sub(r'[.,;!?"\(\)]', '', text)
    politeness_markers = [
        r'\bpo\b', r'\bho\b', r'\bba\b', r'\bnga\b', r'\bnaman\b', r'\blang\b', r'\bsana\b',
        r'\bdaw\b', r'\bkaya\b', r'\bkasi\b', r'\bpalang\b', r'\bnaman\b'
    ]
    for marker in politeness_markers:
        text = re.sub(marker, '', text)
    optional_words = [r'\bang\b', r'\bng\b', r'\bsi\b', r'\bni\b', r'\bsa\b', r'\bat\b', r'\bna\b', r'\bpa\b']
    for word in optional_words:
        text = re.sub(word, '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# EARLY LOGGING
try:
    with open("translator_agent_early.log", "a", encoding="utf-8") as f:
        f.write(f"[EARLY LOG {datetime.now()}] Translator agent script started.\n")
except Exception as e:
    pass

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
from pc2_code.config.system_config import get_config_for_service, get_config_for_machine
    except ImportError as e:
        print(f"Import error: {e}")
    AGENT_SERVICE_ID = "translator-agent-pc2"
    agent_config = get_config_for_service(AGENT_SERVICE_ID)
    pc2_general_config = get_config_for_machine("pc2")

    LOG_LEVEL = pc2_general_config.get('log_level', 'INFO')
    LOGS_DIR = Path(pc2_general_config.get('logs_dir', 'logs'))
    
    CONFIG_MAIN_PC_REP_PORT = agent_config.get('zmq_port', 5563)
    CONFIG_ZMQ_BIND_ADDRESS = agent_config.get('zmq_bind_address', "0.0.0.0")
    
    dependencies_config = agent_config.get('dependencies', {})
    CONFIG_USE_GOOGLE_TRANSLATE = dependencies_config.get('google_translate_api', False)
    nllb_adapter_service_id = dependencies_config.get('nllb_adapter_service_id')
    CONFIG_NLLB_ADAPTER_PORT = None
    CONFIG_NLLB_ADAPTER_HOST = "localhost" # Assuming NLLB adapter is on the same machine (PC2)
    CONFIG_TRANSLATOR_REQ_PORT = agent_config.get('translator_req_port', 5561)
    CONFIG_HEALTH_REP_PORT = agent_config.get('health_rep_port', 5559)

    if nllb_adapter_service_id:
        nllb_config = get_config_for_service(nllb_adapter_service_id)
        CONFIG_NLLB_ADAPTER_PORT = nllb_config.get('zmq_port', 5581)
        # If NLLB adapter binds to 0.0.0.0, localhost is fine. If specific IP, use that.
        # For now, keeping it simple with localhost as it's on PC2.

except ImportError as e:
    print(f"WARNING: Could not import system_config or parse settings: {e}. Using default/hardcoded settings for TranslatorAgent.")
    LOG_LEVEL = 'INFO'
    LOGS_DIR = Path('logs')
    CONFIG_MAIN_PC_REP_PORT = 5563
    CONFIG_ZMQ_BIND_ADDRESS = "0.0.0.0"
    CONFIG_USE_GOOGLE_TRANSLATE = True # Default to trying Google
    CONFIG_NLLB_ADAPTER_PORT = 5581 # Default NLLB port
    CONFIG_NLLB_ADAPTER_HOST = "localhost"
    CONFIG_TRANSLATOR_REQ_PORT = 5561
    CONFIG_HEALTH_REP_PORT = 5559

LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOGS_DIR / "translator_agent.log"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TranslatorAgent")

logger.info(f"TranslatorAgent Config: MainPort={CONFIG_MAIN_PC_REP_PORT}, BindAddr={CONFIG_ZMQ_BIND_ADDRESS}, GoogleTranslate={CONFIG_USE_GOOGLE_TRANSLATE}, NLLBPort={CONFIG_NLLB_ADAPTER_PORT}")

# These might still be needed if the agent retains its listener/router roles, adjust if necessary
# For now, assuming they are not configured via the new 'translator-agent-pc2' service entry
LISTENER_PORT = 5561 
ENHANCED_MODEL_ROUTER_PORT = 7602
MODEL_MANAGER_PORT = 5556  # Main PC's MMA port
MODEL_MANAGER_HOST = "192.168.1.1"  # Main PC's IP address

# --- Advanced session/cache/memory settings ---
MAX_SESSION_HISTORY = agent_config.get('max_session_history', 10)
SESSION_TIMEOUT_SECONDS = agent_config.get('session_timeout_seconds', 3600)
GOOGLE_TRANSLATE_TIMEOUT = agent_config.get('google_translate_timeout', 5)
CACHE_MAX_SIZE = agent_config.get('cache_max_size', 1000)
CACHE_PERSIST_PATH = str(LOGS_DIR / "translator_cache.pkl")
CACHE_CLEANUP_INTERVAL = agent_config.get('cache_cleanup_interval', 600)  # 10 min
MEMORY_MONITOR_INTERVAL = agent_config.get('memory_monitor_interval', 300)  # 5 min
MEMORY_USAGE_LIMIT_MB = agent_config.get('memory_usage_limit_mb', 900)

# --- Confidence thresholds (unchanged, still config-driven) ---
if agent_config and 'translation_confidence' in agent_config:
    conf_config = agent_config.get('translation_confidence', {})
    HIGH_CONF_THRESHOLD_PATTERN = conf_config.get('high_threshold_pattern', 0.98)
    MEDIUM_CONF_THRESHOLD_PATTERN = conf_config.get('medium_threshold_pattern', 0.85)
    HIGH_CONF_THRESHOLD_NLLB = conf_config.get('high_threshold_nllb', 0.85)
    MEDIUM_CONF_THRESHOLD_NLLB = conf_config.get('medium_threshold_nllb', 0.60)
    LOW_CONF_THRESHOLD = conf_config.get('low_threshold', 0.30)
    DEFAULT_GOOGLE_TRANSLATE_CONFIDENCE = conf_config.get('default_google_confidence', 0.90)
    logger.info(f"Loaded translation confidence thresholds from system_config.py")
    logger.debug(f"Confidence thresholds: Pattern={HIGH_CONF_THRESHOLD_PATTERN}, NLLB={HIGH_CONF_THRESHOLD_NLLB}, Low={LOW_CONF_THRESHOLD}")
else:
    HIGH_CONF_THRESHOLD_PATTERN = 0.98
    MEDIUM_CONF_THRESHOLD_PATTERN = 0.85
    HIGH_CONF_THRESHOLD_NLLB = 0.85
    MEDIUM_CONF_THRESHOLD_NLLB = 0.60
    LOW_CONF_THRESHOLD = 0.30
    DEFAULT_GOOGLE_TRANSLATE_CONFIDENCE = 0.90
    logger.warning("Using default confidence thresholds (not configured in system_config.py)")

USE_GOOGLE_TRANSLATE_FALLBACK = CONFIG_USE_GOOGLE_TRANSLATE

# HEALTH_CHECK_PORT = config.get('zmq.translator_health_port', 5559) # Deprecated, merged into main port

# Filipino command patterns and their English equivalents
COMMON_TRANSLATIONS = {
    "buksan": "open",
    "buksan mo": "open",
    "buksan mo ang": "open",
    "isara": "close",
    "isara mo": "close",
    "isara mo ang": "close",
    "i-save": "save",
    "i-save mo": "save",
    "i-save mo ang": "save",
    "gumawa": "create",
    "gumawa ng": "create",
    "gumawa ka ng": "create",
    "magsimula": "start",
    "magsimula ng": "start",
    "tumigil": "stop",
    "ihinto": "stop",
    "i-search": "search",
    "hanapin": "search",
    "hanapin mo": "search",
    "maghanap": "search",
    "maghanap ng": "search",
    "i-restart": "restart",
    "i-restart mo": "restart",
    "ayusin": "fix",
    "ayusin mo": "fix",
    "ayusin mo ang": "fix",
    "i-debug": "debug",
    "i-debug mo": "debug",
    "i-debug mo ang": "debug",
    "i-optimize": "optimize",
    "i-optimize mo": "optimize",
    "i-optimize mo ang": "optimize",
    "i-improve": "improve",
    "i-improve mo": "improve",
    "i-improve mo ang": "improve",
    "pagbutihin": "improve",
    "pagbutihin mo": "improve",
    "pagbutihin mo ang": "improve",
    "i-enhance": "enhance",
    "i-enhance mo": "enhance",
    "i-enhance mo ang": "enhance",
    "pagbutihin": "enhance",
    "pagbutihin mo": "enhance",
    "pagbutihin mo ang": "enhance",
    "i-upgrade": "upgrade",
    "i-upgrade mo": "upgrade",
    "i-upgrade mo ang": "upgrade",
    "i-update": "update",
    "i-update mo": "update",
    "i-update mo ang": "update",
    "i-refresh": "refresh",
    "i-refresh mo": "refresh",
    "i-refresh mo ang": "refresh",
    "i-reload": "reload",
    "i-reload mo": "reload",
    "i-reload mo ang": "reload",
    "i-restart": "restart",
    "i-restart mo": "restart",
    "i-restart mo ang": "restart",
    "i-reboot": "reboot",
    "i-reboot mo": "reboot",
    "i-reboot mo ang": "reboot",
    "i-shutdown": "shutdown",
    "i-shutdown mo": "shutdown",
    "i-shutdown mo ang": "shutdown",
    "i-turn off": "turn off",
    "i-turn off mo": "turn off",
    "i-turn off mo ang": "turn off",
    "patayin": "turn off",
    "patayin mo": "turn off",
    "patayin mo ang": "turn off",
    "i-turn on": "turn on",
    "i-turn on mo": "turn on",
    "i-turn on mo ang": "turn on",
    "i-power on": "power on",
    "i-power on mo": "power on",
    "i-power on mo ang": "power on",
    "i-power off": "power off",
    "i-power off mo": "power off",
    "i-power off mo ang": "power off",
    "patayin": "power off",
    "patayin mo": "power off",
    "patayin mo ang": "power off",
    "patayin mo ang": "power off",
    "i-check": "check",
    "i-check mo": "check",
    "tingnan": "check",
    "tingnan mo": "check",
    "ipakita": "show",
    "ipakita mo": "show",
    "ipakita mo ang": "show",
    "i-run": "run",
    "patakbuhin": "run",
    "patakbuhin mo": "run",
    "i-execute": "execute",
    "i-execute mo": "execute",
    "i-translate": "translate",
    "i-translate mo": "translate",
    "isalin": "translate",
    "isalin mo": "translate",
    "magsalita": "speak",
    "magsalita ka": "speak",
    "sabihin": "say",
    "sabihin mo": "say",
    "i-play": "play",
    "i-play mo": "play",
    "i-pause": "pause",
    "i-pause mo": "pause",
    "i-resume": "resume",
    "i-resume mo": "resume",
    "i-stop": "stop",
    "i-stop mo": "stop",
    "i-cancel": "cancel",
    "i-cancel mo": "cancel",
    "kanselahin": "cancel",
    "kanselahin mo": "cancel",
    "i-delete": "delete",
    "i-delete mo": "delete",
    "burahin": "delete",
    "burahin mo": "delete",
    "i-update": "update",
    "i-update mo": "update",
    "i-upgrade": "upgrade",
    "i-upgrade mo": "upgrade",
    "i-install": "install",
    "i-install mo": "install",
    "i-uninstall": "uninstall",
    "i-uninstall mo": "uninstall",
    "i-download": "download",
    "i-download mo": "download",
    "i-upload": "upload",
    "i-upload mo": "upload",
    "i-send": "send",
    "i-send mo": "send",
    "ipadala": "send",
    "ipadala mo": "send",
    "i-receive": "receive",
    "i-receive mo": "receive",
    "tanggapin": "receive",
    "tanggapin mo": "receive",
    "i-accept": "accept",
    "i-accept mo": "accept",
    "tanggapin": "accept",
    "tanggapin mo": "accept",
    "i-reject": "reject",
    "i-reject mo": "reject",
    "tanggihan": "reject",
    "tanggihan mo": "reject",
    "i-approve": "approve",
    "i-approve mo": "approve",
    "aprubahan": "approve",
    "aprubahan mo": "approve",
    "i-deny": "deny",
    "i-deny mo": "deny",
    "tanggihan": "deny",
    "tanggihan mo": "deny",
    "i-confirm": "confirm",
    "i-confirm mo": "confirm",
    "kumpirmahin": "confirm",
    "kumpirmahin mo": "confirm",
    "i-verify": "verify",
    "i-verify mo": "verify",
    "patunayan": "verify",
    "patunayan mo": "verify",
    "i-validate": "validate",
    "i-validate mo": "validate",
    "patunayan": "validate",
    "patunayan mo": "validate",
    "i-check": "check",
    "i-check mo": "check",
    "suriin": "check",
    "suriin mo": "check",
    "i-test": "test",
    "i-test mo": "test",
    "subukan": "test",
    "subukan mo": "test",
    "i-try": "try",
    "i-try mo": "try",
    "subukan": "try",
    "subukan mo": "try",
    "i-analyze": "analyze",
    "i-analyze mo": "analyze",
    "suriin": "analyze",
    "suriin mo": "analyze",
    "i-monitor": "monitor",
    "i-monitor mo": "monitor",
    "bantayan": "monitor",
    "bantayan mo": "monitor",
    "i-track": "track",
    "i-track mo": "track",
    "subaybayan": "track",
    "subaybayan mo": "track",
    "i-follow": "follow",
    "i-follow mo": "follow",
    "sundan": "follow",
    "sundan mo": "follow",
    "i-generate": "generate",
    "i-generate mo": "generate",
    "gumawa": "generate",
    "gumawa ka": "generate",
    "gumawa ka ng": "generate",
    "i-fix": "fix",
    "i-fix mo": "fix",
    "ayusin": "fix",
    "ayusin mo": "fix",
    "i-repair": "repair",
    "i-repair mo": "repair",
    "ayusin": "repair",
    "ayusin mo": "repair",
    "i-solve": "solve",
    "i-solve mo": "solve",
    "lutasin": "solve",
    "lutasin mo": "solve",
    "i-resolve": "resolve",
    "i-resolve mo": "resolve",
    "lutasin": "resolve",
    "lutasin mo": "resolve",
    "i-debug": "debug",
    "i-debug mo": "debug"
}

class TranslatorAgent:
    def __init__(self):
        # --- Stats tracking ---
        self.start_time = time.time()
        self.stats = {
            "start_time": time.time(),
            "total_requests": 0,
            "successful_translations": 0,
            "failures": 0,
            "last_update": time.time(),
            "last_status": "Initialized",
            "cache_persistence": {
                "last_save_time": 0,
                "total_saves": 0,
                "total_loads": 0,
                "cache_file": str(LOGS_DIR / "translation_cache.pkl")
            },
            "performance": {
                "response_times": [],       # List of recent response times
                "cache_hit_rates": [],      # Historical cache hit rates
                "memory_usage": [],         # Memory usage samples
                "optimization_events": []    # Record of optimization actions
            }
        }
        
        # --- Request tracking ---
        self.request_count = 0
        self.error_count = 0
        self.health_check_count = 0
        
        # --- Translation stats ---
        self.pattern_matches = 0
        self.nllb_translations = 0
        self.google_translations = 0
        self.fallback_translations = 0
        
        # --- Quality metrics ---
        self.quality_metrics = {
            "avg_response_time": 0,
            "success_rate": 1.0,
            "cache_hit_rate": 0
        }
        
        # --- Circuit breaker state ---
        self.circuit_breaker = {
            "nllb": {"failures": 0, "last_failure": 0, "state": "closed"},
            "google": {"failures": 0, "last_failure": 0, "state": "closed"}
        }
        
        # --- Cache and session management ---
        self.cache = {}
        self.cache_keys_order = []
        self.cache_access_freq = {}
        self.session_history = {}
        self.last_cache_save = time.time()
        self.last_memory_check = time.time()
        self.last_cache_cleanup = time.time()
        self.last_session_cleanup = time.time()
        
        # --- Cache sizing parameters ---
        self.cache_max_size = CACHE_MAX_SIZE
        self.cache_min_size = 100
        self.cache_current_size = 0
        self.cache_resize_threshold = 0.85
        self.cache_growth_factor = 1.25
        self.cache_shrink_factor = 0.80
        self.cache_hits = 0
        self.cache_misses = 0
        self.recent_hits = deque(maxlen=100)
        
        # --- Memory monitoring ---
        self.memory_check_counter = 0
        self.memory_high_water_mark = 500  # MB
        self.absolute_max_cache_size = 2000
        
        # --- Context awareness ---
        self.domain_contexts = {
            'technical': set(['code', 'program', 'software', 'hardware', 'file', 'system', 'network', 'database']),
            'general': set(['hello', 'goodbye', 'thank you', 'please', 'sorry', 'excuse me']),
            'command': set(['open', 'close', 'save', 'create', 'delete', 'update', 'start', 'stop']),
            'file_ops': set(['file', 'document', 'folder', 'directory', 'path']),
            'system_ops': set(['system', 'computer', 'server', 'network', 'internet']),
            'app_ops': set(['application', 'program', 'software', 'app', 'tool'])
        }
        self.current_context = 'general'
        
        # --- ZMQ setup ---
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        try:
            self.socket.bind(f"tcp://{CONFIG_ZMQ_BIND_ADDRESS}:{CONFIG_MAIN_PC_REP_PORT}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {CONFIG_MAIN_PC_REP_PORT}: {str(e)}")
            logger.warning("Attempting to use alternative port...")
            # Try alternative port
            try:
                self.socket.bind(f"tcp://{CONFIG_ZMQ_BIND_ADDRESS}:{CONFIG_MAIN_PC_REP_PORT + 1}")
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to bind to alternative port: {str(e)}")
                raise
        
        # --- Health check socket ---
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://{CONFIG_ZMQ_BIND_ADDRESS}:{CONFIG_HEALTH_REP_PORT}")
        
        # --- NLLB adapter socket ---
        self.nllb_socket = self.context.socket(zmq.REQ)
        self.nllb_socket.connect(f"tcp://{CONFIG_NLLB_ADAPTER_HOST}:{CONFIG_NLLB_ADAPTER_PORT}")
        
        # --- Load cache from disk ---
        self._load_cache_from_disk()
        
        # --- Start memory monitoring ---
        self._track_memory_usage()
        
        # --- Model Manager connection ---
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.connect(f"tcp://{MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on {MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
        
        logger.info("TranslatorAgent initialized with enhanced features")

    def run(self):
        """Main server loop with enhanced error handling and monitoring"""
        logger.info("Starting TranslatorAgent main loop")
        while True:
            try:
                # Check for messages on both sockets
                if self.socket.poll(100) == zmq.POLLIN:
                    self._handle_main_request()
                if self.health_socket.poll(100) == zmq.POLLIN:
                    self._handle_health_check()
                
                # Process queued requests in batches
                self._process_request_batch()
                
                # Regular maintenance
                self._perform_maintenance()
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)  # Prevent rapid error loops

    def _handle_main_request(self):
        """Handle main translation requests with enhanced error recovery"""
        try:
            request = json.loads(self.socket.recv_string())
            action = request.get('action', 'translate')
            
            if action == 'translate':
                text = request.get('text', '')
                source_lang = request.get('source_lang', 'tl')
                target_lang = request.get('target_lang', 'en')
                session_id = request.get('session_id')
                
                # Add to request queue
                self.request_queue.append({
                    'text': text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'session_id': session_id
                })
                
                # Process immediately if queue is small
                if len(self.request_queue) < self.batch_size:
                    result = self.translate_command(text, source_lang, target_lang, session_id)
                    self.socket.send_string(json.dumps({
                        'status': 'ok',
                        'translation': result
                    }))
                else:
                    self.socket.send_string(json.dumps({
                        'status': 'queued',
                        'queue_position': len(self.request_queue)
                    }))
            
            elif action == 'health_check':
                self.health_check_count += 1
                self.socket.send_string(json.dumps(self.get_health_status()))
            
            else:
                self.socket.send_string(json.dumps({
                    'status': 'error',
                    'error': f'Unknown action: {action}'
                }))
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error handling request: {str(e)}")
            self.socket.send_string(json.dumps({
                'status': 'error',
                'error': str(e)
            }))

    def _process_request_batch(self):
        """Process queued requests in batches for better performance"""
        if not self.request_queue:
            return
            
        batch = []
        start_time = time.time()
        
        # Collect batch
        while self.request_queue and len(batch) < self.batch_size:
            if time.time() - start_time > self.batch_timeout:
                break
            batch.append(self.request_queue.popleft())
        
        if batch:
            self.batch_count += 1
            logger.info(f"Processing batch of {len(batch)} requests")
            
            # Process batch
            for request in batch:
                try:
                    result = self.translate_command(
                        request['text'],
                        request['source_lang'],
                        request['target_lang'],
                        request['session_id']
                    )
                    # Send result back to client
                    self.socket.send_string(json.dumps({
                        'status': 'ok',
                        'translation': result
                    }))
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error processing batch request: {str(e)}")
                    self.socket.send_string(json.dumps({
                        'status': 'error',
                        'error': str(e)
                    }))

    def _perform_maintenance(self):
        """Perform regular maintenance tasks"""
        current_time = time.time()

        # Cache cleanup
        if current_time - self.last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
            self._reduce_cache_size()
            self.last_cache_cleanup = current_time
        
        # Memory check
        if current_time - self.last_memory_check > MEMORY_MONITOR_INTERVAL:
            self._track_memory_usage()
            self.last_memory_check = current_time
        
        # Cache persistence
        if current_time - self.last_cache_save > 300:  # Save every 5 minutes
            self._save_cache_to_disk()
            self.last_cache_save = current_time

    def _handle_health_check(self):
        """Handle health check requests with detailed metrics"""
        try:
            request = json.loads(self.health_socket.recv_string())
            if request.get('action') == 'health_check':
                self.health_check_count += 1
                status = self.get_health_status()
                self.health_socket.send_string(json.dumps(status))
            else:
                self.health_socket.send_string(json.dumps({
                    'status': 'error',
                    'error': 'Invalid health check request'
                }))
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error handling health check: {str(e)}")
            self.health_socket.send_string(json.dumps({
                'status': 'error',
                'error': str(e)
            }))

    def translate_command(self, text: str, source_lang="tl", target_lang="en", session_id=None) -> str:
        """Enhanced translation with improved error recovery and context awareness"""
        try:
            self.request_count += 1
            normalized_text = normalize_text(text)
            
            # Check cache first
            cache_key = normalize_text_for_cache(normalized_text)
            if cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            
                self.cache_misses += 1

            # Determine context
            self._update_context(normalized_text)
            
            # Try pattern matching first
            translation, confidence = self._try_pattern_matching(normalized_text)
            if confidence >= HIGH_CONF_THRESHOLD_PATTERN:
                self.pattern_matches += 1
                self._update_quality_metrics(confidence)
                self._add_to_cache(normalized_text, translation, source_lang, target_lang)
                return translation
            
            # Try NLLB with retry mechanism
            if not self._is_circuit_open('nllb'):
                translation, confidence = self._try_nllb_with_retry(normalized_text, source_lang, target_lang)
                if confidence >= MEDIUM_CONF_THRESHOLD_NLLB:
                    self.nllb_translations += 1
                    self._update_quality_metrics(confidence)
                    self._add_to_cache(normalized_text, translation, source_lang, target_lang)
                    return translation

            # Try Google Translate with retry mechanism
            if USE_GOOGLE_TRANSLATE_FALLBACK and not self._is_circuit_open('google'):
                translation, confidence = self._try_google_with_retry(normalized_text, source_lang, target_lang)
                if confidence >= LOW_CONF_THRESHOLD:
                    self.google_translations += 1
                    self._update_quality_metrics(confidence)
                    self._add_to_cache(normalized_text, translation, source_lang, target_lang)
                    return translation
            
            # Fallback to basic translation
            self.fallback_translations += 1
            return self._basic_fallback_translation(normalized_text)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Translation error: {str(e)}")
            return self._basic_fallback_translation(normalized_text)

    def _update_context(self, text: str):
        """Update current context based on text content"""
        words = set(text.lower().split())
        for context, keywords in self.domain_contexts.items():
            if keywords.intersection(words):
                self.current_context = context
                break

    def _try_nllb_with_retry(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        """Try NLLB translation with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                self.nllb_socket.send_string(json.dumps({
                        "text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }))
                
                if self.nllb_socket.poll(5000) == 0:
                    raise TimeoutError("NLLB translation timeout")
                
                response = json.loads(self.nllb_socket.recv_string())
                if response.get("status") == "ok":
                    self._reset_circuit('nllb')
                    return response["translation"], response.get("confidence", 0.8)
                
                raise Exception(f"NLLB error: {response.get('error', 'Unknown error')}")
                
                except Exception as e:
                self._update_circuit('nllb')
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e

    def _try_google_with_retry(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        """Try Google Translate with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                # Google Translate implementation
                pass
                except Exception as e:
                self._update_circuit('google')
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e

    def _update_circuit(self, service: str):
        """Update circuit breaker state"""
        circuit = self.circuit_breaker[service]
        circuit['failures'] += 1
        circuit['last_failure'] = time.time()
        if circuit['failures'] >= circuit['threshold']:
            logger.warning(f"Circuit breaker opened for {service}")

    def _reset_circuit(self, service: str):
        """Reset circuit breaker state"""
        self.circuit_breaker[service]['failures'] = 0
        self.circuit_breaker[service]['last_failure'] = 0

    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open"""
        circuit = self.circuit_breaker[service]
        if circuit['failures'] >= circuit['threshold']:
            # Check if enough time has passed to try again
            if time.time() - circuit['last_failure'] > 60:  # 1 minute cooldown
                self._reset_circuit(service)
                return False
            return True
        return False

    def _update_quality_metrics(self, confidence: float):
        """Update translation quality metrics"""
        if confidence >= HIGH_CONF_THRESHOLD_PATTERN:
            self.quality_metrics['high_confidence'] += 1
        elif confidence >= MEDIUM_CONF_THRESHOLD_NLLB:
            self.quality_metrics['medium_confidence'] += 1
        else:
            self.quality_metrics['low_confidence'] += 1

    def get_health_status(self) -> Dict[str, Any]:
        """Enhanced health status with more metrics"""
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "health_check_count": self.health_check_count,
            "cache_stats": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "size": len(self.cache)
            },
            "translation_stats": {
                "pattern_matches": self.pattern_matches,
                "nllb_translations": self.nllb_translations,
                "google_translations": self.google_translations,
                "fallback_translations": self.fallback_translations
            },
            "quality_metrics": self.quality_metrics,
            "circuit_breaker": {
                "nllb": self.circuit_breaker['nllb'],
                "google": self.circuit_breaker['google']
            },
            "memory_usage": self._get_memory_usage()
        }

    def _log_status(self, status, level="info"):
        self.stats["last_update"] = time.time()
        self.stats["last_status"] = status
        if level == "info":
            logger.info(status)
        elif level == "warning":
            logger.warning(status)
        elif level == "error":
            logger.error(status)
        else:
            logger.debug(status)

    # --- Advanced cache/session/memory helpers from translator_fixed.py ---
    def _add_to_cache(self, text, translation, source_lang, target_lang):
        key = (normalize_text_for_cache(text), source_lang, target_lang)
        self.cache[key] = translation
        # LRU update
        if key in self.cache_keys_order:
            self.cache_keys_order.remove(key)
        self.cache_keys_order.append(key)
        # LFU update
        self.cache_access_freq[key] = self.cache_access_freq.get(key, 0) + 1
        # Evict if over capacity
        if len(self.cache) > self.cache_max_size:
            self._evict_cache_entry()
        self._save_cache_to_disk()

    def _evict_cache_entry(self):
        # LRU+LFU hybrid eviction
        if not self.cache_keys_order:
            return
        lru_candidates = self.cache_keys_order[:5] if len(self.cache_keys_order) > 5 else self.cache_keys_order
        # Pick lowest freq among LRU
        evict_key = min(lru_candidates, key=lambda k: self.cache_access_freq.get(k, 0))
        self.cache.pop(evict_key, None)
        self.cache_keys_order.remove(evict_key)
        self.cache_access_freq.pop(evict_key, None)
        logger.info(f"Evicted cache entry: {evict_key}")

    def _save_cache_to_disk(self):
        try:
            cache_file = self.stats["cache_persistence"]["cache_file"]
            cache_data = {
                "translation_cache": self.cache,
                "cache_keys_order": self.cache_keys_order,
                "cache_access_freq": self.cache_access_freq,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "saved_at": time.time()
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            self.stats["cache_persistence"]["last_save_time"] = time.time()
            self.stats["cache_persistence"]["total_saves"] += 1
            logger.info(f"Saved translation cache to disk: {len(self.cache)} entries")
        except Exception as e:
            logger.error(f"Error saving cache to disk: {str(e)}")

    def _load_cache_from_disk(self):
        try:
            cache_file = self.stats["cache_persistence"]["cache_file"]
            if not os.path.exists(cache_file):
                logger.info(f"No cache file found at {cache_file}. Starting with empty cache.")
                return False
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            self.cache = cache_data["translation_cache"]
            self.cache_keys_order = cache_data["cache_keys_order"]
            self.cache_access_freq = cache_data.get("cache_access_freq", {})
            self.cache_hits = cache_data.get("cache_hits", 0)
            self.cache_misses = cache_data.get("cache_misses", 0)
            self.stats["cache_persistence"]["total_loads"] += 1
            cache_age_seconds = time.time() - cache_data.get("saved_at", 0)
            cache_age_hours = cache_age_seconds / 3600
            logger.info(f"Loaded translation cache from disk: {len(self.cache)} entries")
            logger.info(f"Cache age: {cache_age_hours:.1f} hours, hits: {self.cache_hits}, misses: {self.cache_misses}")
            return True
        except Exception as e:
            logger.error(f"Error loading cache from disk: {str(e)}")
            self.cache = {}
            self.cache_keys_order = []
            self.cache_access_freq = {}
            self.cache_hits = 0
            self.cache_misses = 0
            return False

    def _track_memory_usage(self):
        import threading, time
        def process_memory_usage():
            try:
                import psutil
    except ImportError as e:
        print(f"Import error: {e}")
                process = psutil.Process(os.getpid())
                mem_info = process.memory_info()
                return mem_info.rss / (1024 * 1024)
            except ImportError:
                return 0
        while True:
            time.sleep(MEMORY_MONITOR_INTERVAL)
            mem_mb = process_memory_usage()
            logger.info(f"[MemoryMonitor] Current memory usage: {mem_mb:.1f} MB")
            if mem_mb > MEMORY_USAGE_LIMIT_MB:
                logger.warning(f"[MemoryMonitor] Memory usage above limit ({mem_mb:.1f} MB > {MEMORY_USAGE_LIMIT_MB} MB). Triggering cache/session cleanup.")
                self._reduce_cache_size(aggressive=True)
                self._compress_idle_sessions()
            # Periodic cache/session maintenance
            if time.time() - self.last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
                self._reduce_cache_size()
                self.last_cache_cleanup = time.time()
            if time.time() - self.last_session_cleanup > CACHE_CLEANUP_INTERVAL:
                self._compress_idle_sessions()
                self.last_session_cleanup = time.time()

    def _reduce_cache_size(self, aggressive=False):
        # Remove cold/old entries
        to_remove = max(10, int(0.1 * self.cache_max_size)) if aggressive else max(1, int(0.03 * self.cache_max_size))
        for _ in range(to_remove):
            if len(self.cache) > self.cache_max_size:
                self._evict_cache_entry()
            else:
                break
        logger.info(f"Reduced cache size. Current cache size: {len(self.cache)}")

    def _compress_idle_sessions(self):
        # Compress or remove sessions not used recently
        now = time.time()
        idle_sessions = [sid for sid, sess in self.sessions.items() if now - sess.get('last_used', now) > SESSION_TIMEOUT_SECONDS]
        for sid in idle_sessions:
            self.sessions.pop(sid, None)
        logger.info(f"Compressed {len(idle_sessions)} idle sessions.")

    def _generate_session_id(self):
        return str(uuid.uuid4())

    def _update_session(self, session_id, original_text, translated_text):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": [], "last_used": time.time()}
        self.sessions[session_id]["history"].append({
            "original": original_text,
            "translated": translated_text,
            "timestamp": time.time()
        })
        # Prune history if too long
        if len(self.sessions[session_id]["history"]) > MAX_SESSION_HISTORY:
            self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-MAX_SESSION_HISTORY:]
        self.sessions[session_id]["last_used"] = time.time()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run self-test')
    parser.add_argument('--server', action='store_true', help='Run as server')
    args = parser.parse_args()

    agent = TranslatorAgent()

    if args.test:
        test_phrases = [
            "buksan mo ang file",
            "i-save mo ang document",
            "magsimula ng bagong project",
            "i-download mo ang file na iyon",
            "i-save mo ito",  # Test pronoun reference
            "Can you please i-open ang file na ito?"  # Taglish
        ]
        for phrase in test_phrases:
            logger.info(f"Testing translation for: '{phrase}'")
            translated = agent.translate_command(phrase)
            logger.info(f"Translation result: '{phrase}' -> '{translated}'")
        logger.info("Self-test complete.")
        logger.info(f"Translation stats: {json.dumps(agent.stats)}")
    
    elif args.server:
        # Just initialize the agent and keep it running, waiting for ZMQ messages
        logger.info("Translator Agent running in server mode, waiting for messages...")
        try:
            # Keep the process alive with resilient main loop
            while True:
                try:
                    # Run the agent's main loop
                    logger.info("MAIN_SERVER_LOOP: --- Calling agent.run() ---")
                    agent.run()
                    # If run() somehow returns (it shouldn't), log and continue
                    logger.critical("MAIN_SERVER_LOOP: --- agent.run() RETURNED - UNEXPECTED. Restarting loop. ---")
                    time.sleep(1)  # Prevent rapid restart loops
                except KeyboardInterrupt:
                    # Handle keyboard interrupt but don't exit
                    logger.info("Keyboard interrupt received, but continuing operation")
                    time.sleep(1)
                except Exception as e:
                    # Log any exceptions but don't exit
                    logger.error(f"Error in main loop: {str(e)}")
                    traceback.print_exc()
                    time.sleep(5)  # Longer delay on errors
        except KeyboardInterrupt:
            logger.info("Translator Agent interrupted by user")
    else:
        # Run the full agent
        agent.run()
