from src.core.base_agent import BaseAgent
"""
Simple script to record audio and transcribe it using Whisper
"""

import os
import sys
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper
from datetime import datetime

# Constants
DEVICE_INDEX = 39  # SteelSeries Sonar - Microphone (WASAPI)
SAMPLE_RATE = 48000  # Device's native sample rate
CHANNELS = 1
DURATION = 5  # seconds
WHISPER_SAMPLE_RATE = 16000  # Whisper expects 16kHz audio
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def record_audio():
    """Record audio from the specified device and save it as a WAV file"""
    try:
        # Get device info
        device_info = sd.query_devices(DEVICE_INDEX)
        print(f"Using device: {device_info['name']} (Index: {DEVICE_INDEX})")
        print(f"Max input channels: {device_info['max_input_channels']}")
        print(f"Default sample rate: {device_info['default_samplerate']}")
        
        # Set up recording parameters
        channels = min(CHANNELS, device_info["max_input_channels"])
        samplerate = int(device_info["default_samplerate"])
        
        print(f"Recording {DURATION} seconds of audio...")
        print(f"Using settings: channels={channels}, samplerate={samplerate}")
        print("Speak clearly and at a normal volume...")
        
        # Record audio
        recording = sd.rec(
            int(DURATION * samplerate),
            samplerate=samplerate,
            channels=channels,
            dtype='float32',
            device=DEVICE_INDEX,
            blocking=True  # Wait until recording is finished
        )
        
        print("Recording finished")
        
        # Calculate audio stats
        rms = np.sqrt(np.mean(recording**2))
        print(f"Audio stats: shape={recording.shape}, min={recording.min():.4f}, max={recording.max():.4f}, RMS={rms:.4f}")
        
        # Save the recorded audio as a WAV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"speech_{timestamp}.wav")
        
        sf.write(output_file, recording, samplerate)
        print(f"Audio saved to {output_file}")
        
        return output_file, recording, samplerate
    
    except Exception as e:
        print(f"Error recording audio: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def transcribe_audio(audio_file, audio_data=None, sample_rate=None):
    """Transcribe audio using Whisper model"""
    try:
        print("\nLoading Whisper model...")
        model = whisper.load_model("base")
        print("Whisper model loaded successfully")
        
        print(f"Transcribing audio file: {audio_file}")
        
        # Transcribe directly from file
        result_from_file = model.transcribe(
            audio_file,
            language="en",
            fp16=False,
            verbose=True
        )
        
        print(f"\nTranscription from file: '{result_from_file['text'].strip()}'")
        
        # If we have audio data, also transcribe from memory
        if audio_data is not None and sample_rate is not None:
            print("\nResampling audio data for in-memory transcription...")
            # Resample to 16kHz for Whisper
            if sample_rate != WHISPER_SAMPLE_RATE:
                # Use numpy's interp function for simple resampling
                duration = len(audio_data) / sample_rate
                x_old = np.linspace(0, duration, len(audio_data))
                x_new = np.linspace(0, duration, int(duration * WHISPER_SAMPLE_RATE))
                
                # Handle multi-channel audio
                if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                    resampled_audio = np.zeros((len(x_new), audio_data.shape[1]), dtype=np.float32)
                    for channel in range(audio_data.shape[1]):
                        resampled_audio[:, channel] = np.interp(x_new, x_old, audio_data[:, channel])
                else:
                    # Flatten if needed
                    if len(audio_data.shape) > 1:
                        audio_data = audio_data.flatten()
                    resampled_audio = np.interp(x_new, x_old, audio_data)
            else:
                resampled_audio = audio_data
            
            print(f"Resampled audio shape: {resampled_audio.shape}")
            
            # Normalize audio
            max_val = np.max(np.abs(resampled_audio))
            if max_val > 0:
                resampled_audio = resampled_audio / max_val
                print(f"Normalized audio. New min: {resampled_audio.min():.4f}, max: {resampled_audio.max():.4f}")
            
            print("\nTranscribing from memory...")
            result_from_memory = model.transcribe(
                resampled_audio,
                language="en",
                fp16=False,
                verbose=True
            )
            
            print(f"\nTranscription from memory: '{result_from_memory['text'].strip()}'")
        
        return True
    
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Record and Transcribe Test ===")
    
    # Record audio
    audio_file, audio_data, sample_rate = record_audio()
    
    if audio_file:
        print("\nRecording successful!")
        
        # Transcribe audio
        success = transcribe_audio(audio_file, audio_data, sample_rate)
        
        if success:
            print("\nTranscription completed successfully.")
            print("\nTest completed. Please check the transcription results above.")
        else:
            print("\nTranscription failed.")
    else:
        print("\nRecording failed.")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
