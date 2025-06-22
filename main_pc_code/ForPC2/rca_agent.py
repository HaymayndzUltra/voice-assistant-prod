#!/usr/bin/env python3
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
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from src.core.http_server import setup_health_check_server
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/rca_agent.log")
    ]
)
logger = logging.getLogger("RCA_Agent")

# Constants
LOGS_DIR = "logs"
SELF_HEALING_PORT = 5614  # Port for Self-Healing Agent on PC2
SCAN_INTERVAL = 60  # Scan logs every 60 seconds
ERROR_WINDOW = 600  # Track errors in a 10-minute window (600 seconds)
ERROR_THRESHOLD = 5  # Number of errors to trigger recommendation
PC2_IP = "192.168.100.17"  # PC2 IP address

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

class RCA_Agent:
    """Root Cause Analysis Agent for proactive system healing"""
    
    def __init__(self, logs_dir: str = LOGS_DIR, self_healing_port: int = SELF_HEALING_PORT, pc2_ip: str = PC2_IP):
        """Initialize the RCA Agent"""
        self.logs_dir = Path(logs_dir)
        self.self_healing_port = self_healing_port
        self.pc2_ip = pc2_ip
        
        # Create ZMQ context and socket for communicating with Self-Healing Agent
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.connect(f"tcp://{self.pc2_ip}:{self_healing_port}")
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

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
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
        
        self.health_server = setup_health_check_server(5586)  # or the correct port
        
        logger.info("RCA_Agent initialized")
    
    def start(self):
        """Start the RCA Agent"""
        logger.info("Starting RCA_Agent")
        self.scan_thread.start()
        
        try:
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("RCA_Agent interrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the RCA Agent"""
        logger.info("Stopping RCA_Agent")
        self.running = False
        if self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)
        self.socket.close()
        self.context.term()
    
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
        # Extract agent name from filename (remove .log extension)
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
            self.socket.send_json(recommendation)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.socket, zmq.POLLIN)
            if poller.poll(5000):  # 5-second timeout
                response = self.socket.recv_json()
                logger.info(f"Received response from Self-Healing Agent: {response}")
            else:
                logger.warning("Timeout waiting for response from Self-Healing Agent")
                # Reset the socket
                self.socket.close()
                self.socket = self.context.socket(zmq.REQ)
                self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                self.socket.connect(f"tcp://{self.pc2_ip}:{self.self_healing_port}")
                
        except Exception as e:
            logger.error(f"Error sending recommendation to Self-Healing Agent: {e}")
            # Reset the socket
            self.socket.close()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.connect(f"tcp://{self.pc2_ip}:{self.self_healing_port}")

if __name__ == "__main__":
    # Create and start the RCA Agent
    rca_agent = RCA_Agent()
    rca_agent.start() 