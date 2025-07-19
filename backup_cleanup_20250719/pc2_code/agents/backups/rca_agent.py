#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Root Cause Analysis (RCA) Agent
-------------------------------
Analyzes log files for error patterns and provides proactive recommendations to the Self-Healing Agent.

Responsibilities:
- Periodically scans log files in the logs directory
- Uses regex patterns to identify common error types
- Tracks error frequency and patterns over time
- Detects when error thresholds are exceeded
- Generates proactive recommendations for the Self-Healing Agent
- Communicates with the Self-Healing Agent via ZMQ

This agent helps the system transition from reactive to proactive self-healing by
identifying potential issues before they cause critical failures.
"""

import os
import re
import time
import json
import logging
import threading
import zmq
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility with fallback
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
    # Config is loaded at the module level
except ImportError:
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = join_path("logs", "rca_agent.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path)
    ]
)
logger = logging.getLogger("RCA_Agent")

# ZMQ ports
RCA_AGENT_PORT = 7121  # Default, will be overridden by configuration
RCA_AGENT_HEALTH_PORT = 8121  # Default health check port

# Constants
LOGS_DIR = "logs"
SELF_HEALING_PORT = 5614  # Port for Self-Healing Agent on PC2
SCAN_INTERVAL = 60  # Scan logs every 60 seconds
ERROR_WINDOW = 600  # Track errors in a 10-minute window (600 seconds)
ERROR_THRESHOLD = 5  # Number of errors to trigger recommendation
PC2_IP = get_service_ip("pc2")  # PC2 IP address

class ErrorPattern:
    """Class to represent an error pattern with its regex and metadata"""
    def __init__(self, name: str, regex: str, severity: str = "medium", 
                 recommendation: str = "proactive_restart", description: str = ""):
        self.name = name
        self.regex = regex
        self.severity = severity  # low, medium, high, critical
        self.recommendation = recommendation
        self.description = description
        self.compiled_regex = re.compile(regex)
    
    def matches(self, line: str) -> bool:
        """Check if a log line matches this error pattern"""
        return bool(self.compiled_regex.search(line))

class ErrorOccurrence:
    """Class to track occurrences of an error pattern"""
    def __init__(self, agent_name: str, error_pattern: ErrorPattern, timestamp: float, line: str):
         super().__init__(name="DummyArgs", port=None)
self.agent_name = agent_name
        self.error_pattern = error_pattern
        self.timestamp = timestamp
        self.line = line

class RCA_Agent:
    """Root Cause Analysis Agent for proactive system healing"""
    
    def __init__(self, logs_dir: str = LOGS_DIR, self_healing_port: int = SELF_HEALING_PORT, 
                 pc2_ip: str = PC2_IP, port: int = None, health_check_port: int = None):
        """Initialize the RCA Agent"""
        self.logs_dir = Path(logs_dir)
        self.self_healing_port = self_healing_port
        self.pc2_ip = pc2_ip
        
        # Set up ports
        self.main_port = port if port is not None else RCA_AGENT_PORT
        self.health_port = health_check_port if health_check_port is not None else RCA_AGENT_HEALTH_PORT
        
        # Create ZMQ context and server socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")
        
        # Create client socket for communicating with Self-Healing Agent
        self.client_socket = self.context.socket(zmq.REQ)
        self.client_socket.connect(f"tcp://{self.pc2_ip}:{self_healing_port}")
        logger.info(f"Connected to Self-Healing Agent on {self.pc2_ip}:{self_healing_port}")
        
        # Define error patterns to look for
        self.error_patterns = [
            ErrorPattern(
                name="timeout_error",
                regex=r"TimeoutError|timed? out|connection timeout",
                severity="medium",
                recommendation="proactive_restart",
                description="Connection timeout detected"
            ),
            ErrorPattern(
                name="zmq_error",
                regex=r"ZMQError|Address in use|Address already in use|Cannot bind to address",
                severity="high",
                recommendation="proactive_restart",
                description="ZMQ socket binding error detected"
            ),
            ErrorPattern(
                name="cuda_out_of_memory",
                regex=r"CUDA out of memory|CUDA error|CUDA allocation failed|GPU out of memory",
                severity="critical",
                recommendation="proactive_restart",
                description="GPU memory allocation failure detected"
            ),
            ErrorPattern(
                name="connection_refused",
                regex=r"Connection refused|Failed to connect|Cannot connect to|Connection error",
                severity="medium",
                recommendation="proactive_restart",
                description="Connection refused error detected"
            ),
            ErrorPattern(
                name="file_not_found",
                regex=r"FileNotFoundError|No such file or directory|Cannot find the file|File does not exist",
                severity="medium",
                recommendation="proactive_restart",
                description="File not found error detected"
            ),
            ErrorPattern(
                name="permission_error",
                regex=r"PermissionError|Access denied|Permission denied|Not authorized",
                severity="high",
                recommendation="proactive_restart",
                description="Permission error detected"
            ),
            ErrorPattern(
                name="memory_error",
                regex=r"MemoryError|Out of memory|Cannot allocate memory|Memory allocation failed",
                severity="critical",
                recommendation="proactive_restart",
                description="Memory allocation failure detected"
            ),
            ErrorPattern(
                name="json_decode_error",
                regex=r"JSONDecodeError|Invalid JSON|Failed to parse JSON|JSON parsing error",
                severity="low",
                recommendation="proactive_restart",
                description="JSON parsing error detected"
            ),
            ErrorPattern(
                name="key_error",
                regex=r"KeyError|Key not found|Missing key|Invalid key",
                severity="low",
                recommendation="proactive_restart",
                description="Dictionary key error detected"
            ),
            ErrorPattern(
                name="import_error",
                regex=r"ImportError|ModuleNotFoundError|No module named|Failed to import",
                severity="high",
                recommendation="proactive_restart",
                description="Module import error detected"
            )
        ]
        
        # Track file positions to avoid re-reading the same lines
        self.file_positions = {}
        
        # Track error occurrences with timestamps
        self.error_occurrences = deque()
        
        # Track when recommendations were sent to avoid spamming
        self.sent_recommendations = {}
        
        # Flag to control background threads
        self.running = True
        
        # Start the log scanning thread
        self.scan_thread = threading.Thread(target=self._scan_logs_loop)
        self.scan_thread.daemon = True
        
        logger.info(f"RCA_Agent initialized on port {self.main_port}")
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'RCA_Agent',
            'timestamp': datetime.datetime.now().isoformat(),
            'scan_thread_alive': self.scan_thread.is_alive() if hasattr(self, 'scan_thread') else False,
            'error_occurrences_count': len(self.error_occurrences),
            'port': self.main_port
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'health_check':
            return self._health_check()
        elif action == 'get_error_stats':
            return self._get_error_stats()
        elif action == 'scan_logs':
            # Trigger immediate log scan
            try:
                self._scan_logs()
                self._analyze_errors()
                return {'status': 'success', 'message': 'Log scan completed'}
            except Exception as e:
                return {'status': 'error', 'error': str(e)}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def _get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        current_time = time.time()
        
        # Remove old error occurrences outside the time window
        while self.error_occurrences and self.error_occurrences[0].timestamp < current_time - ERROR_WINDOW:
            self.error_occurrences.popleft()
        
        # Count errors by agent and pattern within the time window
        error_counts = defaultdict(lambda: defaultdict(int))
        for occurrence in self.error_occurrences:
            error_counts[occurrence.agent_name][occurrence.error_pattern.name] += 1
        
        return {
            'status': 'success',
            'error_counts': dict(error_counts),
            'total_occurrences': len(self.error_occurrences),
            'time_window_seconds': ERROR_WINDOW
        }
    
    def run(self):
        """Main run loop that handles incoming requests."""
        logger.info(f"RCA_Agent starting on port {self.main_port}")
        
        # Start the log scanning thread
        self.scan_thread.start()
        
        try:
            while self.running:
                try:
                    # Wait for messages with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up RCA_Agent resources...")
        self.running = False
        if hasattr(self, 'scan_thread'):
            self.scan_thread.join(timeout=5)
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'client_socket'):
            self.client_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Cleanup complete")
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False
    
    def _scan_logs_loop(self):
        """Background thread that periodically scans log files"""
        logger.info("Starting log scanning loop")
        
        while self.running:
            try:
                self._scan_logs()
                self._analyze_errors()
                time.sleep(SCAN_INTERVAL)
            except Exception as e:
                logger.error(f"Error in log scanning loop: {e}")
                time.sleep(SCAN_INTERVAL)
    
    def _scan_logs(self):
        """Scan all log files in the logs directory for error patterns"""
        if not self.logs_dir.exists():
            logger.warning(f"Logs directory not found: {self.logs_dir}")
            return
        
        # Get all log files
        log_files = list(self.logs_dir.glob("*.log"))
        logger.debug(f"Found {len(log_files)} log files")
        
        # Process each log file
        for log_file in log_files:
            try:
                self._process_log_file(log_file)
            except Exception as e:
                logger.error(f"Error processing log file {log_file}: {e}")
    
    def _process_log_file(self, log_file: Path):
        """Process a single log file to find error patterns"""
        # Extract agent name from filename 
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from common.env_helpers import get_env

# Load configuration at the module level
config = load_config()(remove .log extension)
        agent_name = log_file.stem
        
        try:
            # Open the file and seek to the last position if we've read it before
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # If we've seen this file before, seek to where we left off
                if log_file in self.file_positions:
                    f.seek(self.file_positions[log_file])
                
                # Read new lines
                new_lines = f.readlines()
                
                # Update the file position for next time
                self.file_positions[log_file] = f.tell()
                
                # Process new lines
                if new_lines:
                    logger.debug(f"Processing {len(new_lines)} new lines from {log_file}")
                    self._process_log_lines(agent_name, new_lines)
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
    
    def _process_log_lines(self, agent_name: str, lines: List[str]):
        """Process log lines to find error patterns"""
        current_time = time.time()
        
        for line in lines:
            # Check each line against all error patterns
            for pattern in self.error_patterns:
                if pattern.matches(line):
                    # Record the error occurrence
                    occurrence = ErrorOccurrence(
                        agent_name=agent_name,
                        error_pattern=pattern,
                        timestamp=current_time,
                        line=line
                    )
                    self.error_occurrences.append(occurrence)
                    logger.debug(f"Found error pattern '{pattern.name}' in {agent_name}: {line.strip()}")
    
    def _analyze_errors(self):
        """Analyze error occurrences and generate recommendations"""
        current_time = time.time()
        
        # Remove old error occurrences outside the time window
        while self.error_occurrences and self.error_occurrences[0].timestamp < current_time - ERROR_WINDOW:
            self.error_occurrences.popleft()
        
        # Count errors by agent and pattern within the time window
        error_counts = defaultdict(lambda: defaultdict(int))
        for occurrence in self.error_occurrences:
            error_counts[occurrence.agent_name][occurrence.error_pattern.name] += 1
        
        # Check if any error counts exceed the threshold
        for agent_name, patterns in error_counts.items():
            for pattern_name, count in patterns.items():
                if count >= ERROR_THRESHOLD:
                    # Find the corresponding error pattern
                    pattern = next((p for p in self.error_patterns if p.name == pattern_name), None)
                    if pattern:
                        # Check if we've already sent a recommendation for this recently
                        recommendation_key = f"{agent_name}:{pattern_name}"
                        last_sent = self.sent_recommendations.get(recommendation_key, 0)
                        
                        # Only send a new recommendation if it's been at least ERROR_WINDOW seconds
                        if current_time - last_sent > ERROR_WINDOW:
                            self._send_recommendation(agent_name, pattern, count)
                            self.sent_recommendations[recommendation_key] = current_time


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to DummyArgs

        base_status.update({

            'service': 'DummyArgs',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status
    
    def _send_recommendation(self, agent_name: str, pattern: ErrorPattern, count: int):
        """Send a recommendation to the Self-Healing Agent"""
        logger.info(f"Sending recommendation for {agent_name}: {pattern.name} ({count} occurrences)")
        
        try:
            # Prepare the recommendation payload
            recommendation = {
                "action": "proactive_recommendation",
                "recommendation": pattern.recommendation,
                "target_agent": agent_name,
                "reason": f"High frequency of {pattern.name} detected ({count} occurrences in {ERROR_WINDOW/60} minutes). {pattern.description}",
                "severity": pattern.severity,
                "error_pattern": pattern.name,
                "error_count": count
            }
            
            # Send the recommendation to the Self-Healing Agent
            self.client_socket.send_json(recommendation)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.client_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5-second timeout
                response = self.client_socket.recv_json()
                logger.info(f"Received response from Self-Healing Agent: {response}")
            else:
                logger.warning("Timeout waiting for response from Self-Healing Agent")
                # Reset the socket
                self.client_socket.close()
                self.client_socket = self.context.socket(zmq.REQ)
                self.client_socket.connect(f"tcp://{self.pc2_ip}:{self.self_healing_port}")
                
        except Exception as e:
            logger.error(f"Error sending recommendation to Self-Healing Agent: {e}")
            # Reset the socket
            self.client_socket.close()
            self.client_socket = self.context.socket(zmq.REQ)
            self.client_socket.connect(f"tcp://{self.pc2_ip}:{self.self_healing_port}")



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = DummyArgs()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()