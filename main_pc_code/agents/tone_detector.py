from src.core.base_agent import BaseAgent
# Tone detection for Human Awareness Agent

import time
import logging
import threading
import zmq
import os
import json
from datetime import datetime
from queue import Queue
import re
import numpy as np
import wave
import sys
from typing import Dict, Any, Optional
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

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
        logging.FileHandler("logs/tone_detector.log"),
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

class ToneDetectorAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ToneDetectorAgent")
        
        # Initialize tone detection components
        self.dev_mode = kwargs.get('dev_mode', True)
        self.whisper_socket = None
        self.tagalog_analyzer = None
        self.whisper_model = None
        
        # Start tone monitoring in background
        self.tone_thread = threading.Thread(target=self._start_tone_monitor, daemon=True)
        self.tone_thread.start()
        
        logger.info(f"ToneDetectorAgent initialized on port {self.port}")
    
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
            context = zmq.Context()
            socket = context.socket(zmq.SUB)
            socket.connect(f"tcp://{_agent_args.host}:5575")  # Partial transcripts port
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
        
        try:
            logger.info("Loading Whisper model...")
            model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return None
    
    def _connect_to_tagalog_analyzer(self):
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            host = _agent_args.get('tagalog_analyzer_host', 'localhost')
            port = _agent_args.get('tagalog_analyzer_port', 5707)
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
        english_count = sum(1 for marker in english_markers if marker in text_lower)
        
        # Determine language based on marker counts
        if tagalog_count > 0 or name_prefix_count > 0:
            if english_count > tagalog_count:
                return "Taglish"  # Mixed Tagalog-English
            else:
                return "Tagalog"
        else:
            return "English"
    
    def _analyze_tone(self, text, tagalog_analyzer=None):
        # Detect language
        language = self._detect_language(text)
        
        # If Tagalog/Taglish and TagalogAnalyzer is available, use it
        if language in ["Tagalog", "Taglish"] and tagalog_analyzer:
            try:
                # Send text to TagalogAnalyzer for analysis
                tagalog_analyzer.send_json({
                    "action": "analyze_sentiment_and_intent",
                    "text": text
                })
                response = tagalog_analyzer.recv_json()
                
                if response.get("status") == "ok":
                    sentiment = response.get("sentiment", {})
                    intent = response.get("intent", {})
                    
                    # Get sentiment label
                    sentiment_label = sentiment.get("label", "neutral")
                    
                    # Check for question patterns (indicates confusion)
                    question_score = intent.get("question", 0.0)
                    if question_score > 0.7 and "bakit" in text.lower():
                        return "confused"  # Questions with "bakit" (why) usually indicate confusion
                    
                    # Check for negative statements (indicates frustration)
                    negative_score = intent.get("negative", 0.0)
                    if negative_score > 0.5 or sentiment_label == "negative":
                        return "frustrated"
                    
                    # Check for positive sentiment (indicates excitement)
                    if sentiment_label == "positive":
                        positive_score = sentiment.get("positive", 0.0)
                        if positive_score > 0.6:
                            return "excited"  # Strong positive sentiment indicates excitement
                        else:
                            return "neutral"  # Mild positive sentiment might just be neutral tone
                    
                    # Default to neutral if no strong indicators
                    return "neutral"
                else:
                    logger.warning(f"TagalogAnalyzer error: {response.get('message')}")
                    # Fall back to keyword approach
            except Exception as e:
                logger.error(f"Error using TagalogAnalyzer: {e}")
                # Fall back to keyword approach
        
        # English text or fallback for Tagalog
        text = text.lower()
        
        # Enhanced keyword-based detection for better accuracy
        indicators = {
            "frustrated": [
                "can't", "not working", "doesn't work", "stupid", "annoying", "frustrated", "argh", "ugh",
                "terrible", "awful", "hate", "useless", "broken", "failed", "failing", "failure", "error", 
                "errors", "problem", "disaster", "horrible", "impossible", "ridiculous", "angry", "upset",
                "bad", "wrong", "not right", "buggy", "bugs"
            ],
            "confused": [
                "don't understand", "confused", "how do i", "what's happening", "why isn't", "not sure",
                "unclear", "confusing", "complicated", "complex", "lost", "puzzled", "unsure", "uncertain",
                "what does this mean", "don't get it", "no idea", "i'm lost", "strange", "weird", "odd", 
                "doesn't make sense", "hard to follow", "not following", "can't figure out", "why is", "how is", "what is"
            ],
            "excited": [
                "great", "awesome", "excellent", "perfect", "nice", "love it", "wow", "amazing", "brilliant",
                "fantastic", "wonderful", "delighted", "happy", "glad", "thrilled", "impressed", "incredible",
                "superb", "outstanding", "remarkable", "spectacular", "terrific", "fabulous", "marvelous",
                "joy", "exciting", "excited", "pleasure", "pleased", "satisfaction", "satisfied", "lovely",
                "cool", "super", "fantastic", "love", "really good", "impressive", "gorgeous", "beautiful"
            ],
            "tired": [
                "tired", "exhausted", "too much", "need a break", "long day", "fatigued", "worn out", 
                "drained", "sleepy", "drowsy", "weary", "beat", "spent", "burned out", "overworked",
                "need rest", "need sleep", "exhausting", "draining", "tedious", "boring", "can't focus"
            ]
        }
        
        # Check for indicators
        scores = {category: 0 for category in TONE_CATEGORIES.keys()}
        scores["neutral"] = 1  # Default score
        
        for tone, keywords in indicators.items():
            for keyword in keywords:
                if keyword in text:
                    scores[tone] += 1
                    scores["neutral"] -= 0.2  # Reduce neutral score when other emotions detected
        
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
        logger.info("Shutting down ToneDetectorAgent")
        self.running = False
        super().stop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5625)
    args = parser.parse_args()
    agent = ToneDetectorAgent(port=args.port)
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        agent.shutdown()
