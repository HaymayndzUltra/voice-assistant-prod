"""Pydantic schemas for Affective Processing Center data models and configuration."""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from enum import Enum
import numpy as np
from pydantic import BaseModel, Field, validator


class EmotionType(str, Enum):
    """Supported emotion types."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"


class ModuleStatus(str, Enum):
    """Processing module status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Audio and Text Input Models
class AudioChunk(BaseModel):
    """Audio input for emotion processing."""
    data: bytes = Field(..., description="Raw audio data")
    sample_rate: int = Field(16000, description="Audio sample rate in Hz")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When audio was captured")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    
    class Config:
        arbitrary_types_allowed = True


class Transcript(BaseModel):
    """Text transcript for emotion processing."""
    text: str = Field(..., description="Transcribed text content")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Transcription confidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When transcript was generated")
    speaker_id: Optional[str] = Field(None, description="Speaker identifier")
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v


# Processing Results
class ModuleOutput(BaseModel):
    """Output from an individual emotion processing module."""
    module_name: str = Field(..., description="Name of the processing module")
    features: List[float] = Field(..., description="Extracted feature vector")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the result")
    processing_time_ms: float = Field(..., description="Time taken to process")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional module-specific metadata")


class EmotionalContext(BaseModel):
    """Unified emotional context vector (ECV) result."""
    emotion_vector: List[float] = Field(..., description="Fused emotion feature vector")
    primary_emotion: EmotionType = Field(..., description="Dominant detected emotion")
    emotion_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in primary emotion")
    valence: float = Field(..., ge=-1.0, le=1.0, description="Emotional valence (-1=negative, +1=positive)")
    arousal: float = Field(..., ge=0.0, le=1.0, description="Emotional arousal (0=calm, 1=excited)")
    module_contributions: Dict[str, float] = Field(..., description="Per-module contribution weights")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When ECV was generated")
    processing_latency_ms: float = Field(..., description="Total processing time")


# Module and Cache Models
class CacheEntry(BaseModel):
    """Feature cache entry."""
    key: str = Field(..., description="Cache key (hash of input)")
    features: List[float] = Field(..., description="Cached feature vector")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When cached")
    access_count: int = Field(1, description="Number of times accessed")
    
    class Config:
        arbitrary_types_allowed = True


class ModuleInfo(BaseModel):
    """Information about a processing module."""
    name: str = Field(..., description="Module name")
    requires: List[str] = Field(default_factory=list, description="Required input features")
    provides: str = Field(..., description="Output feature type")
    status: ModuleStatus = Field(ModuleStatus.PENDING, description="Current status")
    processing_time_ms: Optional[float] = Field(None, description="Last processing time")


# Configuration Models
class FusionConfig(BaseModel):
    """Fusion algorithm configuration."""
    algorithm: str = Field("weighted_ensemble", description="Fusion algorithm type")
    weights: Dict[str, float] = Field(..., description="Module weights for fusion")
    
    @validator('weights')
    def weights_sum_to_one(cls, v):
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f'Weights must sum to 1.0, got {total}')
        return v


class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    enabled_modules: List[str] = Field(..., description="List of enabled modules")
    fusion: FusionConfig = Field(..., description="Fusion configuration")


class AudioConfig(BaseModel):
    """Audio processing configuration."""
    sample_rate: int = Field(16000, description="Audio sample rate")
    frame_ms: int = Field(40, description="Frame duration in milliseconds")
    device: str = Field("default", description="Audio device")


class ModelConfig(BaseModel):
    """Model configuration for individual modules."""
    tone: Dict[str, Any] = Field(default_factory=dict, description="Tone detection model config")
    mood: Dict[str, Any] = Field(default_factory=dict, description="Mood analysis model config")
    empathy: Dict[str, Any] = Field(default_factory=dict, description="Empathy detection model config")
    voice_profile: Dict[str, Any] = Field(default_factory=dict, description="Voice profiling model config")
    synthesis: Dict[str, Any] = Field(default_factory=dict, description="Emotion synthesis model config")


class ResourceConfig(BaseModel):
    """Resource management configuration."""
    device: str = Field("cuda", description="Computing device (cuda/cpu)")
    max_concurrent_gpu_tasks: int = Field(4, description="Maximum concurrent GPU tasks")


class OutputConfig(BaseModel):
    """Output configuration."""
    zmq_pub_port: int = Field(5591, description="ZMQ publisher port")
    topic: str = Field("affect", description="ZMQ topic for publishing")


class ResilienceConfig(BaseModel):
    """Resilience configuration."""
    circuit_breaker: Dict[str, Any] = Field(..., description="Circuit breaker settings")
    bulkhead: Dict[str, Any] = Field(..., description="Bulkhead settings")


class APCConfig(BaseModel):
    """Complete APC configuration."""
    title: str = Field("AffectiveProcessingCenterConfig", description="Configuration title")
    version: str = Field("1.0", description="Configuration version")
    pipeline: PipelineConfig = Field(..., description="Pipeline configuration")
    audio: AudioConfig = Field(..., description="Audio configuration")
    models: ModelConfig = Field(..., description="Model configurations")
    resources: ResourceConfig = Field(..., description="Resource configuration")
    output: OutputConfig = Field(..., description="Output configuration")
    resilience: ResilienceConfig = Field(..., description="Resilience configuration")


# Transport Models
class SynthesisRequest(BaseModel):
    """Request for emotion synthesis."""
    text: str = Field(..., description="Text to synthesize")
    emotion: EmotionType = Field(..., description="Target emotion")
    intensity: float = Field(1.0, ge=0.0, le=2.0, description="Emotion intensity")
    voice_characteristics: Optional[Dict[str, Any]] = Field(None, description="Voice customization")


class SynthesisResponse(BaseModel):
    """Response from emotion synthesis."""
    audio_data: bytes = Field(..., description="Synthesized audio WAV data")
    sample_rate: int = Field(22050, description="Audio sample rate")
    duration_ms: int = Field(..., description="Audio duration")
    processing_time_ms: float = Field(..., description="Time taken to synthesize")


# Payload Union Type
Payload = Union[AudioChunk, Transcript]