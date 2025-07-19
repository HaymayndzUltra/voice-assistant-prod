# ✅ Path patch fix for src/ and utils/ imports
import sys
import os
from pathlib import Path

def get_main_pc_code():
    """Get the path to the main_pc_code directory"""
    current_dir = Path(__file__).resolve().parent
    main_pc_code_dir = current_dir.parent
    return main_pc_code_dir

# First define a basic join_path function for bootstrapping
def join_path(*args):
    return os.path.join(*args)

# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

PROJECT_ROOT = os.path.abspath(join_path("main_pc_code", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.core.base_agent import BaseAgent
# Tone detection for Human Awareness Agent

import time
import logging
import threading
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import yaml
from datetime import datetime
from queue import Queue
import re
import numpy as np
import wave
from typing import Dict, Any, Optional
from main_pc_code.utils.config_loader import load_config
import psutil
from common.env_helpers import get_env

# Load configuration at module level
config = load_config()

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Try to import audio processing libraries
try:
    import pyaudio
    import whisper
    WHISPER_AVAILABLE = True
    logger = logging.getLogger("ToneDetector")
    logger.info("Successfully imported whisper and pyaudio")
except ImportError as e:
    WHISPER_AVAILABLE = False
    logger = logging.getLogger("ToneDetector")
    logger.warning(f"Failed to import audio processing libraries: {e}")

# Configure logging for tone detector
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "tone_detector.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ToneDetector")

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "logs", "human_awareness_tone.log")), 
                              logging.StreamHandler()])
logger = logging.getLogger("HumanAwareness-Tone")

# Shared data queue for detected tones
tone_queue = Queue(maxsize=10)

# Emotional tone categories
TONE_CATEGORIES = {
    "neutral": "calm, balanced",
    "frustrated": "irritated, annoyed, impatient",
    "confused": "uncertain, puzzled, lost",
    "excited": "enthusiastic, eager, animated",
    "tired": "fatigued, exhausted, low-energy"
}

class ToneDetector(BaseAgent):
    def __init__(self):
        # Initialize with proper parameters before calling super().__init__()
        self.port = config.get("port", 5625)
        self.start_time = time.time()
        self.running = True
        self.name = "ToneDetector"
        self.processed_audio_chunks = 0
        self.last_detection_time = None
        
        # Call super().__init__() without _agent_args
        super().__init__()
        
        # Initialize tone detection components
        self.dev_mode = config.get("dev_mode", True)
        self.whisper_socket = None
        self.tagalog_analyzer = None
        self.whisper_model = None
        
        # Setup error bus
        self.error_bus_port = int(config.get("error_bus_port", 7150))
        self.error_bus_host = os.environ.get('PC2_IP', config.get("pc2_ip", get_env("BIND_ADDRESS", "0.0.0.0")))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Start tone monitoring in background
        self.tone_thread = threading.Thread(target=self._start_tone_monitor, daemon=True)
        self.tone_thread.start()
        
        logger.info(f"ToneDetector initialized on port {self.port}")
    
    def _start_tone_monitor(self):
        """Start tone monitoring in background thread."""
        try:
            # Connect to the Whisper stream
            self.whisper_socket = self._connect_to_whisper(self.dev_mode)
            
            # Connect to the TagalogAnalyzer service
            self.tagalog_analyzer = None if self.dev_mode else self._connect_to_tagalog_analyzer()
            
            # Initialize direct microphone access if Whisper stream not available
            if not self.dev_mode and self.whisper_socket is None and WHISPER_AVAILABLE:
                logger.info("Whisper stream not available, trying direct microphone access")
                self.whisper_model = self._initialize_whisper_model()
                if self.whisper_model:
                    logger.info("Direct microphone access enabled with Whisper model")
            
            # If in dev mode or no Whisper access at all, simulate tone detection
            if self.dev_mode or (self.whisper_socket is None and self.whisper_model is None):
                logger.info("Starting simulated tone detection")
                threading.Thread(target=self._simulate_tone_detection, daemon=True).start()
            
            while self.running:
                try:
                    if self.whisper_socket:
                        # Get data from Whisper stream
                        data = self.whisper_socket.recv_json()
                        if "partial_transcript" in data:
                            text = data["partial_transcript"]
                            
                            # Analyze the tone
                            detected_tone = self._analyze_tone(text, self.tagalog_analyzer)
                            
                            # Only log non-neutral tones or every 10th neutral tone
                            if detected_tone != "neutral" or int(time.time()) % 10 == 0:
                                language = self._detect_language(text)
                                logger.info(f"Detected tone: {detected_tone} in {language}: '{text}'")

                            # Add to tone queue for other components to use
                            if detected_tone != "neutral":  # Only queue non-neutral tones
                                try:
                                    # Non-blocking put with discard if full
                                    if not tone_queue.full():
                                        tone_queue.put({
                                            "tone": detected_tone,
                                            "text": text,
                                            "timestamp": time.time()
                                        }, block=False)
                                except Exception:
                                    pass  # Queue full, just discard
                            
                            # Update metrics for health check
                            self.last_detection_time = datetime.utcnow().isoformat()
                            self.processed_audio_chunks += 1
                    elif self.whisper_model:
                        # Use direct microphone access with Whisper
                        logger.info("Listening for speech via direct microphone...")
                        text = self._record_and_transcribe(self.whisper_model, seconds=5)
                        
                        if text and len(text.strip()) > 0:
                            # Analyze the tone
                            detected_tone = self._analyze_tone(text, self.tagalog_analyzer)
                            language = self._detect_language(text)
                            
                            # Log all direct transcriptions
                            logger.info(f"[DIRECT MIC] Detected tone: {detected_tone} in {language}: '{text}'")
                            
                            # Add to tone queue
                            try:
                                if not tone_queue.full():
                                    tone_queue.put({
                                        "tone": detected_tone,
                                        "text": text,
                                        "timestamp": time.time()
                                    }, block=False)
                            except Exception:
                                pass  # Queue full, just discard
                            
                            # Update metrics for health check
                            self.last_detection_time = datetime.utcnow().isoformat()
                            self.processed_audio_chunks += 1
                    else:
                        # No connection, sleep longer
                        time.sleep(5)
                except Exception as e:
                    logger.error(f"Error in tone detection: {e}")
                    time.sleep(5)
        except Exception as e:
            logger.error(f"Error starting tone monitor: {e}")
    
    def _connect_to_whisper(self, dev_mode):
        if dev_mode:
            logger.info("[DEV MODE] Simulating Whisper connection")
            return None
        
        try:
            # Use the partial transcripts port from streaming system
            context = None  # Using pool
            socket = get_sub_socket(endpoint).socket
            host = config.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
            socket.connect(f"tcp://{host}:5575")  # Partial transcripts port
            socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info("Connected to Whisper partial transcripts stream")
            return socket
        except Exception as e:
            logger.error(f"Failed to connect to Whisper stream: {e}")
            logger.info("Will try direct microphone access instead")
            return None
    
    def _initialize_whisper_model(self):
        if not WHISPER_AVAILABLE:
            logger.error("Cannot initialize Whisper model: required libraries not available")
            return None
        
        # Load LLM configuration to check for ENABLE_LEGACY_MODELS flag
        try:
            llm_config_path = get_file_path("main_pc_config", "llm_config.yaml")
            with open(llm_config_path, 'r') as f:
                llm_config = yaml.safe_load(f)
            ENABLE_LEGACY_MODELS = llm_config.get('global_flags', {}).get('ENABLE_LEGACY_MODELS', False)
            logger.info(f"ENABLE_LEGACY_MODELS flag set to: {ENABLE_LEGACY_MODELS}")
        except Exception as e:
            logger.error(f"Error loading llm_config.yaml: {e}")
            ENABLE_LEGACY_MODELS = False
            logger.info("Defaulting ENABLE_LEGACY_MODELS to False")
            
        if not ENABLE_LEGACY_MODELS:
            logger.warning("Direct model loading is disabled. Use model_client instead.")
            return None
        
        try:
            logger.info("Legacy mode: Loading Whisper model...")
            model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return None
    
    def _connect_to_tagalog_analyzer(self):
        try:
            context = None  # Using pool
            socket = get_req_socket(endpoint).socket
            socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            host = config.get("tagalog_analyzer_host", get_env("BIND_ADDRESS", "0.0.0.0"))
            port = config.get("tagalog_analyzer_port", 5707)
            socket.connect(f"tcp://{host}:{port}")  # TagalogAnalyzer service port
            logger.info("Connected to TagalogAnalyzer service")
            return socket
        except Exception as e:
            logger.error(f"Failed to connect to TagalogAnalyzer: {e}")
            return None
    
    def _detect_language(self, text):
        # More comprehensive Tagalog markers including common words and particles
        tagalog_markers = [
            # Common particles
            'ng', 'mga', 'na', 'sa', 'ang', 'ay', 'at', 'ko', 'mo', 'niya', 'namin', 'natin', 
            'nila', 'kayo', 'sila', 'po', 'opo', 'yung', 'iyong', 'yun', 'yan', 'ito', 'iyan',
            
            # Common verbs and their forms
            'ako', 'ikaw', 'siya', 'kami', 'tayo', 'kayo', 'sila',
            'gusto', 'ayaw', 'kailangan', 'dapat', 'pwede', 'puede', 'maaari',
            
            # Common Tagalog words
            'masaya', 'malungkot', 'maganda', 'pangit', 'mabuti', 'masama', 'araw', 'gabi',
            'ngayon', 'kahapon', 'bukas', 'salamat', 'pasensya', 'paumanhin', 'hindi', 'oo',
            
            # Prefixes highly specific to Tagalog
            'naka', 'maka', 'nag', 'mag', 'pina', 'paki', 'makiki', 'nakiki', 'nakaka', 'makaka'
        ]
        
        # Common Filipino name prefixes
        name_prefixes = ['ni', 'si', 'kay', 'nina', 'kina', 'nila']
        
        # Strong English indicators (common English words)
        english_markers = [
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'cannot', 'can\'t', 'don\'t', 'doesn\'t', 'didn\'t', 'won\'t', 'wouldn\'t'
        ]
        
        text_lower = text.lower()
        
        # Count Tagalog markers
        tagalog_count = sum(1 for marker in tagalog_markers if marker in text_lower)
        name_prefix_count = sum(1 for prefix in name_prefixes if prefix in text_lower)
        
        # Count English markers
        english_count = sum(1 for marker in english_markers if f" {marker} " in f" {text_lower} ")
        
        # Detect Tagalog-English code-switching
        words = re.findall(r'\b\w+\b', text_lower)
        total_words = len(words) if words else 1
        
        # Calculate language scores
        tagalog_score = (tagalog_count + name_prefix_count * 2) / total_words
        english_score = english_count / total_words
        
        # Determine language
        if tagalog_score > 0.2 and english_score > 0.1:
            return "Taglish"  # Code-switching
        elif tagalog_score > english_score:
            return "Tagalog"
        else:
            return "English"
    
    def _analyze_tone(self, text, tagalog_analyzer=None):
        # Detect language
        language = self._detect_language(text)
        
        # If Tagalog and we have a Tagalog analyzer, use it
        if language == "Tagalog" and tagalog_analyzer is not None:
            try:
                tagalog_analyzer.send_json({
                    "action": "analyze_tone",
                    "text": text
                })
                response = tagalog_analyzer.recv_json()
                if response.get("status") == "success":
                    return response.get("tone", "neutral")
            except Exception as e:
                logger.error(f"Error using TagalogAnalyzer: {e}")
        
        # For English or if Tagalog analyzer failed, use rule-based approach
        
        # Initialize scores for each tone
        scores = {tone: 0 for tone in TONE_CATEGORIES.keys()}
        
        # Frustrated tone markers
        frustrated_markers = [
            r'\b(argh|ugh|aargh|grr|hmph|tsk)\b',
            r'\b(not working|doesn\'t work|broken|useless|stupid|dumb|hate|annoying)\b',
            r'(!!+|\?!+)',
            r'\b(why (won\'t|can\'t|doesn\'t))\b',
            r'\b(so (annoying|frustrating))\b',
            r'\b(keep|keeps) (getting|having)\b',
            r'\b(tried|trying) (everything|several times)\b',
            r'\b(still|again) (not working|doesn\'t work)\b'
        ]
        
        # Confused tone markers
        confused_markers = [
            r'\b(confused|puzzled|unsure|uncertain|don\'t understand|not sure)\b',
            r'\b(what\'s happening|what is happening)\b',
            r'\b(how (do|does|did))\b',
            r'\b(why (is|are|does))\b',
            r'(\?{2,})',
            r'\b(lost|unclear|ambiguous)\b',
            r'\b(can\'t figure|can\'t tell)\b',
            r'\b(supposed to|meant to)\b'
        ]
        
        # Excited tone markers
        excited_markers = [
            r'\b(wow|amazing|awesome|great|excellent|fantastic|incredible|brilliant)\b',
            r'\b(love|adore|enjoy|appreciate)\b',
            r'(!{2,})',
            r'\b(so (good|great|amazing))\b',
            r'\b(can\'t wait|looking forward)\b',
            r'\b(thank you|thanks) (so much|a lot)\b',
            r'\b(exactly|perfect|precisely)\b',
            r'\b(yes|yep|yeah)!+'
        ]
        
        # Tired tone markers
        tired_markers = [
            r'\b(tired|exhausted|fatigued|drained|weary)\b',
            r'\b(need (a break|rest|sleep))\b',
            r'\b(been (working|trying) (for|all))\b',
            r'\b(so (long|much time))\b',
            r'\b(give up|too much)\b',
            r'(\.{3,})',
            r'\b(sigh|ugh|meh)\b',
            r'\b(not again|once more)\b'
        ]
        
        # Check each tone's markers
        for marker in frustrated_markers:
            if re.search(marker, text.lower()):
                scores["frustrated"] += 1
                
        for marker in confused_markers:
            if re.search(marker, text.lower()):
                scores["confused"] += 1
                
        for marker in excited_markers:
            if re.search(marker, text.lower()):
                scores["excited"] += 1
                
        for marker in tired_markers:
            if re.search(marker, text.lower()):
                scores["tired"] += 1
        
        # Find the highest scoring tone
        max_tone = max(scores.items(), key=lambda x: x[1])
        if max_tone[1] <= 0.5:  # If no strong indicators, default to neutral
            return "neutral"
        
        return max_tone[0]
    
    def _record_and_transcribe(self, whisper_model, seconds=5, device_index=None):
        if not WHISPER_AVAILABLE or whisper_model is None:
            return None
        
        try:
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            
            # Find a working microphone if device_index not specified
            if device_index is None:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        device_index = i
                        logger.info(f"Selected microphone: {info['name']} (index {i})")
                        break
            
            if device_index is None:
                logger.error("No microphone found")
                return None
            
            # Constants for audio recording
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000  # Whisper expects 16kHz
            
            # Open audio stream
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            input_device_index=device_index,
                            frames_per_buffer=CHUNK)
            
            logger.info(f"Recording {seconds} seconds of audio...")
            frames = []
            
            # Record audio
            for i in range(0, int(RATE / CHUNK * seconds)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            logger.info("Finished recording")
            
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Convert frames to numpy array
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe with Whisper
            logger.info("Transcribing audio...")
            result = whisper_model.transcribe(audio_data, language="en")
            transcription = result["text"].strip()
            logger.info(f"Transcription: {transcription}")
            
            return transcription
        except Exception as e:
            logger.error(f"Error in recording/transcription: {e}")
            return None
    
    def _simulate_tone_detection(self):
        samples = [
            {"tone": "frustrated", "text": "This isn't working, I've tried everything!"},
            {"tone": "confused", "text": "I don't understand why this keeps happening"},
            {"tone": "excited", "text": "Wow, that's exactly what I wanted!"},
            {"tone": "neutral", "text": "Let's continue with the next step"},
            {"tone": "tired", "text": "I've been working on this all day"}
        ]
        
        while self.running:
            # Choose a sample every 30 seconds
            import random
            sample = random.choice(samples)
            logger.info(f"[SIMULATED] Detected tone: {sample['tone']} in: '{sample['text']}'")
            
            # Add to tone queue
            try:
                if not tone_queue.full():
                    tone_queue.put({
                        "tone": sample["tone"],
                        "text": sample["text"],
                        "timestamp": time.time(),
                        "simulated": True
                    }, block=False)
            except Exception:
                pass
            
            # Update metrics for health check
            self.last_detection_time = datetime.utcnow().isoformat()
            self.processed_audio_chunks += 1
            
            # Random interval between 20-40 seconds
            time.sleep(random.uniform(20, 40))
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'get_tone':
            # Return the most recent tone detection
            try:
                if not tone_queue.empty():
                    tone_data = tone_queue.get_nowait()
                    return {
                        'status': 'success',
                        'tone': tone_data['tone'],
                        'text': tone_data['text'],
                        'timestamp': tone_data['timestamp']
                    }
                else:
                    return {
                        'status': 'success',
                        'tone': 'neutral',
                        'text': 'No recent tone detected',
                        'timestamp': time.time()
                    }
            except Exception as e:
                return {
                    'status': 'error',
                    'message': str(e)
                }
        else:
            return super().handle_request(request)
    
    def shutdown(self):
        """Gracefully shutdown the agent"""
        logger.info("Shutting down ToneDetector")
        self.running = False
        super().stop()
    
    def cleanup(self):
        """Clean up resources when the agent is stopping."""
        logger.info("Cleaning up resources...")
        
        # Set running flag to False to stop threads
        self.running = False
        
        try:
            # Join tone thread if it exists and is alive
            if hasattr(self, 'tone_thread') and self.tone_thread and self.tone_thread.is_alive():
                try:
                    self.tone_thread.join(timeout=2.0)
                    logger.info("Tone detection thread joined")
                except Exception as e:
                    logger.error(f"Error joining tone detection thread: {e}")
            
            # Close all ZMQ sockets
            for socket_name in ['whisper_socket', 'tagalog_analyzer', 'socket', 'error_bus_pub']:
                if hasattr(self, socket_name) and getattr(self, socket_name):
                    try:
                        getattr(self, socket_name).close()
                        logger.info(f"{socket_name} closed")
                    except Exception as e:
                        logger.error(f"Error closing {socket_name}: {e}")
            
            # Terminate ZMQ context
            if hasattr(self, 'context') and self.context:
                try:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
                    logger.info("ZMQ context terminated")
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")
            
            # Clean up whisper model if it exists
            if hasattr(self, 'whisper_model') and self.whisper_model:
                try:
                    # Free memory used by the model
                    if WHISPER_AVAILABLE and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    del self.whisper_model
                    logger.info("Whisper model resources freed")
                except Exception as e:
                    logger.error(f"Error cleaning up Whisper model: {e}")
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Call parent cleanup method
        super().cleanup()

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "detector_status": "active",
            "last_detection_time": getattr(self, 'last_detection_time', 'N/A'),
            "processed_audio_chunks": getattr(self, 'processed_audio_chunks', 0)
        }
        base_status.update(specific_metrics)
        return base_status

    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = self.running  # Assume healthy if running
            
            # Check if tone detection thread is functioning
            if hasattr(self, 'tone_thread') and not self.tone_thread.is_alive():
                is_healthy = False
                
            # Check if any sockets are initialized
            if hasattr(self, 'whisper_socket') and self.whisper_socket is None and \
               hasattr(self, 'whisper_model') and self.whisper_model is None:
                is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "dev_mode": self.dev_mode,
                    "processed_audio_chunks": self.processed_audio_chunks,
                    "last_detection_time": self.last_detection_time,
                    "whisper_connected": self.whisper_socket is not None,
                    "whisper_model_loaded": self.whisper_model is not None
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            logger.error(f"Health check failed with exception: {str(e)}")
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ToneDetector()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()