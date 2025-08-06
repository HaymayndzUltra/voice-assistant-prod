#!/usr/bin/env python3
"""
GPU Failover Manager - Automatic Model Migration and Disaster Recovery
Provides automatic failover capabilities for GPU resources across MainPC and PC2.

Features:
- Automatic machine failure detection
- Model migration between machines
- Disaster recovery scenarios
- Health-based auto-failover
- Recovery orchestration
- Data synchronization
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
import hashlib
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum

# Core imports
from common.core.base_agent import BaseAgent

# Event system imports
from events.model_events import (
    ModelEventType, create_cross_machine_request, create_model_status_change, ModelStatus
)
from events.event_bus import (
    get_event_bus, publish_model_event, subscribe_to_model_events, subscribe_to_memory_events
)

class FailoverTrigger(Enum):
    """Failover trigger types"""
    MACHINE_OFFLINE = "machine_offline"
    GPU_FAILURE = "gpu_failure"
    MEMORY_CRITICAL = "memory_critical"
    PERFORMANCE_DEGRADED = "performance_degraded"
    MANUAL = "manual"
    PREVENTIVE = "preventive"

class FailoverStrategy(Enum):
    """Failover strategies"""
    IMMEDIATE = "immediate"          # Immediate failover
    GRACEFUL = "graceful"           # Wait for current operations to complete
    SELECTIVE = "selective"         # Only critical models
    FULL_MIGRATION = "full_migration"  # All models
    LOAD_BALANCE = "load_balance"   # Distribute load

class RecoveryState(Enum):
    """Recovery states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    FAILED = "failed"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"

@dataclass
class FailoverPlan:
    """Failover execution plan"""
    trigger: FailoverTrigger
    source_machine: str
    target_machines: List[str]
    strategy: FailoverStrategy
    models_to_migrate: List[str]
    estimated_time_seconds: float
    risk_assessment: str  # low, medium, high
    prerequisites: List[str] = field(default_factory=list)
    rollback_plan: Optional['FailoverPlan'] = None

@dataclass
class MachineHealth:
    """Machine health tracking"""
    machine_id: str
    state: RecoveryState
    last_heartbeat: datetime
    consecutive_failures: int = 0
    gpu_failures: int = 0
    memory_failures: int = 0
    network_failures: int = 0
    recovery_attempts: int = 0
    last_failure_time: Optional[datetime] = None
    health_score: float = 100.0  # 0-100
    
    def update_failure(self, failure_type: str):
        """Update failure counters"""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        
        if failure_type == "gpu":
            self.gpu_failures += 1
        elif failure_type == "memory":
            self.memory_failures += 1
        elif failure_type == "network":
            self.network_failures += 1
        
        # Update health score
        self.health_score = max(0, self.health_score - 10)
    
    def reset_failures(self):
        """Reset failure counters on recovery"""
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.health_score = min(100, self.health_score + 20)

@dataclass
class ModelMigrationJob:
    """Model migration job tracking"""
    job_id: str
    model_id: str
    source_machine: str
    target_machine: str
    migration_type: str  # failover, load_balance, maintenance
    status: str  # queued, in_progress, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    error_message: str = ""
    data_transferred_mb: int = 0
    estimated_total_mb: int = 0

class GPUFailoverManager(BaseAgent):
    """
    GPU Failover Manager for automatic disaster recovery.
    
    Monitors machine health and automatically migrates models
    between machines when failures are detected. Provides
    comprehensive disaster recovery capabilities.
    """
    
    def __init__(self, 
                 heartbeat_timeout_seconds: int = 60,
                 failure_threshold: int = 3,
                 **kwargs):
        super().__init__(name="GPUFailoverManager", **kwargs)
        
        # Configuration
        self.heartbeat_timeout = heartbeat_timeout_seconds
        self.failure_threshold = failure_threshold
        
        # Machine health tracking
        self.machine_health: Dict[str, MachineHealth] = {}
        self.migration_jobs: Dict[str, ModelMigrationJob] = {}
        self.failover_history: deque = deque(maxlen=1000)
        
        # Model tracking
        self.model_locations: Dict[str, str] = {}  # model_id -> machine_id
        self.model_replicas: Dict[str, Set[str]] = defaultdict(set)  # model_id -> set of machines
        self.critical_models: Set[str] = set()
        
        # Failover state
        self.failover_in_progress = False
        self.recovery_plans: Dict[str, FailoverPlan] = {}
        
        # Event subscriptions
        self.subscription_ids = []
        
        # Initialize components
        self._initialize_machine_health()
        self._setup_event_subscriptions()
        self._start_monitoring_threads()
        
        self.logger.info("GPU Failover Manager initialized")
    
    def _initialize_machine_health(self) -> None:
        """Initialize machine health tracking"""
        machines = ["MainPC", "PC2"]
        
        for machine_id in machines:
            health = MachineHealth(
                machine_id=machine_id,
                state=RecoveryState.HEALTHY,
                last_heartbeat=datetime.now()
            )
            self.machine_health[machine_id] = health
    
    def _setup_event_subscriptions(self) -> None:
        """Subscribe to relevant events"""
        # Subscribe to all model events for comprehensive monitoring
        sub_id = subscribe_to_model_events(
            subscriber_id="GPUFailoverManager",
            event_types="*",
            callback=self._handle_model_event,
            priority=35  # Very high priority for failover decisions
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to memory events
        sub_id = subscribe_to_memory_events(
            subscriber_id="GPUFailoverManager",
            event_types="*",
            callback=self._handle_memory_event,
            priority=35
        )
        self.subscription_ids.append(sub_id)
        
        self.logger.info("GPU Failover Manager event subscriptions configured")
    
    def _start_monitoring_threads(self) -> None:
        """Start background monitoring threads"""
        # Health monitoring thread
        health_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        health_thread.start()
        
        # Failover decision thread
        failover_thread = threading.Thread(target=self._failover_decision_loop, daemon=True)
        failover_thread.start()
        
        # Migration execution thread
        migration_thread = threading.Thread(target=self._migration_execution_loop, daemon=True)
        migration_thread.start()
        
        # Recovery orchestration thread
        recovery_thread = threading.Thread(target=self._recovery_orchestration_loop, daemon=True)
        recovery_thread.start()
    
    def _health_monitoring_loop(self) -> None:
        """Monitor machine health and detect failures"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for machine_id, health in self.machine_health.items():
                    # Check heartbeat timeout
                    time_since_heartbeat = (current_time - health.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        if health.state != RecoveryState.FAILED:
                            self.logger.warning(f"Machine {machine_id} heartbeat timeout: {time_since_heartbeat:.1f}s")
                            health.update_failure("network")
                            
                            # Update state based on consecutive failures
                            if health.consecutive_failures >= self.failure_threshold:
                                health.state = RecoveryState.FAILED
                                self._trigger_failover(machine_id, FailoverTrigger.MACHINE_OFFLINE)
                            elif health.consecutive_failures >= 2:
                                health.state = RecoveryState.FAILING
                            else:
                                health.state = RecoveryState.DEGRADED
                    else:
                        # Machine is responsive
                        if health.state in [RecoveryState.FAILED, RecoveryState.FAILING, RecoveryState.DEGRADED]:
                            if health.consecutive_failures > 0:
                                health.reset_failures()
                                health.state = RecoveryState.RECOVERING
                                self.logger.info(f"Machine {machine_id} recovering")
                        elif health.state == RecoveryState.RECOVERING:
                            health.state = RecoveryState.HEALTHY
                            self.logger.info(f"Machine {machine_id} fully recovered")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                time.sleep(30)
    
    def _failover_decision_loop(self) -> None:
        """Make failover decisions based on system state"""
        while self.running:
            try:
                # Check for preventive failover opportunities
                self._evaluate_preventive_failover()
                
                # Check for performance-based failover
                self._evaluate_performance_failover()
                
                time.sleep(60)  # Evaluate every minute
                
            except Exception as e:
                self.logger.error(f"Failover decision error: {e}")
                time.sleep(120)
    
    def _migration_execution_loop(self) -> None:
        """Execute model migration jobs"""
        while self.running:
            try:
                # Process queued migration jobs
                queued_jobs = [job for job in self.migration_jobs.values() if job.status == "queued"]
                
                for job in queued_jobs[:3]:  # Process up to 3 jobs concurrently
                    self._execute_migration_job(job)
                
                # Update job progress
                self._update_migration_progress()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Migration execution error: {e}")
                time.sleep(30)
    
    def _recovery_orchestration_loop(self) -> None:
        """Orchestrate recovery operations"""
        while self.running:
            try:
                # Check for machines in recovery state
                recovering_machines = [
                    machine_id for machine_id, health in self.machine_health.items()
                    if health.state == RecoveryState.RECOVERING
                ]
                
                for machine_id in recovering_machines:
                    self._orchestrate_machine_recovery(machine_id)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Recovery orchestration error: {e}")
                time.sleep(60)
    
    def _trigger_failover(self, failed_machine: str, trigger: FailoverTrigger) -> None:
        """Trigger failover for a failed machine"""
        if self.failover_in_progress:
            self.logger.warning(f"Failover already in progress, queuing failover for {failed_machine}")
            return
        
        self.failover_in_progress = True
        
        try:
            self.logger.critical(f"Triggering failover for {failed_machine} due to {trigger.value}")
            
            # Create failover plan
            plan = self._create_failover_plan(failed_machine, trigger)
            
            if plan:
                # Execute failover plan
                self._execute_failover_plan(plan)
                
                # Record failover event
                self.failover_history.append({
                    'timestamp': datetime.now(),
                    'trigger': trigger.value,
                    'source_machine': failed_machine,
                    'target_machines': plan.target_machines,
                    'models_migrated': len(plan.models_to_migrate),
                    'strategy': plan.strategy.value
                })
            else:
                self.logger.error(f"Could not create failover plan for {failed_machine}")
                
        finally:
            self.failover_in_progress = False
    
    def _create_failover_plan(self, failed_machine: str, trigger: FailoverTrigger) -> Optional[FailoverPlan]:
        """Create a failover plan for the failed machine"""
        # Find models on the failed machine
        models_on_failed_machine = [
            model_id for model_id, machine_id in self.model_locations.items()
            if machine_id == failed_machine
        ]
        
        if not models_on_failed_machine:
            self.logger.info(f"No models to failover from {failed_machine}")
            return None
        
        # Find healthy target machines
        healthy_machines = [
            machine_id for machine_id, health in self.machine_health.items()
            if machine_id != failed_machine and health.state == RecoveryState.HEALTHY
        ]
        
        if not healthy_machines:
            self.logger.critical("No healthy machines available for failover!")
            return None
        
        # Determine strategy based on trigger
        if trigger == FailoverTrigger.MACHINE_OFFLINE:
            strategy = FailoverStrategy.IMMEDIATE
        elif trigger == FailoverTrigger.GPU_FAILURE:
            strategy = FailoverStrategy.GRACEFUL
        elif trigger == FailoverTrigger.MEMORY_CRITICAL:
            strategy = FailoverStrategy.SELECTIVE
        else:
            strategy = FailoverStrategy.LOAD_BALANCE
        
        # Select models to migrate based on strategy
        if strategy == FailoverStrategy.SELECTIVE:
            # Only migrate critical models
            models_to_migrate = [m for m in models_on_failed_machine if m in self.critical_models]
        else:
            # Migrate all models
            models_to_migrate = models_on_failed_machine
        
        # Estimate migration time
        estimated_time = len(models_to_migrate) * 30  # 30 seconds per model
        
        # Assess risk
        risk_assessment = "low"
        if len(models_to_migrate) > 5:
            risk_assessment = "medium"
        if len(healthy_machines) == 1:
            risk_assessment = "high"
        
        plan = FailoverPlan(
            trigger=trigger,
            source_machine=failed_machine,
            target_machines=healthy_machines,
            strategy=strategy,
            models_to_migrate=models_to_migrate,
            estimated_time_seconds=estimated_time,
            risk_assessment=risk_assessment
        )
        
        self.logger.info(f"Created failover plan: {len(models_to_migrate)} models, {estimated_time}s estimated, {risk_assessment} risk")
        
        return plan
    
    def _execute_failover_plan(self, plan: FailoverPlan) -> None:
        """Execute the failover plan"""
        self.logger.info(f"Executing failover plan for {plan.source_machine}")
        
        # Distribute models across target machines
        target_index = 0
        
        for model_id in plan.models_to_migrate:
            target_machine = plan.target_machines[target_index % len(plan.target_machines)]
            target_index += 1
            
            # Create migration job
            job_id = self._generate_job_id(model_id, target_machine)
            
            migration_job = ModelMigrationJob(
                job_id=job_id,
                model_id=model_id,
                source_machine=plan.source_machine,
                target_machine=target_machine,
                migration_type="failover",
                status="queued",
                estimated_total_mb=2048  # Estimate 2GB per model
            )
            
            self.migration_jobs[job_id] = migration_job
            
            self.logger.info(f"Queued migration: {model_id} → {target_machine}")
        
        # Update recovery plan
        self.recovery_plans[plan.source_machine] = plan
    
    def _execute_migration_job(self, job: ModelMigrationJob) -> None:
        """Execute a single model migration job"""
        job.status = "in_progress"
        job.started_at = datetime.now()
        
        try:
            self.logger.info(f"Starting migration: {job.model_id} from {job.source_machine} to {job.target_machine}")
            
            # Step 1: Validate target machine capacity
            if not self._validate_target_capacity(job.target_machine, job.estimated_total_mb):
                job.status = "failed"
                job.error_message = "Insufficient capacity on target machine"
                return
            
            job.progress_percentage = 10.0
            
            # Step 2: Create cross-machine transfer event
            transfer_event = create_cross_machine_request(
                model_id=job.model_id,
                target_machine=job.target_machine,
                source_machine=job.source_machine,
                coordination_type="failover_migration",
                transfer_size_mb=job.estimated_total_mb,
                priority=20,  # High priority for failover
                source_agent=self.name,
                machine_id=job.source_machine
            )
            
            publish_model_event(transfer_event)
            
            job.progress_percentage = 30.0
            
            # Step 3: Simulate model transfer (in real implementation, this would coordinate actual transfer)
            transfer_time = max(5, job.estimated_total_mb / 1024)  # 1 second per GB
            
            for i in range(10):
                time.sleep(transfer_time / 10)
                job.progress_percentage = 30.0 + (i + 1) * 6.0  # 30% to 90%
                job.data_transferred_mb = int((job.progress_percentage / 100) * job.estimated_total_mb)
            
            # Step 4: Update model location tracking
            self.model_locations[job.model_id] = job.target_machine
            
            # Step 5: Create model loaded event on target machine
            loaded_event = create_model_status_change(
                model_id=job.model_id,
                old_status=ModelStatus.TRANSFERRING,
                new_status=ModelStatus.LOADED,
                vram_usage_mb=job.estimated_total_mb,
                load_time_seconds=transfer_time,
                source_agent=self.name,
                machine_id=job.target_machine
            )
            
            publish_model_event(loaded_event)
            
            job.progress_percentage = 100.0
            job.status = "completed"
            job.completed_at = datetime.now()
            
            self.logger.info(f"Migration completed: {job.model_id} → {job.target_machine}")
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            self.logger.error(f"Migration failed: {job.model_id} - {e}")
    
    def _validate_target_capacity(self, target_machine: str, required_mb: int) -> bool:
        """Validate that target machine has sufficient capacity"""
        # In real implementation, this would check actual machine capacity
        # For now, simulate capacity check
        
        machine_health = self.machine_health.get(target_machine)
        if not machine_health or machine_health.state != RecoveryState.HEALTHY:
            return False
        
        # Assume machines have sufficient capacity for demo
        return True
    
    def _update_migration_progress(self) -> None:
        """Update progress of active migration jobs"""
        active_jobs = [job for job in self.migration_jobs.values() if job.status == "in_progress"]
        
        for job in active_jobs:
            # Check if job has been running too long
            if job.started_at:
                running_time = (datetime.now() - job.started_at).total_seconds()
                if running_time > 300:  # 5 minutes timeout
                    job.status = "failed"
                    job.error_message = "Migration timeout"
                    self.logger.error(f"Migration timeout: {job.model_id}")
    
    def _evaluate_preventive_failover(self) -> None:
        """Evaluate opportunities for preventive failover"""
        for machine_id, health in self.machine_health.items():
            # Check if machine is degraded and should be preemptively failed over
            if (health.state == RecoveryState.DEGRADED and 
                health.consecutive_failures >= 2 and
                health.health_score < 50):
                
                self.logger.info(f"Considering preventive failover for {machine_id} (health: {health.health_score})")
                
                # Only do preventive failover if we have healthy alternatives
                healthy_alternatives = [
                    mid for mid, h in self.machine_health.items()
                    if mid != machine_id and h.state == RecoveryState.HEALTHY
                ]
                
                if healthy_alternatives:
                    self._trigger_failover(machine_id, FailoverTrigger.PREVENTIVE)
    
    def _evaluate_performance_failover(self) -> None:
        """Evaluate performance-based failover needs"""
        # This would analyze performance metrics and trigger failover for poor performers
        # For now, just log that we're evaluating
        degraded_machines = [
            machine_id for machine_id, health in self.machine_health.items()
            if health.health_score < 70
        ]
        
        if degraded_machines:
            self.logger.debug(f"Performance evaluation: {len(degraded_machines)} degraded machines")
    
    def _orchestrate_machine_recovery(self, machine_id: str) -> None:
        """Orchestrate recovery operations for a recovering machine"""
        health = self.machine_health[machine_id]
        
        self.logger.info(f"Orchestrating recovery for {machine_id}")
        
        # Check if we have a recovery plan
        if machine_id in self.recovery_plans:
            plan = self.recovery_plans[machine_id]
            
            # Check if we should start migrating models back
            if health.consecutive_failures == 0 and health.health_score > 80:
                self.logger.info(f"Machine {machine_id} stable, considering model restoration")
                self._plan_model_restoration(machine_id, plan)
    
    def _plan_model_restoration(self, machine_id: str, original_plan: FailoverPlan) -> None:
        """Plan restoration of models to recovered machine"""
        # Find models that were originally on this machine
        models_to_restore = []
        
        for model_id in original_plan.models_to_migrate:
            current_location = self.model_locations.get(model_id)
            
            # Only restore if model is still active and we want load balancing
            if current_location and current_location != machine_id:
                models_to_restore.append(model_id)
        
        if models_to_restore:
            self.logger.info(f"Planning restoration of {len(models_to_restore)} models to {machine_id}")
            
            # Create restoration jobs (selective restoration)
            for model_id in models_to_restore[:2]:  # Restore only 2 models initially
                current_location = self.model_locations[model_id]
                
                job_id = self._generate_job_id(model_id, machine_id)
                
                restoration_job = ModelMigrationJob(
                    job_id=job_id,
                    model_id=model_id,
                    source_machine=current_location,
                    target_machine=machine_id,
                    migration_type="restoration",
                    status="queued",
                    estimated_total_mb=2048
                )
                
                self.migration_jobs[job_id] = restoration_job
    
    def _handle_model_event(self, event) -> None:
        """Handle model-related events"""
        # Update machine heartbeat
        if hasattr(event, 'machine_id') and event.machine_id in self.machine_health:
            self.machine_health[event.machine_id].last_heartbeat = datetime.now()
        
        if event.event_type == ModelEventType.MODEL_LOADED:
            # Track model location
            self.model_locations[event.model_id] = event.machine_id
            
        elif event.event_type == ModelEventType.MODEL_UNLOADED:
            # Remove from tracking
            if event.model_id in self.model_locations:
                del self.model_locations[event.model_id]
        
        elif event.event_type == ModelEventType.GPU_MEMORY_CRITICAL:
            # Trigger memory-based failover
            machine_id = getattr(event, 'machine_id', '')
            if machine_id and machine_id in self.machine_health:
                health = self.machine_health[machine_id]
                health.update_failure("memory")
                
                if health.consecutive_failures >= 2:
                    self._trigger_failover(machine_id, FailoverTrigger.MEMORY_CRITICAL)
        
        elif event.event_type == ModelEventType.MODEL_PERFORMANCE_DEGRADED:
            # Track performance issues
            machine_id = getattr(event, 'machine_id', '')
            if machine_id and machine_id in self.machine_health:
                health = self.machine_health[machine_id]
                health.health_score = max(0, health.health_score - 5)
                
                if health.health_score < 30:
                    self._trigger_failover(machine_id, FailoverTrigger.PERFORMANCE_DEGRADED)
    
    def _handle_memory_event(self, event) -> None:
        """Handle memory-related events"""
        # Update machine heartbeat if applicable
        if hasattr(event, 'machine_id') and event.machine_id in self.machine_health:
            self.machine_health[event.machine_id].last_heartbeat = datetime.now()
    
    def _generate_job_id(self, model_id: str, target_machine: str) -> str:
        """Generate unique job ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = f"{model_id}_{target_machine}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def manual_failover(self, machine_id: str, target_machines: Optional[List[str]] = None) -> bool:
        """Manually trigger failover for a machine"""
        if machine_id not in self.machine_health:
            self.logger.error(f"Unknown machine: {machine_id}")
            return False
        
        if self.failover_in_progress:
            self.logger.warning("Failover already in progress")
            return False
        
        self.logger.info(f"Manual failover triggered for {machine_id}")
        
        # If no target machines specified, use all healthy machines
        if not target_machines:
            target_machines = [
                mid for mid, health in self.machine_health.items()
                if mid != machine_id and health.state == RecoveryState.HEALTHY
            ]
        
        if not target_machines:
            self.logger.error("No healthy target machines available")
            return False
        
        # Create manual failover plan
        models_on_machine = [
            model_id for model_id, location in self.model_locations.items()
            if location == machine_id
        ]
        
        plan = FailoverPlan(
            trigger=FailoverTrigger.MANUAL,
            source_machine=machine_id,
            target_machines=target_machines,
            strategy=FailoverStrategy.GRACEFUL,
            models_to_migrate=models_on_machine,
            estimated_time_seconds=len(models_on_machine) * 30,
            risk_assessment="low"
        )
        
        self._execute_failover_plan(plan)
        return True
    
    def add_critical_model(self, model_id: str) -> None:
        """Mark a model as critical for priority failover"""
        self.critical_models.add(model_id)
        self.logger.info(f"Model {model_id} marked as critical")
    
    def remove_critical_model(self, model_id: str) -> None:
        """Remove critical status from a model"""
        self.critical_models.discard(model_id)
        self.logger.info(f"Model {model_id} removed from critical list")
    
    def get_failover_status(self) -> Dict[str, Any]:
        """Get comprehensive failover status"""
        return {
            'machine_health': {
                machine_id: {
                    'state': health.state.value,
                    'health_score': health.health_score,
                    'consecutive_failures': health.consecutive_failures,
                    'last_heartbeat': health.last_heartbeat.isoformat(),
                    'recovery_attempts': health.recovery_attempts
                }
                for machine_id, health in self.machine_health.items()
            },
            'model_distribution': {
                machine_id: [
                    model_id for model_id, location in self.model_locations.items()
                    if location == machine_id
                ]
                for machine_id in self.machine_health.keys()
            },
            'active_migrations': {
                job_id: {
                    'model_id': job.model_id,
                    'source': job.source_machine,
                    'target': job.target_machine,
                    'status': job.status,
                    'progress': job.progress_percentage,
                    'type': job.migration_type
                }
                for job_id, job in self.migration_jobs.items()
                if job.status in ['queued', 'in_progress']
            },
            'critical_models': list(self.critical_models),
            'failover_in_progress': self.failover_in_progress,
            'recent_failovers': list(self.failover_history)[-10:],  # Last 10 failovers
            'total_migrations': len(self.migration_jobs)
        }
    
    def shutdown(self):
        """Clean up subscriptions and resources"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    logger = configure_logging(__name__, level="INFO")
    
    failover_manager = GPUFailoverManager(
        heartbeat_timeout_seconds=60,
        failure_threshold=3
    )
    
    try:
        # Add some critical models
        failover_manager.add_critical_model("critical_model_1")
        failover_manager.add_critical_model("important_model_2")
        
        # Print initial status
        status = failover_manager.get_failover_status()
        print(json.dumps(status, indent=2))
        
        # Keep running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("Shutting down GPU Failover Manager...")
        failover_manager.shutdown() 