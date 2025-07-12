from main_pc_code.src.core.base_agent import BaseAgent
"""
Simple Whisper test script
Records audio from the microphone and transcribes it using Whisper
"""

import os
import sys
import wave
import pyaudio
import numpy as np
import whisper
from datetime import datetime


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
WHISPER_SAMPLE_RATE = 16000
OUTPUT_DIR = get_path("logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def record_and_transcribe(device_index=4, seconds=5, language="en"):
    """Record audio from the specified device and transcribe it using Whisper"""
    p = pyaudio.PyAudio()
    
    # Print device info
    print(f"Using device index: {device_index}")
    try:
        device_info = p.get_device_info_by_index(device_index)
        print(f"Device name: {device_info['name']}")
        print(f"Max input channels: {device_info['maxInputChannels']}")
        print(f"Default sample rate: {device_info['defaultSampleRate']}")
    except Exception as e:
        print(f"Error getting device info: {e}")
        return False
    
    # Open audio stream
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK)
        
        print(f"Recording {seconds} seconds of audio...")
        frames = []
        
        # Record audio
        for i in range(0, int(RATE / CHUNK * seconds)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Print audio level every 10 chunks
            if i % 10 == 0:
                audio_data = np.frombuffer(data, dtype=np.int16)
                rms = np.sqrt(np.mean(np.square(audio_data)))
                print(f"Audio level: {rms:.2f}")
        
        print("Recording finished")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save the recorded audio as a WAV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"whisper_test_{timestamp}.wav")
        
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"Audio saved to {output_file}")
        
        # Convert audio data to numpy array
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        
        # Resample to 16kHz for Whisper
        if RATE != WHISPER_SAMPLE_RATE:
            print(f"Resampling from {RATE}Hz to {WHISPER_SAMPLE_RATE}Hz")
            # Simple resampling using numpy
            duration = len(audio_data) / RATE
            new_length = int(duration * WHISPER_SAMPLE_RATE)
            x_old = np.linspace(0, duration, len(audio_data))
            x_new = np.linspace(0, duration, new_length)
            audio_data = np.interp(x_new, x_old, audio_data)
        
        # Print audio stats
        print(f"Audio data shape: {audio_data.shape}, dtype: {audio_data.dtype}")
        print(f"Audio min: {audio_data.min()}, max: {audio_data.max()}, mean: {audio_data.mean()}")
        
        # Normalize audio
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val
            print(f"Normalized audio. New min: {audio_data.min()}, max: {audio_data.max()}")
        
        # Load Whisper model
        print("Loading Whisper model...")
        model = whisper.load_model("base")
        print("Whisper model loaded successfully")
        
        # Transcribe audio
        print(f"Transcribing audio (language: {language})...")
        result = model.transcribe(
            audio_data,
            language=language,
            fp16=False,
            verbose=True
        )
        
        # Print transcription result
        transcription = result["text"].strip()
        print(f"Transcription result: '{transcription}'")
        
        return transcription
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if 'stream' in locals() and stream:
            stream.stop_stream()
            stream.close()
        if 'p' in locals() and p:
            p.terminate()
        return False

if __name__ == "__main__":
    print("=== Simple Whisper Test ===")
    
    # Try with English first
    print("\nTesting with English:")
    print("Please speak in English for 5 seconds after seeing 'Recording...'")
    input("Press Enter to start recording...")
    transcription_en = record_and_transcribe(device_index=4, seconds=5, language="en")
    
    if transcription_en:
        print(f"\nEnglish transcription: '{transcription_en}'")
    
    # Then try with Tagalog
    print("\nTesting with Tagalog:")
    print("Please speak in Tagalog for 5 seconds after seeing 'Recording...'")
    input("Press Enter to start recording...")
    transcription_tl = record_and_transcribe(device_index=4, seconds=5, language="tl")
    
    if transcription_tl:
        print(f"\nTagalog transcription: '{transcription_tl}'")
    
    print("\nTest completed.")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
