"""
Simple Translation Adapter
A simplified version that just responds to ZMQ requests without Ollama dependency
"""
import zmq
import time
import logging
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleTranslationAdapter")

# ZMQ Configuration
ZMQ_PORT = 5581  # Translation adapter listens on this port

# Basic Tagalog-English translations
BASIC_TRANSLATIONS = {
    "magandang umaga": "good morning",
    "magandang hapon": "good afternoon",
    "magandang gabi": "good evening",
    "salamat": "thank you",
    "kamusta": "how are you",
    "oo": "yes",
    "hindi": "no",
    "mahal kita": "I love you",
    "kumain ka na ba": "have you eaten",
    "tulong": "help",
    "anong oras na": "what time is it"
}

class SimpleTranslationAdapter:
    def __init__(self, port=ZMQ_PORT):
        self.port = port
        self.context = zmq.Context()
        
        # REP socket for receiving translation requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"Simple Translation Adapter bound to port {self.port}")
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "last_error": None,
            "last_update": time.time()
        }
        
        self.running = True
        
    def translate(self, text, source_lang="tl", target_lang="en"):
        """Simple translation function that uses basic dictionary or word-by-word translation"""
        logger.info(f"Translating: '{text}' from {source_lang} to {target_lang}")
        
        start_time = time.time()
        self.stats["requests"] += 1
        
        if not text or text.strip() == "":
            self.stats["successful"] += 1
            return {
                "original": text,
                "translated": text,
                "model": "simple_fallback",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Empty text, no translation needed"
            }
        
        # Simple lowercase for matching
        text_lower = text.lower()
        
        # Check if text is in our basic translation dictionary
        if text_lower in BASIC_TRANSLATIONS:
            translation = BASIC_TRANSLATIONS[text_lower]
            success = True
        else:
            # Very simple word-by-word translation
            words = text_lower.split()
            translated_words = []
            
            for word in words:
                if word in BASIC_TRANSLATIONS:
                    translated_words.append(BASIC_TRANSLATIONS[word])
                else:
                    # Keep original word if no translation
                    translated_words.append(word)
            
            translation = " ".join(translated_words)
            
            # Add message that this is a simple translation
            translation += " [Note: This is a simplified translation as Ollama is not available]"
            success = True
        
        elapsed = time.time() - start_time
        
        # Update stats
        if success:
            self.stats["successful"] += 1
        else:
            self.stats["failures"] += 1
        
        return {
            "original": text,
            "translated": translation,
            "model": "simple_fallback",
            "success": success,
            "elapsed_sec": elapsed,
            "message": "Using simple translation dictionary (Ollama fallback)"
        }
        
    def run(self):
        """Run the adapter, listening for translation requests"""
        logger.info("Starting Simple Translation Adapter")
        
        while self.running:
            try:
                # Wait for a request
                request = self.socket.recv_json()
                logger.debug(f"Received request: {request}")
                
                # Process request
                if "action" in request and request["action"] == "translate":
                    # Get text and languages
                    text = request.get("text", "")
                    source_lang = request.get("source_lang", "tl")
                    target_lang = request.get("target_lang", "en")
                    
                    # Translate
                    result = self.translate(text, source_lang, target_lang)
                    
                    # Send response
                    self.socket.send_json(result)
                    logger.debug(f"Sent response: {result}")
                else:
                    # Unknown action
                    self.socket.send_json({
                        "success": False,
                        "message": f"Unknown action: {request.get('action', 'none')}"
                    })
                    logger.warning(f"Unknown action: {request.get('action', 'none')}")
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                try:
                    self.socket.send_json({
                        "success": False,
                        "message": f"Error: {str(e)}"
                    })
                except:
                    pass

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple Translation Adapter")
    parser.add_argument("--port", type=int, default=ZMQ_PORT, help=f"Port to bind to (default: {ZMQ_PORT})")
    args = parser.parse_args()
    
    print(f"=== Simple Translation Adapter ===")
    print(f"This is a FALLBACK adapter that doesn't require Ollama")
    print(f"It uses a simple dictionary for basic Tagalog-English translations")
    print(f"Binding to port: {args.port}")
    
    # Start the adapter
    adapter = SimpleTranslationAdapter(port=args.port)
    
    try:
        adapter.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        print("Adapter stopped.")
