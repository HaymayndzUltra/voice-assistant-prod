# File: main_pc_code/agents/error_management_system.py
#
# Ito ang FINAL at PINAHUSAY na bersyon ng Error Management System.
# Pinagsasama nito ang error collection, log scanning, health monitoring,
# at recovery sa isang, unified, at modular na ahente.

import sys
import os
import time
import logging
import threading
import json
import uuid
import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import subprocess
import zmq

# --- Path Setup ---
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity

# --- Logging Setup ---
logger = logging.getLogger('ErrorManagementSystem')

# --- Constants ---
DEFAULT_PORT = 7125 # Main port for receiving commands
ERROR_BUS_PORT = 7150 # Port for the ZMQ PUB/SUB Error Bus
DB_PATH = "data/error_system.db"
LOGS_DIR = "logs"
HEARTBEAT_INTERVAL = 15
HEARTBEAT_TIMEOUT = 45
MAX_MISSED_HEARTBEATS = 3
LOG_SCAN_INTERVAL = 60
ANALYSIS_INTERVAL = 300

# ===================================================================
#         MODULAR COMPONENTS (Alinsunod sa Plano)
# ===================================================================

class ErrorCollectorModule:
    """Handles all forms of error collection: direct reports and log scanning."""
    def __init__(self, system):
        self.system = system
        self.logs_dir = Path(LOGS_DIR)
        self.file_positions = {}
        self.error_patterns = self._load_error_patterns()
        self.log_scan_thread = threading.Thread(target=self._scan_logs_loop, daemon=True)
        self.log_scan_thread.start()

    def _load_error_patterns(self):
        # (Logic mula sa RCA_Agent)
        return [re.compile(p) for p in [r"TimeoutError", r"ZMQError", r"CUDA out of memory", r"Connection refused"]]

    def handle_direct_report(self, error_data: Dict):
        """Processes an error reported directly by another agent."""
        logger.info(f"Received direct error report from {error_data.get('source', 'unknown')}")
        self.system.add_to_error_registry(error_data)

    def _scan_logs_loop(self):
        """Periodically scans log files for new error entries."""
        logger.info("Log Scanner thread started.")
        while self.system.running:
            try:
                if not self.logs_dir.exists():
                    time.sleep(LOG_SCAN_INTERVAL)
                    continue
                for log_file in self.logs_dir.glob("*.log"):
                    self._process_log_file(log_file)
            except Exception as e:
                logger.error(f"Error in log scanning loop: {e}")
            time.sleep(LOG_SCAN_INTERVAL)

    def _process_log_file(self, log_file: Path):
        # (Logic mula sa RCA_Agent, pinahusay)
        agent_name = log_file.stem
        last_pos = self.file_positions.get(str(log_file), 0)
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                self.file_positions[str(log_file)] = f.tell()
            for line in new_lines:
                if "ERROR" in line or "CRITICAL" in line:
                    for pattern in self.error_patterns:
                        if pattern.search(line):
                            error_data = {
                                "error_id": f"log-{uuid.uuid4()}",
                                "source": f"LogScanner({agent_name})",
                                "error_type": "log_pattern_detected",
                                "message": line.strip(),
                                "severity": ErrorSeverity.WARNING.value, # Default, can be improved
                                "timestamp": time.time()
                            }
                            self.system.add_to_error_registry(error_data)
                            break
        except Exception as e:
            logger.warning(f"Could not process log file {log_file}: {e}")

class ErrorAnalyzerModule:
    """Analyzes collected errors for patterns, correlations, and anomalies."""
    def __init__(self, system):
        self.system = system
        self.analysis_thread = threading.Thread(target=self._analyze_loop, daemon=True)
        self.analysis_thread.start()

    def _analyze_loop(self):
        logger.info("Error Analyzer thread started.")
        while self.system.running:
            try:
                self._run_analysis()
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
            time.sleep(ANALYSIS_INTERVAL)

    def _run_analysis(self):
        """Main analysis function."""
        errors = self.system.get_recent_errors()
        if not errors: return

        logger.info(f"Analyzing {len(errors)} recent errors...")
        # CHECKLIST ITEM: Extract error correlation system
        correlated_events = self._find_correlations(errors)
        # CHECKLIST ITEM: Add machine learning components for anomaly detection (placeholder)
        anomalies = self._detect_anomalies(errors)

        if correlated_events or anomalies:
            recommendation = {
                "action": "investigate",
                "target": "SystemOperator",
                "reason": "Correlated errors or anomalies detected.",
                "details": {"correlations": correlated_events, "anomalies": anomalies}
            }
            self.system.recovery.add_recovery_task(recommendation)

    def _find_correlations(self, errors: List[Dict]) -> List:
        """Finds errors that happen close together in time."""
        # Simpleng correlation: mga error na nangyari sa loob ng 60s sa iba't ibang ahente
        correlations = []
        for i, error1 in enumerate(errors):
            for error2 in errors[i+1:]:
                if error1.get('source') != error2.get('source'):
                    time_diff = abs(error1.get('timestamp', 0) - error2.get('timestamp', 0))
                    if 0 < time_diff < 60:
                        correlations.append((error1, error2))
        return correlations

    def _detect_anomalies(self, errors: List[Dict]) -> List:
        """Placeholder for ML-based anomaly detection."""
        # Dito maaaring isaksak ang isang ML model sa hinaharap.
        # Sa ngayon, magche-check lang tayo ng biglaang pagdami ng errors.
        return []

class RecoveryManagerModule:
    """Monitors agent health and executes recovery actions."""
    def __init__(self, system):
        self.system = system
        self.agent_registry = {} # agent_name -> {last_heartbeat, status, ...}
        self.recovery_queue = deque()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_monitor_loop, daemon=True)
        self.recovery_thread = threading.Thread(target=self._process_recovery_queue, daemon=True)
        self.heartbeat_thread.start()
        self.recovery_thread.start()
        self.recovery_attempts = {}  # Track recovery attempts per agent
        self.max_recovery_attempts = 3  # Maximum number of recovery attempts

    def receive_heartbeat(self, agent_name: str):
        if agent_name not in self.agent_registry:
            self.agent_registry[agent_name] = {"missed_heartbeats": 0}
        self.agent_registry[agent_name]['last_heartbeat'] = time.time()
        self.agent_registry[agent_name]['status'] = 'online'
        self.agent_registry[agent_name]['missed_heartbeats'] = 0

    def add_recovery_task(self, task: Dict):
        self.recovery_queue.append(task)

    def _heartbeat_monitor_loop(self):
        logger.info("Heartbeat Monitor thread started.")
        while self.system.running:
            now = time.time()
            for agent_name, info in list(self.agent_registry.items()):
                if now - info.get('last_heartbeat', now) > HEARTBEAT_TIMEOUT:
                    info['missed_heartbeats'] += 1
                    if info['missed_heartbeats'] >= MAX_MISSED_HEARTBEATS and info.get('status') != 'offline':
                        logger.warning(f"Agent {agent_name} is offline. Adding recovery task.")
                        info['status'] = 'offline'
                        self.add_recovery_task({"action": "restart", "target": agent_name, "reason": "Missed heartbeats"})
            time.sleep(HEARTBEAT_INTERVAL)
            
    def _process_recovery_queue(self):
        """Process the recovery task queue."""
        logger.info("Recovery task processor thread started.")
        while self.system.running:
            if self.recovery_queue:
                task = self.recovery_queue.popleft()
                action = task.get("action")
                target = task.get("target")
                reason = task.get("reason", "Unknown reason")
                
                logger.info(f"Processing recovery task: {action} for {target} due to {reason}")
                
                if action == "restart" and target:
                    success = self._restart_agent(target)
                    if success:
                        logger.info(f"Successfully restarted agent {target}")
                        # Reset recovery attempts on success
                        self.recovery_attempts[target] = 0
                    else:
                        logger.error(f"Failed to restart agent {target}")
                        # Increment recovery attempts and retry if under max attempts
                        attempts = self.recovery_attempts.get(target, 0) + 1
                        self.recovery_attempts[target] = attempts
                        if attempts < self.max_recovery_attempts:
                            logger.warning(f"Scheduling another restart attempt for {target} (attempt {attempts+1}/{self.max_recovery_attempts})")
                            self.add_recovery_task(task)
                        else:
                            logger.error(f"Maximum restart attempts ({self.max_recovery_attempts}) reached for {target}")
                            # Record this in the system's error log
                            self.system.collector.add_error(
                                source="RecoveryManager",
                                error_type="recovery_failed",
                                message=f"Failed to restart {target} after {self.max_recovery_attempts} attempts",
                                severity="critical"
                            )
            time.sleep(1)  # Check queue every second
    
    def _restart_agent(self, agent_name: str) -> bool:
        """Restart an agent using SystemDigitalTwin to find its details.
        
        Args:
            agent_name: Name of the agent to restart
            
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            # Get agent details from SystemDigitalTwin
            agent_info = self._get_agent_info_from_digital_twin(agent_name)
            
            if not agent_info or "script_path" not in agent_info:
                logger.error(f"Cannot restart {agent_name}: No script path found")
                return False
            
            script_path = agent_info["script_path"]
            
            # Kill any existing process first
            self._kill_existing_process(agent_name)
            
            # Execute the restart command
            logger.info(f"Restarting {agent_name} using script: {script_path}")
            
            # Use subprocess to start the agent in the background
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  # Detach from parent process
            )
            
            # Wait briefly to see if process starts successfully
            time.sleep(2)
            if process.poll() is None:  # Process is still running
                logger.info(f"Successfully started {agent_name} process")
                
                # Record this recovery action in the system's database
                self.system._record_recovery_action(
                    agent_name=agent_name,
                    action_type="restart",
                    reason="Agent recovery",
                    success=True
                )
                return True
            else:
                stderr = process.stderr.read() if process.stderr else "No error output"
                logger.error(f"Failed to start {agent_name}: Process exited immediately with code {process.returncode}. Error: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error restarting {agent_name}: {str(e)}")
            return False
    
    def _kill_existing_process(self, agent_name: str) -> bool:
        """Kill any existing process for the given agent.
        
        Args:
            agent_name: Name of the agent process to kill
            
        Returns:
            bool: True if process was killed or not found, False on error
        """
        try:
            # Try to find and kill the process by name
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 1:
                        cmd_str = ' '.join(cmdline)
                        if agent_name in cmd_str and 'python' in cmd_str.lower():
                            logger.info(f"Killing existing process for {agent_name}: PID {proc.info['pid']}")
                            psutil.Process(proc.info['pid']).terminate()
                            try:
                                psutil.Process(proc.info['pid']).wait(timeout=5)
                            except psutil.TimeoutExpired:
                                psutil.Process(proc.info['pid']).kill()
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            return True  # No process found to kill is still a success
        except Exception as e:
            logger.error(f"Error killing existing process for {agent_name}: {str(e)}")
            return False
    
    def _get_agent_info_from_digital_twin(self, agent_name: str) -> Dict[str, Any]:
        """Get agent information from SystemDigitalTwin.
        
        Args:
            agent_name: Name of the agent to get info for
            
        Returns:
            Dict: Agent information including script_path, or empty dict if not found
        """
        try:
            # Create a ZMQ REQ socket to connect to SystemDigitalTwin
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            # Get SystemDigitalTwin address from environment or use default
            sdt_host = os.environ.get('MAINPC_IP', '192.168.100.10')
            sdt_port = int(os.environ.get('SYSTEM_DIGITAL_TWIN_PORT', 7120))
            socket.connect(f"tcp://{sdt_host}:{sdt_port}")
            
            # Send request for agent info
            request = {
                "action": "get_agent_info",
                "agent_name": agent_name
            }
            socket.send_json(request)
            
            # Wait for response
            response = socket.recv_json()
            
            # Check if response is a dictionary and has the expected fields
            if isinstance(response, dict) and response.get("status") == "success":
                agent_info = response.get("agent_info")
                if isinstance(agent_info, dict):
                    return agent_info
                else:
                    logger.error(f"Invalid agent_info format for {agent_name} from SystemDigitalTwin")
                    return {}
            else:
                error_msg = "Unknown error"
                if isinstance(response, dict) and "error" in response:
                    error_msg = response.get("error", "Unknown error")
                logger.error(f"Failed to get info for {agent_name} from SystemDigitalTwin: {error_msg}")
                return {}
        except Exception as e:
            logger.error(f"Error getting agent info from SystemDigitalTwin: {str(e)}")
            return {}
        finally:
            if 'socket' in locals():
                socket.close()
            if 'context' in locals():
                context.term()

# ===================================================================
#         UNIFIED ERROR MANAGEMENT SYSTEM (Ang Final, Merged Agent)
# ===================================================================
class ErrorManagementSystem(BaseAgent):
    """The central, unified system for error management, health monitoring, and self-healing."""

    def __init__(self, **kwargs):
        super().__init__(name="ErrorManagementSystem", port=DEFAULT_PORT, **kwargs)

        # --- Shared State & Database ---
        self.db_path = DB_PATH
        self.db_lock = threading.Lock()
        self._init_database()

        # --- Modular Architecture ---
        self.collector = ErrorCollectorModule(self)
        self.analyzer = ErrorAnalyzerModule(self)
        self.recovery = RecoveryManagerModule(self)

        # --- Error Bus (ZMQ PUB/SUB) ---
        # CHECKLIST ITEM: Error Bus Enhancement
        self.error_bus_sub = self.context.socket(zmq.SUB)
        self.error_bus_sub.connect(f"tcp://localhost:{ERROR_BUS_PORT}")
        self.error_bus_sub.setsockopt(zmq.SUBSCRIBE, b"ERROR:")
        self.error_bus_listener_thread = threading.Thread(target=self._listen_error_bus, daemon=True)
        self.error_bus_listener_thread.start()

    def _init_database(self):
        """Initializes a unified SQLite DB for errors and agent status."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_log (
                    error_id TEXT PRIMARY KEY,
                    source TEXT,
                    error_type TEXT,
                    message TEXT,
                    severity TEXT,
                    timestamp REAL,
                    details TEXT
                )
            ''')
            
            # Add recovery_actions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recovery_actions (
                    action_id TEXT PRIMARY KEY,
                    agent_name TEXT,
                    action_type TEXT,
                    reason TEXT,
                    timestamp REAL,
                    success INTEGER,
                    details TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
    def _record_recovery_action(self, agent_name: str, action_type: str, reason: str, success: bool, details: str = ""):
        """Record a recovery action in the database.
        
        Args:
            agent_name: Name of the agent that was recovered
            action_type: Type of recovery action (restart, reset, etc.)
            reason: Reason for the recovery action
            success: Whether the recovery was successful
            details: Additional details about the recovery
        """
        try:
            action_id = str(uuid.uuid4())
            timestamp = time.time()
            
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO recovery_actions 
                    (action_id, agent_name, action_type, reason, timestamp, success, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (action_id, agent_name, action_type, reason, timestamp, 1 if success else 0, details)
                )
                conn.commit()
                conn.close()
                
            logger.info(f"Recorded recovery action for {agent_name}: {action_type} - {'Success' if success else 'Failed'}")
        except Exception as e:
            logger.error(f"Error recording recovery action: {str(e)}")

    def _listen_error_bus(self):
        """Listens to the central error bus for reported errors."""
        logger.info(f"Error Bus listener started, connected to port {ERROR_BUS_PORT}.")
        while self.running:
            try:
                topic, msg = self.error_bus_sub.recv_multipart()
                error_data = json.loads(msg.decode('utf-8'))
                self.collector.handle_direct_report(error_data)
            except Exception as e:
                logger.error(f"Error processing message from Error Bus: {e}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles direct commands to the management system."""
        action = request.get("action")
        data = request.get("data", {})
        if action == "heartbeat":
            self.recovery.receive_heartbeat(data.get("agent_name"))
            return {"status": "success", "message": "Heartbeat received."}
        elif action == "get_system_status":
            return {
                "status": "success",
                "agents": self.recovery.agent_registry,
                "recent_errors": self.get_recent_errors(limit=20)
            }
        return {"status": "error", "message": f"Unknown action: {action}"}

    # --- Methods for Inter-Module Communication ---
    def add_to_error_registry(self, error_data: Dict):
        """Adds an error to the central database registry."""
        with self.db_lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO error_log VALUES (?, ?, ?, ?, ?, ?, ?)", (
                    error_data.get("error_id", f"err-{uuid.uuid4()}"),
                    error_data.get("source"), error_data.get("error_type"),
                    error_data.get("message"), error_data.get("severity"),
                    error_data.get("timestamp", time.time()),
                    json.dumps(error_data.get("details", {}))
                ))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to write error to DB: {e}")
            finally:
                conn.close()

    def get_recent_errors(self, limit: int = 100) -> List[Dict]:
        """Retrieves recent errors from the database for analysis."""
        with self.db_lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM error_log ORDER BY timestamp DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to read errors from DB: {e}")
                return []
            finally:
                conn.close()

if __name__ == '__main__':
    try:
        agent = ErrorManagementSystem()
        agent.run()
    except KeyboardInterrupt:
        logger.info("ErrorManagementSystem shutting down.")
    except Exception as e:
        logger.critical(f"ErrorManagementSystem failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup()