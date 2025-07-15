# Unified Agent Design & Migration Plan - Part 2

## 4. UnifiedLearningAgent

### 4.1 Class Design

```python
"""
UnifiedLearningAgent - Consolidated learning pipeline
Merges: LearningManager, LearningOpportunityDetector, LearningOrchestrationService,
        ModelEvaluationFramework, ActiveLearningMonitor, LearningAdjusterAgent
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import numpy as np
from datetime import datetime

class LearningOpportunityType(Enum):
    CORRECTION = "correction"
    REINFORCEMENT = "reinforcement"
    NEW_KNOWLEDGE = "new_knowledge"
    PATTERN = "pattern"

@dataclass
class LearningOpportunity:
    id: str
    type: LearningOpportunityType
    interaction_data: Dict[str, Any]
    confidence_score: float
    timestamp: datetime
    processed: bool = False

@dataclass
class TrainingCycle:
    id: str
    opportunities: List[LearningOpportunity]
    model_version: str
    metrics: Dict[str, float]
    status: str

class UnifiedLearningAgent:
    """
    Unified learning system combining opportunity detection, orchestration,
    evaluation, monitoring, and parameter adjustment.
    
    Features:
    - Real-time learning opportunity detection (from LearningOpportunityDetector)
    - Training cycle orchestration (from LearningOrchestrationService)
    - Model evaluation framework (from ModelEvaluationFramework)
    - Active learning monitoring (from ActiveLearningMonitor)
    - Dynamic parameter adjustment (from LearningAdjusterAgent)
    - Integrated A/B testing framework
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Core configuration
        self.port = config.get('port', 5580)
        self.health_check_port = config.get('health_check_port', 6580)
        
        # Learning parameters
        self.learning_config = config.get('learning', {
            'min_confidence_threshold': 0.7,
            'batch_size': 32,
            'learning_rate_initial': 0.001,
            'decay_rate': 0.95
        })
        
        # Evaluation settings
        self.evaluation_config = config.get('evaluation', {
            'metrics': ['accuracy', 'f1', 'perplexity'],
            'test_split': 0.2,
            'cross_validation_folds': 5
        })
        
        # Parameter adjustment
        self.adjustment_config = config.get('adjustment', {
            'optimization_algorithm': 'bayesian',
            'exploration_rate': 0.1
        })
        
        # Initialize components
        self._init_database()
        self._init_models()
        self._init_monitoring()
        self._start_background_tasks()
    
    # --- Opportunity Detection (from LearningOpportunityDetector) ---
    
    async def detect_opportunities(self, interaction: Dict[str, Any]) -> List[LearningOpportunity]:
        """Detect learning opportunities from user interactions"""
        opportunities = []
        
        # Check for explicit corrections
        if correction := self._detect_correction(interaction):
            opportunities.append(correction)
            
        # Check for implicit feedback
        if feedback := self._detect_implicit_feedback(interaction):
            opportunities.append(feedback)
            
        # Check for new patterns
        if pattern := self._detect_pattern(interaction):
            opportunities.append(pattern)
            
        return opportunities
    
    def _detect_correction(self, interaction: Dict[str, Any]) -> Optional[LearningOpportunity]:
        """Detect explicit corrections in user feedback"""
        # Implementation from LearningOpportunityDetector._detect_explicit_correction()
        pass
    
    def _detect_implicit_feedback(self, interaction: Dict[str, Any]) -> Optional[LearningOpportunity]:
        """Detect implicit feedback signals"""
        # Combines logic from:
        # - _detect_implicit_correction()
        # - _detect_positive_reinforcement()
        pass
    
    # --- Training Orchestration (from LearningOrchestrationService) ---
    
    async def orchestrate_training_cycle(self, opportunities: List[LearningOpportunity]) -> TrainingCycle:
        """Orchestrate a complete training cycle"""
        # Create training batch
        batch = self._create_training_batch(opportunities)
        
        # Prepare data
        train_data, val_data = self._prepare_data(batch)
        
        # Execute training
        model_version = await self._train_model(train_data, val_data)
        
        # Evaluate results
        metrics = await self._evaluate_model(model_version, val_data)
        
        # Create cycle record
        cycle = TrainingCycle(
            id=self._generate_id(),
            opportunities=opportunities,
            model_version=model_version,
            metrics=metrics,
            status='completed'
        )
        
        return cycle
    
    # --- Model Evaluation (from ModelEvaluationFramework) ---
    
    async def evaluate_model(self, model_version: str, test_data: Any) -> Dict[str, float]:
        """Comprehensive model evaluation"""
        metrics = {}
        
        # Standard metrics
        for metric_name in self.evaluation_config['metrics']:
            score = await self._calculate_metric(metric_name, model_version, test_data)
            metrics[metric_name] = score
            
        # Cross-validation
        cv_scores = await self._cross_validate(model_version, test_data)
        metrics['cv_mean'] = np.mean(cv_scores)
        metrics['cv_std'] = np.std(cv_scores)
        
        # Log results
        self._log_evaluation(model_version, metrics)
        
        return metrics
    
    # --- Active Monitoring (from ActiveLearningMonitor) ---
    
    def monitor_learning_effectiveness(self) -> Dict[str, Any]:
        """Monitor learning system effectiveness"""
        return {
            'opportunities_detected': self._get_opportunity_stats(),
            'training_cycles': self._get_training_stats(),
            'model_improvements': self._get_improvement_trends(),
            'resource_usage': self._get_resource_stats()
        }
    
    def get_high_value_interactions(self, limit: int = 100) -> List[Dict]:
        """Get high-value interactions for active learning"""
        # Implementation from ActiveLearningMonitor._is_high_value_interaction()
        pass
    
    # --- Parameter Adjustment (from LearningAdjusterAgent) ---
    
    def adjust_parameters(self, performance_data: Dict[str, float]) -> Dict[str, Any]:
        """Dynamically adjust learning parameters based on performance"""
        current_params = self._get_current_parameters()
        
        # Analyze performance trends
        trends = self._analyze_parameter_trends(performance_data)
        
        # Optimize parameters
        new_params = self._optimize_parameters(current_params, trends)
        
        # Apply adjustments
        self._apply_parameter_updates(new_params)
        
        return new_params
    
    def register_parameter(self, name: str, config: Dict[str, Any]):
        """Register new adjustable parameter"""
        # Implementation from LearningAdjusterAgent.register_parameter()
        pass
    
    # --- Session Management (from LearningManager) ---
    
    def create_learning_session(self, config: Dict[str, Any]) -> str:
        """Create new learning session"""
        # Implementation from LearningManager._create_learning_session()
        pass
    
    def get_learning_rate(self, session_id: str) -> float:
        """Get current learning rate for session"""
        # Implementation from LearningManager._adjust_learning_rate()
        pass
    
    # --- Health & Monitoring ---
    
    def get_health_status(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            'status': 'healthy',
            'components': {
                'detector': self._check_detector_health(),
                'orchestrator': self._check_orchestrator_health(),
                'evaluator': self._check_evaluator_health(),
                'adjuster': self._check_adjuster_health()
            },
            'metrics': self.monitor_learning_effectiveness(),
            'timestamp': datetime.now().isoformat()
        }
```

### 4.2 Configuration Example

```yaml
UnifiedLearningAgent:
  port: 5580
  health_check_port: 6580
  
  # Learning configuration
  learning:
    min_confidence_threshold: 0.7
    batch_size: 32
    learning_rate_initial: 0.001
    decay_rate: 0.95
    max_epochs: 100
    early_stopping_patience: 10
    
  # Opportunity detection
  detection:
    correction_patterns:
      - "no, I meant"
      - "actually"
      - "correction:"
    implicit_threshold: 0.8
    pattern_min_occurrences: 3
    
  # Evaluation settings
  evaluation:
    metrics: ["accuracy", "f1", "perplexity", "bleu"]
    test_split: 0.2
    cross_validation_folds: 5
    benchmark_datasets:
      - "internal_test_set"
      - "public_benchmark"
      
  # Parameter adjustment
  adjustment:
    optimization_algorithm: "bayesian"
    exploration_rate: 0.1
    parameter_bounds:
      learning_rate: [0.0001, 0.1]
      batch_size: [16, 128]
      dropout_rate: [0.0, 0.5]
```

### 4.3 Testing Plan

1. **Opportunity Detection Tests**
   - Test correction pattern matching
   - Test confidence scoring
   - Test deduplication

2. **Training Pipeline Tests**
   - Test data preparation
   - Test model versioning
   - Test rollback capability

3. **Evaluation Tests**
   - Test metric calculations
   - Test cross-validation
   - Test benchmark comparisons

4. **Parameter Adjustment Tests**
   - Test optimization algorithms
   - Test parameter bounds
   - Test convergence

---

## 5. UnifiedTranslationService

### 5.1 Class Design

```python
"""
UnifiedTranslationService - Consolidated translation pipeline
Merges: FixedStreamingTranslation, NLLBAdapter, TranslationService, 
        StreamingLanguageAnalyzer
"""

from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass
import asyncio
from abc import ABC, abstractmethod

@dataclass
class TranslationRequest:
    text: str
    source_lang: Optional[str]
    target_lang: str
    streaming: bool = False
    context: Optional[str] = None

class TranslationAdapter(ABC):
    """Base adapter for translation models"""
    @abstractmethod
    async def translate(self, request: TranslationRequest) -> str:
        pass
    
    @abstractmethod
    def supports_language_pair(self, source: str, target: str) -> bool:
        pass

class UnifiedTranslationService:
    """
    Unified translation service with multiple model adapters, streaming support,
    language detection, and shared caching.
    
    Features:
    - Multiple translation backends (from NLLBAdapter)
    - Streaming translation (from FixedStreamingTranslation)
    - Automatic language detection (from StreamingLanguageAnalyzer)
    - Unified caching layer (from TranslationService)
    - Adaptive timeout management
    - Load balancing across models
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Core configuration
        self.port = config.get('port', 5584)
        self.health_check_port = config.get('health_check_port', 6584)
        
        # Model configurations
        self.model_configs = config.get('models', {
            'nllb': {'enabled': True, 'priority': 1},
            'opus': {'enabled': True, 'priority': 2},
            'whisper': {'enabled': False, 'priority': 3}
        })
        
        # Cache configuration
        self.cache_config = config.get('cache', {
            'max_size': 10000,
            'ttl': 3600,
            'similarity_threshold': 0.95
        })
        
        # Performance settings
        self.performance_config = config.get('performance', {
            'timeout_base': 5.0,
            'timeout_per_char': 0.01,
            'max_concurrent': 100
        })
        
        # Initialize components
        self._init_adapters()
        self._init_cache()
        self._init_language_detector()
        self._init_load_balancer()
    
    # --- Core Translation (unified interface) ---
    
    async def translate(self, request: TranslationRequest) -> str:
        """Translate text with automatic model selection"""
        # Check cache first
        if cached := await self._check_cache(request):
            return cached
            
        # Detect source language if not provided
        if not request.source_lang:
            request.source_lang = await self._detect_language(request.text)
            
        # Select best adapter
        adapter = self._select_adapter(request)
        
        # Perform translation
        result = await adapter.translate(request)
        
        # Cache result
        await self._cache_result(request, result)
        
        return result
    
    async def translate_stream(self, request: TranslationRequest) -> AsyncIterator[str]:
        """Stream translation results"""
        # Implementation from FixedStreamingTranslation
        request.streaming = True
        
        # Select streaming-capable adapter
        adapter = self._select_streaming_adapter(request)
        
        async for chunk in adapter.translate_stream(request):
            yield chunk
    
    # --- Language Detection (from StreamingLanguageAnalyzer) ---
    
    async def detect_language(self, text: str) -> Dict[str, float]:
        """Detect language with confidence scores"""
        # Use multiple detection methods
        results = await asyncio.gather(
            self._detect_with_langdetect(text),
            self._detect_with_fasttext(text),
            self._detect_with_context(text)
        )
        
        # Aggregate results
        return self._aggregate_detection_results(results)
    
    async def analyze_language_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[Dict]:
        """Analyze language from audio stream"""
        # Implementation from StreamingLanguageAnalyzer
        async for chunk in audio_stream:
            # Process audio chunk
            text = await self._transcribe_chunk(chunk)
            
            # Detect language
            lang = await self._detect_language(text)
            
            # Yield analysis
            yield {
                'text': text,
                'language': lang,
                'confidence': self._calculate_confidence(lang)
            }
    
    # --- Adapter Management ---
    
    def _select_adapter(self, request: TranslationRequest) -> TranslationAdapter:
        """Select best adapter for request"""
        eligible = []
        
        for name, adapter in self.adapters.items():
            if adapter.supports_language_pair(request.source_lang, request.target_lang):
                priority = self.model_configs[name]['priority']
                load = self._get_adapter_load(name)
                score = priority / (1 + load)
                eligible.append((score, adapter))
                
        # Return adapter with best score
        eligible.sort(reverse=True)
        return eligible[0][1]
    
    # --- Caching (from TranslationService) ---
    
    async def _check_cache(self, request: TranslationRequest) -> Optional[str]:
        """Check cache with fuzzy matching"""
        # Exact match
        if exact := await self.cache.get(self._cache_key(request)):
            return exact
            
        # Fuzzy match
        if self.cache_config['similarity_threshold'] < 1.0:
            similar = await self._find_similar_cached(request)
            if similar:
                return similar
                
        return None
    
    # --- Performance Optimization (from FixedStreamingTranslation) ---
    
    def _calculate_timeout(self, text_length: int) -> float:
        """Calculate adaptive timeout based on text length"""
        base = self.performance_config['timeout_base']
        per_char = self.performance_config['timeout_per_char']
        return base + (text_length * per_char)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all adapters"""
        return {
            adapter_name: {
                'requests': self._get_request_count(adapter_name),
                'avg_latency': self._get_avg_latency(adapter_name),
                'error_rate': self._get_error_rate(adapter_name),
                'cache_hit_rate': self._get_cache_hit_rate(adapter_name)
            }
            for adapter_name in self.adapters
        }
    
    # --- Health & Monitoring ---
    
    def get_health_status(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            'status': 'healthy',
            'adapters': {
                name: adapter.get_health()
                for name, adapter in self.adapters.items()
            },
            'cache': self._get_cache_stats(),
            'performance': self.get_service_stats(),
            'supported_languages': self._get_supported_languages()
        }
```

### 5.2 Migration Plan

1. **Adapter Migration**
   - Implement adapter interface for each model
   - Migrate model loading logic
   - Test language pair support

2. **Cache Migration**
   - Export existing cache entries
   - Import with new key format
   - Verify cache hit rates

3. **Client Migration**
   - Update client libraries
   - Add streaming support
   - Deprecate old endpoints

---

## 6. UnifiedVisionProcessingAgent

### 6.1 Class Design

```python
"""
UnifiedVisionProcessingAgent - Consolidated vision processing
Merges: FaceRecognitionAgent, VisionProcessingAgent
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass
import cv2

@dataclass
class VisionTask:
    id: str
    type: str  # 'face_recognition', 'object_detection', 'scene_description'
    image: np.ndarray
    priority: int
    metadata: Dict[str, Any]

class UnifiedVisionProcessingAgent:
    """
    Unified vision processing combining face recognition and general vision tasks
    with shared GPU resources and model caching.
    
    Features:
    - Real-time face recognition (from FaceRecognitionAgent)
    - General image description (from VisionProcessingAgent)
    - Shared model loading and GPU management
    - Privacy zone enforcement
    - Unified preprocessing pipeline
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Core configuration
        self.port = config.get('port', 5610)
        self.health_check_port = config.get('health_check_port', 6610)
        
        # Model configurations
        self.model_config = config.get('models', {
            'face_detection': 'retinaface',
            'face_recognition': 'arcface',
            'object_detection': 'yolov8',
            'scene_description': 'blip2'
        })
        
        # Privacy settings
        self.privacy_config = config.get('privacy', {
            'zones_enabled': True,
            'blur_faces': False,
            'store_embeddings': True
        })
        
        # Performance settings
        self.performance_config = config.get('performance', {
            'batch_size': 8,
            'gpu_memory_fraction': 0.7,
            'model_cache_size': 5
        })
        
        # Initialize components
        self._init_models()
        self._init_privacy_manager()
        self._init_task_queue()
    
    # --- Unified Processing Interface ---
    
    async def process_image(self, task: VisionTask) -> Dict[str, Any]:
        """Process image based on task type"""
        # Apply privacy zones if enabled
        if self.privacy_config['zones_enabled']:
            task.image = self._apply_privacy_zones(task.image)
            
        # Route to appropriate processor
        if task.type == 'face_recognition':
            return await self._process_face_recognition(task)
        elif task.type == 'object_detection':
            return await self._process_object_detection(task)
        elif task.type == 'scene_description':
            return await self._process_scene_description(task)
        else:
            raise ValueError(f"Unknown task type: {task.type}")
    
    # --- Face Recognition (from FaceRecognitionAgent) ---
    
    async def _process_face_recognition(self, task: VisionTask) -> Dict[str, Any]:
        """Process face recognition task"""
        # Detect faces
        faces = await self._detect_faces(task.image)
        
        # Extract embeddings
        embeddings = await self._extract_face_embeddings(faces)
        
        # Match against database
        matches = await self._match_faces(embeddings)
        
        # Analyze emotions
        emotions = await self._analyze_emotions(faces)
        
        # Check liveness
        liveness = await self._check_liveness(faces, task.metadata)
        
        return {
            'faces': [
                {
                    'bbox': face.bbox,
                    'identity': match.identity if match else None,
                    'confidence': match.confidence if match else 0.0,
                    'emotion': emotion,
                    'liveness': liveness_score
                }
                for face, match, emotion, liveness_score 
                in zip(faces, matches, emotions, liveness)
            ]
        }
    
    # --- General Vision (from VisionProcessingAgent) ---
    
    async def _process_scene_description(self, task: VisionTask) -> Dict[str, Any]:
        """Generate scene description"""
        # Use BLIP2 or similar model
        description = await self._generate_description(task.image)
        
        # Extract key objects
        objects = await self._extract_objects(task.image)
        
        # Analyze scene attributes
        attributes = await self._analyze_scene_attributes(task.image)
        
        return {
            'description': description,
            'objects': objects,
            'attributes': attributes
        }
    
    # --- Shared Model Management ---
    
    async def _load_model(self, model_name: str):
        """Load model with caching"""
        if model_name in self.model_cache:
            return self.model_cache[model_name]
            
        # Check cache size
        if len(self.model_cache) >= self.performance_config['model_cache_size']:
            # Evict least recently used
            self._evict_lru_model()
            
        # Load model
        model = await self._load_model_from_disk(model_name)
        self.model_cache[model_name] = model
        
        return model
    
    # --- Privacy Management (from FaceRecognitionAgent) ---
    
    def _apply_privacy_zones(self, image: np.ndarray) -> np.ndarray:
        """Apply privacy zones to image"""
        for zone in self.privacy_zones:
            if zone.is_active():
                image = zone.apply(image)
        return image
    
    # --- Batch Processing ---
    
    async def process_batch(self, tasks: List[VisionTask]) -> List[Dict[str, Any]]:
        """Process multiple tasks efficiently"""
        # Group by task type
        grouped = self._group_tasks_by_type(tasks)
        
        results = []
        for task_type, group in grouped.items():
            # Process group in batch
            batch_results = await self._process_batch_by_type(task_type, group)
            results.extend(batch_results)
            
        return results
    
    # --- Health & Monitoring ---
    
    def get_health_status(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            'status': 'healthy',
            'models_loaded': list(self.model_cache.keys()),
            'gpu_memory_used': self._get_gpu_memory_usage(),
            'task_queue_size': self.task_queue.qsize(),
            'privacy_zones_active': len([z for z in self.privacy_zones if z.is_active()]),
            'performance_metrics': {
                'avg_face_detection_time': self._get_avg_metric('face_detection_time'),
                'avg_description_time': self._get_avg_metric('description_time'),
                'cache_hit_rate': self._get_cache_hit_rate()
            }
        }
```

### 6.2 Testing Plan

1. **Face Recognition Tests**
   - Test detection accuracy
   - Test embedding quality
   - Test liveness detection
   - Test privacy zone application

2. **Vision Processing Tests**
   - Test object detection
   - Test scene description
   - Test batch processing

3. **Performance Tests**
   - Test GPU memory management
   - Test model caching
   - Test concurrent requests

### 6.3 Migration Strategy

1. **Model Migration**
   - Convert existing models to unified format
   - Test model compatibility
   - Benchmark performance

2. **Database Migration**
   - Migrate face embeddings
   - Update privacy zones
   - Verify data integrity

3. **API Migration**
   - Provide compatibility layer
   - Update client libraries
   - Deprecate old endpoints

---

## Migration Timeline Summary

### Overall Timeline: 6-8 weeks

**Weeks 1-2: Preparation**
- Set up test environments
- Prepare migration scripts
- Train team

**Weeks 3-4: Shadow Deployment**
- Deploy unified agents in shadow mode
- Compare outputs
- Fix discrepancies

**Weeks 5-6: Gradual Migration**
- Start with 5% traffic
- Increase gradually
- Monitor closely

**Weeks 7-8: Cleanup**
- Decommission old agents
- Archive data
- Update documentation

### Success Criteria

1. **Performance**
   - Latency within 10% of baseline
   - Throughput meets or exceeds current
   - Resource usage optimized

2. **Reliability**
   - Error rate < 0.1%
   - 99.9% uptime maintained
   - Automatic failover working

3. **Functionality**
   - All features preserved
   - No data loss
   - Backward compatibility maintained

---

## Conclusion

The unified agent architecture significantly reduces system complexity while maintaining all functionality. The detailed designs provide clear implementation paths, and the gradual migration strategy minimizes risk. Each unified agent is designed to be more maintainable, performant, and feature-rich than the individual agents it replaces.