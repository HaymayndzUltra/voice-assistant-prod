"""
WP-08 Performance Optimizer
Automatic performance optimization and tuning recommendations
"""

import asyncio
import time
import gc
import threading
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OptimizationType(Enum):
    """Types of optimizations"""
    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    CACHE = "cache"
    ASYNC = "async"
    ALGORITHM = "algorithm"

class OptimizationPriority(Enum):
    """Priority levels for optimizations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    type: OptimizationType
    priority: OptimizationPriority
    function_name: str
    description: str
    estimated_improvement: float  # Percentage improvement
    implementation_difficulty: str  # easy, medium, hard
    code_example: Optional[str] = None
    resources_needed: List[str] = field(default_factory=list)
    
class PerformanceOptimizer:
    """Automatic performance optimization system"""
    
    def __init__(self):
        self._optimization_rules = []
        self._applied_optimizations = {}
        self._performance_baselines = {}
        self._lock = threading.RLock()
        
        # Register default optimization rules
        self._register_default_rules()
        
        logger.info("Performance optimizer initialized")
    
    def _register_default_rules(self):
        """Register default optimization rules"""
        
        # Memory optimization rules
        self.add_optimization_rule(
            lambda metrics: metrics.get('avg_memory_usage', 0) > 100 * 1024 * 1024,
            OptimizationType.MEMORY,
            OptimizationPriority.HIGH,
            "High memory usage detected",
            "Consider using generators, reducing object creation, or implementing memory pooling",
            75.0,
            "medium",
            """
# Use generators instead of lists for large datasets
def process_large_data():
    # Before: return [process(item) for item in large_dataset]
    # After: 
    for item in large_dataset:
        yield process(item)

# Use __slots__ for classes with many instances
class OptimizedClass:
    __slots__ = ['attr1', 'attr2']
    def __init__(self, attr1, attr2):
        self.attr1 = attr1
        self.attr2 = attr2
""",
            ["memory_profiler", "py-spy"]
        )
        
        # CPU optimization rules
        self.add_optimization_rule(
            lambda metrics: metrics.get('avg_execution_time', 0) > 1.0,
            OptimizationType.CPU,
            OptimizationPriority.HIGH,
            "Slow function execution detected",
            "Consider algorithm optimization, caching, or async processing",
            60.0,
            "medium",
            """
# Use async for I/O bound operations
async def optimized_function():
    tasks = [async_operation(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results

# Use caching for expensive computations
from functools import lru_cache
@lru_cache(maxsize=1000)
def expensive_computation(param):
    # Your computation here
    return result
""",
            ["asyncio", "caching"]
        )
        
        # Caching optimization rules
        self.add_optimization_rule(
            lambda metrics: metrics.get('total_calls', 0) > 100 and metrics.get('avg_execution_time', 0) > 0.1,
            OptimizationType.CACHE,
            OptimizationPriority.MEDIUM,
            "Frequently called function with significant execution time",
            "Implement caching to reduce redundant computations",
            80.0,
            "easy",
            """
from common.performance.caching import cached

@cached(cache_name="function_cache", ttl=3600)
async def cacheable_function(param):
    # Your expensive computation
    return result

# Or use manual caching
cache = get_cache("manual_cache")
async def manual_cached_function(param):
    result = await cache.get(param)
    if result is None:
        result = expensive_computation(param)
        await cache.set(param, result)
    return result
""",
            ["redis", "memcached"]
        )
        
        # Async optimization rules
        self.add_optimization_rule(
            lambda metrics: (
                'metadata' in metrics and 
                any('io' in str(meta).lower() for meta in metrics.get('metadata', {}).values())
            ),
            OptimizationType.ASYNC,
            OptimizationPriority.MEDIUM,
            "I/O operations detected in synchronous function",
            "Convert to async for better concurrency",
            50.0,
            "medium",
            """
# Convert sync I/O to async
import aiohttp
import aiofiles

# Before (synchronous)
def sync_function():
    response = requests.get(url)
    with open(file_path) as f:
        data = f.read()
    return process(response.json(), data)

# After (asynchronous) 
async def async_function():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            json_data = await response.json()
    
    async with aiofiles.open(file_path) as f:
        data = await f.read()
    
    return process(json_data, data)
""",
            ["aiohttp", "aiofiles", "asyncpg"]
        )
    
    def add_optimization_rule(self, 
                             condition: Callable[[Dict], bool],
                             opt_type: OptimizationType,
                             priority: OptimizationPriority,
                             description: str,
                             suggestion: str,
                             estimated_improvement: float,
                             difficulty: str,
                             code_example: str = None,
                             resources: List[str] = None):
        """Add custom optimization rule"""
        rule = {
            'condition': condition,
            'type': opt_type,
            'priority': priority,
            'description': description,
            'suggestion': suggestion,
            'estimated_improvement': estimated_improvement,
            'difficulty': difficulty,
            'code_example': code_example,
            'resources': resources or []
        }
        
        self._optimization_rules.append(rule)
        logger.info(f"Added optimization rule: {description}")
    
    def analyze_function(self, function_name: str, metrics: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Analyze function and provide optimization recommendations"""
        recommendations = []
        
        for rule in self._optimization_rules:
            try:
                if rule['condition'](metrics):
                    recommendation = OptimizationRecommendation(
                        type=rule['type'],
                        priority=rule['priority'],
                        function_name=function_name,
                        description=rule['description'],
                        estimated_improvement=rule['estimated_improvement'],
                        implementation_difficulty=rule['difficulty'],
                        code_example=rule['code_example'],
                        resources_needed=rule['resources']
                    )
                    recommendations.append(recommendation)
            except Exception as e:
                logger.warning(f"Error evaluating optimization rule: {e}")
        
        return recommendations
    
    def optimize_system(self, profiler_data: Dict[str, Any]) -> Dict[str, List[OptimizationRecommendation]]:
        """Analyze entire system and provide optimization recommendations"""
        all_recommendations = {}
        
        for function_name, function_data in profiler_data.items():
            if isinstance(function_data, list) and function_data:
                # Calculate aggregate metrics
                metrics = self._calculate_aggregate_metrics(function_data)
                recommendations = self.analyze_function(function_name, metrics)
                
                if recommendations:
                    all_recommendations[function_name] = recommendations
        
        return all_recommendations
    
    def _calculate_aggregate_metrics(self, profile_results: List) -> Dict[str, Any]:
        """Calculate aggregate metrics from profile results"""
        if not profile_results:
            return {}
        
        # Extract numeric metrics
        execution_times = []
        memory_usages = []
        cpu_usages = []
        
        for result in profile_results:
            if hasattr(result, 'execution_time'):
                execution_times.append(result.execution_time)
            if hasattr(result, 'memory_usage') and result.memory_usage is not None:
                memory_usages.append(result.memory_usage)
            if hasattr(result, 'cpu_usage') and result.cpu_usage is not None:
                cpu_usages.append(result.cpu_usage)
        
        metrics = {
            'total_calls': len(profile_results),
            'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
        }
        
        if memory_usages:
            metrics.update({
                'avg_memory_usage': sum(memory_usages) / len(memory_usages),
                'max_memory_usage': max(memory_usages),
                'total_memory_usage': sum(memory_usages)
            })
        
        if cpu_usages:
            metrics.update({
                'avg_cpu_usage': sum(cpu_usages) / len(cpu_usages),
                'max_cpu_usage': max(cpu_usages)
            })
        
        # Add metadata from results
        metadata = {}
        for result in profile_results:
            if hasattr(result, 'metadata') and result.metadata:
                metadata.update(result.metadata)
        
        metrics['metadata'] = metadata
        
        return metrics
    
    def get_prioritized_recommendations(self, 
                                      all_recommendations: Dict[str, List[OptimizationRecommendation]],
                                      max_recommendations: int = 10) -> List[OptimizationRecommendation]:
        """Get prioritized list of recommendations"""
        all_recs = []
        
        for function_name, recommendations in all_recommendations.items():
            all_recs.extend(recommendations)
        
        # Sort by priority and estimated improvement
        priority_scores = {
            OptimizationPriority.CRITICAL: 4,
            OptimizationPriority.HIGH: 3,
            OptimizationPriority.MEDIUM: 2,
            OptimizationPriority.LOW: 1
        }
        
        sorted_recs = sorted(
            all_recs,
            key=lambda r: (priority_scores[r.priority], r.estimated_improvement),
            reverse=True
        )
        
        return sorted_recs[:max_recommendations]
    
    def apply_automatic_optimizations(self) -> Dict[str, Any]:
        """Apply safe automatic optimizations"""
        applied = []
        errors = []
        
        # Automatic garbage collection optimization
        try:
            # Tune garbage collection
            gc.set_threshold(700, 10, 10)  # More aggressive GC
            applied.append("Tuned garbage collection thresholds")
        except Exception as e:
            errors.append(f"GC tuning failed: {e}")
        
        # Memory optimization
        try:
            # Force garbage collection
            collected = gc.collect()
            applied.append(f"Forced garbage collection, collected {collected} objects")
        except Exception as e:
            errors.append(f"GC failed: {e}")
        
        return {
            'applied_optimizations': applied,
            'errors': errors,
            'timestamp': time.time()
        }
    
    def benchmark_optimization(self, 
                             function: Callable,
                             optimization_function: Callable,
                             test_data: Any,
                             iterations: int = 100) -> Dict[str, Any]:
        """Benchmark the effect of an optimization"""
        
        # Benchmark original function
        original_times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            original_result = function(test_data)
            original_times.append(time.perf_counter() - start_time)
        
        # Benchmark optimized function
        optimized_times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            optimized_result = optimization_function(test_data)
            optimized_times.append(time.perf_counter() - start_time)
        
        # Calculate statistics
        original_avg = sum(original_times) / len(original_times)
        optimized_avg = sum(optimized_times) / len(optimized_times)
        
        improvement = ((original_avg - optimized_avg) / original_avg) * 100
        
        return {
            'original_avg_time': original_avg,
            'optimized_avg_time': optimized_avg,
            'improvement_percentage': improvement,
            'iterations': iterations,
            'results_match': original_result == optimized_result,
            'benchmark_timestamp': time.time()
        }
    
    def generate_optimization_report(self, profiler_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        
        # Get recommendations
        all_recommendations = self.optimize_system(profiler_data)
        prioritized = self.get_prioritized_recommendations(all_recommendations)
        
        # Apply automatic optimizations
        auto_optimizations = self.apply_automatic_optimizations()
        
        # Calculate potential impact
        total_functions = len(profiler_data)
        functions_needing_optimization = len(all_recommendations)
        
        estimated_total_improvement = sum(
            rec.estimated_improvement for rec in prioritized
        ) / len(prioritized) if prioritized else 0
        
        # Categorize recommendations
        by_type = {}
        by_priority = {}
        
        for rec in prioritized:
            # By type
            if rec.type not in by_type:
                by_type[rec.type] = []
            by_type[rec.type].append(rec)
            
            # By priority
            if rec.priority not in by_priority:
                by_priority[rec.priority] = []
            by_priority[rec.priority].append(rec)
        
        return {
            'timestamp': time.time(),
            'summary': {
                'total_functions_analyzed': total_functions,
                'functions_needing_optimization': functions_needing_optimization,
                'optimization_coverage': functions_needing_optimization / total_functions if total_functions > 0 else 0,
                'estimated_total_improvement': estimated_total_improvement
            },
            'prioritized_recommendations': [
                {
                    'function_name': rec.function_name,
                    'type': rec.type.value,
                    'priority': rec.priority.value,
                    'description': rec.description,
                    'estimated_improvement': rec.estimated_improvement,
                    'difficulty': rec.implementation_difficulty,
                    'resources_needed': rec.resources_needed
                }
                for rec in prioritized
            ],
            'recommendations_by_type': {
                opt_type.value: len(recs) for opt_type, recs in by_type.items()
            },
            'recommendations_by_priority': {
                priority.value: len(recs) for priority, recs in by_priority.items()
            },
            'automatic_optimizations': auto_optimizations,
            'implementation_plan': self._generate_implementation_plan(prioritized)
        }
    
    def _generate_implementation_plan(self, recommendations: List[OptimizationRecommendation]) -> List[Dict[str, Any]]:
        """Generate step-by-step implementation plan"""
        
        # Group by difficulty and priority
        easy_high = [r for r in recommendations if r.implementation_difficulty == "easy" and r.priority in [OptimizationPriority.HIGH, OptimizationPriority.CRITICAL]]
        medium_high = [r for r in recommendations if r.implementation_difficulty == "medium" and r.priority in [OptimizationPriority.HIGH, OptimizationPriority.CRITICAL]]
        easy_medium = [r for r in recommendations if r.implementation_difficulty == "easy" and r.priority == OptimizationPriority.MEDIUM]
        
        plan = []
        
        # Phase 1: Quick wins (easy + high priority)
        if easy_high:
            plan.append({
                'phase': 1,
                'name': "Quick Wins",
                'description': "Easy to implement, high impact optimizations",
                'estimated_duration': "1-2 days",
                'recommendations': [r.function_name for r in easy_high],
                'expected_improvement': sum(r.estimated_improvement for r in easy_high) / len(easy_high)
            })
        
        # Phase 2: Major improvements (medium difficulty + high priority)
        if medium_high:
            plan.append({
                'phase': 2,
                'name': "Major Improvements", 
                'description': "Medium effort, high impact optimizations",
                'estimated_duration': "1-2 weeks",
                'recommendations': [r.function_name for r in medium_high],
                'expected_improvement': sum(r.estimated_improvement for r in medium_high) / len(medium_high)
            })
        
        # Phase 3: Polishing (easy + medium priority)
        if easy_medium:
            plan.append({
                'phase': 3,
                'name': "Polishing",
                'description': "Easy optimizations for incremental improvements",
                'estimated_duration': "3-5 days",
                'recommendations': [r.function_name for r in easy_medium],
                'expected_improvement': sum(r.estimated_improvement for r in easy_medium) / len(easy_medium)
            })
        
        return plan

# Global optimizer instance
_optimizer: Optional[PerformanceOptimizer] = None

def get_optimizer() -> PerformanceOptimizer:
    """Get global optimizer instance"""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer

def optimize_function(function_name: str, metrics: Dict[str, Any]) -> List[OptimizationRecommendation]:
    """Optimize specific function"""
    optimizer = get_optimizer()
    return optimizer.analyze_function(function_name, metrics)

def run_system_optimization() -> Dict[str, Any]:
    """Run complete system optimization analysis"""
    from common.performance.profiler import get_profiler
    
    profiler = get_profiler()
    optimizer = get_optimizer()
    
    # Get profiling data
    profiler_data = profiler.get_profile_results()
    
    # Generate optimization report
    report = optimizer.generate_optimization_report(profiler_data)
    
    return report 