import zmq
import json
import time
import logging
import os
import sys
import re
import uuid
import argparse
import requests
import urllib.parse
from collections import OrderedDict

# Optional PyTorch import with fallback and detailed error handling
try:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    HAS_TORCH = True
    TORCH_ERROR = None
except ImportError as e:
    torch = None
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
    HAS_TORCH = False
    TORCH_ERROR = str(e)
    print("="*80)
    print("PyTorch DEPENDENCY ERROR")
    print("="*80)
    print(f"Error: {e}")
    print("\nTo install PyTorch and required dependencies:")
    print("1. Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    print("2. Run: pip install transformers")
    print("3. Restart the adapter")
    print("\nFalling back to Google Translate until PyTorch is installed.")
    print("="*80)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("llm_translation_adapter.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("LLMTranslationAdapter")

# Default settings
DEFAULT_LLM_PORT = 5581  # Port for receiving translation requests
DEFAULT_MODEL_NAME = "facebook/nllb-200-1.3B"  # NLLB model for improved translation quality

# Define Google Translate fallback settings
GOOGLE_TRANSLATE_TIMEOUT = 5  # seconds

# Translation cache settings
CACHE_MAX_SIZE = 1000  # keep last 1000 distinct translation pairs
CACHE_STATS_INTERVAL = 100  # Log cache stats every 100 requests
CACHE_PERSIST_PATH = "translation_cache.json"  # Optional persistence

# NLLB language codes mapping
# NLLB uses specific codes: https://github.com/facebookresearch/flores/blob/main/flores200/README.md
LANG_MAPPING = {
    "en": "eng_Latn",  # English
    "tl": "fil_Latn",  # Filipino/Tagalog
    "ceb": "ceb_Latn", # Cebuano
    "ilo": "ilo_Latn", # Ilocano
    "es": "spa_Latn",  # Spanish
    "fr": "fra_Latn",  # French
    "de": "deu_Latn",  # German
    "ja": "jpn_Jpan",  # Japanese
    "ko": "kor_Hang",  # Korean
    "zh": "zho_Hans",  # Chinese (Simplified)
}

class LLMTranslationAdapter:
    """Enhanced adapter for NLLB-based translation with optimized caching and dynamic prompt handling"""
    def __init__(self, model_name=DEFAULT_MODEL_NAME, port=DEFAULT_LLM_PORT):
        """Initialize the LLM translation adapter"""
        # Set parameters with defaults
        self.model_name = model_name or DEFAULT_MODEL_NAME
        self.port = port or DEFAULT_LLM_PORT
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Using NLLB model: {self.model_name}")
        logger.info(f"Using device: {self.device}")
        
        # Set up ZMQ context
        self.context = zmq.Context()
        
        # Socket to receive translation requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"LLM Translation Adapter bound to port {self.port}")
        
        # Flag for running state
        self.running = True
        
        # Enhanced stats tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "avg_time": 0,
            "last_error": None,
            "google_translate_fallback": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_ratio": 0.0,
            "avg_nllb_time": 0.0,
            "avg_google_time": 0.0,
            "start_time": time.time(),
            "uptime_seconds": 0
        }
        
        # Enhanced LRU cache with metadata: {(text, src, tgt): (translated, timestamp, source)}
        self.cache: "OrderedDict[tuple, tuple]" = OrderedDict()
        
        # Try to load persistent cache if available
        self._load_cache()
        
        # Load NLLB model
        self.load_model()
    
    def load_model(self):
        """Load the NLLB translation model if PyTorch is available"""
        # If PyTorch is not available, don't attempt to load model
        if not HAS_TORCH:
            logger.warning("="*80)
            logger.warning("PyTorch not available. Will use Google Translate fallback for translation.")
            if TORCH_ERROR:
                logger.warning(f"Error details: {TORCH_ERROR}")
            logger.warning("To install PyTorch and required dependencies:")
            logger.warning("1. Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            logger.warning("2. Run: pip install transformers")
            logger.warning("3. Restart the adapter")
            logger.warning("="*80)
            self.model = None
            self.tokenizer = None
            return False
            
        try:
            logger.info(f"Loading NLLB model: {self.model_name}")
            start_time = time.time()
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Load model
            logger.info("Loading model...")
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
            # Move model to GPU if available
            if self.device == "cuda":
                self.model = self.model.to("cuda")
                gpu_info = torch.cuda.get_device_name(0)
                logger.info(f"Model loaded on GPU: {gpu_info}")
                # Log memory requirements
                memory_allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)  # Convert to GB
                logger.info(f"GPU memory allocated: {memory_allocated:.2f} GB")
            else:
                logger.info("Model loaded on CPU")
                
            elapsed = time.time() - start_time
            logger.info(f"[SUCCESS] NLLB model loaded in {elapsed:.2f} seconds")
            return True
        except Exception as e:
            logger.error("="*80)
            logger.error(f"[ERROR] Failed to load NLLB model: {e}")
            logger.error("Falling back to Google Translate for translations.")
            logger.error("If this is a memory error, try using a smaller model or freeing up GPU memory.")
            logger.error("="*80)
            self.model = None
            self.tokenizer = None
            return False
    
    def _load_cache(self):
        """Load translation cache from disk if available"""
        try:
            if os.path.exists(CACHE_PERSIST_PATH):
                with open(CACHE_PERSIST_PATH, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Convert list items back to tuples for keys
                    for key_list, value in cache_data.items():
                        # Convert string key back to tuple
                        key_tuple = tuple(key_list)
                        # Store with metadata
                        self.cache[key_tuple] = tuple(value)
                logger.info(f"Loaded {len(self.cache)} entries from persistent cache")
        except Exception as e:
            logger.warning(f"Failed to load persistent cache: {e}")
            # Start with empty cache
            self.cache = OrderedDict()
    
    def _save_cache(self):
        """Save translation cache to disk"""
        try:
            # Convert OrderedDict with tuple keys to a regular dict with list keys for JSON serialization
            cache_data = {}
            for key, value in self.cache.items():
                # Convert tuple key to list for JSON serialization
                key_list = list(key)
                # Store value with metadata
                cache_data[str(key_list)] = list(value)
                
            with open(CACHE_PERSIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.cache)} entries to persistent cache")
        except Exception as e:
            logger.warning(f"Failed to save persistent cache: {e}")
    
    def _clean_text_for_translation(self, text):
        """Clean and normalize text for better translation results"""
        if not text:
            return text
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove repetitive punctuation (e.g., !!! -> !)
        text = re.sub(r'([!?.,;:]){2,}', r'\1', text)
        
        return text
            
    def translate(self, text, src_lang="tl", tgt_lang="en", request=None):
        """Enhanced translation using NLLB model with improved prompt construction and context handling.
        
        This method implements several enhancements for Tagalog to English translation:
        1. Optimized caching with hit/miss tracking
        2. Dynamic prompt construction based on text length and content
        3. Context-aware translation parameters for different text types
        4. Post-processing to improve translation quality
        5. Detailed performance metrics and logging
        
        Args:
            text (str): Text to translate
            src_lang (str): Source language code (default: 'tl' for Tagalog)
            tgt_lang (str): Target language code (default: 'en' for English)
            
        Returns:
            dict: Translation result with metadata
        """
        # Generate a unique request ID for tracking
        request_id = str(uuid.uuid4())[:8]
        
        if not text or text.strip() == "":
            return {"status": "success", "success": True, "translated": text, "message": "Empty text provided", "request_id": request_id}
        
        # Update stats and calculate uptime
        self.stats["requests"] += 1
        self.stats["uptime_seconds"] = int(time.time() - self.stats["start_time"])
        
        # Clean and normalize input text
        cleaned_text = self._clean_text_for_translation(text)
        
        # Track metrics for this request
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)
        
        try:
            # Cache key based on cleaned text and languages
            cache_key = (cleaned_text, src_lang, tgt_lang)
            
            # Check cache
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                # Unpack cached result with metadata
                cached_translated, timestamp, source = cached_result
                
                # Move to end to mark as recently used
                self.cache.move_to_end(cache_key)
                
                # Update cache stats
                self.stats["cache_hits"] += 1
                total_lookups = self.stats["cache_hits"] + self.stats["cache_misses"]
                self.stats["cache_hit_ratio"] = self.stats["cache_hits"] / total_lookups if total_lookups > 0 else 0
                
                # Log cache stats periodically
                if self.stats["requests"] % CACHE_STATS_INTERVAL == 0:
                    logger.info(f"Cache stats: {self.stats['cache_hits']} hits, {self.stats['cache_misses']} misses, "
                               f"{self.stats['cache_hit_ratio']:.2%} hit ratio, {len(self.cache)} entries")
                
                logger.info(f"Cache hit (ReqID: {request_id}) for '{cleaned_text[:30]}...' [{word_count} words]")
                
                return {
                    "status": "success",
                    "success": True,
                    "translated": cached_translated,
                    "source": f"cache_{source}",  # Indicate original source in cache hit
                    "original": text,
                    "cache_age_seconds": int(time.time() - timestamp),
                    "request_id": request_id,
                    "word_count": word_count,
                    "char_count": char_count
                }
                
            # Update cache miss stats
            self.stats["cache_misses"] += 1
            total_lookups = self.stats["cache_hits"] + self.stats["cache_misses"]
            self.stats["cache_hit_ratio"] = self.stats["cache_hits"] / total_lookups if total_lookups > 0 else 0
            
            # Check if PyTorch is available and model is loaded
            if not HAS_TORCH or self.model is None or self.tokenizer is None:
                logger.info(f"PyTorch/NLLB model not available (ReqID: {request_id}), using Google Translate fallback")
                return self._google_translate_fallback(cleaned_text, src_lang, tgt_lang, request_id=request_id)
            
            # Map language codes to NLLB-specific codes
            nllb_src_lang = LANG_MAPPING.get(src_lang, "fil_Latn")  # Default to Filipino if not found
            nllb_tgt_lang = LANG_MAPPING.get(tgt_lang, "eng_Latn")  # Default to English if not found
            
            logger.info(f"Translating (ReqID: {request_id}) '{cleaned_text[:30]}...' [{word_count} words] from {src_lang} to {tgt_lang}")
            
            # Record start time
            start_time = time.time()
            
            # ENHANCED: Dynamic prompt construction based on text characteristics and context
            dynamic_prompt = cleaned_text
            
            # Extract context information if provided
            context = request.get('context', {})
            context_hint = context.get('context_hint', '')
            conversation_history = context.get('conversation_history', [])
            is_taglish = context.get('is_taglish', False)
            
            # For Tagalog to English specifically
            if src_lang == "tl" and tgt_lang == "en":
                # If we have conversation history, add it to the prompt
                if conversation_history:
                    history_text = "\n".join([f"Previous: {item}" for item in conversation_history])
                    dynamic_prompt = f"Context:\n{history_text}\n\nTranslate: {dynamic_prompt}"
                    logger.debug(f"Added conversation history context (ReqID: {request_id})")
                
                # If we have a context hint from the translator agent, use it
                if context_hint:
                    logger.info(f"Using provided context hint (ReqID: {request_id}): {context_hint}")
                    # Add the context hint to the prompt
                    dynamic_prompt = f"{context_hint}\n\n{dynamic_prompt}"
                # Otherwise, generate our own context hints
                else:
                    # 1. For very short commands (1-3 words), add command context
                    if word_count <= 3:
                        # For imperative commands, add clear context
                        lower_text = cleaned_text.lower()
                        imperative_markers = ["buksan", "isara", "i-", "mag", "gawin", "hanapin", "ipakita", 
                                         "tanggalin", "alisin", "ilagay", "ilipat", "ibalik", "itago"]
                        
                        for marker in imperative_markers:
                            if lower_text.startswith(marker):
                                dynamic_prompt = f"Utos: {cleaned_text}"  # "Command: {text}" in Tagalog
                                logger.debug(f"Added command context (ReqID: {request_id}): '{dynamic_prompt}'")
                                break
                
                # Handle Taglish specifically
                if is_taglish:
                    dynamic_prompt = f"Taglish text (mixed Tagalog and English): {dynamic_prompt}"
                    logger.debug(f"Added Taglish context (ReqID: {request_id})")
                
                # 2. For medium-length commands (4-8 words), add light context hints
                elif 4 <= word_count <= 8:
                    # Check if it's a question
                    if cleaned_text.endswith("?") or cleaned_text.lower().startswith("ano") or "ba" in cleaned_text.lower():
                        dynamic_prompt = f"Tanong: {cleaned_text}"  # "Question: {text}" in Tagalog
                        logger.debug(f"Added question context (ReqID: {request_id}): '{dynamic_prompt}'")
                
                # 3. For longer text, ensure proper sentence structure
                elif word_count > 8:
                    # Add period if missing at the end (for declarative sentences)
                    if not cleaned_text.endswith(('.', '?', '!', ':', ';')):
                        dynamic_prompt = cleaned_text + "."
                        logger.debug(f"Added sentence ending (ReqID: {request_id}): '{dynamic_prompt}'")
            
            # Tokenize with the dynamic prompt
            inputs = self.tokenizer(dynamic_prompt, return_tensors="pt")
            
            # Move to GPU if available
            if self.device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Set forced BOS token for target language
            forced_bos_token_id = self.tokenizer.lang_code_to_id[nllb_tgt_lang]
            
            # ENHANCED: Dynamic generation parameters based on text type
            # Adjust parameters based on text length and language pair
            if src_lang == "tl" and tgt_lang == "en":
                if word_count <= 5:  # Short commands need precision
                    generation_params = {
                        "max_length": min(128, word_count * 3 + 10),  # Dynamic but limited
                        "num_beams": 5,  # More beam search for accuracy
                        "length_penalty": 0.8,  # Slightly prefer shorter outputs for commands
                        "temperature": 0.2,  # Lower temperature for deterministic output
                        "early_stopping": True,
                        "do_sample": False,  # Deterministic for commands
                        "no_repeat_ngram_size": 2  # Avoid repetition
                    }
                else:  # Longer text needs more fluency
                    generation_params = {
                        "max_length": min(256, word_count * 2 + 50),  # Dynamic length based on input
                        "num_beams": 4,  # Balanced beam search
                        "length_penalty": 1.0,  # Neutral length penalty
                        "temperature": 0.3,  # Slightly higher for more natural output
                        "early_stopping": True,
                        "do_sample": False,  # Still deterministic for consistency
                        "no_repeat_ngram_size": 3  # Avoid repetition in longer text
                    }
            else:  # Default parameters for other language pairs
                generation_params = {
                    "max_length": 128,
                    "num_beams": 4,
                    "length_penalty": 1.0,
                    "temperature": 0.3,
                    "early_stopping": True,
                    "do_sample": False
                }
            
            # Generate translation with optimized parameters
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                **generation_params
            )
            
            # Decode the translation
            translated_text = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            
            # ENHANCED: Post-processing to improve translation quality
            if src_lang == "tl" and tgt_lang == "en":
                # 1. Remove any artifacts from dynamic prompt
                if translated_text.lower().startswith("command:") and len(translated_text) > 9:
                    translated_text = translated_text[9:].strip()
                elif translated_text.lower().startswith("question:") and len(translated_text) > 10:
                    translated_text = translated_text[10:].strip()
                elif translated_text.lower().startswith("utos:") and len(translated_text) > 6:
                    translated_text = translated_text[6:].strip()
                elif translated_text.lower().startswith("tanong:") and len(translated_text) > 8:
                    translated_text = translated_text[8:].strip()
                
                # 2. Fix common issues with NLLB Tagalog->English translations
                # Remove redundant articles
                translated_text = re.sub(r'\bthe\s+the\b', 'the', translated_text, flags=re.IGNORECASE)
                translated_text = re.sub(r'\ba\s+a\b', 'a', translated_text, flags=re.IGNORECASE)
                
                # 3. Fix capitalization at the beginning of sentences
                if translated_text and translated_text[0].islower():
                    translated_text = translated_text[0].upper() + translated_text[1:]
                
                # 4. Fix common mistranslations for command-like phrases
                if word_count <= 5:  # Only apply to short commands
                    command_fixes = {
                        "opened the": "open the",
                        "opened": "open",
                        "closed the": "close the",
                        "closed": "close",
                        "searched for": "search for",
                        "searched": "search",
                        "showed the": "show the",
                        "showed": "show",
                        "created a": "create a",
                        "created the": "create the",
                        "created": "create",
                        "deleted the": "delete the",
                        "deleted": "delete",
                        "saved the": "save the",
                        "saved": "save"
                    }
                    
                    # Only fix at the beginning of the text (likely commands)
                    for wrong, correct in command_fixes.items():
                        if translated_text.lower().startswith(wrong):
                            translated_text = correct + translated_text[len(wrong):]
                            logger.debug(f"Fixed command form (ReqID: {request_id}): '{wrong}' -> '{correct}'")
                            break
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Update stats
            self.stats["successful"] += 1
            if self.stats["successful"] == 1:
                self.stats["avg_time"] = elapsed_time
                self.stats["avg_nllb_time"] = elapsed_time
            else:
                self.stats["avg_time"] = ((self.stats["avg_time"] * (self.stats["successful"] - 1)) + elapsed_time) / self.stats["successful"]
                self.stats["avg_nllb_time"] = ((self.stats["avg_nllb_time"] * (self.stats["successful"] - 1)) + elapsed_time) / self.stats["successful"]
            
            logger.info(f"NLLB Translation successful in {elapsed_time:.2f}s: '{translated_text[:50]}...'")
            
            # Store successful translation in cache with metadata
            self.cache[cache_key] = (translated_text, time.time(), "nllb")
            
            # Trim cache if necessary
            if len(self.cache) > CACHE_MAX_SIZE:
                # popitem(last=False) pops least-recently-used entry
                self.cache.popitem(last=False)
                
            # Periodically save cache to disk (every 100 successful translations)
            if self.stats["successful"] % 100 == 0:
                self._save_cache()
            
            return {
                "status": "success",
                "translated_text": translated_text,
                "processing_time": elapsed_time,
                "model": "nllb",
                "model_name": self.model_name
            }
        except Exception as e:
            # Update stats
            self.stats["failures"] += 1
            self.stats["last_error"] = str(e)
            
            logger.error(f"NLLB Translation error: {e}")
            logger.info("Falling back to Google Translate")
            # Make sure response from fallback has success=True
            response = self._google_translate_fallback(cleaned_text, src_lang, tgt_lang, request_id=request_id)
            response["success"] = True
            return response
    
    def _google_translate_fallback(self, text, src_lang="tl", tgt_lang="en", request_id=None):
        """Enhanced fallback translation using Google Translate API with improved error handling and metrics.
        
        This method provides a reliable fallback when the NLLB model is not available or fails.
        It includes detailed logging, error handling, and performance tracking.
        
        Args:
            text (str): Text to translate
            src_lang (str): Source language code (default: 'tl' for Tagalog)
            tgt_lang (str): Target language code (default: 'en' for English)
            request_id (str): Optional request ID for tracking (generated if not provided)
            
        Returns:
            dict: Translation result with metadata
        """
        # Log NLLB status for debugging
        if not HAS_TORCH:
            logger.info(f"Using Google Translate because PyTorch is not installed (ReqID: {request_id})")
        elif self.model is None:
            logger.info(f"Using Google Translate because NLLB model failed to load (ReqID: {request_id})")
        else:
            logger.info(f"Using Google Translate as fallback (ReqID: {request_id})")
            
        # Add installation instructions periodically
        if self.stats["requests"] % 50 == 0 and not HAS_TORCH:
            logger.warning("="*80)
            logger.warning("REMINDER: PyTorch is not installed. For better translation quality, install PyTorch:")
            logger.warning("1. Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            logger.warning("2. Run: pip install transformers")
            logger.warning("="*80)
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())[:8]
            
        # Track metrics for this request
        word_count = len(text.split())
        char_count = len(text)
        
        logger.info(f"Using Google Translate fallback (ReqID: {request_id}) for: '{text[:30]}...' [{word_count} words]")
        start_time = time.time()
        
        try:
            # Construct the Google Translate API URL
            base_url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",  # Use free API
                "sl": src_lang,  # Source language
                "tl": tgt_lang,  # Target language
                "dt": "t",       # Return translated text
                "q": text         # Text to translate
            }
            
            # Construct full URL with parameters
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            
            # Make the request with timeout
            response = requests.get(url, timeout=GOOGLE_TRANSLATE_TIMEOUT)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse the response
            result = response.json()
            
            # Google Translate returns a nested list structure
            # Extract the translated text from it
            translated_text = ""
            if result and isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                for segment in result[0]:
                    if segment and isinstance(segment, list) and len(segment) > 0:
                        translated_text += segment[0] or ""
            
            # If we got an empty result, return the original text
            if not translated_text:
                logger.warning(f"Google Translate returned empty result (ReqID: {request_id}) for: '{text[:30]}...'")
                return {
                    "status": "error",
                    "success": False,
                    "translated": text,  # Return original text
                    "source": "google_translate_empty",
                    "original": text,
                    "message": "Google Translate returned empty result",
                    "request_id": request_id,
                    "word_count": word_count,
                    "char_count": char_count
                }
            
            # Post-process the translation for Tagalog to English
            if src_lang == "tl" and tgt_lang == "en" and translated_text:
                # Fix capitalization at the beginning of sentences
                if translated_text[0].islower():
                    translated_text = translated_text[0].upper() + translated_text[1:]
                
                # Fix common mistranslations for command-like phrases
                if word_count <= 5:  # Only apply to short commands
                    command_fixes = {
                        "opened the": "open the",
                        "opened": "open",
                        "closed the": "close the",
                        "closed": "close",
                        "searched for": "search for",
                        "searched": "search",
                        "showed the": "show the",
                        "showed": "show"
                    }
                    
                    # Only fix at the beginning of the text (likely commands)
                    for wrong, correct in command_fixes.items():
                        if translated_text.lower().startswith(wrong):
                            translated_text = correct + translated_text[len(wrong):]
                            logger.debug(f"Fixed command form in Google result (ReqID: {request_id}): '{wrong}' -> '{correct}'")
                            break
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Update stats
            self.stats["google_translate_fallback"] += 1
            self.stats["successful"] += 1
            
            # Update average Google Translate time
            if "avg_google_time" not in self.stats or self.stats["avg_google_time"] == 0:
                self.stats["avg_google_time"] = elapsed_time
            else:
                self.stats["avg_google_time"] = (self.stats["avg_google_time"] * (self.stats["google_translate_fallback"] - 1) + elapsed_time) / self.stats["google_translate_fallback"]
            
            # Add to cache
            cache_key = (text, src_lang, tgt_lang)
            self.cache[cache_key] = (translated_text, time.time(), "google")
            
            # Trim cache if needed
            if len(self.cache) > CACHE_MAX_SIZE:
                self.cache.popitem(last=False)  # Remove oldest item
            
            logger.info(f"Google Translate success (ReqID: {request_id}) in {elapsed_time:.2f}s: '{text[:30]}...' -> '{translated_text[:30]}...'")
            
            return {
                "status": "success",
                "success": True,
                "translated": translated_text,
                "source": "google_translate",
                "original": text,
                "translation_time": elapsed_time,
                "request_id": request_id,
                "word_count": word_count,
                "char_count": char_count
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Google Translate timeout (ReqID: {request_id}) for: '{text[:30]}...'")
            self.stats["failures"] += 1
            self.stats["last_error"] = "google_translate_timeout"
            
            return {
                "status": "error",
                "success": False,
                "translated": text,  # Return original text
                "source": "google_translate_timeout",
                "original": text,
                "message": "Google Translate request timed out",
                "request_id": request_id,
                "word_count": word_count,
                "char_count": char_count
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Translate request error (ReqID: {request_id}) for: '{text[:30]}...': {str(e)}")
            self.stats["failures"] += 1
            self.stats["last_error"] = "google_translate_request_error"
            
            return {
                "status": "error",
                "success": False,
                "translated": text,  # Return original text
                "source": "google_translate_request_error",
                "original": text,
                "message": f"Google Translate request error: {str(e)}",
                "request_id": request_id,
                "word_count": word_count,
                "char_count": char_count
            }
            
        except Exception as e:
            logger.error(f"Unexpected error with Google Translate (ReqID: {request_id}) for: '{text[:30]}...': {str(e)}")
            self.stats["failures"] += 1
            self.stats["last_error"] = "google_translate_unexpected_error"
            
            return {
                "status": "error",
                "success": False,
                "translated": text,  # Return original text
                "source": "google_translate_unexpected_error",
                "original": text,
                "message": f"Unexpected error with Google Translate: {str(e)}",
                "request_id": request_id,
                "word_count": word_count,
                "char_count": char_count
            }
    
    def run(self):
        """Main loop: receive requests, translate, send responses"""
        # Print startup banner with status information
        logger.info("="*80)
        logger.info("LLM Translation Adapter running...")
        logger.info(f"Model: {self.model_name if self.model else 'None (using Google Translate fallback)'}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Port: {self.port}")
        
        # Print PyTorch status
        if not HAS_TORCH:
            logger.warning("PyTorch is NOT installed - using Google Translate fallback only")
            logger.warning("For better translation quality, install PyTorch:")
            logger.warning("1. Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            logger.warning("2. Run: pip install transformers")
            logger.warning("3. Restart the adapter")
        elif self.model is None:
            logger.warning("NLLB model failed to load - using Google Translate fallback only")
        else:
            logger.info("NLLB model loaded successfully")
            
        logger.info("="*80)
        
        while self.running:
            try:
                # Check for incoming requests with a timeout
                poller = zmq.Poller()
                poller.register(self.socket, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    # Receive request
                    request_json = self.socket.recv_json()
                    
                    # Process request
                    action = request_json.get("action", "translate")
                    
                    if action == "translate":
                        # Extract parameters
                        text = request_json.get("text", "")
                        src_lang = request_json.get("source_lang", "tl")
                        tgt_lang = request_json.get("target_lang", "en")
                        
                        # Translate text
                        result = self.translate(text, src_lang, tgt_lang, request=request_json)
                        
                        # Send response
                        self.socket.send_json(result)
                    elif action == "health_check":
                        # Return health status
                        uptime = self._format_uptime(self.stats["uptime_seconds"])
                        
                        health_status = {
                            "status": "ok",
                            "model": self.model_name if self.model else "None (using Google Translate)",
                            "device": self.device,
                            "uptime": uptime,
                            "uptime_seconds": self.stats["uptime_seconds"],
                            "requests": self.stats["requests"],
                            "successful": self.stats["successful"],
                            "failures": self.stats["failures"],
                            "google_translate_fallback": self.stats["google_translate_fallback"],
                            "pytorch_installed": HAS_TORCH,
                            "nllb_model_loaded": self.model is not None,
                            "cache_size": len(self.cache),
                            "cache_hit_ratio": f"{self.stats['cache_hit_ratio']:.2%}",
                            "avg_nllb_time": f"{self.stats['avg_nllb_time']:.2f}ms",
                            "avg_google_time": f"{self.stats['avg_google_time']:.2f}ms",
                            "request_id": request_json.get("request_id", "health")
                        }
                        
                        self.socket.send_json(health_status)
                    elif action == "stop":
                        logger.info("Received stop command. Shutting down...")
                        self.running = False
                        self.socket.send_json({"status": "stopping"})
                    else:
                        # Unknown action
                        self.socket.send_json({
                            "status": "error",
                            "message": f"Unknown action: {action}"
                        })
                        
                # Periodically save cache
                if self.stats["requests"] % 100 == 0 and self.stats["requests"] > 0:
                    self._save_cache()
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    # Try to send error response
                    self.socket.send_json({
                        "status": "error",
                        "message": f"Server error: {str(e)}"
                    })
                except:
                    # If we can't send a response, just log the error
                    pass
                
                # Small delay to prevent CPU overuse in case of repeated errors
                time.sleep(0.1)
    
    def _format_uptime(self, seconds):
        """Format uptime in seconds to human-readable string"""
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def stop(self):
        """Stop the adapter and save cache"""
        self.running = False
        
        # Save cache before shutting down
        try:
            self._save_cache()
        except Exception as e:
            logger.error(f"Error saving cache during shutdown: {e}")
        
        # Close socket and context
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("LLM Translation Adapter stopped")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NLLB Translation Adapter')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL_NAME, help='NLLB model to use')
    parser.add_argument('--port', type=int, default=DEFAULT_LLM_PORT, help='Port to bind to')
    args = parser.parse_args()
    
    # Show adapter information
    print(f"=== NLLB Translation Adapter ===\n")
    print(f"Model: {args.model}")
    print(f"Port: {args.port}")
    print(f"Memory requirement: ~1.3GB")
    print(f"Expected speed: 150-200 tokens/second on RTX 3060\n")
    
    # Create and run the adapter
    logger.info("Starting NLLB Translation Adapter")
    adapter = LLMTranslationAdapter(
        model_name=args.model,
        port=args.port
    )
    
    try:
        adapter.run()
    except KeyboardInterrupt:
        logger.info("Adapter stopped by user")
    finally:
        adapter.stop()