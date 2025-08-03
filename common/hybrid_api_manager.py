#!/usr/bin/env python3
"""
Hybrid API Manager
Handles priority-based API routing for STT/TTS/Translate (cloud-first) and LLM (local-first)
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import openai
import httpx
from pathlib import Path

# Import cloud service clients
try:
    import google.cloud.speech as gcs
    import google.cloud.texttospeech as gctt
    import google.cloud.translate_v2 as translate
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

class ServiceType(Enum):
    STT = "stt"
    TTS = "tts"
    TRANSLATE = "translate"
    LLM = "llm"

class Provider(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"
    ELEVENLABS = "elevenlabs"

class HybridAPIManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.load_config()
        self.initialize_clients()
        
    def load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            # STT Configuration (Cloud First)
            'stt': {
                'primary_provider': os.getenv('STT_PRIMARY_PROVIDER', 'openai'),
                'fallback_provider': os.getenv('STT_FALLBACK_PROVIDER', 'google'),
                'use_local_fallback': os.getenv('STT_USE_LOCAL_FALLBACK', 'true').lower() == 'true'
            },
            
            # TTS Configuration (Cloud First)
            'tts': {
                'primary_provider': os.getenv('TTS_PRIMARY_PROVIDER', 'elevenlabs'),
                'fallback_provider': os.getenv('TTS_FALLBACK_PROVIDER', 'openai'),
                'use_local_fallback': os.getenv('TTS_USE_LOCAL_FALLBACK', 'true').lower() == 'true'
            },
            
            # Translation Configuration (Cloud First)
            'translate': {
                'primary_provider': os.getenv('TRANSLATE_PRIMARY_PROVIDER', 'google'),
                'fallback_provider': os.getenv('TRANSLATE_FALLBACK_PROVIDER', 'azure'),
                'use_local_fallback': os.getenv('TRANSLATE_USE_LOCAL_FALLBACK', 'true').lower() == 'true'
            },
            
            # LLM Configuration (Local First)
            'llm': {
                'primary_provider': os.getenv('LLM_PRIMARY_PROVIDER', 'local'),
                'fallback_provider': os.getenv('LLM_FALLBACK_PROVIDER', 'openai'),
                'local_model_path': os.getenv('LLM_LOCAL_MODEL_PATH', '/models/llama2-13b-chat'),
                'use_cloud_fallback': os.getenv('LLM_USE_CLOUD_FALLBACK', 'true').lower() == 'true'
            }
        }
        
        # API Keys and credentials
        self.credentials = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'api_base': os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
                'organization': os.getenv('OPENAI_ORGANIZATION'),
                'stt_model': os.getenv('OPENAI_STT_MODEL', 'whisper-1'),
                'tts_model': os.getenv('OPENAI_TTS_MODEL', 'tts-1'),
                'tts_voice': os.getenv('OPENAI_TTS_VOICE', 'alloy')
            },
            'google': {
                'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
                'project_id': os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
                'translate_api_key': os.getenv('GOOGLE_TRANSLATE_API_KEY'),
                'stt_language': os.getenv('GOOGLE_STT_LANGUAGE', 'en-US'),
                'tts_language': os.getenv('GOOGLE_TTS_LANGUAGE', 'en-US')
            },
            'azure': {
                'speech_key': os.getenv('AZURE_SPEECH_KEY'),
                'speech_region': os.getenv('AZURE_SPEECH_REGION'),
                'translator_key': os.getenv('AZURE_TRANSLATOR_KEY'),
                'translator_region': os.getenv('AZURE_TRANSLATOR_REGION')
            },
            'aws': {
                'access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
                'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
                'region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            },
            'elevenlabs': {
                'api_key': os.getenv('ELEVENLABS_API_KEY'),
                'voice_id': os.getenv('ELEVENLABS_VOICE_ID'),
                'model_id': os.getenv('ELEVENLABS_MODEL_ID', 'eleven_monolingual_v1')
            }
        }
        
    def initialize_clients(self):
        """Initialize API clients based on available credentials"""
        self.clients = {}
        
        # OpenAI Client
        if self.credentials['openai']['api_key']:
            self.openai_client = openai.OpenAI(
                api_key=self.credentials['openai']['api_key'],
                base_url=self.credentials['openai']['api_base'],
                organization=self.credentials['openai']['organization'] if self.credentials['openai']['organization'] else None
            )
            self.clients['openai'] = self.openai_client
            
        # Google Cloud Clients
        if GOOGLE_AVAILABLE and self.credentials['google']['credentials_path']:
            try:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials['google']['credentials_path']
                self.clients['google_speech'] = gcs.SpeechClient()
                self.clients['google_tts'] = gctt.TextToSpeechClient()
                self.clients['google_translate'] = translate.Client()
            except Exception as e:
                self.logger.warning(f"Failed to initialize Google clients: {e}")
                
        # Azure Clients
        if AZURE_AVAILABLE and self.credentials['azure']['speech_key']:
            try:
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.credentials['azure']['speech_key'],
                    region=self.credentials['azure']['speech_region']
                )
                self.clients['azure_speech'] = speech_config
            except Exception as e:
                self.logger.warning(f"Failed to initialize Azure clients: {e}")
                
        # AWS Clients
        if AWS_AVAILABLE and self.credentials['aws']['access_key_id']:
            try:
                session = boto3.Session(
                    aws_access_key_id=self.credentials['aws']['access_key_id'],
                    aws_secret_access_key=self.credentials['aws']['secret_access_key'],
                    region_name=self.credentials['aws']['region']
                )
                self.clients['aws_polly'] = session.client('polly')
                self.clients['aws_transcribe'] = session.client('transcribe')
                self.clients['aws_translate'] = session.client('translate')
            except Exception as e:
                self.logger.warning(f"Failed to initialize AWS clients: {e}")
                
    async def speech_to_text(self, audio_data: bytes, language: str = "en-US") -> str:
        """
        Convert speech to text using cloud-first strategy
        """
        service_config = self.config['stt']
        
        # Try primary provider first
        try:
            return await self._stt_with_provider(
                audio_data, language, service_config['primary_provider']
            )
        except Exception as e:
            self.logger.warning(f"Primary STT provider {service_config['primary_provider']} failed: {e}")
            
        # Try fallback provider
        if service_config['fallback_provider'] != service_config['primary_provider']:
            try:
                return await self._stt_with_provider(
                    audio_data, language, service_config['fallback_provider']
                )
            except Exception as e:
                self.logger.warning(f"Fallback STT provider {service_config['fallback_provider']} failed: {e}")
                
        # Try local fallback if enabled
        if service_config['use_local_fallback']:
            try:
                return await self._stt_local_fallback(audio_data, language)
            except Exception as e:
                self.logger.error(f"Local STT fallback failed: {e}")
                
        raise Exception("All STT providers failed")
        
    async def text_to_speech(self, text: str, voice: str = None, language: str = "en-US") -> bytes:
        """
        Convert text to speech using cloud-first strategy
        """
        service_config = self.config['tts']
        
        # Try primary provider first
        try:
            return await self._tts_with_provider(
                text, voice, language, service_config['primary_provider']
            )
        except Exception as e:
            self.logger.warning(f"Primary TTS provider {service_config['primary_provider']} failed: {e}")
            
        # Try fallback provider
        if service_config['fallback_provider'] != service_config['primary_provider']:
            try:
                return await self._tts_with_provider(
                    text, voice, language, service_config['fallback_provider']
                )
            except Exception as e:
                self.logger.warning(f"Fallback TTS provider {service_config['fallback_provider']} failed: {e}")
                
        # Try local fallback if enabled
        if service_config['use_local_fallback']:
            try:
                return await self._tts_local_fallback(text, voice, language)
            except Exception as e:
                self.logger.error(f"Local TTS fallback failed: {e}")
                
        raise Exception("All TTS providers failed")
        
    async def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """
        Translate text using cloud-first strategy
        """
        service_config = self.config['translate']
        
        # Try primary provider first
        try:
            return await self._translate_with_provider(
                text, target_language, source_language, service_config['primary_provider']
            )
        except Exception as e:
            self.logger.warning(f"Primary translate provider {service_config['primary_provider']} failed: {e}")
            
        # Try fallback provider
        if service_config['fallback_provider'] != service_config['primary_provider']:
            try:
                return await self._translate_with_provider(
                    text, target_language, source_language, service_config['fallback_provider']
                )
            except Exception as e:
                self.logger.warning(f"Fallback translate provider {service_config['fallback_provider']} failed: {e}")
                
        # Try local fallback if enabled
        if service_config['use_local_fallback']:
            try:
                return await self._translate_local_fallback(text, target_language, source_language)
            except Exception as e:
                self.logger.error(f"Local translate fallback failed: {e}")
                
        raise Exception("All translation providers failed")
        
    async def llm_reasoning(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        """
        LLM reasoning using local-first strategy
        """
        service_config = self.config['llm']
        
        # Try local model first
        if service_config['primary_provider'] == 'local':
            try:
                return await self._llm_local_inference(prompt, model, temperature)
            except Exception as e:
                self.logger.warning(f"Local LLM inference failed: {e}")
                
        # Try cloud fallback if enabled
        if service_config['use_cloud_fallback']:
            try:
                return await self._llm_with_provider(
                    prompt, model, temperature, service_config['fallback_provider']
                )
            except Exception as e:
                self.logger.error(f"Cloud LLM fallback {service_config['fallback_provider']} failed: {e}")
                
        raise Exception("All LLM providers failed")
        
    # Implementation methods for each provider
    async def _stt_with_provider(self, audio_data: bytes, language: str, provider: str) -> str:
        """STT implementation for specific provider"""
        if provider == 'local':
            return await self._stt_local_fallback(audio_data, language)
        elif provider == 'openai':
            return await self._openai_stt(audio_data, language)
        elif provider == 'google':
            return await self._google_stt(audio_data, language)
        elif provider == 'azure':
            return await self._azure_stt(audio_data, language)
        elif provider == 'aws':
            return await self._aws_stt(audio_data, language)
        else:
            raise ValueError(f"Unknown STT provider: {provider}")
            
    async def _tts_with_provider(self, text: str, voice: str, language: str, provider: str) -> bytes:
        """TTS implementation for specific provider"""
        if provider == 'elevenlabs':
            return await self._elevenlabs_tts(text, voice)
        elif provider == 'openai':
            return await self._openai_tts(text, voice)
        elif provider == 'google':
            return await self._google_tts(text, voice, language)
        elif provider == 'azure':
            return await self._azure_tts(text, voice, language)
        elif provider == 'aws':
            return await self._aws_tts(text, voice, language)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")
            
    async def _translate_with_provider(self, text: str, target: str, source: str, provider: str) -> str:
        """Translation implementation for specific provider"""
        if provider == 'google':
            return await self._google_translate(text, target, source)
        elif provider == 'azure':
            return await self._azure_translate(text, target, source)
        elif provider == 'aws':
            return await self._aws_translate(text, target, source)
        elif provider == 'openai':
            return await self._openai_translate(text, target, source)
        else:
            raise ValueError(f"Unknown translate provider: {provider}")
            
    # OpenAI implementations
    async def _openai_stt(self, audio_data: bytes, language: str = "en-US") -> str:
        """OpenAI Whisper STT"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_file.write(audio_data)
            audio_file.flush()
            
            with open(audio_file.name, "rb") as f:
                response = await asyncio.to_thread(
                    self.openai_client.audio.transcriptions.create,
                    model=self.credentials['openai']['stt_model'],
                    file=f,
                    language=language.split('-')[0] if language != 'auto' else None
                )
            return response.text
            
    async def _openai_tts(self, text: str, voice: str) -> bytes:
        """OpenAI TTS"""
        voice = voice or self.credentials['openai']['tts_voice']
        
        response = await asyncio.to_thread(
            self.openai_client.audio.speech.create,
            model=self.credentials['openai']['tts_model'],
            voice=voice,
            input=text
        )
        return response.content
        
    async def _openai_translate(self, text: str, target: str, source: str) -> str:
        """OpenAI GPT-based translation"""
        prompt = f"Translate the following text from {source} to {target}: {text}"
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
        
    # ElevenLabs implementation
    async def _elevenlabs_tts(self, text: str, voice: str) -> bytes:
        """ElevenLabs TTS"""
        voice_id = voice or self.credentials['elevenlabs']['voice_id']
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": self.credentials['elevenlabs']['api_key']},
                json={
                    "text": text,
                    "model_id": self.credentials['elevenlabs']['model_id'],
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
                }
            )
            response.raise_for_status()
            return response.content
            
    # Local fallback implementations
    async def _stt_local_fallback(self, audio_data: bytes, language: str) -> str:
        """Local STT using Whisper"""
        self.logger.info("Using local Whisper STT")
        
        try:
            import whisper
            import tempfile
            import os
            
            # Create temporary audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # Load model (use base model for speed)
                model = whisper.load_model("base")
                
                # Transcribe
                result = await asyncio.to_thread(
                    model.transcribe, 
                    temp_file.name,
                    language=language.split('-')[0] if language != 'auto' else None
                )
                
                # Cleanup
                os.unlink(temp_file.name)
                
                return result['text'].strip()
                
        except Exception as e:
            self.logger.error(f"Local Whisper STT failed: {e}")
            return "Local STT failed"
        
    async def _tts_local_fallback(self, text: str, voice: str, language: str) -> bytes:
        """Local TTS fallback (placeholder - implement with local models)"""
        self.logger.info("Using local TTS fallback")
        # TODO: Implement local TTS model (e.g., Coqui TTS, FastSpeech2)
        return b"Local TTS not implemented yet"
        
    async def _translate_local_fallback(self, text: str, target: str, source: str) -> str:
        """Local translation fallback (placeholder - implement with local models)"""
        self.logger.info("Using local translation fallback")
        # TODO: Implement local translation model (e.g., MarianMT, NLLB)
        return "Local translation not implemented yet"
        
    async def _llm_local_inference(self, prompt: str, model: str, temperature: float) -> str:
        """Local LLM inference with Ollama support"""
        self.logger.info("Using local LLM inference")
        
        model_path = self.config['llm']['local_model_path']
        
        try:
            # Check if using Ollama format
            if model_path.startswith('ollama://'):
                model_name = model_path.replace('ollama://', '')
                return await self._ollama_inference(prompt, model_name, temperature)
            
            # Check if Llama-3 available via Ollama
            elif 'llama-3' in model_path.lower():
                # Try Ollama first for Llama-3
                try:
                    return await self._ollama_inference(prompt, 'llama3:13b-instruct', temperature)
                except:
                    # Fallback to file path if Ollama fails
                    return await self._file_model_inference(prompt, model_path, temperature)
            
            # Default file-based model loading
            else:
                return await self._file_model_inference(prompt, model_path, temperature)
                
        except Exception as e:
            self.logger.error(f"Local LLM inference failed: {e}")
            raise Exception(f"Local LLM failed: {e}")
    
    async def _ollama_inference(self, prompt: str, model: str, temperature: float) -> str:
        """Ollama-based LLM inference"""
        import subprocess
        import json
        
        try:
            # Check if model exists
            list_result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if model not in list_result.stdout:
                # Try to pull the model
                self.logger.info(f"Pulling Ollama model: {model}")
                subprocess.run(['ollama', 'pull', model], check=True)
            
            # Run inference
            cmd = [
                'ollama', 'run', model,
                '--temperature', str(temperature),
                prompt
            ]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, check=True
            )
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ollama inference failed: {e.stderr}")
        except Exception as e:
            raise Exception(f"Ollama error: {e}")
    
    async def _file_model_inference(self, prompt: str, model_path: str, temperature: float) -> str:
        """File-based model inference (placeholder)"""
        # TODO: Implement file-based model loading (transformers, llama.cpp, etc.)
        self.logger.warning(f"File-based model not implemented: {model_path}")
        return f"File-based LLM not implemented for {model_path}"
        
    async def _llm_with_provider(self, prompt: str, model: str, temperature: float, provider: str) -> str:
        """Cloud LLM fallback"""
        if provider == 'openai':
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
            
    async def _openai_translate(self, text: str, target: str, source: str) -> str:
        """OpenAI GPT-based translation"""
        prompt = f"Translate the following text from {source} to {target}: {text}"
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
        
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all configured services"""
        status = {
            'stt': {
                'primary': self.config['stt']['primary_provider'],
                'fallback': self.config['stt']['fallback_provider'],
                'available_providers': []
            },
            'tts': {
                'primary': self.config['tts']['primary_provider'], 
                'fallback': self.config['tts']['fallback_provider'],
                'available_providers': []
            },
            'translate': {
                'primary': self.config['translate']['primary_provider'],
                'fallback': self.config['translate']['fallback_provider'],
                'available_providers': []
            },
            'llm': {
                'primary': self.config['llm']['primary_provider'],
                'fallback': self.config['llm']['fallback_provider'],
                'available_providers': []
            }
        }
        
        # Check available providers
        if 'openai' in self.clients:
            status['stt']['available_providers'].append('openai')
            status['tts']['available_providers'].append('openai')
            status['translate']['available_providers'].append('openai')
            status['llm']['available_providers'].append('openai')
            
        if 'google_speech' in self.clients:
            status['stt']['available_providers'].append('google')
        if 'google_tts' in self.clients:
            status['tts']['available_providers'].append('google')
        if 'google_translate' in self.clients:
            status['translate']['available_providers'].append('google')
            
        return status

# Global instance
api_manager = HybridAPIManager()

# Convenience functions
async def stt(audio_data: bytes, language: str = "en-US") -> str:
    """Speech to text with cloud-first priority"""
    return await api_manager.speech_to_text(audio_data, language)

async def tts(text: str, voice: str = None, language: str = "en-US") -> bytes:
    """Text to speech with cloud-first priority"""
    return await api_manager.text_to_speech(text, voice, language)

async def translate(text: str, target_language: str, source_language: str = "auto") -> str:
    """Translation with cloud-first priority"""
    return await api_manager.translate_text(text, target_language, source_language)

async def llm_chat(prompt: str, model: str = None, temperature: float = 0.7) -> str:
    """LLM reasoning with local-first priority"""
    return await api_manager.llm_reasoning(prompt, model, temperature)

if __name__ == "__main__":
    # Test the API manager
    import asyncio
    
    async def test_apis():
        print("Testing Hybrid API Manager...")
        
        # Test TTS (cloud first)
        try:
            audio = await tts("Hello, this is a test of the hybrid API system.")
            print(f"✅ TTS test successful: {len(audio)} bytes")
        except Exception as e:
            print(f"❌ TTS test failed: {e}")
            
        # Test translation (cloud first)
        try:
            translated = await translate("Hello world", "es")
            print(f"✅ Translation test successful: {translated}")
        except Exception as e:
            print(f"❌ Translation test failed: {e}")
            
        # Test LLM (local first)
        try:
            response = await llm_chat("What is artificial intelligence?")
            print(f"✅ LLM test successful: {response[:100]}...")
        except Exception as e:
            print(f"❌ LLM test failed: {e}")
            
        # Show service status
        status = api_manager.get_service_status()
        print(f"\n📊 Service Status: {json.dumps(status, indent=2)}")
        
    asyncio.run(test_apis())
