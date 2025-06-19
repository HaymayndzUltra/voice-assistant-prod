from src.core.base_agent import BaseAgent
"""
Ultimate TTS Agent
Provides advanced text-to-speech capabilities with 4-tier fallback system:
Tier 1: XTTS v2 (Primary) - High-quality multilingual speech synthesis
Tier 2: Windows SAPI (Secondary) - Reliable system-level TTS
Tier 3: pyttsx3 (Tertiary) - Cross-platform TTS fallback
Tier 4: Console Print (Final) - Text output as last resort
"""
import zmq
import json
import time
import logging
import sys
import os
import threading
import queue
import numpy as np
import sounddevice as sd
from pathlib import Path
import hashlib
import tempfile
import re
from collections import OrderedDict

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).resolve().parent.parent.parent, 'modular_system', 'logs', 'ultimate_tts_agent.py.log'))
    ]
)
logger = logging.getLogger("UltimateTTSAgent")

# Add custom XTTS path
xtts_path = r'C:\Users\haymayndz\Desktop\xtts-local'
if os.path.exists(xtts_path):
    sys.path.append(xtts_path)
    logger.info(f"Added custom XTTS path: {xtts_path}")

# ZMQ Configuration
TTS_PORT = 5562  # Unified TTS port
UNIFIED_SYSTEM_PORT = 5569  # Port for UnifiedSystemAgent health monitoring

# Audio playback settings
SAMPLE_RATE = 24000  # Default for TTS output
CHANNELS = 1
BUFFER_SIZE = 1024
MAX_CACHE_SIZE = 50  # Maximum number of cached audio samples

class UltimateTTSAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingTtsAgent")
        """Initialize the Ultimate TTS agent with 4-tier fallback system"""
        logger.info("Initializing Ultimate TTS Agent")
        self.language = language
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{TTS_PORT}")
        
        # Connect to UnifiedSystemAgent for health monitoring
        self.system_socket = self.context.socket(zmq.PUB)
        self.system_socket.connect(f"tcp://localhost:{UNIFIED_SYSTEM_PORT}")
        logger.info(f"Connected to UnifiedSystemAgent on port {UNIFIED_SYSTEM_PORT}")
        
        # Initialize audio cache (OrderedDict maintains insertion order)
        self.cache = OrderedDict()
        
        # Queue for streaming audio chunks
        self.audio_queue = queue.Queue()
        self.is_speaking = False
        self.stop_speaking = False
        
        # Set up voice samples directory
        self.voice_samples_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "voice_samples"
        )
        if not os.path.exists(self.voice_samples_dir):
            os.makedirs(self.voice_samples_dir)
            logger.info(f"Created voice samples directory at {self.voice_samples_dir}")
        
        # Initialize TTS engines
        self._initialize_tts_engines()
        
        # Start audio playback thread
        self.playback_thread = threading.Thread(target=self.audio_playback_loop, daemon=True)
        self.playback_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._send_health_updates, daemon=True)
        self.health_thread.start()
        
        # Say initialization message
        self.speak("Ultimate TTS Agent initialized and ready.")
    
    def _initialize_tts_engines(self):
        """Initialize all TTS engines in order of preference"""
        self.tts_engines = {}
        
        # Tier 1: XTTS v2
        try:
            from TTS.api import TTS
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tts_engines["xtts"] = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            logger.info(f"Tier 1: XTTS v2 initialized on {device}")
        except Exception as e:
            logger.warning(f"Tier 1: XTTS v2 initialization failed: {e}")
        
        # Tier 2: Windows SAPI
        try:
            import win32com.client
            self.tts_engines["sapi"] = win32com.client.Dispatch("SAPI.SpVoice")
            logger.info("Tier 2: Windows SAPI initialized")
        except Exception as e:
            logger.warning(f"Tier 2: Windows SAPI initialization failed: {e}")
        
        # Tier 3: pyttsx3
        try:
            import pyttsx3
            self.tts_engines["pyttsx3"] = pyttsx3.init()
            logger.info("Tier 3: pyttsx3 initialized")
        except Exception as e:
            logger.warning(f"Tier 3: pyttsx3 initialization failed: {e}")
        
        # Tier 4: Console Print (always available)
        self.tts_engines["console"] = True
        logger.info("Tier 4: Console Print initialized")
    
    def _add_to_cache(self, key, audio):
        """Add audio to cache with size limit"""
        if len(self.cache) >= MAX_CACHE_SIZE:
            # Remove oldest item
            self.cache.popitem(last=False)
        self.cache[key] = audio
    
    def split_into_sentences(self, text):
        """Split text into sentences for streaming"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s for s in sentences if s.strip()]
    
    def speak(self, text):
        """Speak text using the best available TTS engine"""
        if not text or text.strip() == "":
            logger.warning("Empty text provided to speak function")
            return False
        
        # Process text into sentences
        sentences = self.split_into_sentences(text)
        logger.info(f"Split text into {len(sentences)} sentences")
        
        # Clear any existing audio in the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        self.stop_speaking = False
        self.is_speaking = True
        
        try:
            for sentence in sentences:
                if self.stop_speaking:
                    break
                
                # Try each TTS engine in order
                success = False
                
                # Tier 1: XTTS v2
                if "xtts" in self.tts_engines and not success:
                    try:
                        success = self._speak_with_xtts(sentence)
                    except Exception as e:
                        logger.error(f"Tier 1 (XTTS) failed: {e}")
                
                # Tier 2: Windows SAPI
                if not success and "sapi" in self.tts_engines:
                    try:
                        success = self._speak_with_sapi(sentence)
                    except Exception as e:
                        logger.error(f"Tier 2 (SAPI) failed: {e}")
                
                # Tier 3: pyttsx3
                if not success and "pyttsx3" in self.tts_engines:
                    try:
                        success = self._speak_with_pyttsx3(sentence)
                    except Exception as e:
                        logger.error(f"Tier 3 (pyttsx3) failed: {e}")
                
                # Tier 4: Console Print
                if not success:
                    try:
                        success = self._speak_with_console(sentence)
                    except Exception as e:
                        logger.error(f"Tier 4 (Console) failed: {e}")
                
                if not success:
                    logger.error(f"All TTS engines failed for sentence: {sentence}")
            
            # Add a small silence at the end
            silence = np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32)
            self.audio_queue.put(silence)
            
            # Wait for queue to empty
            while not self.audio_queue.empty() and not self.stop_speaking:
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in speak function: {e}")
            return False
        finally:
            self.is_speaking = False
    
    def _speak_with_xtts(self, text):
        """Speak using XTTS v2"""
        # Check cache first
        cache_key = hashlib.md5(f"{text}_{self.language}".encode()).hexdigest()
        cached_audio = self.cache.get(cache_key)
        
        if cached_audio:
            logger.info(f"Using cached XTTS audio for: {text[:30]}...")
            audio_data = np.frombuffer(cached_audio, dtype=np.float32)
        else:
            logger.info(f"Generating XTTS audio for: {text[:30]}...")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio with XTTS
            self.tts_engines["xtts"].tts_to_file(
                text=text,
                file_path=temp_path,
                language=self.language
            )
            
            # Read audio file
            import soundfile as sf
            audio_data, _ = sf.read(temp_path)
            
            # Convert to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Cache the audio
            self._add_to_cache(cache_key, audio_data.tobytes())
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
        
        # Stream audio in chunks
        chunk_size = BUFFER_SIZE
        for i in range(0, len(audio_data), chunk_size):
            if self.stop_speaking:
                break
            chunk = audio_data[i:i+chunk_size]
            self.audio_queue.put(chunk)
        
        return True
    
    def _speak_with_sapi(self, text):
        """Speak using Windows SAPI"""
        logger.info(f"Speaking with SAPI: {text[:30]}...")
        self.tts_engines["sapi"].Speak(text)
        return True
    
    def _speak_with_pyttsx3(self, text):
        """Speak using pyttsx3"""
        logger.info(f"Speaking with pyttsx3: {text[:30]}...")
        engine = self.tts_engines["pyttsx3"]
        engine.say(text)
        engine.runAndWait()
        return True
    
    def _speak_with_console(self, text):
        """Print text to console"""
        logger.info(f"Console output: {text}")
        print(f"[TTS] {text}")
        return True
    
    def audio_playback_loop(self):
        """Background thread for audio playback"""
        logger.info("Starting audio playback thread")
        
        try:
            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32',
                blocksize=BUFFER_SIZE
            ) as stream:
                while True:
                    try:
                        # Get audio chunk from queue with timeout
                        try:
                            chunk = self.audio_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                        
                        # Play audio chunk
                        if len(chunk) > 0:
                            stream.write(chunk)
                        
                        # Mark task as done
                        self.audio_queue.task_done()
                        
                    except Exception as e:
                        logger.error(f"Error in audio playback: {e}")
                        time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error setting up audio stream: {e}")
    
    def _send_health_updates(self):
        """Send periodic health updates to UnifiedSystemAgent"""
        while True:
            try:
                health_data = {
                    "agent_name": "ultimate_tts_agent",
                    "status": "healthy",
                    "timestamp": time.time(),
                    "metrics": {
                        "tts_engine": "XTTS",
                        "active": self.tts_engines["xtts"] is not None
                    }
                }
                self.system_socket.send_string(json.dumps(health_data))
                time.sleep(5)  # Send updates every 5 seconds
            except Exception as e:
                logger.error(f"Error sending health update: {e}")
                time.sleep(1)  # Wait a bit before retrying
    
    def run(self):
        """Main loop for the Ultimate TTS agent"""
        logger.info("Starting Ultimate TTS Agent")
        
        try:
            while True:
                try:
                    # Wait for messages
                    message = self.socket.recv_string()
                    data = json.loads(message)
                    command = data.get("command", "")
                    
                    if command == "speak":
                        text = data.get("text", "")
                        logger.info(f"Received message: {json.dumps(data)[:50]}...")
                        
                        # Speak the text
                        success = self.speak(text)
                        
                        # Send response
                        if success:
                            self.socket.send_string(json.dumps({"status": "ok", "message": "Speech started"}))
                        else:
                            self.socket.send_string(json.dumps({"status": "error", "message": "Failed to speak"}))
                            
                    elif command == "stop":
                        logger.info("Received stop command")
                        self.stop_speaking = True
                        self.socket.send_string(json.dumps({"status": "ok", "message": "Stop command acknowledged"}))
                        
                    else:
                        logger.warning(f"Unknown command: {command}")
                        self.socket.send_string(json.dumps({"status": "error", "message": f"Unknown command: {command}"}))
                        
                except zmq.Again:
                    # No message available, sleep a bit
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected")
        except Exception as e:
            logger.error(f"Error in TTS agent: {e}")
        finally:
            logger.info("Shutting down TTS agent")
            self.socket.close()
            self.system_socket.close()
            self.context.term()

if __name__ == "__main__":
    print("=== Ultimate TTS Agent ===")
    print(f"Listening on ZMQ port {TTS_PORT}")
    print("4-tier TTS system:")
    print("1. XTTS v2 (Primary)")
    print("2. Windows SAPI (Secondary)")
    print("3. pyttsx3 (Tertiary)")
    print("4. Console Print (Final)")
    
    # Create and run TTS agent
    agent = UltimateTTSAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
