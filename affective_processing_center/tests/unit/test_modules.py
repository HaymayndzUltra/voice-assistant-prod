"""
Unit tests for emotion processing modules.

Tests each module in isolation with fixed inputs to verify
correct behavior and output format.
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from core.schemas import AudioChunk, Transcript, ModuleOutput, EmotionType
from core.cache import EmbeddingCache
from modules.base import BaseModule, ModuleRegistry
from modules.tone import ToneModule
from modules.mood import MoodModule
from modules.empathy import EmpathyModule
from modules.voice_profile import VoiceProfileModule
from modules.human_awareness import HumanAwarenessModule
from modules.synthesis import SynthesisModule


class TestBaseModule:
    """Test the base module interface and functionality."""
    
    def test_base_module_is_abstract(self):
        """Test that BaseModule cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseModule({}, "cuda")
    
    def test_module_registry_singleton(self):
        """Test that module registry is a singleton."""
        from modules.base import module_registry
        registry1 = module_registry
        
        from modules.base import module_registry as registry2
        assert registry1 is registry2
    
    def test_module_registry_has_all_modules(self):
        """Test that all modules are registered."""
        from modules.base import module_registry
        
        available_modules = module_registry.get_available_modules()
        expected_modules = ['tone', 'mood', 'empathy', 'voice_profile', 'human_awareness', 'synthesis']
        
        for module in expected_modules:
            assert module in available_modules, f"Module {module} not registered"


class TestToneModule:
    """Test the tone analysis module."""
    
    @pytest.fixture
    def tone_module(self):
        """Create a tone module for testing."""
        config = {
            'model_name': 'facebook/wav2vec2-base',
            'feature_dim': 768,
            'sample_rate': 16000
        }
        return ToneModule(config, device="cpu")
    
    @pytest.fixture
    def audio_chunk(self):
        """Create a test audio chunk."""
        # Generate 1 second of random audio data
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
        return AudioChunk(
            audio_data=audio_data,
            sample_rate=16000,
            timestamp=datetime.utcnow(),
            duration_ms=1000,
            speaker_id="test_speaker"
        )
    
    @pytest.fixture
    def transcript(self):
        """Create a test transcript."""
        return Transcript(
            text="I am feeling happy today!",
            confidence=0.95,
            timestamp=datetime.utcnow(),
            speaker_id="test_speaker",
            language="en"
        )
    
    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return EmbeddingCache(max_size=100, ttl_minutes=10)
    
    def test_tone_module_initialization(self, tone_module):
        """Test tone module initialization."""
        assert tone_module.name == "tone"
        assert tone_module.provides == "tone_features"
        assert tone_module.requires == []
        assert tone_module.device == "cpu"
        assert tone_module.model_name == 'facebook/wav2vec2-base'
    
    @pytest.mark.asyncio
    async def test_tone_module_process_audio(self, tone_module, audio_chunk, cache):
        """Test tone module processing with audio input."""
        result = await tone_module.process(audio_chunk, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "tone"
        assert result.feature_type == "tone_features"
        assert isinstance(result.features, list)
        assert len(result.features) == tone_module.feature_dim
        assert all(isinstance(f, (int, float)) for f in result.features)
        assert 0.0 <= result.confidence <= 1.0
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_tone_module_process_transcript(self, tone_module, transcript, cache):
        """Test tone module processing with transcript input."""
        result = await tone_module.process(transcript, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "tone"
        assert result.feature_type == "tone_features"
        assert isinstance(result.features, list)
        assert len(result.features) == tone_module.feature_dim
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_tone_module_caching(self, tone_module, audio_chunk, cache):
        """Test that tone module uses caching effectively."""
        # First call should compute features
        result1 = await tone_module.process(audio_chunk, cache)
        
        # Second call with same input should use cache
        result2 = await tone_module.process(audio_chunk, cache)
        
        assert result1.features == result2.features
        assert result2.processing_time_ms < result1.processing_time_ms  # Cache should be faster
    
    def test_tone_module_confidence_calculation(self, tone_module, audio_chunk):
        """Test confidence calculation."""
        features = [0.1] * tone_module.feature_dim
        confidence = tone_module.get_confidence(features, audio_chunk)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


class TestMoodModule:
    """Test the mood analysis module."""
    
    @pytest.fixture
    def mood_module(self):
        """Create a mood module for testing."""
        config = {
            'model_path': '/models/mood-bert',
            'feature_dim': 512,
            'max_length': 256
        }
        return MoodModule(config, device="cpu")
    
    @pytest.fixture
    def transcript(self):
        """Create a test transcript."""
        return Transcript(
            text="I am feeling quite sad and disappointed today.",
            confidence=0.9,
            timestamp=datetime.utcnow(),
            speaker_id="test_speaker",
            language="en"
        )
    
    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return EmbeddingCache(max_size=100, ttl_minutes=10)
    
    def test_mood_module_initialization(self, mood_module):
        """Test mood module initialization."""
        assert mood_module.name == "mood"
        assert mood_module.provides == "mood_features"
        assert mood_module.requires == ["tone_features"]
        assert mood_module.device == "cpu"
        assert mood_module.model_path == '/models/mood-bert'
        assert len(mood_module.mood_categories) > 0
    
    @pytest.mark.asyncio
    async def test_mood_module_process_transcript(self, mood_module, transcript, cache):
        """Test mood module processing with transcript."""
        result = await mood_module.process(transcript, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "mood"
        assert result.feature_type == "mood_features"
        assert isinstance(result.features, list)
        assert len(result.features) == mood_module.feature_dim
        assert 0.0 <= result.confidence <= 1.0
    
    def test_mood_module_dependencies(self, mood_module):
        """Test mood module dependency requirements."""
        dependencies = mood_module.get_dependencies()
        assert "tone_features" in dependencies
        
        # Test can_process method
        assert not mood_module.can_process(set())  # No features available
        assert mood_module.can_process({"tone_features"})  # Required feature available
    
    def test_mood_word_embeddings(self, mood_module):
        """Test mood word embedding generation."""
        features = mood_module._generate_word_features("happy")
        assert isinstance(features, list)
        assert len(features) > 0
        assert all(isinstance(f, (int, float)) for f in features)


class TestEmpathyModule:
    """Test the empathy analysis module."""
    
    @pytest.fixture
    def empathy_module(self):
        """Create an empathy module for testing."""
        config = {
            'model_name': 'sentence-transformers/all-mpnet-base-v2'
        }
        return EmpathyModule(config, device="cpu")
    
    @pytest.fixture
    def transcript(self):
        """Create a test transcript."""
        return Transcript(
            text="I understand how you must be feeling right now.",
            confidence=0.92,
            timestamp=datetime.utcnow(),
            speaker_id="test_speaker",
            language="en"
        )
    
    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return EmbeddingCache(max_size=100, ttl_minutes=10)
    
    def test_empathy_module_initialization(self, empathy_module):
        """Test empathy module initialization."""
        assert empathy_module.name == "empathy"
        assert empathy_module.provides == "empathy_features"
        assert empathy_module.requires == ["mood_features"]
        assert empathy_module.feature_dim == 384
    
    @pytest.mark.asyncio
    async def test_empathy_module_process_transcript(self, empathy_module, transcript, cache):
        """Test empathy module processing."""
        result = await empathy_module.process(transcript, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "empathy"
        assert result.feature_type == "empathy_features"
        assert len(result.features) == empathy_module.feature_dim
        assert 0.0 <= result.confidence <= 1.0


class TestVoiceProfileModule:
    """Test the voice profile analysis module."""
    
    @pytest.fixture
    def voice_profile_module(self):
        """Create a voice profile module for testing."""
        config = {
            'embedding_dim': 512
        }
        return VoiceProfileModule(config, device="cpu")
    
    @pytest.fixture
    def audio_chunk(self):
        """Create a test audio chunk."""
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
        return AudioChunk(
            audio_data=audio_data,
            sample_rate=16000,
            timestamp=datetime.utcnow(),
            duration_ms=1000,
            speaker_id="test_speaker"
        )
    
    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return EmbeddingCache(max_size=100, ttl_minutes=10)
    
    def test_voice_profile_module_initialization(self, voice_profile_module):
        """Test voice profile module initialization."""
        assert voice_profile_module.name == "voice_profile"
        assert voice_profile_module.provides == "voice_profile_features"
        assert voice_profile_module.requires == []
        assert voice_profile_module.embedding_dim == 512
    
    @pytest.mark.asyncio
    async def test_voice_profile_module_process_audio(self, voice_profile_module, audio_chunk, cache):
        """Test voice profile module processing."""
        result = await voice_profile_module.process(audio_chunk, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "voice_profile"
        assert result.feature_type == "voice_profile_features"
        assert len(result.features) == voice_profile_module.embedding_dim
        assert 0.0 <= result.confidence <= 1.0


class TestHumanAwarenessModule:
    """Test the human awareness module."""
    
    @pytest.fixture
    def human_awareness_module(self):
        """Create a human awareness module for testing."""
        config = {
            'feature_dim': 256
        }
        return HumanAwarenessModule(config, device="cpu")
    
    @pytest.fixture
    def transcript(self):
        """Create a test transcript."""
        return Transcript(
            text="Hello, is anyone there?",
            confidence=0.88,
            timestamp=datetime.utcnow(),
            speaker_id="test_speaker",
            language="en"
        )
    
    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return EmbeddingCache(max_size=100, ttl_minutes=10)
    
    def test_human_awareness_module_initialization(self, human_awareness_module):
        """Test human awareness module initialization."""
        assert human_awareness_module.name == "human_awareness"
        assert human_awareness_module.provides == "human_awareness_features"
        assert human_awareness_module.requires == ["voice_profile_features"]
        assert human_awareness_module.feature_dim == 256
    
    @pytest.mark.asyncio
    async def test_human_awareness_module_process(self, human_awareness_module, transcript, cache):
        """Test human awareness module processing."""
        result = await human_awareness_module.process(transcript, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "human_awareness"
        assert result.feature_type == "human_awareness_features"
        assert len(result.features) == human_awareness_module.feature_dim
        assert 0.0 <= result.confidence <= 1.0


class TestSynthesisModule:
    """Test the synthesis module."""
    
    @pytest.fixture
    def synthesis_module(self):
        """Create a synthesis module for testing."""
        config = {
            'prosody_model': '/models/prosody-taco.pt'
        }
        return SynthesisModule(config, device="cpu")
    
    @pytest.fixture
    def transcript(self):
        """Create a test transcript."""
        return Transcript(
            text="Generating emotional speech synthesis.",
            confidence=0.95,
            timestamp=datetime.utcnow(),
            speaker_id="test_speaker",
            language="en"
        )
    
    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return EmbeddingCache(max_size=100, ttl_minutes=10)
    
    def test_synthesis_module_initialization(self, synthesis_module):
        """Test synthesis module initialization."""
        assert synthesis_module.name == "synthesis"
        assert synthesis_module.provides == "synthesis_features"
        assert synthesis_module.requires == ["empathy_features", "human_awareness_features"]
        assert synthesis_module.feature_dim == 1024
    
    @pytest.mark.asyncio
    async def test_synthesis_module_process(self, synthesis_module, transcript, cache):
        """Test synthesis module processing."""
        result = await synthesis_module.process(transcript, cache)
        
        assert isinstance(result, ModuleOutput)
        assert result.module_name == "synthesis"
        assert result.feature_type == "synthesis_features"
        assert len(result.features) == synthesis_module.feature_dim
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_synthesis_emotion_generation(self, synthesis_module):
        """Test emotion synthesis functionality."""
        from core.schemas import SynthesisRequest
        
        request = SynthesisRequest(
            text="Hello world",
            emotion=EmotionType.HAPPY,
            intensity=1.0
        )
        
        audio_data = await synthesis_module.synthesize_emotion(request)
        
        assert isinstance(audio_data, bytes)
        assert len(audio_data) > 0


class TestModulePerformance:
    """Test module performance characteristics."""
    
    @pytest.fixture
    def modules(self):
        """Create all modules for performance testing."""
        config = {}
        return {
            'tone': ToneModule(config, device="cpu"),
            'mood': MoodModule(config, device="cpu"),
            'empathy': EmpathyModule(config, device="cpu"),
            'voice_profile': VoiceProfileModule(config, device="cpu"),
            'human_awareness': HumanAwarenessModule(config, device="cpu"),
            'synthesis': SynthesisModule(config, device="cpu")
        }
    
    @pytest.fixture
    def test_inputs(self):
        """Create test inputs."""
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
        
        return {
            'audio': AudioChunk(
                audio_data=audio_data,
                sample_rate=16000,
                timestamp=datetime.utcnow(),
                duration_ms=1000,
                speaker_id="test_speaker"
            ),
            'transcript': Transcript(
                text="Performance testing input text.",
                confidence=0.9,
                timestamp=datetime.utcnow(),
                speaker_id="test_speaker",
                language="en"
            )
        }
    
    @pytest.fixture
    def cache(self):
        """Create a performance test cache."""
        return EmbeddingCache(max_size=1000, ttl_minutes=30)
    
    @pytest.mark.asyncio
    async def test_module_processing_speed(self, modules, test_inputs, cache):
        """Test module processing speed."""
        import time
        
        # Test each module's processing speed
        for module_name, module in modules.items():
            # Choose appropriate input type
            if module.requires == []:
                # Modules with no dependencies can process both types
                test_input = test_inputs['audio'] if module_name in ['tone', 'voice_profile'] else test_inputs['transcript']
            else:
                # Modules with dependencies typically process transcripts
                test_input = test_inputs['transcript']
            
            start_time = time.time()
            result = await module.process(test_input, cache)
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Verify processing completed successfully
            assert isinstance(result, ModuleOutput)
            assert result.processing_time_ms > 0
            
            # Log performance for analysis
            print(f"{module_name} processing time: {processing_time:.2f}ms")
            
            # Basic performance expectation (should process in under 100ms for simple inputs)
            assert processing_time < 100, f"{module_name} took too long: {processing_time:.2f}ms"
    
    @pytest.mark.asyncio
    async def test_module_warmup(self, modules):
        """Test module warmup functionality."""
        for module_name, module in modules.items():
            # Test warmup doesn't fail
            await module.warmup()
            
            # Test that performance stats are available
            stats = module.get_performance_stats()
            assert isinstance(stats, dict)
            assert 'total_calls' in stats
            assert 'total_time_ms' in stats
    
    def test_module_memory_usage(self, modules):
        """Test that modules don't have excessive memory usage."""
        import tracemalloc
        
        tracemalloc.start()
        
        for module_name, module in modules.items():
            # Test module creation doesn't use excessive memory
            current, peak = tracemalloc.get_traced_memory()
            print(f"{module_name} memory usage: current={current / 1024 / 1024:.2f}MB, peak={peak / 1024 / 1024:.2f}MB")
            
            # Basic memory expectation (should be under 100MB for initialization)
            assert peak < 100 * 1024 * 1024, f"{module_name} uses too much memory: {peak / 1024 / 1024:.2f}MB"
        
        tracemalloc.stop()


if __name__ == "__main__":
    # Run tests when called directly
    pytest.main([__file__, "-v"])