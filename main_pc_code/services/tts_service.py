"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
TTS (Text-to-Speech) Micro-service
Purpose: Lightweight wrapper to receive text and request speech synthesis from ModelManagerAgent
Features: Audio streaming, voice customization, multilingual support
"""

import zmq
import numpy as np
import time
import logging
import os
import json
import threading
import traceback
from datetime import datetime
import uuid
from pathlib import Path
import sys
import queue
import sounddevice as sd
import hashlib
from collections import OrderedDict

# Add the project's main_pc_code directory to the Python path
from common.utils.path_manager import PathManager
from common.utils.path_env import get_project_root
MAIN_PC_CODE_DIR = PathManager.get_project_root()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import discover_service, register_service
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from main_pc_code.utils import model_client
from common.env_helpers import get_env

# Load configuration
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TTSService")

# Audio Settings
SAMPLE_RATE = int(config.get("sample_rate", 24000))
CHANNELS = int(config.get("channels", 1))
BUFFER_SIZE = int(config.get("buffer_size", 1024))
MAX_CACHE_SIZE = int(config.get("max_cache_size", 50))
DEFAULT_LANGUAGE = config.get("default_language", "en")

class TTSService(BaseAgent):
    def __init__(self, port=None):
        """Initialize the TTS service."""
        # Get configuration values with fallbacks
        agent_port = int(config.get("tts_service_port", 5801)) if port is None else port
        agent_name = config.get("tts_service_name", "TTSService")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Initialize state variables
        self.running = True
        self.start_time = time.time()
        self.request_count = 0
        self.current_language = DEFAULT_LANGUAGE
        
        # Voice customization settings
        self.speaker_wav = None
        self.temperature = 0.7  # Voice variability
        self.speed = 1.0  # Voice speed multiplier
        self.volume = 1.0  # Volume level
        
        # Set up voice samples directory
        self.voice_samples_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../agents/voice_samples"
        )
        if os.path.exists(self.voice_samples_dir):
            # Look for any wav files in the voice samples directory
            voice_samples = [f for f in os.listdir(self.voice_samples_dir) 
                            if f.endswith(".wav")]
            if voice_samples:
                self.speaker_wav = os.path.join(self.voice_samples_dir, voice_samples[0])
                logger.info(f"Using voice sample: {self.speaker_wav}")
        
        # Initialize audio cache (OrderedDict maintains insertion order)
        self.cache = OrderedDict()
        
        # Queue for streaming audio chunks
        self.audio_queue = queue.Queue()
        self.is_speaking = False
        self.stop_speaking = False
        

        
        # Connect to interrupt handler
        self.interrupt_port = int(config.get("streaming_interrupt_handler_port", 5576))
        self.interrupt_socket = self.context.socket(zmq.SUB)
        
        # Try to get the interrupt handler address from service discovery
        interrupt_address = None
        try:
            interrupt_handler = discover_service("StreamingInterruptHandler")
            if interrupt_handler and interrupt_handler.get("status") == "SUCCESS":
                interrupt_info = interrupt_handler.get("payload", {})
                interrupt_host = interrupt_info.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
                interrupt_port = interrupt_info.get("port", self.interrupt_port)
                interrupt_address = f"tcp://{interrupt_host}:{interrupt_port}"
        except Exception as e:
            logger.warning(f"Error discovering interrupt handler: {e}")
            
        if not interrupt_address:
            interrupt_address = f"tcp://localhost:{self.interrupt_port}"
            
        self.interrupt_socket.connect(interrupt_address)
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to interrupt handler at {interrupt_address}")
        
        self.interrupt_flag = threading.Event()
        self._start_interrupt_thread()
        
        # Start audio playback thread
        self.playback_thread = threading.Thread(target=self.audio_playback_loop, daemon=True)
        self.playback_thread.start()
        
        # Register with service discovery
        self._register_service()
        
        logger.info(f"{self.name} initialized on port {self.port}")

    def _register_service(self):
        """Register this service with the service discovery system."""
        try:
            register_result = register_service(
                name=self.name,
                port=self.port,
                additional_info={
                    "capabilities": ["tts", "speech_synthesis", "multilingual"],
                    "status": "online"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")

    def _add_to_cache(self, key, audio):
        """Add audio to cache with LRU eviction."""
        self.cache[key] = audio
        if len(self.cache) > MAX_CACHE_SIZE:
            self.cache.popitem(last=False)  # Remove oldest item

    def speak(self, text, language=None, voice_sample=None, temperature=None, speed=None, volume=None):
        """
        Generate speech from text using the ModelManagerAgent.
        
        Args:
            text (str): Text to convert to speech
            language (str, optional): Language code. Defaults to current language.
            voice_sample (str, optional): Path to voice sample file. Defaults to current voice.
            temperature (float, optional): Voice variability. Defaults to current setting.
            speed (float, optional): Speech speed. Defaults to current setting.
            volume (float, optional): Volume level. Defaults to current setting.
            
        Returns:
            dict: Status of the speech synthesis request
        """
        try:
            # Reset stop flag
            self.stop_speaking = False
            
            # Use provided parameters or fall back to defaults
            language = language or self.current_language
            voice_sample = voice_sample or self.speaker_wav
            temperature = temperature or self.temperature
            speed = speed or self.speed
            volume = volume or self.volume
            
            # Check cache first - include all voice parameters in the cache key
            cache_key = hashlib.md5(f"{text}_{language}_{voice_sample}_{temperature}_{speed}_{volume}".encode()).hexdigest()
            cached_audio = self.cache.get(cache_key)
            
            if cached_audio is not None:
                logger.info(f"Using cached TTS audio for: {text[:30]}...")
                self._stream_audio(cached_audio)
                return {"status": "success", "message": "Using cached audio", "cached": True}
            
            # Start timing for performance metrics
            start_time = time.time()
            
            # Prepare request parameters
            params = {
                "text": text,
                "language": language,
                "request_id": str(uuid.uuid4()),
                "model_type": "tts",
                "temperature": temperature,
                "speed": speed,
                "volume": volume
            }
            
            # Add voice sample if available
            if voice_sample and os.path.exists(voice_sample):
                # In a real implementation, we'd need to handle the voice sample file
                # For now, just note that we're using it
                params["voice_sample_path"] = voice_sample
                
            # ✅ UPDATED: Use XTTS-v2 model specifically
            request_params = {
                "action": "generate_speech",
                "model_id": "xtts-v2",  # Use downloaded TTS model
                "text": text,
                "voice_settings": {
                    "speaker": "default",
                    "language": language or "en",
                    "speed": speed,
                    "pitch": 1.0,
                    "temperature": temperature
                },
                "streaming": True,  # Enable streaming for real-time response
                "enable_streaming": True,  # Streaming support
                "sample_rate": 22050,  # XTTS-v2 default
                "request_id": str(uuid.uuid4())
            }
            
            # Send request to ModelManagerSuite using XTTS-v2
            response = model_client.request_inference(request_params)
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [TTSService] - [SpeechSynthesis] - Duration: {duration_ms:.2f}ms")
            
            if response and response.get("success"):
                audio_data = response.get("audio_data", [])
                
                if audio_data:
                    # Convert audio data to numpy array
                    audio = np.array(audio_data, dtype=np.float32)
                    
                    # Cache the result
                    self._add_to_cache(cache_key, audio)
                    
                    # Stream the audio
                    self._stream_audio(audio)
                    
                    logger.info(f"✅ TTS Success: '{text[:30]}...' ({len(audio_data)/22050:.2f}s)")
                    return {"status": "success", "message": "XTTS-v2 audio synthesized and playing", "model_used": "xtts-v2"}
                else:
                    error_message = "No audio data received from XTTS-v2"
                    logger.error(error_message)
                    self.report_error("SynthesisError", error_message)
                    return {"status": "error", "message": error_message}
            else:
                error_message = response.get("message", "Unknown error")
                logger.error(f"Speech synthesis failed: {error_message}")
                self.report_error("SynthesisError", f"Failed to synthesize speech: {error_message}")
                return {"status": "error", "message": error_message}
                
        except Exception as e:
            logger.error(f"Error in speech synthesis: {str(e)}")
            logger.error(traceback.format_exc())
            self.report_error("SynthesisError", f"Exception during speech synthesis: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _stream_audio(self, audio):
        """Stream audio in chunks."""
        if audio is None:
            logger.warning("No audio to stream")
            return
            
        self.is_speaking = True
        chunk_size = BUFFER_SIZE
        
        for i in range(0, len(audio), chunk_size):
            if self.stop_speaking:
                logger.info("Streaming interrupted by stop command")
                break
            chunk = audio[i:i+chunk_size]
            self.audio_queue.put(chunk)
            
        self.is_speaking = False

    def audio_playback_loop(self):
        """Background thread for audio playback."""
        logger.info("Starting audio playback thread")
        
        try:
            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32',
                blocksize=BUFFER_SIZE
            ) as stream:
                while self.running:
                    try:
                        # Get audio chunk from queue with timeout
                        try:
                            chunk = self.audio_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                            
                        # Play the chunk
                        stream.write(chunk)
                        self.audio_queue.task_done()
                        
                    except Exception as e:
                        logger.error(f"Error in audio playback: {str(e)}")
                        time.sleep(0.1)  # Prevent tight loop on error
        except Exception as e:
            logger.error(f"Failed to initialize audio output stream: {str(e)}")
            logger.error(traceback.format_exc())

    def _interrupt_listener(self):
        """Thread to listen for interrupt commands."""
        logger.info("Starting interrupt listener thread")
        
        while self.running:
            try:
                # Check for interrupt messages
                try:
                    message = self.interrupt_socket.recv_json(flags=zmq.NOBLOCK)
                    command = message.get("command", "")
                    
                    if command == "STOP_SPEAKING":
                        logger.info("Received STOP_SPEAKING command")
                        self.stop_speaking = True
                        self.interrupt_flag.set()
                        
                        # Clear the queue
                        while not self.audio_queue.empty():
                            try:
                                self.audio_queue.get_nowait()
                                self.audio_queue.task_done()
                            except queue.Empty:
                                break
                except zmq.Again:
                    pass  # No message available
                    
                time.sleep(0.1)  # Small sleep to prevent tight loop
                
            except Exception as e:
                logger.error(f"Error in interrupt listener: {str(e)}")
                time.sleep(1)  # Longer sleep on error

    def _start_interrupt_thread(self):
        """Start the interrupt listener thread."""
        interrupt_thread = threading.Thread(target=self._interrupt_listener, daemon=True)
        interrupt_thread.start()

    def report_error(self, error_type, message, severity="WARNING", context=None):
        """Report an error to the error bus."""
        try:
            error_data = {
                "agent": self.name,
                "error_type": error_type,
                "severity": severity,
                "message": message,
                "context": context or {}
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"Reported error: {message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def handle_request(self, request):
        """Handle incoming requests."""
        try:
            self.request_count += 1
            action = request.get("action", "")
            
            if action == "speak":
                text = request.get("text")
                if not text:
                    return {"status": "error", "message": "Missing text parameter"}
                    
                # Extract optional parameters
                language = request.get("language")
                voice_sample = request.get("voice_sample")
                temperature = request.get("temperature")
                speed = request.get("speed")
                volume = request.get("volume")
                
                result = self.speak(text, language, voice_sample, temperature, speed, volume)
                return result
                
            elif action == "stop":
                self.stop_speaking = True
                return {"status": "success", "message": "Stop command received"}
                
            elif action == "set_voice":
                voice_sample = request.get("voice_sample")
                if voice_sample and os.path.exists(voice_sample):
                    self.speaker_wav = voice_sample
                    return {"status": "success", "message": f"Voice set to {voice_sample}"}
                else:
                    return {"status": "error", "message": "Invalid voice sample path"}
                    
            elif action == "health_check":
                return self._get_health_status()
                
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    def _get_health_status(self):
        """Get the health status of the service."""
        return {
            "status": "ok",
            "service": self.name,
            "uptime_seconds": int(time.time() - self.start_time),
            "request_count": self.request_count,
            "is_speaking": self.is_speaking
        }

    def run(self):
        """Main run loop."""
        logger.info(f"Starting {self.name}...")
        
        while self.running:
            try:
                # Wait for a request with timeout
                if self.socket.poll(1000) == 0:  # 1 second timeout
                    continue
                    
                # Receive and process request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process the request
                response = self.handle_request(message)
                
                # Send the response
                self.socket.send_json(response)
                
            except zmq.error.Again:
                # Timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                logger.error(traceback.format_exc())
                try:
                    self.socket.send_json({"status": "error", "message": str(e)})
                except:
                    pass

    def cleanup(self):
        """Clean up resources."""
        logger.info(f"Cleaning up {self.name}...")
        self.running = False
        self.stop_speaking = True
        
        # Clear the audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
            except queue.Empty:
                break
                
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'error_bus_pub'):
            self.error_bus_pub.close()
        if hasattr(self, 'interrupt_socket'):
            self.interrupt_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
            
        logger.info(f"{self.name} cleaned up successfully")

if __name__ == "__main__":
    service = None
    try:
        service = TTSService()
        service.run()
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        if service:
            service.cleanup() 