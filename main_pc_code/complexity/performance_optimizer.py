#!/usr/bin/env python3
"""
Performance Optimizer - Automated Performance Analysis and Optimization
Provides comprehensive performance profiling with bottleneck detection and optimization.

Features:
- Automated performance profiling and bottleneck detection
- Memory usage analysis and optimization suggestions
- CPU performance monitoring and optimization
- I/O performance analysis and async optimization
- Database query performance optimization
- Caching strategy recommendations and implementation
"""
from __future__ import annotations
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cProfile
import pstats
import tracemalloc
import psutil
import time
import asyncio
import threading
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
from enum import Enum

# Core imports
from common.core.base_agent import BaseAgent

# Event system imports
from events.memory_events import (
    MemoryEventType, create_memory_operation, MemoryType
)
from events.event_bus import publish_memory_event

# Try to import performance monitoring libraries
try:
    import psutil
    PROFILING_LIBS_AVAILABLE = True
except ImportError:
    PROFILING_LIBS_AVAILABLE = False
    print("Profiling libraries not available - install with: pip install psutil memory-profiler")

class PerformanceIssueType(Enum):
    """Types of performance issues"""
    CPU_BOTTLENECK = "cpu_bottleneck"
    MEMORY_LEAK = "memory_leak"
    IO_BOTTLENECK = "io_bottleneck"
    DATABASE_SLOW_QUERY = "database_slow_query"
    INEFFICIENT_ALGORITHM = "inefficient_algorithm"
    MISSING_CACHING = "missing_caching"
    BLOCKING_OPERATION = "blocking_operation"
    MEMORY_FRAGMENTATION = "memory_fragmentation"

class OptimizationStrategy(Enum):
    """Optimization strategies"""
    CACHING = "caching"
    ASYNC_OPTIMIZATION = "async_optimization"
    ALGORITHM_IMPROVEMENT = "algorithm_improvement"
    MEMORY_OPTIMIZATION = "memory_optimization"
    DATABASE_OPTIMIZATION = "database_optimization"
    IO_OPTIMIZATION = "io_optimization"
    PARALLELIZATION = "parallelization"

class PerformanceLevel(Enum):
    """Performance levels"""
    EXCELLENT = "excellent"     # < 90th percentile
    GOOD = "good"              # 90-95th percentile
    FAIR = "fair"              # 95-99th percentile
    POOR = "poor"              # > 99th percentile

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    thread_count: int
    
    @property
    def overall_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        # Weighted scoring
        cpu_score = max(0, 100 - self.cpu_percent)
        memory_score = max(0, 100 - self.memory_percent)
        
        # Weight CPU and memory more heavily
        return (cpu_score * 0.6) + (memory_score * 0.4)

@dataclass
class PerformanceBottleneck:
    """Performance bottleneck detection"""
    bottleneck_id: str
    issue_type: PerformanceIssueType
    severity: str  # low, medium, high, critical
    function_name: str
    file_path: str
    line_number: int
    execution_time_ms: float
    memory_usage_mb: float
    call_count: int
    percentage_of_total: float
    detected_at: datetime = field(default_factory=datetime.now)
    
    @property
    def performance_impact(self) -> str:
        if self.percentage_of_total > 50:
            return "critical"
        elif self.percentage_of_total > 20:
            return "high"
        elif self.percentage_of_total > 10:
            return "medium"
        else:
            return "low"

@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    recommendation_id: str
    strategy: OptimizationStrategy
    target_function: str
    target_file: str
    description: str
    expected_improvement: str
    implementation_effort: str
    code_example: str
    prerequisites: List[str] = field(default_factory=list)
    estimated_impact: float = 0.0  # 0-100 percentage improvement

@dataclass
class ProfilingSession:
    """Profiling session record"""
    session_id: str
    started_at: datetime
    duration_seconds: float
    profile_type: str  # cpu, memory, combined
    total_calls: int
    total_time: float
    bottlenecks_found: int
    completed_at: Optional[datetime] = None

class PerformanceOptimizer(BaseAgent):
    """
    Comprehensive performance optimization system.
    
    Provides automated profiling, bottleneck detection,
    and optimization recommendations for improved performance.
    """
    
    def __init__(self, 
                 monitoring_interval_seconds: int = 60,
                 enable_continuous_profiling: bool = True,
                 profiling_duration_seconds: int = 30,
                 **kwargs):
        super().__init__(name="PerformanceOptimizer", **kwargs)
        
        # Configuration
        self.monitoring_interval = monitoring_interval_seconds
        self.enable_continuous_profiling = enable_continuous_profiling
        self.profiling_duration = profiling_duration_seconds
        
        # Performance data
        self.performance_metrics_history: deque = deque(maxlen=1000)
        self.detected_bottlenecks: Dict[str, PerformanceBottleneck] = {}
        self.optimization_recommendations: Dict[str, OptimizationRecommendation] = {}
        self.profiling_sessions: List[ProfilingSession] = []
        
        # System monitoring
        if PROFILING_LIBS_AVAILABLE:
            self.process = psutil.Process()
        else:
            self.process = None
        
        # Performance baselines
        self.performance_baselines = self._initialize_performance_baselines()
        
        # Optimization patterns
        self.optimization_patterns = self._initialize_optimization_patterns()
        
        # Metrics
        self.performance_stats = {
            'total_profiling_sessions': 0,
            'bottlenecks_detected': 0,
            'optimizations_suggested': 0,
            'average_cpu_usage': 0.0,
            'average_memory_usage': 0.0,
            'performance_trend': 'stable'
        }
        
        # Initialize system
        if PROFILING_LIBS_AVAILABLE:
            self._start_performance_monitoring()
        
        self.logger.info("Performance Optimizer initialized")
    
    def _initialize_performance_baselines(self) -> Dict[str, float]:
        """Initialize performance baselines"""
        return {
            'max_cpu_percent': 80.0,
            'max_memory_percent': 85.0,
            'max_function_time_ms': 1000.0,
            'max_memory_per_function_mb': 100.0,
            'acceptable_response_time_ms': 500.0
        }
    
    def _initialize_optimization_patterns(self) -> List[Dict[str, Any]]:
        """Initialize optimization patterns"""
        return [
            {
                'pattern': r'for\s+\w+\s+in\s+.*\.keys\(\):',
                'strategy': OptimizationStrategy.ALGORITHM_IMPROVEMENT,
                'description': 'Use direct dictionary iteration instead of .keys()',
                'improvement': 'for key in dict: instead of for key in dict.keys():'
            },
            {
                'pattern': r'time\.sleep\(',
                'strategy': OptimizationStrategy.ASYNC_OPTIMIZATION,
                'description': 'Replace time.sleep with async await asyncio.sleep',
                'improvement': 'await asyncio.sleep() for better concurrency'
            },
            {
                'pattern': r'open\([^)]+\)\.read\(\)',
                'strategy': OptimizationStrategy.IO_OPTIMIZATION,
                'description': 'Use context manager for file operations',
                'improvement': 'with open() as f: content = f.read()'
            },
            {
                'pattern': r'list\(filter\(',
                'strategy': OptimizationStrategy.ALGORITHM_IMPROVEMENT,
                'description': 'Use list comprehension instead of filter',
                'improvement': '[x for x in items if condition]'
            },
            {
                'pattern': r'\.join\(\[.*for.*in.*\]\)',
                'strategy': OptimizationStrategy.MEMORY_OPTIMIZATION,
                'description': 'Use generator expression in join',
                'improvement': '.join(x for x in items) instead of .join([x for x in items])'
            }
        ]
    
    def _start_performance_monitoring(self) -> None:
        """Start background performance monitoring"""
        # System metrics monitoring thread
        metrics_thread = threading.Thread(target=self._performance_metrics_loop, daemon=True)
        metrics_thread.start()
        
        # Continuous profiling thread (if enabled)
        if self.enable_continuous_profiling:
            profiling_thread = threading.Thread(target=self._continuous_profiling_loop, daemon=True)
            profiling_thread.start()
        
        # Bottleneck detection thread
        detection_thread = threading.Thread(target=self._bottleneck_detection_loop, daemon=True)
        detection_thread.start()
        
        # Optimization recommendation thread
        optimization_thread = threading.Thread(target=self._optimization_recommendation_loop, daemon=True)
        optimization_thread.start()
    
    def _performance_metrics_loop(self) -> None:
        """Background performance metrics collection"""
        while self.running:
            try:
                metrics = self._collect_system_metrics()
                if metrics:
                    self.performance_metrics_history.append(metrics)
                    self._analyze_performance_trends()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Performance metrics collection error: {e}")
                time.sleep(self.monitoring_interval * 2)
    
    def _continuous_profiling_loop(self) -> None:
        """Background continuous profiling"""
        while self.running:
            try:
                # Run periodic profiling sessions
                session = self._run_profiling_session("continuous")
                if session:
                    self._analyze_profiling_results(session)
                
                time.sleep(300)  # Profile every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Continuous profiling error: {e}")
                time.sleep(600)
    
    def _bottleneck_detection_loop(self) -> None:
        """Background bottleneck detection"""
        while self.running:
            try:
                self._detect_performance_bottlenecks()
                
                time.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                self.logger.error(f"Bottleneck detection error: {e}")
                time.sleep(300)
    
    def _optimization_recommendation_loop(self) -> None:
        """Background optimization recommendation generation"""
        while self.running:
            try:
                self._generate_optimization_recommendations()
                
                time.sleep(600)  # Generate recommendations every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Optimization recommendation error: {e}")
                time.sleep(1200)
    
    def _collect_system_metrics(self) -> Optional[PerformanceMetrics]:
        """Collect current system performance metrics"""
        if not self.process:
            return None
        
        try:
            # CPU and memory
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # I/O statistics
            io_counters = self.process.io_counters()
            disk_read_mb = io_counters.read_bytes / 1024 / 1024
            disk_write_mb = io_counters.write_bytes / 1024 / 1024
            
            # Network statistics (if available)
            try:
                net_io = psutil.net_io_counters()
                network_sent_mb = net_io.bytes_sent / 1024 / 1024
                network_recv_mb = net_io.bytes_recv / 1024 / 1024
            except:
                network_sent_mb = 0.0
                network_recv_mb = 0.0
            
            # Process and thread counts
            process_count = len(psutil.pids())
            thread_count = self.process.num_threads()
            
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                process_count=process_count,
                thread_count=thread_count
            )
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            return None
    
    async def run_performance_analysis(self, target_function: Optional[Callable] = None,
                                     duration_seconds: int = 30) -> ProfilingSession:
        """Run comprehensive performance analysis"""
        session_id = self._generate_session_id()
        
        self.logger.info(f"Starting performance analysis session: {session_id}")
        
        session = ProfilingSession(
            session_id=session_id,
            started_at=datetime.now(),
            duration_seconds=duration_seconds,
            profile_type="combined",
            total_calls=0,
            total_time=0.0,
            bottlenecks_found=0
        )
        
        try:
            # Start memory tracing
            tracemalloc.start()
            
            # CPU profiling
            profiler = cProfile.Profile()
            profiler.enable()
            
            if target_function:
                # Profile specific function
                start_time = time.time()
                target_function()
                execution_time = time.time() - start_time
                
                session.total_time = execution_time
            else:
                # Profile for specified duration
                await asyncio.sleep(duration_seconds)
                session.total_time = duration_seconds
            
            # Stop profiling
            profiler.disable()
            
            # Analyze results
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            
            # Count total calls
            session.total_calls = stats.total_calls
            
            # Memory analysis
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Detect bottlenecks from profiling data
            bottlenecks = self._analyze_profiling_stats(stats, session_id)
            session.bottlenecks_found = len(bottlenecks)
            
            # Store bottlenecks
            for bottleneck in bottlenecks:
                self.detected_bottlenecks[bottleneck.bottleneck_id] = bottleneck
            
            session.completed_at = datetime.now()
            self.profiling_sessions.append(session)
            
            # Update metrics
            self.performance_stats['total_profiling_sessions'] += 1
            self.performance_stats['bottlenecks_detected'] += len(bottlenecks)
            
            # Publish profiling event
            profiling_event = create_memory_operation(
                operation_type=MemoryEventType.MEMORY_CREATED,
                memory_id=f"profiling_session_{session_id}",
                memory_type=MemoryType.PROCEDURAL,
                content=f"Performance analysis: {len(bottlenecks)} bottlenecks found",
                source_agent=self.name,
                machine_id=self._get_machine_id()
            )
            
            publish_memory_event(profiling_event)
            
            self.logger.info(f"Performance analysis completed: {session_id} ({len(bottlenecks)} bottlenecks)")
            
            return session
            
        except Exception as e:
            session.completed_at = datetime.now()
            self.logger.error(f"Performance analysis failed: {e}")
            raise
    
    def _run_profiling_session(self, session_type: str) -> Optional[ProfilingSession]:
        """Run a profiling session"""
        try:
            return asyncio.run(self.run_performance_analysis(duration_seconds=self.profiling_duration))
        except Exception as e:
            self.logger.error(f"Profiling session failed: {e}")
            return None
    
    def _analyze_profiling_stats(self, stats: pstats.Stats, session_id: str) -> List[PerformanceBottleneck]:
        """Analyze profiling statistics to detect bottlenecks"""
        bottlenecks = []
        
        # Get the top time-consuming functions
        stats_data = stats.get_stats()
        total_time = stats.total_tt
        
        for func_key, (cc, nc, tt, ct, callers) in stats_data.items():
            filename, line_number, function_name = func_key
            
            # Skip built-in and library functions
            if 'site-packages' in filename or '<built-in>' in filename:
                continue
            
            # Calculate percentage of total time
            time_percentage = (tt / total_time) * 100 if total_time > 0 else 0
            
            # Only consider significant functions
            if time_percentage > 1.0:  # More than 1% of total time
                severity = self._determine_bottleneck_severity(time_percentage, tt, cc)
                issue_type = self._classify_performance_issue(function_name, tt, cc)
                
                bottleneck = PerformanceBottleneck(
                    bottleneck_id=self._generate_bottleneck_id(session_id, function_name),
                    issue_type=issue_type,
                    severity=severity,
                    function_name=function_name,
                    file_path=filename,
                    line_number=line_number,
                    execution_time_ms=tt * 1000,  # Convert to milliseconds
                    memory_usage_mb=0.0,  # Would need memory profiler for this
                    call_count=cc,
                    percentage_of_total=time_percentage
                )
                
                bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def _determine_bottleneck_severity(self, time_percentage: float, total_time: float, call_count: int) -> str:
        """Determine severity of performance bottleneck"""
        if time_percentage > 30 or total_time > 5.0:
            return "critical"
        elif time_percentage > 15 or total_time > 2.0:
            return "high"
        elif time_percentage > 5 or total_time > 1.0:
            return "medium"
        else:
            return "low"
    
    def _classify_performance_issue(self, function_name: str, execution_time: float, call_count: int) -> PerformanceIssueType:
        """Classify the type of performance issue"""
        # Simple heuristics for classification
        if 'sleep' in function_name.lower():
            return PerformanceIssueType.BLOCKING_OPERATION
        elif 'query' in function_name.lower() or 'sql' in function_name.lower():
            return PerformanceIssueType.DATABASE_SLOW_QUERY
        elif 'read' in function_name.lower() or 'write' in function_name.lower():
            return PerformanceIssueType.IO_BOTTLENECK
        elif call_count > 1000:
            return PerformanceIssueType.INEFFICIENT_ALGORITHM
        elif execution_time > 2.0:
            return PerformanceIssueType.CPU_BOTTLENECK
        else:
            return PerformanceIssueType.CPU_BOTTLENECK
    
    def _analyze_performance_trends(self) -> None:
        """Analyze performance trends from historical data"""
        if len(self.performance_metrics_history) < 10:
            return
        
        recent_metrics = list(self.performance_metrics_history)[-10:]
        older_metrics = list(self.performance_metrics_history)[-20:-10] if len(self.performance_metrics_history) >= 20 else []
        
        # Calculate averages
        recent_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        recent_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        
        if older_metrics:
            older_cpu = sum(m.cpu_percent for m in older_metrics) / len(older_metrics)
            older_memory = sum(m.memory_percent for m in older_metrics) / len(older_metrics)
            
            # Determine trend
            cpu_trend = recent_cpu - older_cpu
            memory_trend = recent_memory - older_memory
            
            if cpu_trend > 10 or memory_trend > 10:
                self.performance_stats['performance_trend'] = 'degrading'
            elif cpu_trend < -5 and memory_trend < -5:
                self.performance_stats['performance_trend'] = 'improving'
            else:
                self.performance_stats['performance_trend'] = 'stable'
        
        # Update average usage
        self.performance_stats['average_cpu_usage'] = recent_cpu
        self.performance_stats['average_memory_usage'] = recent_memory
    
    def _detect_performance_bottlenecks(self) -> None:
        """Detect performance bottlenecks from current metrics"""
        if not self.performance_metrics_history:
            return
        
        current_metrics = self.performance_metrics_history[-1]
        
        # CPU bottleneck detection
        if current_metrics.cpu_percent > self.performance_baselines['max_cpu_percent']:
            self._create_real_time_bottleneck(
                PerformanceIssueType.CPU_BOTTLENECK,
                f"High CPU usage: {current_metrics.cpu_percent:.1f}%",
                current_metrics.cpu_percent
            )
        
        # Memory bottleneck detection
        if current_metrics.memory_percent > self.performance_baselines['max_memory_percent']:
            self._create_real_time_bottleneck(
                PerformanceIssueType.MEMORY_LEAK,
                f"High memory usage: {current_metrics.memory_percent:.1f}%",
                current_metrics.memory_percent
            )
    
    def _create_real_time_bottleneck(self, issue_type: PerformanceIssueType, 
                                   description: str, metric_value: float) -> None:
        """Create a real-time bottleneck detection"""
        bottleneck_id = f"realtime_{issue_type.value}_{int(time.time())}"
        
        severity = "critical" if metric_value > 95 else "high" if metric_value > 85 else "medium"
        
        bottleneck = PerformanceBottleneck(
            bottleneck_id=bottleneck_id,
            issue_type=issue_type,
            severity=severity,
            function_name="system_monitoring",
            file_path="real_time_detection",
            line_number=0,
            execution_time_ms=0.0,
            memory_usage_mb=metric_value if issue_type == PerformanceIssueType.MEMORY_LEAK else 0.0,
            call_count=1,
            percentage_of_total=metric_value
        )
        
        self.detected_bottlenecks[bottleneck_id] = bottleneck
        self.logger.warning(f"Real-time bottleneck detected: {description}")
    
    def _generate_optimization_recommendations(self) -> None:
        """Generate optimization recommendations based on detected bottlenecks"""
        new_recommendations = 0
        
        for bottleneck in self.detected_bottlenecks.values():
            # Skip if we already have a recommendation for this bottleneck
            recommendation_key = f"{bottleneck.function_name}_{bottleneck.issue_type.value}"
            
            if recommendation_key in self.optimization_recommendations:
                continue
            
            recommendation = self._create_optimization_recommendation(bottleneck)
            if recommendation:
                self.optimization_recommendations[recommendation.recommendation_id] = recommendation
                new_recommendations += 1
        
        if new_recommendations > 0:
            self.performance_stats['optimizations_suggested'] += new_recommendations
            self.logger.info(f"Generated {new_recommendations} new optimization recommendations")
    
    def _create_optimization_recommendation(self, bottleneck: PerformanceBottleneck) -> Optional[OptimizationRecommendation]:
        """Create optimization recommendation for a bottleneck"""
        recommendation_id = f"opt_{bottleneck.bottleneck_id}"
        
        # Choose strategy based on issue type
        if bottleneck.issue_type == PerformanceIssueType.CPU_BOTTLENECK:
            strategy = OptimizationStrategy.ALGORITHM_IMPROVEMENT
            description = "Optimize algorithm or add caching to reduce CPU usage"
            code_example = """
# Before:
for item in large_list:
    expensive_calculation(item)

# After:
import functools

@functools.lru_cache(maxsize=1000)
def expensive_calculation(item):
    # cached calculation
    pass
"""
        elif bottleneck.issue_type == PerformanceIssueType.IO_BOTTLENECK:
            strategy = OptimizationStrategy.ASYNC_OPTIMIZATION
            description = "Convert blocking I/O operations to async"
            code_example = """
# Before:
with open('file.txt', 'r') as f:
    data = f.read()

# After:
import aiofiles
async with aiofiles.open('file.txt', 'r') as f:
    data = await f.read()
"""
        elif bottleneck.issue_type == PerformanceIssueType.MEMORY_LEAK:
            strategy = OptimizationStrategy.MEMORY_OPTIMIZATION
            description = "Optimize memory usage and fix potential leaks"
            code_example = """
# Before:
result = []
for item in huge_dataset:
    result.append(process(item))

# After:
def process_generator():
    for item in huge_dataset:
        yield process(item)
"""
        elif bottleneck.issue_type == PerformanceIssueType.DATABASE_SLOW_QUERY:
            strategy = OptimizationStrategy.DATABASE_OPTIMIZATION
            description = "Optimize database queries with indexing or query rewriting"
            code_example = """
# Before:
SELECT * FROM large_table WHERE column LIKE '%pattern%'

# After:
CREATE INDEX idx_column ON large_table(column);
SELECT * FROM large_table WHERE column = 'exact_match'
"""
        else:
            strategy = OptimizationStrategy.CACHING
            description = "Add caching to reduce repeated calculations"
            code_example = "# Consider adding @lru_cache decorator or Redis caching"
        
        # Estimate impact based on bottleneck severity and percentage
        if bottleneck.severity == "critical":
            estimated_impact = min(80.0, bottleneck.percentage_of_total)
        elif bottleneck.severity == "high":
            estimated_impact = min(60.0, bottleneck.percentage_of_total)
        else:
            estimated_impact = min(40.0, bottleneck.percentage_of_total)
        
        return OptimizationRecommendation(
            recommendation_id=recommendation_id,
            strategy=strategy,
            target_function=bottleneck.function_name,
            target_file=bottleneck.file_path,
            description=description,
            expected_improvement=f"{estimated_impact:.1f}% performance improvement",
            implementation_effort=self._estimate_implementation_effort(strategy),
            code_example=code_example.strip(),
            estimated_impact=estimated_impact
        )
    
    def _estimate_implementation_effort(self, strategy: OptimizationStrategy) -> str:
        """Estimate implementation effort for optimization strategy"""
        effort_map = {
            OptimizationStrategy.CACHING: "2-4 hours",
            OptimizationStrategy.ASYNC_OPTIMIZATION: "4-8 hours",
            OptimizationStrategy.ALGORITHM_IMPROVEMENT: "1-3 days",
            OptimizationStrategy.MEMORY_OPTIMIZATION: "4-8 hours",
            OptimizationStrategy.DATABASE_OPTIMIZATION: "2-4 hours",
            OptimizationStrategy.IO_OPTIMIZATION: "2-4 hours",
            OptimizationStrategy.PARALLELIZATION: "1-2 days"
        }
        
        return effort_map.get(strategy, "4-8 hours")
    
    def _analyze_profiling_results(self, session: ProfilingSession) -> None:
        """Analyze profiling session results"""
        # This would perform deeper analysis of profiling results
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import secrets
        return f"session_{secrets.token_urlsafe(12)}"
    
    def _generate_bottleneck_id(self, session_id: str, function_name: str) -> str:
        """Generate unique bottleneck ID"""
        import hashlib
        content = f"{session_id}_{function_name}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance analysis report"""
        # Current performance status
        current_performance = "unknown"
        if self.performance_metrics_history:
            latest_metrics = self.performance_metrics_history[-1]
            score = latest_metrics.overall_score
            
            if score >= 80:
                current_performance = "excellent"
            elif score >= 60:
                current_performance = "good"
            elif score >= 40:
                current_performance = "fair"
            else:
                current_performance = "poor"
        
        # Top bottlenecks
        top_bottlenecks = sorted(
            self.detected_bottlenecks.values(),
            key=lambda x: x.percentage_of_total,
            reverse=True
        )[:10]
        
        # Top recommendations
        top_recommendations = sorted(
            self.optimization_recommendations.values(),
            key=lambda x: x.estimated_impact,
            reverse=True
        )[:10]
        
        return {
            'performance_summary': {
                'current_status': current_performance,
                'total_profiling_sessions': len(self.profiling_sessions),
                'bottlenecks_detected': len(self.detected_bottlenecks),
                'recommendations_available': len(self.optimization_recommendations),
                'performance_trend': self.performance_stats['performance_trend']
            },
            'current_metrics': {
                'average_cpu_usage': self.performance_stats['average_cpu_usage'],
                'average_memory_usage': self.performance_stats['average_memory_usage'],
                'latest_metrics': asdict(self.performance_metrics_history[-1]) if self.performance_metrics_history else None
            },
            'top_bottlenecks': [
                {
                    'bottleneck_id': bottleneck.bottleneck_id,
                    'issue_type': bottleneck.issue_type.value,
                    'severity': bottleneck.severity,
                    'function_name': bottleneck.function_name,
                    'file_path': bottleneck.file_path,
                    'execution_time_ms': bottleneck.execution_time_ms,
                    'percentage_of_total': bottleneck.percentage_of_total,
                    'performance_impact': bottleneck.performance_impact
                }
                for bottleneck in top_bottlenecks
            ],
            'top_recommendations': [
                {
                    'recommendation_id': rec.recommendation_id,
                    'strategy': rec.strategy.value,
                    'target_function': rec.target_function,
                    'description': rec.description,
                    'expected_improvement': rec.expected_improvement,
                    'implementation_effort': rec.implementation_effort,
                    'estimated_impact': rec.estimated_impact
                }
                for rec in top_recommendations
            ],
            'recent_sessions': [
                {
                    'session_id': session.session_id,
                    'started_at': session.started_at.isoformat(),
                    'duration_seconds': session.duration_seconds,
                    'total_calls': session.total_calls,
                    'bottlenecks_found': session.bottlenecks_found,
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None
                }
                for session in self.profiling_sessions[-10:]  # Last 10 sessions
            ],
            'performance_baselines': self.performance_baselines
        }
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def shutdown(self):
        """Shutdown the performance optimizer"""
        # Clear performance data
        self.detected_bottlenecks.clear()
        self.optimization_recommendations.clear()
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    logger = configure_logging(__name__, level="INFO")
    
    async def test_performance_optimizer():
        optimizer = PerformanceOptimizer(monitoring_interval_seconds=5)
        
        try:
            # Run performance analysis
            session = await optimizer.run_performance_analysis(duration_seconds=10)
            print(f"Profiling session: {session.session_id}, bottlenecks: {session.bottlenecks_found}")
            
            # Get performance report
            report = optimizer.get_performance_report()
            print(json.dumps(report, indent=2, default=str))
            
        finally:
            optimizer.shutdown()
    
    if PROFILING_LIBS_AVAILABLE:
        asyncio.run(test_performance_optimizer())
    else:
        print("Profiling libraries not available - skipping test") 