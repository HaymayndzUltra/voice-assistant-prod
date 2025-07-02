from main_pc_code.src.core.base_agent import BaseAgent
# Bark TTS Agent - Enhanced version with GPU optimizations
# Usage: python agents/bark_tts.py "Your text here." [voice_preset]

import sys
import os
import time
import logging
import torch
import numpy as np
import sounddevice as sd
import threading
import zmq
import json
import re
from pathlib import Path
from bark import SAMPLE_RATE, generate_audio, preload_models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BarkTTSAgent")

# ZMQ port for communication
ZMQ_PORT = 5562  # Changed from 5561 to avoid conflict

# Voice presets
VOICE_PRESETS = {
    # English voices
    "en_male": "v2/en_speaker_6",
    "en_female": "v2/en_speaker_9",
    "en_neutral": "v2/en_speaker_0",
    "en_announcer": "v2/en_speaker_1",
    "en_british": "v2/en_speaker_2",
    "en_australian": "v2/en_speaker_3",
    "en_radio": "v2/en_speaker_4",
    "en_deep": "v2/en_speaker_5",
    "en_soft": "v2/en_speaker_7",
    "en_narrator": "v2/en_speaker_8",
    
    # Tagalog/Filipino voices (using standard English voices)
    "tl_male": "v2/en_speaker_6",  # Filipino male voice
    "tl_female": "v2/en_speaker_9",  # Filipino female voice
    "tl_neutral": "v2/en_speaker_0",  # Filipino neutral voice
    "tl_announcer": "v2/en_speaker_1",  # Filipino announcer voice
    "tl_soft": "v2/en_speaker_7",  # Filipino soft voice
    
    # Emotion-based voices
    "happy": "v2/en_speaker_9",
    "sad": "v2/en_speaker_7",
    "angry": "v2/en_speaker_5",
    "surprised": "v2/en_speaker_8",
    "neutral": "v2/en_speaker_0",
    
    # Default voice
    "default": "v2/en_speaker_6"
}

# Cache directory for generated audio
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tts_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class BarkTTSAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="BarkTts")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.is_running = False
        self.current_voice = VOICE_PRESETS["default"]
        self.use_gpu = torch.cuda.is_available()
        self.use_small_models = False  # Set to True for faster generation but lower quality
        self.cache_enabled = True
        
        # Initialize ZMQ socket for communication
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{ZMQ_PORT}")
        
        # Socket to handle health check requests from dashboard
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            # Use a different port (5563) for health checks to avoid conflict with main socket (5562)
            health_port = 5563  # Different port for health checks
            self.health_socket.bind(f"tcp://127.0.0.1:{health_port}")
            logger.info(f"[BarkTTS] Health check socket bound to port {health_port}")
            self.health_port = health_port
        except zmq.error.ZMQError as e:
            logger.error(f"[BarkTTS] Error binding health check socket to port {health_port}: {e}")
            self.health_port = None
            # Don't raise an exception here, just log the error and continue
        
        logger.info(f"[BarkTTS] Initialized with device: {self.device}")
        logger.info(f"[BarkTTS] CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"[BarkTTS] GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"[BarkTTS] CUDA version: {torch.version.cuda}")
        
        # Preload models in a separate thread to avoid blocking
        self.preload_thread = threading.Thread(target=self.preload_models_thread)
        self.preload_thread.daemon = True
        self.preload_thread.start()
    
    def preload_models_thread(self):
        logger.info("[BarkTTS] Preloading models in background...")
        try:
            preload_models(self.use_small_models)
            logger.info("[BarkTTS] Models preloaded successfully")
        except Exception as e:
            logger.error(f"[BarkTTS] Error preloading models: {e}")
    
    
    def detect_language(self, text):
        """
        Detect if text is primarily Tagalog/Filipino or English
        Uses simple heuristics based on common Filipino words
        """
        # Common Filipino words and patterns
        filipino_patterns = [
            r'\b(ang|mga|na|sa|ng|ay|ko|mo|niya|ito|iyon|tayo|kami|kayo|sila)\b',
            r'\b(ako|ikaw|siya|atin|natin|namin|ninyo|nila)\b',
            r'\b(maganda|mabuti|masaya|malungkot|galit|takot|mahal|gusto|ayaw)\b',
            r'\b(kumain|uminom|matulog|gumawa|bumili|magsalita|makinig|tumingin)\b',
            r'\b(salamat|kamusta|oo|hindi|paumanhin|tulungan|pakiusap|po|ho)\b'
        ]
        
        # Count matches for Filipino patterns
        filipino_count = 0
        for pattern in filipino_patterns:
            filipino_count += len(re.findall(pattern, text.lower()))
        
        # Simple heuristic: if we find more than 2 Filipino words, consider it Tagalog
        return "tl" if filipino_count > 2 else "en"
    def get_voice_preset(self, voice_name):
        """Get the voice preset from the name"""
        return VOICE_PRESETS.get(voice_name.lower(), VOICE_PRESETS["default"])
    
    def get_cache_path(self, text, voice_preset):
        """Generate a cache path for the given text and voice preset"""
        import hashlib

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        # Create a hash of the text and voice preset to use as the filename
        text_hash = hashlib.md5(f"{text}_{voice_preset}".encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{text_hash}.npy")
    
    def save_to_cache(self, audio_array, cache_path):
        """Save the audio array to cache"""
        try:
            np.save(cache_path, audio_array)
            logger.info(f"[BarkTTS] Cached audio to {cache_path}")
            return True
        except Exception as e:
            logger.error(f"[BarkTTS] Error caching audio: {e}")
            return False
    
    def load_from_cache(self, cache_path):
        """Load audio array from cache"""
        try:
            if os.path.exists(cache_path):
                audio_array = np.load(cache_path)
                logger.info(f"[BarkTTS] Loaded audio from cache: {cache_path}")
                return audio_array
        except Exception as e:
            logger.error(f"[BarkTTS] Error loading from cache: {e}")
        return None
    
    def speak(self, text, voice_preset=None):
        """Generate and play audio for the given text"""
        try:
            # Auto-detect language if no voice preset is provided
            if not voice_preset:
                detected_language = self.detect_language(text)
                if detected_language == "tl":
                    # Use Tagalog voice
                    voice_preset = "tl_male"  # Default Tagalog male voice
                    logger.info(f"[BarkTTS] Detected Tagalog text, using {voice_preset} voice")
                else:
                    # Use English voice
                    voice_preset = "en_male"  # Default English male voice
                    logger.info(f"[BarkTTS] Detected English text, using {voice_preset} voice")
            if not text:
                logger.warning("[BarkTTS] Empty text provided, nothing to speak")
                return False
        except Exception as e:
            logger.error(f"[BarkTTS] Error in language detection: {str(e)}")
            # Use default voice if language detection fails
            voice_preset = "en_male"
            logger.info(f"[BarkTTS] Using default voice: {voice_preset}")
            if not text:
                logger.warning("[BarkTTS] Empty text provided, nothing to speak")
                return False
            
        # Truncate very long text
        if len(text) > 500:
            logger.warning(f"[BarkTTS] Text too long ({len(text)} chars), truncating to 500 chars")
            text = text[:497] + "..."
        
        # Use the provided voice preset or the current default
        voice = voice_preset if voice_preset else self.current_voice
        
        # Check cache first if enabled
        cache_path = None
        if self.cache_enabled:
            cache_path = self.get_cache_path(text, voice)
            cached_audio = self.load_from_cache(cache_path)
            if cached_audio is not None:
                self.play_audio(cached_audio)
                return True
        
        # Generate audio if not in cache
        try:
            start_time = time.time()
            logger.info(f"[BarkTTS] Generating audio for: {text[:50]}{'...' if len(text) > 50 else ''}")
            logger.info(f"[BarkTTS] Using voice preset: {voice}")
            
            # Check if voice preset exists
            if voice not in VOICE_PRESETS:
                logger.warning(f"[BarkTTS] Voice preset '{voice}' not found, using default")
                voice = "default"
            
            # Set the device for generation
            with torch.device(self.device):
                # Generate the audio
                try:
                    audio_array = generate_audio(text, history_prompt=VOICE_PRESETS[voice])
                    
                    generation_time = time.time() - start_time
                    logger.info(f"[BarkTTS] Audio generated in {generation_time:.2f} seconds")
                    
                    # Cache the generated audio if enabled
                    if self.cache_enabled and cache_path:
                        self.save_to_cache(audio_array, cache_path)
                    
                    # Play the audio
                    self.play_audio(audio_array)
                    return True
                except Exception as gen_error:
                    logger.error(f"[BarkTTS] Error generating audio: {str(gen_error)}")
                    # Try with default voice as fallback
                    try:
                        logger.info("[BarkTTS] Trying with default voice as fallback")
                        audio_array = generate_audio(text, history_prompt=VOICE_PRESETS["default"])
                        self.play_audio(audio_array)
                        return True
                    except Exception as fallback_error:
                        logger.error(f"[BarkTTS] Fallback also failed: {str(fallback_error)}")
                        return False
            
        except Exception as e:
            logger.error(f"[BarkTTS] Error generating audio: {e}")
            return False
    
    def play_audio(self, audio_array):
        """Play the audio array"""
        try:
            sd.play(audio_array, samplerate=SAMPLE_RATE)
            sd.wait()
            logger.info("[BarkTTS] Playback finished")
            return True
        except Exception as e:
            logger.error(f"[BarkTTS] Error playing audio: {e}")
            return False
    
    def set_voice(self, voice_name):
        """Set the current voice preset"""
        if voice_name.lower() in VOICE_PRESETS:
            self.current_voice = VOICE_PRESETS[voice_name.lower()]
            logger.info(f"[BarkTTS] Voice set to {voice_name} ({self.current_voice})")
            return True
        else:
            logger.warning(f"[BarkTTS] Voice '{voice_name}' not found, using default")
            self.current_voice = VOICE_PRESETS["default"]
            return False
    
    def list_voices(self):
        """Return a list of available voice presets"""
        return list(VOICE_PRESETS.keys())
        
    def handle_health_check(self):
        """Handle health check requests from the dashboard"""
        # Skip if health socket wasn't initialized successfully
        if not hasattr(self, 'health_port') or self.health_port is None:
            return False
            
        try:
            # Check if there's a health check request with a short timeout
            if self.health_socket.poll(timeout=10) == 0:  # 10ms timeout
                return False  # No request
            
            # Receive the request
            request_str = self.health_socket.recv_string(flags=zmq.NOBLOCK)
            try:
                request = json.loads(request_str)
            except json.JSONDecodeError:
                logger.warning("[BarkTTS] Invalid JSON in health check request")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Invalid JSON"}))
                return True
            
            # Check if it's a health check request
            if request.get("request_type") == "health_check":
                logger.debug("[BarkTTS] Received health check request")
                # Send success response
                response = {
                    "status": "success",
                    "agent": "tts",
                    "timestamp": time.time()
                }
                self.health_socket.send_string(json.dumps(response))
                return True
            else:
                # Unknown request type
                logger.warning(f"[BarkTTS] Unknown request type: {request.get('request_type')}")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Unknown request type"}))
                return True
                
        except zmq.Again:
            # No message available
            return False
        except Exception as e:
            logger.error(f"[BarkTTS] Error handling health check: {str(e)}")
            try:
                self.health_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
            except Exception:
            return True
            
    except zmq.Again:
        # No message available
        return False
    except Exception as e:
        logger.error(f"[BarkTTS] Error handling health check: {str(e)}")
        try:
            self.health_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
        except Exception:
            pass  # Ignore errors in sending error response
        return True

def run(self):
    """Run the TTS agent and listen for commands"""
    logger.info(f"[BarkTTS] Agent started on port {ZMQ_PORT}")
    
    # Start health check thread
    if self.health_port:
        health_thread = threading.Thread(target=self.handle_health_check, daemon=True)
        health_thread.start()
    
    try:
        while self.is_running:
            try:
                # Use a shorter timeout to be more responsive
                message = self.socket.recv_string(flags=zmq.NOBLOCK)
                
                try:
                    data = json.loads(message)
                    command = data.get("command", "")
                    
                    if command == "speak":
                        text = data.get("text", "")
                        voice = data.get("voice", "default")
                        
                        # Send immediate acknowledgment to prevent timeout
                        self.socket.send_json({"status": "processing"})
                        
                        # Process the speech in a separate thread to avoid blocking
                        def speak_thread(text, voice):
                            try:
                                self.speak(text, voice)
                                logger.info(f"[BarkTTS] Successfully processed: '{text[:30]}...'")
                            except Exception as e:
                                logger.error(f"[BarkTTS] Error in speak thread: {e}")
                        
                        thread = threading.Thread(target=speak_thread, args=(text, voice))
                        thread.daemon = True
                        thread.start()
                        
                    elif command == "set_voice":
                        voice = data.get("voice", "default")
                        success = self.set_voice(voice)
                        elif command == "list_voices":
                            voices = self.list_voices()
                            self.socket.send_json({"status": "ok", "voices": voices})
                            
                        elif command == "stop":
                            self.is_running = False
                            self.socket.send_json({"status": "ok"})
                            
                        else:
                            logger.warning(f"[BarkTTS] Unknown command: {command}")
                            self.socket.send_json({"status": "error", "message": "Unknown command"})
                            
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text to speak
                        success = self.speak(message)
                        self.socket.send_json({"status": "ok" if success else "error"})
                        
                except zmq.Again:
                    # No message available, sleep a bit
                    time.sleep(0.01)
                    continue
                    
        except KeyboardInterrupt:
            logger.info("[BarkTTS] Interrupted by user")
        finally:
            self.socket.close()
            if hasattr(self, 'health_socket'):
                self.health_socket.close()
            self.context.term()
            logger.info("[BarkTTS] Agent stopped")

# Direct usage from command line
def cli_speak(text, voice_preset=None):
    """Command-line interface for speaking text"""
    agent = BarkTTSAgent()
    if voice_preset:
        agent.set_voice(voice_preset)
    return agent.speak(text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
        voice = sys.argv[2] if len(sys.argv) > 2 else None
        cli_speak(text, voice)
    else:
        # Run the agent in server mode
        agent = BarkTTSAgent()
        agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise