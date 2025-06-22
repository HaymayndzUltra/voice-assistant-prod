from src.core.base_agent import BaseAgent
"""
Speech Processor
--------------
Handles speech recognition and processing after wake word detection:
- Real-time speech recognition
- Continuous audio processing
- Command extraction
- Intent detection
"""

import pyaudio
import numpy as np
import json
import os
import logging
import threading
import queue
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
import whisper
import torch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('speech_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SpeechProcessor(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SpeechProcessor")
        """
        Initialize the speech processor.
        
        Args:
            model_name: Whisper model name (tiny, base, small, medium, large)
            sample_rate: Audio sample rate
            channels: Number of audio channels
            chunk_size: Audio chunk size
            silence_threshold: Threshold for silence detection
            silence_duration: Duration of silence to consider speech ended
            callback: Function to call when speech is processed
        """
        self.model_name = model_name
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.callback = callback
        
        # Initialize state
        self.is_running = False
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.last_audio_time = None
        
        # Initialize Whisper
        self._init_whisper()
        
        # Initialize audio
        self._init_audio()
        
        logger.info("Speech processor initialized")
    
    def _init_whisper(self):
        """Initialize Whisper model."""
        try:
            self.model = whisper.load_model(self.model_name)
            logger.info(f"Whisper model {self.model_name} loaded")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {str(e)}")
            raise
    
    def _init_audio(self):
        """Initialize PyAudio for audio capture."""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                rate=self.sample_rate,
                channels=self.channels,
                format=pyaudio.paFloat32,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            logger.info("Audio stream initialized")
        except Exception as e:
            logger.error(f"Error initializing audio: {str(e)}")
            raise
    
    def _calculate_energy(self, audio_data: np.ndarray) -> float:
        """Calculate audio energy level."""
        try:
            return np.sqrt(np.mean(np.square(audio_data)))
        except Exception as e:
            logger.error(f"Error calculating energy: {str(e)}")
            return 0.0
    
    def _audio_capture_thread(self):
        """Thread for capturing audio."""
        audio_buffer = []
        
        while self.is_running:
            try:
                if not self.is_listening:
                    time.sleep(0.1)
                    continue
                
                # Read audio data
                audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
                energy = self._calculate_energy(audio_array)
                
                # Check for silence
                if energy < self.silence_threshold:
                    if self.last_audio_time and (time.time() - self.last_audio_time) > self.silence_duration:
                        if audio_buffer:
                            # Process the complete audio
                            self._process_audio(audio_buffer)
                            audio_buffer = []
                            self.is_listening = False
                else:
                    audio_buffer.append(audio_array)
                    self.last_audio_time = time.time()
                
            except Exception as e:
                logger.error(f"Error in audio capture: {str(e)}")
                time.sleep(0.1)
    
    def _process_audio(self, audio_buffer: list):
        """Process the complete audio buffer."""
        try:
            # Concatenate audio chunks
            audio_data = np.concatenate(audio_buffer)
            
            # Convert to the format expected by Whisper
            audio_data = (audio_data * 32768).astype(np.int16)
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_data,
                language="en",
                task="transcribe"
            )
            
            # Extract text and confidence
            text = result["text"].strip()
            confidence = result.get("confidence", 0.0)
            
            # Create result dictionary
            result_dict = {
                'timestamp': datetime.now().isoformat(),
                'text': text,
                'confidence': confidence
            }
            
            # Call callback if provided
            if self.callback:
                self.callback(result_dict)
            
            logger.info(f"Speech processed: {text}")
            
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
    
    def start_listening(self):
        """Start listening for speech."""
        self.is_listening = True
        self.last_audio_time = time.time()
        logger.info("Started listening for speech")
    
    def stop_listening(self):
        """Stop listening for speech."""
        self.is_listening = False
        logger.info("Stopped listening for speech")
    
    def start(self):
        """Start the speech processor."""
        if not self.is_running:
            self.is_running = True
            
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._audio_capture_thread)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            logger.info("Speech processor started")
    
    def stop(self):
        """Stop the speech processor."""
        if self.is_running:
            self.is_running = False
            self.is_listening = False
            
            # Wait for thread to finish
            if hasattr(self, 'capture_thread'):
                self.capture_thread.join()
            
            # Clean up resources
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            
            logger.info("Speech processor stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

if __name__ == "__main__":
    # Example usage
    def on_speech_processed(result: Dict[str, Any]):
        print(f"Speech detected: {result['text']}")
        print(f"Confidence: {result['confidence']:.2f}")
    
    processor = SpeechProcessor(
        model_name="base",
        callback=on_speech_processed
    )
    
    try:
        processor.start()
        print("Speech processor running. Press Ctrl+C to stop.")
        
        # Simulate wake word detection
        processor.start_listening()
        time.sleep(5)  # Listen for 5 seconds
        processor.stop_listening()
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping speech processor...")
    finally:
        processor.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
