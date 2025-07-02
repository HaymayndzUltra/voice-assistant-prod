from main_pc_code.src.core.base_agent import BaseAgent
# Fallback TTS using Coqui TTS (XTTS or similar) for fast/neutral voice
from TTS.api import TTS
import numpy as np
import sounddevice as sd
import logging

def coqui_speak(text, language="en", voice=None):
    try:
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        wav = tts.tts(text=text, speaker_wav=None, language=language)
        sd.play(wav, samplerate=24000)
        sd.wait()
        return True
    except Exception as e:
        logging.error(f"[CoquiFallback] Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        coqui_speak(' '.join(sys.argv[1:]))
    else:
        coqui_speak("This is the Coqui TTS fallback voice.")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
