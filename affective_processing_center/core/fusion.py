"""Fusion layer for combining emotion processing module outputs."""

import numpy as np
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .schemas import EmotionalContext, ModuleOutput, EmotionType

logger = logging.getLogger(__name__)


class BaseFusion(ABC):
    """Abstract base class for fusion algorithms."""
    
    @abstractmethod
    def combine(self, module_outputs: Dict[str, ModuleOutput]) -> EmotionalContext:
        """
        Combine module outputs into unified emotional context.
        
        Args:
            module_outputs: Dictionary mapping module names to their outputs
            
        Returns:
            Unified emotional context vector
        """
        pass


class WeightedFusion(BaseFusion):
    """
    Weighted ensemble fusion algorithm.
    
    Combines module outputs using configurable weights to produce
    a unified emotional context vector (ECV).
    """
    
    def __init__(self, weights: Dict[str, float], target_dim: int = 512):
        """
        Initialize weighted fusion.
        
        Args:
            weights: Module weights for fusion (must sum to 1.0)
            target_dim: Target dimension for output ECV
        """
        self.weights = weights.copy()
        self.target_dim = target_dim
        
        # Validate weights
        self._validate_weights()
        
        # Emotion detection mappings
        self._emotion_mappings = self._initialize_emotion_mappings()
        
        logger.info(f"WeightedFusion initialized with weights: {weights}")
    
    def _validate_weights(self) -> None:
        """Validate that weights are properly configured."""
        if not self.weights:
            raise ValueError("Weights dictionary cannot be empty")
        
        weight_sum = sum(self.weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            logger.warning(f"Weights sum to {weight_sum}, normalizing to 1.0")
            # Normalize weights
            for module, weight in self.weights.items():
                self.weights[module] = weight / weight_sum
    
    def _initialize_emotion_mappings(self) -> Dict[str, Dict[str, float]]:
        """Initialize emotion detection mappings for different modules."""
        return {
            'tone': {
                'happy': [0.8, 0.2, 0.1, 0.0, 0.0, 0.0, 0.1],
                'sad': [0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.9],
                'angry': [0.0, 0.0, 0.0, 0.9, 0.1, 0.0, 0.0],
                'fearful': [0.0, 0.0, 0.0, 0.1, 0.8, 0.1, 0.0],
                'surprised': [0.1, 0.7, 0.2, 0.0, 0.0, 0.0, 0.0],
                'disgusted': [0.0, 0.0, 0.0, 0.0, 0.1, 0.8, 0.1],
                'neutral': [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.4]
            },
            'mood': {
                'happy': [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
                'sad': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                'angry': [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                'fearful': [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                'surprised': [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'disgusted': [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                'neutral': [0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.3]
            }
        }
    
    def combine(self, module_outputs: Dict[str, ModuleOutput]) -> EmotionalContext:
        """
        Combine module outputs using weighted fusion.
        
        Args:
            module_outputs: Dictionary of module outputs
            
        Returns:
            Unified emotional context
        """
        if not module_outputs:
            return self._create_empty_context()
        
        # Filter successful outputs
        valid_outputs = {
            name: output for name, output in module_outputs.items()
            if output.features and not output.metadata.get('failed', False)
        }
        
        if not valid_outputs:
            return self._create_empty_context()
        
        # Normalize feature vectors to target dimension
        normalized_features = self._normalize_features(valid_outputs)
        
        # Compute weighted combination
        fused_features = self._compute_weighted_average(normalized_features)
        
        # Extract emotional context
        primary_emotion, emotion_confidence = self._detect_primary_emotion(valid_outputs)
        valence, arousal = self._compute_valence_arousal(fused_features, valid_outputs)
        
        # Calculate contribution weights
        module_contributions = self._calculate_contributions(valid_outputs)
        
        # Calculate total processing time
        total_processing_time = sum(output.processing_time_ms for output in valid_outputs.values())
        
        return EmotionalContext(
            emotion_vector=fused_features,
            primary_emotion=primary_emotion,
            emotion_confidence=emotion_confidence,
            valence=valence,
            arousal=arousal,
            module_contributions=module_contributions,
            timestamp=datetime.utcnow(),
            processing_latency_ms=total_processing_time
        )
    
    def _normalize_features(self, outputs: Dict[str, ModuleOutput]) -> Dict[str, List[float]]:
        """Normalize all feature vectors to target dimension."""
        normalized = {}
        
        for name, output in outputs.items():
            features = output.features.copy()
            
            if len(features) > self.target_dim:
                # Truncate to target dimension
                features = features[:self.target_dim]
            elif len(features) < self.target_dim:
                # Pad with zeros or interpolate
                while len(features) < self.target_dim:
                    if len(output.features) > 0:
                        # Interpolate by repeating pattern
                        features.append(output.features[len(features) % len(output.features)])
                    else:
                        features.append(0.0)
            
            # Normalize to [-1, 1] range
            features = np.array(features)
            if np.max(np.abs(features)) > 0:
                features = features / np.max(np.abs(features))
            
            normalized[name] = features.tolist()
        
        return normalized
    
    def _compute_weighted_average(self, normalized_features: Dict[str, List[float]]) -> List[float]:
        """Compute weighted average of normalized features."""
        fused = np.zeros(self.target_dim)
        total_weight = 0.0
        
        for module_name, features in normalized_features.items():
            weight = self.weights.get(module_name, 0.0)
            if weight > 0:
                fused += weight * np.array(features)
                total_weight += weight
        
        # Normalize by total weight if needed
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            fused /= total_weight
        
        return fused.tolist()
    
    def _detect_primary_emotion(self, outputs: Dict[str, ModuleOutput]) -> tuple[EmotionType, float]:
        """Detect the primary emotion from module outputs."""
        emotion_scores = {emotion: 0.0 for emotion in EmotionType}
        total_confidence = 0.0
        
        for module_name, output in outputs.items():
            weight = self.weights.get(module_name, 0.0)
            confidence = output.confidence
            
            # Use feature magnitude to estimate emotions
            feature_mean = np.mean(output.features) if output.features else 0.0
            feature_std = np.std(output.features) if len(output.features) > 1 else 0.0
            
            # Simple heuristic for emotion detection
            if feature_mean > 0.3:
                if feature_std > 0.4:
                    emotion_scores[EmotionType.EXCITED] += weight * confidence
                else:
                    emotion_scores[EmotionType.HAPPY] += weight * confidence
            elif feature_mean < -0.3:
                if feature_std > 0.4:
                    emotion_scores[EmotionType.ANGRY] += weight * confidence
                else:
                    emotion_scores[EmotionType.SAD] += weight * confidence
            elif feature_std > 0.5:
                emotion_scores[EmotionType.SURPRISED] += weight * confidence
            else:
                emotion_scores[EmotionType.NEUTRAL] += weight * confidence
            
            total_confidence += weight * confidence
        
        # Find primary emotion
        primary_emotion = max(emotion_scores.keys(), key=lambda e: emotion_scores[e])
        max_score = emotion_scores[primary_emotion]
        
        # Calculate confidence as ratio of max score to total
        emotion_confidence = max_score / max(total_confidence, 0.01)
        emotion_confidence = max(0.1, min(emotion_confidence, 0.95))
        
        return primary_emotion, emotion_confidence
    
    def _compute_valence_arousal(self, features: List[float], outputs: Dict[str, ModuleOutput]) -> tuple[float, float]:
        """Compute valence and arousal from fused features."""
        if not features:
            return 0.0, 0.0
        
        # Valence: positive/negative emotional dimension
        valence = np.mean(features)  # Average feature value
        valence = max(-1.0, min(valence, 1.0))  # Clamp to [-1, 1]
        
        # Arousal: emotional intensity/activation
        arousal = np.std(features) * 2.0  # Feature variance indicates intensity
        arousal = max(0.0, min(arousal, 1.0))  # Clamp to [0, 1]
        
        # Adjust based on module confidences
        avg_confidence = np.mean([output.confidence for output in outputs.values()])
        arousal *= avg_confidence  # Lower confidence -> lower arousal
        
        return float(valence), float(arousal)
    
    def _calculate_contributions(self, outputs: Dict[str, ModuleOutput]) -> Dict[str, float]:
        """Calculate actual contribution weights of each module."""
        contributions = {}
        total_weighted_confidence = 0.0
        
        # Calculate weighted confidence for each module
        for module_name, output in outputs.items():
            weight = self.weights.get(module_name, 0.0)
            weighted_confidence = weight * output.confidence
            contributions[module_name] = weighted_confidence
            total_weighted_confidence += weighted_confidence
        
        # Normalize to sum to 1.0
        if total_weighted_confidence > 0:
            for module_name in contributions:
                contributions[module_name] /= total_weighted_confidence
        
        return contributions
    
    def _create_empty_context(self) -> EmotionalContext:
        """Create empty emotional context for error cases."""
        return EmotionalContext(
            emotion_vector=[0.0] * self.target_dim,
            primary_emotion=EmotionType.NEUTRAL,
            emotion_confidence=0.0,
            valence=0.0,
            arousal=0.0,
            module_contributions={},
            timestamp=datetime.utcnow(),
            processing_latency_ms=0.0
        )
    
    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Update fusion weights at runtime."""
        self.weights = new_weights.copy()
        self._validate_weights()
        logger.info(f"Updated fusion weights: {self.weights}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fusion algorithm statistics."""
        return {
            'algorithm': 'weighted_ensemble',
            'weights': self.weights.copy(),
            'target_dim': self.target_dim,
            'supported_emotions': [e.value for e in EmotionType]
        }


class AdaptiveFusion(WeightedFusion):
    """
    Adaptive fusion that adjusts weights based on module performance.
    
    This extends WeightedFusion with the ability to adapt weights
    based on historical module confidence and accuracy.
    """
    
    def __init__(self, initial_weights: Dict[str, float], adaptation_rate: float = 0.1, **kwargs):
        super().__init__(initial_weights, **kwargs)
        self.adaptation_rate = adaptation_rate
        self.performance_history = {module: [] for module in initial_weights.keys()}
        self.adaptation_enabled = True
    
    def combine(self, module_outputs: Dict[str, ModuleOutput]) -> EmotionalContext:
        """Combine outputs and adapt weights based on performance."""
        # Get fusion result
        context = super().combine(module_outputs)
        
        # Update performance history
        if self.adaptation_enabled:
            self._update_performance_history(module_outputs)
            self._adapt_weights()
        
        return context
    
    def _update_performance_history(self, outputs: Dict[str, ModuleOutput]) -> None:
        """Update performance history for each module."""
        for module_name, output in outputs.items():
            if module_name in self.performance_history:
                # Use confidence as performance metric
                self.performance_history[module_name].append(output.confidence)
                
                # Keep only recent history (last 100 samples)
                if len(self.performance_history[module_name]) > 100:
                    self.performance_history[module_name] = self.performance_history[module_name][-100:]
    
    def _adapt_weights(self) -> None:
        """Adapt weights based on historical performance."""
        # Calculate average performance for each module
        avg_performance = {}
        for module_name, history in self.performance_history.items():
            if history:
                avg_performance[module_name] = np.mean(history)
            else:
                avg_performance[module_name] = 0.5  # Default performance
        
        # Calculate new weights based on relative performance
        total_performance = sum(avg_performance.values())
        if total_performance > 0:
            target_weights = {
                module: performance / total_performance
                for module, performance in avg_performance.items()
            }
            
            # Gradually adapt towards target weights
            for module_name in self.weights:
                if module_name in target_weights:
                    current_weight = self.weights[module_name]
                    target_weight = target_weights[module_name]
                    
                    # Exponential moving average adaptation
                    new_weight = ((1 - self.adaptation_rate) * current_weight + 
                                 self.adaptation_rate * target_weight)
                    
                    self.weights[module_name] = new_weight
            
            # Renormalize weights
            self._validate_weights()


def create_fusion(config: Dict[str, Any]) -> BaseFusion:
    """
    Factory function to create fusion instances based on configuration.
    
    Args:
        config: Fusion configuration
        
    Returns:
        Fusion instance
    """
    algorithm = config.get('algorithm', 'weighted_ensemble')
    weights = config.get('weights', {})
    
    if algorithm == 'weighted_ensemble':
        return WeightedFusion(weights)
    elif algorithm == 'adaptive':
        adaptation_rate = config.get('adaptation_rate', 0.1)
        return AdaptiveFusion(weights, adaptation_rate)
    else:
        raise ValueError(f"Unknown fusion algorithm: {algorithm}")