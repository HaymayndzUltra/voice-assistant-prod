"""
NLLB Translation Adapter
Connects to No Language Left Behind (NLLB) model for translation
Implementation: facebook/nllb-200-distilled-600M
"""
import zmq
import json
import time
import logging
import sys
import os
import argparse
import traceback
from datetime import datetime
from pathlib import Path

# Import Hugging Face Transformers
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / str(PathManager.get_logs_dir() / "nllb_adapter.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NLLBTranslationAdapter")

# Default ZMQ port
DEFAULT_PORT = 5581

# NLLB language codes
# NLLB uses specific codes: https://github.com/facebookresearch/flores/blob/main/flores200/README.md
LANG_MAPPING = {
    "en": "eng_Latn",  # English
    "tl": "fil_Latn",  # Filipino/Tagalog
    "es": "spa_Latn",  # Spanish
    "fr": "fra_Latn",  # French
    "de": "deu_Latn",  # German
    "ja": "jpn_Jpan",  # Japanese
    "ko": "kor_Hang",  # Korean
    "zh": "zho_Hans",  # Chinese (Simplified)
}

class NLLBTranslationAdapter:
    def __init__(self, port=DEFAULT_PORT, model_name="facebook/nllb-200-distilled-600M"):
        logger.info("=" * 80)
        logger.info("Initializing NLLB Translation Adapter")
        logger.info("=" * 80)
        
        self.port = port
        self.model_name = model_name
        self.context = zmq.Context()
        
        # REP socket for receiving translation requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"NLLB Translation Adapter bound to port {self.port}")
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "last_error": None,
            "start_time": time.time(),
            "avg_translation_time": 0,
            "health_check_requests": 0,
            "translation_requests": 0
        }
        
        # Load NLLB model and tokenizer
        self.load_model()
        
        self.running = True
        logger.info("NLLB Translation Adapter initialized successfully")
        logger.info("=" * 80)
        
    def load_model(self):
        """Load NLLB model and tokenizer"""
        try:
            logger.info(f"Loading NLLB model: {self.model_name}")
            start_time = time.time()
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
            # Try to use GPU if available
            import torch

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")
                self.device = "cuda"
                logger.info(f"Model loaded on GPU ({torch.cuda.get_device_name(0)})")
            else:
                self.device = "cpu"
                logger.info("Model loaded on CPU")
            
            elapsed = time.time() - start_time
            logger.info(f"Model loaded in {elapsed:.2f} seconds")
        except Exception as e:
            logger.error(f"Error loading NLLB model: {e}")
            logger.error(traceback.format_exc()
            raise
        
    def translate(self, text, src_lang="tl", tgt_lang="en"):
        """Translate text using NLLB model"""
        logger.info(f"Translating: '{text}' from {src_lang} to {tgt_lang}")
        
        start_time = time.time()
        self.stats["requests"] += 1
        self.stats["translation_requests"] += 1
        
        if not text or text.strip() == "":
            self.stats["successful"] += 1
            return {
                "original": text,
                "translated": text,
                "model": "nllb",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Empty text, no translation needed"
            }
        
        try:
            # Convert language codes to NLLB format
            nllb_src_lang = LANG_MAPPING.get(src_lang, LANG_MAPPING.get("en")
            nllb_tgt_lang = LANG_MAPPING.get(tgt_lang, LANG_MAPPING.get("en")
            
            logger.debug(f"Using NLLB language codes - Source: {nllb_src_lang}, Target: {nllb_tgt_lang}")
            
            # Tokenize input text
            inputs = self.tokenizer(text, return_tensors="pt")
            
            # Move inputs to the same device as the model
            if self.device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Set the language to translate to
            forced_bos_token_id = self.tokenizer.lang_code_to_id[nllb_tgt_lang]
            
            # Generate translation
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=128,
                num_beams=5,
                early_stopping=True
            )
            
            # Decode the generated tokens
            translation = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            
            # Successful translation
            elapsed = time.time() - start_time
            self.stats["successful"] += 1
            
            # Update average translation time
            if self.stats["successful"] == 1:
                self.stats["avg_translation_time"] = elapsed
            else:
                self.stats["avg_translation_time"] = (
                    (self.stats["avg_translation_time"] * (self.stats["successful"] - 1) + elapsed
                ) / self.stats["successful"]
            
            logger.info(f"Translation completed in {elapsed:.2f} seconds")
            
            return {
                "original": text,
                "translated": translation,
                "model": "nllb",
                "model_name": self.model_name,
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "success": True,
                "elapsed_sec": elapsed,
                "message": "Success"
            }
        except Exception as e:
            # Any other error
            elapsed = time.time() - start_time
            self.stats["failures"] += 1
            self.stats["last_error"] = str(e)
            
            logger.error(f"Translation error: {e}")
            logger.error(traceback.format_exc()
            
            return {
                "original": text,
                "translated": text,  # Return original text on error
                "model": "nllb",
                "success": False,
                "elapsed_sec": elapsed,
                "message": f"Error: {str(e)}"
            }
    
    def get_stats(self):
        """Get adapter statistics"""
        return {
            "status": "ok",
            "service": "nllb_adapter",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.stats["start_time"],
            "total_requests": self.stats["requests"],
            "successful_requests": self.stats["successful"],
            "failed_requests": self.stats["failures"],
            "translation_requests": self.stats["translation_requests"],
            "health_check_requests": self.stats["health_check_requests"],
            "avg_translation_time": self.stats["avg_translation_time"],
            "last_error": self.stats["last_error"],
            "device": self.device,
            "model_name": self.model_name
        }
    
    def run(self):
        """Run the adapter, listening for translation requests"""
        logger.info("Starting NLLB Translation Adapter")
        
        while self.running:
            try:
                # Wait for a request
                request = self.socket.recv_json()
                logger.debug(f"Received request: {request}")
                
                # Process request
                if "action" in request:
                    if request["action"] == "translate":
                    # Get text and languages
                    text = request.get("text", "")
                    src_lang = request.get("src_lang", request.get("source_lang", "tl")  # Support both naming conventions
                    tgt_lang = request.get("tgt_lang", request.get("target_lang", "en")
                    
                    # Translate
                    result = self.translate(text, src_lang, tgt_lang)
                    
                    # Send response
                    self.socket.send_json(result)
                    logger.debug(f"Sent response: {result}")
                    
                    elif request["action"] == "health_check":
                        # Handle health check request
                        self.stats["health_check_requests"] += 1
                        logger.info("Processing health check request")
                        response = self.get_stats()
                        logger.info(f"Health check response: {json.dumps(response)}")
                        self.socket.send_json(response)
                        
                    elif request["action"] == "stats":
                    # Return statistics
                    self.socket.send_json(self.get_stats()
                    logger.debug("Sent stats")
                    
                else:
                    # Unknown action
                        error_msg = f"Unknown action: {request.get('action', 'none')}"
                        logger.warning(error_msg)
                        self.socket.send_json({
                            "success": False,
                            "message": error_msg
                        })
                else:
                    # No action specified
                    error_msg = "No action specified in request"
                    logger.warning(error_msg)
                    self.socket.send_json({
                        "success": False,
                        "message": error_msg
                    })
            except Exception as e:
                error_msg = f"Error processing request: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc()
                try:
                    self.socket.send_json({
                        "success": False,
                        "message": error_msg
                    })
                except:
                    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NLLB Translation Adapter")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--model", type=str, default="facebook/nllb-200-distilled-600M", help="NLLB model to use")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("=== NLLB Translation Adapter ===")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Binding to port: {args.port}")
    logger.info(f"Expected memory usage: ~1.3GB")
    logger.info(f"Estimated translation speed: 150-200 tokens/second on RTX 3060")
    logger.info("=" * 80)
    
    # Start the adapter
    adapter = NLLBTranslationAdapter(port=args.port, model_name=args.model)
    
    try:
        adapter.run()
    except KeyboardInterrupt:
        logger.info("NLLB Translation Adapter interrupted by user")
    except Exception as e:
        logger.error(f"Error running NLLB Translation Adapter: {str(e)}")
        logger.error(traceback.format_exc()
        sys.exit(1)
