from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Improved Bark TTS Agent with better ZMQ responsiveness
Designed to handle requests more efficiently and prevent timeouts
"""
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


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [BarkTTS] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BarkTTSAgent")

# ZMQ port for communication
ZMQ_PORT = 5562  # Port for TTS commands
HEALTH_PORT = 5563  # Port for health checks

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
    
    # Default voice
    "default": "v2/en_speaker_6"
}

# Cache directory for generated audio
CACHE_DIR = Path(PathManager.join_path("cache", "tts_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class BarkTTSAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ImprovedBarkTts")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.is_running = True
        self.current_voice = VOICE_PRESETS["default"]
        self.use_gpu = torch.cuda.is_available()
        self.use_small_models = False
        self.cache_enabled = True
        
        # Initialize ZMQ socket for communication
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{ZMQ_PORT}")
        
        # Socket for health checks
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.health_socket.bind(f"tcp://127.0.0.1:{HEALTH_PORT}")
            logger.info(f"Health check socket bound to port {HEALTH_PORT}")
            self.health_port = HEALTH_PORT
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding health check socket: {e}")
            self.health_port = None
        
        # Log system info
        logger.info(f"Initialized with device: {self.device}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA version: {torch.version.cuda}")
        
        # Preload models in a separate thread
        self.preload_thread = threading.Thread(target=self.preload_models_thread)
        self.preload_thread.daemon = True
        self.preload_thread.start()
    
    def preload_models_thread(self):
        """Preload models in background thread"""
        logger.info("Preloading models in background...")
        try:
            preload_models()
            logger.info("Models preloaded successfully")
        except Exception as e:
            logger.error(f"Error preloading models: {e}")
    
    def detect_language(self, text):
        """Detect if text is primarily Tagalog/Filipino or English"""
        # Simple heuristic based on common Filipino words
        tagalog_words = [
            "ako", "ikaw", "siya", "kami", "tayo", "kayo", "sila",
            "ang", "ng", "sa", "na", "at", "ay", "mga", "po", "opo",
            "hindi", "oo", "salamat", "kamusta", "mahal", "maganda",
            "masarap", "mabuti", "masaya", "malungkot", "galit",
            "kumain", "uminom", "matulog", "gumawa", "pumunta",
            "magandang", "umaga", "hapon", "gabi", "araw"
        ]
        
        # Count Tagalog words
        words = re.findall(r'\b\w+\b', text.lower())
        tagalog_count = sum(1 for word in words if word in tagalog_words)
        tagalog_ratio = tagalog_count / len(words) if words else 0
        
        # Determine language
        if tagalog_ratio > 0.3:
            return "tagalog"
        else:
            return "english"
    
    def get_voice_preset(self, voice_name):
        """Get the voice preset from the name"""
        if not voice_name or voice_name == "default":
            return VOICE_PRESETS["default"]
        
        return VOICE_PRESETS.get(voice_name, VOICE_PRESETS["default"])
    
    def get_cache_path(self, text, voice_preset):
        """Generate a cache path for the given text and voice preset"""
        if not self.cache_enabled:
            return None
        
        # Create a hash of the text and voice preset
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        voice_hash = hashlib.md5(voice_preset.encode()).hexdigest()
        cache_path = CACHE_DIR / f"{text_hash}_{voice_hash}.npy"
        return cache_path
    
    def save_to_cache(self, audio_array, cache_path):
        """Save the audio array to cache"""
        if not self.cache_enabled or cache_path is None:
            return
        
        try:
            np.save(cache_path, audio_array)
            logger.debug(f"Saved audio to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
    
    def load_from_cache(self, cache_path):
        """Load audio array from cache"""
        if not self.cache_enabled or cache_path is None or not cache_path.exists():
            return None
        
        try:
            audio_array = np.load(cache_path)
            logger.debug(f"Loaded audio from cache: {cache_path}")
            return audio_array
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return None
    
    def speak(self, text, voice_preset=None):
        """Generate and play audio for the given text"""
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided, nothing to speak")
                return False
            
            # Determine voice preset
            if not voice_preset:
                # Auto-detect language and select appropriate voice
                language = self.detect_language(text)
                voice_preset = "en_male" if language == "english" else "tl_male"
            
            voice = self.get_voice_preset(voice_preset)
            logger.info(f"Speaking with voice: {voice_preset} ({voice})")
            
            # Check cache first
            cache_path = self.get_cache_path(text, voice)
            audio_array = self.load_from_cache(cache_path)
            
            # Generate audio if not in cache
            if audio_array is None:
                logger.info(f"Generating audio for: '{text[:50]}...'")
                try:
                    audio_array = generate_audio(text, history_prompt=voice)
                    self.save_to_cache(audio_array, cache_path)
                except Exception as e:
                    logger.error(f"Error generating audio with voice {voice_preset}: {e}")
                    # Try with default voice as fallback
                    try:
                        logger.info("Trying with default voice as fallback")
                        audio_array = generate_audio(text, history_prompt=VOICE_PRESETS["default"])
                    except Exception as e2:
                        logger.error(f"Error generating audio with default voice: {e2}")
                        return False
            
            # Log and filter the text before playback
            fallback_phrases = [
                "i didn't catch that",
                "could you please repeat",
                "i'm not sure i understand",
                "could you please rephra"
            ]
            if not text or not text.strip() or len(text.strip()) < 3:
                logger.warning(f"[TTS] Ignoring short/empty text: '{text}'")
                print(f"[DEBUG] Ignoring short/empty text: '{text}'")
                return False
            lower_text = text.strip().lower()
            if any(phrase in lower_text for phrase in fallback_phrases):
                logger.warning(f"[TTS] Ignoring fallback/system phrase: '{text}'")
                print(f"[DEBUG] Ignoring fallback/system phrase: '{text}'")
                return False
            logger.info(f"[TTS] Speaking text: '{text}'")
            print(f"[DEBUG] Speaking text: '{text}'")
            # Play the audio
            self.play_audio(audio_array)
            return True
            
        except Exception as e:
            logger.error(f"Error in speak method: {e}")
            return False
    
    def play_audio(self, audio_array):
        """Play the audio array"""
        import sounddevice as sd

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        try:
            print("[DEBUG] Listing available audio output devices:")
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                print(f"  {i}: {dev['name']} (max output channels: {dev['max_output_channels']})")
            # Set your preferred output device index here (SteelSeries Sonar - Microphone)
            # Find the correct index for 'SteelSeries Sonar - Microphone' with max_output_channels > 0
            preferred_output_device = None
            for i, dev in enumerate(devices):
                if 'SteelSeries Sonar - Microphone' in dev['name'] and dev['max_output_channels'] > 0:
                    preferred_output_device = i
                    break
            if preferred_output_device is None:
                print("[DEBUG] SteelSeries Sonar - Microphone with output channels not found. Using default device 5.")
                preferred_output_device = 5
            print(f"[DEBUG] Forcing playback to device index: {preferred_output_device} - {devices[preferred_output_device]['name']}")
            sd.play(audio_array, SAMPLE_RATE, device=preferred_output_device)
            sd.wait()
            print("[DEBUG] Playback finished.")
            return True
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            print(f"[DEBUG] Error playing audio: {e}")
            return False
    
    def set_voice(self, voice_name):
        """Set the current voice preset"""
        if voice_name in VOICE_PRESETS:
            self.current_voice = VOICE_PRESETS[voice_name]
            logger.info(f"Voice set to: {voice_name} ({self.current_voice})")
            return True
        else:
            logger.warning(f"Unknown voice preset: {voice_name}")
            return False
    
    def list_voices(self):
        """Return a list of available voice presets"""
        return list(VOICE_PRESETS.keys())
    
    def handle_health_check(self):
        """Handle health check requests from the dashboard"""
        if not self.health_port:
            return
        
        try:
            message = self.health_socket.recv_string(flags=zmq.NOBLOCK)
            try:
                request = json.loads(message)
                request_type = request.get("request_type", "")
                
                if request_type == "health_check":
                    logger.debug("Received health check request")
                    response = {
                        "status": "success",
                        "agent": "tts",
                        "timestamp": time.time()
                    }
                    self.health_socket.send_string(json.dumps(response))
                else:
                    logger.warning(f"Unknown request type: {request_type}")
                    self.health_socket.send_string(json.dumps({"status": "error", "message": "Unknown request type"}))
            except Exception as e:
                logger.error(f"Error handling health check: {e}")
                try:
                    self.health_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
        except zmq.Again:
            pass  # No message available
        except Exception as e:
            logger.error(f"Error in health check: {e}")
    
    def process_speak_command(self, text, voice):
        """Process speak command in a separate thread"""
        try:
            success = self.speak(text, voice)
            logger.info(f"Successfully processed: '{text[:30]}...'")
            return success
        except Exception as e:
            logger.error(f"Error in speak thread: {e}")
            return False
    
    def run(self):
        """Run the TTS agent and listen for commands"""
        logger.info(f"Agent started on port {ZMQ_PORT}")
        
        # Start health check thread
        if self.health_port:
            health_thread = threading.Thread(target=self.handle_health_check, daemon=True)
            health_thread.start()
        
        try:
            while self.is_running:
                # Handle health checks
                self.handle_health_check()
                
                try:
                    # Check for incoming messages with non-blocking
                    message = self.socket.recv_string(flags=zmq.NOBLOCK)
                    
                    try:
                        # Parse the message as JSON
                        data = json.loads(message)
                        command = data.get("command", "")
                        
                        if command == "speak":
                            text = data.get("text", "")
                            voice = data.get("voice", "default")
                            
                            # Send immediate acknowledgment
                            self.socket.send_json({"status": "ok"})
                            
                            # Process in separate thread
                            thread = threading.Thread(
                                target=self.process_speak_command, 
                                args=(text, voice)
                            )
                            thread.daemon = True
                            thread.start()
                            
                        elif command == "set_voice":
                            voice = data.get("voice", "default")
                            success = self.set_voice(voice)
                            self.socket.send_json({"status": "ok" if success else "error"})
                            
                        elif command == "list_voices":
                            voices = self.list_voices()
                            self.socket.send_json({"status": "ok", "voices": voices})
                            
                        elif command == "stop":
                            self.is_running = False
                            self.socket.send_json({"status": "ok"})
                            
                        else:
                            logger.warning(f"Unknown command: {command}")
                            self.socket.send_json({"status": "error", "message": "Unknown command"})
                            
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text to speak
                        self.socket.send_json({"status": "ok"})
                        thread = threading.Thread(
                            target=self.process_speak_command, 
                            args=(message, None)
                        )
                        thread.daemon = True
                        thread.start()
                        
                except zmq.Again:
                    # No message available, sleep a bit
                    time.sleep(0.01)
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.socket.close()
            if hasattr(self, 'health_socket'):
                self.health_socket.close()
            self.context.term()
            logger.info("Agent stopped")

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
        # Run as server
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