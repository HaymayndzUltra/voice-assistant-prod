"""Base module interface for emotion processing modules."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
import logging
import time
import asyncio
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import Payload, ModuleOutput, ModuleStatus, EmotionType
from core.cache import EmbeddingCache

logger = logging.getLogger(__name__)


class BaseModule(ABC):
    """
    Abstract base class for all emotion processing modules.
    
    Each module processes input payloads (audio or text) and produces
    feature vectors that contribute to the final emotional context.
    """
    
    # Class attributes to be overridden by subclasses
    requires: List[str] = []  # List of required input feature types
    provides: str = ""        # Output feature type this module provides
    
    def __init__(self, config: Dict[str, Any], device: str = "cuda"):
        """
        Initialize the base module.
        
        Args:
            config: Module-specific configuration
            device: Computing device (cuda/cpu)
        """
        self.config = config
        self.device = device
        self.status = ModuleStatus.PENDING
        self.name = self.__class__.__name__.lower().replace('module', '')
        
        # Performance tracking
        self._processing_times = []
        self._total_processed = 0
        self._last_error = None
        
        # Validate module definition
        self._validate_module_definition()
        
        logger.info(f"Module {self.name} initialized on {device}")
    
    def _validate_module_definition(self) -> None:
        """Validate that the module is properly defined."""
        if not self.provides:
            raise ValueError(f"Module {self.name} must define 'provides' attribute")
        
        if not isinstance(self.requires, list):
            raise ValueError(f"Module {self.name} 'requires' must be a list")
        
        # Check for circular dependencies (basic check)
        if self.provides in self.requires:
            raise ValueError(f"Module {self.name} cannot require its own output")
    
    @abstractmethod
    async def _extract_features(self, payload: Payload) -> List[float]:
        """
        Extract features from the input payload.
        
        This is the core processing method that must be implemented
        by each concrete module.
        
        Args:
            payload: Input audio chunk or transcript
            
        Returns:
            Feature vector as list of floats
        """
        pass
    
    @abstractmethod
    def get_confidence(self, features: List[float], payload: Payload) -> float:
        """
        Calculate confidence score for the extracted features.
        
        Args:
            features: Extracted feature vector
            payload: Original input payload
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
    
    async def process(self, payload: Payload, cache: EmbeddingCache) -> ModuleOutput:
        """
        Process input payload and return module output.
        
        This method handles caching, error handling, and performance tracking.
        
        Args:
            payload: Input payload to process
            cache: Feature cache for optimization
            
        Returns:
            Module output with features and metadata
        """
        start_time = time.time()
        self.status = ModuleStatus.RUNNING
        
        try:
            # Check cache first
            cached_features = cache.get(payload, self.name)
            if cached_features is not None:
                confidence = self.get_confidence(cached_features, payload)
                processing_time = (time.time() - start_time) * 1000
                
                self.status = ModuleStatus.COMPLETED
                
                return ModuleOutput(
                    module_name=self.name,
                    features=cached_features,
                    confidence=confidence,
                    processing_time_ms=processing_time,
                    metadata={'cached': True}
                )
            
            # Extract features
            features = await self._extract_features(payload)
            
            # Validate features
            if not features or not isinstance(features, list):
                raise ValueError(f"Invalid features returned by {self.name}")
            
            if not all(isinstance(f, (int, float)) for f in features):
                raise ValueError(f"Features must be numeric values in {self.name}")
            
            # Calculate confidence
            confidence = self.get_confidence(features, payload)
            
            # Cache the results
            cache.put(payload, self.name, features)
            
            # Update performance tracking
            processing_time = (time.time() - start_time) * 1000
            self._processing_times.append(processing_time)
            self._total_processed += 1
            
            # Keep only last 100 processing times for memory efficiency
            if len(self._processing_times) > 100:
                self._processing_times = self._processing_times[-100:]
            
            self.status = ModuleStatus.COMPLETED
            self._last_error = None
            
            logger.debug(f"Module {self.name} processed in {processing_time:.2f}ms")
            
            return ModuleOutput(
                module_name=self.name,
                features=features,
                confidence=confidence,
                processing_time_ms=processing_time,
                metadata={
                    'cached': False,
                    'feature_count': len(features),
                    'device': self.device
                }
            )
            
        except Exception as e:
            self.status = ModuleStatus.FAILED
            self._last_error = str(e)
            processing_time = (time.time() - start_time) * 1000
            
            logger.error(f"Module {self.name} failed: {e}")
            
            # Return empty output with error information
            return ModuleOutput(
                module_name=self.name,
                features=[],
                confidence=0.0,
                processing_time_ms=processing_time,
                metadata={
                    'error': str(e),
                    'failed': True
                }
            )
    
    def get_dependencies(self) -> Set[str]:
        """Get set of required dependencies."""
        return set(self.requires)
    
    def can_process(self, available_features: Set[str]) -> bool:
        """
        Check if module can process given available features.
        
        Args:
            available_features: Set of available feature types
            
        Returns:
            True if all required features are available
        """
        required_set = set(self.requires)
        return required_set.issubset(available_features)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this module."""
        if not self._processing_times:
            return {
                'module_name': self.name,
                'total_processed': self._total_processed,
                'avg_processing_time_ms': 0.0,
                'min_processing_time_ms': 0.0,
                'max_processing_time_ms': 0.0,
                'status': self.status.value,
                'last_error': self._last_error
            }
        
        return {
            'module_name': self.name,
            'total_processed': self._total_processed,
            'avg_processing_time_ms': sum(self._processing_times) / len(self._processing_times),
            'min_processing_time_ms': min(self._processing_times),
            'max_processing_time_ms': max(self._processing_times),
            'p95_processing_time_ms': sorted(self._processing_times)[int(0.95 * len(self._processing_times))],
            'status': self.status.value,
            'last_error': self._last_error
        }
    
    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self._processing_times.clear()
        self._total_processed = 0
        self._last_error = None
        logger.info(f"Reset statistics for module {self.name}")
    
    async def warmup(self) -> None:
        """
        Warm up the module (load models, initialize resources).
        
        This method can be overridden by subclasses that need
        expensive initialization (e.g., loading ML models).
        """
        logger.info(f"Module {self.name} warmup complete")
    
    async def shutdown(self) -> None:
        """
        Clean up module resources.
        
        This method can be overridden by subclasses that need
        cleanup (e.g., releasing GPU memory).
        """
        logger.info(f"Module {self.name} shutdown complete")
    
    def __repr__(self) -> str:
        """String representation of the module."""
        return f"{self.__class__.__name__}(provides='{self.provides}', requires={self.requires})"


class ModuleRegistry:
    """Registry for managing available emotion processing modules."""
    
    def __init__(self):
        self._modules: Dict[str, type] = {}
        self._instances: Dict[str, BaseModule] = {}
    
    def register(self, module_class: type) -> None:
        """Register a module class."""
        if not issubclass(module_class, BaseModule):
            raise ValueError(f"Module {module_class} must inherit from BaseModule")
        
        name = module_class.__name__.lower().replace('module', '')
        self._modules[name] = module_class
        logger.info(f"Registered module: {name}")
    
    def create_instance(self, name: str, config: Dict[str, Any], device: str = "cuda") -> BaseModule:
        """Create an instance of the specified module."""
        if name not in self._modules:
            raise ValueError(f"Unknown module: {name}")
        
        module_class = self._modules[name]
        instance = module_class(config, device)
        self._instances[name] = instance
        
        return instance
    
    def get_available_modules(self) -> List[str]:
        """Get list of available module names."""
        return list(self._modules.keys())
    
    def get_module_info(self, name: str) -> Dict[str, Any]:
        """Get information about a module."""
        if name not in self._modules:
            raise ValueError(f"Unknown module: {name}")
        
        module_class = self._modules[name]
        
        return {
            'name': name,
            'class': module_class.__name__,
            'provides': getattr(module_class, 'provides', ''),
            'requires': getattr(module_class, 'requires', []),
            'instantiated': name in self._instances
        }
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph of all registered modules."""
        graph = {}
        for name, module_class in self._modules.items():
            graph[name] = getattr(module_class, 'requires', [])
        return graph


# Global module registry
module_registry = ModuleRegistry()