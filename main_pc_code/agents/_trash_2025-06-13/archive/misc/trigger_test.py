"""
Trigger word test script
Tests if the Whisper model can recognize a specific trigger word
"""

import os
import sys
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper
from datetime import datetime


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Constants
DEVICE_INDEX = 39  # SteelSeries Sonar - Microphone (WASAPI)
SAMPLE_RATE = 48000  # Device's native sample rate
CHANNELS = 1
DURATION = 5  # seconds
WHISPER_SAMPLE_RATE = 16000  # Whisper expects 16kHz audio
OUTPUT_DIR = get_path("logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Trigger words to test
TRIGGER_WORDS = [
    "Hey Assistant",
    "Computer",
    "Jarvis",
    "Hello",
    "Testing"
]

def record_audio():
    """Record audio from the specified device and save it as a WAV file"""
    try:
        # Get device info
        device_info = sd.query_devices(DEVICE_INDEX)
        print(f"Using device: {device_info['name']} (Index: {DEVICE_INDEX})")
        
        # Set up recording parameters
        channels = min(CHANNELS, device_info["max_input_channels"])
        samplerate = int(device_info["default_samplerate"])
        
        print(f"Recording {DURATION} seconds of audio...")
        print(f"Using settings: channels={channels}, samplerate={samplerate}")
        
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
        print(f"Audio stats: RMS={rms:.4f}")
        
        # Save the recorded audio as a WAV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"trigger_test_{timestamp}.wav")
        
        sf.write(output_file, recording, samplerate)
        print(f"Audio saved to {output_file}")
        
        return output_file, recording, samplerate
    
    except Exception as e:
        print(f"Error recording audio: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def transcribe_and_check_trigger(audio_file):
    """Transcribe audio and check if it contains a trigger word"""
    try:
        print("\nLoading Whisper model...")
        model = whisper.load_model("base")
        print("Whisper model loaded successfully")
        
        print(f"Transcribing audio file: {audio_file}")
        
        # Transcribe directly from file
        result = model.transcribe(
            audio_file,
            language="en",
            fp16=False
        )
        
        transcription = result["text"].strip()
        print(f"\nTranscription: '{transcription}'")
        
        # Check if any trigger word is in the transcription
        found_trigger = False
        for trigger in TRIGGER_WORDS:
            if trigger.lower() in transcription.lower():
                print(f"\n✅ TRIGGER WORD DETECTED: '{trigger}'")
                found_trigger = True
                break
        
        if not found_trigger:
            print("\n❌ No trigger word detected in transcription")
        
        return transcription
    
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_trigger_test():
    """Run a complete trigger word test"""
    print("\n=== TRIGGER WORD TEST ===")
    print("This test will check if the Whisper model can recognize trigger words.")
    print("Available trigger words to test:")
    for i, trigger in enumerate(TRIGGER_WORDS):
        print(f"  {i+1}. {trigger}")
    
    print("\nInstructions:")
    print("1. Choose a trigger word from the list above")
    print("2. When recording starts, say the trigger word clearly")
    print("3. The script will check if the trigger word was recognized")
    
    input("\nPress Enter to start recording...")
    
    # Record audio
    audio_file, _, _ = record_audio()
    
    if audio_file:
        # Transcribe and check for trigger
        transcription = transcribe_and_check_trigger(audio_file)
        
        if transcription:
            print("\nTest completed.")
            
            # Ask if user wants to try again
            try_again = input("\nDo you want to try again? (y/n): ").strip().lower()
            if try_again == "y":
                run_trigger_test()
        else:
            print("\nTranscription failed.")
    else:
        print("\nRecording failed.")

if __name__ == "__main__":
    print("=== Trigger Word Recognition Test ===")
    
    # Run the trigger test
    run_trigger_test()
