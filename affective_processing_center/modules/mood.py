"""Mood analysis module for detecting emotional mood from text."""

import numpy as np
import logging
from typing import List, Dict, Any
import asyncio

from .base import BaseModule, module_registry
from ..core.schemas import Payload, AudioChunk, Transcript

logger = logging.getLogger(__name__)


class MoodModule(BaseModule):
    """
    Mood analysis module that extracts emotional mood features from text.
    
    This module uses BERT-like analysis to understand the emotional context
    and mood indicators in textual content.
    """
    
    requires: List[str] = ["tone_features"]  # Depends on tone analysis
    provides: str = "mood_features"
    
    def __init__(self, config: Dict[str, Any], device: str = "cuda"):
        """Initialize mood analysis module."""
        super().__init__(config, device)
        
        # Configuration parameters
        self.model_path = config.get('model_path', '/models/mood-bert')
        self.feature_dim = config.get('feature_dim', 512)
        self.max_length = config.get('max_length', 256)
        
        # Mood categories and their weights
        self.mood_categories = {
            'positive': 0.3,
            'negative': 0.3,
            'neutral': 0.2,
            'excited': 0.1,
            'calm': 0.1
        }
        
        # Simulated BERT-like embeddings
        self._word_embeddings = {}
        self._initialize_embeddings()
        
        logger.info(f"MoodModule initialized with model at {self.model_path}")
    
    def _initialize_embeddings(self):
        """Initialize simulated word embeddings for mood analysis."""
        mood_words = {
            # Positive emotions
            'happy': [0.8, 0.2, 0.1, 0.7, 0.3],
            'joy': [0.9, 0.1, 0.0, 0.8, 0.2],
            'excited': [0.7, 0.3, 0.2, 0.9, 0.1],
            'pleased': [0.6, 0.2, 0.1, 0.5, 0.4],
            'wonderful': [0.8, 0.1, 0.0, 0.6, 0.5],
            
            # Negative emotions
            'sad': [-0.8, 0.1, 0.9, 0.2, 0.7],
            'angry': [-0.6, 0.8, 0.7, 0.3, 0.2],
            'terrible': [-0.9, 0.2, 0.8, 0.1, 0.6],
            'awful': [-0.8, 0.3, 0.9, 0.0, 0.5],
            'disappointed': [-0.7, 0.1, 0.6, 0.2, 0.8],
            
            # Neutral/calm
            'okay': [0.0, 0.1, 0.2, 0.1, 0.9],
            'fine': [0.2, 0.0, 0.1, 0.2, 0.8],
            'calm': [0.3, 0.0, 0.0, 0.1, 0.9],
        }
        
        # Expand embeddings to full feature dimension
        for word, base_embedding in mood_words.items():
            full_embedding = base_embedding.copy()
            while len(full_embedding) < self.feature_dim:
                # Add variations and noise
                variation = [base_embedding[i % len(base_embedding)] * np.random.normal(0.1, 0.05) 
                           for i in range(len(base_embedding))]
                full_embedding.extend(variation)
            
            self._word_embeddings[word] = full_embedding[:self.feature_dim]
    
    async def _extract_features(self, payload: Payload) -> List[float]:
        """
        Extract mood features from payload.
        
        Args:
            payload: Input audio chunk or transcript
            
        Returns:
            Mood feature vector
        """
        if isinstance(payload, Transcript):
            return await self._extract_text_mood(payload)
        elif isinstance(payload, AudioChunk):
            # For audio, derive mood from prosodic features
            return await self._extract_audio_mood(payload)
        else:
            raise ValueError(f"Unsupported payload type: {type(payload)}")
    
    async def _extract_text_mood(self, transcript: Transcript) -> List[float]:
        """Extract mood features from text content."""
        # Simulate BERT processing delay
        await asyncio.sleep(0.02)
        
        text = transcript.text.lower()
        words = text.split()
        
        if not words:
            return [0.0] * self.feature_dim
        
        # Initialize feature accumulator
        mood_features = np.zeros(self.feature_dim)
        word_count = 0
        
        # Process each word
        for word in words:
            if word in self._word_embeddings:
                mood_features += np.array(self._word_embeddings[word])
                word_count += 1
            else:
                # Generate features for unknown words based on length and characteristics
                word_features = self._generate_word_features(word)
                mood_features += np.array(word_features)
                word_count += 1
        
        # Average the features
        if word_count > 0:
            mood_features /= word_count
        
        # Add contextual features
        context_features = self._extract_context_features(text, transcript)
        mood_features = np.concatenate([mood_features[:self.feature_dim-len(context_features)], 
                                       context_features])
        
        # Normalize to [-1, 1] range
        if np.max(np.abs(mood_features)) > 0:
            mood_features = mood_features / np.max(np.abs(mood_features))
        
        return mood_features.tolist()
    
    async def _extract_audio_mood(self, audio: AudioChunk) -> List[float]:
        """Extract mood features from audio prosodic characteristics."""
        # Simulate audio mood analysis delay
        await asyncio.sleep(0.015)
        
        # Simulate prosodic mood indicators
        audio_length = len(audio.data)
        duration = audio.duration_ms
        
        # Generate mood features based on audio characteristics
        features = []
        
        # Energy-based mood indicators
        for i in range(32):
            energy_feature = np.sin(i * 0.1) * (audio_length % 1000) / 1000.0
            features.append(float(energy_feature))
        
        # Temporal mood patterns
        for i in range(32):
            temporal_feature = np.cos(i * 0.15) * (duration % 500) / 500.0
            features.append(float(temporal_feature))
        
        # Frequency-based mood indicators
        for i in range(32):
            freq_feature = np.tanh(i * 0.08) * (audio.sample_rate % 4000) / 4000.0
            features.append(float(freq_feature))
        
        # Pad to full feature dimension
        while len(features) < self.feature_dim:
            remaining = self.feature_dim - len(features)
            for i in range(min(remaining, 32)):
                feature = np.exp(-i * 0.05) * (audio_length % 200) / 200.0
                features.append(float(feature))
        
        # Normalize and return
        features = np.array(features[:self.feature_dim])
        if np.max(np.abs(features)) > 0:
            features = features / np.max(np.abs(features))
        
        return features.tolist()
    
    def _generate_word_features(self, word: str) -> List[float]:
        """Generate mood features for unknown words."""
        features = []
        
        # Length-based features
        length_factor = len(word) / 10.0
        features.append(length_factor)
        
        # Vowel/consonant ratio
        vowels = 'aeiou'
        vowel_count = sum(1 for char in word if char in vowels)
        vowel_ratio = vowel_count / len(word) if word else 0
        features.append(vowel_ratio)
        
        # Character-based indicators
        for i, char in enumerate(word[:10]):  # First 10 characters
            char_value = ord(char) / 127.0 if char.isalpha() else 0.5
            features.append(char_value)
        
        # Pad to feature dimension
        while len(features) < self.feature_dim:
            # Add derived features
            char_diversity = len(set(word)) / len(word) if word else 0
            features.append(char_diversity)
            
            if len(features) < self.feature_dim:
                # Fill with noise based on word characteristics
                noise = np.random.normal(0, 0.1)
                features.append(float(noise))
        
        return features[:self.feature_dim]
    
    def _extract_context_features(self, text: str, transcript: Transcript) -> List[float]:
        """Extract contextual mood features."""
        features = []
        
        # Sentence structure indicators
        sentence_count = len([s for s in text.split('.') if s.strip()])
        avg_sentence_length = len(text.split()) / max(sentence_count, 1)
        
        features.extend([
            min(sentence_count / 10.0, 1.0),
            min(avg_sentence_length / 20.0, 1.0),
            transcript.confidence,
            len(text) / 1000.0
        ])
        
        # Punctuation-based mood indicators
        features.extend([
            text.count('!') / 10.0,
            text.count('?') / 10.0,
            text.count(',') / 20.0,
            text.count('.') / 10.0
        ])
        
        return features
    
    def get_confidence(self, features: List[float], payload: Payload) -> float:
        """Calculate confidence score for mood analysis."""
        if not features:
            return 0.0
        
        # Base confidence on feature variance and input quality
        feature_variance = np.var(features)
        feature_magnitude = np.mean(np.abs(features))
        
        if isinstance(payload, Transcript):
            # For text, confidence based on length and known words
            text_length_factor = min(len(payload.text) / 50.0, 1.0)
            known_words = sum(1 for word in payload.text.lower().split() 
                            if word in self._word_embeddings)
            known_word_ratio = known_words / max(len(payload.text.split()), 1)
            
            base_confidence = 0.85 * text_length_factor * known_word_ratio * payload.confidence
        elif isinstance(payload, AudioChunk):
            # For audio, confidence based on duration and quality
            duration_factor = min(payload.duration_ms / 2000.0, 1.0)
            quality_factor = min(payload.sample_rate / 16000.0, 1.0)
            base_confidence = 0.75 * duration_factor * quality_factor
        else:
            base_confidence = 0.5
        
        # Adjust based on feature quality
        feature_quality = min(feature_variance * 10.0 + feature_magnitude, 1.0)
        final_confidence = (base_confidence + feature_quality) / 2.0
        
        return max(0.2, min(final_confidence, 0.92))
    
    async def warmup(self) -> None:
        """Warm up the mood analysis model."""
        logger.info("Warming up mood analysis model...")
        
        # Simulate model loading time
        await asyncio.sleep(0.15)
        
        # In real implementation, load BERT model here
        # self.model = load_bert_model(self.model_path, device=self.device)
        
        logger.info("Mood analysis model ready")


# Register the module
module_registry.register(MoodModule)