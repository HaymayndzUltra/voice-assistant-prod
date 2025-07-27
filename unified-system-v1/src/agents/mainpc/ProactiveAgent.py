#!/usr/bin/env python3
"""
ProactiveAgent - Provides proactive assistance and suggestions
Enhanced with modern BaseAgent infrastructure and unified error handling
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import zmq

# Modern imports using BaseAgent infrastructure
from common.core.base_agent import BaseAgent
from common.utils.path_manager import PathManager
from common.utils.data_models import ErrorSeverity
from common.config_manager import get_service_ip, get_service_url

class ProactivityLevel(Enum):
    """Levels of proactive engagement"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ADAPTIVE = "adaptive"

class SuggestionType(Enum):
    """Types of proactive suggestions"""
    TASK_REMINDER = "task_reminder"
    OPTIMIZATION = "optimization"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    WORKFLOW_IMPROVEMENT = "workflow_improvement"
    CONTEXT_AWARE_HELP = "context_aware_help"
    PREVENTIVE_ACTION = "preventive_action"

@dataclass
class ProactiveSuggestion:
    """Proactive suggestion data structure"""
    suggestion_id: str
    suggestion_type: SuggestionType
    title: str
    description: str
    priority: int  # 1-5, 5 being highest
    context: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    user_feedback: Optional[str] = None

class ProactiveAgent(BaseAgent):
    """
    Modern ProactiveAgent using BaseAgent infrastructure
    Provides intelligent proactive assistance and contextual suggestions
    """
    
    def __init__(self, name="ProactiveAgent", port=5624):
        super().__init__(name, port)
        
        # Proactivity configuration
        self.proactivity_level = ProactivityLevel.ADAPTIVE
        self.suggestion_frequency = 300  # seconds
        self.max_active_suggestions = 10
        
        # Suggestion storage and management
        self.active_suggestions: Dict[str, ProactiveSuggestion] = {}
        self.suggestion_history: List[ProactiveSuggestion] = []
        self.user_preferences = {
            'preferred_suggestion_types': [
                SuggestionType.OPTIMIZATION,
                SuggestionType.WORKFLOW_IMPROVEMENT,
                SuggestionType.CONTEXT_AWARE_HELP
            ],
            'quiet_hours': {'start': '22:00', 'end': '08:00'},
            'max_suggestions_per_hour': 5,
            'feedback_learning_enabled': True
        }
        
        # Context monitoring
        self.context_patterns = {
            'work_hours': {'start': '09:00', 'end': '17:00'},
            'frequent_tasks': {},
            'error_patterns': {},
            'performance_metrics': {},
            'user_activity_patterns': {}
        }
        
        # ZMQ setup for communication
        self.context = zmq.Context()
        self.suggestion_publisher = self.context.socket(zmq.PUB)
        self.suggestion_publisher.bind(f"tcp://*:{port + 100}")  # Suggestion broadcast port
        
        # Background monitoring and suggestion generation
        self.monitoring_thread = None
        self.suggestion_thread = None
        self.running = False
        
        # Suggestion patterns and rules
        self.suggestion_rules = self._initialize_suggestion_rules()
        
        # Statistics
        self.statistics = {
            'suggestions_generated': 0,
            'suggestions_accepted': 0,
            'suggestions_dismissed': 0,
            'avg_suggestion_relevance': 0.0,
            'suggestion_type_performance': {stype.value: {'count': 0, 'acceptance_rate': 0.0} for stype in SuggestionType}
        }
    
    def _initialize_suggestion_rules(self) -> Dict[str, Any]:
        """Initialize suggestion generation rules"""
        return {
            'task_reminder': {
                'triggers': ['scheduled_task', 'recurring_task', 'deadline_approaching'],
                'conditions': ['time_based', 'context_based'],
                'priority_factors': ['urgency', 'importance', 'user_preference']
            },
            'optimization': {
                'triggers': ['repetitive_action', 'inefficient_workflow', 'resource_usage'],
                'conditions': ['pattern_detected', 'threshold_exceeded'],
                'priority_factors': ['potential_impact', 'ease_of_implementation']
            },
            'learning_opportunity': {
                'triggers': ['new_feature_available', 'skill_gap_detected', 'best_practice_deviation'],
                'conditions': ['user_readiness', 'relevance_score'],
                'priority_factors': ['learning_value', 'current_context']
            },
            'workflow_improvement': {
                'triggers': ['bottleneck_detected', 'alternative_approach', 'tool_suggestion'],
                'conditions': ['improvement_potential', 'compatibility'],
                'priority_factors': ['efficiency_gain', 'adoption_difficulty']
            },
            'context_aware_help': {
                'triggers': ['user_struggle', 'error_pattern', 'unfamiliar_context'],
                'conditions': ['help_needed', 'appropriate_timing'],
                'priority_factors': ['urgency', 'relevance']
            },
            'preventive_action': {
                'triggers': ['risk_detected', 'maintenance_due', 'resource_limit_approaching'],
                'conditions': ['prevention_possible', 'action_required'],
                'priority_factors': ['risk_level', 'prevention_cost']
            }
        }
    
    def generate_suggestion_id(self) -> str:
        """Generate unique suggestion ID"""
        import uuid
        return f"suggestion_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def analyze_context(self, context_data: Dict[str, Any]) -> List[str]:
        """Analyze context to identify suggestion opportunities"""
        opportunities = []
        
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Check for work hours context
            work_start = int(self.context_patterns['work_hours']['start'].split(':')[0])
            work_end = int(self.context_patterns['work_hours']['end'].split(':')[0])
            
            if work_start <= current_hour <= work_end:
                opportunities.append('work_context')
            
            # Check for repetitive patterns
            if context_data.get('recent_actions'):
                actions = context_data['recent_actions']
                if len(actions) >= 3 and len(set(actions)) == 1:
                    opportunities.append('repetitive_action')
            
            # Check for error patterns
            if context_data.get('recent_errors'):
                error_count = len(context_data['recent_errors'])
                if error_count >= 2:
                    opportunities.append('error_pattern')
            
            # Check for performance issues
            if context_data.get('performance_metrics'):
                perf = context_data['performance_metrics']
                if perf.get('response_time', 0) > 5000:  # 5 seconds
                    opportunities.append('performance_issue')
            
            # Check for learning opportunities
            if context_data.get('new_features_available'):
                opportunities.append('learning_opportunity')
            
            return opportunities
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Context analysis failed", {"error": str(e)})
            return []
    
    def generate_suggestion(self, opportunity: str, context: Dict[str, Any]) -> Optional[ProactiveSuggestion]:
        """Generate a specific suggestion based on opportunity and context"""
        try:
            suggestion_id = self.generate_suggestion_id()
            current_time = time.time()
            
            if opportunity == 'repetitive_action':
                return ProactiveSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type=SuggestionType.OPTIMIZATION,
                    title="Repetitive Task Detected",
                    description="I noticed you're performing the same action repeatedly. Would you like me to help automate this task?",
                    priority=4,
                    context=context,
                    actions=["create_automation", "learn_shortcuts", "batch_process"],
                    expires_at=current_time + 3600  # 1 hour
                )
            
            elif opportunity == 'error_pattern':
                return ProactiveSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type=SuggestionType.PREVENTIVE_ACTION,
                    title="Error Pattern Detected",
                    description="I've noticed recurring errors. Let me help you prevent these issues.",
                    priority=5,
                    context=context,
                    actions=["diagnose_issue", "implement_fix", "create_prevention"],
                    expires_at=current_time + 1800  # 30 minutes
                )
            
            elif opportunity == 'performance_issue':
                return ProactiveSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type=SuggestionType.OPTIMIZATION,
                    title="Performance Optimization",
                    description="System performance seems slower than usual. I can help optimize it.",
                    priority=3,
                    context=context,
                    actions=["analyze_performance", "optimize_resources", "clear_cache"],
                    expires_at=current_time + 7200  # 2 hours
                )
            
            elif opportunity == 'learning_opportunity':
                return ProactiveSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type=SuggestionType.LEARNING_OPPORTUNITY,
                    title="New Feature Available",
                    description="There are new features that might help improve your workflow.",
                    priority=2,
                    context=context,
                    actions=["explore_features", "schedule_tutorial", "gradual_adoption"],
                    expires_at=current_time + 86400  # 24 hours
                )
            
            elif opportunity == 'work_context':
                return ProactiveSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type=SuggestionType.WORKFLOW_IMPROVEMENT,
                    title="Work Day Optimization",
                    description="Would you like me to suggest ways to optimize your work day?",
                    priority=2,
                    context=context,
                    actions=["plan_tasks", "set_reminders", "organize_workspace"],
                    expires_at=current_time + 14400  # 4 hours
                )
            
            return None
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Suggestion generation failed", {"error": str(e), "opportunity": opportunity})
            return None
    
    def evaluate_suggestion_relevance(self, suggestion: ProactiveSuggestion, current_context: Dict[str, Any]) -> float:
        """Evaluate how relevant a suggestion is to the current context"""
        try:
            relevance_score = 0.0
            
            # Base priority contribution
            relevance_score += suggestion.priority * 0.2
            
            # Time-based relevance
            time_since_creation = time.time() - suggestion.created_at
            if time_since_creation < 300:  # Recent suggestions are more relevant
                relevance_score += 0.3
            elif time_since_creation > 3600:  # Old suggestions lose relevance
                relevance_score -= 0.2
            
            # Context match
            context_overlap = len(set(suggestion.context.keys()) & set(current_context.keys()))
            if context_overlap > 0:
                relevance_score += context_overlap * 0.1
            
            # User preference alignment
            if suggestion.suggestion_type in self.user_preferences.get('preferred_suggestion_types', []):
                relevance_score += 0.3
            
            # Historical performance of suggestion type
            type_performance = self.statistics['suggestion_type_performance'].get(suggestion.suggestion_type.value, {})
            acceptance_rate = type_performance.get('acceptance_rate', 0.0)
            relevance_score += acceptance_rate * 0.2
            
            return min(max(relevance_score, 0.0), 1.0)  # Clamp between 0 and 1
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Relevance evaluation failed", {"error": str(e)})
            return 0.5  # Default relevance
    
    def should_generate_suggestion(self, current_context: Dict[str, Any]) -> bool:
        """Determine if we should generate suggestions at this time"""
        try:
            current_time = datetime.now()
            current_hour_str = current_time.strftime('%H:%M')
            
            # Check quiet hours
            quiet_start = self.user_preferences['quiet_hours']['start']
            quiet_end = self.user_preferences['quiet_hours']['end']
            
            if quiet_start <= current_hour_str or current_hour_str <= quiet_end:
                return False
            
            # Check suggestion frequency limits
            recent_suggestions = [s for s in self.suggestion_history 
                                if s.created_at > time.time() - 3600]  # Last hour
            
            if len(recent_suggestions) >= self.user_preferences['max_suggestions_per_hour']:
                return False
            
            # Check if we have too many active suggestions
            if len(self.active_suggestions) >= self.max_active_suggestions:
                return False
            
            # Adaptive proactivity based on user engagement
            if self.proactivity_level == ProactivityLevel.ADAPTIVE:
                recent_acceptance_rate = self._calculate_recent_acceptance_rate()
                if recent_acceptance_rate < 0.2:  # Low acceptance rate
                    return False
            
            return True
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Suggestion timing check failed", {"error": str(e)})
            return False
    
    def _calculate_recent_acceptance_rate(self) -> float:
        """Calculate recent suggestion acceptance rate"""
        try:
            recent_suggestions = [s for s in self.suggestion_history 
                                if s.created_at > time.time() - 86400]  # Last 24 hours
            
            if not recent_suggestions:
                return 0.5  # Default rate
            
            accepted = sum(1 for s in recent_suggestions if s.user_feedback == 'accepted')
            return accepted / len(recent_suggestions)
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Acceptance rate calculation failed", {"error": str(e)})
            return 0.5
    
    def process_user_feedback(self, suggestion_id: str, feedback: str, feedback_data: Optional[Dict[str, Any]] = None):
        """Process user feedback on suggestions"""
        try:
            if suggestion_id in self.active_suggestions:
                suggestion = self.active_suggestions[suggestion_id]
                suggestion.user_feedback = feedback
                
                # Move to history
                self.suggestion_history.append(suggestion)
                del self.active_suggestions[suggestion_id]
                
                # Update statistics
                self.statistics['suggestions_generated'] += 1
                if feedback == 'accepted':
                    self.statistics['suggestions_accepted'] += 1
                elif feedback == 'dismissed':
                    self.statistics['suggestions_dismissed'] += 1
                
                # Update suggestion type performance
                type_key = suggestion.suggestion_type.value
                type_stats = self.statistics['suggestion_type_performance'][type_key]
                type_stats['count'] += 1
                
                if feedback == 'accepted':
                    current_rate = type_stats['acceptance_rate']
                    count = type_stats['count']
                    type_stats['acceptance_rate'] = ((current_rate * (count - 1)) + 1.0) / count
                else:
                    current_rate = type_stats['acceptance_rate']
                    count = type_stats['count']
                    type_stats['acceptance_rate'] = (current_rate * (count - 1)) / count
                
                # Publish feedback event
                self._publish_feedback_event(suggestion, feedback, feedback_data)
                
                self.logger.info(f"Processed feedback '{feedback}' for suggestion {suggestion_id}")
                
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Feedback processing failed", {"error": str(e), "suggestion_id": suggestion_id})
    
    def _publish_feedback_event(self, suggestion: ProactiveSuggestion, feedback: str, feedback_data: Optional[Dict[str, Any]]):
        """Publish user feedback event"""
        try:
            feedback_event = {
                'timestamp': time.time(),
                'suggestion_id': suggestion.suggestion_id,
                'suggestion_type': suggestion.suggestion_type.value,
                'feedback': feedback,
                'suggestion_priority': suggestion.priority,
                'feedback_data': feedback_data or {}
            }
            
            self.suggestion_publisher.send_string(f"SUGGESTION_FEEDBACK {json.dumps(feedback_event)}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Feedback event publishing failed", {"error": str(e)})
    
    def cleanup_expired_suggestions(self):
        """Remove expired suggestions"""
        try:
            current_time = time.time()
            expired_ids = []
            
            for suggestion_id, suggestion in self.active_suggestions.items():
                if suggestion.expires_at and current_time > suggestion.expires_at:
                    expired_ids.append(suggestion_id)
            
            for suggestion_id in expired_ids:
                expired_suggestion = self.active_suggestions.pop(suggestion_id)
                self.suggestion_history.append(expired_suggestion)
                self.logger.info(f"Expired suggestion {suggestion_id}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Suggestion cleanup failed", {"error": str(e)})
    
    def get_active_suggestions(self) -> List[Dict[str, Any]]:
        """Get all active suggestions"""
        try:
            suggestions = []
            for suggestion in self.active_suggestions.values():
                relevance = self.evaluate_suggestion_relevance(suggestion, {})
                suggestions.append({
                    'id': suggestion.suggestion_id,
                    'type': suggestion.suggestion_type.value,
                    'title': suggestion.title,
                    'description': suggestion.description,
                    'priority': suggestion.priority,
                    'relevance': relevance,
                    'actions': suggestion.actions,
                    'created_at': suggestion.created_at,
                    'expires_at': suggestion.expires_at
                })
            
            # Sort by relevance and priority
            suggestions.sort(key=lambda x: (x['relevance'], x['priority']), reverse=True)
            return suggestions
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Error getting active suggestions", {"error": str(e)})
            return []
    
    def process_context_update(self, context_data: Dict[str, Any]):
        """Process context update and generate suggestions if appropriate"""
        try:
            if not self.should_generate_suggestion(context_data):
                return
            
            # Analyze context for opportunities
            opportunities = self.analyze_context(context_data)
            
            for opportunity in opportunities:
                suggestion = self.generate_suggestion(opportunity, context_data)
                if suggestion:
                    self.active_suggestions[suggestion.suggestion_id] = suggestion
                    
                    # Publish new suggestion
                    suggestion_event = {
                        'timestamp': time.time(),
                        'suggestion_id': suggestion.suggestion_id,
                        'type': suggestion.suggestion_type.value,
                        'title': suggestion.title,
                        'description': suggestion.description,
                        'priority': suggestion.priority,
                        'actions': suggestion.actions
                    }
                    
                    self.suggestion_publisher.send_string(f"NEW_SUGGESTION {json.dumps(suggestion_event)}")
                    self.logger.info(f"Generated new suggestion: {suggestion.title}")
            
            # Cleanup expired suggestions
            self.cleanup_expired_suggestions()
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Context update processing failed", {"error": str(e)})
    
    async def start(self):
        """Start the ProactiveAgent service"""
        try:
            self.logger.info(f"Starting ProactiveAgent on port {self.port}")
            
            # Start background monitoring
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.logger.info("ProactiveAgent started successfully")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.report_error(ErrorSeverity.CRITICAL, "Failed to start ProactiveAgent", {"error": str(e)})
            raise
    
    def _monitoring_loop(self):
        """Background monitoring and suggestion generation loop"""
        while self.running:
            try:
                # Periodic suggestion cleanup
                self.cleanup_expired_suggestions()
                
                # Process any pending context updates
                # This would typically be triggered by external events
                
                # Log statistics periodically
                if self.statistics['suggestions_generated'] % 10 == 0 and self.statistics['suggestions_generated'] > 0:
                    self.logger.info(f"Proactive statistics: {self.statistics}")
                
                time.sleep(self.suggestion_frequency)
                
            except Exception as e:
                self.report_error(ErrorSeverity.WARNING, "Monitoring loop error", {"error": str(e)})
                time.sleep(30)
    
    def cleanup(self):
        """Modern cleanup using try...finally pattern"""
        self.logger.info("Starting ProactiveAgent cleanup...")
        cleanup_errors = []
        
        try:
            # Stop background monitoring
            self.running = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            # Save suggestion history if needed
            try:
                # Could save to file here if persistence is needed
                pass
            except Exception as e:
                cleanup_errors.append(f"History save error: {e}")
            
            # Close ZMQ resources
            try:
                if hasattr(self, 'suggestion_publisher'):
                    self.suggestion_publisher.close()
                if hasattr(self, 'context'):
                    self.context.term()
            except Exception as e:
                cleanup_errors.append(f"ZMQ cleanup error: {e}")
                
        finally:
            # Always call parent cleanup for BaseAgent resources
            try:
                super().cleanup()
                self.logger.info("✅ ProactiveAgent cleanup completed")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
        
        if cleanup_errors:
            self.logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors: {cleanup_errors}")

if __name__ == "__main__":
    import asyncio
    
    agent = ProactiveAgent()
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        agent.logger.info("ProactiveAgent interrupted by user")
    except Exception as e:
        agent.logger.error(f"ProactiveAgent error: {e}")
    finally:
        agent.cleanup()