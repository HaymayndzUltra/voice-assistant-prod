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
        
        # Voice customization settings
        self.speaker_wav = None
        self.temperature = 0.7  # Voice variability
        self.speed = 1.0  # Voice speed multiplier
        self.volume = 1.0  # Volume level
        self.use_filipino_accent = False
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
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
            
        # Check for Tetey voice sample (from deprecated version)
        tetey_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
        if os.path.exists(tetey_voice_path):
            self.speaker_wav = tetey_voice_path
            logger.info(f"Found Tetey voice sample at {tetey_voice_path}")
        else:
            # Look for any wav files in the voice samples directory
            voice_samples = [f for f in os.listdir(self.voice_samples_dir) 
                            if f.endswith(".wav")]
            if voice_samples:
                self.speaker_wav = os.path.join(self.voice_samples_dir, voice_samples[0])
                logger.info(f"Using voice sample: {self.speaker_wav}")
        
        # Initialize TTS engines
        self._initialize_tts_engines()
        
        # Start audio playback thread
        self.playback_thread = threading.Thread(target=self.audio_playback_loop, daemon=True)
        self.playback_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._send_health_updates, daemon=True)
        self.health_thread.start()
        
        # Say initialization message with a more interesting phrase
        self.speak("Voice system is now online and ready for interaction. How may I assist you today?")
    
    def _initialize_tts_engines(self):
        """Initialize all TTS engines in order of preference"""
        self.tts_engines = {}
        
        # --- Start of XTTS Initialization Block ---
        
        print("\n==== XTTS INITIALIZATION DEBUG ====")
        
        # Set up voice sample
        tetey_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
        untitled_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/untitled1.wav"
        
        # Check which voice samples exist
        print("Checking available voice samples:")
        if os.path.exists(tetey_voice_path):
            print(f"  - Found tetey1.wav at: {tetey_voice_path}")
            self.speaker_wav = tetey_voice_path
        
        if os.path.exists(untitled_voice_path):
            print(f"  - Found untitled1.wav at: {untitled_voice_path}")
            self.speaker_wav = untitled_voice_path  # Prefer this one if both exist
        
        # Look for any wav files in the voice samples directory
        voice_samples = [f for f in os.listdir(self.voice_samples_dir) 
                        if f.endswith(".wav")]
        if voice_samples:
            sample_path = os.path.join(self.voice_samples_dir, voice_samples[0])
            print(f"  - Found sample in voice_samples dir: {sample_path}")
            # Only use if no other samples found
            if not self.speaker_wav:
                self.speaker_wav = sample_path
        
        if not self.speaker_wav:
            print("  - No voice samples found!")
        else:
            print(f"Using voice sample: {self.speaker_wav}")
        
        try:
            from TTS.api import TTS
            import torch
            
            # Check for CUDA
            cuda_available = torch.cuda.is_available()
            print(f"CUDA available: {cuda_available}")
            device = "cuda" if cuda_available else "cpu"
            
            print(f"Loading predefined XTTS model...")
            # Use the predefined model which we know works
            
            # Initialize XTTS without speaker_wav parameter
            try:
                print("Initializing XTTS model without voice sample")
                self.tts_engines["xtts"] = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                print("SUCCESS: XTTS model loaded successfully!")
            except Exception as e:
                print(f"Failed to initialize XTTS: {e}")
                import traceback
                print("--- DETAILED XTTS INITIALIZATION ERROR ---")
                traceback.print_exc()
                print("------------------------------------------")
            
            logger.info("Tier 1: XTTS v2 model loaded successfully.")
            print("XTTS initialization complete. Model is ready to use.")
            
        except Exception as e:
            logger.error(f"Tier 1 (XTTS) failed during initialization: {e}")
            print(f"CRITICAL ERROR in XTTS initialization: {e}")
            import traceback
            print("--- DETAILED XTTS INITIALIZATION ERROR ---")
            traceback.print_exc()
            print("------------------------------------------")

        print("==== END XTTS INITIALIZATION DEBUG ====\n")
        # --- End of XTTS Initialization Block ---
        
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
        print("\n===== SPEAK REQUEST =====")
        print(f"Text to speak: '{text[:50]}...'")
        print(f"Available engines: {list(self.tts_engines.keys())}")
        
        if not text or text.strip() == "":
            logger.warning("Empty text provided to speak function")
            print("ERROR: Empty text provided to speak function")
            print("===== END SPEAK REQUEST (FAILED) =====\n")
            return False
        
        # Process text into sentences
        sentences = self.split_into_sentences(text)
        logger.info(f"Split text into {len(sentences)} sentences")
        print(f"Split into {len(sentences)} sentences")
        
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
                    print("Attempting Tier 1: XTTS v2")
                    try:
                        success = self._speak_with_xtts(sentence)
                        print("XTTS was successful!")
                    except Exception as e:
                        logger.error(f"Tier 1 (XTTS) failed: {e}")
                        print(f"XTTS failed: {e}")
                else:
                    print("XTTS engine not available, skipping to next tier")
                
                # Tier 2: Windows SAPI
                if not success and "sapi" in self.tts_engines:
                    print("Attempting Tier 2: Windows SAPI")
                    try:
                        success = self._speak_with_sapi(sentence)
                        print("Windows SAPI was successful!")
                    except Exception as e:
                        logger.error(f"Tier 2 (SAPI) failed: {e}")
                        print(f"Windows SAPI failed: {e}")
                
                # Tier 3: pyttsx3
                if not success and "pyttsx3" in self.tts_engines:
                    print("Attempting Tier 3: pyttsx3")
                    try:
                        success = self._speak_with_pyttsx3(sentence)
                        print("pyttsx3 was successful!")
                    except Exception as e:
                        logger.error(f"Tier 3 (pyttsx3) failed: {e}")
                        print(f"pyttsx3 failed: {e}")
                
                # Tier 4: Console Print
                if not success:
                    print("Attempting Tier 4: Console Print")
                    try:
                        success = self._speak_with_console(sentence)
                        print("Console Print was successful!")
                    except Exception as e:
                        logger.error(f"Tier 4 (Console) failed: {e}")
                        print(f"Console Print failed: {e}")
                
                if not success:
                    logger.error(f"All TTS engines failed for sentence: {sentence}")
                    print(f"ERROR: All TTS engines failed for sentence: '{sentence}'")
            
            # Add a small silence at the end
            silence = np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32)
            self.audio_queue.put(silence)
            
            # Wait for queue to empty
            while not self.audio_queue.empty() and not self.stop_speaking:
                time.sleep(0.1)
            
            print("===== END SPEAK REQUEST (SUCCESS) =====\n")
            return True
            
        except Exception as e:
            logger.error(f"Error in speak function: {e}")
            print(f"Error in speak function: {e}")
            print("===== END SPEAK REQUEST (FAILED) =====\n")
            return False
        finally:
            self.is_speaking = False
    
    def _speak_with_xtts(self, text):
        """Speak using XTTS v2"""
        # Make sure numpy is imported
        import numpy as np
        
        print(f"\n==== XTTS SPEAK ATTEMPT ====")
        print(f"Attempting to speak with XTTS: '{text[:50]}...'")
        
        # Map Tagalog/Filipino to English since XTTS doesn't support 'tl' directly
        # The voice sample will still give it Filipino characteristics
        actual_language = self.language
        tts_language = self.language
        
        # List of supported languages from the error message
        supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']
        
        # If language is not supported, fall back to English
        if tts_language not in supported_languages:
            print(f"Language '{tts_language}' not directly supported, using 'en' with voice sample instead")
            tts_language = 'en'
        
        print(f"Voice settings: language={actual_language} (using {tts_language}), temperature={self.temperature}, speed={self.speed}, volume={self.volume}")
        
        # DETAILED VOICE SAMPLE VERIFICATION
        voice_sample = self.speaker_wav
        print(f"Voice sample path: {voice_sample}")
        if voice_sample:
            if os.path.exists(voice_sample):
                try:
                    import soundfile as sf
                    info = sf.info(voice_sample)
                    print(f"VOICE SAMPLE VERIFIED: {voice_sample}")
                    print(f"  - File exists: YES")
                    print(f"  - Duration: {info.duration:.2f} seconds")
                    print(f"  - Sample rate: {info.samplerate} Hz")
                    print(f"  - Channels: {info.channels}")
                except Exception as e:
                    print(f"  - Error reading voice sample: {e}")
            else:
                print(f"  - File exists: NO - VOICE SAMPLE NOT FOUND!")
                print(f"  - Will fall back to default voice")
        else:
            print("  - No voice sample specified")
        
        # Check cache first - include all voice parameters in the cache key
        cache_key = hashlib.md5(f"{text}_{actual_language}_{self.speaker_wav}_{self.temperature}_{self.speed}_{self.volume}".encode()).hexdigest()
        cached_audio = self.cache.get(cache_key)
        audio = None  # Initialize audio variable
        
        if cached_audio:
            print("Using cached XTTS audio")
            logger.info(f"Using cached XTTS audio for: {text[:30]}...")
            audio = cached_audio
        else:
            print("Generating new XTTS audio - no cache hit")
            logger.info(f"Generating XTTS audio for: {text[:30]}...")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio using XTTS
            try:
                print(f"Generating new XTTS audio...")
                
                # Ensure we have a valid speaker_wav
                if not self.speaker_wav or not os.path.exists(self.speaker_wav):
                    print("WARNING: No valid speaker_wav found for XTTS!")
                    # Try to find any available voice sample
                    tetey_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
                    untitled_voice_path = "C:/Users/haymayndz/Desktop/Voice assistant/untitled1.wav"
                    
                    if os.path.exists(untitled_voice_path):
                        self.speaker_wav = untitled_voice_path
                        print(f"Found and using untitled1.wav: {untitled_voice_path}")
                    elif os.path.exists(tetey_voice_path):
                        self.speaker_wav = tetey_voice_path
                        print(f"Found and using tetey1.wav: {tetey_voice_path}")
                
                # Double check we have a valid speaker_wav before proceeding
                if not self.speaker_wav or not os.path.exists(self.speaker_wav):
                    print("ERROR: Still no valid speaker_wav found! Will likely use default voice.")
                
                # Explicitly load the voice sample for this generation
                print(f"Generating with voice sample: {self.speaker_wav}")
                
                # Use the TTS model to generate audio
                wav = self.tts_engines["xtts"].tts(
                    text=text,
                    speaker_wav=self.speaker_wav,
                    language=tts_language,
                    temperature=self.temperature
                )
                
                print("XTTS generation successful!")
                
                # Handle the case where wav is a list (newer XTTS versions return a list)
                if isinstance(wav, list):
                    print("Converting list output to numpy array...")
                    # If it's a list of sentences, concatenate them
                    if len(wav) > 0:
                        if isinstance(wav[0], np.ndarray):
                            wav = np.concatenate(wav)
                        else:
                            # If it's a list of floats, convert directly to numpy array
                            wav = np.array(wav)
                
                # Apply speed adjustment if needed
                if self.speed != 1.0:
                    print(f"Adjusting speed to {self.speed}x")
                    import librosa
                    wav = librosa.effects.time_stretch(wav, rate=self.speed)
                
                # Apply volume adjustment if needed
                if self.volume != 1.0:
                    print(f"Adjusting volume to {self.volume}x")
                    wav = wav * self.volume
                
                # Keep audio as float32 for compatibility with sounddevice
                # Make sure values are between -1 and 1
                audio = wav.astype(np.float32)
                
                # Cache the result
                self.cache[cache_key] = audio
                
            except Exception as e:
                print(f"XTTS generation failed: {e}")
                import traceback

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
                traceback.print_exc()
                # Fall back to SAPI
                return self._speak_with_sapi(text)
        
        # Stream audio in chunks
        if audio is not None:
            print(f"Streaming XTTS audio in chunks: {len(audio)} samples")
            chunk_size = BUFFER_SIZE
            for i in range(0, len(audio), chunk_size):
                if self.stop_speaking:
                    print("Streaming interrupted by stop command")
                    break
                chunk = audio[i:i+chunk_size]
                self.audio_queue.put(chunk)
            
            print("==== END XTTS SPEAK ATTEMPT (SUCCESS) ====\n")
            return True
        else:
            print("==== END XTTS SPEAK ATTEMPT (FAILED - NO AUDIO) ====\n")
            return self._speak_with_sapi(text)
    
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
                dtype='float32',  # Always use float32 for output
                blocksize=BUFFER_SIZE
            ) as stream:
                while True:
                    try:
                        # Get audio chunk from queue with timeout
                        try:
                            chunk = self.audio_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                        
                        # Convert chunk to float32 if it's not already
                        if chunk.dtype != np.float32:
                            if chunk.dtype == np.int16:
                                # Convert from int16 to float32
                                chunk = chunk.astype(np.float32) / 32767.0
                            else:
                                # For any other type, try to convert to float32
                                chunk = chunk.astype(np.float32)
                        
                        # Make sure values are between -1 and 1
                        if np.max(np.abs(chunk)) > 1.0:
                            chunk = chunk / np.max(np.abs(chunk))
                        
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
                        # Check if language is specified
                        if "language" in data:
                            self.language = data.get("language")
                            logger.info(f"Using language: {self.language}")
                            
                        logger.info(f"Received message: {json.dumps(data)[:50]}...")
                        
                        # Speak the text
                        success = self.speak(text)
                        
                        # Send response
                        if success:
                            self.socket.send_string(json.dumps({"status": "ok", "message": "Speech started"}))
                        else:
                            self.socket.send_string(json.dumps({"status": "error", "message": "Failed to speak"}))
                    
                    elif command == "set_voice":
                        logger.info(f"Setting voice parameters: {json.dumps(data)}")
                        response = {"status": "ok", "message": "Voice settings updated", "updated": []}
                        
                        # Update language if provided
                        if "language" in data:
                            self.language = data.get("language")
                            logger.info(f"Language set to: {self.language}")
                            response["updated"].append("language")
                        
                        # Update speaker_wav if provided
                        speaker_wav = data.get("speaker_wav")
                        if speaker_wav and os.path.exists(speaker_wav):
                            self.speaker_wav = speaker_wav
                            logger.info(f"Voice sample set to: {speaker_wav}")
                            response["updated"].append("voice_sample")
                        
                        # Update temperature if provided
                        if "temperature" in data:
                            try:
                                temp = float(data.get("temperature"))
                                if 0.0 <= temp <= 1.0:
                                    self.temperature = temp
                                    logger.info(f"Voice temperature set to: {temp}")
                                    response["updated"].append("temperature")
                            except (ValueError, TypeError):
                                pass
                        
                        # Update speed if provided
                        if "speed" in data:
                            try:
                                speed = float(data.get("speed"))
                                if 0.5 <= speed <= 2.0:
                                    self.speed = speed
                                    logger.info(f"Voice speed set to: {speed}")
                                    response["updated"].append("speed")
                            except (ValueError, TypeError):
                                pass
                        
                        # Update volume if provided
                        if "volume" in data:
                            try:
                                volume = float(data.get("volume"))
                                if 0.1 <= volume <= 2.0:
                                    self.volume = volume
                                    logger.info(f"Voice volume set to: {volume}")
                                    response["updated"].append("volume")
                            except (ValueError, TypeError):
                                pass
                        
                        # Filipino mode compatibility
                        if data.get("filipino_accent", False):
                            tetey_path = "C:/Users/haymayndz/Desktop/Voice assistant/tetey1.wav"
                            if os.path.exists(tetey_path):
                                self.speaker_wav = tetey_path
                                self.use_filipino_accent = True
                                logger.info(f"Filipino accent mode activated using {tetey_path}")
                                response["updated"].append("filipino_accent")
                            else:
                                logger.warning("Filipino voice sample not found")
                                response["status"] = "warning"
                                response["message"] = "Filipino voice sample not found"
                        
                        # Get current voice settings
                        response["current_settings"] = {
                            "language": self.language,
                            "temperature": self.temperature,
                            "speed": self.speed,
                            "volume": self.volume,
                            "speaker_wav": self.speaker_wav,
                            "use_filipino_accent": self.use_filipino_accent
                        }
                        
                        self.socket.send_string(json.dumps(response))
                    
                    elif command == "get_voice_settings":
                        # Return current voice settings
                        settings = {
                            "language": self.language,
                            "temperature": self.temperature,
                            "speed": self.speed,
                            "volume": self.volume,
                            "speaker_wav": self.speaker_wav,
                            "use_filipino_accent": self.use_filipino_accent
                        }
                        self.socket.send_string(json.dumps({
                            "status": "ok", 
                            "settings": settings
                        }))
                            
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