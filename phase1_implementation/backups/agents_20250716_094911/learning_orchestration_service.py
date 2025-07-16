#!/usr/bin/env python3
"""
Learning Orchestration Service (LOS)

Central manager for training cycles, resource allocation, and learning pipeline coordination.
Implements unified training management for continuous learning.
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
from typing import Dict, Any, List, Optional, cast


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
# --- Path Setup ---
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from main_pc_code.utils.config_loader import load_config
from main_pc_code.agents.request_coordinator import CircuitBreaker
from common.utils.learning_models import TrainingCycle

# --- Logging Setup ---
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'learning_orchestration_service.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('LearningOrchestrationService')

# --- Constants ---
config = load_config()
DEFAULT_PORT = config.get('los_port', 7210)
HEALTH_CHECK_PORT = config.get('los_health_port', 7211)
ZMQ_REQUEST_TIMEOUT = config.get('zmq_request_timeout', 5000)
TRAINING_DB_PATH = config.get('los_db_path', join_path("data", "training_cycles.db"))

class LearningOrchestrationService(BaseAgent):
    """
    Manages the learning lifecycle: training cycles, resource allocation, and coordination.
    Receives learning opportunities, schedules training, and tracks results.
    Now follows the best agent pattern for maintainability and extensibility.
    """
    def __init__(self, **kwargs):
        port = kwargs.get('port', DEFAULT_PORT)
        super().__init__(name="LearningOrchestrationService", port=port, health_check_port=HEALTH_CHECK_PORT)
        self.config = config
        self.start_time = time.time()
        self.running = True
        self.training_cycles = {}
        self.active_jobs = {}
        self.metrics = {
            'cycles_created': 0,
            'cycles_completed': 0,
            'cycles_failed': 0,
            'opportunities_received': 0
        }
        self.db_path = TRAINING_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
        self.context = zmq.Context()
        self._setup_zmq()
        self.downstream_services = ["ModelEvaluationFramework"]
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
        logger.info(f"Learning Orchestration Service initialized on port {self.port}")

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
                "capabilities": ["learning_orchestration"],
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
                CREATE TABLE IF NOT EXISTS training_cycles (
                    id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    learning_opportunities TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    resource_allocation TEXT,
                    hyperparameters TEXT,
                    training_logs TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resource_allocation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT,
                    resource_type TEXT,
                    amount REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    # Defensive: ensure request is a dict
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
        if action == 'new_learning_opportunity':
            return self._handle_new_opportunity(request)
        elif action == 'get_training_cycles':
            return self._handle_get_training_cycles(request)
        elif action == 'get_stats':
            return {'status': 'success', 'metrics': self.metrics}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def _handle_new_opportunity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Use shared TrainingCycle model
            opportunity_id = request.get('opportunity_id')
            score = request.get('score')
            category = request.get('category')
            timestamp = request.get('timestamp', datetime.utcnow().isoformat())
            self.metrics['opportunities_received'] += 1
            # Create a new TrainingCycle instance
            cycle = TrainingCycle(
                model_name="ChitChatLLM_v2",  # This should be dynamic/configurable
                learning_opportunities=[opportunity_id],
                status='scheduled',
                start_time=datetime.fromisoformat(timestamp),
                resource_allocation={"gpu_id": 0, "vram_mb": 8192},
                hyperparameters={"learning_rate": 0.001, "epochs": 3, "batch_size": 8},
                training_logs=None
            )
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO training_cycles (
                    id, model_name, learning_opportunities, status, start_time, end_time, resource_allocation, hyperparameters, training_logs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(cycle.cycle_id),
                cycle.model_name,
                json.dumps(cycle.learning_opportunities),
                cycle.status,
                cycle.start_time.isoformat() if cycle.start_time else None,
                cycle.end_time.isoformat() if cycle.end_time else None,
                json.dumps(cycle.resource_allocation),
                json.dumps(cycle.hyperparameters),
                cycle.training_logs
            ))
            conn.commit()
            conn.close()
            self.metrics['cycles_created'] += 1
            logger.info(f"Scheduled new training cycle {cycle.cycle_id} for opportunity {opportunity_id}")
            return {'status': 'acknowledged', 'cycle_id': str(cycle.cycle_id)}
        except Exception as e:
            logger.error(f"Error handling new opportunity: {e}")
            self.report_error("handle_opportunity_error", str(e), ErrorSeverity.ERROR)
            return {'status': 'error', 'message': str(e)}

    def _handle_get_training_cycles(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            limit = request.get('limit', 10)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, model_name, learning_opportunities, status, start_time, end_time, resource_allocation, hyperparameters, training_logs
                FROM training_cycles
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            conn.close()
            cycles = []
            for row in rows:
                # Defensive: ensure all learning_opportunities are UUIDs and not None
                raw_opps = json.loads(row[2])
                from uuid import UUID
                from typing import List
                def safe_uuid(val) -> UUID | None:
                    try:
                        if val is None:
                            return None
                        if isinstance(val, UUID):
                            return val
                        return UUID(str(val))
                    except Exception:
                        logger.warning(f"Invalid UUID in learning_opportunities: {val}")
                        return None
                opp_uuids: List[UUID] = []
                for opp in raw_opps:
                    u = safe_uuid(opp)
                    if isinstance(u, UUID):
                        opp_uuids.append(u)
                opp_uuids = cast(List[UUID], opp_uuids)
                assert all(isinstance(u, UUID) for u in opp_uuids), "learning_opportunities must be List[UUID] with no None"
                cycle = TrainingCycle(  # type: ignore
                    cycle_id=row[0],
                    model_name=row[1],
                    learning_opportunities=opp_uuids,
                    status=row[3],
                    start_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    end_time=datetime.fromisoformat(row[5]) if row[5] else None,
                    resource_allocation=json.loads(row[6]) if row[6] else {},
                    hyperparameters=json.loads(row[7]) if row[7] else {},
                    training_logs=row[8]
                )
                cycles.append(cycle.dict())
            return {'status': 'success', 'cycles': cycles}
        except Exception as e:
            logger.error(f"Error getting training cycles: {e}")
            self.report_error("get_cycles_error", str(e), ErrorSeverity.ERROR)
            return {'status': 'error', 'message': str(e)}

    def _get_health_status(self):
        """Return standardized health status with SQLite and ZMQ readiness checks."""
        base_status = super()._get_health_status() if hasattr(super(), '_get_health_status') else {}

        db_connected = False
        cycle_count = -1
        try:
            conn = sqlite3.connect(self.db_path, timeout=1)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM training_cycles')
            cycle_count = cursor.fetchone()[0]
            conn.close()
            db_connected = True
        except Exception as e:
            logger.error(f"Health check DB error: {e}")

        zmq_ready = hasattr(self, 'socket') and self.socket is not None

        uptime = time.time() - self.start_time if hasattr(self, 'start_time') else 0

        specific_metrics = {
            'uptime_sec': uptime,
            'cycles_created': getattr(self, 'metrics', {}).get('cycles_created', 0),
            'cycles_completed': getattr(self, 'metrics', {}).get('cycles_completed', 0),
            'cycles_failed': getattr(self, 'metrics', {}).get('cycles_failed', 0),
            'opportunities_received': getattr(self, 'metrics', {}).get('opportunities_received', 0),
            'training_cycle_count': cycle_count,
            'db_connected': db_connected,
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
        agent = LearningOrchestrationService()
        while agent.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Learning Orchestration Service shutting down due to keyboard interrupt")
    except Exception as e:
        logger.critical(f"Learning Orchestration Service failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup()


if __name__ == "__main__":
    agent = None
    try:
        agent = LearningOrchestrationService()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
