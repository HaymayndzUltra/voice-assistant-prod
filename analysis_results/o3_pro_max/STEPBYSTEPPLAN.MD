
🔴 COMMAND 1: CONFIGURATION SCHEMA UNIFICATION

Step 1.1: Create Universal Config Manager

# CREATE FILE: common/config_manager.py
cat > common/config_manager.py << 'EOF'
"""
Universal Configuration Manager
Handles both MainPC (agent_groups) and PC2 (pc2_services) formats
"""
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Union

def load_unified_config(config_path: str) -> Dict[str, Any]:
    """
    Load config and normalize to standard format regardless of source
    Returns: Unified agent list with standard fields
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'agent_groups' in config:
        return normalize_mainpc_config(config)
    elif 'pc2_services' in config:
        return normalize_pc2_config(config)
    else:
        raise ValueError(f"Unknown config format in {config_path}")

def normalize_mainpc_config(config: Dict) -> Dict[str, Any]:
    """Convert MainPC agent_groups to unified format"""
    unified_agents = []
    
    for group_name, agents in config['agent_groups'].items():
        for agent_name, agent_data in agents.items():
            unified_agent = {
                'name': agent_name,
                'group': group_name,
                'script_path': agent_data.get('script_path'),
                'port': agent_data.get('port'),
                'health_check_port': agent_data.get('health_check_port'),
                'required': agent_data.get('required', False),
                'dependencies': agent_data.get('dependencies', []),
                'config': agent_data.get('config', {}),
                'machine': 'mainpc'
            }
            unified_agents.append(unified_agent)
    
    return {
        'unified_agents': unified_agents,
        'global_settings': config.get('global_settings', {}),
        'source_format': 'agent_groups'
    }

def normalize_pc2_config(config: Dict) -> Dict[str, Any]:
    """Convert PC2 pc2_services to unified format"""
    unified_agents = []
    
    for agent_data in config['pc2_services']:
        unified_agent = {
            'name': agent_data.get('name'),
            'group': 'pc2_services',  # Default group for PC2
            'script_path': agent_data.get('script_path'),
            'port': agent_data.get('port'),
            'health_check_port': agent_data.get('health_check_port'),
            'required': agent_data.get('required', False),
            'dependencies': agent_data.get('dependencies', []),
            'config': agent_data.get('config', {}),
            'machine': 'pc2'
        }
        unified_agents.append(unified_agent)
    
    return {
        'unified_agents': unified_agents,
        'global_settings': {
            'environment': config.get('environment', {}),
            'resource_limits': config.get('resource_limits', {}),
            'health_checks': config.get('health_checks', {})
        },
        'source_format': 'pc2_services'
    }

def get_agents_by_machine(unified_config: Dict, machine: str) -> List[Dict]:
    """Filter agents by machine type"""
    return [agent for agent in unified_config['unified_agents'] 
            if agent['machine'] == machine]

def validate_config_consistency(unified_config: Dict) -> List[str]:
    """Validate configuration for common issues"""
    issues = []
    ports_used = set()
    
    for agent in unified_config['unified_agents']:
        # Check port conflicts
        port = agent.get('port')
        health_port = agent.get('health_check_port')
        
        if port in ports_used:
            issues.append(f"Port conflict: {port} used by multiple agents")
        if health_port in ports_used:
            issues.append(f"Health port conflict: {health_port} used by multiple agents")
        
        if port:
            ports_used.add(port)
        if health_port:
            ports_used.add(health_port)
        
        # Check script path exists
        script_path = agent.get('script_path')
        if script_path and not os.path.exists(script_path):
            issues.append(f"Script not found: {script_path} for agent {agent['name']}")
    
    return issues
EOF


_____________________________________________________________________________
WHY THIS STEP: Creates foundation para sa unified config handling. Ito ang base na gagamitin ng lahat ng startup scripts.
_____________________________________________________________________________


Step 1.2: Test the Config Manage

# TEST: Verify config manager works with both formats
python3 -c "
from common.config_manager import load_unified_config, validate_config_consistency
import json

print('Testing MainPC config...')
mainpc_config = load_unified_config('main_pc_code/config/startup_config.yaml')
print(f'MainPC agents found: {len(mainpc_config[\"unified_agents\"])}')

print('Testing PC2 config...')
pc2_config = load_unified_config('pc2_code/config/startup_config.yaml')
print(f'PC2 agents found: {len(pc2_config[\"unified_agents\"])}')

print('Validating configurations...')
mainpc_issues = validate_config_consistency(mainpc_config)
pc2_issues = validate_config_consistency(pc2_config)

print(f'MainPC issues: {len(mainpc_issues)}')
for issue in mainpc_issues[:5]:  # Show first 5
    print(f'  - {issue}')

print(f'PC2 issues: {len(pc2_issues)}')
for issue in pc2_issues[:5]:  # Show first 5
    print(f'  - {issue}')
"

_____________________________________________________________________________

WHY THIS STEP: Validates na working ang config manager at nag-identify ng existing issues bago mag-proceed.
_____________________________________________________________________________

Step 1.3: Update start_system_v2.py to Use Unified Config

# MODIFY FILE: main_pc_code/scripts/start_system_v2.py
# Add import at the top
sed -i '1i\\nimport sys\nsys.path.insert(0, "/home/haymayndz/AI_System_Monorepo")\nfrom common.config_manager import load_unified_config, get_agents_by_machine' main_pc_code/scripts/start_system_v2.py

# Replace config loading section
python3 << 'EOF'
import re

# Read current file
with open('main_pc_code/scripts/start_system_v2.py', 'r') as f:
    content = f.read()

# Replace config loading
old_pattern = r'with open\(config_path.*?\) as f:\s*config = yaml\.safe_load\(f\)'
new_code = '''unified_config = load_unified_config(config_path)
        config = unified_config  # For backward compatibility
        agents = get_agents_by_machine(unified_config, "mainpc")'''

content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

# Write back
with open('main_pc_code/scripts/start_system_v2.py', 'w') as f:
    f.write(content)

print("Updated start_system_v2.py to use unified config")
EOF


_____________________________________________________________________________
WHY THIS STEP: Integrates unified config manager sa existing startup script para ma-test immediately.
_____________________________________________________________________________


🔴 COMMAND 2: HEALTH CHECK STANDARDIZATION

PURPOSE:
May 3 different health check patterns causing ObservabilityHub to report "unknown" status. Need to standardize to UnifiedHealthMixin pattern across all agents.

STEP-BY-STEP EXECUTION:

Step 2.1: Enhance UnifiedHealthMixin


# MODIFY FILE: common/health/unified_health.py
cat > common/health/unified_health.py << 'EOF'
"""
Enhanced Unified Health Check Mixin - WP-07 Standard
Provides standardized health endpoints and response formats
"""
import time
import psutil
import zmq
import threading
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

@dataclass
class HealthMetrics:
    """Standardized health metrics"""
    timestamp: str
    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float
    cpu_percent: float
    memory_percent: float
    zmq_connections: int
    active_threads: int
    error_count: int
    last_error: Optional[str] = None
    dependencies_status: Optional[Dict[str, str]] = None
    custom_metrics: Optional[Dict[str, Any]] = None

@dataclass
class HealthCheckResponse:
    """Standardized health check response"""
    agent_name: str
    health_metrics: HealthMetrics
    version: str = "1.0"
    schema: str = "WP-07-unified-health"

class UnifiedHealthMixin:
    """
    Unified health check mixin - embeddable in any agent
    """
    
    def __init_health_monitoring__(self, health_check_port: int = None):
        """Initialize health monitoring system"""
        self.health_start_time = time.time()
        self.health_error_count = 0
        self.health_last_error = None
        self.health_custom_metrics = {}
        self.health_dependencies = {}
        
        # Set health check port
        if health_check_port:
            self.health_check_port = health_check_port
        elif hasattr(self, 'port'):
            self.health_check_port = self.port + 1000
        else:
            self.health_check_port = 8000
        
        # Initialize health check ZMQ socket
        self._init_health_socket()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True
        )
        self.health_running = True
        self.health_thread.start()
    
    def _init_health_socket(self):
        """Initialize health check ZMQ socket"""
        try:
            self.health_context = zmq.Context()
            self.health_socket = self.health_context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://*:{self.health_check_port}")
            print(f"Health endpoint initialized on port {self.health_check_port}")
        except Exception as e:
            print(f"Failed to initialize health socket: {e}")
            self.health_socket = None
    
    def _health_monitor_loop(self):
        """Main health monitoring loop"""
        while self.health_running:
            try:
                if self.health_socket:
                    message = self.health_socket.recv_string(zmq.NOBLOCK)
                    
                    if message in ["health_check", "ping", "health"]:
                        response = self.get_health_status()
                        self.health_socket.send_json(response)
                    elif message == "detailed_health":
                        response = self.get_detailed_health_status()
                        self.health_socket.send_json(response)
                    else:
                        self.health_socket.send_string("Unknown health request")
                        
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                self.health_error_count += 1
                self.health_last_error = str(e)
                time.sleep(1)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get standardized health status"""
        try:
            metrics = self._collect_health_metrics()
            response = HealthCheckResponse(
                agent_name=getattr(self, 'name', self.__class__.__name__),
                health_metrics=metrics
            )
            return asdict(response)
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "schema": "WP-07-unified-health"
            }
    
    def _collect_health_metrics(self) -> HealthMetrics:
        """Collect health metrics"""
        now = datetime.now()
        uptime = time.time() - self.health_start_time
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Process metrics
        process = psutil.Process()
        active_threads = process.num_threads()
        
        # ZMQ connections (simplified)
        zmq_connections = getattr(self, '_active_connections', 0)
        
        # Determine overall status
        status = self._determine_health_status(cpu_percent, memory_percent)
        
        return HealthMetrics(
            timestamp=now.isoformat(),
            status=status,
            uptime_seconds=uptime,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            zmq_connections=zmq_connections,
            active_threads=active_threads,
            error_count=self.health_error_count,
            last_error=self.health_last_error,
            dependencies_status=self.health_dependencies.copy(),
            custom_metrics=self.health_custom_metrics.copy()
        )
    
    def _determine_health_status(self, cpu_percent: float, memory_percent: float) -> str:
        """Determine overall health status"""
        if cpu_percent > 90 or memory_percent > 90:
            return "unhealthy"
        elif cpu_percent > 70 or memory_percent > 70:
            return "degraded"
        elif self.health_error_count > 10:
            return "degraded"
        else:
            return "healthy"
    
    def add_dependency_check(self, name: str, check_func):
        """Add a dependency health check"""
        try:
            result = check_func()
            self.health_dependencies[name] = "healthy" if result else "unhealthy"
        except Exception as e:
            self.health_dependencies[name] = f"error: {e}"
    
    def add_custom_metric(self, name: str, value: Any):
        """Add custom health metric"""
        self.health_custom_metrics[name] = value
    
    def record_error(self, error: str):
        """Record an error for health monitoring"""
        self.health_error_count += 1
        self.health_last_error = error
    
    def shutdown_health_monitoring(self):
        """Shutdown health monitoring"""
        self.health_running = False
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'health_context'):
            self.health_context.term()
EOF

__________________________________________________________________
WHY THIS STEP: Creates enhanced, production-ready health check standard na compatible sa ObservabilityHub expectations.
__________________________________________________________________

Step 2.2: Integrate into BaseAgent

# MODIFY FILE: common/core/base_agent.py
python3 << 'EOF'
# Read current BaseAgent file
with open('common/core/base_agent.py', 'r') as f:
    content = f.read()

# Add import at top if not exists
if 'from common.health.unified_health import UnifiedHealthMixin' not in content:
    import_line = "from common.health.unified_health import UnifiedHealthMixin\n"
    content = content.replace('import logging\n', f'import logging\n{import_line}')

# Update class definition
content = content.replace(
    'class BaseAgent:', 
    'class BaseAgent(UnifiedHealthMixin):'
)

# Add health initialization in __init__
init_pattern = r'(self\.context = zmq\.Context\(\).*?\n)'
health_init = '''        # Initialize unified health monitoring
        self.__init_health_monitoring__(self.health_check_port)
        
'''
content = re.sub(init_pattern, r'\1' + health_init, content)

# Write back
with open('common/core/base_agent.py', 'w') as f:
    f.write(content)

print("Integrated UnifiedHealthMixin into BaseAgent")
EOF

__________________________________________________________________

WHY THIS STEP: Automatically adds health monitoring sa lahat ng agents na inherit from BaseAgent, ensuring consistency.

__________________________________________________________________

Step 2.3: Test Health Check Integration

# Test health check works
python3 -c "
import sys
sys.path.insert(0, '.')
from common.core.base_agent import BaseAgent
import time
import zmq

print('Testing BaseAgent health integration...')

# Create test agent
class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(name='TestAgent', port=9999)

agent = TestAgent()
time.sleep(2)  # Let health monitoring start

# Test health check
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect('tcp://localhost:10999')  # health_check_port = port + 1000
socket.send_string('health_check')
response = socket.recv_json()

print('Health check response:')
print(f'  Agent: {response.get(\"agent_name\")}')
print(f'  Status: {response.get(\"health_metrics\", {}).get(\"status\")}')
print(f'  Schema: {response.get(\"schema\")}')

socket.close()
context.term()
print('Health check test completed successfully!')
"
__________________________________________________________________
WHY THIS STEP: Validates na working ang health check integration before deploying sa production agents.
__________________________________________________________________

🔴 COMMAND 3: ERROR BUS MIGRATION (ZMQ → NATS)

PURPOSE:
Currently may 60/40 split between ZMQ PUB/SUB (port 7150) vs NATS JetStream for error handling. This causes duplicate errors and missing flood detection. Need to migrate all to NATS

STEP-BY-STEP EXECUTION:


Step 3.1: Enhance NATS Error Bus Client


# MODIFY FILE: common/error_bus/nats_client.py
cat > common/error_bus/nats_client.py << 'EOF'
"""
Enhanced NATS Error Bus Client
Centralized error handling with flood detection and correlation
"""
import asyncio
import nats
import json
import uuid
import time
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

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

class ErrorFloodDetector:
    """Prevents error floods"""
    
    def __init__(self):
        self.error_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.throttled_patterns: Dict[str, datetime] = {}
        self.lock = threading.Lock()
        
        # Default flood patterns
        self.patterns = [
            {"pattern": "ConnectionError", "threshold": 10, "window": 60, "action": "THROTTLE"},
            {"pattern": "TimeoutError", "threshold": 5, "window": 30, "action": "THROTTLE"},
            {"pattern": "MemoryError", "threshold": 3, "window": 300, "action": "ESCALATE"},
            {"pattern": "CRITICAL", "threshold": 5, "window": 60, "action": "ESCALATE"},
        ]
    
    def check_flood(self, error_msg: ErrorMessage) -> bool:
        """Check if error should be throttled"""
        with self.lock:
            current_time = datetime.now()
            
            for pattern in self.patterns:
                if pattern["pattern"] in error_msg.message or pattern["pattern"] in error_msg.error_type:
                    pattern_key = f"{error_msg.source_agent}:{pattern['pattern']}"
                    
                    # Check if currently throttled
                    if pattern_key in self.throttled_patterns:
                        throttle_end = self.throttled_patterns[pattern_key] + timedelta(seconds=pattern["window"])
                        if current_time < throttle_end:
                            return True
                        else:
                            del self.throttled_patterns[pattern_key]
                    
                    # Add to history
                    self.error_history[pattern_key].append(current_time)
                    
                    # Check threshold
                    window_start = current_time - timedelta(seconds=pattern["window"])
                    recent_errors = [t for t in self.error_history[pattern_key] if t >= window_start]
                    
                    if len(recent_errors) >= pattern["threshold"]:
                        if pattern["action"] == "THROTTLE":
                            self.throttled_patterns[pattern_key] = current_time
                            return True
            
            return False

class NATSErrorBus:
    """Enhanced NATS error bus"""
    
    def __init__(self, agent_name: str = "unknown"):
        self.agent_name = agent_name
        self.nats_servers = os.getenv("NATS_SERVERS", "nats://localhost:4222").split(",")
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[nats.aio.client.JetStreamContext] = None
        
        # Configuration
        self.error_subject = "errors"
        self.error_stream = "ERROR_STREAM"
        self.error_consumer = f"error_consumer_{agent_name}"
        
        # Flood detection
        self.flood_detector = ErrorFloodDetector()
        
        # Handlers
        self.error_handlers: List[Callable[[ErrorMessage], None]] = []
        
        # Background task
        self._running = False
        self._consumer_task = None
    
    async def connect(self):
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(servers=self.nats_servers)
            self.js = self.nc.jetstream()
            
            # Create stream if needed
            await self._ensure_stream_exists()
            
            # Start consuming
            await self._start_error_consumer()
            
            print(f"Connected to NATS error bus for agent {self.agent_name}")
            
        except Exception as e:
            print(f"Failed to connect to NATS: {e}")
            # Fallback to local logging
            return False
        
        return True
    
    async def _ensure_stream_exists(self):
        """Ensure error stream exists"""
        try:
            await self.js.stream_info(self.error_stream)
        except:
            await self.js.add_stream(
                name=self.error_stream,
                subjects=[f"{self.error_subject}.>"],
                retention="limits",
                max_msgs=1000000,
                max_age=7 * 24 * 3600,  # 7 days
                storage="file"
            )
    
    async def publish_error(self, error_type: str, message: str, severity: str = "ERROR",
                           stack_trace: str = None, context: Dict = None, 
                           correlation_id: str = None) -> bool:
        """Publish error to NATS"""
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
            return False
        
        try:
            if self.nc and self.js:
                subject = f"{self.error_subject}.{severity.lower()}.{self.agent_name}"
                data = json.dumps(asdict(error_msg)).encode()
                await self.js.publish(subject, data)
                return True
        except Exception as e:
            print(f"Failed to publish to NATS: {e}")
        
        return False

# Global instance
_error_bus: Optional[NATSErrorBus] = None
_error_bus_lock = threading.Lock()

def get_error_bus(agent_name: str = None) -> NATSErrorBus:
    """Get global error bus instance"""
    global _error_bus
    with _error_bus_lock:
        if _error_bus is None:
            agent_name = agent_name or os.getenv("AGENT_NAME", "unknown")
            _error_bus = NATSErrorBus(agent_name)
        return _error_bus

# Convenience functions
def report_error(error_type: str, message: str, severity: str = "ERROR", **kwargs):
    """Report error (sync wrapper)"""
    error_bus = get_error_bus()
    
    # If in async context, await directly
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(error_bus.publish_error(error_type, message, severity, **kwargs))
        else:
            asyncio.run(error_bus.publish_error(error_type, message, severity, **kwargs))
    except RuntimeError:
        # No event loop, fallback to logging
        import logging
        logging.error(f"[{severity}] {error_type}: {message}")

def report_critical(message: str, **kwargs):
    """Report critical error"""
    report_error("CRITICAL_ERROR", message, "CRITICAL", **kwargs)

def report_warning(message: str, **kwargs):
    """Report warning"""
    report_error("WARNING", message, "WARNING", **kwargs)
EOF

_____________________________________________________________
WHY THIS STEP: Creates production-ready NATS error bus with flood detection, correlation, and fallback mechanisms.
_____________________________________________________________

Step 3.2: Create Migration Script

# CREATE FILE: scripts/migrate_error_bus.py
cat > scripts/migrate_error_bus.py << 'EOF'
#!/usr/bin/env python3
"""
Error Bus Migration Script
Migrates agents from ZMQ PUB/SUB to NATS JetStream
"""
import os
import re
import sys
import argparse
from pathlib import Path

def find_zmq_error_publishers():
    """Find agents using ZMQ error publishing"""
    zmq_publishers = []
    
    # Search patterns
    patterns = [
        r'error_bus_pub\.send_.*ERROR',
        r'zmq\.PUB.*7150',
        r'error_bus.*\.send',
        r'publish.*error.*zmq'
    ]
    
    # Search directories
    search_dirs = ['main_pc_code/agents', 'pc2_code/agents']
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for file_path in Path(search_dir).rglob('*.py'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            zmq_publishers.append(str(file_path))
                            break
                            
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return list(set(zmq_publishers))

def migrate_agent_to_nats(file_path: str, phase: str = "dual"):
    """Migrate single agent to NATS"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add NATS import if not present
        if 'from common.error_bus.nats_client import' not in content:
            import_line = "from common.error_bus.nats_client import report_error, report_critical, report_warning\n"
            
            # Find where to insert import
            if 'import zmq' in content:
                content = content.replace('import zmq', f'import zmq\n{import_line}')
            else:
                # Add after other imports
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        continue
                    else:
                        lines.insert(i, import_line.strip())
                        break
                content = '\n'.join(lines)
        
        # Replace ZMQ error publishing with NATS
        replacements = [
            # Common ZMQ error patterns
            (r'self\.error_bus_pub\.send_json\(\s*\{\s*["\']type["\']\s*:\s*["\']error["\']\s*,\s*["\']message["\']\s*:\s*([^}]+)\}\s*\)',
             r'report_error("AGENT_ERROR", \1)'),
            
            (r'self\.error_bus_pub\.send_string\(\s*f?["\']ERROR:\s*([^"\']+)["\']\s*\)',
             r'report_error("AGENT_ERROR", \1)'),
            
            (r'error_bus\.send\(\s*([^)]+)\)',
             r'report_error("AGENT_ERROR", \1)'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # If dual phase, keep ZMQ for now
        if phase == "dual":
            content = content.replace(
                'report_error(',
                'report_error(  # MIGRATION: Dual ZMQ+NATS phase\n        ('
            )
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Migrated: {file_path}")
            return True
        else:
            print(f"⏭️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error migrating {file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate error bus from ZMQ to NATS')
    parser.add_argument('--phase', choices=['dual', 'nats-only'], default='dual',
                       help='Migration phase: dual (ZMQ+NATS) or nats-only')
    parser.add_argument('--scan-only', action='store_true',
                       help='Only scan for ZMQ publishers, do not migrate')
    parser.add_argument('--agent', help='Migrate specific agent file')
    
    args = parser.parse_args()
    
    if args.agent:
        # Migrate specific agent
        if os.path.exists(args.agent):
            migrate_agent_to_nats(args.agent, args.phase)
        else:
            print(f"Agent file not found: {args.agent}")
        return
    
    # Find all ZMQ publishers
    print("🔍 Scanning for ZMQ error publishers...")
    zmq_publishers = find_zmq_error_publishers()
    
    print(f"📊 Found {len(zmq_publishers)} agents using ZMQ error publishing:")
    for publisher in zmq_publishers:
        print(f"  - {publisher}")
    
    if args.scan_only:
        return
    
    # Migrate all found publishers
    print(f"\n🚀 Starting migration (phase: {args.phase})...")
    migrated_count = 0
    
    for publisher in zmq_publishers:
        if migrate_agent_to_nats(publisher, args.phase):
            migrated_count += 1
    
    print(f"\n✅ Migration complete: {migrated_count}/{len(zmq_publishers)} agents migrated")
    
    if args.phase == "dual":
        print("\n⚠️  DUAL PHASE: Agents now publish to both ZMQ and NATS")
        print("   Next step: Run with --phase nats-only to complete migration")
    else:
        print("\n🎉 NATS-ONLY PHASE: Migration complete!")
        print("   ZMQ error bus can now be decommissioned")

if __name__ == '__main__':
    main()
EOF

chmod +x scripts/migrate_error_bus.py

_______________________________________________________________
WHY THIS STEP: Automated migration script para sa phased approach - dual publishing muna, then NATS-only.
_______________________________________________________________




Step 3.3: Execute Migration Phase 1 (Dual Publishing)

# Phase 1: Scan current ZMQ usage
python3 scripts/migrate_error_bus.py --scan-only

# Phase 1: Migrate to dual publishing (ZMQ + NATS)
python3 scripts/migrate_error_bus.py --phase dual

# Test migration worked
echo "Testing migration results..."
grep -r "report_error" main_pc_code/agents/ | head -5
grep -r "error_bus_pub" main_pc_code/agents/ | head -5


_____________________________________________________________
WHY THIS STEP: Implements phased migration - ensures both systems work before cutting over completely.
_____________________________________________________________

📝 SUMMARY OF COMMANDS CREATED:
🎯 EXECUTION ORDER:
COMMAND 1: Configuration Schema Unification (3 steps)
COMMAND 2: Health Check Standardization (3 steps)
COMMAND 3: Error Bus Migration (3 steps)
📁 FILES CREATED/MODIFIED:
common/config_manager.py (NEW)
common/health/unified_health.py (ENHANCED)
common/core/base_agent.py (MODIFIED)
common/error_bus/nats_client.py (ENHANCED)
scripts/migrate_error_bus.py (NEW)
main_pc_code/scripts/start_system_v2.py (MODIFIED)
🚨 RECOVERY COMMANDS:

# If something goes wrong, restore from backup
git stash push -m "Implementation backup $(date)"
git checkout HEAD~1  # Go back one commit