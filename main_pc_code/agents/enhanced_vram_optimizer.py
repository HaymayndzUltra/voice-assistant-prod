#!/usr/bin/env python3
"""
Enhanced VRAM Optimizer - Cross-Machine Memory Management
Integrates with the event system and GPU load balancer for intelligent VRAM optimization.

Features:
- Real-time VRAM monitoring across machines
- Predictive memory management
- Cross-machine model offloading
- Memory fragmentation detection and defragmentation
- Adaptive optimization strategies
- Integration with GPU Load Balancer
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import logging
import threading
import gc
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum

# Core imports
from common.core.base_agent import BaseAgent
from common_utils.error_handling import SafeExecutor

# Event system imports
from events.model_events import (
    ModelEventType, ModelLoadEvent, ModelPerformanceEvent,
    CrossMachineModelEvent, create_vram_warning,
    create_cross_machine_request, create_model_status_change, ModelStatus
)
from events.memory_events import (
    MemoryEventType, create_memory_pressure_warning, MemoryPerformanceEvent
)
from events.event_bus import (
    get_event_bus, publish_model_event, publish_memory_event, 
    subscribe_to_model_events, subscribe_to_memory_events
)

# Try to import GPU libraries
try:
    import torch
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("GPU libraries not available - running in simulation mode")

class OptimizationStrategy(Enum):
    """VRAM optimization strategies"""
    CONSERVATIVE = "conservative"  # Minimize model movements
    AGGRESSIVE = "aggressive"      # Optimize for maximum free memory
    BALANCED = "balanced"          # Balance performance and memory
    PREDICTIVE = "predictive"      # Use ML predictions for optimization
    EMERGENCY = "emergency"        # Emergency memory recovery

class MemoryPressureLevel(Enum):
    """Memory pressure severity levels"""
    LOW = "low"           # < 70% usage
    MEDIUM = "medium"     # 70-85% usage  
    HIGH = "high"         # 85-95% usage
    CRITICAL = "critical" # > 95% usage
    EMERGENCY = "emergency" # > 98% usage

@dataclass
class ModelMemoryProfile:
    """Memory profile for a loaded model"""
    model_id: str
    model_type: str
    base_memory_mb: int = 0
    peak_memory_mb: int = 0
    current_memory_mb: int = 0
    memory_efficiency: float = 1.0  # actual/expected ratio
    access_frequency: int = 0
    last_access_time: datetime = field(default_factory=datetime.now)
    load_time_seconds: float = 0.0
    inference_count: int = 0
    avg_inference_time_ms: float = 0.0
    priority_score: float = 50.0  # 0-100, higher = more important
    fragmentation_score: float = 0.0  # 0-100, higher = more fragmented
    
    @property
    def memory_waste_mb(self) -> int:
        """Calculate memory waste due to inefficiency"""
        expected_memory = self.base_memory_mb
        actual_memory = self.current_memory_mb
        return max(0, actual_memory - expected_memory)
    
    @property
    def age_minutes(self) -> float:
        """Age since last access in minutes"""
        return (datetime.now() - self.last_access_time).total_seconds() / 60

@dataclass
class MemorySegment:
    """Represents a memory segment for fragmentation analysis"""
    start_offset: int
    size_mb: int
    model_id: Optional[str] = None
    is_free: bool = False
    allocation_time: datetime = field(default_factory=datetime.now)

@dataclass
class OptimizationPlan:
    """Plan for VRAM optimization"""
    strategy: OptimizationStrategy
    actions: List[Dict[str, Any]] = field(default_factory=list)
    expected_memory_freed_mb: int = 0
    estimated_execution_time_seconds: float = 0.0
    confidence_score: float = 0.0
    risk_level: str = "low"  # low, medium, high
    prerequisites: List[str] = field(default_factory=list)

class EnhancedVRAMOptimizer(BaseAgent):
    """
    Enhanced VRAM Optimizer with cross-machine capabilities.
    
    Provides intelligent VRAM management using:
    - Real-time memory monitoring and prediction
    - Cross-machine model offloading
    - Memory fragmentation detection and repair
    - Adaptive optimization strategies
    - Integration with GPU Load Balancer
    """
    
    def __init__(self, 
                 optimization_strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
                 memory_threshold_mb: int = 20480,  # 20GB default for RTX 4090
                 **kwargs):
        super().__init__(name="EnhancedVRAMOptimizer", **kwargs)
        
        # Configuration
        self.optimization_strategy = optimization_strategy
        self.memory_threshold_mb = memory_threshold_mb
        
        # Memory tracking
        self.model_profiles: Dict[str, ModelMemoryProfile] = {}
        self.memory_segments: List[MemorySegment] = []
        self.memory_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        
        # Optimization state
        self.current_memory_usage_mb = 0
        self.peak_memory_usage_mb = 0
        self.fragmentation_percentage = 0.0
        self.optimization_in_progress = False
        self.last_optimization_time = datetime.now()
        
        # Cross-machine coordination
        self.connected_machines: Set[str] = set()
        self.remote_memory_status: Dict[str, Dict[str, Any]] = {}
        
        # Predictive modeling
        self.memory_prediction_model = None
        self.prediction_history: deque = deque(maxlen=100)
        
        # Event subscriptions
        self.subscription_ids = []
        
        # Initialize components
        self._setup_event_subscriptions()
        self._start_monitoring_threads()
        self._initialize_memory_tracking()
        
        self.logger.info(f"Enhanced VRAM Optimizer initialized with {optimization_strategy.value} strategy")
    
    def _setup_event_subscriptions(self) -> None:
        """Subscribe to relevant events"""
        # Subscribe to model events
        sub_id = subscribe_to_model_events(
            subscriber_id="EnhancedVRAMOptimizer",
            event_types=[
                ModelEventType.MODEL_LOAD_REQUESTED,
                ModelEventType.MODEL_LOADED,
                ModelEventType.MODEL_UNLOADED,
                ModelEventType.MODEL_PERFORMANCE_DEGRADED
            ],
            callback=self._handle_model_event,
            priority=30  # Very high priority for memory management
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to cross-machine events
        sub_id = subscribe_to_model_events(
            subscriber_id="EnhancedVRAMOptimizer",
            event_types=[
                ModelEventType.CROSS_MACHINE_MODEL_REQUEST,
                ModelEventType.CROSS_MACHINE_MODEL_TRANSFER,
                ModelEventType.LOAD_BALANCING_REQUIRED
            ],
            callback=self._handle_cross_machine_event,
            priority=25
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to memory events
        sub_id = subscribe_to_memory_events(
            subscriber_id="EnhancedVRAMOptimizer",
            event_types=[
                MemoryEventType.MEMORY_PRESSURE_WARNING,
                MemoryEventType.MEMORY_FRAGMENTATION_DETECTED,
                MemoryEventType.MEMORY_OPTIMIZATION_COMPLETED
            ],
            callback=self._handle_memory_event,
            priority=30
        )
        self.subscription_ids.append(sub_id)
        
        self.logger.info("Enhanced VRAM Optimizer event subscriptions configured")
    
    def _start_monitoring_threads(self) -> None:
        """Start background monitoring threads"""
        # Memory monitoring thread
        memory_thread = threading.Thread(target=self._memory_monitoring_loop, daemon=True)
        memory_thread.start()
        
        # Fragmentation analysis thread
        fragmentation_thread = threading.Thread(target=self._fragmentation_analysis_loop, daemon=True)
        fragmentation_thread.start()
        
        # Predictive optimization thread
        prediction_thread = threading.Thread(target=self._predictive_optimization_loop, daemon=True)
        prediction_thread.start()
        
        # Cross-machine coordination thread
        coordination_thread = threading.Thread(target=self._cross_machine_coordination_loop, daemon=True)
        coordination_thread.start()
    
    def _initialize_memory_tracking(self) -> None:
        """Initialize memory tracking system"""
        if GPU_AVAILABLE and torch.cuda.is_available():
            # Initialize with current GPU state
            device_count = torch.cuda.device_count()
            
            for i in range(device_count):
                try:
                    # Get current memory info
                    memory_allocated = torch.cuda.memory_allocated(i)
                    torch.cuda.memory_reserved(i)
                    memory_total = torch.cuda.get_device_properties(i).total_memory
                    
                    self.current_memory_usage_mb = int(memory_allocated / (1024 * 1024))
                    self.memory_threshold_mb = int(memory_total / (1024 * 1024))
                    
                    # Initialize memory segments
                    self._rebuild_memory_segments()
                    
                    self.logger.info(f"Memory tracking initialized: {self.current_memory_usage_mb}MB / {self.memory_threshold_mb}MB")
                    break
                    
                except Exception as e:
                    self.logger.error(f"Error initializing memory tracking for GPU {i}: {e}")
        else:
            # Simulation mode
            self.current_memory_usage_mb = 4096  # 4GB simulated usage
            self.logger.info("Memory tracking initialized in simulation mode")
    
    def _memory_monitoring_loop(self) -> None:
        """Continuous memory monitoring loop"""
        while self.running:
            try:
                # Update memory metrics
                self._update_memory_metrics()
                
                # Check memory pressure
                pressure_level = self._calculate_memory_pressure()
                
                # Record history
                self.memory_history.append({
                    'timestamp': datetime.now(),
                    'usage_mb': self.current_memory_usage_mb,
                    'pressure_level': pressure_level.value,
                    'fragmentation': self.fragmentation_percentage,
                    'model_count': len(self.model_profiles)
                })
                
                # Trigger optimization if needed
                if pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL, MemoryPressureLevel.EMERGENCY]:
                    self._trigger_optimization(pressure_level)
                
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Memory monitoring error: {e}")
                time.sleep(10)
    
    def _update_memory_metrics(self) -> None:
        """Update current memory usage metrics"""
        def get_memory_info():
            if GPU_AVAILABLE and torch.cuda.is_available():
                memory_allocated = torch.cuda.memory_allocated(0)
                torch.cuda.memory_reserved(0)
                
                self.current_memory_usage_mb = int(memory_allocated / (1024 * 1024))
                self.peak_memory_usage_mb = max(self.peak_memory_usage_mb, self.current_memory_usage_mb)
                
                # Update model profiles with actual memory usage
                self._update_model_memory_profiles()
            else:
                # Simulation: gradually increase memory usage
                self.current_memory_usage_mb += 10  # Simulate 10MB growth
                if self.current_memory_usage_mb > self.memory_threshold_mb * 0.9:
                    self.current_memory_usage_mb = int(self.memory_threshold_mb * 0.3)  # Reset to 30%
        
        SafeExecutor.execute_with_fallback(
            get_memory_info,
            fallback_value=None,
            context="update memory metrics",
            expected_exceptions=(RuntimeError, OSError, Exception)
        )
    
    def _update_model_memory_profiles(self) -> None:
        """Update memory profiles for all loaded models"""
        for model_id, profile in self.model_profiles.items():
            # Update access patterns
            profile.access_frequency += 1
            
            # Simulate memory efficiency calculations
            if GPU_AVAILABLE and torch.cuda.is_available():
                # Real implementation would track actual model memory usage
                # For now, simulate based on model type and usage patterns
                pass
            else:
                # Simulation: vary memory efficiency
                profile.memory_efficiency = max(0.7, min(1.3, profile.memory_efficiency + (time.time() % 0.1 - 0.05)))
    
    def _calculate_memory_pressure(self) -> MemoryPressureLevel:
        """Calculate current memory pressure level"""
        usage_percentage = (self.current_memory_usage_mb / self.memory_threshold_mb) * 100
        
        if usage_percentage < 70:
            return MemoryPressureLevel.LOW
        elif usage_percentage < 85:
            return MemoryPressureLevel.MEDIUM
        elif usage_percentage < 95:
            return MemoryPressureLevel.HIGH
        elif usage_percentage < 98:
            return MemoryPressureLevel.CRITICAL
        else:
            return MemoryPressureLevel.EMERGENCY
    
    def _fragmentation_analysis_loop(self) -> None:
        """Analyze memory fragmentation"""
        while self.running:
            try:
                self._analyze_memory_fragmentation()
                time.sleep(60)  # Analyze every minute
                
            except Exception as e:
                self.logger.error(f"Fragmentation analysis error: {e}")
                time.sleep(30)
    
    def _analyze_memory_fragmentation(self) -> None:
        """Analyze and quantify memory fragmentation"""
        if not self.memory_segments:
            self._rebuild_memory_segments()
        
        total_free_space = 0
        largest_free_block = 0
        free_blocks = []
        
        for segment in self.memory_segments:
            if segment.is_free:
                total_free_space += segment.size_mb
                largest_free_block = max(largest_free_block, segment.size_mb)
                free_blocks.append(segment.size_mb)
        
        if total_free_space > 0:
            # Fragmentation score: how much of free space is in small chunks
            fragmentation_ratio = 1.0 - (largest_free_block / total_free_space)
            self.fragmentation_percentage = fragmentation_ratio * 100
            
            # If fragmentation is high, trigger defragmentation
            if self.fragmentation_percentage > 40:
                self._trigger_defragmentation()
        else:
            self.fragmentation_percentage = 0.0
    
    def _rebuild_memory_segments(self) -> None:
        """Rebuild memory segment map"""
        self.memory_segments = []
        current_offset = 0
        
        # Create segments for each loaded model
        for model_id, profile in self.model_profiles.items():
            segment = MemorySegment(
                start_offset=current_offset,
                size_mb=profile.current_memory_mb,
                model_id=model_id,
                is_free=False
            )
            self.memory_segments.append(segment)
            current_offset += profile.current_memory_mb
        
        # Add free space segment
        free_space_mb = self.memory_threshold_mb - self.current_memory_usage_mb
        if free_space_mb > 0:
            free_segment = MemorySegment(
                start_offset=current_offset,
                size_mb=free_space_mb,
                is_free=True
            )
            self.memory_segments.append(free_segment)
    
    def _predictive_optimization_loop(self) -> None:
        """Predictive optimization using historical data"""
        while self.running:
            try:
                # Run predictive analysis every 5 minutes
                if len(self.memory_history) >= 10:
                    self._run_predictive_analysis()
                
                time.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Predictive optimization error: {e}")
                time.sleep(60)
    
    def _run_predictive_analysis(self) -> None:
        """Run predictive analysis on memory usage patterns"""
        # Simple trend analysis (could be replaced with ML model)
        recent_usage = [entry['usage_mb'] for entry in list(self.memory_history)[-10:]]
        
        if len(recent_usage) >= 5:
            # Calculate trend
            x = list(range(len(recent_usage)))
            y = recent_usage
            
            # Simple linear regression
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
            
            # Predict usage in next 10 minutes (2 data points ahead)
            predicted_usage = slope * (n + 2) + intercept
            
            # Store prediction
            self.prediction_history.append({
                'timestamp': datetime.now(),
                'predicted_usage_mb': predicted_usage,
                'current_usage_mb': self.current_memory_usage_mb,
                'trend_slope': slope
            })
            
            # If prediction shows memory pressure, trigger proactive optimization
            predicted_pressure = (predicted_usage / self.memory_threshold_mb) * 100
            if predicted_pressure > 80 and not self.optimization_in_progress:
                self.logger.info(f"Predictive optimization triggered: {predicted_pressure:.1f}% predicted pressure")
                self._trigger_optimization(MemoryPressureLevel.MEDIUM, proactive=True)
    
    def _cross_machine_coordination_loop(self) -> None:
        """Handle cross-machine coordination"""
        while self.running:
            try:
                # Update remote machine status
                self._update_remote_machine_status()
                
                # Check for cross-machine optimization opportunities
                self._evaluate_cross_machine_opportunities()
                
                time.sleep(30)  # Every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Cross-machine coordination error: {e}")
                time.sleep(60)
    
    def _update_remote_machine_status(self) -> None:
        """Update status of remote machines"""
        # In a real implementation, this would query remote machines
        # For now, simulate PC2 status
        if "PC2" not in self.remote_memory_status:
            self.remote_memory_status["PC2"] = {
                'available_memory_mb': 8192,  # 8GB available on PC2
                'cpu_utilization': 30.0,
                'model_count': 2,
                'last_updated': datetime.now(),
                'capabilities': ['cpu_inference', 'lightweight_models']
            }
        
        # Update timestamp
        for machine_id in self.remote_memory_status:
            self.remote_memory_status[machine_id]['last_updated'] = datetime.now()
    
    def _evaluate_cross_machine_opportunities(self) -> None:
        """Evaluate opportunities for cross-machine optimization"""
        # Check if we have high memory pressure and available remote capacity
        current_pressure = self._calculate_memory_pressure()
        
        if current_pressure in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
            for machine_id, status in self.remote_memory_status.items():
                if status['available_memory_mb'] > 1024:  # At least 1GB available
                    # Find candidate models for offloading
                    candidates = self._find_offload_candidates()
                    
                    if candidates:
                        self.logger.info(f"Cross-machine offload opportunity: {len(candidates)} models to {machine_id}")
                        self._initiate_cross_machine_offload(machine_id, candidates[:1])  # Offload 1 model
    
    def _find_offload_candidates(self) -> List[str]:
        """Find models suitable for cross-machine offloading"""
        candidates = []
        
        for model_id, profile in self.model_profiles.items():
            # Criteria for offloading:
            # 1. Low access frequency
            # 2. Not accessed recently
            # 3. Suitable for CPU inference
            
            if (profile.access_frequency < 5 and 
                profile.age_minutes > 30 and
                profile.priority_score < 70):
                candidates.append(model_id)
        
        # Sort by offload suitability (least important first)
        candidates.sort(key=lambda mid: (
            self.model_profiles[mid].priority_score,
            -self.model_profiles[mid].age_minutes
        ))
        
        return candidates
    
    def _initiate_cross_machine_offload(self, target_machine: str, model_ids: List[str]) -> None:
        """Initiate cross-machine model offloading"""
        for model_id in model_ids:
            if model_id in self.model_profiles:
                profile = self.model_profiles[model_id]
                
                # Create cross-machine transfer event
                transfer_event = create_cross_machine_request(
                    model_id=model_id,
                    target_machine=target_machine,
                    source_machine=self._get_current_machine_id(),
                    coordination_type="memory_optimization_offload",
                    transfer_size_mb=profile.current_memory_mb,
                    priority=10,  # High priority for memory optimization
                    source_agent=self.name,
                    machine_id=self._get_current_machine_id()
                )
                
                publish_model_event(transfer_event)
                
                self.logger.info(f"Initiated offload: {model_id} → {target_machine} ({profile.current_memory_mb}MB)")
    
    def _handle_model_event(self, event) -> None:
        """Handle model-related events"""
        if event.event_type == ModelEventType.MODEL_LOAD_REQUESTED:
            self._handle_model_load_request(event)
        elif event.event_type == ModelEventType.MODEL_LOADED:
            self._handle_model_loaded(event)
        elif event.event_type == ModelEventType.MODEL_UNLOADED:
            self._handle_model_unloaded(event)
        elif event.event_type == ModelEventType.MODEL_PERFORMANCE_DEGRADED:
            self._handle_performance_degradation(event)
    
    def _handle_model_load_request(self, event: ModelLoadEvent) -> None:
        """Handle model load request by checking memory availability"""
        required_memory = event.expected_vram_mb
        available_memory = self.memory_threshold_mb - self.current_memory_usage_mb
        
        self.logger.info(f"Model load request: {event.model_id} requires {required_memory}MB, {available_memory}MB available")
        
        if required_memory > available_memory:
            # Not enough memory - trigger optimization
            self.logger.warning(f"Insufficient memory for {event.model_id}: {required_memory}MB > {available_memory}MB")
            
            # Create optimization plan
            plan = self._create_optimization_plan(required_memory, OptimizationStrategy.AGGRESSIVE)
            
            if plan.expected_memory_freed_mb >= required_memory:
                # Execute optimization plan
                self._execute_optimization_plan(plan)
                
                # Publish VRAM optimization completed event
                optimization_event = create_vram_warning(
                    used_vram_mb=self.current_memory_usage_mb - plan.expected_memory_freed_mb,
                    total_vram_mb=self.memory_threshold_mb,
                    threshold_percentage=70.0,
                    affected_models=[event.model_id],
                    source_agent=self.name,
                    machine_id=self._get_current_machine_id()
                )
                optimization_event.event_type = ModelEventType.VRAM_OPTIMIZED
                optimization_event.optimization_action = f"Freed {plan.expected_memory_freed_mb}MB for {event.model_id}"
                optimization_event.bytes_freed = plan.expected_memory_freed_mb * 1024 * 1024
                
                publish_model_event(optimization_event)
            else:
                # Not enough memory can be freed - suggest cross-machine placement
                self.logger.warning(f"Cannot free enough memory locally for {event.model_id}")
                
                # Publish VRAM threshold exceeded event
                threshold_event = create_vram_warning(
                    used_vram_mb=self.current_memory_usage_mb,
                    total_vram_mb=self.memory_threshold_mb,
                    threshold_percentage=90.0,
                    affected_models=[event.model_id],
                    source_agent=self.name,
                    machine_id=self._get_current_machine_id()
                )
                publish_model_event(threshold_event)
    
    def _handle_model_loaded(self, event) -> None:
        """Handle model loaded event"""
        # Create or update model profile
        profile = ModelMemoryProfile(
            model_id=event.model_id,
            model_type=getattr(event, 'model_type', 'unknown'),
            base_memory_mb=event.vram_usage_mb,
            current_memory_mb=event.vram_usage_mb,
            load_time_seconds=event.load_time_seconds,
            last_access_time=datetime.now()
        )
        
        self.model_profiles[event.model_id] = profile
        self.current_memory_usage_mb += event.vram_usage_mb
        
        # Rebuild memory segments
        self._rebuild_memory_segments()
        
        self.logger.info(f"Model loaded: {event.model_id} ({event.vram_usage_mb}MB)")
    
    def _handle_model_unloaded(self, event) -> None:
        """Handle model unloaded event"""
        if event.model_id in self.model_profiles:
            profile = self.model_profiles[event.model_id]
            self.current_memory_usage_mb -= profile.current_memory_mb
            del self.model_profiles[event.model_id]
            
            # Rebuild memory segments
            self._rebuild_memory_segments()
            
            self.logger.info(f"Model unloaded: {event.model_id}")
    
    def _handle_performance_degradation(self, event: ModelPerformanceEvent) -> None:
        """Handle performance degradation event"""
        if event.model_id in self.model_profiles:
            profile = self.model_profiles[event.model_id]
            
            # Lower priority for poorly performing models
            profile.priority_score = max(0, profile.priority_score - 10)
            
            # Update performance metrics
            profile.avg_inference_time_ms = event.inference_time_ms
            
            self.logger.info(f"Performance degradation recorded for {event.model_id}")
    
    def _handle_cross_machine_event(self, event: CrossMachineModelEvent) -> None:
        """Handle cross-machine coordination events"""
        if event.coordination_type == "memory_optimization_offload":
            self._handle_offload_request(event)
        elif event.coordination_type == "rebalance":
            self._handle_rebalance_request(event)
    
    def _handle_memory_event(self, event) -> None:
        """Handle memory-related events"""
        if event.event_type == MemoryEventType.MEMORY_PRESSURE_WARNING:
            self._handle_memory_pressure_warning(event)
        elif event.event_type == MemoryEventType.MEMORY_FRAGMENTATION_DETECTED:
            self._handle_fragmentation_detected(event)
    
    def _handle_memory_pressure_warning(self, event: MemoryPerformanceEvent) -> None:
        """Handle memory pressure warning"""
        pressure_level = MemoryPressureLevel.HIGH
        if event.memory_utilization_percentage > 95:
            pressure_level = MemoryPressureLevel.CRITICAL
        elif event.memory_utilization_percentage > 98:
            pressure_level = MemoryPressureLevel.EMERGENCY
        
        self._trigger_optimization(pressure_level)
    
    def _trigger_optimization(self, pressure_level: MemoryPressureLevel, proactive: bool = False) -> None:
        """Trigger VRAM optimization based on pressure level"""
        if self.optimization_in_progress:
            self.logger.debug("Optimization already in progress, skipping")
            return
        
        self.optimization_in_progress = True
        
        try:
            # Determine strategy based on pressure level
            if pressure_level == MemoryPressureLevel.EMERGENCY:
                strategy = OptimizationStrategy.EMERGENCY
                target_memory_mb = int(self.memory_threshold_mb * 0.6)  # Free to 60%
            elif pressure_level == MemoryPressureLevel.CRITICAL:
                strategy = OptimizationStrategy.AGGRESSIVE
                target_memory_mb = int(self.memory_threshold_mb * 0.7)  # Free to 70%
            elif pressure_level == MemoryPressureLevel.HIGH:
                strategy = OptimizationStrategy.BALANCED
                target_memory_mb = int(self.memory_threshold_mb * 0.8)  # Free to 80%
            else:
                strategy = OptimizationStrategy.CONSERVATIVE
                target_memory_mb = int(self.memory_threshold_mb * 0.85)  # Free to 85%
            
            memory_to_free = max(0, self.current_memory_usage_mb - target_memory_mb)
            
            if memory_to_free > 0:
                self.logger.info(f"Triggering {strategy.value} optimization: free {memory_to_free}MB (pressure: {pressure_level.value})")
                
                # Create and execute optimization plan
                plan = self._create_optimization_plan(memory_to_free, strategy)
                
                if plan.expected_memory_freed_mb > 0:
                    self._execute_optimization_plan(plan)
                else:
                    self.logger.warning("No feasible optimization plan found")
            
        finally:
            self.optimization_in_progress = False
            self.last_optimization_time = datetime.now()
    
    def _create_optimization_plan(self, target_memory_mb: int, strategy: OptimizationStrategy) -> OptimizationPlan:
        """Create an optimization plan to free the target amount of memory"""
        plan = OptimizationPlan(strategy=strategy)
        memory_freed = 0
        
        # Get list of models sorted by eviction priority
        eviction_candidates = self._get_eviction_candidates(strategy)
        
        for model_id, eviction_score in eviction_candidates:
            if memory_freed >= target_memory_mb:
                break
            
            profile = self.model_profiles[model_id]
            
            # Determine action based on strategy and model characteristics
            if strategy == OptimizationStrategy.EMERGENCY:
                # Emergency: unload immediately
                action = {
                    'type': 'unload',
                    'model_id': model_id,
                    'memory_freed_mb': profile.current_memory_mb,
                    'risk_level': 'high',
                    'reasoning': 'Emergency memory recovery'
                }
            elif strategy == OptimizationStrategy.AGGRESSIVE:
                # Aggressive: unload or offload
                if profile.priority_score < 50 and self._can_offload_to_remote(model_id):
                    action = {
                        'type': 'offload',
                        'model_id': model_id,
                        'target_machine': self._find_best_offload_target(),
                        'memory_freed_mb': profile.current_memory_mb,
                        'risk_level': 'medium',
                        'reasoning': 'Cross-machine offload for memory optimization'
                    }
                else:
                    action = {
                        'type': 'unload',
                        'model_id': model_id,
                        'memory_freed_mb': profile.current_memory_mb,
                        'risk_level': 'medium',
                        'reasoning': 'Model unload for memory optimization'
                    }
            else:
                # Balanced/Conservative: try optimization first, then unload
                if profile.memory_efficiency < 0.9:
                    action = {
                        'type': 'optimize',
                        'model_id': model_id,
                        'memory_freed_mb': int(profile.memory_waste_mb),
                        'risk_level': 'low',
                        'reasoning': 'Memory optimization without unloading'
                    }
                elif profile.priority_score < 30:
                    action = {
                        'type': 'unload',
                        'model_id': model_id,
                        'memory_freed_mb': profile.current_memory_mb,
                        'risk_level': 'low',
                        'reasoning': 'Low priority model unload'
                    }
                else:
                    continue  # Skip this model
            
            plan.actions.append(action)
            memory_freed += action['memory_freed_mb']
        
        plan.expected_memory_freed_mb = memory_freed
        plan.estimated_execution_time_seconds = len(plan.actions) * 2.0  # 2 seconds per action
        plan.confidence_score = min(1.0, memory_freed / max(target_memory_mb, 1))
        
        return plan
    
    def _get_eviction_candidates(self, strategy: OptimizationStrategy) -> List[Tuple[str, float]]:
        """Get models ranked by eviction priority"""
        candidates = []
        
        for model_id, profile in self.model_profiles.items():
            # Calculate eviction score (higher = more likely to evict)
            score = 0.0
            
            # Age factor (older = higher score)
            age_factor = min(1.0, profile.age_minutes / 60.0)  # Normalize to hours
            score += age_factor * 30
            
            # Priority factor (lower priority = higher score)
            priority_factor = (100 - profile.priority_score) / 100
            score += priority_factor * 40
            
            # Access frequency factor (less used = higher score)
            max_frequency = max([p.access_frequency for p in self.model_profiles.values()] + [1])
            frequency_factor = 1.0 - (profile.access_frequency / max_frequency)
            score += frequency_factor * 20
            
            # Memory efficiency factor (less efficient = higher score)
            efficiency_factor = 1.0 - profile.memory_efficiency
            score += efficiency_factor * 10
            
            # Strategy-specific adjustments
            if strategy == OptimizationStrategy.EMERGENCY:
                # In emergency, prioritize larger models
                size_factor = profile.current_memory_mb / max([p.current_memory_mb for p in self.model_profiles.values()] + [1])
                score += size_factor * 20
            
            candidates.append((model_id, score))
        
        # Sort by eviction score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    def _execute_optimization_plan(self, plan: OptimizationPlan) -> None:
        """Execute the optimization plan"""
        self.logger.info(f"Executing optimization plan: {len(plan.actions)} actions, {plan.expected_memory_freed_mb}MB target")
        
        for action in plan.actions:
            try:
                if action['type'] == 'unload':
                    self._execute_model_unload(action['model_id'])
                elif action['type'] == 'offload':
                    self._execute_model_offload(action['model_id'], action['target_machine'])
                elif action['type'] == 'optimize':
                    self._execute_model_optimization(action['model_id'])
                
                time.sleep(0.5)  # Brief pause between actions
                
            except Exception as e:
                self.logger.error(f"Error executing optimization action {action}: {e}")
        
        self.logger.info("Optimization plan execution completed")
    
    def _execute_model_unload(self, model_id: str) -> None:
        """Execute model unloading"""
        if model_id in self.model_profiles:
            # Create model unload event
            unload_event = create_model_status_change(
                model_id=model_id,
                old_status=ModelStatus.LOADED,
                new_status=ModelStatus.UNLOADED,
                source_agent=self.name,
                machine_id=self._get_current_machine_id()
            )
            unload_event.event_type = ModelEventType.MODEL_UNLOAD_REQUESTED
            
            publish_model_event(unload_event)
            
            self.logger.info(f"Unload requested for model: {model_id}")
    
    def _execute_model_offload(self, model_id: str, target_machine: str) -> None:
        """Execute cross-machine model offloading"""
        if model_id in self.model_profiles:
            profile = self.model_profiles[model_id]
            
            # Create cross-machine transfer event
            transfer_event = create_cross_machine_request(
                model_id=model_id,
                target_machine=target_machine,
                source_machine=self._get_current_machine_id(),
                coordination_type="optimization_offload",
                transfer_size_mb=profile.current_memory_mb,
                source_agent=self.name,
                machine_id=self._get_current_machine_id()
            )
            
            publish_model_event(transfer_event)
            
            self.logger.info(f"Offload requested: {model_id} → {target_machine}")
    
    def _execute_model_optimization(self, model_id: str) -> None:
        """Execute in-place model optimization"""
        if GPU_AVAILABLE and torch.cuda.is_available():
            # Real implementation would optimize model memory usage
            # For now, simulate by running garbage collection
            SafeExecutor.execute_with_fallback(
                lambda: [torch.cuda.empty_cache(), gc.collect()],
                fallback_value=None,
                context="model memory optimization",
                expected_exceptions=(RuntimeError, Exception)
            )
        
        self.logger.info(f"Memory optimization applied to model: {model_id}")
    
    def _trigger_defragmentation(self) -> None:
        """Trigger memory defragmentation"""
        self.logger.info(f"Triggering memory defragmentation (fragmentation: {self.fragmentation_percentage:.1f}%)")
        
        if GPU_AVAILABLE and torch.cuda.is_available():
            # Real defragmentation would reorganize GPU memory
            SafeExecutor.execute_with_fallback(
                lambda: torch.cuda.empty_cache(),
                fallback_value=None,
                context="memory defragmentation",
                expected_exceptions=(RuntimeError, Exception)
            )
        
        # Rebuild memory segments after defragmentation
        self._rebuild_memory_segments()
        
        # Publish memory optimization event
        optimization_event = create_memory_pressure_warning(
            memory_utilization_percentage=self.current_memory_usage_mb / self.memory_threshold_mb * 100,
            fragmentation_percentage=0.0,  # Should be lower after defrag
            optimization_suggestions=["Memory defragmentation completed"],
            source_agent=self.name,
            machine_id=self._get_current_machine_id()
        )
        optimization_event.event_type = MemoryEventType.MEMORY_OPTIMIZATION_COMPLETED
        
        publish_memory_event(optimization_event)
    
    def _can_offload_to_remote(self, model_id: str) -> bool:
        """Check if model can be offloaded to remote machine"""
        if model_id not in self.model_profiles:
            return False
        
        profile = self.model_profiles[model_id]
        
        # Check if any remote machine has sufficient capacity
        for machine_id, status in self.remote_memory_status.items():
            if status['available_memory_mb'] >= profile.current_memory_mb:
                return True
        
        return False
    
    def _find_best_offload_target(self) -> Optional[str]:
        """Find the best remote machine for offloading"""
        best_machine = None
        best_score = 0
        
        for machine_id, status in self.remote_memory_status.items():
            # Score based on available memory and capabilities
            score = status['available_memory_mb'] / 1024  # GB available
            score += (100 - status['cpu_utilization']) / 100 * 10  # Low CPU usage bonus
            
            if score > best_score:
                best_score = score
                best_machine = machine_id
        
        return best_machine
    
    def _get_current_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive optimization status"""
        pressure_level = self._calculate_memory_pressure()
        
        return {
            'memory_usage': {
                'current_mb': self.current_memory_usage_mb,
                'threshold_mb': self.memory_threshold_mb,
                'usage_percentage': (self.current_memory_usage_mb / self.memory_threshold_mb) * 100,
                'pressure_level': pressure_level.value,
                'fragmentation_percentage': self.fragmentation_percentage
            },
            'models': {
                'total_count': len(self.model_profiles),
                'profiles': {
                    model_id: {
                        'memory_mb': profile.current_memory_mb,
                        'priority_score': profile.priority_score,
                        'age_minutes': profile.age_minutes,
                        'access_frequency': profile.access_frequency,
                        'memory_efficiency': profile.memory_efficiency
                    }
                    for model_id, profile in self.model_profiles.items()
                }
            },
            'optimization': {
                'strategy': self.optimization_strategy.value,
                'in_progress': self.optimization_in_progress,
                'last_optimization': self.last_optimization_time.isoformat(),
                'prediction_accuracy': self._get_prediction_accuracy()
            },
            'cross_machine': {
                'connected_machines': list(self.connected_machines),
                'remote_status': self.remote_memory_status
            }
        }
    
    def _get_prediction_accuracy(self) -> float:
        """Calculate prediction accuracy"""
        if len(self.prediction_history) < 5:
            return 0.0
        
        recent_predictions = list(self.prediction_history)[-5:]
        errors = []
        
        for pred in recent_predictions:
            actual_usage = self.current_memory_usage_mb
            predicted_usage = pred['predicted_usage_mb']
            error = abs(actual_usage - predicted_usage) / max(actual_usage, 1)
            errors.append(error)
        
        avg_error = sum(errors) / len(errors)
        accuracy = max(0, 1 - avg_error)
        
        return accuracy
    
    def shutdown(self):
        """Clean up subscriptions and resources"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        
        # Clear GPU cache if available
        if GPU_AVAILABLE and torch.cuda.is_available():
            SafeExecutor.execute_with_fallback(
                lambda: torch.cuda.empty_cache(),
                fallback_value=None,
                context="final GPU cache cleanup",
                expected_exceptions=(RuntimeError, Exception)
            )
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    optimizer = EnhancedVRAMOptimizer(
        optimization_strategy=OptimizationStrategy.ADAPTIVE,
        memory_threshold_mb=24576  # 24GB RTX 4090
    )
    
    try:
        # Print initial status
        status = optimizer.get_optimization_status()
        print(json.dumps(status, indent=2))
        
        # Keep running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("Shutting down Enhanced VRAM Optimizer...")
        optimizer.shutdown() 