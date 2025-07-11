#!/usr/bin/env python3
"""
Model Evaluation Framework (MEF)

Centralized agent for model performance tracking, evaluation, and feedback.
Merges Agent Trust Scorer and Performance Logger Agent logic.
"""

import sys
import os
import time
import logging
import threading
import json
import zmq
import sqlite3
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# --- Path Setup ---
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from main_pc_code.utils.config_loader import load_config
from main_pc_code.agents.request_coordinator import CircuitBreaker
from common.utils.learning_models import PerformanceMetric, ModelEvaluationScore

# --- Logging Setup ---
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'model_evaluation_framework.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ModelEvaluationFramework')

# --- Constants ---
config = load_config()
DEFAULT_PORT = config.get('mef_port', 7220)
HEALTH_CHECK_PORT = config.get('mef_health_port', 7221)
ZMQ_REQUEST_TIMEOUT = config.get('zmq_request_timeout', 5000)
EVAL_DB_PATH = config.get('mef_db_path', 'data/model_evaluation.db')

class ModelEvaluationFramework(BaseAgent):
    """
    Centralized agent for model performance tracking, evaluation, and feedback.
    Provides standardized metrics, historical data, and feedback to the learning pipeline.
    Now follows the best agent pattern for maintainability and extensibility.
    """
    def __init__(self, **kwargs):
        port = kwargs.get('port', DEFAULT_PORT)
        super().__init__(name="ModelEvaluationFramework", port=port, health_check_port=HEALTH_CHECK_PORT)
        self.config = config
        self.start_time = time.time()
        self.running = True
        self.db_path = EVAL_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
        self.context = zmq.Context()
        self._setup_zmq()
        self.metrics = {
            'performance_logs': 0,
            'trust_score_updates': 0,
            'models_tracked': 0
        }
        self.downstream_services = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()
        self.error_bus_port = config.get('error_bus_port', 7150)
        self.error_bus_host = os.environ.get('PC2_IP', config.get('error_bus_host', '192.168.100.17'))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        self.service_registry = {}
        self._register_with_service_discovery()
        self._start_background_threads()
        logger.info(f"Model Evaluation Framework initialized on port {self.port}")

    def _register_with_service_discovery(self):
        """Register this agent with the service discovery system if available."""
        try:
            from main_pc_code.utils.service_discovery_client import get_service_discovery_client
            client = get_service_discovery_client()
            self.service_registry[self.name] = {
                "name": self.name,
                "ip": self.config.get('bind_address', '0.0.0.0'),
                "port": self.port,
                "health_check_port": HEALTH_CHECK_PORT,
                "capabilities": ["model_evaluation"],
                "status": "running"
            }
            logger.info("Successfully registered with service registry.")
        except Exception as e:
            logger.warning(f"Service discovery not available: {e}")

    def _init_circuit_breakers(self):
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    context TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_evaluation_scores (
                    evaluation_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    cycle_id TEXT NOT NULL,
                    trust_score REAL NOT NULL,
                    accuracy REAL,
                    f1_score REAL,
                    avg_latency_ms REAL NOT NULL,
                    evaluation_timestamp TIMESTAMP NOT NULL,
                    comparison_data TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.report_error("database_init_error", str(e), ErrorSeverity.ERROR)

    def _setup_zmq(self):
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://*:{HEALTH_CHECK_PORT}")

    def _start_background_threads(self):
        thread = threading.Thread(target=self._main_loop, daemon=True)
        thread.start()
        logger.info("Started main loop thread")

    def _main_loop(self):
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        poller.register(self.health_socket, zmq.POLLIN)
        while self.running:
            try:
                events = dict(poller.poll(500))
                if self.socket in events and events[self.socket] == zmq.POLLIN:
                    request = self.socket.recv_json()
                    if not isinstance(request, dict):
                        logger.error(f"Received non-dict request: {request}")
                        self.socket.send_json({'status': 'error', 'message': 'Invalid request format'})
                        continue
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                if self.health_socket in events and events[self.health_socket] == zmq.POLLIN:
                    _ = self.health_socket.recv()
                    self.health_socket.send_json(self._get_health_status())
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.report_error("main_loop_error", str(e), ErrorSeverity.ERROR)
                time.sleep(1)

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get('action')
        if action == 'log_performance_metric':
            return self._handle_log_performance_metric(request)
        elif action == 'get_performance_metrics':
            return self._handle_get_performance_metrics(request)
        elif action == 'log_model_evaluation':
            return self._handle_log_model_evaluation(request)
        elif action == 'get_model_evaluation_scores':
            return self._handle_get_model_evaluation_scores(request)
        elif action == 'get_stats':
            return {'status': 'success', 'metrics': self.metrics}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def _handle_log_performance_metric(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            metric = PerformanceMetric(**request['metric'])
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO performance_metrics (metric_id, agent_name, metric_name, value, timestamp, context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(metric.metric_id),
                metric.agent_name,
                metric.metric_name,
                metric.value,
                metric.timestamp.isoformat(),
                json.dumps(metric.context) if metric.context else None
            ))
            conn.commit()
            conn.close()
            self.metrics['performance_logs'] += 1
            logger.info(f"Logged performance metric {metric.metric_id} for agent {metric.agent_name}")
            return {'status': 'success', 'metric_id': str(metric.metric_id)}
        except Exception as e:
            logger.error(f"Error logging performance metric: {e}")
            self.report_error("log_performance_metric_error", str(e), ErrorSeverity.ERROR)
            return {'status': 'error', 'message': str(e)}

    def _handle_get_performance_metrics(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            agent_name = request.get('agent_name')
            metric_name = request.get('metric_name')
            limit = request.get('limit', 10)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = '''
                SELECT metric_id, agent_name, metric_name, value, timestamp, context
                FROM performance_metrics
                WHERE 1=1
            '''
            params = []
            if agent_name:
                query += ' AND agent_name = ?'
                params.append(agent_name)
            if metric_name:
                query += ' AND metric_name = ?'
                params.append(metric_name)
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            metrics = []
            for row in rows:
                metric = PerformanceMetric(
                    metric_id=row[0],
                    agent_name=row[1],
                    metric_name=row[2],
                    value=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    context=json.loads(row[5]) if row[5] else None
                )
                metrics.append(metric.dict())
            return {'status': 'success', 'metrics': metrics}
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            self.report_error("get_performance_metrics_error", str(e), ErrorSeverity.ERROR)
            return {'status': 'error', 'message': str(e)}

    def _handle_log_model_evaluation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            evaluation = ModelEvaluationScore(**request['evaluation'])
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO model_evaluation_scores (
                    evaluation_id, model_name, cycle_id, trust_score, accuracy, f1_score, avg_latency_ms, evaluation_timestamp, comparison_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(evaluation.evaluation_id),
                evaluation.model_name,
                str(evaluation.cycle_id),
                evaluation.trust_score,
                evaluation.accuracy,
                evaluation.f1_score,
                evaluation.avg_latency_ms,
                evaluation.evaluation_timestamp.isoformat(),
                json.dumps(evaluation.comparison_data) if evaluation.comparison_data else None
            ))
            conn.commit()
            conn.close()
            self.metrics['trust_score_updates'] += 1
            logger.info(f"Logged model evaluation {evaluation.evaluation_id} for model {evaluation.model_name}")
            return {'status': 'success', 'evaluation_id': str(evaluation.evaluation_id)}
        except Exception as e:
            logger.error(f"Error logging model evaluation: {e}")
            self.report_error("log_model_evaluation_error", str(e), ErrorSeverity.ERROR)
            return {'status': 'error', 'message': str(e)}

    def _handle_get_model_evaluation_scores(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            model_name = request.get('model_name')
            limit = request.get('limit', 10)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = '''
                SELECT evaluation_id, model_name, cycle_id, trust_score, accuracy, f1_score, avg_latency_ms, evaluation_timestamp, comparison_data
                FROM model_evaluation_scores
                WHERE 1=1
            '''
            params = []
            if model_name:
                query += ' AND model_name = ?'
                params.append(model_name)
            query += ' ORDER BY evaluation_timestamp DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            evaluations = []
            for row in rows:
                evaluation = ModelEvaluationScore(
                    evaluation_id=row[0],
                    model_name=row[1],
                    cycle_id=row[2],
                    trust_score=row[3],
                    accuracy=row[4],
                    f1_score=row[5],
                    avg_latency_ms=row[6],
                    evaluation_timestamp=datetime.fromisoformat(row[7]),
                    comparison_data=json.loads(row[8]) if row[8] else None
                )
                evaluations.append(evaluation.dict())
            return {'status': 'success', 'evaluations': evaluations}
        except Exception as e:
            logger.error(f"Error getting model evaluation scores: {e}")
            self.report_error("get_model_evaluation_scores_error", str(e), ErrorSeverity.ERROR)
            return {'status': 'error', 'message': str(e)}

    def _get_health_status(self):
        """Return standardized health status with DB and ZMQ readiness checks."""
        base_status = super()._get_health_status() if hasattr(super(), '_get_health_status') else {}

        # SQLite connectivity
        db_connected = False
        perf_count = eval_count = -1
        try:
            conn = sqlite3.connect(self.db_path, timeout=1)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM performance_metrics')
            perf_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM model_evaluation_scores')
            eval_count = cursor.fetchone()[0]
            conn.close()
            db_connected = True
        except Exception as e:
            logger.error(f"Health check DB error: {e}")

        # ZMQ readiness (use self.health_socket or any socket attribute)
        zmq_ready = hasattr(self, 'socket') and self.socket is not None

        uptime = time.time() - self.start_time if hasattr(self, 'start_time') else 0

        specific_metrics = {
            'uptime_sec': uptime,
            'performance_logs': getattr(self, 'metrics', {}).get('performance_logs', 0),
            'trust_score_updates': getattr(self, 'metrics', {}).get('trust_score_updates', 0),
            'models_tracked': getattr(self, 'metrics', {}).get('models_tracked', 0),
            'db_connected': db_connected,
            'perf_count': perf_count,
            'eval_count': eval_count,
            'zmq_ready': zmq_ready
        }
        overall_status = 'ok' if all([db_connected, zmq_ready]) else 'degraded'
        base_status.update({
            'status': overall_status,
            'agent_specific_metrics': specific_metrics
        })
        return base_status

    def report_error(self, error_type: str, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR):
        try:
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "error_type": error_type,
                "message": message,
                "severity": severity.value
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"Reported error to bus: {error_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'error_bus_pub'):
            self.error_bus_pub.close()
        super().cleanup()
        logger.info("Cleanup complete")

if __name__ == '__main__':
    try:
        agent = ModelEvaluationFramework()
        while agent.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Model Evaluation Framework shutting down due to keyboard interrupt")
    except Exception as e:
        logger.critical(f"Model Evaluation Framework failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup() 

if __name__ == "__main__":
    agent = None
    try:
        agent = ModelEvaluationFramework()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
