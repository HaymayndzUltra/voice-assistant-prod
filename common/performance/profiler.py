"""
WP-08 Performance Profiler
Advanced profiling and performance monitoring for AI system optimization
"""

import asyncio
import time
import threading
import functools
import cProfile
import pstats
import tracemalloc
import psutil
import gc
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager, asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class ProfileType(Enum):
    """Types of profiling"""
    CPU = "cpu"
    MEMORY = "memory"
    TIME = "time"
    ASYNC = "async"
    CUSTOM = "custom"

@dataclass
class ProfileResult:
    """Result of a profiling session"""
    profile_type: ProfileType
    function_name: str
    execution_time: float
    cpu_usage: Optional[float] = None
    memory_usage: Optional[int] = None
    memory_peak: Optional[int] = None
    calls_count: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    gc_collections: Dict[int, int]
    timestamp: float = field(default_factory=time.time)

class PerformanceProfiler:
    """Advanced performance profiler"""
    
    def __init__(self):
        self._profiles: Dict[str, List[ProfileResult]] = {}
        self._active_profiles: Dict[str, Dict[str, Any]] = {}
        self._system_metrics: List[PerformanceMetrics] = []
        self._lock = threading.RLock()
        
        # Enable tracemalloc for memory profiling
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        # System monitoring
        self._process = psutil.Process()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info("Performance profiler initialized")
    
    @contextmanager
    def profile_cpu(self, name: str):
        """Profile CPU usage"""
        profiler = cProfile.Profile()
        start_time = time.time()
        
        profiler.enable()
        try:
            yield
        finally:
            profiler.disable()
            
            execution_time = time.time() - start_time
            
            # Extract stats
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            
            # Get CPU usage (approximation)
            cpu_usage = psutil.cpu_percent(interval=None)
            
            result = ProfileResult(
                profile_type=ProfileType.CPU,
                function_name=name,
                execution_time=execution_time,
                cpu_usage=cpu_usage,
                metadata={'stats': stats}
            )
            
            self._store_result(name, result)
    
    @contextmanager
    def profile_memory(self, name: str):
        """Profile memory usage"""
        # Take snapshot before
        snapshot_before = tracemalloc.take_snapshot()
        start_time = time.time()
        memory_before = self._process.memory_info().rss
        
        try:
            yield
        finally:
            # Take snapshot after
            snapshot_after = tracemalloc.take_snapshot()
            execution_time = time.time() - start_time
            memory_after = self._process.memory_info().rss
            
            # Calculate memory usage
            memory_usage = memory_after - memory_before
            
            # Get peak memory from tracemalloc
            top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
            memory_peak = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
            
            result = ProfileResult(
                profile_type=ProfileType.MEMORY,
                function_name=name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                memory_peak=memory_peak,
                metadata={
                    'memory_before': memory_before,
                    'memory_after': memory_after,
                    'top_allocations': top_stats[:10]
                }
            )
            
            self._store_result(name, result)
    
    @contextmanager
    def profile_time(self, name: str):
        """Profile execution time"""
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            execution_time = time.perf_counter() - start_time
            
            result = ProfileResult(
                profile_type=ProfileType.TIME,
                function_name=name,
                execution_time=execution_time
            )
            
            self._store_result(name, result)
    
    @asynccontextmanager
    async def profile_async(self, name: str):
        """Profile async function execution"""
        start_time = time.perf_counter()
        memory_before = self._process.memory_info().rss
        
        try:
            yield
        finally:
            execution_time = time.perf_counter() - start_time
            memory_after = self._process.memory_info().rss
            memory_usage = memory_after - memory_before
            
            result = ProfileResult(
                profile_type=ProfileType.ASYNC,
                function_name=name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                metadata={
                    'async_task': True,
                    'memory_before': memory_before,
                    'memory_after': memory_after
                }
            )
            
            self._store_result(name, result)
    
    def _store_result(self, name: str, result: ProfileResult):
        """Store profiling result"""
        with self._lock:
            if name not in self._profiles:
                self._profiles[name] = []
            
            self._profiles[name].append(result)
            
            # Keep only last 1000 results per function
            if len(self._profiles[name]) > 1000:
                self._profiles[name] = self._profiles[name][-1000:]
    
    def get_profile_results(self, name: str = None) -> Dict[str, List[ProfileResult]]:
        """Get profiling results"""
        with self._lock:
            if name:
                return {name: self._profiles.get(name, [])}
            return self._profiles.copy()
    
    def get_profile_summary(self, name: str) -> Dict[str, Any]:
        """Get summary statistics for a function"""
        with self._lock:
            results = self._profiles.get(name, [])
            if not results:
                return {}
            
            execution_times = [r.execution_time for r in results]
            memory_usages = [r.memory_usage for r in results if r.memory_usage is not None]
            cpu_usages = [r.cpu_usage for r in results if r.cpu_usage is not None]
            
            summary = {
                'function_name': name,
                'total_calls': len(results),
                'avg_execution_time': sum(execution_times) / len(execution_times),
                'min_execution_time': min(execution_times),
                'max_execution_time': max(execution_times),
                'total_execution_time': sum(execution_times)
            }
            
            if memory_usages:
                summary.update({
                    'avg_memory_usage': sum(memory_usages) / len(memory_usages),
                    'max_memory_usage': max(memory_usages),
                    'total_memory_usage': sum(memory_usages)
                })
            
            if cpu_usages:
                summary.update({
                    'avg_cpu_usage': sum(cpu_usages) / len(cpu_usages),
                    'max_cpu_usage': max(cpu_usages)
                })
            
            return summary
    
    def clear_profiles(self, name: str = None):
        """Clear profiling data"""
        with self._lock:
            if name:
                self._profiles.pop(name, None)
            else:
                self._profiles.clear()
    
    async def start_system_monitoring(self, interval: float = 5.0):
        """Start system performance monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_system(interval))
        logger.info(f"Started system monitoring with {interval}s interval")
    
    async def stop_system_monitoring(self):
        """Stop system performance monitoring"""
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped system monitoring")
    
    async def _monitor_system(self, interval: float):
        """Monitor system performance metrics"""
        while self._monitoring:
            try:
                # CPU and memory
                cpu_percent = self._process.cpu_percent()
                memory_info = self._process.memory_info()
                memory_percent = self._process.memory_percent()
                
                # System memory
                system_memory = psutil.virtual_memory()
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                
                # Network I/O
                network_io = psutil.net_io_counters()
                
                # Garbage collection stats
                gc_stats = {i: gc.get_count()[i] for i in range(len(gc.get_count()))}
                
                metrics = PerformanceMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    memory_used=memory_info.rss,
                    memory_available=system_memory.available,
                    disk_io_read=disk_io.read_bytes if disk_io else 0,
                    disk_io_write=disk_io.write_bytes if disk_io else 0,
                    network_io_sent=network_io.bytes_sent if network_io else 0,
                    network_io_recv=network_io.bytes_recv if network_io else 0,
                    gc_collections=gc_stats
                )
                
                with self._lock:
                    self._system_metrics.append(metrics)
                    
                    # Keep only last 1000 metrics
                    if len(self._system_metrics) > 1000:
                        self._system_metrics = self._system_metrics[-1000:]
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(interval)
    
    def get_system_metrics(self, last_n: int = 100) -> List[PerformanceMetrics]:
        """Get recent system metrics"""
        with self._lock:
            return self._system_metrics[-last_n:]
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system performance summary"""
        with self._lock:
            if not self._system_metrics:
                return {}
            
            recent_metrics = self._system_metrics[-100:]  # Last 100 data points
            
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_percent for m in recent_metrics]
            
            return {
                'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
                'max_cpu_percent': max(cpu_values),
                'avg_memory_percent': sum(memory_values) / len(memory_values),
                'max_memory_percent': max(memory_values),
                'current_memory_used': recent_metrics[-1].memory_used,
                'total_data_points': len(self._system_metrics),
                'monitoring_duration': recent_metrics[-1].timestamp - recent_metrics[0].timestamp if len(recent_metrics) > 1 else 0
            }

# Global profiler instance
_profiler: Optional[PerformanceProfiler] = None

def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler

# Decorators for profiling
def profile_cpu(name: str = None):
    """Decorator for CPU profiling"""
    def decorator(func):
        profile_name = name or f"{func.__module__}.{func.__name__}"
        profiler = get_profiler()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with profiler.profile_cpu(profile_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def profile_memory(name: str = None):
    """Decorator for memory profiling"""
    def decorator(func):
        profile_name = name or f"{func.__module__}.{func.__name__}"
        profiler = get_profiler()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with profiler.profile_memory(profile_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def profile_time(name: str = None):
    """Decorator for time profiling"""
    def decorator(func):
        profile_name = name or f"{func.__module__}.{func.__name__}"
        profiler = get_profiler()
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with profiler.profile_async(profile_name):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with profiler.profile_time(profile_name):
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator

def profile_all(name: str = None):
    """Decorator for comprehensive profiling (CPU, memory, time)"""
    def decorator(func):
        profile_name = name or f"{func.__module__}.{func.__name__}"
        profiler = get_profiler()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with profiler.profile_cpu(f"{profile_name}_cpu"):
                with profiler.profile_memory(f"{profile_name}_memory"):
                    with profiler.profile_time(f"{profile_name}_time"):
                        return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Performance analysis utilities
class PerformanceAnalyzer:
    """Analyze performance data and provide recommendations"""
    
    def __init__(self, profiler: PerformanceProfiler = None):
        self.profiler = profiler or get_profiler()
    
    def analyze_function_performance(self, function_name: str) -> Dict[str, Any]:
        """Analyze performance of a specific function"""
        summary = self.profiler.get_profile_summary(function_name)
        if not summary:
            return {"error": "No profiling data found"}
        
        recommendations = []
        
        # Check execution time
        avg_time = summary.get('avg_execution_time', 0)
        max_time = summary.get('max_execution_time', 0)
        
        if avg_time > 1.0:
            recommendations.append("Function has high average execution time (>1s)")
        
        if max_time > 5.0:
            recommendations.append("Function has very high peak execution time (>5s)")
        
        # Check memory usage
        if 'avg_memory_usage' in summary:
            avg_memory = summary['avg_memory_usage']
            if avg_memory > 100 * 1024 * 1024:  # 100MB
                recommendations.append("Function uses significant memory (>100MB)")
        
        # Check call frequency
        total_calls = summary.get('total_calls', 0)
        if total_calls > 1000:
            recommendations.append("Function called frequently - consider caching")
        
        analysis = {
            **summary,
            'recommendations': recommendations,
            'performance_score': self._calculate_performance_score(summary)
        }
        
        return analysis
    
    def _calculate_performance_score(self, summary: Dict[str, Any]) -> float:
        """Calculate performance score (0-100, higher is better)"""
        score = 100.0
        
        # Penalize slow functions
        avg_time = summary.get('avg_execution_time', 0)
        if avg_time > 0.1:
            score -= min(50, avg_time * 10)
        
        # Penalize memory-heavy functions
        if 'avg_memory_usage' in summary:
            avg_memory_mb = summary['avg_memory_usage'] / (1024 * 1024)
            if avg_memory_mb > 10:
                score -= min(30, avg_memory_mb)
        
        # Penalize high variance
        min_time = summary.get('min_execution_time', 0)
        max_time = summary.get('max_execution_time', 0)
        if min_time > 0:
            variance_ratio = max_time / min_time
            if variance_ratio > 5:
                score -= min(20, variance_ratio)
        
        return max(0, score)
    
    def get_top_bottlenecks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performance bottlenecks"""
        all_profiles = self.profiler.get_profile_results()
        
        bottlenecks = []
        for func_name in all_profiles:
            analysis = self.analyze_function_performance(func_name)
            if 'error' not in analysis:
                bottlenecks.append({
                    'function_name': func_name,
                    'performance_score': analysis['performance_score'],
                    'avg_execution_time': analysis.get('avg_execution_time', 0),
                    'total_calls': analysis.get('total_calls', 0),
                    'recommendations': analysis['recommendations']
                })
        
        # Sort by performance score (lower is worse)
        bottlenecks.sort(key=lambda x: x['performance_score'])
        
        return bottlenecks[:limit]
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        all_profiles = self.profiler.get_profile_results()
        system_summary = self.profiler.get_system_summary()
        bottlenecks = self.get_top_bottlenecks()
        
        total_functions = len(all_profiles)
        total_calls = sum(len(profiles) for profiles in all_profiles.values())
        
        # Calculate overall system health
        avg_scores = [
            self.analyze_function_performance(name).get('performance_score', 50)
            for name in all_profiles
        ]
        overall_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
        
        return {
            'timestamp': time.time(),
            'overall_performance_score': overall_score,
            'total_functions_profiled': total_functions,
            'total_function_calls': total_calls,
            'system_metrics': system_summary,
            'top_bottlenecks': bottlenecks,
            'recommendations': self._generate_global_recommendations(bottlenecks, system_summary)
        }
    
    def _generate_global_recommendations(self, bottlenecks: List[Dict], system_summary: Dict) -> List[str]:
        """Generate global performance recommendations"""
        recommendations = []
        
        # Check system-wide issues
        if system_summary.get('avg_cpu_percent', 0) > 80:
            recommendations.append("High CPU usage detected - consider optimizing CPU-intensive operations")
        
        if system_summary.get('avg_memory_percent', 0) > 80:
            recommendations.append("High memory usage detected - consider memory optimization")
        
        # Check function-level issues
        slow_functions = [b for b in bottlenecks if b['avg_execution_time'] > 1.0]
        if len(slow_functions) > 5:
            recommendations.append("Multiple slow functions detected - consider async optimization")
        
        frequent_functions = [b for b in bottlenecks if b['total_calls'] > 100]
        if len(frequent_functions) > 3:
            recommendations.append("Frequently called functions detected - consider caching")
        
        if not recommendations:
            recommendations.append("System performance looks good!")
        
        return recommendations 