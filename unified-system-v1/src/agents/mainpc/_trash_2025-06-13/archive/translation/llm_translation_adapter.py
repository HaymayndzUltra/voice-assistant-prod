from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
LLM Translation Adapter
Connects to LLMs for high-quality translation using the dynamic runtime system
"""
import sys
import os
import zmq
import json
import time
import logging
import threading
import requests
from typing import Dict, Any, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import LLM runtime tools
from src.agents.mainpc.llm_runtime_tools import ensure_model, get_model_status, get_model_url, get_model_api_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "llm_translation_adapter.log"))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LLMTranslationAdapter")

# ZMQ Configuration
ZMQ_PORT = 5581  # Translation adapter listens on this port
ZMQ_HEALTH_PORT = 5597  # Health reporting

class LLMTranslationAdapter(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="LlmTranslationAdapter")
        self.model = model
        self.port = port
        self.host = host
        self.context = zmq.Context()
        
        # REP socket for receiving translation requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"LLM Translation Adapter bound to port {self.port}")
        
        # Health reporting socket
        self.health_socket = self.context.socket(zmq.PUB)
        try:
            self.health_socket.connect(f"tcp://localhost:{ZMQ_HEALTH_PORT}")
            logger.info(f"Connected to health dashboard on port {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.warning(f"Could not connect to health dashboard: {e}")
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "fallbacks_used": 0,
            "avg_latency": 0,
            "last_error": None,
            "last_update": time.time()
        }
        
        # Check primary model on startup
        logger.info(f"Using {self.model} as primary translation model")
        success, fallback = ensure_model(self.model)
        if success:
            if fallback:
                logger.warning(f"Primary model '{self.model}' not available, using fallback '{fallback}'")
            else:
                logger.info(f"Primary model '{self.model}' available")
        else:
            logger.error(f"Failed to ensure translation model '{self.model}' is available")
        
        # Start health reporting thread
        self.running = True
        self.health_thread = threading.Thread(target=self.report_health)
        self.health_thread.daemon = True
        self.health_thread.start()
    
    def translate(self, text: str, source_lang: str = "tl", target_lang: str = "en") -> Dict[str, Any]:
        """
        Translate text using the LLM
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Dict with translation result and metadata
        """
        start_time = time.time()
        self.stats["requests"] += 1
        
        if not text or text.strip() == "":
            return {
                "original": text,
                "translated": text,
                "model": "none",
                "success": True,
                "elapsed_sec": 0,
                "message": "Empty text, no translation needed"
            }
        
        # Build prompt based on source language
from src.agents.mainpc.taglish_detector import detect_taglish
from common.env_helpers import get_env
        is_taglish, fil_ratio, eng_ratio = detect_taglish(text)
        if is_taglish:
            logger.info(f"[LLMTranslationAdapter] Taglish detected: Filipino={fil_ratio:.2f}, English={eng_ratio:.2f}")
        if source_lang == "tl" and target_lang == "en":
            prompt = f"""
            You are a highly skilled translator from Tagalog to English. Your only job is to translate the input text accurately. 
            
            Do not add any additional text, commentary, or answer as if this is a question. Simply translate the given Tagalog text to accurate English.
            
            For example:
            Tagalog: "Kamusta ka?"
            English: "How are you?"
            
            Tagalog: "Mabuti naman ako, salamat."
            English: "I am fine, thank you."
            
            Tagalog: "Ang bagal mo mag translate"
            English: "You are slow at translating"
            
            Tagalog: "Ayusin mo"
            English: "Fix it"
            
            Tagalog: "{text}"
            English:
            """
        elif source_lang == "en" and target_lang == "tl":
            prompt = f"""
            You are an English to Tagalog (Filipino) translator. Translate the following text to natural, fluent Tagalog.
            Remember to preserve the meaning, tone, and intent of the original text. If a word doesn't have a direct translation,
            translate its meaning rather than transliterating.
            
            English text: "{text}"
            
            Tagalog translation:
            """
        else:
            # Generic translation prompt
            prompt = f"""
            Translate the following text from {source_lang} to {target_lang}:
            
            Original text: "{text}"
            
            Translation:
            """
        
        # Ensure primary model is available
        success, fallback_used = ensure_model(self.model)
        model_used = fallback_used if fallback_used else self.model
        
        if not success:
            # No model available, return error
            elapsed = time.time() - start_time
            self.stats["failures"] += 1
            self.stats["last_error"] = "No translation model available"
            
            # Update average latency
            if self.stats["avg_latency"] == 0:
                self.stats["avg_latency"] = elapsed
            else:
                self.stats["avg_latency"] = (self.stats["avg_latency"] * 0.9) + (elapsed * 0.1)
            
            return {
                "original": text,
                "translated": text,  # Return original text on error
                "model": "none",
                "success": False,
                "elapsed_sec": elapsed,
                "message": "No translation model available"
            }
        
        try:
            # Get model URL and API type from configuration
            model_url = get_model_url(model_used)
            api_type = get_model_api_type(model_used)
            
            logger.info(f"Using model {model_used} with URL {model_url} and API type {api_type}")
            
            # If URL is not configured, use default Ollama URL
            if not model_url:
                if api_type == "ollama":
                    # Try local Ollama first
                    model_url = "http://localhost:11434/api/generate"
                else:
                    # Default llama.cpp server API
                    model_url = "http://localhost:8080/completion"
            
            api_url = model_url
            
            # Call the API with format depending on API type
            if api_type == "direct":
                # Direct API format (like Phi-3 API)
                response = requests.post(
                    api_url,
                    json={
                        "prompt": prompt,
                        "temperature": 0.3,
                        "max_tokens": 1024,
                        "stop": ["\n\n"]
                    },
                    timeout=10
                )
            else:  # ollama API
                response = requests.post(
                    api_url,
                    json={
                        "model": model_used,
                        "prompt": prompt,
                        "temperature": 0.3,
                        "max_tokens": 1024,
                        "stop": ["\n\n"]
                    },
                    timeout=10
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract translation based on API type
                if api_type == "direct":
                    # Direct API response format
                    translation = result.get("content", "").strip()
                    if not translation and "choices" in result:
                        # Handle OpenAI-like API format
                        translation = result["choices"][0]["message"]["content"].strip()
                else:  # ollama API
                    translation = result.get("response", "").strip()
                
                # Successful translation
                elapsed = time.time() - start_time
                self.stats["successful"] += 1
                
                # Update average latency
                if self.stats["avg_latency"] == 0:
                    self.stats["avg_latency"] = elapsed
                else:
                    self.stats["avg_latency"] = (self.stats["avg_latency"] * 0.9) + (elapsed * 0.1)
                
                # Check if fallback was used
                if fallback_used:
                    self.stats["fallbacks_used"] += 1
                
                return {
                    "original": text,
                    "translated": translation,
                    "model": model_used,
                    "success": True,
                    "elapsed_sec": elapsed,
                    "fallback_used": fallback_used is not None
                }
            else:
                # API error
                elapsed = time.time() - start_time
                self.stats["failures"] += 1
                self.stats["last_error"] = f"API error: {response.status_code}"
                
                # Update average latency
                if self.stats["avg_latency"] == 0:
                    self.stats["avg_latency"] = elapsed
                else:
                    self.stats["avg_latency"] = (self.stats["avg_latency"] * 0.9) + (elapsed * 0.1)
                
                return {
                    "original": text,
                    "translated": text,  # Return original text on error
                    "model": model_used,
                    "success": False,
                    "elapsed_sec": elapsed,
                    "message": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            # Any other error
            elapsed = time.time() - start_time
            self.stats["failures"] += 1
            self.stats["last_error"] = str(e)
            
            # Update average latency
            if self.stats["avg_latency"] == 0:
                self.stats["avg_latency"] = elapsed
            else:
                self.stats["avg_latency"] = (self.stats["avg_latency"] * 0.9) + (elapsed * 0.1)
            
            logger.error(f"Translation error: {e}")
            
            return {
                "original": text,
                "translated": text,  # Return original text on error
                "model": model_used,
                "success": False,
                "elapsed_sec": elapsed,
                "message": f"Error: {str(e)}"
            }
    
    def report_health(self):
        """Report health metrics to the system dashboard"""
        logger.info("Health reporting thread started")
        
        while self.running:
            try:
                # Calculate derived metrics
                current_time = time.time()
                total = self.stats["requests"]
                
                # Calculate success rate
                success_rate = (self.stats["successful"] / total * 100) if total > 0 else 0
                
                # Determine overall status
                status = "online"
                status_reason = "Operating normally"
                
                if total > 10:
                    if success_rate < 50:
                        status = "degraded"
                        status_reason = f"Low success rate: {success_rate:.1f}%"
                
                # Get model status
                primary_model_status = get_model_status("phi3")
                fallback_model_status = get_model_status("tinyllama")
                
                # Create health data
                health_data = {
                    "status": status,
                    "status_reason": status_reason,
                    "timestamp": current_time,
                    "component": "llm_translation_adapter",
                    "metrics": {
                        "success_rate": success_rate,
                        "total_requests": total,
                        "successful": self.stats["successful"],
                        "failures": self.stats["failures"],
                        "fallbacks_used": self.stats["fallbacks_used"],
                        "avg_latency": self.stats["avg_latency"],
                        "last_error": self.stats["last_error"]
                    },
                    "models": {
                        "primary": primary_model_status,
                        "fallback": fallback_model_status
                    }
                }
                
                # Send health data
                try:
                    self.health_socket.send_string(f"health {json.dumps(health_data)}")
                    logger.debug(f"Sent health metrics to dashboard")
                except Exception as e:
                    logger.warning(f"Failed to send health metrics: {e}")
            
            except Exception as e:
                logger.error(f"Error in health reporting: {e}")
            
            # Report every 5 seconds
            time.sleep(5)
    
    def run(self):
        """Run the adapter, listening for translation requests"""
        logger.info("Starting LLM Translation Adapter")
        
        while self.running:
            try:
                # Wait for a request
                request = self.socket.recv_json()
                logger.debug(f"Received request: {request}")
                
                # Extract request data
                text = request.get("text", "")
                source_lang = request.get("source_lang", "tl")
                target_lang = request.get("target_lang", "en")
                action = request.get("action", "translate")
                
                # Handle 'none' action - just pass through without translation
                if action == "none":
                    logger.info(f"Received 'none' action request - no translation needed")
                    self.socket.send_json({
                        "original": text,
                        "translated": text,  # Return original text unchanged
                        "source": "direct_passthrough",
                        "success": True,
                        "status": "success",
                        "message": "No translation requested (action: none)"
                    })
                    continue
                
                # Translate the text
                result = self.translate(text, source_lang, target_lang)
                
                # Make sure response has both success and status fields
                if "status" not in result and "success" in result:
                    result["status"] = "success" if result["success"] else "error"
                if "success" not in result and "status" in result:
                    result["success"] = result["status"] == "success"
                
                # Send the response
                self.socket.send_json(result)
                
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                # Try to send error response
                try:
                    self.socket.send_json({
                        "original": request.get("text", ""),
                        "translated": request.get("text", ""),
                        "source": "error_fallback",
                        "model": "none",
                        "success": False,
                        "status": "error",
                        "message": f"Server error: {str(e)}"
                    })
                except:
                    pass

if __name__ == "__main__":
    import argparse

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LLM Translation Adapter")
    parser.add_argument("--model", type=str, default="phi3", help="Model to use for translation (default: phi3)")
    parser.add_argument("--port", type=int, default=ZMQ_PORT, help=f"Port to bind to (default: {ZMQ_PORT})")
    parser.add_argument("--host", type=str, help="Remote host IP to connect to (optional)")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    print(f"=== LLM Translation Adapter ===")
    print(f"Using model: {args.model}")
    print(f"Binding to port: {args.port}")
    
    if args.host:
        print(f"Remote host: {args.host}")
    
    # Start the adapter
    adapter = LLMTranslationAdapter(model=args.model, port=args.port, host=args.host)
    adapter.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise