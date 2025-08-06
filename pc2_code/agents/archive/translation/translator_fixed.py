#!/usr/bin/env python3
"""
Translator Agent - Fixed Implementation
- Translates commands from Filipino to English
- Includes enhanced caching with persistence
- Uses text normalization for better cache hit rates
- Implements session context for improved translations
"""
import os
import sys
import json
import time
import zmq
import uuid
import random
import pickle
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from collections import deque
from common.utils.log_setup import configure_logging

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent)

# Configure logging
LOG_LEVEL = 'INFO'
LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOGS_DIR / str(PathManager.get_logs_dir() / "translator_fixed.log")

# Enhanced logging format with more details
logger = configure_logging(__name__),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TranslatorAgent")

# Add startup logging
logger.info("=" * 80)
logger.info("Starting TranslatorAgent Service")
logger.info(f"Log file: {log_file_path}")
logger.info(f"ZMQ Port: {ZMQ_PORT}")
logger.info(f"Bind Address: {ZMQ_BIND_ADDRESS}")
logger.info("=" * 80)

# Constants
ZMQ_PORT = 5563
ZMQ_BIND_ADDRESS = "0.0.0.0"
MAX_SESSION_HISTORY = 10
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

# Text normalization functions
def normalize_text(text: str) -> str:
    """Basic normalization function"""
    
# Memory monitoring function
def process_memory_usage() -> float:
    """Get current process memory usage in MB"""
    try:
        import psutil

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
    except ImportError as e:
        print(f"Import error: {e}")
        process = psutil.Process(os.getpid()
        mem_info = process.memory_info()
        return mem_info.rss / (1024 * 1024)  # Convert to MB
    except ImportError:
        # If psutil is not available, use a simpler method
        return 0  # Fallback value
        
def normalize_text(text):
    """Basic text normalization with safety checks"""
    # Safety check for None input
    if text is None:
        logger.warning("normalize_text received None input, returning empty string")
        return ""
        
    try:
        # Trim whitespace
        text = text.strip()
        # Remove excess spaces
        text = re.sub(r'\s+', ' ', text)
        # Handle common Taglish contractions
        text = re.sub(r'\bi[-\s]', "i-", text)
        text = text.replace("i-on", "i-turn on")
        text = text.replace("i-off", "i-turn off")
        return text
    except Exception as e:
        logger.error(f"Error in normalize_text: {str(e)}")
        return text if isinstance(text, str) else ""

def normalize_text_for_cache(text: str) -> str:
    """Enhanced normalization for cache key generation"""
    # Safety check for None inputs
    if text is None:
        logger.warning("normalize_text_for_cache received None input, returning empty string")
        return ""
        
    # Start with basic normalization
    text = normalize_text(text)
    # Convert to lowercase for case-insensitive matching
    text = text.lower()
    # Remove punctuation that doesn't affect meaning
    text = re.sub(r'[.,;!?"\(\)]', '', text)
    
    # Standardize common Filipino politeness and emphasis markers
    # These don't generally affect the core translation meaning
    politeness_markers = [
        r'\bpo\b',      # formal politeness marker
        r'\bho\b',      # alternative politeness marker
        r'\bba\b',      # question marker
        r'\bnga\b',     # emphasis marker
        r'\bnaman\b',   # comparative marker
        r'\blang\b',    # limiting marker ('just', 'only')
        r'\bsana\b',    # expressing hope ('hopefully')
        r'\bdaw\b',     # hearsay marker ('reportedly', 'they say')
        r'\bkaya\b',    # 'so', 'therefore', or question 'can/is it?'
        r'\bkasi\b',    # 'because'
        r'\bpalang\b',  # 'apparently', 'as it turns out'
        r'\bnaman\b',   # 'also', 'too', or contrast marker
    ]
    
    # Remove all politeness markers
    for marker in politeness_markers:
        text = re.sub(marker, '', text)
    
    # Standardize articles and particles that are often optional
    optional_words = [
        r'\bang\b',     # 'the'
        r'\bng\b',      # 'of'
        r'\bsa\b',      # 'to', 'in', 'at'
        r'\bna\b',      # linker 'that', 'which'
        r'\bat\b',      # 'and'
        r'\bayun\b',    # 'that' (demonstrative)
        r'\bito\b',     # 'this' (demonstrative)
        r'\biyan\b',    # 'that' (demonstrative, alternative form)
        r'\bpala\b',    # 'by the way'
    ]
    
    # Remove optional words for normalization
    for word in optional_words:
        text = re.sub(word, '', text)
    
    # Handle honorific prefixes (doesn't affect translation meaning)
    text = re.sub(r'\bgi[n]?oo\b', '', text)  # 'sir', 'mister'
    text = re.sub(r'\bbin[i]?bini\b', '', text)  # 'miss', 'mrs'
    
    # Normalize Taglish prefixes
    text = re.sub(r'i-([a-z]+)', r'\1', text)  # i-save → save, i-open → open
    
    # Remove excess spaces again after our transformations
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

class TranslatorAgent:
    """Enhanced Translator Agent with advanced caching and session management"""
    
    def __init__(self, test_mode=False):
        """Initialize the translator agent with optimized caching
        
        Args:
            test_mode (bool): If True, skip ZMQ socket binding for testing
        """
        # Store test_mode flag for later use
        self.test_mode = test_mode
        logger.info("Initializing TranslatorAgent with advanced caching and memory management")
        
        # Initialize stats
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
        
        # Translation cache with adaptive sizing
        self.translation_cache = {}
        self.cache_frequency = {}      # Track frequency of cache key access
        self.cache_keys_order = []     # Track recency (LRU ordering)
        self.cache_key_categories = {  # Categorize cache entries
            "hot": set(),             # Very frequently accessed items
            "warm": set(),            # Regularly accessed items
            "cold": set()             # Rarely accessed items
        }
        
        # Adaptive cache sizing parameters
        self.cache_initial_size = 500  # Starting size
        self.cache_min_size = 100      # Minimum cache size
        self.cache_max_size = 500
        self.max_cache_size = self.cache_max_size  # Alias for compatibility with test
        self.cache_current_size = self.cache_initial_size
        self.cache_resize_threshold = 0.85  # Resize when hit rate drops below this
        self.cache_growth_factor = 1.25    # Grow by this factor when needed
        self.cache_shrink_factor = 0.80    # Shrink by this factor when needed
        
        # Cache hit/miss tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.recent_hits = deque(maxlen=100)  # Track recent hit/miss for adaptive sizing
        
        # Session tracking with optimization
        self.sessions = {}
        self.session_memory_limit = 10 * 1024 * 1024  # 10MB limit for session data
        self.session_current_memory = 0        # Estimated memory usage
        
        # ZMQ setup - skip for test mode
        if not test_mode:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            bind_address = f"tcp://{ZMQ_BIND_ADDRESS}:{ZMQ_PORT}"
            logger.info(f"Binding to {bind_address}")
            try:
                self.socket.bind(bind_address)
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to bind to {bind_address}: {str(e)}")
                logger.warning("Socket binding failed - continuing in limited mode")
        else:
            logger.info("Running in test mode - skipping socket binding")
            self.context = None
            self.socket = None
        
        # Load cache from disk if available
        self._load_cache_from_disk()
        
        logger.info("TranslatorAgent initialized successfully")
    
    def run(self):
        """Main event loop with enhanced logging"""
        logger.info("TranslatorAgent service started and listening for requests")
        
        try:
            while True:
                try:
                    # Wait for next request from client
                    message_json = self.socket.recv_string()
                    message = json.loads(message_json)
                    
                    # Process the request
                    start_time = time.time()
                    response = self._process_request(message)
                    
                    # Send response
                    self.socket.send_string(json.dumps(response)
                    
                    # Log performance metrics
                    response_time = (time.time() - start_time) * 1000  # ms
                    logger.debug(f"Request processed in {response_time:.2f}ms")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {str(e)}")
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "error": "Invalid JSON format"
                    })
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "error": "Internal server error"
                    })
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.critical(f"Fatal error in main loop: {str(e)}", exc_info=True)
        finally:
            logger.info("Shutting down TranslatorAgent service")
            self._cleanup()
    
    def _process_request(self, message):
        """Process incoming ZMQ requests with enhanced logging"""
        try:
            logger.info(f"Received request: {json.dumps(message)}")
            
            # Extract action and validate
            action = message.get("action")
            if not action:
                logger.error("No action specified in request")
                return {"status": "error", "error": "No action specified"}
            
            logger.debug(f"Processing action: {action}")
        
        if action == "translate":
                # Extract translation parameters
            text = message.get("text", "")
            source_lang = message.get("source_lang", "tl")
            target_lang = message.get("target_lang", "en")
                session_id = message.get("session_id")
                
                logger.info(f"Translation request - Text: '{text[:30]}...', Source: {source_lang}, Target: {target_lang}")
            
            # Translate the text
            translated_text = self.translate(text, source_lang, target_lang, session_id)
            
            # Build response
            response = {
                "status": "success",
                "translated_text": translated_text,
                "original_text": text,
                "method": self.stats.get("last_translation_method", "unknown"),
                "confidence": self.stats.get("last_confidence", 0.0),
                "session_id": session_id
            }
            
                logger.info(f"Translation completed - Method: {response['method']}, Confidence: {response['confidence']}")
            return response
        
        elif action == "health_check":
                logger.info("Processing health check request")
            cache_size = len(self.translation_cache)
            hit_ratio = (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0
            
            response = {
                "status": "success",
                "uptime_seconds": time.time() - self.stats["start_time"],
                "total_requests": self.stats["total_requests"],
                "cache_size": cache_size,
                "cache_max_size": self.cache_max_size,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_ratio": hit_ratio,
                "session_count": len(self.sessions)
            }
            
                logger.info(f"Health check response - Uptime: {response['uptime_seconds']:.2f}s, Cache Hit Ratio: {hit_ratio:.2f}%")
            return response
        
        else:
                logger.error(f"Unknown action received: {action}")
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": f"Internal error: {str(e)}"
            }
    
    def translate(self, text, source_lang="tl", target_lang="en", session_id=None):
        """Translate text with advanced caching and session context"""
        # Debug output
        logger.info(f"Translate called with text: '{text}', source_lang: {source_lang}, target_lang: {target_lang}")
        
        # Skip translation for empty text
        if not text or not text.strip():
            logger.info("Empty text, returning as is")
            return text
        
        # Track start time for performance monitoring
        start_time = time.time()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = self._generate_session_id()
        
        # Initialize default values in case of errors
        normalized_text = ""
        cache_key = ""
        translation = f"Translation of: {text}"
        
        try:
            # Check cache first (using normalized text)
            normalized_text = normalize_text_for_cache(text)
            if normalized_text is None:
                normalized_text = ""
                logger.warning("normalize_text_for_cache returned None, using empty string")
                
            cache_key = f"{normalized_text}|{source_lang}|{target_lang}"
            
            # Check if we have a cache hit
            if cache_key in self.translation_cache:
                # Cache hit - update access patterns and stats
                self.cache_hits += 1
                self.recent_hits.append(1)  # Record hit for adaptive sizing
                cached_translation = self.translation_cache[cache_key]
                logger.info(f"Cache hit for '{text[:30]}...'")
                
                # Update cache access patterns (frequency and recency)
                self._update_cache_access(cache_key)
                
                # Update stats
                self.stats["last_translation_method"] = "cache"
                self.stats["last_confidence"] = 1.0
                
                # Update session history
                self._update_session(session_id, text, cached_translation)
                
                # Track session memory usage periodically
                self._track_memory_usage()
                
                # Track response time for performance monitoring
                response_time = (time.time() - start_time) * 1000  # ms
                self.stats["performance"]["response_times"].append((time.time(), response_time)
                if len(self.stats["performance"]["response_times"]) > 100:
                    self.stats["performance"]["response_times"] = self.stats["performance"]["response_times"][-100:]
                
                return cached_translation
                
            # Cache miss processing continues below
        except Exception as e:
            logger.error(f"Error in cache lookup: {str(e)}")
            # Continue with translation attempt without using cache
        
        # Cache miss - process the translation with error handling
        try:
            self.cache_misses += 1
            self.recent_hits.append(0)  # Record miss for adaptive sizing
            logger.debug(f"Cache miss for '{text[:30]}...'")
            
            # Get session context if available
            try:
                context = self._get_session_context(session_id)
            except Exception as e:
                logger.error(f"Error getting session context: {str(e)}")
                context = None
            
            # For demo purposes, we'll use a simple direct translation
            # In a real implementation, this would call the NLLB adapter or other services
            logger.info(f"Calling _simple_translate with text: '{text}'")
            try:
                translation = self._simple_translate(text, context)
                logger.info(f"Result from _simple_translate: '{translation}'")
            except Exception as e:
                logger.error(f"Error in _simple_translate: {str(e)}")
                # Use direct fallback translation for robustness
                translation = f"Translation of: {text}"
            
            # Ensure we never return None - use fallback
            if translation is None:
                logger.warning(f"_simple_translate returned None for '{text}', using fallback")
                translation = f"Translation of: {text}"
            
            # Add to cache with advanced eviction strategy - with error handling
            try:
                self._add_to_cache(text, translation, source_lang, target_lang)
            except Exception as e:
                logger.error(f"Error adding to cache: {str(e)}")
                # Continue even if caching fails
        except Exception as e:
            logger.error(f"Critical error in translation process: {str(e)}")
            # Last resort fallback
            translation = f"Translation error - please try again: {text}"
        
        # Update session history with memory-efficient storage - with error handling
        try:
            self._update_session(session_id, text, translation)
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            # Continue even if session update fails
        
        # Track session memory periodically - with error handling
        try:
            self._track_memory_usage()
        except Exception as e:
            logger.error(f"Error tracking memory: {str(e)}")
        
        # Update stats - with error handling
        try:
            self.stats["last_translation_method"] = "direct"
            self.stats["last_confidence"] = 0.8  # Simulated confidence score
            
            # Track response time for performance monitoring
            response_time = (time.time() - start_time) * 1000  # ms
            self.stats["performance"]["response_times"].append((time.time(), response_time)
            if len(self.stats["performance"]["response_times"]) > 100:
                self.stats["performance"]["response_times"] = self.stats["performance"]["response_times"][-100:]
        except Exception as e:
            logger.error(f"Error updating stats: {str(e)}")
        
        # Final safety check before returning
        if translation is None:
            logger.error("Critical error: Translation is None at final return point")
            translation = f"Emergency fallback translation: {text}"
            
        return translation
    
    def _update_cache_access(self, cache_key):
        """Update cache access patterns for a given key
        Tracks both recency (LRU) and frequency (LFU) for advanced eviction
        """
        # Update frequency counter
        if cache_key not in self.cache_frequency:
            self.cache_frequency[cache_key] = 0
        self.cache_frequency[cache_key] += 1
        
        # Update recency order (LRU)
        if cache_key in self.cache_keys_order:
            self.cache_keys_order.remove(cache_key)
        self.cache_keys_order.append(cache_key)
        
        # Update cache category based on access patterns
        current_freq = self.key_frequency[cache_key]
        if current_freq >= self.hot_threshold:
            # Move to hot category
            if cache_key in self.warm_keys:
                self.warm_keys.remove(cache_key)
            if cache_key not in self.hot_keys:
                self.hot_keys.add(cache_key)
        elif current_freq >= self.warm_threshold:
            # Move to warm category
            if cache_key not in self.hot_keys and cache_key not in self.warm_keys:
                self.warm_keys.add(cache_key)
    
    def _track_memory_usage(self):
        """Track memory usage of the translator and perform maintenance if needed"""
        # Only check periodically to avoid overhead
        self.memory_check_counter += 1
        if self.memory_check_counter % 50 != 0:
            return
            
        # Get current memory usage
        current_usage = process_memory_usage()
        self.stats["performance"]["memory_usage"].append((time.time(), current_usage)
        
        # Keep only recent memory measurements
        if len(self.stats["performance"]["memory_usage"]) > 100:
            self.stats["performance"]["memory_usage"] = self.stats["performance"]["memory_usage"][-100:]
        
        # Adjust cache size dynamically based on memory pressure
        if current_usage > self.memory_high_water_mark:
            # Memory pressure - reduce cache size
            logger.warning(f"Memory pressure detected ({current_usage:.1f} MB) - reducing cache size")
            self._reduce_cache_size(aggressive=True)
            
            # Also compress idle sessions
            self._compress_idle_sessions()
            
        # Adjust cache size based on hit rate
        if len(self.recent_hits) >= 100:
            hit_rate = sum(self.recent_hits) / len(self.recent_hits)
            self.recent_hits = self.recent_hits[-50:]  # Keep last 50 hits/misses
            
            if hit_rate < 0.3 and len(self.translation_cache) < self.max_cache_size * 1.5:
                # Low hit rate, expand cache if possible
                new_max = min(int(self.max_cache_size * 1.1), self.absolute_max_cache_size)
                if new_max > self.max_cache_size:
                    logger.info(f"Low hit rate ({hit_rate:.2f}), increasing cache size: {self.max_cache_size} → {new_max}")
                    self.max_cache_size = new_max
            elif hit_rate > 0.8 and len(self.translation_cache) > self.min_cache_size:
                # High hit rate, we can reduce cache size to save memory
                new_max = max(int(self.max_cache_size * 0.95), self.min_cache_size)
                if new_max < self.max_cache_size:
                    logger.info(f"High hit rate ({hit_rate:.2f}), optimizing cache size: {self.max_cache_size} → {new_max}")
                    self.max_cache_size = new_max
                    self._reduce_cache_size()
    
    def _reduce_cache_size(self, aggressive=False):
        """Reduce cache size using intelligent eviction strategy
        If aggressive=True, removes more entries to quickly free memory
        """
        # Calculate how many entries to remove
        target_size = self.max_cache_size
        if aggressive:
            target_size = int(self.max_cache_size * 0.8)  # More aggressive reduction
        
        # Only proceed if we need to remove entries
        current_size = len(self.translation_cache)
        if current_size <= target_size:
            return
            
        entries_to_remove = current_size - target_size
        logger.info(f"Reducing cache size, removing {entries_to_remove} entries")
        
        # First, try to remove cold entries (neither hot nor warm)
        cold_keys = [k for k in self.cache_keys_order 
                    if k not in self.hot_keys and k not in self.warm_keys]
                    
        # Start by removing oldest cold entries
        removed = 0
        for key in cold_keys[:entries_to_remove]:
            if key in self.translation_cache:
                del self.translation_cache[key]
                if key in self.cache_keys_order:
                    self.cache_keys_order.remove(key)
                if key in self.key_frequency:
                    del self.key_frequency[key]
                removed += 1
        
        # If we still need to remove more, target warm entries next
        if removed < entries_to_remove and len(self.warm_keys) > 0:
            # Sort warm keys by frequency (ascending)
            warm_keys_by_freq = sorted(
                list(self.warm_keys),
                key=lambda k: self.key_frequency.get(k, 0)
            )
            
            # Remove least frequently used warm entries
            for key in warm_keys_by_freq[:entries_to_remove-removed]:
                if key in self.translation_cache:
                    del self.translation_cache[key]
                    if key in self.cache_keys_order:
                        self.cache_keys_order.remove(key)
                    if key in self.key_frequency:
                        del self.key_frequency[key]
                    self.warm_keys.remove(key)
                    removed += 1
        
        # As a last resort, remove hot entries if we still need space
        if removed < entries_to_remove and aggressive and len(self.hot_keys) > 0:
            # Sort hot keys by recency (oldest first)
            hot_keys_by_recency = [k for k in self.cache_keys_order if k in self.hot_keys]
            
            # Remove oldest hot entries if absolutely necessary
            for key in hot_keys_by_recency[:entries_to_remove-removed]:
                if key in self.translation_cache:
                    del self.translation_cache[key]
                    if key in self.cache_keys_order:
                        self.cache_keys_order.remove(key)
                    if key in self.key_frequency:
                        del self.key_frequency[key]
                    self.hot_keys.remove(key)
                    removed += 1
        
        logger.debug(f"Cache reduction complete, removed {removed} entries")
    
    def _compress_idle_sessions(self):
        """Compress inactive sessions to save memory"""
        current_time = time.time()
        compressed = 0
        
        for session_id, session_data in list(self.sessions.items():
            # Skip already compressed sessions
            if session_data.get('compressed', False):
                continue
                
            last_access = session_data.get('last_access', 0)
            if current_time - last_access > self.session_compression_threshold:
                # This session is idle, compress it
                if 'history' in session_data and len(session_data['history']) > 2:
                    # Create a summary instead of keeping full history
                    summary = self._create_session_summary(session_data['history'])
                    session_data['compressed'] = True
                    session_data['history_summary'] = summary
                    session_data['history_length'] = len(session_data['history'])
                    # Keep only the most recent 2 items
                    session_data['history'] = session_data['history'][-2:]
                    compressed += 1
        
        if compressed > 0:
            logger.info(f"Compressed {compressed} idle sessions to save memory")
    
    def _create_session_summary(self, history):
        """Create a memory-efficient summary of session history"""
        # Extract key information from history
        summary = {
            'frequent_terms': {},
            'total_characters': 0,
            'avg_length': 0,
            'languages': set()
        }
        
        if not history:
            return summary
            
        # Count term frequency and gather stats
        all_words = []
        for entry in history:
            text = entry.get('original', '')
            summary['total_characters'] += len(text)
            
            # Track languages used
            lang = entry.get('source_lang')
            if lang:
                summary['languages'].add(lang)
                
            # Extract words for frequency analysis
            words = text.lower().split()
            all_words.extend(words)
        
        # Calculate average length
        if len(history) > 0:
            summary['avg_length'] = summary['total_characters'] / len(history)
        
        # Find most frequent terms (only keep top 10)
        word_counts = {}
        for word in all_words:
            if len(word) > 3:  # Skip very short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency and keep top terms
        sorted_terms = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        for term, count in sorted_terms[:10]:
            summary['frequent_terms'][term] = count
        
        # Convert languages set to list for serialization
        summary['languages'] = list(summary['languages'])
        
        return summary
        
    def _simple_translate(self, text, context=None):
        """Simple translation for demo purposes
        In real implementation, this would call machine translation APIs
        """
        # Add detailed debugging and safety checks
        logger.debug(f"_simple_translate called with text: '{text}', context type: {type(context)}")
        
        # Safety check for None or empty text
        if text is None:
            logger.warning("_simple_translate received None input, returning default message")
            return "Translation unavailable"
            
        if not text or text.strip() == "":
            logger.warning("_simple_translate received empty text, returning empty string")
            return ""
        
        # Simulate translation with context awareness
        if context:
            logger.debug(f"Using context for translation: {context}")
            
            # Check for pronoun resolution in follow-up questions
            # Add safety check before calling lower()
            if text and ('ito' in text.lower() or 'iyon' in text.lower():
                # Look for previous objects in context
                last_action = None
                for action, details in context.get('actions', {}).items():
                    if details.get('recency', 999) < last_action or last_action is None:
                        last_action = action
                        last_object = details.get('object')
                
                # If we found a recent object, use it for context
                if last_action and 'ito' in text.lower():
                    # Replace generic pronouns with context-specific objects
                    if 'file' in context.get('commands', [])[-1].lower():
                        text = text.replace('ito', 'this file')
        
        # Special cases dictionary with common translations
        special_cases = {
            "buksan mo ang file": "open the file",
            "i-save mo ang document": "save the document",
            "magsimula ng bagong project": "start a new project",
            "isara mo ang window": "close the window",
            "i-maximize mo ang browser": "maximize the browser",
            "i-delete mo ang file": "delete the file",
            "i-download mo ang file": "download the file",
            "i-download mo ang file na iyon": "download that file",
            "i-print mo": "print",
            "i-cancel mo": "cancel",
            "maghanap": "search",
            "kumusta": "hello",
            "salamat": "thank you",
            "paalam": "goodbye",
            "i-save mo ito": "save this",
            "isara mo ito": "close this",
            "buksan mo ito": "open this",
            "command 0": "command zero",
            "command 1": "command one",
            "command 2": "command two",
            "command 3": "command three",
            "command 4": "command four",
            "command 5": "command five",
            "command 6": "command six",
            "command 7": "command seven",
            "command 8": "command eight",
            "command 9": "command nine"
        }
        
        # Check if text is in special cases - with safety checks
        try:
            normalized_input = normalize_text_for_cache(text.lower()
            for key, value in special_cases.items():
                if normalized_input in normalize_text_for_cache(key) or normalize_text_for_cache(key) in normalized_input:
                    logger.debug(f"Found special case match: '{text}' -> '{value}'")
                    return value
        except Exception as e:
            logger.error(f"Error in special case matching: {str(e)}")
            # Continue to fallback translation
        
        # Fallback word-by-word translation for unknown phrases
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
        
        # Try word-by-word translation with safety checks
        try:
            words = text.lower().split()
            translated_words = []
            for word in words:
                # Check if word is in dictionary
                if word in tagalog_to_english:
                    translated_words.append(tagalog_to_english[word])
                else:
                    # Keep original word if not found
                    translated_words.append(word)
            
            result = " ".join(translated_words)
            logger.debug(f"Word-by-word translation: '{text}' -> '{result}'")
            return result
        except Exception as e:
            logger.error(f"Error in word-by-word translation: {str(e)}")
            return f"Translation error: {text}"
        
        # Join words and return
        return " ".join(translated_words)
                
        # NOTE: The code below is unreachable after the return above. It's left here for
        # reference purposes, but we're now using the word-by-word approach as fallback
        # instead of the contextual translation logic below
        
        # Apply contextual translation if context is available (UNREACHABLE CODE)
        if context:
            logger.debug("Applying contextual translation")
            # Get the most recent focus and objects from context
            current_focus = context.get("current_focus", "")
            current_objects = context.get("current_objects", [])
            conversation_history = context.get("conversation_history", [])
            
            # Check if this is a follow-up to a previous command
            if current_focus and any(word in normalized_input for word in ["ito", "iyan", "iyon", "nito"]):
                return f"Regarding {current_focus}: {text}"
                
            # If we have objects mentioned in context, incorporate them
            if current_objects and len(current_objects) > 0:
                return f"Translated (with context about {current_objects[0]}): {text}"
                
        # Default simple translation
        return f"Translated: {text}"
    
    def _add_to_cache(self, text, translation, source_lang, target_lang):
        """Add a translation to the cache with advanced eviction strategy"""
        normalized_text = normalize_text_for_cache(text)
        cache_key = f"{normalized_text}|{source_lang}|{target_lang}"
        
        # If already in cache, just update access patterns
        if cache_key in self.translation_cache:
            self._update_cache_access(cache_key)
            return
        
        # Check if we need to make room in the cache
        if len(self.translation_cache) >= self.cache_current_size:
            # Perform intelligent eviction based on frequency and recency
            self._evict_cache_entry()
        
        # Add to cache
        self.translation_cache[cache_key] = translation
        
        # Initialize frequency counter
        self.cache_frequency[cache_key] = 1
        
        # Add to recency tracking
        if cache_key in self.cache_keys_order:
            self.cache_keys_order.remove(cache_key)
        self.cache_keys_order.append(cache_key)
        
        # Categorize as "cold" initially
        self.cache_key_categories["cold"].add(cache_key)
        
        logger.debug(f"Added to cache: '{text[:30]}...' -> '{translation[:30]}...'")
        
        # Check if we should adapt cache size based on recent hit rate
        self._check_cache_adaptation()
    
    def _update_cache_access(self, cache_key):
        """Update cache access patterns for a key"""
        # Update frequency counter
        if cache_key in self.cache_frequency:
            self.cache_frequency[cache_key] += 1
        else:
            self.cache_frequency[cache_key] = 1
        
        # Update recency (LRU ordering)
        if cache_key in self.cache_keys_order:
            self.cache_keys_order.remove(cache_key)
        self.cache_keys_order.append(cache_key)
        
        # Update category based on access frequency
        freq = self.cache_frequency[cache_key]
        
        # Remove from current category
        for category in self.cache_key_categories.values():
            if cache_key in category:
                category.remove(cache_key)
        
        # Add to appropriate category
        if freq >= 10:  # Accessed 10+ times: hot
            self.cache_key_categories["hot"].add(cache_key)
        elif freq >= 3:  # Accessed 3-9 times: warm
            self.cache_key_categories["warm"].add(cache_key)
        else:  # Accessed 1-2 times: cold
            self.cache_key_categories["cold"].add(cache_key)
    
    def _evict_cache_entry(self):
        """Intelligently evict an entry from the cache"""
        # First try to evict from cold items
        if self.cache_key_categories["cold"]:
            # Find the least recently used cold item
            for key in self.cache_keys_order:
                if key in self.cache_key_categories["cold"]:
                    self._remove_cache_entry(key)
                    return
        
        # If no cold items, try warm items
        if self.cache_key_categories["warm"]:
            # Find the least recently used warm item
            for key in self.cache_keys_order:
                if key in self.cache_key_categories["warm"]:
                    self._remove_cache_entry(key)
                    return
        
        # As a last resort, evict from hot items
        if self.cache_key_categories["hot"]:
            # Find the least recently used hot item
            for key in self.cache_keys_order:
                if key in self.cache_key_categories["hot"]:
                    self._remove_cache_entry(key)
                    return
        
        # If all else fails, evict the oldest item
        if self.cache_keys_order:
            oldest_key = self.cache_keys_order[0]
            self._remove_cache_entry(oldest_key)
    
    def _remove_cache_entry(self, key):
        """Remove a specific entry from the cache and all tracking structures"""
        # Remove from main cache
        if key in self.translation_cache:
            del self.translation_cache[key]
        
        # Remove from frequency tracking
        if key in self.cache_frequency:
            del self.cache_frequency[key]
        
        # Remove from recency list
        if key in self.cache_keys_order:
            self.cache_keys_order.remove(key)
        
        # Remove from categories
        for category in self.cache_key_categories.values():
            if key in category:
                category.remove(key)
        
        logger.debug(f"Evicted cache entry: '{key[:30]}...'")
    
    def _check_cache_adaptation(self):
        """Check if cache size should be adapted based on hit rate"""
        # Only adapt after we have enough data
        if len(self.recent_hits) < self.recent_hits.maxlen:
            return
        
        # Calculate recent hit rate
        recent_hit_rate = sum(self.recent_hits) / len(self.recent_hits)
        
        # Track this for analytics
        self.stats["performance"]["cache_hit_rates"].append((time.time(), recent_hit_rate)
        if len(self.stats["performance"]["cache_hit_rates"]) > 100:
            self.stats["performance"]["cache_hit_rates"] = self.stats["performance"]["cache_hit_rates"][-100:]
        
        # Determine if adaptation is needed
        if recent_hit_rate < self.cache_resize_threshold and self.cache_current_size < self.cache_max_size:
            # Hit rate is low, grow the cache
            old_size = self.cache_current_size
            self.cache_current_size = min(
                int(self.cache_current_size * self.cache_growth_factor),
                self.cache_max_size
            )
            
            # Log the event
            logger.info(f"Growing cache from {old_size} to {self.cache_current_size} entries (hit rate: {recent_hit_rate:.2f})")
            self.stats["performance"]["optimization_events"].append({
                "time": time.time(),
                "action": "grow_cache",
                "old_size": old_size,
                "new_size": self.cache_current_size,
                "hit_rate": recent_hit_rate
            })
        
        elif recent_hit_rate > 0.95 and len(self.translation_cache) < (self.cache_current_size * 0.7) and self.cache_current_size > self.cache_min_size:
            # Hit rate is very high and we're using much less than capacity, shrink the cache
            old_size = self.cache_current_size
            self.cache_current_size = max(
                int(self.cache_current_size * self.cache_shrink_factor),
                self.cache_min_size
            )
            
            # Log the event
            logger.info(f"Shrinking cache from {old_size} to {self.cache_current_size} entries (hit rate: {recent_hit_rate:.2f})")
            self.stats["performance"]["optimization_events"].append({
                "time": time.time(),
                "action": "shrink_cache",
                "old_size": old_size,
                "new_size": self.cache_current_size,
                "hit_rate": recent_hit_rate
            })
        
        # If we're approaching capacity, preemptively clean up cold entries
        if len(self.translation_cache) > (self.cache_current_size * 0.9):
            self._cleanup_cold_entries()
    
    def _cleanup_cold_entries(self):
        """Cleanup cold entries to prevent cache from hitting capacity limits"""
        # Check if we have cold entries to clean up
        if not self.cache_key_categories["cold"]:
            return
        
        # Determine how many entries to remove
        current_size = len(self.translation_cache)
        target_size = int(self.cache_current_size * 0.8)  # Aim for 80% capacity
        entries_to_remove = max(current_size - target_size, 1)  # Remove at least 1
        
        # Get cold entries sorted by recency (oldest first)
        cold_entries = []
        for key in self.cache_keys_order:
            if key in self.cache_key_categories["cold"]:
                cold_entries.append(key)
        
        # Remove the oldest cold entries
        removed = 0
        for key in cold_entries:
            if removed >= entries_to_remove:
                break
            
            self._remove_cache_entry(key)
            removed += 1
        
        logger.debug(f"Cleaned up {removed} cold cache entries")
        
        # Record this optimization event
        self.stats["performance"]["optimization_events"].append({
            "time": time.time(),
            "action": "cleanup_cold_entries",
            "removed": removed,
            "new_size": len(self.translation_cache)
        })
    
    def _generate_session_id(self):
        """Generate a unique session ID"""
        return f"session_{int(time.time()}_{random.randint(1000, 9999)}"
    
    def _update_session(self, session_id, original_text, translated_text):
        """Update session history with translation using memory-efficient storage"""
        # Create new session if needed
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created": time.time(),
                "last_updated": time.time(),
                "translations": [],
                "summary": {},  # Stores summarized session data
                "memory_usage": 0,  # Tracks estimated memory usage
                "compressed": False  # Indicates if session is in compressed form
            }
        
        # Prepare the translation entry with minimal data structure
        entry = {
            "timestamp": time.time(),
            "original": original_text,
            "translated": translated_text
        }
        
        # Estimate memory usage of this entry
        entry_size = self._estimate_object_size(entry)
        
        # Add translation to session history
        self.sessions[session_id]["translations"].append(entry)
        self.sessions[session_id]["last_updated"] = time.time()
        self.sessions[session_id]["memory_usage"] += entry_size
        
        # Perform session management based on memory usage and history length
        self._manage_session_memory(session_id)
        
    def _manage_session_memory(self, session_id):
        """Manage session memory efficiently for large-scale deployments"""
        session = self.sessions[session_id]
        
        # Check if session exceeds history limit
        if len(session["translations"]) > MAX_SESSION_HISTORY:
            # Calculate how many items to remove
            excess = len(session["translations"]) - MAX_SESSION_HISTORY
            
            # Before removing, update the session summary with key information
            self._update_session_summary(session_id, session["translations"][:excess])
            
            # Remove oldest entries
            for _ in range(excess):
                removed_entry = session["translations"].pop(0)
                # Adjust memory usage estimation
                session["memory_usage"] -= self._estimate_object_size(removed_entry)
        
        # Check if overall memory usage exceeds limit
        if self.session_current_memory > self.session_memory_limit:
            self._compress_inactive_sessions()
            
        # Check if this specific session is getting too large
        session_limit = 1024 * 1024  # 1MB per session limit
        if session["memory_usage"] > session_limit and not session["compressed"]:
            self._compress_session(session_id)
    
    def _update_session_summary(self, session_id, entries):
        """Summarize removed session entries to preserve context"""
        session = self.sessions[session_id]
        
        # If summary doesn't exist yet, initialize it
        if not session.get("summary"):
            session["summary"] = {
                "frequent_terms": {},  # Terms that appear frequently
                "object_references": {},  # Objects that were mentioned
                "command_patterns": [],  # Common command patterns
                "topics": set(),  # Discussion topics
                "entry_count": 0  # Total entries summarized
            }
        
        # Process each entry to be summarized
        for entry in entries:
            original = entry.get("original", "").lower()
            translated = entry.get("translated", "").lower()
            
            # Extract and count terms
            terms = original.split() + translated.split()
            for term in terms:
                if len(term) > 3:  # Only consider meaningful terms
                    if term in session["summary"]["frequent_terms"]:
                        session["summary"]["frequent_terms"][term] += 1
                    else:
                        session["summary"]["frequent_terms"][term] = 1
            
            # Extract object references
            object_types = ["file", "document", "folder", "browser", "window"]
            for obj_type in object_types:
                if obj_type in translated:
                    session["summary"]["object_references"][obj_type] = True
            
            # Track command patterns
            command_verbs = ["open", "close", "save", "delete", "edit", "modify", "create", 
                "upload", "download", "search", "find", "play", "pause", "stop",
                "maximize", "minimize", "resize", "move", "copy", "paste", "cut",
                "refresh", "update", "install", "uninstall", "start", "end", "exit"
            ]
            
            for verb in command_verbs:
                if verb in translated.split():
                    pattern = f"{verb} command"
                    if pattern not in session["summary"]["command_patterns"]:
                        session["summary"]["command_patterns"].append(pattern)
            
            # Update entry count
            session["summary"]["entry_count"] += 1
        
        # Prune the summary to keep it compact
        self._prune_summary(session["summary"])
    
    def _prune_summary(self, summary):
        """Prune session summary to keep it manageable"""
        # Keep only the top 20 most frequent terms
        if len(summary["frequent_terms"]) > 20:
            sorted_terms = sorted(
                summary["frequent_terms"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            summary["frequent_terms"] = dict(sorted_terms[:20])
        
        # Limit command patterns
        if len(summary["command_patterns"]) > 10:
            summary["command_patterns"] = summary["command_patterns"][-10:]
    
    def _compress_inactive_sessions(self):
        """Compress or remove inactive sessions to free up memory"""
        current_time = time.time()
        
        # First, identify inactive sessions
        inactive_sessions = []
        very_inactive_sessions = []
        
        for session_id, session in self.sessions.items():
            inactive_time = current_time - session["last_updated"]
            
            if inactive_time > SESSION_TIMEOUT_SECONDS:  # Over 1 hour inactive
                very_inactive_sessions.append(session_id)
            elif inactive_time > 300 and not session.get("compressed"):  # 5 minutes inactive
                inactive_sessions.append(session_id)
        
        # Remove very inactive sessions
        for session_id in very_inactive_sessions:
            memory_freed = self.sessions[session_id]["memory_usage"]
            self.session_current_memory -= memory_freed
            del self.sessions[session_id]
            logger.debug(f"Removed very inactive session: {session_id}, freed {memory_freed} bytes")
        
        # Compress inactive sessions
        for session_id in inactive_sessions:
            self._compress_session(session_id)
        
        # If still over limit, remove more aggressively
        if self.session_current_memory > self.session_memory_limit:
            self._emergency_session_cleanup()
    
    def _compress_session(self, session_id):
        """Compress a session to reduce memory usage"""
        if session_id not in self.sessions:
            return
            
        session = self.sessions[session_id]
        
        # Skip if already compressed
        if session.get("compressed"):
            return
        
        # First, ensure we have a summary
        if not session.get("summary") and session["translations"]:
            self._update_session_summary(session_id, session["translations"])
        
        # Keep only the most recent translations
        keep_count = min(5, len(session["translations"])
        if keep_count < len(session["translations"]):
            # Calculate memory to be freed
            to_remove = session["translations"][:-keep_count]
            memory_to_free = sum(self._estimate_object_size(entry) for entry in to_remove)
            
            # Keep only recent entries
            session["translations"] = session["translations"][-keep_count:]
            
            # Update memory usage
            session["memory_usage"] -= memory_to_free
            self.session_current_memory -= memory_to_free
            
            # Mark as compressed
            session["compressed"] = True
            
            logger.debug(f"Compressed session {session_id}, freed {memory_to_free} bytes")
    
    def _emergency_session_cleanup(self):
        """Emergency cleanup when memory pressure is high"""
        # Sort sessions by last updated time (oldest first)
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1]["last_updated"]
        )
        
        # Remove sessions until we're under the memory limit or have only 3 left
        removed = 0
        for session_id, session in sorted_sessions:
            if removed > 5 or len(self.sessions) <= 3 or self.session_current_memory <= self.session_memory_limit * 0.8:
                break
                
            memory_freed = session["memory_usage"]
            self.session_current_memory -= memory_freed
            del self.sessions[session_id]
            removed += 1
            
            logger.warning(f"Emergency removal of session {session_id}, freed {memory_freed} bytes")
        
        logger.info(f"Emergency cleanup removed {removed} sessions, current memory: {self.session_current_memory} bytes")
    
    def _estimate_object_size(self, obj):
        """Estimate memory usage of an object in bytes"""
        # Simple estimation based on string lengths
        if isinstance(obj, dict):
            return sum(self._estimate_object_size(k) + self._estimate_object_size(v) for k, v in obj.items()
        elif isinstance(obj, list):
            return sum(self._estimate_object_size(item) for item in obj)
        elif isinstance(obj, str):
            return len(obj) * 2  # Unicode strings use ~2 bytes per char
        elif isinstance(obj, (int, float, bool):
            return 8  # Approximation for numeric types
        else:
            return 32  # Default estimate for other types
        
    def _track_memory_usage(self):
        """Track total memory usage of all sessions"""
        total_memory = 0
        for session in self.sessions.values():
            total_memory += session.get("memory_usage", 0)
        
        self.session_current_memory = total_memory
        
        # Log memory usage periodically
        if random.random() < 0.01:  # 1% chance each time this is called
            logger.debug(f"Current session memory usage: {total_memory} bytes, {len(self.sessions)} active sessions")
            
            # Store in performance stats
            self.stats["performance"]["memory_usage"].append((time.time(), total_memory)
            if len(self.stats["performance"]["memory_usage"]) > 100:
                self.stats["performance"]["memory_usage"] = self.stats["performance"]["memory_usage"][-100:]
    
    def _get_session_context(self, session_id, max_history=3):
        """Extract contextual information from session history for improved translation"""
        context = {
            "conversation_history": [],
            "references": {},
            "actions": {},
            "topics": set(),
            "commands": [],
            "is_follow_up": False,
            "user_preferences": {},
            "current_focus": None,
            "current_objects": [],
            "last_pronouns": []
        }
        
        # If no session history exists, return empty context
        if session_id not in self.sessions or not self.sessions[session_id]["translations"]:
            return context
        
        # Get recent translations (newest first)
        recent_translations = list(reversed(self.sessions[session_id]["translations"][-max_history:])
        
        # Extract conversation history and build rich context
        for i, item in enumerate(recent_translations):
            # Add to conversation history (original -> translated pairs)
            context["conversation_history"].append({
                "original": item["original"],
                "translated": item["translated"],
                "timestamp": item["timestamp"]
            })
            
            # Process the translated text to extract semantic information
            translated = item["translated"].lower()
            original = item["original"].lower()
            
            # Find common objects that might be referenced later
            object_types = [
                "file", "document", "folder", "window", "browser", "app", 
                "image", "photo", "video", "music", "song", "email", "message",
                "contact", "person", "website", "link", "project", "program"
            ]
            
            # Process original text for Filipino pronouns
            filipino_pronouns = ["ito", "iyan", "iyon", "nito", "niyan", "niyon", "dito", "diyan", "doon"]
            
            # Check for pronouns in original text
            for pronoun in filipino_pronouns:
                if pronoun in original.split():
                    context["last_pronouns"].append(pronoun)
            
            # Extract noun phrases and identify potential objects
            words = translated.split()
            for j, word in enumerate(words):
                # Check if this word is an object type
                if word in object_types:
                    # Try to get the full phrase (e.g., "text file", "browser window")
                    if j > 0 and len(words[j-1]) > 2:  # Potential modifier
                        full_object = f"{words[j-1]} {word}"
                    else:
                        full_object = word
                    
                    # Save reference with recency info
                    context["references"][word] = {
                        "timestamp": item["timestamp"],
                        "full_phrase": full_object,
                        "recency": i  # 0 is most recent
                    }
                    
                    # Track current objects of focus
                    if i == 0:  # Most recent translation
                        context["current_objects"].append(full_object)
                        context["current_focus"] = full_object
            
            # Extract verbs/actions
            action_verbs = [
                "open", "close", "save", "delete", "edit", "modify", "create", 
                "upload", "download", "search", "find", "play", "pause", "stop",
                "maximize", "minimize", "resize", "move", "copy", "paste", "cut",
                "refresh", "update", "install", "uninstall", "start", "end", "exit"
            ]
            
            for verb in action_verbs:
                if verb in translated.split():
                    # Find object of the action if available
                    verb_idx = translated.split().index(verb)
                    object_of_action = None
                    
                    # Look for an object after the verb
                    remaining_words = translated.split()[verb_idx+1:]
                    for obj_type in object_types:
                        if obj_type in remaining_words:
                            object_of_action = obj_type
                            break
                    
                    # Save the action with its object
                    context["actions"][verb] = {
                        "timestamp": item["timestamp"],
                        "object": object_of_action,
                        "recency": i
                    }
                    
                    # Also save as a command for easier access
                    if i == 0 or (verb not in [cmd.split()[0] for cmd in context["commands"]]):
                        context["commands"].append(translated)
            
            # Extract potential topics (meaningful content words)
            content_words = [w for w in words if len(w) > 3 and w not in action_verbs and w not in object_types]
            context["topics"].update(content_words)
        
        # Determine if this is likely a follow-up question
        # Time-based detection (within 30 seconds)
        if recent_translations and time.time() - recent_translations[0]["timestamp"] < 30:
            context["is_follow_up"] = True
        
        # Content-based detection (pronoun without clear referent)
        original_first = recent_translations[0]["original"].lower() if recent_translations else ""
        if any(pronoun in original_first.split() for pronoun in filipino_pronouns):
            context["is_follow_up"] = True
            
        return context
    
    def _cleanup_old_sessions(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session["last_updated"] > SESSION_TIMEOUT_SECONDS:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def _save_cache_to_disk(self):
        """Save translation cache to disk for persistence between restarts"""
        try:
            cache_file = self.stats["cache_persistence"]["cache_file"]
            
            # Prepare data to save
            cache_data = {
                "translation_cache": self.translation_cache,
                "cache_keys_order": self.cache_keys_order,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "saved_at": time.time()
            }
            
            # Save to disk
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Update stats
            self.stats["cache_persistence"]["last_save_time"] = time.time()
            self.stats["cache_persistence"]["total_saves"] += 1
            
            logger.info(f"Saved translation cache to disk: {len(self.translation_cache)} entries")
            return True
        except Exception as e:
            logger.error(f"Error saving cache to disk: {str(e)}")
            return False
    
    def _load_cache_from_disk(self):
        """Load translation cache from disk"""
        try:
            cache_file = self.stats["cache_persistence"]["cache_file"]
            
            if not os.path.exists(cache_file):
                logger.info(f"No cache file found at {cache_file}. Starting with empty cache.")
                return False
            
            # Load from disk
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Restore cache
            self.translation_cache = cache_data["translation_cache"]
            self.cache_keys_order = cache_data["cache_keys_order"]
            self.cache_hits = cache_data.get("cache_hits", 0)
            self.cache_misses = cache_data.get("cache_misses", 0)
            
            # Update stats
            self.stats["cache_persistence"]["total_loads"] += 1
            
            # Log cache loaded
            cache_age_seconds = time.time() - cache_data.get("saved_at", 0)
            cache_age_hours = cache_age_seconds / 3600
            logger.info(f"Loaded translation cache from disk: {len(self.translation_cache)} entries")
            logger.info(f"Cache age: {cache_age_hours:.1f} hours, hits: {self.cache_hits}, misses: {self.cache_misses}")
            
            return True
        except Exception as e:
            logger.error(f"Error loading cache from disk: {str(e)}")
            self.translation_cache = {}
            self.cache_keys_order = []
            self.cache_hits = 0
            self.cache_misses = 0
            return False
    
    def _cleanup(self):
        """Cleanup resources before exiting"""
        try:
            # Save cache to disk before shutting down
            self._save_cache_to_disk()
            
            # Close ZMQ socket
            if hasattr(self, 'socket'):
                self.socket.close()
            
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                
            logger.info("TranslatorFixed agent shutdown complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        # Create the translator agent
        agent = TranslatorAgent()
        
        # Parse command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            # Run a simple self-test
            logger.info("Running self-test...")
            
            test_phrases = [
                "buksan mo ang file",
                "i-save mo ang document",
                "magsimula ng bagong project",
                "i-download mo ang file na iyon",
                "i-save mo ito"  # Test pronoun reference
            ]
            
            session_id = agent._generate_session_id()
            for phrase in test_phrases:
                logger.info(f"Testing: '{phrase}'")
                translated = agent.translate(phrase, session_id=session_id)
                logger.info(f"Result: '{translated}'")
            
            logger.info("Self-test complete")
        else:
            # Run the main server loop
            agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)
