print('[DEBUG] tts_agent.py script started')
import sys
import logging
import importlib
import re

# Add path_env import for containerization-friendly paths
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
from common.utils.path_manager import PathManager

# Import sounddevice configuration module to ensure correct device settings
try:
from main_pc_code.agents.sd_config import DEVICE_INDEX, SAMPLE_RATE
    except ImportError as e:
        print(f"Import error: {e}")
    print(f'[DEBUG] Imported sounddevice config: Device {DEVICE_INDEX} at {SAMPLE_RATE} Hz')
except ImportError:
    print('[DEBUG] Could not import sd_config module, using default sounddevice settings')

# Monkey-patch torch.load to default weights_only=False for Bark TTS compatibility
try:
    import torch
    except ImportError as e:
        print(f"Import error: {e}")
    _orig_torch_load = torch.load
    def patched_torch_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _orig_torch_load(*args, **kwargs)
    torch.load = patched_torch_load
    print('[DEBUG] Monkey-patched torch.load to default weights_only=False')
except Exception as e:
    print(f'[DEBUG] Could not monkey-patch torch.load: {e}')

# Patch for Bark TTS + PyTorch 2.6+ weights_only error
try:
    import torch
    except ImportError as e:
        print(f"Import error: {e}")
    import numpy
    torch.serialization.add_safe_globals([numpy.core.multiarray.scalar])
    torch.serialization.add_safe_globals([numpy.dtype])
    print('[DEBUG] Patched torch to allow numpy.core.multiarray.scalar and numpy.dtype for Bark TTS.')
except Exception as e:
    print(f'[DEBUG] Could not patch torch safe_globals: {e}')

# XTTS integration as primary TTS engine
import os
import sys

# Add Python site-packages to path to ensure TTS can be found
python_path = os.path.dirname(sys.executable)
site_packages = os.path.join(python_path, 'Lib', 'site-packages')
if site_packages not in sys.path:
    sys.path.append(site_packages)
    print(f"[DEBUG] Added {site_packages} to sys.path")

import torch
import numpy as np
from scipy.io.wavfile import write as write_wav
import time
try:
    from TTS.api import TTS
    except ImportError as e:
        print(f"Import error: {e}")
    print(f"[DEBUG] Imported TTS from: {TTS.__module__}")
    try:
        print(f"[DEBUG] TTS file: {TTS.__file__}")
    except AttributeError:
        pass
except ImportError as e:
    print(f"[XTTS] Import error: {e}")
    TTS = None
import sounddevice as sd

def xtts_speak(text, voice_sample_path=None, language="en"):
    """Generate and play speech using XTTS with a specific voice sample."""
    if TTS is None:
        print("[XTTS] TTS library not available.")
        return False
    print(f"[XTTS] Generating speech for: '{text}'")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        # Use a known XTTS model directly instead of searching
        xtts_model = "tts_models/multilingual/multi-dataset/xtts_v2"
        print(f"[XTTS] Using model: {xtts_model} on {device}")
        
        # Use GPU if available with appropriate settings
        if device == "cuda":
            tts = TTS(xtts_model, gpu=True)
        else:
            tts = TTS(xtts_model)
        
        # Always use the user's provided default sample if none is given
        import os
        if not voice_sample_path:
            voice_sample_path = PathManager.join_path("data", "voice_samples", "voice.wav")
        
        # Check if voice sample exists
        if voice_sample_path and os.path.isfile(voice_sample_path):
            print(f"[XTTS] Using provided voice sample: {voice_sample_path}")
            voice_samples = [voice_sample_path]
        else:
            print("[XTTS] ⚠️ No valid voice sample found at path: {voice_sample_path}")
            print("[XTTS] Using default model voice instead.")
            voice_samples = None
            # Return early as this will likely fail
            return False
        
        # Force language to 'en' if not supported by XTTS
        supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']
        if language not in supported_languages:
            print(f"[XTTS] Language '{language}' not supported. Using 'en' instead.")
            language = "en"
        
        # Set a default speaker name for multi-speaker models
        # This fixes the "Model is multi-speaker but no speaker is provided" error
        speaker = "default_speaker"
        
        # Generate speech - note the added speaker parameter
        print(f"[XTTS] Generating with: text='{text[:30]}...', language='{language}', speaker='{speaker}'")
        wav = tts.tts(
            text=text, 
            speaker_wav=voice_samples,
            language=language,
            speaker=speaker  # Add the required speaker parameter
        )
        
        # Play the audio
        sd.play(wav, samplerate=24000)
        sd.wait()
        print("[XTTS] ✓ Playback finished successfully.")
        return True
    except Exception as e:
        print(f"[XTTS] ❌ Error: {e}")
        import traceback
        print(f"[XTTS] Stack trace: {traceback.format_exc()}")
        return False

# pyttsx3 fallback
try:
    import pyttsx3
    except ImportError as e:
        print(f"Import error: {e}")
    def pyttsx3_speak(text):
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
        return True
except ImportError:
    pyttsx3_speak = None

# Emotion-based speech parameters
EMOTION_PARAMS = {
    "happy": {
        "rate": 1.1,       # Slightly faster
        "volume": 1.0,     # Normal volume
        "pitch": 1.1,      # Slightly higher pitch
        "speaker": "v2/en_speaker_6",  # Cheerful voice for Bark
        "energy": 1.2      # More energetic
    },
    "sad": {
        "rate": 0.9,       # Slower
        "volume": 0.8,     # Quieter
        "pitch": 0.9,      # Lower pitch
        "speaker": "v2/en_speaker_9",  # Melancholic voice for Bark
        "energy": 0.8      # Less energetic
    },
    "angry": {
        "rate": 1.1,       # Slightly faster
        "volume": 1.2,     # Louder
        "pitch": 1.0,      # Normal pitch
        "speaker": "v2/en_speaker_8",  # Stern voice for Bark
        "energy": 1.5      # More energetic
    },
    "surprised": {
        "rate": 1.2,       # Faster
        "volume": 1.1,     # Slightly louder
        "pitch": 1.2,      # Higher pitch
        "speaker": "v2/en_speaker_3",  # Expressive voice for Bark
        "energy": 1.3      # More energetic
    },
    "neutral": {
        "rate": 1.0,       # Normal rate
        "volume": 1.0,     # Normal volume
        "pitch": 1.0,      # Normal pitch
        "speaker": "v2/en_speaker_6",  # Default voice for Bark
        "energy": 1.0      # Normal energy
    },
    "filipino": {
        "rate": 1.0,       # Normal rate
        "volume": 1.0,     # Normal volume
        "pitch": 1.0,      # Normal pitch
        "speaker": "v2/fil_speaker_1",  # Filipino voice (if available)
        "energy": 1.0      # Normal energy
    }
}

# Import the TTS cache system
try:
    # Try to import from current directory first
    try:
        from tts_cache import get_cached_audio, add_to_cache, play_cached_audio, clear_cache
    except ImportError as e:
        print(f"Import error: {e}")
        has_cache_system = True
        print("[TTS] Audio caching system loaded successfully from current directory")
    except ImportError:
        # Then try from agents package
from main_pc_code.agents.tts_cache import get_cached_audio, add_to_cache, play_cached_audio, clear_cache
        has_cache_system = True
        print("[TTS] Audio caching system loaded successfully from agents package")
except ImportError as e:
    print(f"[TTS] Audio caching system not available: {e}")
    has_cache_system = False

def detect_emotion_from_text(text):
    """Simple rule-based emotion detection from text"""
    text = text.lower()
    
    # Simple keyword-based emotion detection
    happy_keywords = ['happy', 'great', 'excellent', 'wonderful', 'joy', 'yay', 'woohoo', 'congratulations']
    sad_keywords = ['sad', 'sorry', 'unfortunate', 'regret', 'disappointed', 'miss', 'grief']
    angry_keywords = ['angry', 'mad', 'frustrating', 'annoying', 'terrible', 'hate', 'furious']
    surprised_keywords = ['wow', 'amazing', 'incredible', 'surprised', 'shocking', 'unbelievable']
    
    # Check for Filipino language
    filipino_keywords = ['ako', 'ikaw', 'siya', 'tayo', 'kami', 'kayo', 'sila', 'salamat', 'kamusta']
    
    # Count keyword matches
    happy_count = sum(1 for word in happy_keywords if word in text)
    sad_count = sum(1 for word in sad_keywords if word in text)
    angry_count = sum(1 for word in angry_keywords if word in text)
    surprised_count = sum(1 for word in surprised_keywords if word in text)
    filipino_count = sum(1 for word in filipino_keywords if word in text)
    
    # Determine dominant emotion
    if filipino_count > 2:  # If multiple Filipino words detected
        return "filipino"
    elif happy_count > max(sad_count, angry_count, surprised_count):
        return "happy"
    elif sad_count > max(happy_count, angry_count, surprised_count):
        return "sad"
    elif angry_count > max(happy_count, sad_count, surprised_count):
        return "angry"
    elif surprised_count > max(happy_count, sad_count, angry_count):
        return "surprised"
    else:
        return "neutral"

def check_interrupt():
    # Check for interrupt signal via file (interrupt_tts.flag)
    return os.path.exists('interrupt_tts.flag')

def clear_interrupt():
    # Remove interrupt flag if present
    if os.path.exists('interrupt_tts.flag'):
        os.remove('interrupt_tts.flag')

def split_sentences(text):
    # Simple sentence splitter (handles . ! ?)
    return [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]

def speak(text, emotion=None, voice_sample_path=None, language="en"):
    """Speak text with emotion-based parameters, sentence by sentence with interrupt support."""
    # Auto-detect emotion if not provided
    if emotion is None:
        emotion = detect_emotion_from_text(text)
    
    # Get emotion parameters (default to neutral if not found)
    params = EMOTION_PARAMS.get(emotion, EMOTION_PARAMS["neutral"])
    print(f"[TTS] Speaking with emotion: {emotion}")
    
    # Split text into sentences
    sentences = split_sentences(text)
    for idx, sentence in enumerate(sentences):
        if check_interrupt():
            print(f"[TTS] Interrupt detected before sentence {idx+1}, stopping playback.")
            clear_interrupt()
            return False
        print(f"[TTS] Speaking sentence {idx+1}/{len(sentences)}: {sentence}")
        # XTTS as primary
        try:
            if xtts_speak(sentence, voice_sample_path=voice_sample_path, language=language):
                continue
        except Exception as e:
            print(f"[TTS] XTTS error: {e}")
            logging.error(f"[TTS] XTTS error: {e}")
        # pyttsx3 fallback
        if pyttsx3_speak:
            try:
                import pyttsx3
    except ImportError as e:
        print(f"Import error: {e}")
                engine = pyttsx3.init()
                engine.setProperty('rate', int(engine.getProperty('rate') * params["rate"]))
                engine.setProperty('volume', params["volume"])
                try:
                    engine.setProperty('pitch', params["pitch"])
                except Exception:
                    pass
                engine.say(sentence)
                engine.runAndWait()
                continue
            except Exception as e:
                print(f"[TTS] pyttsx3 error: {e}")
                logging.error(f"[TTS] pyttsx3 error: {e}")
        # If all fail for this sentence
        print(f"[TTS] All TTS engines failed for sentence {idx+1}.")
        logging.error(f"[TTS] All TTS engines failed for sentence {idx+1}.")
    return True

# ZMQ Communication for agent integration
try:
    import zmq
except ImportError:
    print("[ERROR] ZMQ not installed. Run 'pip install pyzmq' to install it.")

# TTS agent ZMQ ports
TTS_PORT = 5562  # Port for receiving TTS requests - updated to match config.json

# Setup ZMQ for communication
def setup_zmq():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.bind(f"tcp://*:{TTS_PORT}")
    print(f"[TTS] Agent listening on port {TTS_PORT}")
    return context, socket

# Main entry point
if __name__ == "__main__":
    print('[DEBUG] __main__ block reached')
    import sys

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    
    # Test speak functionality directly if arguments are provided
    if len(sys.argv) > 1:
        speak(' '.join(sys.argv[1:]))
    else:
        # Run as service
        print("[TTS] Starting TTS agent service...")
        context, socket = setup_zmq()
        
        # Test startup with sample speech
        speak("TTS agent initialized and ready.")
        
        # Service loop
        try:
            while True:
                # Wait for message
                message = socket.recv_json()
                print(f"[TTS] Received request: {message}")
                
                # Process message
                if 'command' in message and message['command'] == 'speak':
                    text = message.get('text', '')
                    emotion = message.get('emotion', None)
                    voice_sample = message.get('voice_sample', None)
                    language = message.get('language', 'en')
                    
                    # Speak the text
                    result = speak(text, emotion, voice_sample, language)
                    
                    # Send response
                    response = {
                        'status': 'ok' if result else 'error',
                        'message': 'Speech completed' if result else 'Failed to generate speech'
                    }
                    socket.send_json(response)
                else:
                    # Unknown command
                    socket.send_json({
                        'status': 'error',
                        'message': 'Unknown command'
                    })
        except KeyboardInterrupt:
            print("[TTS] Shutting down TTS agent...")
        finally:
            socket.close()
            context.term()