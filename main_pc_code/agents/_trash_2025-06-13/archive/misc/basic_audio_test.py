from main_pc_code.src.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
"""
Basic Audio Test - Simplified version of listener.py for debugging
This script focuses only on audio capture and basic processing.
"""

import os
import sys
import time
import json
import logging
import numpy as np
import sounddevice as sd
from datetime import datetime
from scipy.io import wavfile


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Set up basic logging
logger = configure_logging(__name__)
logger = logging.getLogger("BasicAudioTest")

# Constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500
SILENCE_TIMEOUT = 30
RECORD_SECONDS = 5  # Record for fixed 5 seconds for testing

# Create logs directory if it doesn't exist
LOG_DIR = get_path("logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Print all input devices for manual selection
print("Available audio input devices:")
try:
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device["max_input_channels"] > 0:  # Only show input devices
            display_name = device["name"]
            print(f'  [{idx}] {display_name} (channels: {device["max_input_channels"]})')
except Exception as e:
    print(f"Error listing devices: {e}")

# Device selection - using DirectSound API (Index 18)
DEVICE_INDEX = 18  # SteelSeries Sonar - Microphone (SteelSeries Sonar Virtual Audio Device)
print(f"Using device index: {DEVICE_INDEX}")

try:
    device_info = sd.query_devices(DEVICE_INDEX)
    print(f"Device info: {json.dumps(device_info, indent=2)}")
    
    if device_info['max_input_channels'] <= 0:
        print(f"WARNING: Device {DEVICE_INDEX} has no input channels! Please check selection.")
        # sys.exit(1)
    else:
        print(f"Using Device: {DEVICE_INDEX} - {device_info['name']} (Input Channels: {device_info['max_input_channels']}, Default SR: {device_info['default_samplerate']})")
except Exception as e:
    print(f"Error getting device info: {e}")
    # sys.exit(1)

def record_audio(duration=5, device_index=DEVICE_INDEX):
    """Record audio for a fixed duration"""
    print(f"Recording {duration} seconds of audio from device {device_index}...")
    
    try:
        # Get device info
        device_info = sd.query_devices(device_index)
        samplerate = int(device_info["default_samplerate"])
        channels = min(1, device_info["max_input_channels"])  # Use mono for processing
        
        # Calculate frames
        frames = int(samplerate * duration)
        
        # Record audio
        print("Starting recording...")
        audio_data = sd.rec(frames, samplerate=samplerate, channels=channels, dtype='float32', device=device_index)
        
        # Wait for recording to complete
        print("Recording in progress...")
        sd.wait()
        print("Recording completed!")
        
        # Convert to mono if needed
        if channels > 1:
            audio_data = audio_data.mean(axis=1)
        
        # Calculate RMS to check if we captured audio
        rms = np.sqrt(np.mean(audio_data**2)) * 32768  # Scale to int16 range
        print(f"Audio RMS: {rms}")
        
        # Save the audio file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(LOG_DIR, f"test_audio_{timestamp}.wav")
        
        # Convert to int16 for saving
        audio_int16 = (audio_data * 32768).astype(np.int16)
        
        # Resample to 16kHz if needed
        if samplerate != SAMPLE_RATE:
            print(f"Resampling from {samplerate}Hz to {SAMPLE_RATE}Hz")
            # Simple resampling - in production use a proper resampling library
            ratio = SAMPLE_RATE / samplerate
            audio_int16 = np.interp(
                np.arange(0, len(audio_int16) * ratio),
                np.arange(0, len(audio_int16) * ratio, ratio),
                audio_int16
            ).astype(np.int16)
        
        # Save the file
        wavfile.write(output_file, SAMPLE_RATE, audio_int16)
        print(f"Audio saved to {output_file}")
        
        return True
    
    except Exception as e:
        print(f"Error recording audio: {e}")
        return False

def stream_audio(duration=10, device_index=DEVICE_INDEX):
    """Stream audio and process in chunks"""
    print(f"Streaming audio for {duration} seconds from device {device_index}...")
    
    try:
        # Get device info
        device_info = sd.query_devices(device_index)
        samplerate = int(device_info["default_samplerate"])
        channels = min(1, device_info["max_input_channels"])  # Use mono for processing
        
        # Calculate frames per buffer (100ms chunks)
        frames_per_buffer = int(samplerate * 0.1)
        
        # Open audio stream
        print("Opening audio stream...")
        stream = sd.InputStream(
            samplerate=samplerate,
            device=device_index,
            channels=channels,
            callback=None,
            blocksize=frames_per_buffer
        )
        
        print("Audio stream created, starting stream")
        stream.start()
        
        # Variables for audio processing
        audio_buffer = []
        start_time = time.time()
        
        print("Entering main loop")
        while time.time() - start_time < duration:
            # Read audio data
            try:
                audio_data, overflowed = stream.read(frames_per_buffer)
                if overflowed:
                    print("WARNING: Audio buffer overflow")
                
                # Convert to mono and calculate RMS
                audio_mono = audio_data.mean(axis=1) if audio_data.ndim > 1 else audio_data
                rms = np.sqrt(np.mean(audio_mono**2)) * 32768  # Scale to int16 range
                print(f"Chunk RMS: {rms}")
                
                # Add to buffer
                audio_buffer.append(audio_mono)
                
                # Sleep a bit to reduce CPU usage
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                break
        
        # Clean up
        print("Stopping stream")
        stream.stop()
        stream.close()
        
        # Process collected audio
        if audio_buffer:
            print("Processing collected audio")
            full_audio = np.concatenate(audio_buffer)
            
            # Save the audio file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(LOG_DIR, f"stream_audio_{timestamp}.wav")
            
            # Convert to int16 for saving
            audio_int16 = (full_audio * 32768).astype(np.int16)
            
            # Resample to 16kHz if needed
            if samplerate != SAMPLE_RATE:
                print(f"Resampling from {samplerate}Hz to {SAMPLE_RATE}Hz")
                ratio = SAMPLE_RATE / samplerate
                audio_int16 = np.interp(
                    np.arange(0, len(audio_int16) * ratio),
                    np.arange(0, len(audio_int16) * ratio, ratio),
                    audio_int16
                ).astype(np.int16)
            
            # Save the file
            wavfile.write(output_file, SAMPLE_RATE, audio_int16)
            print(f"Audio saved to {output_file}")
        
        return True
    
    except Exception as e:
        print(f"Error streaming audio: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Basic Audio Test ===")
    print("1. Testing simple audio recording...")
    success = record_audio(5, DEVICE_INDEX)
    
    if success:
        print("\n2. Testing audio streaming...")
        stream_audio(10, DEVICE_INDEX)
    
    print("\n=== Test Completed ===")
    print("Check the logs directory for saved audio files.")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
