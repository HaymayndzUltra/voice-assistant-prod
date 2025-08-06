#!/usr/bin/env python3
"""
GPU Load Balancer - Cross-Machine GPU Resource Management
Uses the event system to coordinate GPU resources across MainPC and PC2.

Features:
- Cross-machine GPU monitoring and load balancing
- Event-driven model distribution
- Automatic failover and recovery
- Performance-based routing decisions
- VRAM optimization across machines
"""
from __future__ import annotations
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum

# Core imports
from common.core.base_agent import BaseAgent
from common_utils.error_handling import SafeExecutor

# Event system imports
from events.model_events import (
    ModelEventType, ModelLoadEvent, VRAMEvent, ModelPerformanceEvent,
    CrossMachineModelEvent, create_cross_machine_request
)
from events.event_bus import (
    get_event_bus, publish_model_event, subscribe_to_model_events
)

# Try to import GPU monitoring libraries
try:
    import torch
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("GPU libraries not available - running in simulation mode")

class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    BEST_PERFORMANCE = "best_performance"
    FAILOVER_ONLY = "failover_only"
    ADAPTIVE = "adaptive"

class MachineStatus(Enum):
    """Machine availability status"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"

@dataclass
class GPUMetrics:
    """GPU performance metrics"""
    gpu_id: int
    machine_id: str
    utilization_percent: float = 0.0
    memory_used_mb: int = 0
    memory_total_mb: int = 0
    temperature_celsius: float = 0.0
    power_usage_watts: float = 0.0
    compute_capability: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def memory_utilization_percent(self) -> float:
        if self.memory_total_mb == 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100
    
    @property
    def available_memory_mb(self) -> int:
        return self.memory_total_mb - self.memory_used_mb

@dataclass
class MachineInfo:
    """Information about a machine in the cluster"""
    machine_id: str
    ip_address: str
    status: MachineStatus = MachineStatus.ONLINE
    gpu_metrics: List[GPUMetrics] = field(default_factory=list)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    network_latency_ms: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_gpu_memory_mb(self) -> int:
        return sum(gpu.memory_total_mb for gpu in self.gpu_metrics)
    
    @property
    def used_gpu_memory_mb(self) -> int:
        return sum(gpu.memory_used_mb for gpu in self.gpu_metrics)
    
    @property
    def available_gpu_memory_mb(self) -> int:
        return sum(gpu.available_memory_mb for gpu in self.gpu_metrics)
    
    @property
    def avg_gpu_utilization(self) -> float:
        if not self.gpu_metrics:
            return 0.0
        return sum(gpu.utilization_percent for gpu in self.gpu_metrics) / len(self.gpu_metrics)

@dataclass
class LoadBalancingDecision:
    """Result of load balancing decision"""
    target_machine: str
    target_gpu: Optional[int] = None
    confidence_score: float = 0.0
    reasoning: str = ""
    alternative_machines: List[str] = field(default_factory=list)
    estimated_load_time_seconds: float = 0.0

class GPULoadBalancer(BaseAgent):
    """
    GPU Load Balancer for cross-machine coordination.
    
    Coordinates GPU resources across MainPC and PC2 using the event system.
    Makes intelligent decisions about where to place models based on:
    - Current GPU utilization and memory
    - Machine performance characteristics
    - Network latency and bandwidth
    - Historical performance data
    """
    
    def __init__(self, 
                 strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE,
                 **kwargs):
        super().__init__(name="GPULoadBalancer", **kwargs)
        
        # Configuration
        self.strategy = strategy
        self.machines: Dict[str, MachineInfo] = {}
        self.model_placements: Dict[str, str] = {}  # model_id -> machine_id
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Load balancing state
        self.last_round_robin_index = 0
        self.subscription_ids = []
        
        # Monitoring
        self.metrics_update_interval = 30  # seconds
        self.heartbeat_timeout = 120  # seconds
        
        # Initialize machine discovery
        self._discover_machines()
        self._setup_event_subscriptions()
        self._start_monitoring_threads()
        
        self.logger.info(f"GPU Load Balancer initialized with strategy: {strategy.value}")
    
    def _discover_machines(self) -> None:
        """Discover available machines in the cluster"""
        # Initialize known machines
        machines_config = {
            "MainPC": {
                "ip_address": "192.168.100.16",
                "capabilities": {
                    "gpu_count": 1,
                    "gpu_type": "RTX 4090",
                    "cuda_version": "12.1",
                    "compute_capability": "8.9",
                    "primary_machine": True
                }
            },
            "PC2": {
                "ip_address": "192.168.100.17", 
                "capabilities": {
                    "gpu_count": 0,  # CPU-only machine
                    "gpu_type": None,
                    "cuda_version": None,
                    "compute_capability": None,
                    "primary_machine": False
                }
            }
        }
        
        for machine_id, config in machines_config.items():
            machine_info = MachineInfo(
                machine_id=machine_id,
                ip_address=config["ip_address"],
                capabilities=config["capabilities"]
            )
            self.machines[machine_id] = machine_info
        
        self.logger.info(f"Discovered {len(self.machines)} machines: {list(self.machines.keys())}")
    
    def _setup_event_subscriptions(self) -> None:
        """Subscribe to relevant events"""
        # Subscribe to model load requests
        sub_id = subscribe_to_model_events(
            subscriber_id="GPULoadBalancer",
            event_types=[ModelEventType.MODEL_LOAD_REQUESTED],
            callback=self._handle_model_load_request,
            priority=25  # Highest priority for load balancing decisions
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to VRAM events
        sub_id = subscribe_to_model_events(
            subscriber_id="GPULoadBalancer",
            event_types=[
                ModelEventType.VRAM_THRESHOLD_EXCEEDED,
                ModelEventType.GPU_MEMORY_WARNING,
                ModelEventType.GPU_MEMORY_CRITICAL
            ],
            callback=self._handle_vram_event,
            priority=20
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to performance events
        sub_id = subscribe_to_model_events(
            subscriber_id="GPULoadBalancer",
            event_types=[
                ModelEventType.MODEL_PERFORMANCE_DEGRADED,
                ModelEventType.MODEL_INFERENCE_SLOW
            ],
            callback=self._handle_performance_event,
            priority=15
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to cross-machine events
        sub_id = subscribe_to_model_events(
            subscriber_id="GPULoadBalancer",
            event_types=[
                ModelEventType.CROSS_MACHINE_MODEL_REQUEST,
                ModelEventType.LOAD_BALANCING_REQUIRED
            ],
            callback=self._handle_cross_machine_event,
            priority=20
        )
        self.subscription_ids.append(sub_id)
        
        self.logger.info("GPU Load Balancer event subscriptions set up")
    
    def _start_monitoring_threads(self) -> None:
        """Start background monitoring threads"""
        # GPU metrics monitoring
        gpu_thread = threading.Thread(target=self._monitor_gpu_metrics, daemon=True)
        gpu_thread.start()
        
        # Machine health monitoring
        health_thread = threading.Thread(target=self._monitor_machine_health, daemon=True)
        health_thread.start()
        
        # Load balancing optimization
        optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        optimization_thread.start()
    
    def _monitor_gpu_metrics(self) -> None:
        """Monitor GPU metrics across all machines"""
        while self.running:
            try:
                # Update metrics for current machine
                current_machine = self._detect_current_machine()
                if current_machine in self.machines:
                    self._update_local_gpu_metrics(current_machine)
                
                # Update machine status based on heartbeats
                self._update_machine_status()
                
                time.sleep(self.metrics_update_interval)
                
            except Exception as e:
                self.logger.error(f"GPU metrics monitoring error: {e}")
                time.sleep(5)
    
    def _update_local_gpu_metrics(self, machine_id: str) -> None:
        """Update GPU metrics for the local machine"""
        def get_gpu_metrics():
            gpu_metrics = []
            
            if GPU_AVAILABLE and torch.cuda.is_available():
                # Real GPU monitoring
                device_count = torch.cuda.device_count()
                
                for i in range(device_count):
                    try:
                        # Get GPU properties
                        props = torch.cuda.get_device_properties(i)
                        
                        # Get memory info
                        memory_allocated = torch.cuda.memory_allocated(i)
                        torch.cuda.memory_reserved(i)
                        memory_total = props.total_memory
                        
                        # Try to get additional metrics with GPUtil
                        gpu_util = 0.0
                        gpu_temp = 0.0
                        gpu_power = 0.0
                        
                        if 'GPUtil' in globals():
                            try:
                                gpu_info = GPUtil.getGPUs()[i] if i < len(GPUtil.getGPUs()) else None
                                if gpu_info:
                                    gpu_util = gpu_info.load * 100
                                    gpu_temp = gpu_info.temperature
                                    gpu_power = getattr(gpu_info, 'powerDraw', 0.0)
                            except Exception:
                                pass  # GPUtil might not work in all environments
                        
                        metrics = GPUMetrics(
                            gpu_id=i,
                            machine_id=machine_id,
                            utilization_percent=gpu_util,
                            memory_used_mb=int(memory_allocated / (1024 * 1024)),
                            memory_total_mb=int(memory_total / (1024 * 1024)),
                            temperature_celsius=gpu_temp,
                            power_usage_watts=gpu_power,
                            compute_capability=f"{props.major}.{props.minor}"
                        )
                        gpu_metrics.append(metrics)
                        
                    except Exception as e:
                        self.logger.error(f"Error getting metrics for GPU {i}: {e}")
            else:
                # Simulated metrics for testing
                metrics = GPUMetrics(
                    gpu_id=0,
                    machine_id=machine_id,
                    utilization_percent=30.0,  # Simulated values
                    memory_used_mb=4096,
                    memory_total_mb=24576,  # 24GB RTX 4090
                    temperature_celsius=65.0,
                    power_usage_watts=350.0,
                    compute_capability="8.9"
                )
                gpu_metrics.append(metrics)
            
            return gpu_metrics
        
        # Use SafeExecutor for robust metric collection
        gpu_metrics = SafeExecutor.execute_with_fallback(
            get_gpu_metrics,
            fallback_value=[],
            context="collect GPU metrics",
            expected_exceptions=(RuntimeError, OSError, Exception)
        )
        
        if machine_id in self.machines and gpu_metrics:
            self.machines[machine_id].gpu_metrics = gpu_metrics
            self.machines[machine_id].last_heartbeat = datetime.now()
    
    def _update_machine_status(self) -> None:
        """Update machine status based on heartbeat and health"""
        current_time = datetime.now()
        
        for machine_id, machine_info in self.machines.items():
            time_since_heartbeat = (current_time - machine_info.last_heartbeat).total_seconds()
            
            if time_since_heartbeat > self.heartbeat_timeout:
                if machine_info.status != MachineStatus.OFFLINE:
                    machine_info.status = MachineStatus.OFFLINE
                    self.logger.warning(f"Machine {machine_id} marked as OFFLINE (no heartbeat for {time_since_heartbeat:.1f}s)")
            else:
                # Check for degraded performance
                avg_util = machine_info.avg_gpu_utilization
                memory_util = (machine_info.used_gpu_memory_mb / max(machine_info.total_gpu_memory_mb, 1)) * 100
                
                if avg_util > 95 or memory_util > 90:
                    machine_info.status = MachineStatus.DEGRADED
                elif machine_info.status != MachineStatus.ONLINE:
                    machine_info.status = MachineStatus.ONLINE
                    self.logger.info(f"Machine {machine_id} status: ONLINE")
    
    def _monitor_machine_health(self) -> None:
        """Monitor overall machine health"""
        while self.running:
            try:
                # Check for overloaded machines
                for machine_id, machine_info in self.machines.items():
                    if machine_info.status == MachineStatus.ONLINE:
                        if machine_info.avg_gpu_utilization > 90:
                            # Publish load balancing required event
                            rebalance_event = create_cross_machine_request(
                                model_id="",
                                target_machine="",
                                source_machine=machine_id,
                                coordination_type="rebalance",
                                source_agent=self.name,
                                machine_id=machine_id
                            )
                            rebalance_event.event_type = ModelEventType.LOAD_BALANCING_REQUIRED
                            publish_model_event(rebalance_event)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Machine health monitoring error: {e}")
                time.sleep(10)
    
    def _optimization_loop(self) -> None:
        """Background optimization loop"""
        while self.running:
            try:
                # Perform periodic load balancing optimization
                if self.strategy == LoadBalancingStrategy.ADAPTIVE:
                    self._adaptive_optimization()
                
                time.sleep(300)  # Optimize every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
                time.sleep(30)
    
    def _handle_model_load_request(self, event: ModelLoadEvent) -> None:
        """Handle model load requests by making load balancing decisions"""
        self.logger.info(f"Load balancing decision for model {event.model_id}")
        
        # Make load balancing decision
        decision = self._make_load_balancing_decision(event)
        
        if decision.target_machine:
            # Update model placement tracking
            self.model_placements[event.model_id] = decision.target_machine
            
            # If target is different from requester's machine, create cross-machine request
            requester_machine = self._detect_current_machine()
            
            if decision.target_machine != requester_machine:
                # Create cross-machine model transfer event
                transfer_event = create_cross_machine_request(
                    model_id=event.model_id,
                    target_machine=decision.target_machine,
                    source_machine=requester_machine,
                    coordination_type="transfer",
                    transfer_size_mb=event.expected_vram_mb,
                    source_agent=self.name,
                    machine_id=requester_machine
                )
                transfer_event.event_type = ModelEventType.CROSS_MACHINE_MODEL_TRANSFER
                publish_model_event(transfer_event)
                
                self.logger.info(f"Model {event.model_id} assigned to {decision.target_machine} (cross-machine)")
            else:
                self.logger.info(f"Model {event.model_id} assigned to local machine")
        else:
            self.logger.warning(f"No suitable machine found for model {event.model_id}")
    
    def _make_load_balancing_decision(self, event: ModelLoadEvent) -> LoadBalancingDecision:
        """Make an intelligent load balancing decision"""
        available_machines = [
            (machine_id, machine_info) 
            for machine_id, machine_info in self.machines.items()
            if machine_info.status in [MachineStatus.ONLINE, MachineStatus.DEGRADED]
        ]
        
        if not available_machines:
            return LoadBalancingDecision(
                target_machine="",
                confidence_score=0.0,
                reasoning="No available machines"
            )
        
        # Apply load balancing strategy
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_decision(available_machines, event)
        elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._least_loaded_decision(available_machines, event)
        elif self.strategy == LoadBalancingStrategy.BEST_PERFORMANCE:
            return self._best_performance_decision(available_machines, event)
        elif self.strategy == LoadBalancingStrategy.ADAPTIVE:
            return self._adaptive_decision(available_machines, event)
        else:
            # Fallback to least loaded
            return self._least_loaded_decision(available_machines, event)
    
    def _least_loaded_decision(self, machines: List[Tuple[str, MachineInfo]], event: ModelLoadEvent) -> LoadBalancingDecision:
        """Select machine with least current load"""
        best_machine = None
        best_score = float('inf')
        
        for machine_id, machine_info in machines:
            # Check if machine has enough memory
            if machine_info.available_gpu_memory_mb < event.expected_vram_mb:
                continue
            
            # Calculate load score (lower is better)
            load_score = (
                machine_info.avg_gpu_utilization * 0.4 +
                (machine_info.used_gpu_memory_mb / max(machine_info.total_gpu_memory_mb, 1)) * 100 * 0.4 +
                machine_info.cpu_percent * 0.2
            )
            
            if load_score < best_score:
                best_score = load_score
                best_machine = machine_id
        
        confidence = 1.0 - (best_score / 100.0) if best_machine else 0.0
        
        return LoadBalancingDecision(
            target_machine=best_machine or "",
            confidence_score=max(0.0, min(1.0, confidence)),
            reasoning=f"Least loaded machine (score: {best_score:.1f})",
            estimated_load_time_seconds=2.0 + (best_score / 100.0) * 3.0
        )
    
    def _adaptive_decision(self, machines: List[Tuple[str, MachineInfo]], event: ModelLoadEvent) -> LoadBalancingDecision:
        """Adaptive decision based on multiple factors"""
        best_machine = None
        best_score = 0.0
        
        for machine_id, machine_info in machines:
            # Check basic requirements
            if machine_info.available_gpu_memory_mb < event.expected_vram_mb:
                continue
            
            # Multi-factor scoring
            memory_score = (machine_info.available_gpu_memory_mb / max(machine_info.total_gpu_memory_mb, 1)) * 100
            utilization_score = 100 - machine_info.avg_gpu_utilization
            
            # Performance history bonus
            history_score = 50  # Base score
            if machine_id in self.performance_history:
                recent_performance = list(self.performance_history[machine_id])[-10:]
                if recent_performance:
                    avg_performance = sum(recent_performance) / len(recent_performance)
                    history_score = avg_performance
            
            # Machine capability bonus
            capability_score = 50
            if machine_info.capabilities.get("primary_machine"):
                capability_score += 20
            if machine_info.capabilities.get("gpu_count", 0) > 0:
                capability_score += 30
            
            # Network latency penalty
            latency_penalty = min(machine_info.network_latency_ms / 10.0, 20)
            
            # Combined score
            total_score = (
                memory_score * 0.3 +
                utilization_score * 0.25 +
                history_score * 0.2 +
                capability_score * 0.15 +
                (50 - latency_penalty) * 0.1
            )
            
            if total_score > best_score:
                best_score = total_score
                best_machine = machine_id
        
        confidence = best_score / 100.0 if best_machine else 0.0
        
        return LoadBalancingDecision(
            target_machine=best_machine or "",
            confidence_score=max(0.0, min(1.0, confidence)),
            reasoning=f"Adaptive scoring (score: {best_score:.1f})",
            estimated_load_time_seconds=1.0 + ((100 - best_score) / 100.0) * 4.0
        )
    
    def _round_robin_decision(self, machines: List[Tuple[str, MachineInfo]], event: ModelLoadEvent) -> LoadBalancingDecision:
        """Simple round-robin selection"""
        suitable_machines = [
            machine_id for machine_id, machine_info in machines
            if machine_info.available_gpu_memory_mb >= event.expected_vram_mb
        ]
        
        if not suitable_machines:
            return LoadBalancingDecision(
                target_machine="",
                confidence_score=0.0,
                reasoning="No machines with sufficient memory"
            )
        
        # Round robin selection
        selected_machine = suitable_machines[self.last_round_robin_index % len(suitable_machines)]
        self.last_round_robin_index += 1
        
        return LoadBalancingDecision(
            target_machine=selected_machine,
            confidence_score=0.8,  # Fixed confidence for round robin
            reasoning="Round-robin selection",
            estimated_load_time_seconds=2.0
        )
    
    def _best_performance_decision(self, machines: List[Tuple[str, MachineInfo]], event: ModelLoadEvent) -> LoadBalancingDecision:
        """Select machine with best historical performance"""
        best_machine = None
        best_performance = 0.0
        
        for machine_id, machine_info in machines:
            if machine_info.available_gpu_memory_mb < event.expected_vram_mb:
                continue
            
            # Get performance history
            if machine_id in self.performance_history:
                recent_scores = list(self.performance_history[machine_id])[-5:]
                if recent_scores:
                    avg_performance = sum(recent_scores) / len(recent_scores)
                    if avg_performance > best_performance:
                        best_performance = avg_performance
                        best_machine = machine_id
        
        # If no performance history, fall back to least loaded
        if not best_machine:
            return self._least_loaded_decision(machines, event)
        
        return LoadBalancingDecision(
            target_machine=best_machine,
            confidence_score=best_performance / 100.0,
            reasoning=f"Best performance (avg: {best_performance:.1f})",
            estimated_load_time_seconds=1.5
        )
    
    def _handle_vram_event(self, event: VRAMEvent) -> None:
        """Handle VRAM threshold events"""
        self.logger.warning(f"VRAM event: {event.event_type.value} on {event.machine_id}")
        
        # Update machine metrics
        if event.machine_id in self.machines:
            machine = self.machines[event.machine_id]
            if machine.gpu_metrics:
                # Update first GPU metrics (simplified)
                machine.gpu_metrics[0].memory_used_mb = event.used_vram_mb
                machine.gpu_metrics[0].memory_total_mb = event.total_vram_mb
        
        # Consider load rebalancing if critical
        if event.event_type == ModelEventType.GPU_MEMORY_CRITICAL:
            self._trigger_emergency_rebalancing(event.machine_id)
    
    def _handle_performance_event(self, event: ModelPerformanceEvent) -> None:
        """Handle performance degradation events"""
        self.logger.info(f"Performance event for model {event.model_id}: {event.event_type.value}")
        
        # Record performance metrics
        machine_id = self.model_placements.get(event.model_id)
        if machine_id:
            performance_score = 100.0 - (event.inference_time_ms / 1000.0) * 10  # Simplified scoring
            self.performance_history[machine_id].append(max(0, min(100, performance_score)))
    
    def _handle_cross_machine_event(self, event: CrossMachineModelEvent) -> None:
        """Handle cross-machine coordination events"""
        self.logger.info(f"Cross-machine event: {event.coordination_type} from {event.source_machine} to {event.target_machine}")
        
        if event.coordination_type == "rebalance":
            self._perform_load_rebalancing()
    
    def _trigger_emergency_rebalancing(self, overloaded_machine: str) -> None:
        """Trigger emergency load rebalancing"""
        self.logger.warning(f"Emergency rebalancing triggered for {overloaded_machine}")
        
        # Find models that can be moved
        models_to_move = [
            model_id for model_id, machine_id in self.model_placements.items()
            if machine_id == overloaded_machine
        ]
        
        # Try to move some models to other machines
        for model_id in models_to_move[:2]:  # Move up to 2 models
            # Find alternative machine
            best_machine = None
            best_capacity = 0
            
            for machine_id, machine_info in self.machines.items():
                if (machine_id != overloaded_machine and 
                    machine_info.status == MachineStatus.ONLINE and
                    machine_info.available_gpu_memory_mb > best_capacity):
                    best_capacity = machine_info.available_gpu_memory_mb
                    best_machine = machine_id
            
            if best_machine:
                # Create model transfer event
                transfer_event = create_cross_machine_request(
                    model_id=model_id,
                    target_machine=best_machine,
                    source_machine=overloaded_machine,
                    coordination_type="emergency_transfer",
                    transfer_priority=10,  # High priority
                    source_agent=self.name,
                    machine_id=overloaded_machine
                )
                publish_model_event(transfer_event)
                
                # Update tracking
                self.model_placements[model_id] = best_machine
                
                self.logger.info(f"Emergency transfer: {model_id} → {best_machine}")
    
    def _perform_load_rebalancing(self) -> None:
        """Perform proactive load rebalancing"""
        self.logger.info("Performing load rebalancing")
        
        # Calculate load distribution
        machine_loads = {}
        for machine_id, machine_info in self.machines.items():
            if machine_info.status == MachineStatus.ONLINE:
                load = machine_info.avg_gpu_utilization
                machine_loads[machine_id] = load
        
        if len(machine_loads) < 2:
            return  # Need at least 2 machines for rebalancing
        
        # Find imbalanced situation
        max_load = max(machine_loads.values())
        min_load = min(machine_loads.values())
        
        if max_load - min_load > 30:  # Significant imbalance
            overloaded_machine = max(machine_loads, key=machine_loads.get)
            underloaded_machine = min(machine_loads, key=machine_loads.get)
            
            self.logger.info(f"Rebalancing: {overloaded_machine} ({max_load:.1f}%) → {underloaded_machine} ({min_load:.1f}%)")
            
            # Move one model from overloaded to underloaded
            models_on_overloaded = [
                model_id for model_id, machine_id in self.model_placements.items()
                if machine_id == overloaded_machine
            ]
            
            if models_on_overloaded:
                model_to_move = models_on_overloaded[0]
                
                transfer_event = create_cross_machine_request(
                    model_id=model_to_move,
                    target_machine=underloaded_machine,
                    source_machine=overloaded_machine,
                    coordination_type="rebalance_transfer",
                    source_agent=self.name,
                    machine_id=overloaded_machine
                )
                publish_model_event(transfer_event)
                
                self.model_placements[model_to_move] = underloaded_machine
    
    def _adaptive_optimization(self) -> None:
        """Adaptive optimization based on system state"""
        # Analyze recent performance
        total_events = len(self.model_placements)
        if total_events == 0:
            return
        
        # Check if current strategy is working well
        recent_performance_scores = []
        for machine_id in self.machines:
            if machine_id in self.performance_history:
                recent_scores = list(self.performance_history[machine_id])[-10:]
                recent_performance_scores.extend(recent_scores)
        
        if recent_performance_scores:
            avg_performance = sum(recent_performance_scores) / len(recent_performance_scores)
            
            # Adapt strategy based on performance
            if avg_performance < 60 and self.strategy != LoadBalancingStrategy.BEST_PERFORMANCE:
                self.strategy = LoadBalancingStrategy.BEST_PERFORMANCE
                self.logger.info("Adapted strategy to BEST_PERFORMANCE due to low performance")
            elif avg_performance > 85 and self.strategy != LoadBalancingStrategy.LEAST_LOADED:
                self.strategy = LoadBalancingStrategy.LEAST_LOADED
                self.logger.info("Adapted strategy to LEAST_LOADED due to good performance")
    
    def _detect_current_machine(self) -> str:
        """Detect which machine we're currently running on"""
        # Simple hostname-based detection
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or "pc" in hostname and "pc2" not in hostname:
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default fallback
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status"""
        return {
            "machines": {
                machine_id: {
                    "status": machine_info.status.value,
                    "gpu_metrics": [
                        {
                            "gpu_id": gpu.gpu_id,
                            "utilization": gpu.utilization_percent,
                            "memory_used_mb": gpu.memory_used_mb,
                            "memory_total_mb": gpu.memory_total_mb,
                            "temperature": gpu.temperature_celsius
                        }
                        for gpu in machine_info.gpu_metrics
                    ],
                    "total_memory_mb": machine_info.total_gpu_memory_mb,
                    "used_memory_mb": machine_info.used_gpu_memory_mb,
                    "available_memory_mb": machine_info.available_gpu_memory_mb,
                    "avg_utilization": machine_info.avg_gpu_utilization,
                    "last_heartbeat": machine_info.last_heartbeat.isoformat()
                }
                for machine_id, machine_info in self.machines.items()
            },
            "model_placements": self.model_placements.copy(),
            "strategy": self.strategy.value,
            "total_models": len(self.model_placements)
        }
    
    def shutdown(self):
        """Clean up subscriptions"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    logger = configure_logging(__name__, level="INFO")
    
    load_balancer = GPULoadBalancer(strategy=LoadBalancingStrategy.ADAPTIVE)
    
    try:
        # Simulate some load balancing activity
        time.sleep(5)
        
        # Print cluster status
        status = load_balancer.get_cluster_status()
        print(json.dumps(status, indent=2))
        
        # Keep running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("Shutting down GPU Load Balancer...")
        load_balancer.shutdown() 