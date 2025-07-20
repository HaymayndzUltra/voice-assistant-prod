#!/usr/bin/env python3
"""
🎙️ VOICE PIPELINE RECOMMENDATION
Voice Input → STT (Whisper) → Translation → AI → TTS

RECOMMENDED SETUP:
1. Whisper STT (offline, fast)
2. TranslationService (Tagalog → English)
3. Local LLM (basic tasks) / API (deep reasoning)
4. TTS (speech output)
"""

import whisper
import json
import requests
import time
from pathlib import Path

class VoicePipelineManager:
    """
    Complete voice pipeline: STT → Translation → AI → TTS
    """
    
    def __init__(self):
        # STT Setup (Whisper)
        self.whisper_model = None
        self.whisper_model_size = "base"  # Recommended: base or small
        
        # Translation Service
        self.translation_service_url = "tcp://localhost:5595"
        
        # TTS Setup (you can add later)
        self.tts_engine = None
        
    def setup_whisper(self, model_size="base"):
        """
        Setup Whisper STT
        
        RECOMMENDED MODELS:
        - "tiny": Fastest, basic quality (39MB)
        - "base": Good balance (74MB) ⭐ RECOMMENDED
        - "small": Better quality (244MB)
        - "medium": Very good (769MB)
        - "large": Best quality (1550MB)
        """
        print(f"🎤 Loading Whisper model: {model_size}")
        
        try:
            # Download and load model
            self.whisper_model = whisper.load_model(model_size)
            self.whisper_model_size = model_size
            print(f"✅ Whisper {model_size} loaded successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error loading Whisper: {e}")
            return False
    
    def transcribe_audio(self, audio_file_path):
        """
        Convert audio to text using Whisper
        
        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            dict: Transcription result with text and language
        """
        if not self.whisper_model:
            return {"error": "Whisper model not loaded"}
            
        try:
            print(f"🎤 Transcribing audio: {audio_file_path}")
            
            # Transcribe with language detection
            result = self.whisper_model.transcribe(
                audio_file_path,
                language='tl',  # Force Tagalog detection
                task='transcribe'
            )
            
            transcribed_text = result['text'].strip()
            detected_language = result.get('language', 'tl')
            
            print(f"📝 Transcribed: '{transcribed_text}'")
            print(f"🌐 Detected language: {detected_language}")
            
            return {
                "text": transcribed_text,
                "language": detected_language,
                "confidence": 0.9,  # Whisper doesn't provide confidence
                "status": "success"
            }
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return {"error": str(e), "status": "failed"}
    
    def translate_to_english(self, tagalog_text):
        """
        Translate Tagalog to English using TranslationService
        
        Args:
            tagalog_text: Tagalog text to translate
            
        Returns:
            dict: Translation result
        """
        try:
            print(f"🔄 Translating: '{tagalog_text}' (tl → en)")
            
            # Prepare request for TranslationService
            request = {
                "text": tagalog_text,
                "source_lang": "tl",
                "target_lang": "en",
                "session_id": f"voice_session_{int(time.time())}"
            }
            
            # TODO: Replace with actual ZMQ communication
            # For now, simulate TranslationService response
            
            # MOCK RESPONSE (replace with real ZMQ call)
            mock_response = {
                "status": "success",
                "translation": self._mock_translate(tagalog_text),
                "engine": "dictionary",
                "source_lang": "tl",
                "target_lang": "en"
            }
            
            print(f"✅ Translation: '{mock_response['translation']}'")
            return mock_response
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return {"error": str(e), "status": "failed"}
    
    def _mock_translate(self, text):
        """Mock translation for testing (replace with real TranslationService)"""
        simple_translations = {
            "kumusta": "hello",
            "salamat": "thank you", 
            "paalam": "goodbye",
            "oo": "yes",
            "hindi": "no",
            "ano ang oras": "what time is it",
            "buksan mo ang file": "open the file",
            "isara mo ang app": "close the app"
        }
        
        text_lower = text.lower().strip()
        return simple_translations.get(text_lower, text)  # Fallback to original
    
    def process_voice_command(self, audio_file_path):
        """
        Complete voice pipeline: Audio → Text → Translation → Ready for AI
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            dict: Complete processing result
        """
        pipeline_start = time.time()
        
        print("🎙️ === VOICE PIPELINE STARTED ===")
        
        # Step 1: STT (Speech-to-Text)
        stt_result = self.transcribe_audio(audio_file_path)
        if stt_result.get("status") == "failed":
            return {"error": "STT failed", "details": stt_result}
        
        tagalog_text = stt_result.get("text", "")
        if not tagalog_text:
            return {"error": "No speech detected"}
        
        # Step 2: Translation (Tagalog → English)
        translation_result = self.translate_to_english(tagalog_text)
        if translation_result.get("status") == "failed":
            return {"error": "Translation failed", "details": translation_result}
        
        english_text = translation_result.get("translation", "")
        
        # Step 3: Prepare for AI Processing
        pipeline_time = time.time() - pipeline_start
        
        result = {
            "status": "success",
            "pipeline_time_ms": int(pipeline_time * 1000),
            "original_audio": audio_file_path,
            "stt": {
                "tagalog_text": tagalog_text,
                "detected_language": stt_result.get("language"),
                "model_used": self.whisper_model_size
            },
            "translation": {
                "english_text": english_text,
                "engine_used": translation_result.get("engine"),
                "source_lang": "tl",
                "target_lang": "en"
            },
            "ready_for_ai": english_text,  # This goes to your LLM/AI
            "metadata": {
                "session_type": "voice_command",
                "processing_steps": ["stt", "translation"],
                "timestamp": time.time()
            }
        }
        
        print(f"✅ === PIPELINE COMPLETE ({pipeline_time:.2f}s) ===")
        print(f"🎯 Ready for AI: '{english_text}'")
        
        return result

# Example usage and recommendations
def main():
    """Example usage of the voice pipeline"""
    
    print("🎙️ VOICE PIPELINE RECOMMENDATION")
    print("=" * 50)
    
    # Initialize pipeline
    pipeline = VoicePipelineManager()
    
    # Setup Whisper (choose model size)
    print("\n📦 WHISPER MODEL RECOMMENDATIONS:")
    print("  tiny   - 39MB  - Fastest, basic quality")
    print("  base   - 74MB  - Good balance ⭐ RECOMMENDED")
    print("  small  - 244MB - Better quality")
    print("  medium - 769MB - Very good quality")
    print("  large  - 1550MB - Best quality")
    
    # Load recommended model
    if pipeline.setup_whisper("base"):
        print("\n✅ Whisper ready!")
        
        # Example processing (when you have audio file)
        print("\n🎤 EXAMPLE VOICE COMMAND FLOW:")
        print("1. User says: 'Kumusta, buksan mo ang file'")
        print("2. STT Output: 'Kumusta, buksan mo ang file'")
        print("3. Translation: 'Hello, open the file'")
        print("4. AI Input: 'Hello, open the file'")
        print("5. AI Response: 'Opening file...'")
        print("6. TTS Output: Synthesized speech")
        
        # Mock processing example
        example_result = {
            "status": "success",
            "pipeline_time_ms": 850,
            "stt": {
                "tagalog_text": "Kumusta, buksan mo ang file",
                "detected_language": "tl",
                "model_used": "base"
            },
            "translation": {
                "english_text": "Hello, open the file",
                "engine_used": "dictionary",
                "source_lang": "tl",
                "target_lang": "en"
            },
            "ready_for_ai": "Hello, open the file"
        }
        
        print(f"\n📊 EXAMPLE RESULT:")
        print(json.dumps(example_result, indent=2))
    
    print("\n🚀 NEXT STEPS:")
    print("1. pip install openai-whisper")
    print("2. Test with: pipeline.setup_whisper('base')")
    print("3. Record audio file (WAV/MP3)")
    print("4. Call: pipeline.process_voice_command('audio.wav')")
    print("5. Use result['ready_for_ai'] for your LLM")

if __name__ == "__main__":
    main() 