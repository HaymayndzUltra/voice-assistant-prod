# PHASE 3: Distributed Error Management & Self-Healing - Detailed Implementation Plan

## 1. Executive Summary

Phase 3 implements a comprehensive error management and self-healing system through a major architectural shift. This phase consolidates multiple error handling agents into a centralized SystemHealthManager while implementing a standardized "Error Bus" for system-wide error reporting.

Key achievements:
- **Centralized Error Management**: SystemHealthManager now handles all error collection, analysis, and recovery
- **Event-driven Architecture**: Error Bus using ZMQ PUB/SUB pattern enables asynchronous error reporting
- **Self-healing Capabilities**: Automated monitoring and recovery of failed components

While this represents a strategic pivot from the original Phase 0 design (where SystemDigitalTwin was central), the new architecture provides a cleaner, more scalable, and more focused approach to error handling.

## 2. Critical Functional Requirements

### 2.1 SystemHealthManager Core Functions

The SystemHealthManager must implement three core functions:
- **Passive Error Collection**: Listen to the Error Bus for reported errors
- **Proactive Monitoring**: Actively check agent health via heartbeats and log scanning
- **Automated Recovery**: Restart or repair failed components

### 2.2 Error Bus Architecture

The Error Bus must provide:
- **Standardized Error Format**: Common schema for all error messages
- **Topic-based Routing**: Errors categorized by severity and source
- **Asynchronous Communication**: "Fire-and-forget" publishing for performance
- **System-wide Accessibility**: All agents can connect and report errors

### 2.3 Client Integration Requirements

All agents in the system must:
- **Report Errors Consistently**: Use the standard error reporting interface
- **Include Sufficient Context**: Provide details needed for analysis and recovery
- **Handle Local Errors**: Implement appropriate fallbacks when errors occur
- **Send Heartbeats**: Regularly signal their health status

## 3. Implementation Steps

### 3.1 SystemHealthManager Implementation

1. **Core Infrastructure**:
   - Implement ZMQ SUB socket to listen on ERROR: topic
   - Create background threads for heartbeat monitoring and log scanning
   - Integrate with SystemDigitalTwin for service discovery

2. **Error Analysis Engine**:
   - Implement pattern matching for common error types
   - Create root cause analysis algorithms
   - Build error correlation to group related issues

3. **Recovery Mechanisms**:
   - Implement agent restart capability
   - Add configuration reload functionality
   - Create resource allocation adjustment logic
   - Implement notification system for human intervention

### 3.2 Error Bus Implementation

1. **Message Broker Setup**:
   - Configure ZMQ PUB/SUB sockets
   - Define topic structure (ERROR:, WARNING:, INFO:)
   - Implement message serialization/deserialization

2. **Error Reporting Client**:
   - Create base error reporting functions
   - Implement in RequestCoordinator and other key agents
   - Add utility functions for common error patterns

### 3.3 Client Integration

1. **BaseAgent Enhancement**:
   - Add report_error method to BaseAgent class
   - Implement heartbeat functionality
   - Create error handling decorators

2. **Adapt Existing Agents**:
   - Update RequestCoordinator to use Error Bus
   - Refactor ModelOrchestrator for error reporting
   - Update remaining agents to use new error system

## 4. Architecture Diagram

```
┌─────────────────────┐      ┌───────────────────────┐
│                     │      │                       │
│  RequestCoordinator  │◄─┐   │   ModelOrchestrator   │
│                     │  │   │                       │
└─────────┬───────────┘  │   └───────────┬───────────┘
          │              │               │
          │              │               │
          ▼              │               ▼
┌─────────────────────┐  │   ┌───────────────────────┐
│                     │  │   │                       │
│     Error Bus       │◄─┘   │     Error Bus         │
│    (ZMQ PUB)        │◄─────│     (ZMQ PUB)         │
│                     │      │                       │
└─────────┬───────────┘      └───────────────────────┘
          │
          │
          ▼
┌─────────────────────┐      ┌───────────────────────┐
│                     │      │                       │
│ SystemHealthManager │◄─────│   SystemDigitalTwin    │
│    (ZMQ SUB)        │      │                       │
│                     │      │                       │
└─────────┬───────────┘      └───────────────────────┘
          │
          │
          ▼
┌─────────────────────┐
│                     │
│  Recovery Actions   │
│                     │
└─────────────────────┘
```

## 5. Critical Logic Reference

### 5.1 SystemHealthManager Core Components

```python
# Consolidated from UnifiedErrorAgent, RCA_Agent, and SelfHealingAgent
class SystemHealthManager(BaseAgent):
    def __init__(self, config_path=None):
        super().__init__("system_health_manager", config_path)
        self.error_bus_address = self.config.get("error_bus_address", "tcp://127.0.0.1:5600")
        self.digital_twin_address = self.config.get("digital_twin_address", "tcp://127.0.0.1:5555")
        self.log_dir = self.config.get("log_dir", "../logs")
        self.scan_interval = self.config.get("scan_interval", 60)  # seconds
        self.heartbeat_timeout = self.config.get("heartbeat_timeout", 120)  # seconds
        
        # Initialize components
        self._setup_error_bus_listener()
        self._setup_digital_twin_connection()
        self._setup_heartbeat_monitor()
        self._setup_log_scanner()
        
        # Error patterns database
        self.error_patterns = self._load_error_patterns()
        
        # Recovery history to avoid infinite restart loops
        self.recovery_history = {}
        
        # Start background threads
        self._start_background_threads()
    
    def _setup_error_bus_listener(self):
        """Setup ZMQ SUB socket to listen to the Error Bus"""
        self.error_bus_socket = self.context.socket(zmq.SUB)
        self.error_bus_socket.connect(self.error_bus_address)
        self.error_bus_socket.setsockopt_string(zmq.SUBSCRIBE, "ERROR:")
        self.error_bus_socket.setsockopt_string(zmq.SUBSCRIBE, "WARNING:")
        self.logger.info(f"Connected to Error Bus at {self.error_bus_address}")
    
    def _setup_digital_twin_connection(self):
        """Connect to SystemDigitalTwin for service discovery"""
        self.digital_twin_client = DigitalTwinClient(self.digital_twin_address)
        self.logger.info(f"Connected to Digital Twin at {self.digital_twin_address}")
    
    def _listen_error_bus_loop(self):
        """Background thread to listen for error messages on the Error Bus"""
        self.logger.info("Starting Error Bus listener thread")
        while self.running:
            try:
                if self.error_bus_socket.poll(1000):
                    topic, message = self.error_bus_socket.recv_multipart()
                    error_data = json.loads(message.decode('utf-8'))
                    self.logger.debug(f"Received on {topic.decode('utf-8')}: {error_data}")
                    self._process_error_message(topic.decode('utf-8'), error_data)
            except Exception as e:
                self.logger.error(f"Error in Error Bus listener: {str(e)}")
                time.sleep(1)  # Prevent tight loop if something goes wrong
    
    def _process_error_message(self, topic, error_data):
        """Process an incoming error message"""
        try:
            # Extract error information
            source = error_data.get("source", "unknown")
            error_type = error_data.get("type", "unknown")
            severity = error_data.get("severity", "medium")
            message = error_data.get("message", "")
            timestamp = error_data.get("timestamp", datetime.now().isoformat())
            
            # Log the error
            self.logger.info(f"Processing error from {source}: {error_type} - {message}")
            
            # Perform root cause analysis
            root_cause = self._analyze_root_cause(source, error_type, message)
            
            # Determine and execute recovery action
            self._execute_recovery_action(source, error_type, root_cause, severity)
            
        except Exception as e:
            self.logger.error(f"Error processing error message: {str(e)}")
    
    def _analyze_root_cause(self, source, error_type, message):
        """Analyze the root cause of an error using pattern matching"""
        for pattern in self.error_patterns:
            if re.search(pattern["regex"], message):
                return {
                    "cause": pattern["cause"],
                    "confidence": pattern["confidence"],
                    "recommended_action": pattern["action"]
                }
        
        # No matching pattern found, use generic response
        return {
            "cause": "Unknown",
            "confidence": 0.3,
            "recommended_action": "restart" if error_type in ["crash", "timeout"] else "monitor"
        }
    
    def _execute_recovery_action(self, source, error_type, root_cause, severity):
        """Execute a recovery action based on the error and root cause analysis"""
        # Check if we've tried to recover this agent too many times recently
        if self._check_recovery_throttle(source):
            self.logger.warning(f"Recovery for {source} throttled due to too many recent attempts")
            return False
            
        action = root_cause["recommended_action"]
        
        if action == "restart" and severity in ["high", "critical"]:
            return self._restart_agent(source)
        elif action == "reload_config":
            return self._reload_agent_config(source)
        elif action == "notify":
            return self._send_notification(source, error_type, root_cause["cause"])
        else:  # "monitor" or unknown action
            self.logger.info(f"Monitoring {source} for further errors")
            return True
    
    def _restart_agent(self, agent_name):
        """Restart an agent using SystemDigitalTwin to find its details"""
        try:
            # Get agent details from Digital Twin
            agent_info = self.digital_twin_client.get_agent_info(agent_name)
            
            if not agent_info or "script_path" not in agent_info:
                self.logger.error(f"Cannot restart {agent_name}: No script path found")
                return False
            
            script_path = agent_info["script_path"]
            
            # Record this recovery attempt
            self._record_recovery_attempt(agent_name)
            
            # Execute the restart command
            self.logger.info(f"Restarting {agent_name} using script: {script_path}")
            result = subprocess.run(["python", script_path], 
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Successfully restarted {agent_name}")
                return True
            else:
                self.logger.error(f"Failed to restart {agent_name}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restarting {agent_name}: {str(e)}")
            return False
            
    def _heartbeat_monitor_loop(self):
        """Background thread that monitors agent heartbeats"""
        self.logger.info("Starting heartbeat monitor thread")
        while self.running:
            try:
                # Get list of all agents from Digital Twin
                agents = self.digital_twin_client.list_agents()
                
                for agent in agents:
                    # Skip ourselves
                    if agent["name"] == self.name:
                        continue
                        
                    # Check last heartbeat time
                    last_heartbeat = agent.get("last_heartbeat")
                    if not last_heartbeat:
                        continue
                        
                    # Parse the timestamp
                    try:
                        last_time = datetime.fromisoformat(last_heartbeat)
                        now = datetime.now()
                        
                        # Check if heartbeat is older than timeout
                        if (now - last_time).total_seconds() > self.heartbeat_timeout:
                            self.logger.warning(f"Agent {agent['name']} missed heartbeats. Last: {last_heartbeat}")
                            
                            # Report this as an error and handle it
                            error_data = {
                                "source": agent["name"],
                                "type": "heartbeat_timeout",
                                "severity": "high",
                                "message": f"Agent missed heartbeats for {self.heartbeat_timeout} seconds",
                                "timestamp": now.isoformat()
                            }
                            self._process_error_message("ERROR:", error_data)
                    except Exception as e:
                        self.logger.error(f"Error parsing heartbeat for {agent['name']}: {str(e)}")
                
                # Sleep until next check
                time.sleep(self.scan_interval)
                        
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {str(e)}")
                time.sleep(10)  # Prevent tight loop if something goes wrong
    
    def _scan_logs_loop(self):
        """Background thread that scans log files for error patterns"""
        self.logger.info("Starting log scanner thread")
        
        # Keep track of processed log lines
        self.last_processed_position = {}
        
        while self.running:
            try:
                # Get all log files
                log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
                
                for log_file in log_files:
                    self._scan_single_log(log_file)
                    
                # Sleep until next scan
                time.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Error in log scanner: {str(e)}")
                time.sleep(10)  # Prevent tight loop if something goes wrong
    
    def _scan_single_log(self, log_file):
        """Scan a single log file for error patterns"""
        try:
            file_size = os.path.getsize(log_file)
            last_position = self.last_processed_position.get(log_file, 0)
            
            # Skip if no new content
            if file_size <= last_position:
                return
                
            # File was truncated or rotated, start from beginning
            if file_size < last_position:
                last_position = 0
            
            with open(log_file, 'r') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                
                # Update processed position
                self.last_processed_position[log_file] = f.tell()
                
                # Extract agent name from log filename
                agent_name = os.path.basename(log_file).split('.')[0]
                
                # Scan for error patterns
                for line in new_lines:
                    if "ERROR" in line or "CRITICAL" in line:
                        self.logger.debug(f"Found error in {agent_name} log: {line.strip()}")
                        
                        # Generate error message
                        error_data = {
                            "source": agent_name,
                            "type": "log_error",
                            "severity": "high" if "CRITICAL" in line else "medium",
                            "message": line.strip(),
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Process as if it came from the Error Bus
                        self._process_error_message("ERROR:", error_data)
        
        except Exception as e:
            self.logger.error(f"Error scanning log file {log_file}: {str(e)}")
```

### 5.2 Error Bus Client Implementation

```python
# Error reporting implementation for BaseAgent
def report_error(self, error_type, message, severity="medium", context=None):
    """
    Report an error to the Error Bus.
    
    Args:
        error_type: Type of error (e.g., "network", "timeout", "crash")
        message: Error message
        severity: One of "low", "medium", "high", "critical"
        context: Additional context information (dict)
    """
    try:
        # Lazy initialization of error bus socket
        if not hasattr(self, 'error_bus_socket'):
            self._initialize_error_bus()
            
        # Prepare error message
        error_data = {
            "source": self.name,
            "type": error_type,
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        # Determine topic based on severity
        if severity in ["critical", "high"]:
            topic = "ERROR:"
        elif severity == "medium":
            topic = "WARNING:"
        else:
            topic = "INFO:"
            
        # Send to Error Bus
        self.error_bus_socket.send_multipart([
            topic.encode('utf-8'),
            json.dumps(error_data).encode('utf-8')
        ])
        
        # Also log locally
        log_method = self.logger.error if severity in ["critical", "high"] else self.logger.warning
        log_method(f"{error_type}: {message}")
        
        return True
        
    except Exception as e:
        # Fallback to local logging if Error Bus fails
        self.logger.error(f"Failed to report error to Error Bus: {str(e)}")
        self.logger.error(f"Original error - {error_type}: {message}")
        return False
        
def _initialize_error_bus(self):
    """Initialize connection to the Error Bus"""
    try:
        # Get Error Bus address from config
        error_bus_address = self.config.get(
            "error_bus_address", 
            "tcp://127.0.0.1:5600"
        )
        
        # Create PUB socket
        self.error_bus_socket = self.context.socket(zmq.PUB)
        self.error_bus_socket.connect(error_bus_address)
        
        # Allow time for connection to establish
        time.sleep(0.1)
        
        self.logger.info(f"Connected to Error Bus at {error_bus_address}")
        
    except Exception as e:
        self.logger.error(f"Failed to initialize Error Bus connection: {str(e)}")
```

### 5.3 Error Handling Decorator

```python
# Error handling decorator for agent methods
def handle_errors(func):
    """
    Decorator for agent methods to catch and report errors.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            # Extract error information
            error_type = e.__class__.__name__
            message = str(e)
            
            # Determine severity based on error type
            severity = "high" if error_type in ["ConnectionError", "TimeoutError"] else "medium"
            
            # Get additional context
            context = {
                "function": func.__name__,
                "args": str(args),
                "traceback": traceback.format_exc()
            }
            
            # Report the error
            self.report_error(error_type, message, severity, context)
            
            # Re-raise or return a default value based on the agent's config
            error_behavior = self.config.get("error_behavior", "raise")
            
            if error_behavior == "raise":
                raise
            elif error_behavior == "default":
                return self.config.get("default_return_value", None)
            else:
                return None
                
    return wrapper
```

### 5.4 RequestCoordinator Error Integration

```python
# Implementing error reporting in RequestCoordinator
def process_request(self, request_data):
    """
    Process an incoming request.
    """
    try:
        # Validate request data
        if not self._validate_request(request_data):
            self.report_error("invalid_request", 
                             f"Invalid request format: {request_data}",
                             severity="low")
            return {"status": "error", "message": "Invalid request format"}
            
        # Route the request based on type
        request_type = request_data.get("type", "text")
        
        if request_type == "text":
            result = self._process_text(request_data)
        elif request_type == "audio":
            result = self._process_audio(request_data)
        elif request_type == "image":
            result = self._process_image(request_data)
        else:
            self.report_error("unsupported_request_type", 
                             f"Unsupported request type: {request_type}",
                             severity="low")
            return {"status": "error", "message": f"Unsupported request type: {request_type}"}
            
        return result
        
    except ConnectionError as e:
        # Network error connecting to another agent
        self.report_error("connection_error", 
                         str(e),
                         severity="high",
                         context={"request_data": request_data})
        return {"status": "error", "message": "Connection error", "error_type": "connection"}
        
    except TimeoutError as e:
        # Timeout waiting for another agent
        self.report_error("timeout_error", 
                         str(e),
                         severity="high",
                         context={"request_data": request_data})
        return {"status": "error", "message": "Request timed out", "error_type": "timeout"}
        
    except Exception as e:
        # Unexpected error
        self.report_error("unexpected_error", 
                         str(e),
                         severity="critical",
                         context={"request_data": request_data, 
                                 "traceback": traceback.format_exc()})
        return {"status": "error", "message": "Internal server error"}
```

## 6. File Structure Updates

The following files need to be created or modified:

```
pc2_code/
  agents/
    system_health_manager.py      (new - core health monitoring agent)
  
common/
  core/
    base_agent.py                (modified - add error reporting)
  utils/
    error_models.py              (new - Pydantic models for errors)
    
main_pc_code/
  agents/
    request_coordinator.py       (modified - integrate error reporting)
    model_orchestrator.py        (modified - integrate error reporting)
    goal_manager.py              (modified - integrate error reporting)
```

## 7. Configuration Updates

The following configuration files must be updated:

1. **pc2_code/config/system_health_config.yaml** (new file):
   - Error Bus address
   - Digital Twin address
   - Scan intervals and timeouts
   - Error patterns database

2. **pc2_code/config/startup_config.yaml**:
   - Add SystemHealthManager configuration

3. **main_pc_code/config/startup_config.yaml**:
   - Add Error Bus configuration

## 8. Improvement Recommendations

### 8.1 Address Single Point of Failure (SPOF)

The current implementation creates a potential single point of failure with SystemHealthManager. To address this:

1. **High Availability Mode**:
   - Implement a standby SystemHealthManager that can take over if primary fails
   - Use leader election algorithm to determine active instance
   - Share recovery history across instances

2. **Self-Monitoring**:
   - Add a simple "watchdog" process that can restart SystemHealthManager itself
   - Implement basic self-diagnosis capabilities

### 8.2 Improve Error Bus Reliability

The current ZMQ PUB/SUB implementation doesn't guarantee message delivery. To improve reliability:

1. **Message Persistence**:
   - Add a disk-backed queue for critical error messages
   - Implement message acknowledgment for critical errors

2. **Consider Alternative Brokers**:
   - Evaluate RabbitMQ or NATS for critical error messages
   - Maintain ZMQ for non-critical errors where performance matters

### 8.3 Implement Traffic Management

To prevent "noisy neighbor" problems:

1. **Rate Limiting**:
   - Add per-agent rate limits for error messages
   - Implement exponential backoff for repeated errors

2. **Error Deduplication**:
   - Group similar errors from the same source
   - Implement intelligent suppression of repeated errors

## 9. Testing Strategy

### 9.1 Unit Testing
- Test error reporting functions with mock Error Bus
- Test pattern matching and root cause analysis
- Validate recovery actions with mocked environment

### 9.2 Integration Testing
- Test error propagation from agents to SystemHealthManager
- Verify correct recovery actions based on error types
- Test log scanning and heartbeat monitoring

### 9.3 Chaos Testing
- Deliberately crash agents to test recovery
- Simulate network partitions
- Test under high error message load

## 10. Future Enhancements

For future phases, consider:

1. **Machine Learning for RCA**:
   - Train models to identify error patterns
   - Implement predictive failure detection

2. **Advanced Recovery Strategies**:
   - Gradual resource allocation adjustments
   - Advanced dependency analysis for cascading failures

3. **Visualization Dashboard**:
   - Real-time error monitoring UI
   - Historical error analysis
   - System health visualization 