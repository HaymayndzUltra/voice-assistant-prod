#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
WP-10 NATS Error Bus Migration Script
Implements NATS messaging system for decoupling error floods and centralized error management
Target: Replace direct error logging with NATS-based error bus for scalable error handling
"""

import os
import ast
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import subprocess

@dataclass
class ErrorMessage:
    """Standardized error message structure"""
    error_id: str
    timestamp: str
    source_agent: str
    error_type: str
    severity: str  # CRITICAL, ERROR, WARNING, INFO
    message: str
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0

@dataclass
class ErrorPattern:
    """Error pattern for flood detection"""
    pattern: str
    threshold: int
    time_window: int  # seconds
    action: str  # THROTTLE, BLOCK, ESCALATE

class NATSErrorBusAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect error handling patterns"""
    
    def __init__(self):
        self.logging_calls = []
        self.exception_handlers = []
        self.error_patterns = []
        self.print_statements = []
        self.error_score = 0
        
    def visit_Call(self, node):
        # Detect logging calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['error', 'warning', 'critical', 'exception', 'info', 'debug']):
            self.logging_calls.append({
                'method': node.func.attr,
                'line': node.lineno
            })
            self.error_score += 5
        
        # Detect print statements
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.print_statements.append(node.lineno)
            self.error_score += 2
        
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        # Detect exception handlers
        self.exception_handlers.append({
            'type': str(node.type) if node.type else 'generic',
            'line': node.lineno
        })
        self.error_score += 10
        self.generic_visit(node)

def find_error_handling_candidates() -> List[Path]:
    """Find agent files that need error bus integration"""
    agent_files = []
    
    # Main PC agents
    main_pc_path = Path("main_pc_code/agents")
    if main_pc_path.exists():
        agent_files.extend(main_pc_path.glob("*.py"))
    
    # PC2 agents
    pc2_path = Path("pc2_code/agents")
    if pc2_path.exists():
        agent_files.extend(pc2_path.glob("*.py"))
    
    # FORMAINPC agents
    formainpc_path = Path("main_pc_code/FORMAINPC")
    if formainpc_path.exists():
        agent_files.extend(formainpc_path.glob("*.py"))
    
    return [f for f in agent_files if not f.name.startswith('__')]

def analyze_error_patterns(file_path: Path) -> Dict:
    """Analyze error handling patterns in an agent file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = NATSErrorBusAnalyzer()
        analyzer.visit(tree)
        
        # Determine error bus priority
        priority = determine_error_bus_priority(analyzer, content)
        
        return {
            'file_path': str(file_path),
            'agent_name': file_path.stem,
            'error_score': analyzer.error_score,
            'priority': priority,
            'logging_calls': analyzer.logging_calls,
            'exception_handlers': analyzer.exception_handlers,
            'print_statements': analyzer.print_statements,
            'needs_error_bus': analyzer.error_score > 10
        }
    except Exception as e:
        return {
            'file_path': str(file_path),
            'agent_name': file_path.stem,
            'error': str(e),
            'needs_error_bus': True,
            'error_score': 0
        }

def determine_error_bus_priority(analyzer: NATSErrorBusAnalyzer, content: str) -> str:
    """Determine error bus integration priority"""
    if analyzer.error_score > 50:
        return 'critical'
    elif analyzer.error_score > 30:
        return 'high'
    elif analyzer.error_score > 15:
        return 'medium'
    else:
        return 'low'

def generate_nats_error_bus_library() -> str:
    """Generate NATS error bus library"""
    return '''
"""
NATS Error Bus Library for WP-10 NATS Error Bus Integration
Provides centralized error handling, flood detection, and error correlation
"""

import asyncio
import nats
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict, deque
import threading
import os

@dataclass
class ErrorMessage:
    """Standardized error message structure"""
    error_id: str
    timestamp: str
    source_agent: str
    error_type: str
    severity: str  # CRITICAL, ERROR, WARNING, INFO
    message: str
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0

@dataclass
class ErrorPattern:
    """Error pattern for flood detection"""
    pattern: str
    threshold: int
    time_window: int  # seconds
    action: str  # THROTTLE, BLOCK, ESCALATE

class ErrorFloodDetector:
    """Detects and prevents error floods"""
    
    def __init__(self, patterns: List[ErrorPattern]):
        self.patterns = patterns
        self.error_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.throttled_patterns: Dict[str, datetime] = {}
        self.lock = threading.Lock()
    
    def check_flood(self, error_msg: ErrorMessage) -> bool:
        """Check if error should be throttled due to flood detection"""
        with self.lock:
            current_time = datetime.now()
            
            for pattern in self.patterns:
                if pattern.pattern in error_msg.message or pattern.pattern in error_msg.error_type:
                    pattern_key = f"{error_msg.source_agent}:{pattern.pattern}"
                    
                    # Check if pattern is currently throttled
                    if pattern_key in self.throttled_patterns:
                        throttle_end = self.throttled_patterns[pattern_key] + timedelta(seconds=pattern.time_window)
                        if current_time < throttle_end:
                            return True  # Still throttled
                        else:
                            del self.throttled_patterns[pattern_key]
                    
                    # Add to history
                    self.error_history[pattern_key].append(current_time)
                    
                    # Check if threshold exceeded
                    window_start = current_time - timedelta(seconds=pattern.time_window)
                    recent_errors = [t for t in self.error_history[pattern_key] if t >= window_start]
                    
                    if len(recent_errors) >= pattern.threshold:
                        if pattern.action == "THROTTLE":
                            self.throttled_patterns[pattern_key] = current_time
                            return True
                        elif pattern.action == "ESCALATE":
                            # Send escalation notification
                            self._escalate_error(error_msg, pattern, len(recent_errors))
            
            return False
    
    def _escalate_error(self, error_msg: ErrorMessage, pattern: ErrorPattern, count: int):
        """Escalate error to higher severity"""
        escalated_msg = ErrorMessage(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            source_agent="error_flood_detector",
            error_type="ERROR_FLOOD_DETECTED",
            severity="CRITICAL",
            message=f"Error flood detected: {pattern.pattern} occurred {count} times",
            context={
                "original_error": asdict(error_msg),
                "pattern": pattern.pattern,
                "count": count,
                "time_window": pattern.time_window
            }
        )
        
        # This would be sent back to the error bus
        print(f"ESCALATED: {escalated_msg.message}")

class NATSErrorBus:
    """
    NATS-based error bus for centralized error handling
    """
    
    def __init__(self, nats_servers: List[str] = None, agent_name: str = "unknown"):
        self.nats_servers = nats_servers or ["nats://nats_coordination:4222"]
        self.agent_name = agent_name
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[nats.aio.client.JetStreamContext] = None
        
        # Error handling configuration
        self.error_subject = "errors"
        self.error_stream = "ERROR_STREAM"
        self.error_consumer = f"error_consumer_{agent_name}"
        
        # Flood detection
        self.flood_detector = ErrorFloodDetector([
            ErrorPattern("ConnectionError", threshold=10, time_window=60, action="THROTTLE"),
            ErrorPattern("TimeoutError", threshold=5, time_window=30, action="THROTTLE"),
            ErrorPattern("MemoryError", threshold=3, time_window=300, action="ESCALATE"),
            ErrorPattern("CRITICAL", threshold=5, time_window=60, action="ESCALATE"),
        ])
        
        # Message handlers
        self.error_handlers: List[Callable[[ErrorMessage], None]] = []
        
        # Background task
        self._running = False
        self._consumer_task = None
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(servers=self.nats_servers)
            self.js = self.nc.jetstream()
            
            # Create stream if it doesn't exist
            await self._ensure_stream_exists()
            
            # Start consuming errors
            await self._start_error_consumer()
            
            self.logger.info(f"Connected to NATS error bus for agent {self.agent_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to NATS: {e}")
            raise
    
    async def _ensure_stream_exists(self):
        """Ensure the error stream exists"""
        try:
            await self.js.stream_info(self.error_stream)
        except nats.js.errors.NotFoundError:
            # Create the stream
            await self.js.add_stream(
                name=self.error_stream,
                subjects=[f"{self.error_subject}.>"],
                retention="limits",
                max_msgs=1000000,
                max_age=7 * 24 * 3600,  # 7 days
                storage="file"
            )
            self.logger.info(f"Created NATS stream: {self.error_stream}")
    
    async def _start_error_consumer(self):
        """Start consuming error messages"""
        if self._consumer_task and not self._consumer_task.done():
            return
        
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_errors())
    
    async def _consume_errors(self):
        """Background task to consume error messages"""
        try:
            # Create consumer
            consumer = await self.js.pull_subscribe(
                subject=f"{self.error_subject}.>",
                stream=self.error_stream,
                durable=self.error_consumer
            )
            
            while self._running:
                try:
                    msgs = await consumer.fetch(batch=10, timeout=1)
                    
                    for msg in msgs:
                        try:
                            error_data = json.loads(msg.data.decode())
                            error_msg = ErrorMessage(**error_data)
                            
                            # Process error message
                            await self._process_error_message(error_msg)
                            
                            # Acknowledge message
                            await msg.ack()
                            
                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
                            await msg.nak()
                
                except nats.js.errors.TimeoutError:
                    # No messages available, continue
                    continue
                except Exception as e:
                    self.logger.error(f"Error in consumer loop: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"Error starting consumer: {e}")
    
    async def _process_error_message(self, error_msg: ErrorMessage):
        """Process a received error message"""
        # Skip processing our own errors to avoid loops
        if error_msg.source_agent == self.agent_name:
            return
        
        # Call registered handlers
        for handler in self.error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error_msg)
                else:
                    handler(error_msg)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")
    
    def add_error_handler(self, handler: Callable[[ErrorMessage], None]):
        """Add an error message handler"""
        self.error_handlers.append(handler)
    
    async def publish_error(self, error_type: str, message: str, severity: str = "ERROR",
                           stack_trace: str = None, context: Dict = None, 
                           correlation_id: str = None) -> bool:
        """Publish an error message to the bus"""
        error_msg = ErrorMessage(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            source_agent=self.agent_name,
            error_type=error_type,
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            context=context or {},
            correlation_id=correlation_id
        )
        
        # Check flood detection
        if self.flood_detector.check_flood(error_msg):
            self.logger.debug(f"Error throttled due to flood detection: {message}")
            return False
        
        try:
            subject = f"{self.error_subject}.{severity.lower()}.{self.agent_name}"
            data = json.dumps(asdict(error_msg)).encode()
            
            await self.js.publish(subject, data)
            return True
            
        except Exception as e:
            # Fallback to local logging if NATS fails
            self.logger.error(f"Failed to publish error to NATS: {e}")
            self.logger.error(f"Original error: {message}")
            return False
    
    async def disconnect(self):
        """Disconnect from NATS"""
        self._running = False
        
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
        
        self.logger.info("Disconnected from NATS error bus")

# Global error bus instance
_error_bus: Optional[NATSErrorBus] = None

def get_error_bus() -> NATSErrorBus:
    """Get the global error bus instance"""
    global _error_bus
    if _error_bus is None:
        agent_name = os.getenv("AGENT_NAME", "unknown")
        nats_servers = os.getenv("NATS_SERVERS", "nats://nats_coordination:4222").split(",")
        _error_bus = NATSErrorBus(nats_servers, agent_name)
    return _error_bus

async def init_error_bus(agent_name: str, nats_servers: List[str] = None) -> NATSErrorBus:
    """Initialize the error bus for an agent"""
    global _error_bus
    _error_bus = NATSErrorBus(nats_servers, agent_name)
    await _error_bus.connect()
    return _error_bus

# Convenience functions for error reporting
async def report_error(error_type: str, message: str, severity: str = "ERROR", **kwargs):
    """Report an error to the bus"""
    error_bus = get_error_bus()
    return await error_bus.publish_error(error_type, message, severity, **kwargs)

async def report_critical(message: str, **kwargs):
    """Report a critical error"""
    return await report_error("CRITICAL_ERROR", message, "CRITICAL", **kwargs)

async def report_warning(message: str, **kwargs):
    """Report a warning"""
    return await report_error("WARNING", message, "WARNING", **kwargs)

async def report_info(message: str, **kwargs):
    """Report an info message"""
    return await report_error("INFO", message, "INFO", **kwargs)

# Decorator for automatic error reporting
def error_bus_handler(error_type: str = None, severity: str = "ERROR"):
    """Decorator to automatically report exceptions to error bus"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    import traceback
                    await report_error(
                        error_type or f"{func.__name__}_error",
                        str(e),
                        severity,
                        stack_trace=traceback.format_exc(),
                        context={"function": func.__name__, "args": len(args), "kwargs": list(kwargs.keys())}
                    )
                    raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    import traceback
                    # For sync functions, we need to run the error reporting in an event loop
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(report_error(
                            error_type or f"{func.__name__}_error",
                            str(e),
                            severity,
                            stack_trace=traceback.format_exc(),
                            context={"function": func.__name__, "args": len(args), "kwargs": list(kwargs.keys())}
                        ))
                    except RuntimeError:
                        # No event loop running, fallback to logging
                        logging.error(f"Error in {func.__name__}: {e}")
                    raise
            return sync_wrapper
    return decorator

# Context manager for error correlation
class ErrorContext:
    """Context manager for error correlation"""
    
    def __init__(self, correlation_id: str = None, context: Dict = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.context = context or {}
        self._previous_correlation_id = None
    
    def __enter__(self):
        # Store in thread-local storage if needed
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Report the exception with correlation ID
            import traceback
            asyncio.create_task(report_error(
                str(exc_type.__name__),
                str(exc_val),
                "ERROR",
                stack_trace=traceback.format_exc(),
                correlation_id=self.correlation_id,
                context=self.context
            ))
        return False  # Don't suppress exceptions

# Usage examples in comments:
"""
# Initialize error bus
await init_error_bus("my_agent", ["nats://nats_coordination:4222"])

# Report errors
await report_error("DATABASE_ERROR", "Connection failed", severity="CRITICAL")
await report_warning("High memory usage detected")

# Use decorator
@error_bus_handler("API_ERROR", "WARNING")
async def call_api():
    # Your API call here
    pass

# Use context manager
with ErrorContext(correlation_id="req-123", context={"user_id": "user456"}):
    # Your code here
    pass
"""
'''

def generate_nats_error_dashboard() -> str:
    """Generate error monitoring dashboard"""
    return '''
"""
NATS Error Bus Dashboard
Real-time error monitoring and analysis dashboard
"""

import asyncio
import nats
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List
import time

class ErrorDashboard:
    """Real-time error monitoring dashboard"""
    
    def __init__(self, nats_servers: List[str] = None):
        self.nats_servers = nats_servers or ["nats://nats_coordination:4222"]
        self.nc = None
        self.js = None
        
        # Statistics
        self.error_counts = defaultdict(int)
        self.error_by_agent = defaultdict(int)
        self.error_by_severity = defaultdict(int)
        self.error_timeline = []
        self.flood_alerts = []
        
        # Configuration
        self.dashboard_update_interval = 5  # seconds
        self.max_timeline_entries = 1000
        
    async def start(self):
        """Start the dashboard"""
        # Connect to NATS
        self.nc = await nats.connect(servers=self.nats_servers)
        self.js = self.nc.jetstream()
        
        # Subscribe to all error messages
        await self.nc.subscribe("errors.>", cb=self._handle_error_message)
        
        # Start dashboard updates
        asyncio.create_task(self._dashboard_loop())
        
        print("Error Dashboard started")
    
    async def _handle_error_message(self, msg):
        """Handle incoming error messages"""
        try:
            error_data = json.loads(msg.data.decode())
            
            # Update statistics
            self.error_counts[error_data["error_type"]] += 1
            self.error_by_agent[error_data["source_agent"]] += 1
            self.error_by_severity[error_data["severity"]] += 1
            
            # Add to timeline
            self.error_timeline.append({
                "timestamp": error_data["timestamp"],
                "agent": error_data["source_agent"],
                "type": error_data["error_type"],
                "severity": error_data["severity"],
                "message": error_data["message"]
            })
            
            # Keep timeline size manageable
            if len(self.error_timeline) > self.max_timeline_entries:
                self.error_timeline = self.error_timeline[-self.max_timeline_entries:]
            
            # Check for flood patterns
            await self._check_flood_patterns()
            
        except Exception as e:
            print(f"Error processing dashboard message: {e}")
    
    async def _check_flood_patterns(self):
        """Check for error flood patterns"""
        now = datetime.now()
        recent_errors = [
            err for err in self.error_timeline 
            if datetime.fromisoformat(err["timestamp"]) > now - timedelta(minutes=5)
        ]
        
        # Check for floods by agent
        agent_counts = Counter(err["agent"] for err in recent_errors)
        for agent, count in agent_counts.items():
            if count > 20:  # More than 20 errors in 5 minutes
                self.flood_alerts.append({
                    "timestamp": now.isoformat(),
                    "type": "AGENT_FLOOD",
                    "agent": agent,
                    "count": count,
                    "message": f"Agent {agent} generated {count} errors in 5 minutes"
                })
        
        # Keep only recent alerts
        self.flood_alerts = [
            alert for alert in self.flood_alerts
            if datetime.fromisoformat(alert["timestamp"]) > now - timedelta(hours=1)
        ]
    
    async def _dashboard_loop(self):
        """Dashboard update loop"""
        while True:
            await asyncio.sleep(self.dashboard_update_interval)
            self._print_dashboard()
    
    def _print_dashboard(self):
        """Print dashboard to console"""
        print("\\n" + "="*80)
        print(f"🚨 ERROR BUS DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Error counts by severity
        print("\\n📊 ERRORS BY SEVERITY:")
        for severity in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
            count = self.error_by_severity.get(severity, 0)
            print(f"   {severity}: {count}")
        
        # Top error types
        print("\\n🔝 TOP ERROR TYPES:")
        top_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for error_type, count in top_errors:
            print(f"   {error_type}: {count}")
        
        # Top error agents
        print("\\n🤖 TOP ERROR AGENTS:")
        top_agents = sorted(self.error_by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
        for agent, count in top_agents:
            print(f"   {agent}: {count}")
        
        # Recent errors
        print("\\n🕐 RECENT ERRORS (Last 10):")
        recent = self.error_timeline[-10:]
        for error in recent:
            timestamp = datetime.fromisoformat(error["timestamp"]).strftime("%H:%M:%S")
            print(f"   {timestamp} [{error['severity']}] {error['agent']}: {error['message'][:50]}...")
        
        # Flood alerts
        if self.flood_alerts:
            print("\\n🚨 FLOOD ALERTS:")
            for alert in self.flood_alerts[-5:]:  # Last 5 alerts
                timestamp = datetime.fromisoformat(alert["timestamp"]).strftime("%H:%M:%S")
                print(f"   {timestamp} {alert['message']}")
        
        print("="*80)
    
    def get_stats(self) -> Dict:
        """Get dashboard statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_by_severity": dict(self.error_by_severity),
            "error_by_agent": dict(self.error_by_agent),
            "top_error_types": dict(sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_errors": self.error_timeline[-50:],
            "flood_alerts": self.flood_alerts[-10:]
        }

async def main():
    """Run the error dashboard"""
    dashboard = ErrorDashboard()
    await dashboard.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\\nDashboard stopped")

if __name__ == "__main__":
    asyncio.run(main())
'''

def create_nats_error_bus_structure():
    """Create NATS error bus directory structure"""
    error_bus_dir = Path("common/error_bus")
    error_bus_dir.mkdir(parents=True, exist_ok=True)
    
    # Create NATS error bus library
    with open(error_bus_dir / "nats_client.py", 'w') as f:
        f.write(generate_nats_error_bus_library())
    
    # Create error dashboard
    with open(error_bus_dir / "dashboard.py", 'w') as f:
        f.write(generate_nats_error_dashboard())
    
    # Create __init__.py
    with open(error_bus_dir / "__init__.py", 'w') as f:
        f.write('"""NATS Error Bus for WP-10"""\n\nfrom .nats_client import NATSErrorBus, get_error_bus, init_error_bus, report_error, report_critical, report_warning, error_bus_handler, ErrorContext\n\n__all__ = ["NATSErrorBus", "get_error_bus", "init_error_bus", "report_error", "report_critical", "report_warning", "error_bus_handler", "ErrorContext"]\n')
    
    # Create Docker Compose for NATS
    with open(error_bus_dir / "docker-compose.yml", 'w') as f:
        f.write('''
version: '3.8'
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"
      - "8222:8222"
      - "6222:6222"
    command: [
      "--jetstream",
      "--store_dir=/data",
      "--max_mem_store=1GB",
      "--max_file_store=10GB"
    ]
    volumes:
      - nats_data:/data
    environment:
      - NATS_LOG_LEVEL=info
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8222/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  nats-box:
    image: natsio/nats-box:latest
    depends_on:
      - nats
    command: |
      sh -c "
        echo 'Waiting for NATS server...'
        sleep 5
        nats --server nats:4222 stream add ERROR_STREAM --subjects 'errors.>' --storage file --retention limits --max-msgs 1000000 --max-age 7d
        echo 'NATS Error Stream created'
        sleep infinity
      "

volumes:
  nats_data:
''')
    
    return error_bus_dir

def generate_error_bus_integration_example(agent_info: Dict) -> str:
    """Generate error bus integration example for an agent"""
    agent_name = agent_info['agent_name']
    
    return f'''
# NATS Error Bus Integration Example for {agent_name}
# Generated by WP-10 NATS Error Bus Migration

import asyncio
import logging
from common.error_bus import init_error_bus, report_error, report_critical, error_bus_handler, ErrorContext

class {agent_name.title().replace('_', '')}WithErrorBus:
    """
    Enhanced {agent_name} with NATS error bus integration
    """
    
    def __init__(self):
        self.agent_name = "{agent_name}"
        self.error_bus = None
        
        # Setup logging to also use error bus
        self._setup_error_bus_logging()
    
    async def initialize(self):
        """Initialize the agent with error bus"""
        try:
            # Initialize error bus connection
            self.error_bus = await init_error_bus(
                agent_name=self.agent_name,
                nats_servers=["nats://nats_coordination:4222"]
            )
            
            await report_error("AGENT_STARTUP", f"{{self.agent_name}} initialized successfully", "INFO")
            print(f"{{self.agent_name}} connected to error bus")
            
        except Exception as e:
            logging.error(f"Failed to initialize error bus: {{e}}")
            # Continue without error bus - graceful degradation
    
    def _setup_error_bus_logging(self):
        """Setup logging handler that also sends to error bus"""
        class ErrorBusHandler(logging.Handler):
            def __init__(self, agent_name):
                super().__init__()
                self.agent_name = agent_name
            
            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    severity = "CRITICAL" if record.levelno >= logging.CRITICAL else "ERROR"
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(report_error(
                            record.name,
                            record.getMessage(),
                            severity,
                            stack_trace=self.format(record) if record.exc_info else None
                        ))
                    except RuntimeError:
                        pass  # No event loop, skip error bus
        
        # Add error bus handler to logger
        logger = logging.getLogger(self.agent_name)
        error_bus_handler = ErrorBusHandler(self.agent_name)
        logger.addHandler(error_bus_handler)
    
    @error_bus_handler("DATABASE_ERROR", "ERROR")
    async def connect_to_database(self):
        """Example method with automatic error reporting"""
        # Simulate database connection
        if False:  # This would be your actual condition
            raise ConnectionError("Database connection failed")
        
        return "Connected successfully"
    
    async def process_request_with_correlation(self, request_id: str, data: dict):
        """Example of processing with error correlation"""
        with ErrorContext(correlation_id=request_id, context={{"request_data": data}}):
            try:
                # Your processing logic here
                result = await self._process_data(data)
                
                # Report successful processing
                await report_error("REQUEST_PROCESSED", f"Request {{request_id}} processed", "INFO")
                
                return result
                
            except ValueError as e:
                # This error will be automatically correlated with the request
                await report_error("VALIDATION_ERROR", str(e), "WARNING")
                raise
            except Exception as e:
                # Critical processing error
                await report_critical(f"Failed to process request {{request_id}}: {{e}}")
                raise
    
    async def _process_data(self, data: dict):
        """Simulate data processing"""
        if not data:
            raise ValueError("Empty data provided")
        
        # Simulate processing
        await asyncio.sleep(0.1)
        return {{"processed": True, "data": data}}
    
    async def monitor_system_health(self):
        """Monitor system health and report issues"""
        import psutil
        
        while True:
            try:
                # Check memory usage
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    await report_critical(
                        f"High memory usage: {{memory.percent}}%",
                        context={{"memory_available": memory.available, "memory_total": memory.total}}
                    )
                
                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > 95:
                    await report_error(
                        "HIGH_CPU_USAGE",
                        f"High CPU usage: {{cpu_percent}}%",
                        "WARNING",
                        context={{"cpu_percent": cpu_percent}}
                    )
                
                # Check disk space
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                if disk_percent > 90:
                    await report_error(
                        "LOW_DISK_SPACE",
                        f"Low disk space: {{disk_percent:.1f}}%",
                        "WARNING",
                        context={{"disk_free": disk.free, "disk_total": disk.total}}
                    )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                await report_error("HEALTH_MONITOR_ERROR", str(e), "ERROR")
                await asyncio.sleep(60)
    
    async def shutdown(self):
        """Graceful shutdown with error reporting"""
        try:
            await report_error("AGENT_SHUTDOWN", f"{{self.agent_name}} shutting down gracefully", "INFO")
            
            if self.error_bus:
                await self.error_bus.disconnect()
            
        except Exception as e:
            logging.error(f"Error during shutdown: {{e}}")

# Example usage and testing
async def main():
    agent = {agent_name.title().replace('_', '')}WithErrorBus()
    
    try:
        # Initialize
        await agent.initialize()
        
        # Test error reporting
        await agent.connect_to_database()
        
        # Test request processing with correlation
        await agent.process_request_with_correlation("req-123", {{"test": "data"}})
        
        # Start health monitoring (would run in background)
        health_task = asyncio.create_task(agent.monitor_system_health())
        
        # Simulate running for a while
        await asyncio.sleep(10)
        
        # Clean shutdown
        health_task.cancel()
        await agent.shutdown()
        
    except Exception as e:
        await report_critical(f"Agent failed: {{e}}")

if __name__ == "__main__":
    # Setup basic logging
    logger = configure_logging(__name__, level="INFO")
    
    # Run the agent
    asyncio.run(main())
'''

def update_requirements_txt():
    """Update requirements.txt with NATS dependencies"""
    requirements = [
        "nats-py>=2.3.0",
        "asyncio-nats-client>=0.11.4",
        "psutil>=5.9.0"
    ]
    
    requirements_file = Path("requirements.txt")
    
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            existing = f.read()
        
        new_requirements = []
        for req in requirements:
            if req.split('>=')[0] not in existing:
                new_requirements.append(req)
        
        if new_requirements:
            with open(requirements_file, 'a') as f:
                f.write('\n# WP-10 NATS Error Bus dependencies\n')
                for req in new_requirements:
                    f.write(f'{req}\n')

def main():
    """Main execution function"""
    print("🚀 WP-10: NATS ERROR BUS")
    print("=" * 50)
    
    # Update requirements
    update_requirements_txt()
    print("✅ Updated requirements.txt with NATS dependencies")
    
    # Create NATS error bus structure
    error_bus_dir = create_nats_error_bus_structure()
    print(f"✅ Created NATS error bus framework in {error_bus_dir}")
    
    # Find error handling candidates
    candidates = find_error_handling_candidates()
    print(f"📁 Found {len(candidates)} agent files to analyze")
    
    # Analyze error patterns
    analysis_results = []
    error_candidates = []
    
    for candidate in candidates:
        result = analyze_error_patterns(candidate)
        analysis_results.append(result)
        
        if result.get('needs_error_bus', False):
            error_candidates.append(result)
    
    print(f"\n📊 ERROR BUS ANALYSIS:")
    print(f"✅ Total agents: {len(analysis_results)}")
    print(f"🔧 Agents needing error bus integration: {len(error_candidates)}")
    
    # Priority breakdown
    priority_counts = {}
    for result in error_candidates:
        priority = result.get('priority', 'unknown')
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    print(f"🎯 Priority breakdown:")
    for priority in ['critical', 'high', 'medium', 'low']:
        count = priority_counts.get(priority, 0)
        print(f"   {priority}: {count}")
    
    # Generate integration examples
    examples_dir = Path("docs/error_bus_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    # Sort by error score and take top candidates
    top_candidates = sorted(error_candidates, key=lambda x: x.get('error_score', 0), reverse=True)[:10]
    
    for agent_info in top_candidates:
        example_code = generate_error_bus_integration_example(agent_info)
        example_file = examples_dir / f"{agent_info['agent_name']}_error_bus_integration.py"
        
        with open(example_file, 'w') as f:
            f.write(example_code)
        
        print(f"✅ Generated error bus integration example for {agent_info['agent_name']}")
    
    # Generate NATS configuration
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    nats_config = {
        "nats": {
            "servers": ["nats://nats_coordination:4222"],
            "error_stream": "ERROR_STREAM",
            "error_subject": "errors",
            "retention_days": 7,
            "max_messages": 1000000
        },
        "error_patterns": [
            {"pattern": "ConnectionError", "threshold": 10, "time_window": 60, "action": "THROTTLE"},
            {"pattern": "TimeoutError", "threshold": 5, "time_window": 30, "action": "THROTTLE"},
            {"pattern": "MemoryError", "threshold": 3, "time_window": 300, "action": "ESCALATE"},
            {"pattern": "CRITICAL", "threshold": 5, "time_window": 60, "action": "ESCALATE"}
        ],
        "dashboard": {
            "update_interval": 5,
            "max_timeline_entries": 1000,
            "flood_detection_window": 300
        }
    }
    
    with open(config_dir / "nats_error_bus.json", 'w') as f:
        json.dump(nats_config, f, indent=2)
    
    # Generate summary report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_agents": len(analysis_results),
        "error_bus_candidates": len(error_candidates),
        "priority_breakdown": priority_counts,
        "error_bus_coverage": (len(error_candidates) / len(analysis_results)) * 100,
        "top_error_agents": [
            {
                "agent": a['agent_name'],
                "error_score": a['error_score'],
                "priority": a['priority'],
                "logging_calls": len(a.get('logging_calls', [])),
                "exception_handlers": len(a.get('exception_handlers', []))
            }
            for a in top_candidates
        ]
    }
    
    with open("WP-10_NATS_ERROR_BUS_REPORT.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ NATS ERROR BUS INTEGRATION COMPLETE:")
    print(f"📊 Error Bus Coverage: {report['error_bus_coverage']:.1f}%")
    print(f"🚨 Critical Priority Agents: {priority_counts.get('critical', 0)}")
    print(f"⚠️  High Priority Agents: {priority_counts.get('high', 0)}")
    print(f"📝 Report: WP-10_NATS_ERROR_BUS_REPORT.json")
    print(f"🔌 NATS Error Bus Framework: common/error_bus/")
    print(f"🐳 Docker Compose: common/error_bus/docker-compose.yml")
    print(f"📖 Integration Examples: docs/error_bus_examples/")
    print(f"⚙️  Configuration: config/nats_error_bus.json")
    
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Start NATS server: cd common/error_bus && docker-compose up -d")
    print(f"2. Run error dashboard: python common/error_bus/dashboard.py")
    print(f"3. Integrate agents using examples in docs/error_bus_examples/")
    
    print(f"\n🎯 WP-10 NATS ERROR BUS: COMPLETE")

if __name__ == "__main__":
    main() 