from src.core.base_agent import BaseAgent
import sys
import os
# Auto-accept Coqui CPML terms for non-commercial use.
# Set the env var only if user hasn't explicitly provided one.
os.environ.setdefault("COQUI_TOS_AGREED", "1")
import zmq
import json
# import os
import sounddevice as sd
import numpy as np
import threading
import queue
from TTS.api import TTS
import torch
import logging
import time
import pickle
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Import common Tagalog phrases module
try:
    from agents.common_tagalog_phrases import (
        translate_common_phrase,
        check_and_replace_common_phrases,
        TAGALOG_TO_ENGLISH,
        ENGLISH_TO_TAGALOG
    )
    COMMON_PHRASES_AVAILABLE = True
    logging.info("[Responder] Common Tagalog phrases module loaded successfully")
except ImportError:
    COMMON_PHRASES_AVAILABLE = False
    logging.warning("[Responder] Common Tagalog phrases module not available")


def add_all_safe_globals():
    # List of known required safe globals for XTTS
    safe_globals = [
        ('TTS.tts.configs.xtts_config', 'XttsConfig'),
        ('TTS.tts.models.xtts', 'XttsAudioConfig'),
        ('TTS.config.shared_configs', 'BaseDatasetConfig'),
        ('TTS.tts.models.xtts', 'XttsArgs'),
    ]
    for module, name in safe_globals:
        try:
            torch.serialization.add_safe_globals([
                __import__(module, fromlist=[name]).__dict__[name]
            ])
            logging.info(f"[Responder] Added safe global: {module}.{name}")
        except Exception as e:
            logging.warning(
                f"[Responder] Could not add safe global {module}.{name}: {e}")


add_all_safe_globals()

# Lazy-load TTS at runtime to avoid blocking import time
try:
    from TTS.api import TTS  # only import, do not instantiate
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


            

        
            

    


# Settings
ZMQ_RESPONDER_PORT = 5637  # Updated to match config
ZMQ_FACE_PORT = 5556  # Port for face recognition agent
ZMQ_TTS_PORT = 5562  # Port for StreamingTTSAgent
ZMQ_TTS_CACHE_PORT = 5628  # Port for TTSCache
ZMQ_TTS_CONNECTOR_PORT = 5582  # Port for TTSConnector

# Health monitoring settings
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

# Language-specific voice configurations
LANGUAGE_VOICES = {
    "en": "en",       # Default English voice
    "tl": "tl",       # Tagalog voice
    "mixed": "tl",    # For mixed language (Taglish), prefer Tagalog voice
    "unknown": "en"   # Default to English for unknown
}

# Use pre-translated responses for common phrases
USE_PRETRANSLATED_PHRASES = True

# Emotion to voice parameter mapping with enhanced expressiveness
EMOTION_VOICE_PARAMS = {
    # Basic emotions with enhanced parameters
    "joy": {"speed": 1.15, "pitch": 1.15, "energy": 1.2, "vibrato": 0.1, "breathiness": 0.1, "color": "#FFD700"},
    "sadness": {"speed": 0.85, "pitch": 0.9, "energy": 0.8, "vibrato": 0.0, "breathiness": 0.3, "color": "#4682B4"},
    "anger": {"speed": 1.2, "pitch": 0.85, "energy": 1.3, "vibrato": 0.2, "breathiness": 0.0, "color": "#FF4500"},
    "fear": {"speed": 1.15, "pitch": 1.1, "energy": 0.9, "vibrato": 0.3, "breathiness": 0.2, "color": "#800080"},
    "surprise": {"speed": 1.25, "pitch": 1.2, "energy": 1.2, "vibrato": 0.1, "breathiness": 0.1, "color": "#FF69B4"},
    "neutral": {"speed": 1.0, "pitch": 1.0, "energy": 1.0, "vibrato": 0.0, "breathiness": 0.0, "color": "#FFFFFF"},
    "disgust": {"speed": 1.05, "pitch": 0.9, "energy": 1.1, "vibrato": 0.1, "breathiness": 0.0, "color": "#556B2F"},
    
    # Nuanced emotions
    "excitement": {"speed": 1.3, "pitch": 1.25, "energy": 1.3, "vibrato": 0.2, "breathiness": 0.1, "color": "#FFA500"},
    "contentment": {"speed": 0.95, "pitch": 1.05, "energy": 0.95, "vibrato": 0.0, "breathiness": 0.1, "color": "#98FB98"},
    "amusement": {"speed": 1.1, "pitch": 1.15, "energy": 1.1, "vibrato": 0.1, "breathiness": 0.0, "color": "#FFFF00"},
    "pride": {"speed": 1.05, "pitch": 1.1, "energy": 1.15, "vibrato": 0.0, "breathiness": 0.0, "color": "#B8860B"},
    "embarrassment": {"speed": 1.0, "pitch": 0.95, "energy": 0.85, "vibrato": 0.1, "breathiness": 0.2, "color": "#FF6347"},
    "guilt": {"speed": 0.9, "pitch": 0.9, "energy": 0.8, "vibrato": 0.0, "breathiness": 0.2, "color": "#2F4F4F"},
    "shame": {"speed": 0.85, "pitch": 0.85, "energy": 0.75, "vibrato": 0.0, "breathiness": 0.3, "color": "#8B4513"},
    
    # General sentiment categories
    "positive": {"speed": 1.1, "pitch": 1.1, "energy": 1.15, "vibrato": 0.05, "breathiness": 0.05, "color": "#7CFC00"},
    "negative": {"speed": 0.9, "pitch": 0.9, "energy": 0.85, "vibrato": 0.05, "breathiness": 0.15, "color": "#DC143C"},
    "calm": {"speed": 0.85, "pitch": 1.0, "energy": 0.9, "vibrato": 0.0, "breathiness": 0.1, "color": "#87CEEB"},
    "energetic": {"speed": 1.2, "pitch": 1.15, "energy": 1.25, "vibrato": 0.1, "breathiness": 0.0, "color": "#FF8C00"},
    "serious": {"speed": 0.95, "pitch": 0.95, "energy": 1.0, "vibrato": 0.0, "breathiness": 0.0, "color": "#708090"},
    "playful": {"speed": 1.15, "pitch": 1.2, "energy": 1.1, "vibrato": 0.1, "breathiness": 0.05, "color": "#FF69B4"},
}

# Visual feedback settings
VISUAL_FEEDBACK_ENABLED = False  # Set to True to enable visual feedback
VISUAL_FEEDBACK_DURATION = 3.0  # How long to show visual feedback in seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


class ResponderAgent(BaseAgent):
    def __init__(self, port: int = ZMQ_RESPONDER_PORT, voice: str = VOICE, **kwargs):
        super().__init__(port=port, name="Responder")
        self.context = zmq.Context()
        
        # Set up main socket for receiving TTS requests
        self.socket = self.context.socket(zmq.SUB)
        self.socket.bind(f"tcp://127.0.0.1:{port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Set up face recognition socket for emotion data
        self.face_socket = self.context.socket(zmq.SUB)
        self.face_socket.connect(f"tcp://127.0.0.1:{ZMQ_FACE_PORT}")
        self.face_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Set up TTS service connections
        self.tts_socket = self.context.socket(zmq.REQ)
        self.tts_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.connect(f"tcp://127.0.0.1:{ZMQ_TTS_PORT}")
        
        self.tts_cache_socket = self.context.socket(zmq.REQ)
        self.tts_cache_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_cache_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_cache_socket.connect(f"tcp://127.0.0.1:{ZMQ_TTS_CACHE_PORT}")
        
        self.tts_connector_socket = self.context.socket(zmq.REQ)
        self.tts_connector_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_connector_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_connector_socket.connect(f"tcp://127.0.0.1:{ZMQ_TTS_CONNECTOR_PORT}")
        
        # Health monitoring
        self.health_status = {
            "status": "ok",
            "service": "responder",
            "last_check": time.time(),
            "connections": {
                "tts": False,
                "tts_cache": False,
                "tts_connector": False,
                "face_recognition": False
            }
        }
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.health_thread.start()
        
        # Defer heavy TTS model loading to a background thread
        self.tts = None
        self.tts_ready = threading.Event()
        threading.Thread(target=self._load_tts_model, daemon=True).start()
        self.voice = voice
        
        # Queue for audio processing
        self.audio_queue = queue.Queue()
        self.running = True
        
        # State tracking
        self.last_text = None
        self.last_emotion = None
        self.last_language = None
        self.last_user = None
        self.history = []
        
        # Face data tracking
        self.detected_faces = {}  # Format: {name: {emotion, last_seen, confidence}}
        self.current_speaker = None
        
        # User voice profiles - can be customized per user
        self.user_voice_profiles = {}
        
        logging.info(f"[Responder] Ready on port {port}.")

    def _load_tts_model(self):
        """Background loader for XTTS model."""
        if not TTS_AVAILABLE:
            logging.info("[Responder] TTS library not available; speech synthesis disabled.")
            self.tts_ready.set()
            return
        try:
            self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            logging.info("[Responder] XTTS model loaded successfully.")
        except Exception as e:
            logging.error(f"[Responder] Failed to load XTTS model: {e}")
        finally:
            self.tts_ready.set()
        
    def face_recognition_listener(self):
        """Background thread to listen for face recognition events"""
        logging.info("[Responder] Face recognition listener started")
        while self.running:
            try:
                msg = self.face_socket.recv_string(flags=zmq.NOBLOCK)
                data = json.loads(msg)
                
                # Handle different event types from face recognition agent
                event_type = data.get("event")
                
                if event_type == "face_detected":
                    name = data.get("name")
                    timestamp = data.get("timestamp")
                    emotion = data.get("emotion", "neutral")
                    confidence = data.get("confidence", 0.0)
                    
                    # Update detected faces
                    self.detected_faces[name] = {
                        "last_seen": timestamp,
                        "emotion": emotion,
                        "confidence": confidence
                    }
                    
                    # If high confidence, set as current speaker
                    if confidence > 0.8 and name != "Unknown":
                        self.current_speaker = name
                    
                    logging.info(f"[Responder] Face detected: {name} with emotion {emotion}")
                    
            except zmq.Again:
                # No message available, continue
                pass
            except Exception as e:
                logging.error(f"[Responder] Error in face recognition listener: {e}")
            
            time.sleep(0.1)  # Small sleep to prevent CPU hogging

    def process_message(self):
        """Process incoming messages with enhanced language handling"""
        try:
            message = self.socket.recv_string(flags=zmq.NOBLOCK)
            data = json.loads(message)

            # Extract message data
            text = data.get("text", "")
            emotion = data.get("emotion")
            language = data.get("language")
            user = data.get("user")
            original_language = data.get("original_language")  # Original language of user input
            original_text = data.get("original_text", "")    # Original text before translation
            
            # Process the message with enhanced language awareness
            self.speak(
                text, 
                emotion=emotion, 
                language=language, 
                user=user, 
                original_language=original_language
            )
            
            # Update health status
            self.last_health_check = time.time()
            self.health_status = "OK"
                
            return True
            
        except zmq.Again:
            # No message available
            return False
        except json.JSONDecodeError:
            logging.error("[Responder] Invalid JSON received")
            self.health_status = "ERROR: Invalid JSON"
            return False
        except Exception as e:
            logging.error(f"[Responder] Error processing message: {e}")
            self.health_status = f"ERROR: {str(e)}"
            return False

    def speak(self, text, emotion=None, language=None, user=None, face_emotion=None, original_language=None):
        """
        Enhanced speak method with improved emotion handling, user personalization,
        visual feedback support, and language-specific voice selection.
        """
        logging.info(f"[Responder] Speaking to {user or 'unknown user'}: {text} (Text emotion: {emotion}, Face emotion: {face_emotion}, Language: {language}, Original language: {original_language})")
        
        try:
            # Default parameters
            speed = 1.0
            pitch = 1.0
            energy = 1.0
            vibrato = 0.0
            breathiness = 0.0
            color = "#FFFFFF"  # Default color for visual feedback
            
            # Determine primary emotion to use (prioritize face emotion if available)
            primary_emotion = face_emotion if face_emotion and face_emotion != "neutral" else emotion
            if primary_emotion:
                # Clean up emotion string to extract the base emotion
                # Handle formats like "joy (0.85)" or "text: joy, face: neutral"
                base_emotion = primary_emotion.lower()
                for emotion_key in EMOTION_VOICE_PARAMS.keys():
                    if emotion_key in base_emotion:
                        params = EMOTION_VOICE_PARAMS[emotion_key]
                        speed = params["speed"]
                        pitch = params["pitch"]
                        energy = params["energy"]
                        vibrato = params.get("vibrato", 0.0)
                        breathiness = params.get("breathiness", 0.0)
                        color = params.get("color", "#FFFFFF")
                        logging.debug(f"[Responder] Using voice parameters for emotion '{emotion_key}': {params}")
                        break
            
            # Apply user-specific voice profile if available
            if user and user in self.user_voice_profiles:
                user_profile = self.user_voice_profiles[user]
                # Adjust parameters based on user preferences
                speed *= user_profile.get("speed_modifier", 1.0)
                pitch *= user_profile.get("pitch_modifier", 1.0)
                energy *= user_profile.get("energy_modifier", 1.0)
                vibrato *= user_profile.get("vibrato_modifier", 1.0)
                breathiness *= user_profile.get("breathiness_modifier", 1.0)
                
                # Use custom voice if specified
                custom_voice = user_profile.get("voice")
                if custom_voice:
                    language = custom_voice
            
            # Select appropriate voice based on original language if not specified
            if not language and original_language:
                language = LANGUAGE_VOICES.get(original_language, self.voice)
                logging.debug(f"[Responder] Selected {language} voice based on original language {original_language}")
            
            # Show visual feedback if enabled
            if VISUAL_FEEDBACK_ENABLED:
                self._show_visual_feedback(text, color, VISUAL_FEEDBACK_DURATION)
            
            # Generate speech with XTTS – ensure model is ready
            if not getattr(self, "tts_ready", threading.Event()).is_set() or self.tts is None:
                logging.warning("[Responder] TTS engine not ready; skipping audio generation.")
                return
            wav = self.tts.tts(
                text=text,
                speaker_wav=None,  # Could use user-specific reference audio in the future
                language=language or self.voice)
            
            # Post-process: modify speed, pitch, energy, vibrato, and breathiness
            wav_mod = self._modulate_audio(
                wav, 
                speed=speed, 
                pitch=pitch, 
                energy=energy,
                vibrato=vibrato,
                breathiness=breathiness
            )
            
            # Play the audio
            sd.play(wav_mod, samplerate=24000)
            sd.wait()
            
            # Record this interaction
            self.last_text = text
            self.last_emotion = emotion
            self.last_language = language
            self.last_user = user
            
        except Exception as e:
            logging.error(f"[Responder] TTS error: {e} -- Falling back to Coqui TTS.")
            try:
                from agents.coqui_fallback import coqui_speak
                coqui_success = coqui_speak(text, language=language or self.voice)
                if not coqui_success:
                    logging.error("[Responder] Coqui TTS fallback also failed.")
            except Exception as e2:
                logging.error(f"[Responder] Coqui TTS fallback import/use error: {e2}")
                
    def _show_visual_feedback(self, text, color, duration):
        """
        Display visual feedback for the spoken text using a transient Tk window.
        Falls back gracefully if tkinter is not available or a display is not
        present (e.g. running headless).
        """
        if not VISUAL_FEEDBACK_ENABLED:
            return
        try:
            import tkinter as tk
            import threading

            def show_overlay():
                root = tk.Tk()
                root.overrideredirect(True)
                root.attributes("-topmost", True)
                root.attributes("-alpha", 0.8)
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                window_width = min(screen_width - 100, len(text) * 10 + 100)
                window_height = 100
                x = (screen_width - window_width) // 2
                y = screen_height - window_height - 50
                root.geometry(f"{window_width}x{window_height}+{x}+{y}")

                frame = tk.Frame(root, bg=color)
                frame.pack(fill=tk.BOTH, expand=True)
                label = tk.Label(
                    frame,
                    text=text,
                    font=("Arial", 14),
                    bg=color,
                    fg="#000000" if self._is_light_color(color) else "#FFFFFF",
                    wraplength=window_width - 20,
                )
                label.pack(pady=20)
                root.after(int(duration * 1000), root.destroy)
                root.mainloop()

            threading.Thread(target=show_overlay, daemon=True).start()
        except Exception as e:
            logging.error(f"[Responder] Visual feedback error: {e}")

    def _is_light_color(self, hex_color):
        """Return True if the supplied hex color is considered light."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        brightness = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        return brightness > 0.5

    def _modulate_audio(
        self,
        audio,
        speed: float = 1.0,
        pitch: float = 1.0,
        energy: float = 1.0,
        vibrato: float = 0.0,
        breathiness: float = 0.0,
    ):
        """Simple audio post-processing placeholder.

        For now only applies a volume (energy) adjustment and clips the output.
        """
        # TODO: re-implement full DSP chain (speed, pitch, etc.) if necessary.
        audio = audio * energy
        return np.clip(audio, -1.0, 1.0)

    # --------------------------------------------------------------------- #
    #                        PUBLIC AGENT INTERFACE                         #
    # --------------------------------------------------------------------- #
    def generate_response(self, text, user=None, language=None, original_language=None):
        """Generate a textual response. Currently echoes the input."""
        return f"I received your message: {text}"

    def start(self):
        """Start the agent's main loop."""
        logging.info("[Responder] Agent started.")
        self.running = True
        try:
            while self.running:
                self.process_message()
                # Simple heartbeat and cleanup
                if time.time() - self.last_health_check > 60:
                    self.health_check()
                self.cleanup_old_face_data()
                time.sleep(0.05)
        except KeyboardInterrupt:
            logging.info("[Responder] KeyboardInterrupt received. Stopping...")
        finally:
            self.stop()

    def cleanup_old_face_data(self):
        now = time.time()
        expired = [
            name for name, info in self.detected_faces.items()
            if now - info.get("last_seen", 0) > 300
        ]
        for name in expired:
            self.detected_faces.pop(name, None)
        if expired:
            logging.info(f"[Responder] Cleaned up {len(expired)} expired face entries")

    def add_user_voice_profile(self, user, profile_data):
        if not user:
            logging.warning("[Responder] Cannot add voice profile without user name")
            return False
        profile = {
            "speed_modifier": 1.0,
            "pitch_modifier": 1.0,
            "energy_modifier": 1.0,
            "vibrato_modifier": 1.0,
            "breathiness_modifier": 1.0,
            "voice": None,
        }
        profile.update(profile_data or {})
        self.user_voice_profiles[user] = profile
        logging.info(f"[Responder] Updated voice profile for user {user}: {profile}")
        return True

    def stop(self):
        if not self.running:
            return
        self.running = False
        try:
            self.socket.close(0)
            self.context.term()
        finally:
            logging.info("[Responder] Stopped and cleaned up.")

    def hot_reload_watcher(self):
        last_voice = self.voice
        while self.running:
            time.sleep(5)
            try:
                if self.voice != last_voice:
                    logging.info("[Responder] Voice hot reloaded.")
                    last_voice = self.voice
            except Exception as e:
                logging.error(f"[Responder] Hot reload watcher error: {e}")

    def health_check(self):
        self.last_health_check = time.time()
        logging.debug("[Responder] Health check OK")
        return {"status": self.health_status}

    def _monitor_health(self):
        """Monitor health of all connections"""
        while self.running:
            try:
                # Check TTS service
                self.tts_socket.send_json({"action": "health_check"})
                if self.tts_socket.poll(HEALTH_CHECK_TIMEOUT * 1000):
                    response = self.tts_socket.recv_json()
                    self.health_status["connections"]["tts"] = response.get("status") == "ok"
                else:
                    self.health_status["connections"]["tts"] = False
                
                # Check TTS Cache
                self.tts_cache_socket.send_json({"action": "health_check"})
                if self.tts_cache_socket.poll(HEALTH_CHECK_TIMEOUT * 1000):
                    response = self.tts_cache_socket.recv_json()
                    self.health_status["connections"]["tts_cache"] = response.get("status") == "ok"
                else:
                    self.health_status["connections"]["tts_cache"] = False
                
                # Check TTS Connector
                self.tts_connector_socket.send_json({"action": "health_check"})
                if self.tts_connector_socket.poll(HEALTH_CHECK_TIMEOUT * 1000):
                    response = self.tts_connector_socket.recv_json()
                    self.health_status["connections"]["tts_connector"] = response.get("status") == "ok"
                else:
                    self.health_status["connections"]["tts_connector"] = False
                
                # Update overall health status
                all_healthy = all(self.health_status["connections"].values())
                self.health_status["status"] = "ok" if all_healthy else "degraded"
                self.health_status["last_check"] = time.time()
                
                # Log health status
                if not all_healthy:
                    logging.warning(f"[Responder] Health check failed: {self.health_status}")
                
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logging.error(f"[Responder] Health monitoring error: {e}")
                time.sleep(HEALTH_CHECK_INTERVAL)

# ------------------------------------------------------------------------- #
#                         SCRIPT ENTRY POINT                                #
# ------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        agent = ResponderAgent()
        agent.start()
    except KeyboardInterrupt:
        logging.info("[Responder] KeyboardInterrupt received. Stopping...")
        agent.stop()
    except Exception as e:
        logging.critical(f"[Responder] FATAL error in __main__: {e}")
        import traceback
        traceback.print_exc()