import os
import re
import time
import uuid
import json
import zmq
import logging
import requests
from typing import Tuple, Dict, List, Optional, Any, Union
from config.system_config import (
    TRANSLATOR_AGENT_PORT,
    NLLB_ADAPTER_PORT,
    NLLB_ADAPTER_HOST,
    TRANSLATOR_LOG_LEVEL,
    USE_NLLB_ADAPTER,
    USE_GOOGLE_TRANSLATE_FALLBACK,
    HIGH_CONF_THRESHOLD_PATTERN,
    HIGH_CONF_THRESHOLD_NLLB,
    LOW_CONF_THRESHOLD
)

# Configure logging
logging.basicConfig(level=TRANSLATOR_LOG_LEVEL,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('translator_agent')

class TranslatorAgent:
    def __init__(self):
        # Initialize ZMQ context and socket for communication
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{TRANSLATOR_AGENT_PORT}")
        
        # Initialize NLLB adapter socket if enabled
        self.nllb_socket = None
        if USE_NLLB_ADAPTER:
            self.nllb_socket = self.context.socket(zmq.REQ)
            self.nllb_socket.connect(f"tcp://{NLLB_ADAPTER_HOST}:{NLLB_ADAPTER_PORT}")
            logger.info(f"Connected to NLLB adapter at {NLLB_ADAPTER_HOST}:{NLLB_ADAPTER_PORT}")
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "pattern_match_success": 0,
            "nllb_success": 0,
            "google_translate_success": 0,
            "failures": 0,
            "english_skipped_count": 0,
            "last_translation_method": "none",
            "pattern_times_ms": [],
            "nllb_times_ms": [],
            "google_times_ms": [],
            "total_times_ms": [],
        }
        
        # Current translation tracking (for response metadata)
        self.current_translation_confidence = 0.0
        self.current_translation_method = "none"
        
        logger.info(f"Translator agent initialized and listening on port {TRANSLATOR_AGENT_PORT}")
        
    def translate_command(self, text: str, source_lang="tl", target_lang="en", request_id=None) -> str:
        """Enhanced translation of Filipino text to English using confidence-driven tiered approach.
        
        This method implements a confidence-driven tiered translation approach:
        1. Language/Taglish detection: Skip translation if already English or mostly English Taglish
        2. Tier 1 (Pattern Matching): Use if confidence >= HIGH_CONF_THRESHOLD_PATTERN
        3. Tier 2 (NLLB Adapter): Use if confidence >= HIGH_CONF_THRESHOLD_NLLB
        4. Tier 3 (Google Translate API): Use as fallback for low confidence or failed translations
        5. Final Fallback: Return translation with highest confidence or original text
        
        Args:
            text (str): Text to translate
            source_lang (str): Source language code (default: 'tl' for Tagalog)
            target_lang (str): Target language code (default: 'en' for English)
            request_id (str, optional): Request ID for end-to-end tracing (generated if not provided)
            
        Returns:
            str: Translated text (or original if translation fails)
        """
        start_time_translate = time.time()
        self.stats["requests"] += 1
        self.stats["last_translation_method"] = "unknown"
        
        # Initialize confidence tracking for this translation request
        self.current_translation_confidence = 0.0
        self.current_translation_method = "unknown"
        
        # Store original text for potential fallback
        original_text_for_return = str(text)
        
        # Track request details for analytics
        if not request_id:
            request_id = str(uuid.uuid4())[:8]  # Generate short ID for logging if not provided
        word_count = len(text.split())
        char_count = len(text)
        
        try:
            # Step 0: Input validation and preprocessing
            if not text or text.strip() == "":
                logger.info(f"Empty text provided, skipping translation (ReqID: {request_id})")
                self.stats["last_translation_method"] = "skipped_empty"
                return original_text_for_return
            
            # Normalize text: remove excessive spaces, standardize punctuation
            normalized_text = re.sub(r'\s+', ' ', text.strip())
            
            # Step 1: Language detection - check if already English
            if self._is_likely_english(normalized_text):
                logger.info(f"Text appears to be English already (ReqID: {request_id}): '{normalized_text[:50]}...'")
                self.stats["english_skipped_count"] += 1
                self.stats["last_translation_method"] = "skipped_english"
                self.current_translation_method = "skipped_english"
                self.current_translation_confidence = 1.0  # High confidence for English detection
                return original_text_for_return
            
            # Step 1.5: Check for exact matches in our special cases dictionary first (highest priority)
            # This ensures common commands are handled by pattern matching
            special_cases = {
                "buksan mo ang file": "open the file",
                "i-save mo ang document": "save the document",
                "isara mo ang window": "close the window",
                "i-download mo ang file na iyon": "download that file",
                "i-delete mo ang file na ito": "delete this file"
            }
            
            if normalized_text.lower() in special_cases:
                translation = special_cases[normalized_text.lower()]
                logger.info(f"Direct special case match (ReqID: {request_id}): '{normalized_text[:50]}...' -> '{translation[:50]}...'")
                self.stats["pattern_match_success"] += 1
                self.current_translation_method = "pattern_direct_special"
                self.current_translation_confidence = 1.0  # Perfect confidence for direct matches
                self.stats["last_translation_method"] = "pattern_direct_special"
                return translation
            
            # Step 2: Taglish detection - check if mixed language
            is_taglish, fil_ratio, eng_ratio = self._detect_taglish(normalized_text)
            
            # If mostly English Taglish (>70% English), skip translation
            if is_taglish and eng_ratio > 0.7:
                logger.info(f"Text appears to be mostly English Taglish (ReqID: {request_id}): '{normalized_text[:50]}...'")
                self.stats["english_skipped_count"] += 1
                self.stats["last_translation_method"] = "skipped_mostly_english_taglish"
                self.current_translation_method = "skipped_mostly_english_taglish"
                self.current_translation_confidence = eng_ratio  # Confidence based on English ratio
                return original_text_for_return
            
            # Initialize variables to track best translation and confidence across all tiers
            best_translation = original_text_for_return
            best_confidence = 0.0
            best_method = "original_text"
            
            # Step 3: Tier 1 - Pattern matching (fastest and most reliable for common phrases)
            logger.debug(f"Attempting pattern matching (ReqID: {request_id}): '{normalized_text[:50]}...'")
            pattern_translated_text, pattern_confidence = self._pattern_match_translation(normalized_text)
            
            # For common commands, prioritize pattern matching more aggressively
            # Check if this is likely a command (short text with command words)
            is_likely_command = False
            if len(normalized_text.split()) <= 6:  # Short phrase (likely a command)
                command_indicators = ['buksan', 'isara', 'i-save', 'i-open', 'i-close', 'i-download', 'i-upload', 'i-delete', 'i-create']
                if any(indicator in normalized_text.lower() for indicator in command_indicators):
                    is_likely_command = True
                    logger.debug(f"Text appears to be a command: '{normalized_text[:50]}...' (ReqID: {request_id})")
            
            if pattern_translated_text is not None:
                # Track pattern match metrics
                self.stats["pattern_match_success"] += 1
                match_method = self.stats.get('last_translation_method', 'pattern')
                translation_time_ms = (time.time() - start_time_translate) * 1000
                
                # Track pattern matching metrics
                if 'pattern_times_ms' not in self.stats:
                    self.stats['pattern_times_ms'] = []
                self.stats['pattern_times_ms'].append(translation_time_ms)
                self.stats['pattern_avg_time_ms'] = sum(self.stats['pattern_times_ms']) / len(self.stats['pattern_times_ms'])
                
                logger.info(f"Pattern matching succeeded in {translation_time_ms:.2f}ms (confidence: {pattern_confidence:.2f}) (ReqID: {request_id}): "
                           f"'{normalized_text[:50]}...' -> '{pattern_translated_text[:50]}...'")
                
                # Boost confidence for likely commands
                if is_likely_command and pattern_confidence >= 0.7:
                    pattern_confidence = min(1.0, pattern_confidence + 0.2)  # Boost confidence but cap at 1.0
                    logger.debug(f"Boosted command pattern confidence to {pattern_confidence:.2f} (ReqID: {request_id})")
                
                # Update best translation if this has higher confidence
                if pattern_confidence > best_confidence:
                    best_translation = pattern_translated_text
                    best_confidence = pattern_confidence
                    best_method = match_method
                    
                    # Store the current best confidence and method for response
                    self.current_translation_confidence = pattern_confidence
                    self.current_translation_method = match_method
                
                # Use pattern matching result if it has high confidence
                if pattern_confidence >= HIGH_CONF_THRESHOLD_PATTERN:
                    logger.info(f"Using high-confidence pattern matching (confidence: {pattern_confidence:.2f}) (ReqID: {request_id})")
                    self.current_translation_method = match_method
                    self.current_translation_confidence = pattern_confidence
                    self._update_avg_translation_time(translation_time_ms)
                    return pattern_translated_text
            
            # Step 4: Tier 2 - NLLB adapter (more accurate for complex sentences)
            if USE_NLLB_ADAPTER:
                logger.debug(f"Attempting NLLB adapter translation (ReqID: {request_id}): '{normalized_text[:50]}...'")
                
                # Prepare context hints for NLLB adapter to improve translation quality
                context_hints = {}
                if is_likely_command:
                    context_hints["domain"] = "command"
                    context_hints["style"] = "imperative"
                
                # Call NLLB adapter
                nllb_success, translated_text_nllb, nllb_confidence = self._nllb_adapter_translation(
                    normalized_text, source_lang, target_lang, context_hints=context_hints)
                
                if nllb_success:
                    self.stats["nllb_success"] += 1
                    nllb_method = "nllb_adapter"
                    self.stats["last_translation_method"] = nllb_method
                    translation_time_ms = (time.time() - start_time_translate) * 1000
                    
                    # Track NLLB metrics
                    if 'nllb_times_ms' not in self.stats:
                        self.stats['nllb_times_ms'] = []
                    self.stats['nllb_times_ms'].append(translation_time_ms)
                    self.stats['nllb_avg_time_ms'] = sum(self.stats['nllb_times_ms']) / len(self.stats['nllb_times_ms'])
                    
                    logger.info(f"NLLB adapter succeeded in {translation_time_ms:.2f}ms (confidence: {nllb_confidence:.2f}) (ReqID: {request_id}): "
                               f"'{normalized_text[:50]}...' -> '{translated_text_nllb[:50]}...'")
                    
                    # Update best translation if this has higher confidence
                    if nllb_confidence > best_confidence:
                        best_translation = translated_text_nllb
                        best_confidence = nllb_confidence
                        best_method = nllb_method
                        
                        # Store the current best confidence and method for response
                        self.current_translation_confidence = nllb_confidence
                        self.current_translation_method = nllb_method
                    
                    # Use NLLB result if it has high confidence
                    if nllb_confidence >= HIGH_CONF_THRESHOLD_NLLB:
                        logger.info(f"Using high-confidence NLLB adapter (confidence: {nllb_confidence:.2f}) (ReqID: {request_id})")
                        self.current_translation_method = nllb_method
                        self.current_translation_confidence = nllb_confidence
                        self._update_avg_translation_time(translation_time_ms)
                        return translated_text_nllb
                else:
                    logger.warning(f"NLLB adapter failed (ReqID: {request_id})")
            
            # Step 5: Tier 3 - Google Translate fallback (if enabled and other methods failed or had low confidence)
            if USE_GOOGLE_TRANSLATE_FALLBACK and best_confidence < HIGH_CONF_THRESHOLD_NLLB:
                logger.debug(f"Attempting Google Translate fallback (ReqID: {request_id}): '{normalized_text[:50]}...'")
                google_success, translated_text_google, google_confidence = self._google_translate_fallback(normalized_text, source_lang, target_lang, request_id)
                
                if google_success:
                    self.stats["google_translate_success"] = self.stats.get("google_translate_success", 0) + 1
                    google_method = "google_translate"
                    self.stats["last_translation_method"] = google_method
                    translation_time_ms = (time.time() - start_time_translate) * 1000
                    
                    # Track Google Translate metrics
                    if 'google_times_ms' not in self.stats:
                        self.stats['google_times_ms'] = []
                    self.stats['google_times_ms'].append(translation_time_ms)
                    self.stats['google_avg_time_ms'] = sum(self.stats['google_times_ms']) / len(self.stats['google_times_ms'])
                    
                    logger.info(f"Google Translate fallback succeeded in {translation_time_ms:.2f}ms (confidence: {google_confidence:.2f}) (ReqID: {request_id}): "
                               f"'{normalized_text[:50]}...' -> '{translated_text_google[:50]}...'")
                    
                    # Update best translation if this has higher confidence
                    if google_confidence > best_confidence:
                        best_translation = translated_text_google
                        best_confidence = google_confidence
                        best_method = google_method
                        
                        # Store the current best confidence and method for response
                        self.current_translation_confidence = google_confidence
                        self.current_translation_method = google_method
                    
                    # Use Google Translate result if it has high confidence
                    if google_confidence >= HIGH_CONF_THRESHOLD_NLLB:
                        logger.info(f"Using high-confidence Google Translate (confidence: {google_confidence:.2f}) (ReqID: {request_id})")
                        self.current_translation_method = google_method
                        self.current_translation_confidence = google_confidence
                        self._update_avg_translation_time(translation_time_ms)
                        return translated_text_google
                else:
                    logger.warning(f"Google Translate fallback failed (ReqID: {request_id})")
            
            # If we haven't returned a translation yet, try Google Translate as a direct fallback
            if USE_GOOGLE_TRANSLATE_FALLBACK and best_confidence < HIGH_CONF_THRESHOLD_NLLB:
                logger.info(f"Attempting direct Google Translate fallback (ReqID: {request_id})")
                google_success, translated_text_google, google_confidence = self._google_translate_fallback(normalized_text, source_lang, target_lang, request_id)
                if google_success:
                    self.stats["google_translate_success"] = self.stats.get("google_translate_success", 0) + 1
                    google_method = "google_translate_direct"
                    self.stats["last_translation_method"] = google_method
                    translation_time_ms = (time.time() - start_time_translate) * 1000
                    
                    # Track Google Translate metrics
                    if 'google_times_ms' not in self.stats:
                        self.stats['google_times_ms'] = []
                    self.stats['google_times_ms'].append(translation_time_ms)
                    self.stats['google_avg_time_ms'] = sum(self.stats['google_times_ms']) / len(self.stats['google_times_ms'])
                    
                    logger.info(f"Google Translate direct fallback succeeded in {translation_time_ms:.2f}ms (confidence: {google_confidence:.2f}) (ReqID: {request_id}): "
                               f"'{normalized_text[:50]}...' -> '{translated_text_google[:50]}...'")
                    
                    # Update best translation if this has higher confidence
                    if google_confidence > best_confidence:
                        best_translation = translated_text_google
                        best_confidence = google_confidence
                        best_method = google_method
                        
                        # Store the current best confidence and method for response
                        self.current_translation_confidence = google_confidence
                        self.current_translation_method = google_method
                else:
                    logger.warning(f"Google Translate direct fallback failed (ReqID: {request_id})")
            
            # Final decision: Use the translation with the highest confidence
            translation_time_ms = (time.time() - start_time_translate) * 1000
            
            if best_confidence > LOW_CONF_THRESHOLD:
                # We have at least one translation with acceptable confidence
                logger.info(f"Using best translation method: {best_method} (confidence: {best_confidence:.2f}) in {translation_time_ms:.2f}ms (ReqID: {request_id})")
                self.stats["last_translation_method"] = best_method
                self.current_translation_method = best_method
                self.current_translation_confidence = best_confidence
                self._update_avg_translation_time(translation_time_ms)
                return best_translation
            else:
                # No translation with acceptable confidence, return original text
                self.stats["failures"] += 1
                self.stats["last_translation_method"] = "all_methods_failed"
                self.current_translation_method = "all_methods_failed"
                self.current_translation_confidence = 0.0
                
                logger.warning(f"All translation methods failed or had low confidence in {translation_time_ms:.2f}ms (ReqID: {request_id}): '{normalized_text[:50]}...'. Returning original text.")
                self._update_avg_translation_time(translation_time_ms)
                return normalized_text
            
        except Exception as e:
            self.stats["failures"] += 1
            self.stats["last_translation_method"] = "exception_in_translate_command"
            translation_time_ms = (time.time() - start_time_translate) * 1000
            logger.error(f"Unexpected error in translate_command (ReqID: {request_id}) for '{text[:50]}...' after {translation_time_ms:.2f}ms: {str(e)}", exc_info=True)
            return original_text_for_return
