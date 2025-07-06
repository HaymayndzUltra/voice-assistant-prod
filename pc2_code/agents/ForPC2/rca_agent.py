#!/usr/bin/env python3
from typing import Dict, Any, Optional
import yaml
"""
Root Cause Analysis (RCA) Agent
-------------------------------
Analyzes log files for error patterns and provides proactive recommendations to the UnifiedErrorAgent.

Responsibilities:
- Periodically scans log files in the logs directory
- Uses regex patterns to identify common error types
- Tracks error frequency and patterns over time
- Detects when error thresholds are exceeded
- Generates error reports for the UnifiedErrorAgent
- Communicates with the UnifiedErrorAgent via standard BaseAgent methods

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
from common.core.base_agent import BaseAgent

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config utilities
from pc2_code.utils.config_loader import parse_agent_args, load_config
from pc2_code.agents.utils.config_loader import Config

# Configure logging
log_file_path = 'logs/rca_agent.log'
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

# Load PC2 specific configuration at the module level
pc2_config = Config().get_config()

# ZMQ ports - use values from pc2_config if available
RCA_AGENT_PORT = pc2_config.get('rca_agent_port', 7121)
RCA_AGENT_HEALTH_PORT = pc2_config.get('rca_agent_health_port', 8121)

# Constants
LOGS_DIR = pc2_config.get('logs_dir', "logs")
SCAN_INTERVAL = pc2_config.get('scan_interval', 60)
ERROR_WINDOW = pc2_config.get('error_window', 600)
ERROR_THRESHOLD = pc2_config.get('error_threshold', 5)

# Also load main PC configuration for cross-machine communication
main_config = load_config()

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
        self.agent_name = agent_name
        self.error_pattern = error_pattern
        self.timestamp = timestamp
        self.line = line

class RCA_Agent(BaseAgent):
    """Root Cause Analysis Agent for proactive system healing"""
    
    def __init__(self, logs_dir: str = LOGS_DIR, port: int = None, health_check_port: int = None):
        """Initialize the RCA Agent"""
        # Call BaseAgent's __init__ first
        super().__init__(name="RCA_Agent", port=port if port is not None else RCA_AGENT_PORT)
        
        self.logs_dir = Path(logs_dir)
        
        # Set up ports - use self.port from BaseAgent for main_port
        self.main_port = self.port
        self.health_port = health_check_port if health_check_port is not None else RCA_AGENT_HEALTH_PORT
        
        # Initialize data structures
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
        self.error_occurrences = deque()
        self.file_positions = {}
        self.sent_recommendations = {}
        self.running = True
        
        # Start the log scanning thread
        self.scan_thread = threading.Thread(target=self._scan_logs_loop)
        self.scan_thread.daemon = True
        
        logger.info(f"RCA_Agent initialized on port {self.main_port}")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information. Overrides BaseAgent's _get_health_status."""
        # Get base status from parent class
        base_status = super()._get_health_status()
        
        # Add RCA_Agent specific health info
        base_status.update({
            'agent': 'RCA_Agent',
            'timestamp': datetime.datetime.now().isoformat(),
            'scan_thread_alive': self.scan_thread.is_alive() if hasattr(self, 'scan_thread') else False,
            'error_patterns_count': len(self.error_patterns),
            'error_occurrences_count': len(self.error_occurrences),
            'logs_dir': str(self.logs_dir)
        })
        
        return base_status

    def _health_check(self) -> Dict[str, Any]:
        """Legacy health check method for backward compatibility."""
        return self._get_health_status()
    
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

    def _send_recommendation(self, agent_name: str, pattern: ErrorPattern, count: int):
        """Send a recommendation to the UnifiedErrorAgent"""
        logger.info(f"Sending error report for {agent_name}: {pattern.name} ({count} occurrences)")
        
        try:
            # Prepare the error report payload
            error_report = {
                "action": "report_error",
                "source": "RCA_Agent",
                "error_type": "log_pattern_detected",
                "target_agent": agent_name,
                "reason": f"High frequency of {pattern.name} detected ({count} occurrences in {ERROR_WINDOW/60} minutes). {pattern.description}",
                "severity": pattern.severity,
                "error_pattern": pattern.name,
                "error_count": count
            }
            
            # Send the error report to the UnifiedErrorAgent using BaseAgent's method
            response = self.send_request_to_agent("UnifiedErrorAgent", error_report)
            if response:
                logger.info(f"Received response from UnifiedErrorAgent: {response}")
            else:
                logger.warning("No response received from UnifiedErrorAgent")
            
        except Exception as e:
            logger.error(f"Error sending error report to UnifiedErrorAgent: {e}")

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = RCA_Agent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")