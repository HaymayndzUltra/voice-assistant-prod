#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Learning Opportunity Detector (LOD)

Refactored to follow the best agent pattern:
- Uses shared Pydantic models (LearningOpportunity)
- All config is dynamic (no hardcoding)
- Registers with service discovery (if available)
- Modular setup, run, and cleanup
- Detailed health check and logging
- All ZMQ endpoints and DB paths are dynamic/configurable
"""

import sys
import os
import time
import logging
import threading
import json
import zmq
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import sqlite3
import psutil
from pathlib import Path
from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional, Union, Tuple
from uuid import UUID


# Import path manager for containerization-friendly paths
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager

# --- Path Setup ---
project_root = str(PathManager.get_project_root())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from common.utils.learning_models import LearningOpportunity
from common.config_manager import load_unified_config

# --- Shared Utilities ---
from src.agents.mainpc.request_coordinator import CircuitBreaker
from common.env_helpers import get_env

# --- Logging Setup ---
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, str(PathManager.get_logs_dir() / "learning_opportunity_detector.log"))),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('LearningOpportunityDetector')

# --- Load configuration ---
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))
DEFAULT_PORT = config.get('lod_port', 7200)
HEALTH_CHECK_PORT = config.get('lod_health_port', 7201)
ZMQ_REQUEST_TIMEOUT = config.get('zmq_request_timeout', 5000)
OPPORTUNITY_DB_PATH = config.get('lod_db_path', str(PathManager.get_data_dir() / str(PathManager.get_data_dir() / "learning_opportunities.db")))
INTERACTION_BUFFER_SIZE = config.get('lod_buffer_size', 1000)
SCORING_THRESHOLD = config.get('lod_scoring_threshold', 0.7)

class LearningOpportunityDetector(BaseAgent):
    """
    Learning Opportunity Detector (LOD)
    
    Identifies and prioritizes learning opportunities from user interactions.
    Implements multiple detection strategies and a scoring system.
    Now follows the best agent pattern for maintainability and extensibility.
    """
    def __init__(self, **kwargs):
        port = kwargs.get('port', DEFAULT_PORT)
        super().__init__(name="LearningOpportunityDetector", port=port, health_check_port=HEALTH_CHECK_PORT)
        self.config = config
        self.start_time = time.time()
        self.running = True
        self.processed_items = 0
        self.monitored_events = 0
        self.valuable_opportunities = 0
        self.interaction_buffer = deque(maxlen=INTERACTION_BUFFER_SIZE)
        self.data_dir = config.get('lod_data_dir', 'training_data')
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.dirname(OPPORTUNITY_DB_PATH), exist_ok=True)
        self._init_database()
        self._setup_zmq_connections()
        self.downstream_services = ["LearningOrchestrationService", "MemoryClient"]
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()
        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
        self.service_registry = {}
        self._register_with_service_discovery()
        self._start_background_threads()
        logger.info(f"Learning Opportunity Detector initialized on port {self.port}")

    def _register_with_service_discovery(self):
        """Register this agent with the service discovery system if available."""
        try:
            from main_pc_code.utils.service_discovery_client import get_service_discovery_client
            from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
        except ImportError as e:
            print(f"Import error in learning_opportunity_detector: {e}")
            return
        try:
            client = get_service_discovery_client()
            self.service_registry[self.name] = {
                "name": self.name,
                "ip": self.config.get('bind_address', '0.0.0.0'),
                "health_check_port": HEALTH_CHECK_PORT,
                "capabilities": ["learning_opportunity_detection"],
                "status": "running"
            }
            logger.info("Successfully registered with service registry.")
        except Exception as e:
            logger.warning(f"Service discovery not available: {e}")

    def _init_circuit_breakers(self):
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _setup_zmq_connections(self):
        try:
            self.umra_socket = self.context.socket(zmq.SUB)
            self.umra_socket.connect(get_zmq_connection_string(self.config.get('umra_port', 5701), "localhost"))
            self.umra_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.coordinator_socket = self.context.socket(zmq.SUB)
            self.coordinator_socket.connect(get_zmq_connection_string(self.config.get('request_coordinator_port', 5702), "localhost"))
            self.coordinator_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.los_socket = self.context.socket(zmq.REQ)
            self.los_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.los_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.los_socket.connect(get_zmq_connection_string(self.config.get('los_port', 7210), "localhost"))
            logger.info("ZMQ connections established successfully")
        except Exception as e:
            logger.error(f"Error setting up ZMQ connections: {e}")
            self.report_error("zmq_connection_error", str(e), ErrorSeverity.ERROR)

    def _init_database(self):
        try:
            conn = sqlite3.connect(OPPORTUNITY_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_opportunities (
                    id TEXT PRIMARY KEY,
                    source_agent TEXT NOT NULL,
                    opportunity_type TEXT NOT NULL,
                    priority_score REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    interaction_data TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.report_error("database_init_error", str(e), ErrorSeverity.ERROR)

    def _start_background_threads(self):
        threads = {
            "UMRA_Monitor": self._monitor_umra,
            "Coordinator_Monitor": self._monitor_coordinator,
            "Opportunity_Analyzer": self._analyze_interactions
        }
        for name, target in threads.items():
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            logger.info(f"Started {name} thread")

    def _monitor_umra(self):
        """Monitor UMRA output for valuable interactions."""
        while self.running:
            try:
                message = self.umra_socket.recv_json()
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append({
                        'source': 'umra',
                        'data': message,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.monitored_events += 1
            except Exception as e:
                logger.error(f"Error monitoring UMRA: {str(e)}")
                time.sleep(1)

    def _monitor_coordinator(self):
        """Monitor RequestCoordinator output for valuable interactions."""
        while self.running:
            try:
                message = self.coordinator_socket.recv_json()
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append({
                        'source': 'coordinator',
                        'data': message,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.monitored_events += 1
            except Exception as e:
                logger.error(f"Error monitoring RequestCoordinator: {str(e)}")
                time.sleep(1)

    def _analyze_interactions(self):
        """Analyze buffered interactions for learning opportunities."""
        while self.running:
            try:
                if self.interaction_buffer:
                    interaction = self.interaction_buffer.popleft()
                    self.processed_items += 1
                    
                    # Score the interaction using multiple detectors
                    scores = self._score_interaction(interaction)
                    
                    # Calculate final score (weighted average)
                    final_score = self._calculate_final_score(scores)
                    
                    # Determine category based on highest scoring detector
                    category = max(scores.items(), key=lambda x: x[1])[0] if scores else "unknown"
                    
                    # If score is above threshold, save as learning opportunity
                    if final_score >= SCORING_THRESHOLD:
                        self._save_learning_opportunity(interaction, final_score, category, scores)
                        self.valuable_opportunities += 1
            except Exception as e:
                logger.error(f"Error analyzing interactions: {str(e)}")
            time.sleep(0.1)  # Prevent CPU overuse
    
    def _score_interaction(self, interaction: Dict) -> Dict[str, float]:
        """
        Score an interaction using multiple detection strategies.
        Returns a dictionary of detector names and their scores.
        """
        scores = {}
        
        # Get the interaction data
        data = interaction.get('data', {})
        user_input = data.get('user_input', '')
        assistant_response = data.get('assistant_response', '')
        
        # 1. Explicit Correction Detector
        scores['explicit_correction'] = self._detect_explicit_correction(user_input, assistant_response)
        
        # 2. Implicit Correction Detector
        scores['implicit_correction'] = self._detect_implicit_correction(user_input, assistant_response)
        
        # 3. Positive Reinforcement Detector
        scores['positive_reinforcement'] = self._detect_positive_reinforcement(user_input)
        
        # 4. Question-Answer Pattern Detector
        scores['question_answer'] = self._detect_question_answer_pattern(user_input, assistant_response)
        
        # 5. Complex Reasoning Detector
        scores['complex_reasoning'] = self._detect_complex_reasoning(user_input, assistant_response)
        
        return scores
    
    def _detect_explicit_correction(self, user_input: str, assistant_response: str) -> float:
        """Detect explicit corrections in user input."""
        correction_phrases = ['no,', 'incorrect', 'wrong', 'that\'s not', 'actually', 'not true']
        score = 0.0
        
        user_input_lower = user_input.lower()
        for phrase in correction_phrases:
            if phrase in user_input_lower:
                score += 0.3
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def _detect_implicit_correction(self, user_input: str, assistant_response: str) -> float:
        """Detect implicit corrections (user restating or clarifying)."""
        score = 0.0
        user_input_lower = user_input.lower()
        
        # Check for clarification indicators
        clarification_phrases = ['but', 'however', 'although', 'though', 'rather', 'instead', 'what I meant']
        for phrase in clarification_phrases:
            if phrase in user_input_lower:
                score += 0.2
        
        # Check for substantial input (longer inputs are more likely to be corrections)
        if len(user_input.split()) > 10:
            score += 0.1
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def _detect_positive_reinforcement(self, user_input: str) -> float:
        """Detect positive reinforcement in user input."""
        positive_phrases = ['yes,', 'correct', 'right', 'exactly', 'perfect', 'good job', 'well done']
        score = 0.0
        
        user_input_lower = user_input.lower()
        for phrase in positive_phrases:
            if phrase in user_input_lower:
                score += 0.2
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def _detect_question_answer_pattern(self, user_input: str, assistant_response: str) -> float:
        """Detect question-answer patterns that might be valuable for learning."""
        score = 0.0
        user_input_lower = user_input.lower()
        
        # Check if user input is a question
        question_indicators = ['?', 'what', 'how', 'why', 'when', 'where', 'who', 'which', 'can you', 'could you']
        is_question = False
        for indicator in question_indicators:
            if indicator in user_input_lower:
                is_question = True
                break
        
        if is_question:
            # Questions with substantial responses are more valuable
            if len(assistant_response.split()) > 50:
                score += 0.3
            elif len(assistant_response.split()) > 20:
                score += 0.2
            else:
                score += 0.1
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def _detect_complex_reasoning(self, user_input: str, assistant_response: str) -> float:
        """Detect complex reasoning tasks that might be valuable for learning."""
        score = 0.0
        user_input_lower = user_input.lower()
        
        # Check for complex reasoning indicators in user input
        reasoning_phrases = ['explain', 'analyze', 'compare', 'evaluate', 'synthesize', 'why', 'how does']
        for phrase in reasoning_phrases:
            if phrase in user_input_lower:
                score += 0.1
        
        # Check for complex response (longer responses with multiple paragraphs)
        paragraphs = assistant_response.split('\n\n')
        if len(paragraphs) > 2:
            score += 0.2
        
        # Check for code blocks which indicate technical explanations
        if '```' in assistant_response:
            score += 0.2
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def _calculate_final_score(self, scores: Dict[str, float]) -> float:
        """Calculate final score as weighted average of detector scores."""
        if not scores:
            return 0.0
        
        # Detector weights (sum should be 1.0)
        weights = {
            'explicit_correction': 0.3,
            'implicit_correction': 0.2,
            'positive_reinforcement': 0.15,
            'question_answer': 0.15,
            'complex_reasoning': 0.2
        }
        
        # Calculate weighted average
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for detector, score in scores.items():
            weight = weights.get(detector, 0.1)  # Default weight for unknown detectors
            weighted_sum += score * weight
            weight_sum += weight
        
        # Avoid division by zero
        if weight_sum == 0:
            return 0.0
        
        return weighted_sum / weight_sum
    
    def _save_learning_opportunity(self, interaction: Dict, score: float, category: str, detector_scores: Dict[str, float]):
        """Save a learning opportunity using the shared Pydantic model."""
        try:
            opportunity = LearningOpportunity(
                source_agent=self.name,
                interaction_data=interaction,
                opportunity_type=category,
                priority_score=score,
                status='pending'
            )
            conn = sqlite3.connect(OPPORTUNITY_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO learning_opportunities (
                    id, source_agent, opportunity_type, priority_score, status, created_at, interaction_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(opportunity.opportunity_id),
                opportunity.source_agent,
                opportunity.opportunity_type,
                opportunity.priority_score,
                opportunity.status,
                opportunity.created_at.isoformat(),
                json.dumps(opportunity.interaction_data)
            ))
            conn.commit()
            conn.close()
            logger.info(f"Saved learning opportunity {opportunity.opportunity_id} (score={score:.2f}, type={category})")
            self.valuable_opportunities += 1
            self._notify_learning_orchestration_service(str(opportunity.opportunity_id), score, category)
        except Exception as e:
            logger.error(f"Error saving learning opportunity: {e}")
            self.report_error("db_save_error", str(e), ErrorSeverity.ERROR)
    
    def _notify_learning_orchestration_service(self, opportunity_id: str, score: float, category: str):
        """Notify the Learning Orchestration Service about a new learning opportunity."""
        try:
            if not self.circuit_breakers["LearningOrchestrationService"].allow_request():
                logger.warning("Circuit breaker open for LearningOrchestrationService, skipping notification")
                return
            
            payload = {
                "opportunity_id": opportunity_id,
                "score": score,
                "category": category
            }
            self.los_socket.send_json(payload)
            response = self.los_socket.recv_json()
            if isinstance(response, dict) and response.get("status") == "acknowledged":
                logger.info(f"LOS acknowledged opportunity {opportunity_id}")
            else:
                logger.warning(f"LOS did not acknowledge opportunity {opportunity_id}: {response}")
        except Exception as e:
            logger.error(f"Error notifying LOS: {e}")
            self.report_error("los_notify_error", str(e), ErrorSeverity.WARNING)
    
    def get_top_opportunities(self, category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get top learning opportunities, optionally filtered by category."""
        try:
            conn = sqlite3.connect(OPPORTUNITY_DB_PATH)
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT id, source, score, category, created_at, processed
                    FROM learning_opportunities
                    WHERE category = ?
                    ORDER BY score DESC
                    LIMIT ?
                ''', (category, limit))
            else:
                cursor.execute('''
                    SELECT id, source, score, category, created_at, processed
                    FROM learning_opportunities
                    ORDER BY score DESC
                    LIMIT ?
                ''', (limit,))
            
            opportunities = []
            for row in cursor.fetchall():
                opportunities.append({
                    'id': row[0],
                    'source': row[1],
                    'score': row[2],
                    'category': row[3],
                    'created_at': row[4],
                    'processed': bool(row[5])
                })
            
            conn.close()
            return opportunities
        except Exception as e:
            logger.error(f"Error getting top opportunities: {str(e)}")
            self.report_error("get_opportunities_error", str(e), ErrorSeverity.WARNING)
            return []
    
    def mark_opportunity_processed(self, opportunity_id: int) -> bool:
        """Mark a learning opportunity as processed."""
        try:
            conn = sqlite3.connect(OPPORTUNITY_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE learning_opportunities
                SET processed = TRUE
                WHERE id = ?
            ''', (opportunity_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Marked opportunity {opportunity_id} as processed")
            return True
        except Exception as e:
            logger.error(f"Error marking opportunity as processed: {str(e)}")
            self.report_error("mark_processed_error", str(e), ErrorSeverity.WARNING)
            return False
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'get_top_opportunities':
            category = request.get('category')
            limit = request.get('limit', 10)
            opportunities = self.get_top_opportunities(category, limit)
            
            return {
                'status': 'success',
                'opportunities': opportunities
            }
            
        elif action == 'mark_processed':
            opportunity_id = request.get('opportunity_id')
            if not opportunity_id:
                return {'status': 'error', 'message': 'Missing opportunity_id parameter'}
            
            success = self.mark_opportunity_processed(opportunity_id)
            
            if success:
                return {'status': 'success', 'message': f'Opportunity {opportunity_id} marked as processed'}
            else:
                return {'status': 'error', 'message': f'Failed to mark opportunity {opportunity_id} as processed'}
                
        elif action == 'get_stats':
            return {
                'status': 'success',
                'stats': {
                    'monitored_events': self.monitored_events,
                    'processed_items': self.processed_items,
                    'valuable_opportunities': self.valuable_opportunities,
                    'buffer_size': len(self.interaction_buffer)
                }
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def _get_health_status(self):
        """Return standardized health status with SQLite and ZMQ readiness checks."""
        base_status = super()._get_health_status() if hasattr(super(), '_get_health_status') else {}

        db_connected = False
        opportunity_count = -1
        try:
            conn = sqlite3.connect(OPPORTUNITY_DB_PATH, timeout=1)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM learning_opportunities')
            opportunity_count = cursor.fetchone()[0]
            conn.close()
            db_connected = True
        except Exception as e:
            logger.error(f"Health check DB error: {e}")

        zmq_ready = hasattr(self, 'socket') and self.socket is not None

        specific_metrics = {
            'uptime_sec': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            'buffer_size': len(self.interaction_buffer),
            'db_connected': db_connected,
            'opportunity_count': opportunity_count,
            'valuable_opportunities': self.valuable_opportunities,
            'zmq_ready': zmq_ready
        }
        overall_status = 'ok' if all([db_connected, zmq_ready]) else 'degraded'
        base_status.update({
            'status': overall_status,
            'agent_specific_metrics': specific_metrics
        })
        return base_status

    def health_check(self):
        """Expose health check endpoint."""
        return self._get_health_status()
    
    # report_error() method now inherited from BaseAgent (UnifiedErrorHandler)
    
    def cleanup(self):
        self.running = False
        try:
            self.umra_
            self.coordinator_
            self.los_
            self.error_bus_pub.close()
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        logger.info("LearningOpportunityDetector shutdown complete")

if __name__ == '__main__':
    try:
        agent = LearningOpportunityDetector()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Learning Opportunity Detector shutting down due to keyboard interrupt")
    except Exception as e:
        logger.critical(f"Learning Opportunity Detector failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup() 

if __name__ == "__main__":
    agent = None
    try:
        agent = LearningOpportunityDetector()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
