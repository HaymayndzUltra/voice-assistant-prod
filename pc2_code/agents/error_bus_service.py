#!/usr/bin/env python3
"""
Error Bus Service

The centralized error bus for the distributed AI system.
Uses ZeroMQ PUB/SUB pattern to decouple error reporting from error processing.
"""

import os
import sys
import time
import json
import logging
import threading
import sqlite3
import yaml
import re
import zmq
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project's pc2_code directory to the Python path
PC2_CODE_DIR = get_main_pc_code()
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

# Add the project's root directory to the Python path
ROOT_DIR = PC2_CODE_DIR.parent
if ROOT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, ROOT_DIR.as_posix())

from common.core.base_agent import BaseAgent

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "error_bus.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ErrorBus")

class ErrorBusService(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()"""
    Error Bus Service
    
    A centralized error bus for the distributed AI system.
    Uses ZeroMQ PUB/SUB pattern to decouple error reporting from error processing.
    """
    
    def __init__(self, port: int = 7150, **kwargs):
        super().__init__(name="ErrorBus", port=port, **kwargs)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize database
        self.db_path = self.config.get('error_management', {}).get('db_path', join_path("data", "error_system.db"))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
        
        # Error bus ZMQ setup
        self.pub_socket = None
        self.sub_socket = None
        self._setup_zmq()
        
        # Error pattern matching
        self.error_patterns = self.config.get('error_management', {}).get('error_patterns', [])
        
        # Start error collection thread
        self.collection_thread = threading.Thread(target=self._run_error_collection, daemon=True)
        self.collection_thread.start()
        
        # Start log scanning thread
        self.log_scan_interval = self.config.get('error_management', {}).get('scan_interval', 300)
        self.logs_dir = self.config.get('error_management', {}).get('logs_dir', 'logs')
        self.log_scan_thread = threading.Thread(target=self._run_log_scanning, daemon=True)
        self.log_scan_thread.start()
        
        logger.info(f"{self.name} initialized successfully")
    
    def _load_config(self) -> Dict:
        """Load error bus configuration from YAML file"""
        try:
            config_path = Path(ROOT_DIR) / 'documentation' / 'error_management' / 'error_bus_config.yaml'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                
                # Process environment variables in the config
                config = self._process_env_vars(config)
                return config
            else:
                logger.warning(f"Configuration file not found at {config_path}")
                return {
                    "error_bus": {
                        "port": 7150,
                        "topic": "ERROR:",
                        "bind_address": "0.0.0.0",
                    },
                    "error_management": {
                        "db_path": join_path("data", "error_system.db"),
                        "logs_dir": "logs",
                        "scan_interval": 300,
                    }
                }
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _process_env_vars(self, config: Dict) -> Dict:
        """Process environment variables in the configuration"""
        def process_value(value: Any) -> Any:
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                return os.environ.get(env_var, value)
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(v) for v in value]
            else:
                return value
        
        if not isinstance(config, dict):
            return {}
                
        return process_value(config)
    
    def _init_database(self):
        """Initialize the error database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables defined in the configuration
            schema = self.config.get('database_schema', {}).get('tables', [])
            
            if not schema:
                # Default schema if not defined in configuration
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        agent TEXT,
                        error_type TEXT,
                        message TEXT,
                        severity TEXT,
                        context TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS agent_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent TEXT,
                        status TEXT,
                        last_heartbeat REAL,
                        error_count INTEGER
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recovery_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        agent TEXT,
                        action TEXT,
                        success INTEGER,
                        details TEXT
                    )
                ''')
            else:
                # Create tables from the configuration
                for table in schema:
                    table_name = table.get('name')
                    columns = table.get('columns', [])
                    
                    if table_name and columns:
                        column_defs = [f"{col['name']} {col['type']}" for col in columns]
                        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
                        cursor.execute(query)
            
            conn.commit()
            conn.close()
            logger.info(f"Error database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def _setup_zmq(self):
        """Set up ZMQ PUB/SUB sockets for the error bus"""
        try:
            # Configuration
            bind_address = self.config.get('error_bus', {}).get('bind_address', '0.0.0.0')
            port = self.config.get('error_bus', {}).get('port', 7150)
            topic = self.config.get('error_bus', {}).get('topic', 'ERROR:')
            
            # PUB socket for broadcasting errors
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://{bind_address}:{port}")
            logger.info(f"Error bus PUB socket bound to tcp://{bind_address}:{port}")
            
            # SUB socket for collecting errors
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.bind(f"tcp://{bind_address}:{port + 1}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, topic)
            logger.info(f"Error bus SUB socket bound to tcp://{bind_address}:{port + 1}")
            
        except Exception as e:
            logger.error(f"Error setting up ZMQ sockets: {e}")
    
    def _run_error_collection(self):
        """Run the error collection loop"""
        logger.info("Error collection thread started")
        while self.running:
            try:
                if self.sub_socket:
                    # Poll with timeout to allow for clean shutdown
                    if self.sub_socket.poll(timeout=1000):
                        message = self.sub_socket.recv_string()
                        self._process_error_message(message)
            except Exception as e:
                logger.error(f"Error in collection thread: {e}")
                time.sleep(1)
    
    def _process_error_message(self, message: str):
        """Process an incoming error message"""
        try:
            if message.startswith("ERROR:"):
                json_str = message[6:]  # Remove the ERROR: prefix
                error_data = json.loads(json_str)
                
                # Log the error
                logger.info(f"Received error: {error_data}")
                
                # Store in database
                self._store_error(error_data)
                
                # Forward to subscribers (if needed)
                self._forward_error(error_data)
            else:
                logger.warning(f"Received message with unknown format: {message[:20]}...")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in error message: {message[:50]}...")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _store_error(self, error_data: Dict):
        """Store an error in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = error_data.get('timestamp', time.time())
            agent = error_data.get('agent', 'unknown')
            error_type = error_data.get('error_type', 'unknown')
            message = error_data.get('message', '')
            severity = error_data.get('severity', 'ERROR')
            context = json.dumps(error_data.get('details', {}))
            
            cursor.execute(
                "INSERT INTO errors (timestamp, agent, error_type, message, severity, context) VALUES (?, ?, ?, ?, ?, ?)",
                (timestamp, agent, error_type, message, severity, context)
            )
            
            # Update agent health status
            cursor.execute("SELECT error_count FROM agent_health WHERE agent = ?", (agent,))
            row = cursor.fetchone()
            if row:
                error_count = row[0] + 1
                cursor.execute(
                    "UPDATE agent_health SET error_count = ?, last_heartbeat = ?, status = ? WHERE agent = ?",
                    (error_count, time.time(), 'error', agent)
                )
            else:
                cursor.execute(
                    "INSERT INTO agent_health (agent, status, last_heartbeat, error_count) VALUES (?, ?, ?, ?)",
                    (agent, 'error', time.time(), 1)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing in database: {e}")
    
    def _forward_error(self, error_data: Dict):
        """Forward error to subscribers if needed"""
        # If errors need to be forwarded to other systems or services
        pass
    
    def _run_log_scanning(self):
        """Run the log scanning loop"""
        logger.info("Log scanning thread started")
        while self.running:
            try:
                self._scan_logs()
                # Sleep until next scan
                time.sleep(self.log_scan_interval)
            except Exception as e:
                logger.error(f"Error in log scanning thread: {e}")
                time.sleep(60)  # Longer sleep on error
    
    def _scan_logs(self):
        """Scan log files for error patterns"""
        try:
            log_dir = Path(self.logs_dir)
            if not log_dir.exists():
                logger.warning(f"Log directory not found: {log_dir}")
                return
                
            for log_file in log_dir.glob("*.log"):
                self._scan_log_file(log_file)
        except Exception as e:
            logger.error(f"Error scanning logs: {e}")
    
    def _scan_log_file(self, log_file: Path):
        """Scan a single log file for error patterns"""
        try:
            # Skip files that haven't been modified in the last scan interval
            if time.time() - os.path.getmtime(log_file) > self.log_scan_interval:
                return
                
            with open(log_file, 'r') as f:
                # Read only the last 1000 lines to avoid excessive memory usage
                lines = f.readlines()[-1000:]
                content = ''.join(lines)
                
                # Check for error patterns
                for pattern in self.error_patterns:
                    regex = pattern.get('pattern', '')
                    error_type = pattern.get('error_type', 'unknown')
                    severity = pattern.get('severity', 'WARNING')
                    
                    matches = re.findall(regex, content)
                    for match in matches:
                        # Create an error entry for each match
                        error_data = {
                            'timestamp': time.time(),
                            'agent': log_file.stem,
                            'error_type': error_type,
                            'message': str(match),
                            'severity': severity,
                            'details': {
                                'source': 'log_scan',
                                'log_file': str(log_file)
                            }
                        }
                        
                        # Store the error
                        self._store_error(error_data)
        except Exception as e:
            logger.error(f"Error scanning log file {log_file}: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check"""
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "errors_collected": self._get_error_count(),
            "db_path": self.db_path
        }
    
    def _get_error_count(self) -> int:
        """Get the total number of errors collected"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM errors")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting error count: {e}")
            return -1
    
    def get_recent_errors(self, limit: int = 100) -> List[Dict]:
        """Get recent errors from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM errors ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            errors = [dict(row) for row in rows]
            conn.close()
            return errors
        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return []
    
    def get_agent_health(self) -> List[Dict]:
        """Get health status for all agents"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_health ORDER BY last_heartbeat DESC")
            rows = cursor.fetchall()
            health = [dict(row) for row in rows]
            conn.close()
            return health
        except Exception as e:
            logger.error(f"Error getting agent health: {e}")
            return []
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        if not isinstance(request, dict):
            return {"status": "error", "message": "Invalid request format"}
            
        action = request.get("action")
        data = request.get("data", {})
        
        try:
            if action == "health_check":
                return {"status": "success", "data": self.health_check()}
            elif action == "get_recent_errors":
                limit = data.get("limit", 100)
                return {"status": "success", "data": self.get_recent_errors(limit)}
            elif action == "get_agent_health":
                return {"status": "success", "data": self.get_agent_health()}
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"status": "error", "message": str(e)}
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Shutting down Error Bus")
        self.running = False
        
        # Close ZMQ sockets
        if self.pub_socket:
            self.pub_socket.close()
        if self.sub_socket:
            self.sub_socket.close()
        
        super().cleanup()


    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None))
        }
if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Error Bus Service")
    parser.add_argument("--port", type=int, default=7150, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start the Error Bus service
    service = ErrorBusService(port=args.port)
    service.run() 