"""
Standardized Learning Pipeline Data Models

This module defines Pydantic models for all continuous learning and model evaluation
data structures. These models serve as a single source of truth for learning-related
data exchanged between agents across the distributed system.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from uuid import UUID
from pydantic import BaseModel, Field


class LearningOpportunity(BaseModel):
    """
    Represents a detected opportunity for model learning or improvement.
    
    This model captures instances where an agent might benefit from additional
    training, such as user corrections, negative feedback, or high uncertainty
    in responses.
    """
    opportunity_id: UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the learning opportunity")
    source_agent: str = Field(..., description="Name of the agent that identified the learning opportunity")
    interaction_data: Dict[str, Any] = Field(..., description="Relevant data from the interaction (e.g., user query, agent response, user correction)")
    opportunity_type: str = Field(..., description="Type of learning opportunity (e.g., 'user_correction', 'negative_feedback', 'high_uncertainty')")
    priority_score: float = Field(..., ge=0.0, le=1.0, description="Priority score for this learning opportunity (0.0 to 1.0)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the learning opportunity was created")
    status: str = Field(default='pending', description="Current status of the learning opportunity ('pending', 'processed', 'discarded')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "opportunity_id": "123e4567-e89b-12d3-a456-426614174000",
                "source_agent": "ChitChatAgent",
                "interaction_data": {
                    "user_query": "What's the capital of France?",
                    "agent_response": "The capital of France is Berlin.",
                    "user_correction": "No, it's Paris."
                },
                "opportunity_type": "user_correction",
                "priority_score": 0.85,
                "created_at": "2025-07-01T12:00:00Z",
                "status": "pending"
            }
        }


class TrainingCycle(BaseModel):
    """
    Represents a complete cycle of model training.
    
    This model captures all information related to a specific training run,
    including the learning opportunities used, resource allocation, and results.
    """
    cycle_id: UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the training cycle")
    model_name: str = Field(..., description="Name of the model being trained")
    learning_opportunities: List[UUID] = Field(..., description="List of learning opportunity IDs included in this training cycle")
    status: str = Field(default='pending', description="Current status of the training cycle ('pending', 'running', 'completed', 'failed')")
    start_time: Optional[datetime] = Field(default=None, description="Timestamp when the training cycle started")
    end_time: Optional[datetime] = Field(default=None, description="Timestamp when the training cycle completed")
    resource_allocation: Dict[str, Any] = Field(..., description="Resources allocated for this training cycle (e.g., GPU ID, VRAM)")
    hyperparameters: Dict[str, Any] = Field(..., description="Training hyperparameters (e.g., learning rate, epochs)")
    training_logs: Optional[str] = Field(default=None, description="Path to log file or the logs themselves")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cycle_id": "123e4567-e89b-12d3-a456-426614174001",
                "model_name": "ChitChatLLM_v2",
                "learning_opportunities": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "123e4567-e89b-12d3-a456-426614174002"
                ],
                "status": "completed",
                "start_time": "2025-07-01T13:00:00Z",
                "end_time": "2025-07-01T14:30:00Z",
                "resource_allocation": {
                    "gpu_id": 0,
                    "vram_mb": 8192
                },
                "hyperparameters": {
                    "learning_rate": 0.001,
                    "epochs": 3,
                    "batch_size": 8
                },
                "training_logs": "/logs/training/chitchat_v2_20250701.log"
            }
        }


class PerformanceMetric(BaseModel):
    """
    Represents a single performance metric measurement.
    
    This model captures individual performance measurements for agents and models,
    which can be used for monitoring and evaluation.
    """
    metric_id: UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the metric")
    agent_name: str = Field(..., description="Name of the agent being measured")
    metric_name: str = Field(..., description="Name of the metric being measured (e.g., 'response_time_ms', 'cpu_usage_percent')")
    value: float = Field(..., description="Numeric value of the metric")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the metric was recorded")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional contextual information (e.g., request ID)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric_id": "123e4567-e89b-12d3-a456-426614174003",
                "agent_name": "ChitChatAgent",
                "metric_name": "response_time_ms",
                "value": 245.7,
                "timestamp": "2025-07-01T12:05:00Z",
                "context": {
                    "request_id": "req-xyz-123",
                    "query_length": 25,
                    "response_length": 150
                }
            }
        }


class ModelEvaluationScore(BaseModel):
    """
    Represents a comprehensive evaluation of a trained model.
    
    This model captures the results of evaluating a model after training,
    including various performance metrics and comparison to previous versions.
    """
    evaluation_id: UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the evaluation")
    model_name: str = Field(..., description="Name of the model being evaluated")
    cycle_id: UUID = Field(..., description="ID of the training cycle that produced this model")
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Overall trust score for the model (0.0 to 1.0)")
    accuracy: Optional[float] = Field(default=None, description="Accuracy score if applicable")
    f1_score: Optional[float] = Field(default=None, description="F1 score if applicable")
    avg_latency_ms: float = Field(..., description="Average inference latency in milliseconds")
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the evaluation was performed")
    comparison_data: Optional[Dict[str, Any]] = Field(default=None, description="Comparison with previous model versions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "evaluation_id": "123e4567-e89b-12d3-a456-426614174004",
                "model_name": "ChitChatLLM_v2",
                "cycle_id": "123e4567-e89b-12d3-a456-426614174001",
                "trust_score": 0.92,
                "accuracy": 0.89,
                "f1_score": 0.87,
                "avg_latency_ms": 120.5,
                "evaluation_timestamp": "2025-07-01T15:00:00Z",
                "comparison_data": {
                    "previous_version": "ChitChatLLM_v1",
                    "trust_score_delta": 0.05,
                    "accuracy_delta": 0.03,
                    "latency_improvement_percent": 15.2
                }
            }
        } 