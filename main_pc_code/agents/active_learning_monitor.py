#!/usr/bin/env python3
"""
ActiveLearningMonitor - Monitors and optimizes learning processes
Enhanced with modern BaseAgent infrastructure and unified error handling
"""

import asyncio
import json
import threading
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import zmq
import numpy as np

# Modern imports using BaseAgent infrastructure
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from common.utils.env_standardizer import get_env
from common.utils.log_setup import configure_logging
from main_pc_code.agents.error_publisher import ErrorPublisher

class LearningPhase(Enum):
    """Learning process phases"""
    INITIALIZATION = "initialization"
    ACTIVE_LEARNING = "active_learning"
    EVALUATION = "evaluation"
    OPTIMIZATION = "optimization"
    CONSOLIDATION = "consolidation"
    IDLE = "idle"

class MetricType(Enum):
    """Types of learning metrics"""
    ACCURACY = "accuracy"
    LOSS = "loss"
    LEARNING_RATE = "learning_rate"
    CONVERGENCE = "convergence"
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"

@dataclass
class LearningMetric:
    """Learning metric data structure"""
    metric_type: MetricType
    value: float
    timestamp: float
    phase: LearningPhase
    context: Dict[str, Any] = field(default_factory=dict)
    trend: Optional[str] = None  # 'improving', 'declining', 'stable'

@dataclass
class LearningSession:
    """Learning session tracking"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    phase: LearningPhase = LearningPhase.INITIALIZATION
    metrics: List[LearningMetric] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, completed, failed, paused

class ActiveLearningMonitor(BaseAgent):
    """
    Modern ActiveLearningMonitor using BaseAgent infrastructure
    Monitors learning processes and provides optimization recommendations
    """
    
    def __init__(self, name="ActiveLearningMonitor", port=5638):
        super().__init__(name, port)
        
        # Learning monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.metric_history_limit = 1000
        self.optimization_threshold = 0.95  # convergence threshold
        
        # Active monitoring state
        self.active_sessions: Dict[str, LearningSession] = {}
        self.metric_history: List[LearningMetric] = []
        self.learning_patterns = {}
        
        # Optimization parameters
        self.optimization_strategies = {
            'learning_rate_decay': {'enabled': True, 'factor': 0.95, 'patience': 10},
            'early_stopping': {'enabled': True, 'patience': 20, 'min_delta': 0.001},
            'dynamic_batching': {'enabled': True, 'min_batch': 16, 'max_batch': 128},
            'gradient_clipping': {'enabled': True, 'max_norm': 1.0},
            'adaptive_momentum': {'enabled': True, 'beta1_range': (0.9, 0.999)}
        }
        
        # Performance tracking
        self.performance_stats = {
            'total_sessions': 0,
            'successful_sessions': 0,
            'failed_sessions': 0,
            'avg_convergence_time': 0.0,
            'optimization_interventions': 0,
            'performance_improvements': 0
        }
        
        # ZMQ setup for communication
        self.context = zmq.Context()
        self.learning_publisher = self.context.socket(zmq.PUB)
        self.learning_publisher.bind(f"tcp://*:{port + 100}")  # Learning updates port
        
        # Background monitoring
        self.monitoring_thread = None
        self.analysis_thread = None
        self.running = False
        
        # Trend analysis window
        self.trend_window_size = 10
        self.trend_analysis_cache = {}
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        import uuid
        return f"learning_session_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def start_learning_session(self, parameters: Dict[str, Any]) -> str:
        """Start monitoring a new learning session"""
        try:
            session_id = self.generate_session_id()
            
            session = LearningSession(
                session_id=session_id,
                start_time=time.time(),
                parameters=parameters,
                phase=LearningPhase.INITIALIZATION
            )
            
            self.active_sessions[session_id] = session
            self.performance_stats['total_sessions'] += 1
            
            # Publish session start event
            start_event = {
                'timestamp': time.time(),
                'event_type': 'session_start',
                'session_id': session_id,
                'parameters': parameters
            }
            
            self.learning_publisher.send_string(f"LEARNING_SESSION_START {json.dumps(start_event)}")
            
            self.logger.info(f"Started learning session {session_id}")
            return session_id
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Failed to start learning session", {"error": str(e), "parameters": parameters})
            return ""
    
    def add_metric(self, session_id: str, metric_type: MetricType, value: float, context: Optional[Dict[str, Any]] = None) -> bool:
        """Add a learning metric to a session"""
        try:
            if session_id not in self.active_sessions:
                self.report_error(ErrorSeverity.WARNING, "Session not found for metric", {"session_id": session_id})
                return False
            
            session = self.active_sessions[session_id]
            
            # Create metric
            metric = LearningMetric(
                metric_type=metric_type,
                value=value,
                timestamp=time.time(),
                phase=session.phase,
                context=context or {}
            )
            
            # Calculate trend
            metric.trend = self._calculate_metric_trend(session_id, metric_type, value)
            
            # Add to session and global history
            session.metrics.append(metric)
            self.metric_history.append(metric)
            
            # Limit history size
            if len(self.metric_history) > self.metric_history_limit:
                self.metric_history = self.metric_history[-self.metric_history_limit:]
            
            # Analyze for optimization opportunities
            self._analyze_learning_progress(session_id, metric)
            
            # Publish metric event
            metric_event = {
                'timestamp': time.time(),
                'event_type': 'metric_update',
                'session_id': session_id,
                'metric_type': metric_type.value,
                'value': value,
                'trend': metric.trend,
                'phase': session.phase.value
            }
            
            self.learning_publisher.send_string(f"LEARNING_METRIC {json.dumps(metric_event)}")
            
            return True
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Failed to add metric", {"error": str(e), "session_id": session_id})
            return False
    
    def _calculate_metric_trend(self, session_id: str, metric_type: MetricType, current_value: float) -> str:
        """Calculate trend for a metric"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return 'unknown'
            
            # Get recent values of this metric type
            recent_metrics = [m for m in session.metrics if m.metric_type == metric_type][-self.trend_window_size:]
            
            if len(recent_metrics) < 3:
                return 'insufficient_data'
            
            # Calculate trend using linear regression
            values = [m.value for m in recent_metrics] + [current_value]
            x = np.arange(len(values))
            y = np.array(values)
            
            # Simple linear regression
            slope = np.polyfit(x, y, 1)[0]
            
            # Determine trend based on slope and metric type
            threshold = 0.001
            
            if metric_type in [MetricType.ACCURACY, MetricType.PERFORMANCE, MetricType.EFFICIENCY]:
                # For these metrics, positive slope is good
                if slope > threshold:
                    return 'improving'
                elif slope < -threshold:
                    return 'declining'
                else:
                    return 'stable'
            else:
                # For loss and similar metrics, negative slope is good
                if slope < -threshold:
                    return 'improving'
                elif slope > threshold:
                    return 'declining'
                else:
                    return 'stable'
                    
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Trend calculation failed", {"error": str(e)})
            return 'unknown'
    
    def _analyze_learning_progress(self, session_id: str, metric: LearningMetric):
        """Analyze learning progress and suggest optimizations"""
        try:
            session = self.active_sessions[session_id]
            
            # Check for convergence
            if metric.metric_type == MetricType.ACCURACY and metric.value >= self.optimization_threshold:
                self._handle_convergence(session_id)
            
            # Check for stagnation
            elif metric.trend == 'stable' and len(session.metrics) > 20:
                self._handle_stagnation(session_id, metric)
            
            # Check for declining performance
            elif metric.trend == 'declining':
                self._handle_performance_decline(session_id, metric)
            
            # Check for phase transitions
            self._check_phase_transition(session_id, metric)
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Learning progress analysis failed", {"error": str(e)})
    
    def _handle_convergence(self, session_id: str):
        """Handle learning convergence"""
        try:
            session = self.active_sessions[session_id]
            session.phase = LearningPhase.CONSOLIDATION
            
            convergence_event = {
                'timestamp': time.time(),
                'event_type': 'convergence_detected',
                'session_id': session_id,
                'recommendation': 'prepare_for_consolidation'
            }
            
            self.learning_publisher.send_string(f"LEARNING_CONVERGENCE {json.dumps(convergence_event)}")
            self.logger.info(f"Convergence detected for session {session_id}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Convergence handling failed", {"error": str(e)})
    
    def _handle_stagnation(self, session_id: str, metric: LearningMetric):
        """Handle learning stagnation"""
        try:
            recommendations = []
            
            # Suggest learning rate adjustment
            if self.optimization_strategies['learning_rate_decay']['enabled']:
                recommendations.append({
                    'type': 'learning_rate_decay',
                    'factor': self.optimization_strategies['learning_rate_decay']['factor']
                })
            
            # Suggest dynamic batching
            if self.optimization_strategies['dynamic_batching']['enabled']:
                recommendations.append({
                    'type': 'increase_batch_size',
                    'target_batch_size': min(
                        session.parameters.get('batch_size', 32) * 2,
                        self.optimization_strategies['dynamic_batching']['max_batch']
                    )
                })
            
            stagnation_event = {
                'timestamp': time.time(),
                'event_type': 'stagnation_detected',
                'session_id': session_id,
                'metric_type': metric.metric_type.value,
                'recommendations': recommendations
            }
            
            self.learning_publisher.send_string(f"LEARNING_STAGNATION {json.dumps(stagnation_event)}")
            self.performance_stats['optimization_interventions'] += 1
            
            self.logger.warning(f"Learning stagnation detected for session {session_id}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Stagnation handling failed", {"error": str(e)})
    
    def _handle_performance_decline(self, session_id: str, metric: LearningMetric):
        """Handle performance decline"""
        try:
            recommendations = []
            
            # Suggest gradient clipping
            if self.optimization_strategies['gradient_clipping']['enabled']:
                recommendations.append({
                    'type': 'gradient_clipping',
                    'max_norm': self.optimization_strategies['gradient_clipping']['max_norm']
                })
            
            # Suggest learning rate reduction
            recommendations.append({
                'type': 'reduce_learning_rate',
                'factor': 0.5
            })
            
            decline_event = {
                'timestamp': time.time(),
                'event_type': 'performance_decline',
                'session_id': session_id,
                'metric_type': metric.metric_type.value,
                'current_value': metric.value,
                'recommendations': recommendations
            }
            
            self.learning_publisher.send_string(f"LEARNING_DECLINE {json.dumps(decline_event)}")
            self.performance_stats['optimization_interventions'] += 1
            
            self.logger.warning(f"Performance decline detected for session {session_id}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Performance decline handling failed", {"error": str(e)})
    
    def _check_phase_transition(self, session_id: str, metric: LearningMetric):
        """Check if learning phase should transition"""
        try:
            session = self.active_sessions[session_id]
            current_phase = session.phase
            
            # Transition logic based on metrics and time
            session_duration = time.time() - session.start_time
            
            if current_phase == LearningPhase.INITIALIZATION and session_duration > 60:
                session.phase = LearningPhase.ACTIVE_LEARNING
                self._publish_phase_transition(session_id, current_phase, session.phase)
                
            elif current_phase == LearningPhase.ACTIVE_LEARNING:
                # Check for evaluation phase
                if metric.metric_type == MetricType.ACCURACY and metric.value > 0.8:
                    session.phase = LearningPhase.EVALUATION
                    self._publish_phase_transition(session_id, current_phase, session.phase)
                    
            elif current_phase == LearningPhase.EVALUATION:
                # Check for optimization phase
                if metric.trend == 'stable':
                    session.phase = LearningPhase.OPTIMIZATION
                    self._publish_phase_transition(session_id, current_phase, session.phase)
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Phase transition check failed", {"error": str(e)})
    
    def _publish_phase_transition(self, session_id: str, old_phase: LearningPhase, new_phase: LearningPhase):
        """Publish phase transition event"""
        try:
            transition_event = {
                'timestamp': time.time(),
                'event_type': 'phase_transition',
                'session_id': session_id,
                'old_phase': old_phase.value,
                'new_phase': new_phase.value
            }
            
            self.learning_publisher.send_string(f"LEARNING_PHASE_TRANSITION {json.dumps(transition_event)}")
            self.logger.info(f"Session {session_id} transitioned from {old_phase.value} to {new_phase.value}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Phase transition publishing failed", {"error": str(e)})
    
    def end_learning_session(self, session_id: str, status: str = "completed") -> Dict[str, Any]:
        """End a learning session"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Session not found'}
            
            session = self.active_sessions[session_id]
            session.end_time = time.time()
            session.status = status
            
            # Calculate session summary
            session_duration = session.end_time - session.start_time
            
            # Update performance statistics
            if status == "completed":
                self.performance_stats['successful_sessions'] += 1
            else:
                self.performance_stats['failed_sessions'] += 1
            
            # Update average convergence time
            total_sessions = self.performance_stats['successful_sessions'] + self.performance_stats['failed_sessions']
            if total_sessions > 0:
                current_avg = self.performance_stats['avg_convergence_time']
                self.performance_stats['avg_convergence_time'] = ((current_avg * (total_sessions - 1)) + session_duration) / total_sessions
            
            # Create session summary
            summary = {
                'session_id': session_id,
                'duration': session_duration,
                'status': status,
                'total_metrics': len(session.metrics),
                'final_phase': session.phase.value,
                'performance_summary': self._calculate_session_performance(session)
            }
            
            # Publish session end event
            end_event = {
                'timestamp': time.time(),
                'event_type': 'session_end',
                'session_id': session_id,
                'status': status,
                'summary': summary
            }
            
            self.learning_publisher.send_string(f"LEARNING_SESSION_END {json.dumps(end_event)}")
            
            # Move to completed sessions (could implement persistence here)
            del self.active_sessions[session_id]
            
            self.logger.info(f"Ended learning session {session_id} with status {status}")
            
            return {'status': 'success', 'summary': summary}
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Failed to end learning session", {"error": str(e), "session_id": session_id})
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_session_performance(self, session: LearningSession) -> Dict[str, Any]:
        """Calculate performance summary for a session"""
        try:
            if not session.metrics:
                return {'message': 'No metrics available'}
            
            # Group metrics by type
            metrics_by_type = {}
            for metric in session.metrics:
                metric_type = metric.metric_type.value
                if metric_type not in metrics_by_type:
                    metrics_by_type[metric_type] = []
                metrics_by_type[metric_type].append(metric.value)
            
            # Calculate summary statistics
            performance = {}
            for metric_type, values in metrics_by_type.items():
                performance[metric_type] = {
                    'initial': values[0] if values else 0,
                    'final': values[-1] if values else 0,
                    'best': max(values) if metric_type in ['accuracy', 'performance'] else min(values),
                    'average': sum(values) / len(values) if values else 0,
                    'improvement': values[-1] - values[0] if len(values) >= 2 else 0
                }
            
            return performance
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Performance calculation failed", {"error": str(e)})
            return {'error': str(e)}
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a learning session"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Session not found'}
            
            session = self.active_sessions[session_id]
            current_time = time.time()
            
            return {
                'status': 'success',
                'session_id': session_id,
                'phase': session.phase.value,
                'duration': current_time - session.start_time,
                'metric_count': len(session.metrics),
                'recent_trends': self._get_recent_trends(session),
                'performance_indicators': self._get_performance_indicators(session)
            }
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Failed to get session status", {"error": str(e)})
            return {'status': 'error', 'message': str(e)}
    
    def _get_recent_trends(self, session: LearningSession) -> Dict[str, str]:
        """Get recent trends for a session"""
        try:
            trends = {}
            recent_metrics = session.metrics[-10:]  # Last 10 metrics
            
            for metric in recent_metrics:
                metric_type = metric.metric_type.value
                if metric_type not in trends or metric.timestamp > session.metrics[-1].timestamp:
                    trends[metric_type] = metric.trend
            
            return trends
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_performance_indicators(self, session: LearningSession) -> Dict[str, Any]:
        """Get performance indicators for a session"""
        try:
            if not session.metrics:
                return {}
            
            # Calculate convergence rate
            accuracy_metrics = [m for m in session.metrics if m.metric_type == MetricType.ACCURACY]
            convergence_rate = 0.0
            
            if len(accuracy_metrics) >= 2:
                initial_acc = accuracy_metrics[0].value
                current_acc = accuracy_metrics[-1].value
                time_diff = accuracy_metrics[-1].timestamp - accuracy_metrics[0].timestamp
                convergence_rate = (current_acc - initial_acc) / max(time_diff, 1.0)
            
            return {
                'convergence_rate': convergence_rate,
                'session_health': 'good' if convergence_rate > 0 else 'concerning',
                'optimization_interventions': sum(1 for m in session.metrics if m.trend == 'declining'),
                'stability_score': sum(1 for m in session.metrics if m.trend == 'stable') / max(len(session.metrics), 1)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global monitoring statistics"""
        return {
            'timestamp': time.time(),
            'active_sessions': len(self.active_sessions),
            'performance_stats': self.performance_stats.copy(),
            'optimization_strategies': self.optimization_strategies.copy(),
            'metric_history_size': len(self.metric_history),
            'monitoring_config': {
                'interval': self.monitoring_interval,
                'history_limit': self.metric_history_limit,
                'optimization_threshold': self.optimization_threshold
            }
        }
    
    async def start(self):
        """Start the ActiveLearningMonitor service"""
        try:
            self.logger.info(f"Starting ActiveLearningMonitor on port {self.port}")
            
            # Start background monitoring
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
            self.analysis_thread.start()
            
            self.logger.info("ActiveLearningMonitor started successfully")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.report_error(ErrorSeverity.CRITICAL, "Failed to start ActiveLearningMonitor", {"error": str(e)})
            raise
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Monitor active sessions for timeouts or issues
                current_time = time.time()
                
                for session_id, session in list(self.active_sessions.items()):
                    session_duration = current_time - session.start_time
                    
                    # Check for session timeout (24 hours)
                    if session_duration > 86400:  # 24 hours
                        self.logger.warning(f"Session {session_id} has been running for over 24 hours")
                        self.end_learning_session(session_id, "timeout")
                
                # Log periodic statistics
                if len(self.active_sessions) > 0:
                    self.logger.info(f"Monitoring {len(self.active_sessions)} active learning sessions")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.report_error(ErrorSeverity.WARNING, "Monitoring loop error", {"error": str(e)})
                time.sleep(60)
    
    def _analysis_loop(self):
        """Background analysis loop"""
        while self.running:
            try:
                # Perform periodic analysis of learning patterns
                if len(self.metric_history) > 100:
                    self._analyze_global_patterns()
                
                # Clean up old metrics
                if len(self.metric_history) > self.metric_history_limit:
                    self.metric_history = self.metric_history[-self.metric_history_limit:]
                
                time.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                self.report_error(ErrorSeverity.WARNING, "Analysis loop error", {"error": str(e)})
                time.sleep(600)
    
    def _analyze_global_patterns(self):
        """Analyze global learning patterns"""
        try:
            # This could implement more sophisticated pattern analysis
            # For now, just log basic statistics
            recent_metrics = [m for m in self.metric_history if m.timestamp > time.time() - 3600]  # Last hour
            
            if recent_metrics:
                improving_count = sum(1 for m in recent_metrics if m.trend == 'improving')
                total_count = len(recent_metrics)
                improvement_rate = improving_count / total_count
                
                if improvement_rate < 0.3:  # Less than 30% improving
                    self.logger.warning(f"Low improvement rate detected: {improvement_rate:.2f}")
                
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Global pattern analysis failed", {"error": str(e)})
    
    def cleanup(self):
        """Modern cleanup using try...finally pattern"""
        self.logger.info("Starting ActiveLearningMonitor cleanup...")
        cleanup_errors = []
        
        try:
            # Stop background threads
            self.running = False
            
            for thread_name, thread in [
                ("monitoring_thread", self.monitoring_thread),
                ("analysis_thread", self.analysis_thread)
            ]:
                if thread and thread.is_alive():
                    thread.join(timeout=5)
                    if thread.is_alive():
                        cleanup_errors.append(f"{thread_name} didn't stop gracefully")
            
            # End all active sessions
            try:
                for session_id in list(self.active_sessions.keys()):
                    self.end_learning_session(session_id, "shutdown")
            except Exception as e:
                cleanup_errors.append(f"Session cleanup error: {e}")
            
            # Close ZMQ resources
            try:
                if hasattr(self, 'learning_publisher'):
                    self.learning_publisher.close()
                if hasattr(self, 'context'):
                    self.context.term()
            except Exception as e:
                cleanup_errors.append(f"ZMQ cleanup error: {e}")
                
        finally:
            # Always call parent cleanup for BaseAgent resources
            try:
                super().cleanup()
                self.logger.info("✅ ActiveLearningMonitor cleanup completed")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
        
        if cleanup_errors:
            self.logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors: {cleanup_errors}")

if __name__ == "__main__":
    import asyncio
    
    agent = ActiveLearningMonitor()
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        agent.logger.info("ActiveLearningMonitor interrupted by user")
    except Exception as e:
        agent.logger.error(f"ActiveLearningMonitor error: {e}")
    finally:
        agent.cleanup()
