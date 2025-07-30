#!/usr/bin/env python3
"""
Migration-Specific Observability and Metrics
===========================================
Enhanced observability configuration for Phase 2 Week 2 agent migration tracking
Provides real-time migration monitoring, alerting, and comprehensive metrics collection
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import requests
from common.path_manager import PathManager

logger = logging.getLogger("MigrationMetrics")

class MigrationPhase(Enum):
    """Migration phases for tracking"""
    PREPARATION = "preparation"
    INFRASTRUCTURE_VALIDATION = "infrastructure_validation"
    BATCH_1_CORE = "batch_1_core_infrastructure"
    BATCH_2_MEMORY = "batch_2_memory_context"
    BATCH_3_PROCESSING = "batch_3_processing_communication"
    BATCH_4_SPECIALIZED = "batch_4_specialized"
    FINAL_VALIDATION = "final_validation"
    COMPLETED = "completed"
    FAILED = "failed"

class MigrationStatus(Enum):
    """Individual agent migration status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class MigrationMetric:
    """Individual migration metric"""
    agent_name: str
    metric_type: str
    value: float
    timestamp: datetime
    phase: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentMigrationTracker:
    """Track individual agent migration progress"""
    agent_name: str
    batch_name: str
    status: MigrationStatus = MigrationStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    pre_migration_baseline: Dict[str, float] = field(default_factory=dict)
    post_migration_metrics: Dict[str, float] = field(default_factory=dict)
    performance_delta: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None
    rollback_performed: bool = False
    cross_machine_test_passed: bool = False

class MigrationObservabilityHub:
    """Enhanced observability specifically for migration tracking"""
    
    def __init__(self):
        self.centralhub_endpoint = "http://192.168.100.16:9000"
        self.edgehub_endpoint = "http://192.168.1.2:9100"
        self.prometheus_mainpc = "http://192.168.100.16:9091"
        self.prometheus_pc2 = "http://192.168.1.2:9091"
        
        # Migration tracking
        self.current_phase = MigrationPhase.PREPARATION
        self.migration_start_time = None
        self.agent_trackers: Dict[str, AgentMigrationTracker] = {}
        self.metrics_buffer: List[MigrationMetric] = []
        
        # Real-time statistics
        self.migration_stats = {
            "total_agents": 0,
            "completed_agents": 0,
            "failed_agents": 0,
            "rolled_back_agents": 0,
            "current_batch": None,
            "overall_progress_percent": 0.0,
            "estimated_completion_time": None,
            "average_migration_time": 0.0
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "failure_rate_percent": 20.0,  # Alert if >20% fail
            "performance_degradation_percent": 25.0,  # Alert if >25% slower
            "migration_timeout_minutes": 60.0,  # Alert if single migration >60min
            "batch_timeout_hours": 6.0  # Alert if batch >6 hours
        }
        
        # Real-time monitoring thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Initialize observability integration
        self._setup_observability_integration()
    
    def _setup_observability_integration(self):
        """Setup integration with existing ObservabilityHubs"""
        logger.info("🔧 Setting up migration observability integration")
        
        # Test connectivity to both hubs
        try:
            central_response = requests.get(f"{self.centralhub_endpoint}/health", timeout=5)
            if central_response.status_code == 200:
                logger.info("✅ CentralHub observability connection established")
            else:
                logger.warning("⚠️ CentralHub observability connection degraded")
        except Exception as e:
            logger.warning(f"⚠️ CentralHub observability unreachable: {e}")
        
        try:
            edge_response = requests.get(f"{self.edgehub_endpoint}/health", timeout=5)
            if edge_response.status_code == 200:
                logger.info("✅ EdgeHub observability connection established")
            else:
                logger.warning("⚠️ EdgeHub observability connection degraded")
        except Exception as e:
            logger.warning(f"⚠️ EdgeHub observability unreachable: {e}")
    
    def start_migration_tracking(self, agents: List[str], batches: Dict[str, List[str]]):
        """Initialize migration tracking for all agents"""
        logger.info(f"🚀 Starting migration tracking for {len(agents)} agents")
        
        self.migration_start_time = datetime.now()
        self.current_phase = MigrationPhase.PREPARATION
        
        # Initialize agent trackers
        for agent_name in agents:
            # Find which batch this agent belongs to
            batch_name = "unknown"
            for batch, batch_agents in batches.items():
                if agent_name in batch_agents:
                    batch_name = batch
                    break
            
            self.agent_trackers[agent_name] = AgentMigrationTracker(
                agent_name=agent_name,
                batch_name=batch_name
            )
        
        self.migration_stats["total_agents"] = len(agents)
        
        # Start real-time monitoring
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._migration_monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info("✅ Migration tracking initialized")
    
    def set_migration_phase(self, phase: MigrationPhase):
        """Update current migration phase"""
        logger.info(f"📍 Migration phase: {self.current_phase.value} → {phase.value}")
        self.current_phase = phase
        
        # Record phase transition metric
        self.record_migration_metric(
            agent_name="system",
            metric_type="phase_transition",
            value=1.0,
            metadata={
                "from_phase": self.current_phase.value,
                "to_phase": phase.value,
                "transition_time": datetime.now().isoformat()
            }
        )
    
    def start_agent_migration(self, agent_name: str):
        """Mark agent migration as started"""
        if agent_name in self.agent_trackers:
            tracker = self.agent_trackers[agent_name]
            tracker.status = MigrationStatus.IN_PROGRESS
            tracker.start_time = datetime.now()
            
            logger.info(f"🔄 Started migration: {agent_name}")
            
            # Record start metric
            self.record_migration_metric(
                agent_name=agent_name,
                metric_type="migration_start",
                value=1.0,
                metadata={"batch": tracker.batch_name}
            )
    
    def complete_agent_migration(self, agent_name: str, success: bool, 
                                performance_delta: Optional[Dict[str, float]] = None,
                                error_message: Optional[str] = None):
        """Mark agent migration as completed"""
        if agent_name not in self.agent_trackers:
            logger.warning(f"Unknown agent: {agent_name}")
            return
        
        tracker = self.agent_trackers[agent_name]
        tracker.end_time = datetime.now()
        tracker.status = MigrationStatus.COMPLETED if success else MigrationStatus.FAILED
        
        if performance_delta:
            tracker.performance_delta = performance_delta
        
        if error_message:
            tracker.error_message = error_message
        
        # Update statistics
        if success:
            self.migration_stats["completed_agents"] += 1
            logger.info(f"✅ Completed migration: {agent_name}")
        else:
            self.migration_stats["failed_agents"] += 1
            logger.error(f"❌ Failed migration: {agent_name} - {error_message}")
        
        # Calculate migration time
        if tracker.start_time and tracker.end_time:
            migration_time = (tracker.end_time - tracker.start_time).total_seconds()
            
            # Record completion metric
            self.record_migration_metric(
                agent_name=agent_name,
                metric_type="migration_duration",
                value=migration_time,
                metadata={
                    "success": success,
                    "batch": tracker.batch_name,
                    "performance_delta": performance_delta,
                    "error": error_message
                }
            )
            
            # Update average migration time
            self._update_average_migration_time()
            
            # Check for alerts
            self._check_migration_alerts(agent_name, tracker)
    
    def record_agent_rollback(self, agent_name: str, rollback_success: bool):
        """Record agent rollback event"""
        if agent_name in self.agent_trackers:
            tracker = self.agent_trackers[agent_name]
            tracker.rollback_performed = True
            tracker.status = MigrationStatus.ROLLED_BACK
            
            if rollback_success:
                logger.info(f"🔄 Rollback successful: {agent_name}")
            else:
                logger.error(f"💥 Rollback failed: {agent_name}")
            
            self.migration_stats["rolled_back_agents"] += 1
            
            # Record rollback metric
            self.record_migration_metric(
                agent_name=agent_name,
                metric_type="rollback",
                value=1.0 if rollback_success else 0.0,
                metadata={"rollback_success": rollback_success}
            )
    
    def record_cross_machine_test(self, agent_name: str, test_passed: bool, 
                                 latency_ms: Optional[float] = None):
        """Record cross-machine communication test results"""
        if agent_name in self.agent_trackers:
            tracker = self.agent_trackers[agent_name]
            tracker.cross_machine_test_passed = test_passed
            
            metadata = {"test_passed": test_passed}
            if latency_ms is not None:
                metadata["latency_ms"] = latency_ms
            
            self.record_migration_metric(
                agent_name=agent_name,
                metric_type="cross_machine_test",
                value=latency_ms if latency_ms else (1.0 if test_passed else 0.0),
                metadata=metadata
            )
            
            if test_passed:
                logger.info(f"🌐 Cross-machine test passed: {agent_name} ({latency_ms}ms)")
            else:
                logger.warning(f"⚠️ Cross-machine test failed: {agent_name}")
    
    def record_performance_baseline(self, agent_name: str, baseline: Dict[str, float]):
        """Record pre-migration performance baseline"""
        if agent_name in self.agent_trackers:
            self.agent_trackers[agent_name].pre_migration_baseline = baseline
            
            for metric_name, value in baseline.items():
                self.record_migration_metric(
                    agent_name=agent_name,
                    metric_type=f"baseline_{metric_name}",
                    value=value,
                    metadata={"baseline": True}
                )
            
            logger.info(f"📊 Baseline recorded for {agent_name}: {baseline}")
    
    def record_migration_metric(self, agent_name: str, metric_type: str, value: float,
                               metadata: Optional[Dict[str, Any]] = None):
        """Record a migration-specific metric"""
        metric = MigrationMetric(
            agent_name=agent_name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            phase=self.current_phase.value,
            metadata=metadata or {}
        )
        
        self.metrics_buffer.append(metric)
        
        # Send to observability hubs
        self._send_metric_to_hubs(metric)
        
        # Trim buffer if it gets too large
        if len(self.metrics_buffer) > 10000:
            self.metrics_buffer = self.metrics_buffer[-5000:]  # Keep last 5000
    
    def _send_metric_to_hubs(self, metric: MigrationMetric):
        """Send metric to both CentralHub and EdgeHub"""
        metric_data = {
            "agent_name": metric.agent_name,
            "metric_type": metric.metric_type,
            "value": metric.value,
            "timestamp": metric.timestamp.isoformat(),
            "phase": metric.phase,
            "metadata": metric.metadata,
            "source": "migration_manager"
        }
        
        # Send to CentralHub
        try:
            requests.post(
                f"{self.centralhub_endpoint}/metrics/migration",
                json=metric_data,
                timeout=5
            )
        except Exception as e:
            logger.debug(f"Failed to send metric to CentralHub: {e}")
        
        # Send to EdgeHub
        try:
            requests.post(
                f"{self.edgehub_endpoint}/metrics/migration",
                json=metric_data,
                timeout=5
            )
        except Exception as e:
            logger.debug(f"Failed to send metric to EdgeHub: {e}")
    
    def _update_average_migration_time(self):
        """Update average migration time calculation"""
        completed_trackers = [
            t for t in self.agent_trackers.values() 
            if t.status == MigrationStatus.COMPLETED and t.start_time and t.end_time
        ]
        
        if completed_trackers:
            total_time = sum(
                (t.end_time - t.start_time).total_seconds() 
                for t in completed_trackers
            )
            self.migration_stats["average_migration_time"] = total_time / len(completed_trackers)
            
            # Estimate completion time for remaining agents
            remaining_agents = len([
                t for t in self.agent_trackers.values() 
                if t.status in [MigrationStatus.PENDING, MigrationStatus.IN_PROGRESS]
            ])
            
            if remaining_agents > 0:
                estimated_remaining_seconds = remaining_agents * self.migration_stats["average_migration_time"]
                self.migration_stats["estimated_completion_time"] = (
                    datetime.now() + timedelta(seconds=estimated_remaining_seconds)
                ).isoformat()
        
        # Update progress percentage
        total_agents = self.migration_stats["total_agents"]
        completed_agents = self.migration_stats["completed_agents"]
        
        if total_agents > 0:
            self.migration_stats["overall_progress_percent"] = (completed_agents / total_agents) * 100
    
    def _check_migration_alerts(self, agent_name: str, tracker: AgentMigrationTracker):
        """Check for migration alerts and thresholds"""
        alerts = []
        
        # Check migration timeout
        if tracker.start_time and tracker.end_time:
            migration_time_minutes = (tracker.end_time - tracker.start_time).total_seconds() / 60
            if migration_time_minutes > self.alert_thresholds["migration_timeout_minutes"]:
                alerts.append(f"⏰ {agent_name} migration took {migration_time_minutes:.1f} minutes (threshold: {self.alert_thresholds['migration_timeout_minutes']})")
        
        # Check performance degradation
        if tracker.performance_delta:
            for metric, delta in tracker.performance_delta.items():
                if "time" in metric and delta > self.alert_thresholds["performance_degradation_percent"]:
                    alerts.append(f"⚠️ {agent_name} {metric} degraded by {delta:.1f}% (threshold: {self.alert_thresholds['performance_degradation_percent']}%)")
        
        # Check overall failure rate
        total_processed = self.migration_stats["completed_agents"] + self.migration_stats["failed_agents"]
        if total_processed > 0:
            failure_rate = (self.migration_stats["failed_agents"] / total_processed) * 100
            if failure_rate > self.alert_thresholds["failure_rate_percent"]:
                alerts.append(f"🚨 High failure rate: {failure_rate:.1f}% (threshold: {self.alert_thresholds['failure_rate_percent']}%)")
        
        # Send alerts
        for alert in alerts:
            logger.warning(alert)
            self._send_alert(alert, agent_name)
    
    def _send_alert(self, alert_message: str, agent_name: str):
        """Send alert to observability system"""
        alert_data = {
            "alert_type": "migration_alert",
            "message": alert_message,
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat(),
            "phase": self.current_phase.value,
            "severity": "warning"
        }
        
        # Send to both hubs
        for endpoint in [self.centralhub_endpoint, self.edgehub_endpoint]:
            try:
                requests.post(
                    f"{endpoint}/alerts",
                    json=alert_data,
                    timeout=5
                )
            except Exception as e:
                logger.debug(f"Failed to send alert to {endpoint}: {e}")
    
    def _migration_monitoring_loop(self):
        """Background monitoring loop for real-time statistics"""
        logger.info("🔍 Started migration monitoring loop")
        
        while self.monitoring_active:
            try:
                # Update real-time statistics
                self._update_real_time_stats()
                
                # Check for batch timeouts
                self._check_batch_timeouts()
                
                # Send periodic status updates
                self._send_status_update()
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in migration monitoring loop: {e}")
                time.sleep(60)  # Wait longer if there's an error
        
        logger.info("🛑 Migration monitoring loop stopped")
    
    def _update_real_time_stats(self):
        """Update real-time migration statistics"""
        # Count agents by status
        status_counts = {}
        for status in MigrationStatus:
            status_counts[status.value] = len([
                t for t in self.agent_trackers.values() 
                if t.status == status
            ])
        
        # Update migration stats
        self.migration_stats.update({
            "status_breakdown": status_counts,
            "active_migrations": status_counts[MigrationStatus.IN_PROGRESS.value],
            "pending_migrations": status_counts[MigrationStatus.PENDING.value]
        })
    
    def _check_batch_timeouts(self):
        """Check for batch-level timeouts"""
        # This would check if any batch is taking too long
        # and generate appropriate alerts
    
    def _send_status_update(self):
        """Send periodic status update to observability system"""
        status_data = {
            "migration_phase": self.current_phase.value,
            "start_time": self.migration_start_time.isoformat() if self.migration_start_time else None,
            "stats": self.migration_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send status update as metric
        self.record_migration_metric(
            agent_name="system",
            metric_type="status_update",
            value=self.migration_stats["overall_progress_percent"],
            metadata=status_data
        )
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """Get comprehensive migration summary"""
        summary = {
            "migration_phase": self.current_phase.value,
            "start_time": self.migration_start_time.isoformat() if self.migration_start_time else None,
            "duration_hours": None,
            "statistics": self.migration_stats.copy(),
            "agent_details": {},
            "performance_summary": {},
            "alerts_summary": {}
        }
        
        # Calculate duration
        if self.migration_start_time:
            duration = datetime.now() - self.migration_start_time
            summary["duration_hours"] = duration.total_seconds() / 3600
        
        # Agent details
        for agent_name, tracker in self.agent_trackers.items():
            summary["agent_details"][agent_name] = {
                "status": tracker.status.value,
                "batch": tracker.batch_name,
                "start_time": tracker.start_time.isoformat() if tracker.start_time else None,
                "end_time": tracker.end_time.isoformat() if tracker.end_time else None,
                "performance_delta": tracker.performance_delta,
                "cross_machine_test_passed": tracker.cross_machine_test_passed,
                "rollback_performed": tracker.rollback_performed,
                "error_message": tracker.error_message
            }
        
        # Performance summary
        performance_deltas = [
            t.performance_delta for t in self.agent_trackers.values() 
            if t.performance_delta
        ]
        
        if performance_deltas:
            # Calculate average performance impact
            all_metrics = {}
            for delta in performance_deltas:
                for metric, value in delta.items():
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(value)
            
            summary["performance_summary"] = {
                metric: {
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
                for metric, values in all_metrics.items()
            }
        
        return summary
    
    def generate_migration_report(self) -> str:
        """Generate detailed migration report"""
        summary = self.get_migration_summary()
        
        report_lines = [
            "=" * 60,
            "PHASE 2 WEEK 2 MIGRATION REPORT",
            "=" * 60,
            f"Migration Phase: {summary['migration_phase']}",
            f"Start Time: {summary['start_time']}",
            f"Duration: {summary['duration_hours']:.2f} hours" if summary['duration_hours'] else "In Progress",
            "",
            "STATISTICS:",
            f"  Total Agents: {summary['statistics']['total_agents']}",
            f"  Completed: {summary['statistics']['completed_agents']}",
            f"  Failed: {summary['statistics']['failed_agents']}",
            f"  Rolled Back: {summary['statistics']['rolled_back_agents']}",
            f"  Progress: {summary['statistics']['overall_progress_percent']:.1f}%",
            f"  Average Migration Time: {summary['statistics']['average_migration_time']:.1f}s",
            "",
            "AGENT STATUS BREAKDOWN:"
        ]
        
        # Add agent details by batch
        batches = {}
        for agent_name, details in summary["agent_details"].items():
            batch = details["batch"]
            if batch not in batches:
                batches[batch] = []
            batches[batch].append((agent_name, details))
        
        for batch_name, agents in batches.items():
            report_lines.append(f"\n  {batch_name}:")
            for agent_name, details in agents:
                status_emoji = {
                    "completed": "✅",
                    "failed": "❌",
                    "in_progress": "🔄",
                    "pending": "⏳",
                    "rolled_back": "🔄"
                }.get(details["status"], "❓")
                
                report_lines.append(f"    {status_emoji} {agent_name}: {details['status']}")
                
                if details["error_message"]:
                    report_lines.append(f"        Error: {details['error_message']}")
        
        # Add performance summary
        if summary["performance_summary"]:
            report_lines.extend([
                "",
                "PERFORMANCE IMPACT:",
            ])
            
            for metric, stats in summary["performance_summary"].items():
                report_lines.append(f"  {metric}:")
                report_lines.append(f"    Average: {stats['average']:.2f}")
                report_lines.append(f"    Range: {stats['min']:.2f} to {stats['max']:.2f}")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def stop_migration_tracking(self):
        """Stop migration tracking and monitoring"""
        logger.info("🛑 Stopping migration tracking")
        
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=10)
        
        # Generate final report
        final_report = self.generate_migration_report()
        logger.info(f"\n{final_report}")
        
        # Save report to file
        try:
            report_file = f"{PathManager.get_project_root()}/logs/migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(final_report)
            logger.info(f"📄 Migration report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save migration report: {e}")

# Global migration observability instance
migration_observer = MigrationObservabilityHub()

def get_migration_observer() -> MigrationObservabilityHub:
    """Get the global migration observability instance"""
    return migration_observer 