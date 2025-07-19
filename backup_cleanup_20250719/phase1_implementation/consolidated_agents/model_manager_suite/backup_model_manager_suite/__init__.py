"""
ModelManagerSuite - Consolidated Model Management Service
=======================================================

This package consolidates the following agents into a unified service:
- GGUFModelManager: Handles loading, unloading, and managing GGUF models
- PredictiveLoader: Predicts and preloads models based on usage patterns
- ModelEvaluationFramework: Tracks model performance and evaluation

Port: 7011 (Main service)
Health: 7111 (Health check)
Hardware: MainPC (RTX 4090)

CRITICAL REQUIREMENTS:
- Preserve ALL logic, error handling, imports, and patterns from source agents
- Maintain backward compatibility with all legacy endpoints
- Keep modular structure within the consolidated service
- Expose all legacy REST/gRPC endpoints for backward compatibility
"""

from .model_manager_suite import ModelManagerSuite

__all__ = ['ModelManagerSuite']
__version__ = '1.0.0' 