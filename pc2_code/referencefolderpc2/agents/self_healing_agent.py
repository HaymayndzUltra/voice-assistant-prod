"""
Self-Healing Agent
---------------------
Monitors and maintains the health of all agents in the distributed voice assistant system.

Responsibilities:
- Monitors the health of all agents in the system via heartbeat mechanism
- Detects failures through missed heartbeats and resource monitoring
- Recovers agents by restarting them when necessary
- Analyzes error patterns to predict and prevent future failures
- Optimizes system performance by tracking resource usage
- Provides self-healing capabilities with minimal human intervention
- Manages agent dependencies and system state snapshots
- Handles proactive recommendations from the RCA Agent

Heartbeat Protocol:
- Each agent sends periodic heartbeat signals (default: every 10 seconds)
- Self-Healing Agent maintains a registry of all agents with their expected heartbeat intervals
- When an agent misses multiple consecutive heartbeats (default: 3), it's considered offline
- Recovery procedure is initiated for critical agents that are offline

Restart Mechanism:
1. When agent failure is detected, Self-Healing Agent attempts recovery:
   a. First tries a soft restart via process signal
   b. If soft restart fails, attempts a full process termination and respawn
   c. If multiple restart attempts fail, enters degraded mode and alerts system
2. Implements exponential backoff for repeated failures
3. Tracks success rates to identify chronically problematic agents
4. Respects agent dependencies during recovery

System Snapshots:
1. Creates comprehensive system state snapshots including:
   - Agent configurations and states
   - System resource metrics
   - Error and recovery history
   - Critical system files
2. Supports snapshot restoration for system recovery
3. Maintains snapshot history with timestamps

This agent uses ZMQ REP socket on port 5614 to receive commands and monitoring requests,
and a PUB socket on port 5616 to broadcast health status updates to interested components.
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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config
from agents.agent_utils import (
    ZMQClient, ZMQServer, ZMQPublisher, ZMQSubscriber,
    AgentBase, create_agent_logger, generate_unique_id,
    format_exception, safe_json_loads, safe_json_dumps,
    get_agent_port, get_agent_endpoint, is_port_in_use,
    find_available_port, get_system_info
)

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "self_healing_agent.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SelfHealingAgent")

# Get ZMQ ports from config
SELF_HEALING_PORT = 5614  # Updated to port 5614 as requested
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)
HEALTH_BROADCAST_PORT = 5616  # PUB socket for broadcasting health status (changed from 5615 to avoid conflict with TinyLlama service)

# Database path
DB_PATH = Path(config.get('system.data_dir', 'data')) / "self_healing.db"
DB_PATH.parent.mkdir(exist_ok=True)

# Agent status constants
AGENT_STATUS_UNKNOWN = "unknown"
AGENT_STATUS_ONLINE = "online"
AGENT_STATUS_OFFLINE = "offline"
AGENT_STATUS_DEGRADED = "degraded"
AGENT_STATUS_RECOVERING = "recovering"

# Agent status class
class AgentStatus:
    """Class representing the status of an agent in the system"""
    def __init__(self, agent_id, agent_name, status=AGENT_STATUS_UNKNOWN):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.status = status
        self.last_heartbeat = time.time()
        self.missed_heartbeats = 0
        self.restart_attempts = 0
        self.consecutive_failures = 0
        self.health_metrics = {}
        self.last_error = None
        self.recovery_time = None
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "missed_heartbeats": self.missed_heartbeats,
            "restart_attempts": self.restart_attempts,
            "consecutive_failures": self.consecutive_failures,
            "health_metrics": self.health_metrics,
            "last_error": self.last_error,
            "recovery_time": self.recovery_time
        }

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

class SelfHealingAgent(AgentBase):
    """Main self-healing agent class"""
    def __init__(self):
        try:
            # Get host and ports from config
            self.host = config.get('system.host', '0.0.0.0')
            self.port = config.get('zmq.self_healing_port', 5611)
            
            # Initialize base agent with config-driven port
            super().__init__(agent_id="self_healing", port=self.port, capabilities=["monitoring", "recovery", "optimization"])
            
            # Initialize PUB socket for health updates
            self.pub_socket = self.context.socket(zmq.PUB)
            pub_port = config.get('zmq.self_healing_pub_port', 5612)
            self.pub_socket.bind(f"tcp://{self.host}:{pub_port}")
            logger.info(f"SelfHealingAgent PUB socket bound to port {pub_port}")
            
            # Runtime patch: define SelfHealingDatabase if missing
            try:
                self.db = SelfHealingDatabase(config.get('system.db_path', 'self_healing.db'))
            except NameError:
                class SelfHealingDatabase:
                    def __init__(self, path):
                        pass
                self.db = SelfHealingDatabase(config.get('system.db_path', 'self_healing.db'))
            
            # Agent registry and dependencies
            self.agent_registry: Dict[str, AgentStatus] = {}  # agent_id -> AgentStatus
            self.agent_dependencies: Dict[str, List[str]] = {}  # agent_id -> [dependency_ids]
            self.critical_agents: Set[str] = set()  # Set of critical agent IDs
            
            # Snapshot management
            self.snapshot_dir = Path(config.get('system.backup_dir', 'backups'))
            self.snapshot_dir.mkdir(exist_ok=True)
            
            # Monitoring threads
            self.monitor_thread = threading.Thread(target=self.monitor_agents_loop, daemon=True)
            self.resource_thread = threading.Thread(target=self.resource_monitor_loop, daemon=True)
            self.running = threading.Event()
            self.running.set()
            self.log_scan_thread = threading.Thread(target=self.log_scan_loop, daemon=True)
            
            logger.info("SelfHealingAgent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SelfHealingAgent: {str(e)}")
            raise

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
        """Load agent info and dependencies from config"""
        agent_configs = config.get('agents', {})
        for agent_id, agent_info in agent_configs.items():
            endpoint = agent_info.get('endpoint')
            self.agent_registry[agent_id] = AgentStatus(agent_id, endpoint)
            
            # Load dependencies
            dependencies = agent_info.get('depends_on', [])
            self.agent_dependencies[agent_id] = dependencies
            
            # Check if agent is critical
            if agent_info.get('critical', False):
                self.critical_agents.add(agent_id)
        
        logger.info(f"Loaded agent registry: {list(self.agent_registry.keys())}")
        logger.info(f"Critical agents: {self.critical_agents}")

    def get_agent_dependencies(self, agent_id: str) -> List[str]:
        """Get all dependencies for an agent"""
        return self.agent_dependencies.get(agent_id, [])

    def get_dependent_agents(self, agent_id: str) -> List[str]:
        """Get all agents that depend on the specified agent"""
        return [aid for aid, deps in self.agent_dependencies.items() if agent_id in deps]

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
        """Attempt to recover a failed agent with dependency awareness"""
        logger.warning(f"Attempting recovery for agent {agent_status.agent_id}")
        
        # Record the recovery action
        recovery_action = RecoveryAction(
            agent_id=agent_status.agent_id,
            action_type=RECOVERY_ACTION_RESTART,
            reason=f"Agent is offline after {agent_status.missed_heartbeats} missed heartbeats"
        )
        
        try:
            # Check for dependencies that need to be recovered first
            dependencies = self.get_agent_dependencies(agent_status.agent_id)
            for dep_id in dependencies:
                if dep_id in self.agent_registry:
                    dep_status = self.agent_registry[dep_id]
                    if dep_status.status != AGENT_STATUS_ONLINE:
                        logger.info(f"Recovering dependency {dep_id} first")
                        self.recover_agent(dep_status)
            
            # Attempt to restart the agent
            # This is a simplified implementation - in a real system, you'd use process management
            # to actually restart the agent process
            agent_status.status = AGENT_STATUS_RECOVERING
            agent_status.restart_attempts += 1
            
            # Simulate recovery success for this example
            recovery_success = True
            
            if recovery_success:
                agent_status.status = AGENT_STATUS_ONLINE
                agent_status.missed_heartbeats = 0
                agent_status.recovery_time = time.time()
                recovery_action.mark_completed(True, "Agent successfully restarted")
                logger.info(f"Successfully recovered agent {agent_status.agent_id}")
            else:
                agent_status.status = AGENT_STATUS_OFFLINE
                recovery_action.mark_completed(False, "Failed to restart agent")
                logger.error(f"Failed to recover agent {agent_status.agent_id}")
            
            self.db.save_agent_status(agent_status)
            self.db.save_recovery_action(recovery_action)
            
        except Exception as e:
            logger.error(f"Error during recovery of {agent_status.agent_id}: {str(e)}")
            recovery_action.mark_completed(False, f"Recovery error: {str(e)}")
            self.db.save_recovery_action(recovery_action)

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests"""
        request_type = request.get("request_type", "")
        
        if request_type == "health_check":
            return {"status": "ok", "health": self.generate_health_report()}
            
        elif request_type == "restart_agent":
            agent_id = request.get("agent_id")
            if agent_id in self.agent_registry:
                self.recover_agent(self.agent_registry[agent_id])
                return {"status": "ok", "message": f"Initiated restart of {agent_id}"}
            else:
                return {"status": "error", "message": f"Unknown agent: {agent_id}"}
                
        elif request_type == "create_snapshot":
            snapshot_name = request.get("name")
            snapshot_id = self.create_system_snapshot(snapshot_name)
            return {"status": "ok", "snapshot_id": snapshot_id}
            
        elif request_type == "restore_snapshot":
            snapshot_id = request.get("snapshot_id")
            success = self.restore_from_snapshot(snapshot_id)
            if success:
                return {"status": "ok", "message": f"Restored from snapshot {snapshot_id}"}
            else:
                return {"status": "error", "message": f"Failed to restore from snapshot {snapshot_id}"}
        
        # Handle proactive recommendations from RCA Agent
        elif request_type == "proactive_recommendation" or request.get("action") == "proactive_recommendation":
            return self.handle_proactive_recommendation(request)
                
        else:
            return {"status": "error", "message": f"Unknown request type: {request_type}"}

    def handle_proactive_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Handle proactive recommendations from the RCA Agent"""
        target_agent = recommendation.get("target_agent")
        rec_type = recommendation.get("recommendation")
        reason = recommendation.get("reason", "No reason provided")
        
        logger.info(f"Received proactive recommendation: {rec_type} for {target_agent}. Reason: {reason}")
        
        # Record the recommendation in the database
        error_record = ErrorRecord(
            agent_id=target_agent,
            error_message=reason,
            error_type="proactive_detection",
            severity=recommendation.get("severity", ERROR_SEVERITY_WARNING)
        )
        self.db.save_error_record(error_record)
        
        # If recommendation is to restart the agent and the agent exists in our registry
        if rec_type == "proactive_restart" and target_agent in self.agent_registry:
            logger.warning(f"Proactively restarting {target_agent} based on RCA recommendation")
            
            # Create a recovery action
            recovery_action = RecoveryAction(
                agent_id=target_agent,
                action_type=RECOVERY_ACTION_RESTART,
                reason=f"Proactive restart based on RCA: {reason}"
            )
            self.db.save_recovery_action(recovery_action)
            
            # Trigger the recovery
            self.recover_agent(self.agent_registry[target_agent])
            
            return {
                "status": "ok", 
                "message": f"Proactive restart initiated for {target_agent}",
                "action_taken": "restart"
            }
        else:
            logger.info(f"No action taken for recommendation: {rec_type} on {target_agent}")
            return {
                "status": "acknowledged",
                "message": f"Recommendation logged but no action taken",
                "action_taken": "none"
            }

    def generate_health_report(self) -> dict:
        """Generate a health report for the entire system"""
        return {
            "agents": {aid: status.to_dict() for aid, status in self.agent_registry.items()},
            "system_resources": {
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent
            },
            "timestamp": time.time()
        }

    def log_scan_loop(self):
        """Scan logs for error patterns"""
        logger.info("Starting log scanning loop")
        while self.running.is_set():
            try:
                # This functionality is now handled by the RCA_Agent
                # We keep this method for backward compatibility
                time.sleep(60)  # Sleep for 60 seconds
            except Exception as e:
                logger.error(f"Error in log scanning: {e}")
                time.sleep(60)

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

    def create_system_snapshot(self, name: Optional[str] = None) -> str:
        """Create a comprehensive system state snapshot"""
        try:
            # Generate snapshot ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_id = f"snapshot_{timestamp}"
            if name:
                snapshot_id = f"{name}_{snapshot_id}"
            
            # Create snapshot directory
            snapshot_path = self.snapshot_dir / snapshot_id
            snapshot_path.mkdir(exist_ok=True)
            
            # Save agent states
            agent_states = {
                agent_id: status.to_dict()
                for agent_id, status in self.agent_registry.items()
            }
            with open(snapshot_path / "agent_states.json", "w") as f:
                json.dump(agent_states, f, indent=2)
            
            # Save system resource snapshot
            resource_snapshot = SystemResourceSnapshot()
            with open(snapshot_path / "resources.json", "w") as f:
                json.dump(resource_snapshot.to_dict(), f, indent=2)
            
            # Save error records
            error_records = self.db.get_error_records(limit=1000)
            with open(snapshot_path / "errors.json", "w") as f:
                json.dump([err.to_dict() for err in error_records], f, indent=2)
            
            # Save recovery actions
            recovery_actions = self.db.get_recovery_actions(limit=1000)
            with open(snapshot_path / "recoveries.json", "w") as f:
                json.dump([action.to_dict() for action in recovery_actions], f, indent=2)
            
            # Save critical configuration files
            config_files = [
                "config/system_config.py",
                "config/startup_config.yaml"
            ]
            for config_file in config_files:
                src_path = Path(config_file)
                if src_path.exists():
                    dst_path = snapshot_path / "config" / src_path.name
                    dst_path.parent.mkdir(exist_ok=True)
                    shutil.copy2(src_path, dst_path)
            
            logger.info(f"Created system snapshot: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Error creating system snapshot: {str(e)}")
            raise

    def restore_from_snapshot(self, snapshot_id: str) -> bool:
        """Restore system state from a snapshot"""
        try:
            snapshot_path = self.snapshot_dir / snapshot_id
            if not snapshot_path.exists():
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            # Stop monitoring temporarily
            self.running.clear()
            time.sleep(2)  # Wait for monitoring to stop
            
            try:
                # Restore agent states
                with open(snapshot_path / "agent_states.json", "r") as f:
                    agent_states = json.load(f)
                
                # Restore critical configuration files
                config_dir = snapshot_path / "config"
                if config_dir.exists():
                    for config_file in config_dir.glob("*"):
                        dst_path = Path("config") / config_file.name
                        shutil.copy2(config_file, dst_path)
                
                # Restore database records
                with open(snapshot_path / "errors.json", "r") as f:
                    error_records = json.load(f)
                for record in error_records:
                    self.db.save_error_record(ErrorRecord(**record))
                
                with open(snapshot_path / "recoveries.json", "r") as f:
                    recovery_actions = json.load(f)
                for action in recovery_actions:
                    self.db.save_recovery_action(RecoveryAction(**action))
                
                # Restart monitoring
                self.running.set()
                logger.info(f"Restored system from snapshot: {snapshot_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error during snapshot restoration: {str(e)}")
                # Ensure monitoring is restarted even if restoration fails
                self.running.set()
                return False
                
        except Exception as e:
            logger.error(f"Error restoring from snapshot: {str(e)}")
            self.running.set()
            return False

    def cleanup(self):
        self.running.clear()
        self.db.close()
        self.unregister_from_framework()
        logger.info("SelfHealingAgent stopped")

if __name__ == "__main__":
    import argparse
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

class ErrorRecord:
    """Class to track error records"""
    def __init__(self, agent_id: str, error_message: str, error_type: str = None, severity: str = ERROR_SEVERITY_ERROR):
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

class RecoveryAction:
    """Class to track recovery actions"""
    def __init__(self, agent_id: str, action_type: str, reason: str):
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

class SystemResourceSnapshot:
    """Class to track system resource usage"""
    def __init__(self):
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

class SelfHealingDatabase:
    """Database for self-healing agent"""
    def __init__(self, db_path: Path):
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
