#!/usr/bin/env python3
"""
Patch for ModelManagerSuite to add Hybrid LLM Routing
This patch adds select_backend() method and metrics reporting
"""

import re
import time
import logging
import requests
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('HybridLLMRouter')

@dataclass
class TaskMetadata:
    """Metadata for a task to determine routing"""
    task_type: str
    context_length: int
    estimated_tokens: int
    priority: str = "normal"
    user_preference: Optional[str] = None
    
@dataclass
class RoutingDecision:
    """Result of routing decision"""
    backend: str  # 'local' or 'cloud'
    model: str
    reason: str
    complexity_score: float
    timestamp: datetime

class HybridLLMRouter:
    """Hybrid LLM Routing logic for ModelManagerSuite"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.routing_rules = config.get('task_routing_rules', [])
        self.complexity_threshold = config.get('complexity_threshold', 0.7)
        self.cloud_endpoint = config.get('cloud_llm_endpoint', '')
        self.failover_strategy = config.get('failover_strategy', {})
        self.metrics_enabled = config.get('metrics_feedback', True)
        
        # Routing statistics
        self.routing_stats = {
            'total_requests': 0,
            'cloud_requests': 0,
            'local_requests': 0,
            'failovers': 0,
            'last_reset': datetime.now()
        }
        
    def select_backend(self, task_meta: TaskMetadata) -> RoutingDecision:
        """
        Select the appropriate backend (local or cloud) for a task
        
        Args:
            task_meta: Metadata about the task
            
        Returns:
            RoutingDecision with backend selection and reasoning
        """
        start_time = time.time()
        
        # Calculate complexity score
        complexity = self._calculate_complexity(task_meta)
        
        # Check user preference first
        if task_meta.user_preference:
            backend = task_meta.user_preference
            reason = f"User preference: {backend}"
        else:
            # Apply routing rules
            backend, reason = self._apply_routing_rules(task_meta, complexity)
            
        # Check resource availability
        if backend == 'local':
            if not self._check_local_resources(task_meta):
                # Failover to cloud
                backend = 'cloud'
                reason = "Local resources insufficient, failing over to cloud"
                self.routing_stats['failovers'] += 1
                
        elif backend == 'cloud':
            if not self._check_cloud_availability():
                # Failover to local
                backend = 'local'
                reason = "Cloud unavailable, failing over to local"
                self.routing_stats['failovers'] += 1
                
        # Select specific model
        model = self._select_model(backend, task_meta, complexity)
        
        # Create routing decision
        decision = RoutingDecision(
            backend=backend,
            model=model,
            reason=reason,
            complexity_score=complexity,
            timestamp=datetime.now()
        )
        
        # Update statistics
        self.routing_stats['total_requests'] += 1
        if backend == 'cloud':
            self.routing_stats['cloud_requests'] += 1
        else:
            self.routing_stats['local_requests'] += 1
            
        # Report metrics
        if self.metrics_enabled:
            self._report_metrics(decision, time.time() - start_time)
            
        logger.info(f"Routing decision: {backend} ({model}) - {reason}")
        
        return decision
        
    def _calculate_complexity(self, task_meta: TaskMetadata) -> float:
        """Calculate task complexity score (0.0 to 1.0)"""
        complexity = 0.0
        
        # Factor 1: Task type complexity
        task_complexities = {
            'code_generation': 0.9,
            'large_context_reasoning': 0.95,
            'training': 1.0,
            'fine_tuning': 1.0,
            'simple_chat': 0.2,
            'greeting': 0.1,
            'command_parsing': 0.3,
            'emotion_detection': 0.4,
            'translation': 0.5,
            'summarization': 0.6,
            'question_answering': 0.5,
        }
        
        # Check task type
        for task_type, score in task_complexities.items():
            if task_type in task_meta.task_type.lower():
                complexity = max(complexity, score)
                
        # Factor 2: Context length
        if task_meta.context_length > 8000:
            complexity = max(complexity, 0.9)
        elif task_meta.context_length > 4000:
            complexity = max(complexity, 0.7)
        elif task_meta.context_length > 2000:
            complexity = max(complexity, 0.5)
            
        # Factor 3: Estimated tokens
        if task_meta.estimated_tokens > 2000:
            complexity = max(complexity, 0.8)
        elif task_meta.estimated_tokens > 1000:
            complexity = max(complexity, 0.6)
            
        # Factor 4: Priority
        if task_meta.priority == 'high':
            complexity = min(complexity + 0.1, 1.0)
            
        return complexity
        
    def _apply_routing_rules(self, task_meta: TaskMetadata, complexity: float) -> Tuple[str, str]:
        """Apply routing rules to determine backend"""
        
        # Check specific routing rules first
        for rule in self.routing_rules:
            pattern = rule.get('pattern', '')
            if re.search(pattern, task_meta.task_type, re.IGNORECASE):
                backend = rule.get('preferred_backend', 'local')
                return backend, f"Matched rule: {pattern}"
                
        # Default complexity-based routing
        if complexity >= self.complexity_threshold:
            return 'cloud', f"High complexity ({complexity:.2f} >= {self.complexity_threshold})"
        else:
            return 'local', f"Low complexity ({complexity:.2f} < {self.complexity_threshold})"
            
    def _check_local_resources(self, task_meta: TaskMetadata) -> bool:
        """Check if local resources are sufficient for the task"""
        try:
            # Query VRAMOptimizerAgent
            vram_endpoint = "http://localhost:6572/vram/status"
            response = requests.get(vram_endpoint, timeout=2)
            
            if response.status_code == 200:
                vram_data = response.json()
                available_vram = vram_data.get('available_mb', 0)
                
                # Estimate required VRAM based on task
                required_vram = self._estimate_vram_requirement(task_meta)
                
                return available_vram >= required_vram
            else:
                # Conservative: assume resources available if can't check
                return True
                
        except Exception as e:
            logger.debug(f"Failed to check local resources: {e}")
            return True  # Optimistic default
            
    def _check_cloud_availability(self) -> bool:
        """Check if cloud LLM endpoint is available"""
        if not self.cloud_endpoint:
            return False
            
        try:
            # Simple health check
            response = requests.get(f"{self.cloud_endpoint}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Cloud endpoint unavailable: {e}")
            return False
            
    def _estimate_vram_requirement(self, task_meta: TaskMetadata) -> int:
        """Estimate VRAM requirement in MB"""
        base_requirement = 1000  # 1GB base
        
        # Add based on context length
        context_factor = task_meta.context_length / 1000  # KB of context
        vram_needed = base_requirement + (context_factor * 0.5)
        
        # Add based on task type
        if 'generation' in task_meta.task_type:
            vram_needed += 500
        elif 'reasoning' in task_meta.task_type:
            vram_needed += 300
            
        return int(vram_needed)
        
    def _select_model(self, backend: str, task_meta: TaskMetadata, complexity: float) -> str:
        """Select specific model based on backend and task"""
        if backend == 'cloud':
            # Cloud models
            if complexity > 0.9:
                return "gpt-4-turbo"
            elif complexity > 0.7:
                return "gpt-3.5-turbo"
            else:
                return "gpt-3.5-turbo"
                
        else:
            # Local models
            if complexity > 0.7:
                return "llama2-13b"
            elif complexity > 0.5:
                return "llama2-7b"
            elif complexity > 0.3:
                return "tinyllama-1.1b"
            else:
                return "tinyllama-1.1b"
                
    def _report_metrics(self, decision: RoutingDecision, latency: float):
        """Report routing metrics to ObservabilityHub"""
        try:
            obs_endpoint = "http://localhost:9000/metrics/llm_routing"
            
            metrics = {
                'timestamp': decision.timestamp.isoformat(),
                'backend': decision.backend,
                'model': decision.model,
                'complexity_score': decision.complexity_score,
                'reason': decision.reason,
                'latency_ms': int(latency * 1000),
                'stats': self.routing_stats
            }
            
            requests.post(obs_endpoint, json=metrics, timeout=2)
            
        except Exception as e:
            logger.debug(f"Failed to report metrics: {e}")
            
    def get_routing_stats(self) -> Dict:
        """Get current routing statistics"""
        total = self.routing_stats['total_requests']
        if total == 0:
            return self.routing_stats
            
        # Calculate percentages
        stats = self.routing_stats.copy()
        stats['cloud_percentage'] = (stats['cloud_requests'] / total) * 100
        stats['local_percentage'] = (stats['local_requests'] / total) * 100
        stats['failover_rate'] = (stats['failovers'] / total) * 100
        
        return stats
        
    def reset_stats(self):
        """Reset routing statistics"""
        self.routing_stats = {
            'total_requests': 0,
            'cloud_requests': 0,
            'local_requests': 0,
            'failovers': 0,
            'last_reset': datetime.now()
        }

# Patch function to integrate with ModelManagerSuite
def patch_model_manager_suite():
    """
    This function would be called to patch the existing ModelManagerSuite
    In practice, this would modify the actual ModelManagerSuite class
    """
    patch_code = '''
# Add to ModelManagerSuite.__init__()
self.hybrid_router = HybridLLMRouter(self.config.get('hybrid_llm_routing', {}))

# Add new method to ModelManagerSuite
def select_backend(self, task_meta: Dict) -> Dict:
    """Select backend for LLM task using hybrid routing"""
    # Convert dict to TaskMetadata
    meta = TaskMetadata(
        task_type=task_meta.get('type', 'unknown'),
        context_length=task_meta.get('context_length', 0),
        estimated_tokens=task_meta.get('estimated_tokens', 0),
        priority=task_meta.get('priority', 'normal'),
        user_preference=task_meta.get('user_preference')
    )
    
    # Get routing decision
    decision = self.hybrid_router.select_backend(meta)
    
    # Return as dict for compatibility
    return {
        'backend': decision.backend,
        'model': decision.model,
        'reason': decision.reason,
        'complexity_score': decision.complexity_score
    }

# Add endpoint to get routing stats
def get_routing_stats(self) -> Dict:
    """Get hybrid routing statistics"""
    return self.hybrid_router.get_routing_stats()
'''
    
    return patch_code

if __name__ == "__main__":
    # Example usage
    config = {
        'complexity_threshold': 0.7,
        'cloud_llm_endpoint': 'https://api.openai.com',
        'task_routing_rules': [
            {'pattern': 'code_generation', 'complexity': 0.9, 'preferred_backend': 'cloud'},
            {'pattern': 'simple_chat', 'complexity': 0.2, 'preferred_backend': 'local'}
        ]
    }
    
    router = HybridLLMRouter(config)
    
    # Test routing
    task = TaskMetadata(
        task_type='code_generation',
        context_length=5000,
        estimated_tokens=1500
    )
    
    decision = router.select_backend(task)
    print(f"Routing decision: {decision}")
    
    # Show patch code
    print("\nPatch code for ModelManagerSuite:")
    print(patch_model_manager_suite())