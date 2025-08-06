"""
M2M100 Translation Adapter
Specialized for Tagalog-English translation using Facebook's M2M100 model
"""
import zmq
import json
import time
import logging
import sys
import os
import argparse
import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__) / "m2m_adapter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("M2MTranslationAdapter")

# Default ZMQ port
DEFAULT_PORT = 5581

# Default model
DEFAULT_MODEL = "facebook/m2m100_418M"  # 418M parameter model, ~1GB in size

# Language code mapping (ISO to M2M100 codes)
LANG_MAPPING = {
    # CRITICAL FIX: M2M100 directly supports Tagalog but with code 'tl' not 'fil'
    "tl": "tl",  # Correct code for Tagalog in M2M100
    "fil": "tl", # Map Filipino code to Tagalog
    "tagalog": "tl",  # Map full name to code
    "filipino": "tl", # Map full name to code
    
    # Other languages
    "en": "en",   # English
    "es": "es",   # Spanish
    "fr": "fr",   # French
    "de": "de",   # German
    "ja": "ja",   # Japanese
    "ko": "ko",   # Korean
    "zh": "zh",   # Chinese
}

class M2MTranslationAdapter:
    def __init__(self, port=DEFAULT_PORT, model_name=DEFAULT_MODEL, device=None):
        """Initialize the M2M100 translation adapter"""
        self.port = port
        self.model_name = model_name
        
        # Determine device (CPU/GPU)
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Using M2M100 model: {self.model_name}")
        logger.info(f"Using device: {self.device}")
        
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"M2M Translation Adapter bound to port {self.port}")
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "avg_time": 0,
            "last_error": None,
            "last_update": time.time()
        }
        
        # Load model
        self.load_model()
        
        # Running flag
        self.running = True
    
    def load_model(self):
        """Load M2M100 model and tokenizer"""
        try:
            logger.info(f"Loading M2M100 model: {self.model_name}")
            start_time = time.time()
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
            
            # Load model
            logger.info("Loading model...")
            self.model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)
            
            # Move to device
            if self.device == "cuda":
                self.model = self.model.to("cuda")
                gpu_info = torch.cuda.get_device_name(0)
                logger.info(f"Model loaded on GPU: {gpu_info}")
            else:
                logger.info("Model loaded on CPU")
            
            elapsed = time.time() - start_time
            logger.info(f"Model loaded in {elapsed:.2f} seconds")
            return True
        except Exception as e:
            logger.error(f"Error loading M2M100 model: {e}")
            raise
    
    def translate(self, text, src_lang="tl", tgt_lang="en"):
        """Translate text using M2M100 model"""
        if not text or text.strip() == "":
            return {
                "status": "success",
                "translated_text": text,
                "message": "Empty text provided"
            }
        
        try:
            # Update stats
            self.stats["requests"] += 1
            
            # Get M2M100 language codes
            m2m_src_lang = LANG_MAPPING.get(src_lang.lower(), src_lang)
            m2m_tgt_lang = LANG_MAPPING.get(tgt_lang.lower(), tgt_lang)
            
            logger.info(f"Translating '{text[:50]}...' from {src_lang} ({m2m_src_lang}) to {tgt_lang} ({m2m_tgt_lang})")
            
            # Record start time
            start_time = time.time()
            
            # Special handling for Taglish (code-switched Filipino-English)
            if src_lang.lower() in ["tl", "fil", "tagalog", "filipino"]:
                # Apply pre-processing for common Taglish patterns
                text = self._preprocess_taglish(text)
            
            # Set source language
            self.tokenizer.src_lang = m2m_src_lang
            
            # Tokenize
            encoded = self.tokenizer(text, return_tensors="pt")
            
            # Move to device
            if self.device == "cuda":
                encoded = {k: v.to("cuda") for k, v in encoded.items()}
            
            # Generate translation
            generated_tokens = self.model.generate(
                **encoded,
                forced_bos_token_id=self.tokenizer.get_lang_id(m2m_tgt_lang),
                max_length=128,
                num_beams=5,
                length_penalty=1.0,  # Encourage complete translations
                temperature=0.7,     # Better for Filipino fluency
                early_stopping=True
            )
            
            # Decode translation
            translated_text = self.tokenizer.batch_decode(
                generated_tokens, skip_special_tokens=True
            )[0]
            
            # Apply post-processing
            if tgt_lang.lower() == "en":
                translated_text = self._postprocess_english(translated_text)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Update stats
            self.stats["successful"] += 1
            if self.stats["successful"] == 1:
                self.stats["avg_time"] = elapsed_time
            else:
                self.stats["avg_time"] = (
                    (self.stats["avg_time"] * (self.stats["successful"] - 1) + elapsed_time
                ) / self.stats["successful"]
            
            logger.info(f"Translation successful in {elapsed_time:.2f}s: '{translated_text[:50]}...'")
            
            # Return result
            return {
                "status": "success",
                "translated_text": translated_text,
                "original_text": text,
                "processing_time": elapsed_time,
                "model": "m2m100",
                "model_name": self.model_name
            }
            
        except Exception as e:
            # Update stats
            self.stats["failures"] += 1
            self.stats["last_error"] = str(e)
            
            logger.error(f"Translation error: {e}")
            return {
                "status": "error",
                "message": f"Error during translation: {str(e)}"
            }
    
    def _preprocess_taglish(self, text):
        """Preprocess Taglish text for better translation quality"""
        # Common Taglish patterns and replacements
        patterns = {
            # Fix common Taglish patterns with hyphens
            r'i-([a-zA-Z]+)': r'i \1',   # i-download -> i download
            r'I-([a-zA-Z]+)': r'I \1',   # I-download -> I download
            r'na-([a-zA-Z]+)': r'na \1', # na-check -> na check
            
            # Add spaces after Filipino particles before English words
            r'(ang|ng|na|sa|at) ([A-Z][a-z]+)': r'\1 \2',
            
            # Handle common Filipino modal verbs with English main verbs
            r'(dapat|pwede|kailangan) ([a-zA-Z]+)': r'\1 \2',
        }
        
        # Apply patterns
        processed_text = text
        for pattern, replacement in patterns.items():
            import re
            processed_text = re.sub(pattern, replacement, processed_text)
        
        return processed_text
    
    def _postprocess_english(self, text):
        """Apply post-processing to improve English translation quality"""
        # Fix common translation artifacts
        import re

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
        
        # Capitalize first letter of sentence
        if text and len(text) > 0:
            text = text[0].upper() + text[1:]
        
        # Fix common issues
        fixes = {
            # Common translation artifacts
            r' the the ': ' the ',
            r' a a ': ' a ',
            
            # Fix question marks
            r'(\w)\?(\w)': r'\1? \2',
            
            # Fix periods
            r'(\w)\.(\w)': r'\1. \2',
            
            # Common mistranslations
            r'\bAko\b': 'I',
            r'\bIkaw\b': 'You',
            r'\bKami\b': 'We',
        }
        
        # Apply fixes
        for pattern, replacement in fixes.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def get_stats(self):
        """Get adapter statistics"""
        uptime = time.time() - self.stats["last_update"]
        stats = self.stats.copy()
        stats["uptime_seconds"] = uptime
        return stats
    
    def run(self):
        """Run the adapter, listening for translation requests"""
        logger.info("M2M Translation Adapter running...")
        
        while self.running:
            try:
                # Wait for a request
                request = self.socket.recv_json()
                logger.debug(f"Received request: {request}")
                
                if "action" in request and request["action"] == "translate":
                    # Extract text and language info
                    text = request.get("text", "")
                    
                    # Support both naming conventions for language params
                    src_lang = request.get("src_lang", request.get("source_lang", "tl")
                    tgt_lang = request.get("tgt_lang", request.get("target_lang", "en")
                    
                    # Translate
                    result = self.translate(text, src_lang, tgt_lang)
                    
                    # Send response
                    self.socket.send_json(result)
                    logger.debug("Sent translation response")
                
                elif "action" in request and request["action"] == "stats":
                    # Return statistics
                    stats = self.get_stats()
                    self.socket.send_json({
                        "status": "success",
                        "stats": stats
                    })
                    logger.debug("Sent stats response")
                
                else:
                    # Unknown action
                    self.socket.send_json({
                        "status": "error",
                        "message": f"Unknown action: {request.get('action', 'none')}"
                    })
                    logger.warning(f"Unknown action: {request.get('action', 'none')}")
                    
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                try:
                    self.socket.send_json({
                        "status": "error",
                        "message": f"Error: {str(e)}"
                    })
                except:
                    # Socket might be closed
                    pass
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
    
    def stop(self):
        """Stop the adapter"""
        logger.info("Stopping M2M Translation Adapter...")
        self.running = False
        self.socket.close()
        self.context.term()
        logger.info("M2M Translation Adapter stopped")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="M2M100 Translation Adapter")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage even if GPU is available")
    args = parser.parse_args()
    
    # Print startup info
    print(f"=== M2M100 Translation Adapter ===")
    print(f"Model: {args.model}")
    print(f"Port: {args.port}")
    print(f"Device: {'CPU' if args.cpu else 'GPU if available, otherwise CPU'}")
    print(f"Expected memory usage: ~1GB")
    print(f"Expected translation speed: 2-3 seconds per request on CPU, <1 second on GPU")
    print()
    
    # Set device
    device = "cpu" if args.cpu else None
    
    # Start the adapter
    logger.info("Starting M2M Translation Adapter")
    adapter = M2MTranslationAdapter(
        port=args.port,
        model_name=args.model,
        device=device
    )
    
    try:
        adapter.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        adapter.stop()
        print("Adapter stopped.")
