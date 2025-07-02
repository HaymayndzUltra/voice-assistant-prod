from main_pc_code.src.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Self-Healing Agent
- Monitors the health of all agents in the system
- Detects and recovers from failures
- Analyzes error patterns
- Optimizes system performance
- Provides self-healing capabilities
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import threading
import psutil
import re
import datetime
import sqlite3
import numpy as np
from collections import defaultdict, deque
import subprocess
import signal
import shutil
import importlib
import inspect

# Define the AgentStatus class class(BaseAgent) AgentStatus:
    """Class to track the status of an agent"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.agent_id = agent_id
        self.endpoint = endpoint
        self.last_heartbeat = None
        self.status = "unknown"
        self.error_count = 0
        self.recovery_attempts = 0
        self.metrics = {}
        self.is_alive = False
        
    def update_heartbeat(self):
        """Update the last heartbeat time"""
        self.last_heartbeat = time.time()
        self.is_alive = True
        
    def mark_error(self, error_type=None):
        """Mark an error occurred with this agent"""
        self.error_count += 1
        self.status = "error"
        self.is_alive = False
        
    def mark_recovery_attempt(self):
        """Mark a recovery attempt for this agent"""
        self.recovery_attempts += 1
        
    def __str__(self):
        return f"Agent {self.agent_id}: status={self.status}, alive={self.is_alive}"

# Add the parent directory to sys.path to import the config module

try:
from main_pc_code.config.system_config import config
except ImportError:
    # Fallback configuration if import fails
    config = {
        'agents': {},
        'logging': {'level': 'INFO'},
        'self_healing': {
            'enabled': True,
            'check_interval': 5,
            'resource_check_interval': 30,
            'log_scan_interval': 60,
            'recovery_actions': ['restart', 'notify']
        }
    }

# Setup logger first before any imports that might use it
logger = logging.getLogger("SelfHealingAgent")
log_level = 'INFO'  # Default log level
log_format = '%(asctime)s [%(levelname)s] %(message)s'  # Default format
log_file = "self_healing_agent.log"

# Configure logger
logger.setLevel(getattr(logging, log_level))
formatter = logging.Formatter(log_format)

# Add handlers if they don't exist
if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Now try to import the real AgentBase class from(BaseAgent) agent_utils
try:
from main_pc_code.agents.agent_utils import (
    except ImportError as e:
        print(f"Import error: {e}")
        ZMQClient, ZMQServer, ZMQPublisher, ZMQSubscriber,
        AgentBase, create_agent_logger, generate_unique_id,
        load_config, save_config, get_agent_status, set_agent_status
    )
    logger.info("Successfully imported AgentBase from agent_utils")
except ImportError as e:
    logger.warning(f"Could not import from agent_utils: {e}. Using fallback classes.")
    # Define a fallback AgentBase class if(BaseAgent) the import fails
    class AgentBase(BaseAgent):
        """Fallback base class for(BaseAgent) all agents in the system"""
        def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
            self.agent_id = agent_id
            self.port = port
            self.capabilities = capabilities or []
            self.context = zmq.Context()
            self.socket = None
            if port:
                self.socket = self.context.socket(zmq.REP)
                self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                try:
                    self.socket.bind(f"tcp://127.0.0.1:{port}")
                    logger.info(f"Agent {agent_id} bound to port {port}")
                except zmq.error.ZMQError as e:
                    logger.error(f"Failed to bind to port {port}: {e}")
                    # Try alternative ports
                    for alt_port in range(port+1, port+10):
                        try:
                            self.socket.bind(f"tcp://127.0.0.1:{alt_port}")
                            logger.info(f"Agent {agent_id} bound to alternative port {alt_port}")
                            self.port = alt_port
                            break
                        except zmq.error.ZMQError:
                            continue
            
        def register_with_framework(self):
            """Register this agent with the framework"""
            logger.info(f"Registering agent {self.agent_id} with framework")
            # Implementation would depend on your framework
            
        def handle_requests(self):
            """Handle incoming requests"""
            logger.info(f"Agent {self.agent_id} handling requests")
            while True:
                try:
                    if not self.socket:
                        logger.error("No socket available")
                        time.sleep(5)
                        continue
                        
                    message = self.socket.recv_json()
                    response = self.process_message(message)
                    self.socket.send_json(response)
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    time.sleep(1)
                    
        def process_message(self, message):
            """Process a received message"""
            return {"status": "ok", "agent_id": self.agent_id}
            
        def cleanup(self):
            """Clean up resources"""
            if self.socket:
                self.socket.close()
            self.context.term()
            
    # Define fallback utility functions
    def create_agent_logger(agent_id):
        return logging.getLogger(agent_id)
        
    def generate_unique_id():
        import uuid
        return str(uuid.uuid4())
        
    def load_config(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
            
    def save_config(config, path):
        try:
            with open(path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
            
    def get_agent_status(agent_id):
        return "unknown"
        
    def set_agent_status(agent_id, status):
        logger.info(f"Setting agent {agent_id} status to {status}")
        return True
        
    # Define fallback ZMQ classes
    class ZMQClient(BaseAgent):
        def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
            self.endpoint = endpoint
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.connect(endpoint)
            
        def send_request(self, request):
            try:
                self.socket.send_json(request)
                return self.socket.recv_json()
            except Exception as e:
                logger.error(f"Error sending request: {e}")
                return {"status": "error", "reason": str(e)}
                
    class ZMQServer(BaseAgent):
        def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
            self.port = port
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.bind(f"tcp://127.0.0.1:{port}")
            
    class ZMQPublisher(BaseAgent):
        def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
            self.port = port
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind(f"tcp://127.0.0.1:{port}")
            
        def publish(self, topic, message):
            try:
                self.socket.send_multipart([topic.encode(), json.dumps(message).encode()])
                return True
            except Exception as e:
                logger.error(f"Error publishing message: {e}")
                return False
                
    class ZMQSubscriber(BaseAgent):
        def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
            self.endpoint = endpoint
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(endpoint)
            
            if topics:
                for topic in topics:
                    self.socket.setsockopt(zmq.SUBSCRIBE, topic.encode())
            else:
                self.socket.setsockopt(zmq.SUBSCRIBE, b"")
                
        def receive(self, timeout=None):
            try:
                if timeout:
                    if self.socket.poll(timeout) == 0:
                        return None
                topic, message = self.socket.recv_multipart()
                return topic.decode(), json.loads(message.decode())
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                return None

# Update logger configuration with values from config
log_level = config.get('system.log_level', 'INFO')
logger.setLevel(getattr(logging, log_level))

# Log configuration loaded
logger.info(f"Loaded configuration with log level: {log_level}")

# Get ZMQ ports from config
SELF_HEALING_PORT = config.get('zmq.self_healing_port', 5604)
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)
HEALTH_BROADCAST_PORT = config.get('zmq.health_broadcast_port', 5650)

# Database path
DB_PATH = config.get('self_healing.db_path', 'self_healing.db')

# Ensure DB_PATH is a string, not a Path object
if isinstance(DB_PATH, Path):
    DB_PATH = str(DB_PATH)

# Define the SelfHealingDatabase class class(BaseAgent) SelfHealingDatabase:
    """Database for storing self-healing data"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.db_path = db_path
        self.conn = None
        self.initialize_db()
        
    def initialize_db(self):
        """Initialize the database"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_status (
                    agent_id TEXT PRIMARY KEY,
                    status TEXT,
                    last_heartbeat REAL,
                    error_count INTEGER,
                    recovery_attempts INTEGER
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    timestamp REAL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    gpu_percent REAL,
                    disk_percent REAL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    timestamp REAL,
                    agent_id TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    recovery_action TEXT
                )
            """)
            
            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            
    def save_agent_status(self, agent_id, status, last_heartbeat, error_count, recovery_attempts):
        """Save agent status to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agent_status (agent_id, status, last_heartbeat, error_count, recovery_attempts)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, status, last_heartbeat, error_count, recovery_attempts))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving agent status: {e}")
            
    def save_system_metrics(self, metrics):
        """Save system metrics to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO system_metrics (timestamp, cpu_percent, memory_percent, gpu_percent, disk_percent)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), metrics.get('cpu', 0), metrics.get('memory', 0), metrics.get('gpu', 0), metrics.get('disk', 0)))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving system metrics: {e}")
            
    def log_error(self, agent_id, error_type, error_message, recovery_action=None):
        """Log an error to the database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO error_logs (timestamp, agent_id, error_type, error_message, recovery_action)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), agent_id, error_type, error_message, recovery_action))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging error: {e}")
            
    def get_agent_status(self, agent_id):
        """Get agent status from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM agent_status WHERE agent_id = ?", (agent_id,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting agent status: {e}")
            return None
            
    def get_recent_errors(self, limit=10):
        """Get recent errors from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM error_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting recent errors: {e}")
            return []
            
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()

# Create directory for database if needed
os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)

# Agent status constants
AGENT_STATUS_UNKNOWN = "unknown"
AGENT_STATUS_ONLINE = "online"
AGENT_STATUS_OFFLINE = "offline"
AGENT_STATUS_DEGRADED = "degraded"
AGENT_STATUS_RECOVERING = "recovering"

# Error severity levels
ERROR_SEVERITY_INFO = "info"
ERROR_SEVERITY_WARNING = "warning"
ERROR_SEVERITY_ERROR = "error"
ERROR_SEVERITY_CRITICAL = "critical"

# Recovery action types
RECOVERY_ACTION_RESTART = "restart"
RECOVERY_ACTION_RESET = "reset"
RECOVERY_ACTION_CLEAR_MEMORY = "clear_memory"
RECOVERY_ACTION_OPTIMIZE = "optimize"
RECOVERY_ACTION_NOTIFY = "notify"

class SelfHealingAgent(BaseAgent)(AgentBase):
    """Main self-healing agent class"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        super().__init__(agent_id="self_healing", port=SELF_HEALING_PORT, capabilities=["monitoring", "recovery", "optimization"])
        self.db = SelfHealingDatabase(DB_PATH)
        self.agent_registry: Dict[str, AgentStatus] = {}  # agent_id -> AgentStatus
        self.monitor_thread = threading.Thread(target=self.monitor_agents_loop, daemon=True)
        self.resource_thread = threading.Thread(target=self.resource_monitor_loop, daemon=True)
        self.running = threading.Event()
        self.running.set()
        self.log_scan_thread = threading.Thread(target=self.log_scan_loop, daemon=True)
        logger.info("SelfHealingAgent initialized")

    def run(self):
        """Start monitoring and handle requests"""
        self.register_with_framework()
        self.load_agent_registry()
        self.monitor_thread.start()
        self.resource_thread.start()
        self.log_scan_thread.start()
        try:
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("SelfHealingAgent interrupted by user")
        finally:
            self.cleanup()

    def load_agent_registry(self):
        # TODO: Load agent info from config or discovery
        agent_configs = config.get('agents', {})
        for agent_id, agent_info in agent_configs.items():
            endpoint = agent_info.get('endpoint')
            self.agent_registry[agent_id] = AgentStatus(agent_id, endpoint)
        logger.info(f"Loaded agent registry: {list(self.agent_registry.keys())}")

    def monitor_agents_loop(self):
        """Monitor all agents' heartbeat and status in a loop"""
        logger.info("Starting agent monitoring loop")
        while self.running.is_set():
            for agent_id, agent_status in self.agent_registry.items():
                self.check_agent_heartbeat(agent_status)
            time.sleep(5)

    def check_agent_heartbeat(self, agent_status: AgentStatus):
        """Check if agent is alive and update status"""
        try:
            client = ZMQClient(agent_status.endpoint)
            response = client.send_request({"request_type": "heartbeat"})
            if response.get("status") == "ok":
                agent_status.update_heartbeat()
                agent_status.status = AGENT_STATUS_ONLINE
                logger.debug(f"Agent {agent_status.agent_id} is online.")
            else:
                agent_status.check_heartbeat()
            self.db.save_agent_status(agent_status)
            client.close()
        except Exception as e:
            logger.warning(f"Heartbeat check failed for {agent_status.agent_id}: {str(e)}")
            agent_status.check_heartbeat()
            self.db.save_agent_status(agent_status)
            if agent_status.can_recover():
                self.recover_agent(agent_status)

    def recover_agent(self, agent_status: AgentStatus):
        """Attempt to recover a failed agent (real restart/reset logic)"""
        logger.warning(f"Attempting recovery for agent {agent_status.agent_id}")
        agent_status.mark_recovery_attempt()
        recovery_success = False
        result_message = ""
        # Attempt to restart the agent process if possible
        try:
            agent_configs = config.get('agents', {})
            agent_info = agent_configs.get(agent_status.agent_id, {})
            start_cmd = agent_info.get('start_command')
            process_name = agent_info.get('process_name')
            # Try to kill old process if process_name is known
            if process_name:
                for proc in psutil.process_iter(['name', 'cmdline']):
                    try:
                        if process_name in proc.info['name'] or (proc.info['cmdline'] and process_name in ' '.join(proc.info['cmdline'])):
                            proc.kill()
                            logger.info(f"Killed old process for {agent_status.agent_id}")
                    except Exception:
                        pass
            # Try to start new process
            if start_cmd:
                subprocess.Popen(start_cmd, shell=True)
                logger.info(f"Restarted agent {agent_status.agent_id} with command: {start_cmd}")
                recovery_success = True
                result_message = f"Agent {agent_status.agent_id} restarted with command: {start_cmd}"
            else:
                result_message = f"No start_command defined for {agent_status.agent_id} in config."
                logger.error(result_message)
        except Exception as e:
            result_message = f"Error during restart: {str(e)}"
            logger.error(result_message)
        # Log recovery action in DB
        action = RecoveryAction(agent_status.agent_id, RECOVERY_ACTION_RESTART, "heartbeat failure")
        action.mark_completed(success=recovery_success, result_message=result_message)
        self.db.save_recovery_action(action)
        if recovery_success:
            logger.info(result_message)
        else:
            logger.error(result_message)

    def resource_monitor_loop(self):
        """Monitor system resources, log snapshots, and alert if thresholds are exceeded"""
        logger.info("Starting resource monitoring loop")
        # Thresholds (configurable)
        cpu_threshold = config.get('self_healing.cpu_threshold', 90)  # percent
        mem_threshold = config.get('self_healing.mem_threshold', 90)  # percent
        disk_threshold = config.get('self_healing.disk_threshold', 95)  # percent
        while self.running.is_set():
            snapshot = SystemResourceSnapshot()
            self.db.save_system_resource_snapshot(snapshot)
            alerts = []
            # Check CPU
            if snapshot.cpu_percent > cpu_threshold:
                alerts.append(f"CPU usage high: {snapshot.cpu_percent}% > {cpu_threshold}%")
            # Check memory
            if snapshot.memory.percent > mem_threshold:
                alerts.append(f"Memory usage high: {snapshot.memory.percent}% > {mem_threshold}%")
            # Check disk
            if snapshot.disk.percent > disk_threshold:
                alerts.append(f"Disk usage high: {snapshot.disk.percent}% > {disk_threshold}%")
            # Log alerts as error records
            for alert in alerts:
                err = ErrorRecord(
                    agent_id="system",
                    error_message=alert,
                    error_type="resource",
                    severity=ERROR_SEVERITY_WARNING if 'high' in alert else ERROR_SEVERITY_CRITICAL
                )
                self.db.save_error_record(err)
                logger.warning(f"Resource alert: {alert}")
                # Stub for future notification (e.g., desktop alert, email)
            time.sleep(10)

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests and generate health/status reports"""
        req_type = request.get("request_type")
        if req_type == "status":
            # Generate a health report
            report = self.generate_health_report()
            return {"status": "ok", "report": report}
        elif req_type == "heartbeat":
            return {"status": "ok"}
        elif req_type == "recover":
            agent_id = request.get("agent_id")
            if agent_id in self.agent_registry:
                self.recover_agent(self.agent_registry[agent_id])
                return {"status": "ok", "msg": f"Recovery triggered for {agent_id}"}
            return {"status": "error", "error": "Agent not found"}
        elif req_type == "errors":
            # Return recent error records
            limit = request.get("limit", 20)
            errors = [e.to_dict() for e in self.db.get_error_records(limit=limit)]
            return {"status": "ok", "errors": errors}
        else:
            return {"status": "error", "error": "Unknown request type"}

    def generate_health_report(self) -> dict:
        """Summarize agent health, recent errors, and resource alerts"""
        agents = {aid: astat.to_dict() for aid, astat in self.agent_registry.items()}
        errors = [e.to_dict() for e in self.db.get_error_records(limit=10)]
        resources = self.db.get_system_resource_snapshots(limit=3)
        # Compose a summary
        summary = {
            "agent_status": agents,
            "recent_errors": errors,
            "recent_resources": resources,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        # Stub for real-time notification (future: desktop/email alerts)
        logger.info(f"Health Report Generated: {json.dumps(summary, indent=2)[:500]}...")
        return summary

    def log_scan_loop(self):
        """Scan agent log files for errors and record in DB"""
        logger.info("Starting log scan loop")
        # Get log directory and scan interval from config
        logs_dir = Path(config.get('system.logs_dir', 'logs'))
        scan_interval = config.get('self_healing.log_scan_interval', 15)
        error_patterns = [re.compile(r'\bERROR\b', re.IGNORECASE), re.compile(r'\bCRITICAL\b', re.IGNORECASE), re.compile(r'\bException\b')]
        # Track last read position for each log file
        log_offsets = {}
        while self.running.is_set():
            for log_file in logs_dir.glob('*.log'):
                try:
                    agent_id = log_file.stem.replace('_agent', '')
                    if log_file not in log_offsets:
                        log_offsets[log_file] = 0
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(log_offsets[log_file])
                        for line in f:
                            for pat in error_patterns:
                                if pat.search(line):
                                    err = ErrorRecord(
                                        agent_id=agent_id,
                                        error_message=line.strip(),
                                        error_type="log_error",
                                        severity=ERROR_SEVERITY_ERROR if 'CRITICAL' in line or 'Exception' in line else ERROR_SEVERITY_WARNING
                                    )
                                    self.db.save_error_record(err)
                                    logger.warning(f"Log error detected in {log_file.name}: {line.strip()}")
                        log_offsets[log_file] = f.tell()
                except Exception as e:
                    logger.error(f"Log scan failed for {log_file}: {str(e)}")
            time.sleep(scan_interval)

    def cleanup(self):
        self.running.clear()
        self.db.close()
        self.unregister_from_framework()
        logger.info("SelfHealingAgent stopped")

if __name__ == "__main__":
    import argparse

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    parser = argparse.ArgumentParser(description="Self-Healing Agent: Monitors and recovers system agents.")
    parser.add_argument('--server', action='store_true', help='Run in server mode, waiting for ZMQ requests')
    args = parser.parse_args()
    
    agent = SelfHealingAgent()
    
    if args.server:
        # Just initialize the agent and keep it running, waiting for ZMQ requests
        logger.info("Self-Healing Agent running in server mode, waiting for requests...")
        try:
            # Keep the process alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Self-Healing Agent interrupted by user")
    else:
        # Run the full agent with monitoring
        agent.run()


class AgentStatus(BaseAgent):
    """Class to track agent status"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.agent_id = agent_id
        self.endpoint = endpoint
        self.status = AGENT_STATUS_UNKNOWN
        self.last_heartbeat = 0
        self.heartbeat_interval = 10  # seconds
        self.missed_heartbeats = 0
        self.max_missed_heartbeats = 3
        self.capabilities = []
        self.resource_usage = {}
        self.error_count = 0
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.last_recovery_time = 0
        self.recovery_cooldown = 60  # seconds
        self.is_critical = False
    
    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = time.time()
        self.missed_heartbeats = 0
        if self.status == AGENT_STATUS_UNKNOWN or self.status == AGENT_STATUS_OFFLINE:
            self.status = AGENT_STATUS_ONLINE
    
    def check_heartbeat(self) -> bool:
        """Check if heartbeat is still valid"""
        if time.time() - self.last_heartbeat > self.heartbeat_interval:
            self.missed_heartbeats += 1
            
            if self.missed_heartbeats >= self.max_missed_heartbeats:
                if self.status != AGENT_STATUS_OFFLINE:
                    logger.warning(f"Agent {self.agent_id} is offline (missed {self.missed_heartbeats} heartbeats)")
                    self.status = AGENT_STATUS_OFFLINE
                return False
            
            if self.status == AGENT_STATUS_ONLINE:
                logger.warning(f"Agent {self.agent_id} missed heartbeat ({self.missed_heartbeats}/{self.max_missed_heartbeats})")
                self.status = AGENT_STATUS_DEGRADED
            
            return False
        
        return True
    
    def can_recover(self) -> bool:
        """Check if agent can be recovered"""
        # Check if agent is offline
        if self.status != AGENT_STATUS_OFFLINE:
            return False
        
        # Check if recovery cooldown has passed
        if time.time() - self.last_recovery_time < self.recovery_cooldown:
            return False
        
        # Check if max recovery attempts reached
        if self.recovery_attempts >= self.max_recovery_attempts:
            return False
        
        return True
    
    def mark_recovery_attempt(self):
        """Mark a recovery attempt"""
        self.recovery_attempts += 1
        self.last_recovery_time = time.time()
        self.status = AGENT_STATUS_RECOVERING
    
    def reset_recovery_attempts(self):
        """Reset recovery attempts"""
        self.recovery_attempts = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "endpoint": self.endpoint,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_interval": self.heartbeat_interval,
            "missed_heartbeats": self.missed_heartbeats,
            "capabilities": self.capabilities,
            "resource_usage": self.resource_usage,
            "error_count": self.error_count,
            "recovery_attempts": self.recovery_attempts,
            "is_critical": self.is_critical
        }

class ErrorRecord(BaseAgent):
    """Class to track error records"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.id = generate_unique_id()
        self.agent_id = agent_id
        self.error_message = error_message
        self.error_type = error_type or self._detect_error_type(error_message)
        self.severity = severity
        self.timestamp = time.time()
        self.resolved = False
        self.resolved_timestamp = None
        self.resolution_message = None
        self.recovery_action = None
    
    def _detect_error_type(self, error_message: str) -> str:
        """Detect error type from message"""
        if "connection" in error_message.lower() or "timeout" in error_message.lower():
            return "connection"
        elif "memory" in error_message.lower():
            return "memory"
        elif "permission" in error_message.lower():
            return "permission"
        elif "not found" in error_message.lower():
            return "not_found"
        elif "syntax" in error_message.lower():
            return "syntax"
        else:
            return "unknown"
    
    def mark_resolved(self, resolution_message: str, recovery_action: str = None):
        """Mark error as resolved"""
        self.resolved = True
        self.resolved_timestamp = time.time()
        self.resolution_message = resolution_message
        self.recovery_action = recovery_action
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolved_timestamp": self.resolved_timestamp,
            "resolution_message": self.resolution_message,
            "recovery_action": self.recovery_action
        }

class RecoveryAction(BaseAgent):
    """Class to track recovery actions"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.id = generate_unique_id()
        self.agent_id = agent_id
        self.action_type = action_type
        self.reason = reason
        self.timestamp = time.time()
        self.success = None
        self.completed_timestamp = None
        self.result_message = None
    
    def mark_completed(self, success: bool, result_message: str):
        """Mark action as completed"""
        self.success = success
        self.completed_timestamp = time.time()
        self.result_message = result_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "success": self.success,
            "completed_timestamp": self.completed_timestamp,
            "result_message": self.result_message
        }

class SystemResourceSnapshot(BaseAgent):
    """Class to track system resource usage"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.timestamp = time.time()
        self.cpu_percent = psutil.cpu_percent(interval=0.1)
        self.memory = psutil.virtual_memory()
        self.disk = psutil.disk_usage('/')
        self.network = psutil.net_io_counters()
        self.processes = len(psutil.pids())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory": {
                "total": self.memory.total,
                "available": self.memory.available,
                "percent": self.memory.percent,
                "used": self.memory.used,
                "free": self.memory.free
            },
            "disk": {
                "total": self.disk.total,
                "used": self.disk.used,
                "free": self.disk.free,
                "percent": self.disk.percent
            },
            "network": {
                "bytes_sent": self.network.bytes_sent,
                "bytes_recv": self.network.bytes_recv,
                "packets_sent": self.network.packets_sent,
                "packets_recv": self.network.packets_recv
            },
            "processes": self.processes
        }

class SelfHealingDatabase(BaseAgent):
    """Database for self-healing agent"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SelfHealingAgent")
        self.db_path = db_path
        self.conn = None
        self.initialize_db()
    
    def initialize_db(self):
        """Initialize the database"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            cursor = self.conn.cursor()
            
            # Create agent status table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_status (
                agent_id TEXT PRIMARY KEY,
                status TEXT,
                last_heartbeat REAL,
                missed_heartbeats INTEGER,
                capabilities TEXT,
                resource_usage TEXT,
                error_count INTEGER,
                recovery_attempts INTEGER,
                is_critical INTEGER
            )
            ''')
            
            # Create error records table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_records (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                error_message TEXT,
                error_type TEXT,
                severity TEXT,
                timestamp REAL,
                resolved INTEGER,
                resolved_timestamp REAL,
                resolution_message TEXT,
                recovery_action TEXT
            )
            ''')
            
            # Create recovery actions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_actions (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                action_type TEXT,
                reason TEXT,
                timestamp REAL,
                success INTEGER,
                completed_timestamp REAL,
                result_message TEXT
            )
            ''')
            
            # Create system resources table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_resources (
                timestamp REAL PRIMARY KEY,
                cpu_percent REAL,
                memory_total REAL,
                memory_available REAL,
                memory_percent REAL,
                disk_total REAL,
                disk_used REAL,
                disk_free REAL,
                disk_percent REAL,
                network_bytes_sent REAL,
                network_bytes_recv REAL,
                processes INTEGER
            )
            ''')
            
            # Create optimization settings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT,
                last_updated REAL
            )
            ''')
            
            self.conn.commit()
            logger.info("Database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            traceback.print_exc()
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
    
    def save_agent_status(self, agent_status: AgentStatus):
        """Save agent status to database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO agent_status
            (agent_id, status, last_heartbeat, missed_heartbeats, capabilities, 
            resource_usage, error_count, recovery_attempts, is_critical)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_status.agent_id,
                agent_status.status,
                agent_status.last_heartbeat,
                agent_status.missed_heartbeats,
                json.dumps(agent_status.capabilities),
                json.dumps(agent_status.resource_usage),
                agent_status.error_count,
                agent_status.recovery_attempts,
                1 if agent_status.is_critical else 0
            ))
            
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving agent status: {str(e)}")
    
    def load_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Load agent status from database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            SELECT agent_id, status, last_heartbeat, missed_heartbeats, capabilities, 
            resource_usage, error_count, recovery_attempts, is_critical
            FROM agent_status
            WHERE agent_id = ?
            ''', (agent_id,))
            
            row = cursor.fetchone()
            
            if row:
                agent_status = AgentStatus(row[0], "")  # Endpoint will be updated later
                agent_status.status = row[1]
                agent_status.last_heartbeat = row[2]
                agent_status.missed_heartbeats = row[3]
                agent_status.capabilities = json.loads(row[4])
                agent_status.resource_usage = json.loads(row[5])
                agent_status.error_count = row[6]
                agent_status.recovery_attempts = row[7]
                agent_status.is_critical = bool(row[8])
                
                return agent_status
            
            return None
        
        except Exception as e:
            logger.error(f"Error loading agent status: {str(e)}")
            return None
    
    def save_error_record(self, error_record: ErrorRecord):
        """Save error record to database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO error_records
            (id, agent_id, error_message, error_type, severity, timestamp, 
            resolved, resolved_timestamp, resolution_message, recovery_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                error_record.id,
                error_record.agent_id,
                error_record.error_message,
                error_record.error_type,
                error_record.severity,
                error_record.timestamp,
                1 if error_record.resolved else 0,
                error_record.resolved_timestamp,
                error_record.resolution_message,
                error_record.recovery_action
            ))
            
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving error record: {str(e)}")
    
    def get_error_records(self, agent_id: Optional[str] = None, resolved: Optional[bool] = None,
                         error_type: Optional[str] = None, limit: int = 100) -> List[ErrorRecord]:
        """Get error records from database"""
        try:
            cursor = self.conn.cursor()
            
            query = '''
            SELECT id, agent_id, error_message, error_type, severity, timestamp, 
            resolved, resolved_timestamp, resolution_message, recovery_action
            FROM error_records
            '''
            
            conditions = []
            params = []
            
            if agent_id:
                conditions.append("agent_id = ?")
                params.append(agent_id)
            
            if resolved is not None:
                conditions.append("resolved = ?")
                params.append(1 if resolved else 0)
            
            if error_type:
                conditions.append("error_type = ?")
                params.append(error_type)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            records = []
            for row in cursor.fetchall():
                record = ErrorRecord(row[1], row[2], row[3], row[4])
                record.id = row[0]
                record.timestamp = row[5]
                record.resolved = bool(row[6])
                record.resolved_timestamp = row[7]
                record.resolution_message = row[8]
                record.recovery_action = row[9]
                
                records.append(record)
            
            return records
        
        except Exception as e:
            logger.error(f"Error getting error records: {str(e)}")
            return []
    
    def save_recovery_action(self, action: RecoveryAction):
        """Save recovery action to database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO recovery_actions
            (id, agent_id, action_type, reason, timestamp, success, completed_timestamp, result_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action.id,
                action.agent_id,
                action.action_type,
                action.reason,
                action.timestamp,
                1 if action.success else 0 if action.success is False else None,
                action.completed_timestamp,
                action.result_message
            ))
            
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving recovery action: {str(e)}")
    
    def get_recovery_actions(self, agent_id: Optional[str] = None, action_type: Optional[str] = None,
                            success: Optional[bool] = None, limit: int = 100) -> List[RecoveryAction]:
        """Get recovery actions from database"""
        try:
            cursor = self.conn.cursor()
            
            query = '''
            SELECT id, agent_id, action_type, reason, timestamp, success, completed_timestamp, result_message
            FROM recovery_actions
            '''
            
            conditions = []
            params = []
            
            if agent_id:
                conditions.append("agent_id = ?")
                params.append(agent_id)
            
            if action_type:
                conditions.append("action_type = ?")
                params.append(action_type)
            
            if success is not None:
                conditions.append("success = ?")
                params.append(1 if success else 0)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            actions = []
            for row in cursor.fetchall():
                action = RecoveryAction(row[1], row[2], row[3])
                action.id = row[0]
                action.timestamp = row[4]
                action.success = bool(row[5]) if row[5] is not None else None
                action.completed_timestamp = row[6]
                action.result_message = row[7]
                
                actions.append(action)
            
            return actions
        
        except Exception as e:
            logger.error(f"Error getting recovery actions: {str(e)}")
            return []
    
    def save_system_resource_snapshot(self, snapshot: SystemResourceSnapshot):
        """Save system resource snapshot to database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO system_resources
            (timestamp, cpu_percent, memory_total, memory_available, memory_percent,
            disk_total, disk_used, disk_free, disk_percent,
            network_bytes_sent, network_bytes_recv, processes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.timestamp,
                snapshot.cpu_percent,
                snapshot.memory.total,
                snapshot.memory.available,
                snapshot.memory.percent,
                snapshot.disk.total,
                snapshot.disk.used,
                snapshot.disk.free,
                snapshot.disk.percent,
                snapshot.network.bytes_sent,
                snapshot.network.bytes_recv,
                snapshot.processes
            ))
            
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving system resource snapshot: {str(e)}")
    
    def get_system_resource_snapshots(self, start_time: Optional[float] = None,
                                     end_time: Optional[float] = None,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get system resource snapshots from database"""
        try:
            cursor = self.conn.cursor()
            
            query = '''
            SELECT timestamp, cpu_percent, memory_total, memory_available, memory_percent,
            disk_total, disk_used, disk_free, disk_percent,
            network_bytes_sent, network_bytes_recv, processes
            FROM system_resources
            '''
            
            conditions = []
            params = []
            
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            snapshots = []
            for row in cursor.fetchall():
                snapshot = {
                    "timestamp": row[0],
                    "cpu_percent": row[1],
                    "memory": {
                        "total": row[2],
                        "available": row[3],
                        "percent": row[4]
                    },
                    "disk": {
                        "total": row[5],
                        "used": row[6],
                        "free": row[7],
                        "percent": row[8]
                    },
                    "network": {
                        "bytes_sent": row[9],
                        "bytes_recv": row[10]
                    },
                    "processes": row[11]
                }
                
                snapshots.append(snapshot)
            
            return snapshots
        
        except Exception as e:
            logger.error(f"Error getting system resource snapshots: {str(e)}")
            return []
    
    def save_optimization_setting(self, key: str, value: Any):
        """Save optimization setting to database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO optimization_settings
            (setting_key, setting_value, last_updated)
            VALUES (?, ?, ?)
            ''', (
                key,
                json.dumps(value),
                time.time()
            ))
            
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving optimization setting: {str(e)}")
    
    def get_optimization_setting(self, key: str, default: Any = None) -> Any:
        """Get optimization setting from database"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            SELECT setting_value
            FROM optimization_settings
            WHERE setting_key = ?
            ''', (key,))
            
            row = cursor.fetchone()
            
            if row:
                return json.loads(row[0])
            
            return default
        
        except Exception as e:
            logger.error(f"Error getting optimization setting: {str(e)}")
            return default

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise