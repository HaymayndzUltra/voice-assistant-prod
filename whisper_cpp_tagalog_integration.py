#!/usr/bin/env python3
"""
🎙️ WHISPER.CPP + TAGALOG INTEGRATION
Ultra-fast C++ Whisper with TranslationService integration
Perfect for real-time Tagalog voice commands

FEATURES:
- Whisper.cpp medium model (1.5GB, best accuracy)
- Direct Tagalog recognition
- TranslationService integration (Tagalog → English)
- Voice command pipeline for AI system
"""

import subprocess
import json
import time
import os
import tempfile
import wave
import zmq
from pathlib import Path
from typing import Dict, Any, Optional

class WhisperCppTagalogEngine:
    """
    High-performance Tagalog voice recognition using whisper.cpp

    Uses medium model for best accuracy with Tagalog/Taglish content
    Integrates with TranslationService for seamless AI pipeline
    """

    def __init__(self, whisper_cpp_path="/home/haymayndz/AI_System_Monorepo/whisper.cpp"):
        """TODO: Add description for __init__."""
        self.whisper_cpp_path = Path(whisper_cpp_path)
        self.whisper_cli = self.whisper_cpp_path / "build/bin/whisper-cli"
        self.model_path = self.whisper_cpp_path / "models/ggml-medium.bin"

        # ZMQ setup for TranslationService
        self.zmq_context = zmq.Context()
        self.translation_socket = None
        self.translation_service_url = "tcp://localhost:5595"

        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "average_processing_time": 0,
            "total_processing_time": 0
        }

        self._verify_installation()
        self._setup_translation_service()

    def _verify_installation(self):
        """Verify whisper.cpp installation and model availability"""
        if not self.whisper_cli.exists():
            raise FileNotFoundError(f"Whisper CLI not found at {self.whisper_cli}")

        if not self.model_path.exists():
            raise FileNotFoundError(f"Medium model not found at {self.model_path}")

        print(f"✅ Whisper.cpp CLI: {self.whisper_cli}")
        print(f"✅ Medium model: {self.model_path} ({self.model_path.stat().st_size / (1024**3):.1f}GB)")

    def _setup_translation_service(self):
        """Setup connection to TranslationService"""
        try:
            self.translation_socket = self.zmq_context.socket(zmq.REQ)
            self.translation_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 sec timeout
            self.translation_socket.setsockopt(zmq.SNDTIMEO, 5000)   # 5 sec timeout
            self.translation_socket.connect(self.translation_service_url)
            print(f"✅ Connected to TranslationService at {self.translation_service_url}")
        except Exception as e:
            print(f"⚠️ Could not connect to TranslationService: {e}")
            self.translation_socket = None

    def transcribe_audio_file(self, audio_path: str, language="tl") -> Dict[str, Any]:
        """
        Transcribe audio file using whisper.cpp medium model

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Language code (tl for Tagalog, auto for detection)

        Returns:
            Dict with transcription results
        """
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # Build whisper.cpp command
            cmd = [
                str(self.whisper_cli),
                "-m", str(self.model_path),
                "-f", audio_path,
                "--output-json",  # JSON output for easier parsing
                "--language", language,
                "--threads", "4",  # Use 4 threads for speed
            ]

            print(f"🎤 Transcribing: {audio_path}")
            print(f"🔧 Command: {' '.join(cmd)}")

            # Run whisper.cpp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            processing_time = time.time() - start_time

            if result.returncode == 0:
                # Parse output to extract transcribed text
                transcribed_text = self._parse_whisper_output(result.stdout)

                if transcribed_text:
                    self.stats["successful_transcriptions"] += 1
                    self.stats["total_processing_time"] += processing_time
                    self.stats["average_processing_time"] = (
                        self.stats["total_processing_time"] / self.stats["successful_transcriptions"]
                    )

                    return {
                        "status": "success",
                        "text": transcribed_text,
                        "language": language,
                        "processing_time": processing_time,
                        "model": "whisper-cpp-medium",
                        "engine": "whisper.cpp"
                    }
                else:
                    self.stats["failed_transcriptions"] += 1
                    return {
                        "status": "error",
                        "message": "No text detected in audio",
                        "processing_time": processing_time
                    }
            else:
                self.stats["failed_transcriptions"] += 1
                return {
                    "status": "error",
                    "message": f"Whisper.cpp error: {result.stderr}",
                    "processing_time": processing_time
                }

        except subprocess.TimeoutExpired:
            self.stats["failed_transcriptions"] += 1
            return {
                "status": "error",
                "message": "Transcription timeout (>120s)",
                "processing_time": time.time() - start_time
            }
        except Exception as e:
            self.stats["failed_transcriptions"] += 1
            return {
                "status": "error",
                "message": f"Transcription failed: {str(e)}",
                "processing_time": time.time() - start_time
            }

    def _parse_whisper_output(self, output: str) -> str:
        """Parse whisper.cpp output to extract transcribed text"""
        try:
            # whisper.cpp outputs text in format:
            # [timestamp] text
            lines = output.strip().split('\n')

            # Find lines with transcribed text (contain timestamps)
            transcribed_lines = []
            for line in lines:
                line = line.strip()
                if line and ('[' in line and ']' in line):
                    # Extract text after timestamp
                    if ']' in line:
                        text_part = line.split(']', 1)[1].strip()
                        if text_part:
                            transcribed_lines.append(text_part)

            # Join all transcribed text
            full_text = ' '.join(transcribed_lines).strip()
            return full_text if full_text else None

        except Exception as e:
            print(f"Error parsing whisper output: {e}")
            return None

    def translate_to_english(self, tagalog_text: str) -> Dict[str, Any]:
        """
        Translate Tagalog text to English using TranslationService

        Args:
            tagalog_text: Tagalog text to translate

        Returns:
            Dict with translation result
        """
        if not self.translation_socket:
            return {
                "status": "error",
                "message": "TranslationService not available"
            }

        try:
            # Prepare translation request
            request = {
                "text": tagalog_text,
                "source_lang": "tl",
                "target_lang": "en",
                "session_id": f"voice_session_{int(time.time())}"
            }

            print(f"🔄 Translating: '{tagalog_text}' (tl → en)")

            # Send request
            self.translation_socket.send_json(request)

            # Receive response
            response = self.translation_socket.recv_json()

            if response.get("status") == "success":
                english_text = response.get("translation", "")
                print(f"✅ Translation: '{english_text}'")

                return {
                    "status": "success",
                    "english_text": english_text,
                    "engine_used": response.get("engine", "unknown"),
                    "original_text": tagalog_text
                }
            else:
                return {
                    "status": "error",
                    "message": response.get("message", "Translation failed"),
                    "original_text": tagalog_text
                }

        except Exception as e:
            print(f"❌ Translation error: {e}")
            return {
                "status": "error",
                "message": f"Translation service error: {str(e)}",
                "original_text": tagalog_text
            }

    def process_voice_command(self, audio_path: str) -> Dict[str, Any]:
        """
        Complete voice pipeline: Audio → STT → Translation → Ready for AI

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with complete processing result
        """
        pipeline_start = time.time()

        print("🎙️ === TAGALOG VOICE PIPELINE STARTED ===")

        # Step 1: Speech-to-Text (Tagalog)
        stt_result = self.transcribe_audio_file(audio_path, language="tl")

        if stt_result.get("status") != "success":
            return {
                "status": "error",
                "message": "STT failed",
                "details": stt_result,
                "pipeline_time": time.time() - pipeline_start
            }

        tagalog_text = stt_result.get("text", "")
        if not tagalog_text:
            return {
                "status": "error",
                "message": "No speech detected",
                "pipeline_time": time.time() - pipeline_start
            }

        # Step 2: Translation (Tagalog → English)
        translation_result = self.translate_to_english(tagalog_text)

        if translation_result.get("status") != "success":
            # Even if translation fails, we still have the Tagalog text
            english_text = tagalog_text  # Fallback to original
            translation_warning = translation_result.get("message", "Translation failed")
        else:
            english_text = translation_result.get("english_text", tagalog_text)
            translation_warning = None

        # Step 3: Prepare final result
        pipeline_time = time.time() - pipeline_start

        result = {
            "status": "success",
            "pipeline_time_ms": int(pipeline_time * 1000),
            "audio_file": audio_path,
            "stt": {
                "tagalog_text": tagalog_text,
                "processing_time": stt_result.get("processing_time", 0),
                "model": "whisper-cpp-medium",
                "language": "tl"
            },
            "translation": {
                "english_text": english_text,
                "status": translation_result.get("status", "unknown"),
                "engine": translation_result.get("engine_used", "fallback")
            },
            "ready_for_ai": english_text,  # This goes to your LLM
            "metadata": {
                "pipeline_type": "tagalog_voice_command",
                "processing_steps": ["stt", "translation"],
                "timestamp": time.time(),
                "warnings": [translation_warning] if translation_warning else []
            }
        }

        print(f"✅ === PIPELINE COMPLETE ({pipeline_time:.2f}s) ===")
        print(f"🎯 Ready for AI: '{english_text}'")

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        success_rate = 0
        if self.stats["total_requests"] > 0:
            success_rate = (self.stats["successful_transcriptions"] / self.stats["total_requests"]) * 100

        return {
            "total_requests": self.stats["total_requests"],
            "successful_transcriptions": self.stats["successful_transcriptions"],
            "failed_transcriptions": self.stats["failed_transcriptions"],
            "success_rate": f"{success_rate:.1f}%",
            "average_processing_time": f"{self.stats['average_processing_time']:.2f}s",
            "model": "whisper-cpp-medium",
            "model_size": "1.5GB"
        }

    def cleanup(self):
        """Clean up resources"""
        if self.translation_socket:
            self.translation_socket.close()
        if self.zmq_context:
            self.zmq_context.term()
        print("🧹 Whisper.cpp engine cleaned up")

# Example usage and testing
def main():
    """Example usage of Whisper.cpp Tagalog engine"""

    print("🎙️ WHISPER.CPP TAGALOG INTEGRATION TEST")
    print("=" * 50)

    try:
        # Initialize engine
        engine = WhisperCppTagalogEngine()

        # Show stats
        print(f"\n📊 ENGINE STATS:")
        stats = engine.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Test with sample file (if available)
        sample_path = "/home/haymayndz/AI_System_Monorepo/whisper.cpp/samples/jfk.wav"
        if os.path.exists(sample_path):
            print(f"\n🎤 TESTING WITH SAMPLE FILE: {sample_path}")

            # Test STT only
            stt_result = engine.transcribe_audio_file(sample_path, language="en")
            print(f"STT Result: {json.dumps(stt_result, indent=2)}")

            # Test full pipeline
            pipeline_result = engine.process_voice_command(sample_path)
            print(f"Pipeline Result: {json.dumps(pipeline_result, indent=2)}")

        print(f"\n🚀 READY FOR TAGALOG VOICE COMMANDS!")
        print(f"Use: engine.process_voice_command('your_tagalog_audio.wav')")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'engine' in locals():
            engine.cleanup()

if __name__ == "__main__":
    main()