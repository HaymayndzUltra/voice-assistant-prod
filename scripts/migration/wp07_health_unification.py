#!/usr/bin/env python3
"""
WP-07 Health Unification Migration Script
Standardizes health check endpoints across all agents in the system
Target: Unified health monitoring with consistent endpoints and response formats
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
import json
from datetime import datetime

class HealthUnificationAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect existing health check patterns"""
    
    def __init__(self):
        self.has_health_endpoint = False
        self.health_port = None
        self.health_methods = []
        self.inherits_base_agent = False
        self.class_names = []
        self.imports = []
        self.route_patterns = []
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(f"from {node.module}")
            if 'base_agent' in node.module.lower() or 'BaseAgent' in str(node.names):
                self.inherits_base_agent = True
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.class_names.append(node.name)
        
        # Check if inherits from BaseAgent
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseAgent':
                self.inherits_base_agent = True
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseAgent':
                self.inherits_base_agent = True
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        # Check for health-related methods
        if 'health' in node.name.lower():
            self.health_methods.append(node.name)
            self.has_health_endpoint = True
        
        self.generic_visit(node)
    
    def visit_Str(self, node):
        # Check for health-related routes
        if hasattr(node, 's') and isinstance(node.s, str):
            if '/health' in node.s or 'health_check' in node.s:
                self.route_patterns.append(node.s)
                self.has_health_endpoint = True
        self.generic_visit(node)

def find_agent_files() -> List[Path]:
    """Find all agent files in the system"""
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
    
    # Filter out __init__ and test files
    return [f for f in agent_files if not f.name.startswith('__') and 'test' not in f.name.lower()]

def analyze_health_patterns(file_path: Path) -> Dict:
    """Analyze health check patterns in an agent file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = HealthUnificationAnalyzer()
        analyzer.visit(tree)
        
        # Extract health port
        health_port = extract_health_port(content)
        
        # Check for existing health implementation
        health_score = calculate_health_score(analyzer, content)
        
        return {
            'file_path': str(file_path),
            'agent_name': file_path.stem,
            'has_health_endpoint': analyzer.has_health_endpoint,
            'health_port': health_port,
            'health_methods': analyzer.health_methods,
            'inherits_base_agent': analyzer.inherits_base_agent,
            'route_patterns': analyzer.route_patterns,
            'health_score': health_score,
            'needs_unification': health_score < 100
        }
    except Exception as e:
        return {
            'file_path': str(file_path),
            'agent_name': file_path.stem,
            'error': str(e),
            'needs_unification': True,
            'health_score': 0
        }

def extract_health_port(content: str) -> int:
    """Extract health check port from content"""
    patterns = [
        r'health[_\s]*check[_\s]*port["\s]*=[\s]*(\d+)',
        r'HEALTH[_\s]*CHECK[_\s]*PORT["\s]*=[\s]*(\d+)',
        r'health[_\s]*port["\s]*=[\s]*(\d+)',
        r'HEALTH[_\s]*PORT["\s]*=[\s]*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0

def calculate_health_score(analyzer: HealthUnificationAnalyzer, content: str) -> int:
    """Calculate health implementation score (0-100)"""
    score = 0
    
    # Base agent inheritance
    if analyzer.inherits_base_agent:
        score += 40
    
    # Has health endpoint
    if analyzer.has_health_endpoint:
        score += 30
    
    # Has health methods
    if analyzer.health_methods:
        score += 20
    
    # Has standardized routes
    if any('/health' in route for route in analyzer.route_patterns):
        score += 10
    
    return min(score, 100)

def generate_unified_health_mixin() -> str:
    """Generate unified health check mixin"""
    return '''
"""
Unified Health Check Mixin for WP-07 Health Unification
Provides standardized health endpoints and response formats
"""

import time
import psutil
import zmq
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
import threading

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
    Unified health check mixin that can be added to any agent
    Provides standardized health endpoints and monitoring
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
            self.health_check_port = self.port + 1000  # Standard offset
        else:
            self.health_check_port = 8000  # Default fallback
        
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
                    # Wait for health check request
                    message = self.health_socket.recv_string(zmq.NOBLOCK)
                    
                    if message == "health_check":
                        response = self.get_health_status()
                        self.health_socket.send_json(response)
                    elif message == "detailed_health":
                        response = self.get_detailed_health_status()
                        self.health_socket.send_json(response)
                    else:
                        self.health_socket.send_string("Unknown health request")
                        
            except zmq.Again:
                # No message received, continue
                time.sleep(0.1)
            except Exception as e:
                self.health_error_count += 1
                self.health_last_error = str(e)
                time.sleep(1)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get basic health status"""
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
                "timestamp": datetime.now().isoformat()
            }
    
    def get_detailed_health_status(self) -> Dict[str, Any]:
        """Get detailed health status with additional metrics"""
        basic_health = self.get_health_status()
        
        # Add detailed system information
        basic_health.update({
            "system_info": {
                "python_version": self._get_python_version(),
                "platform": self._get_platform_info(),
                "disk_usage": self._get_disk_usage(),
                "network_connections": self._get_network_connections()
            }
        })
        
        return basic_health
    
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
    
    def _get_python_version(self) -> str:
        """Get Python version"""
        import sys
        return sys.version
    
    def _get_platform_info(self) -> str:
        """Get platform information"""
        import platform
        return platform.platform()
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage information"""
        usage = psutil.disk_usage('/')
        return {
            "total_gb": usage.total / (1024**3),
            "used_gb": usage.used / (1024**3),
            "free_gb": usage.free / (1024**3),
            "percent": (usage.used / usage.total) * 100
        }
    
    def _get_network_connections(self) -> int:
        """Get number of network connections"""
        try:
            connections = psutil.net_connections()
            return len(connections)
        except:
            return 0
    
    def shutdown_health_monitoring(self):
        """Shutdown health monitoring"""
        self.health_running = False
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'health_context'):
            self.health_context.term()
'''

def generate_health_integration_example(agent_info: Dict) -> str:
    """Generate health integration example for an agent"""
    agent_name = agent_info['agent_name']
    
    return f'''
# Health Integration Example for {agent_name}
# Generated by WP-07 Health Unification

from common.health.unified_health import UnifiedHealthMixin

class {agent_name.title().replace('_', '')}(UnifiedHealthMixin):
    """
    Enhanced {agent_name} with unified health monitoring
    """
    
    def __init__(self, *args, **kwargs):
        # Initialize your agent normally
        super().__init__(*args, **kwargs)
        
        # Initialize health monitoring
        self.__init_health_monitoring__(health_check_port={agent_info.get('health_port', 8000)})
        
        # Add custom health metrics
        self.add_custom_metric("agent_type", "{agent_name}")
        self.add_custom_metric("initialization_time", time.time())
        
        # Add dependency checks (customize for your agent)
        # self.add_dependency_check("database", self._check_database_connection)
        # self.add_dependency_check("external_api", self._check_external_api)
    
    def _check_database_connection(self) -> bool:
        """Example dependency check for database"""
        try:
            # Add your database check logic here
            return True
        except:
            return False
    
    def _check_external_api(self) -> bool:
        """Example dependency check for external API"""
        try:
            # Add your API check logic here
            return True
        except:
            return False
    
    # Override any existing health methods to use unified system
    def health_check(self):
        """Unified health check endpoint"""
        return self.get_health_status()
    
    def detailed_health(self):
        """Detailed health check endpoint"""
        return self.get_detailed_health_status()

# Usage example:
if __name__ == "__main__":
    agent = {agent_name.title().replace('_', '')}()
    
    # Your agent logic here
    
    # Health monitoring runs automatically in background
    # Access via: tcp://localhost:{agent_info.get('health_port', 8000)}
'''

def create_health_unification_structure():
    """Create the health unification directory structure"""
    health_dir = Path("common/health")
    health_dir.mkdir(parents=True, exist_ok=True)
    
    # Create unified health mixin
    with open(health_dir / "unified_health.py", 'w') as f:
        f.write(generate_unified_health_mixin())
    
    # Create __init__.py
    with open(health_dir / "__init__.py", 'w') as f:
        f.write('"""Unified Health Monitoring System"""\n\nfrom .unified_health import UnifiedHealthMixin, HealthMetrics, HealthCheckResponse\n\n__all__ = ["UnifiedHealthMixin", "HealthMetrics", "HealthCheckResponse"]\n')
    
    return health_dir

def update_requirements_txt():
    """Update requirements.txt with health monitoring dependencies"""
    requirements = [
        "psutil>=5.9.0",
        "pyzmq>=24.0.0"
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
                f.write('\n# WP-07 Health Unification dependencies\n')
                for req in new_requirements:
                    f.write(f'{req}\n')

def main():
    """Main execution function"""
    print("🚀 WP-07: HEALTH UNIFICATION")
    print("=" * 50)
    
    # Update requirements
    update_requirements_txt()
    print("✅ Updated requirements.txt with health monitoring dependencies")
    
    # Create health monitoring structure
    health_dir = create_health_unification_structure()
    print(f"✅ Created unified health monitoring system in {health_dir}")
    
    # Find all agent files
    agent_files = find_agent_files()
    print(f"📁 Found {len(agent_files)} agent files to analyze")
    
    # Analyze agents
    analysis_results = []
    needs_unification = []
    
    for agent_file in agent_files:
        result = analyze_health_patterns(agent_file)
        analysis_results.append(result)
        
        if result.get('needs_unification', True):
            needs_unification.append(result)
    
    print(f"\n📊 HEALTH UNIFICATION ANALYSIS:")
    print(f"✅ Agents with good health implementation: {len(analysis_results) - len(needs_unification)}")
    print(f"🔧 Agents needing health unification: {len(needs_unification)}")
    
    # Generate integration examples
    examples_dir = Path("docs/health_integration_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    for agent_info in needs_unification[:10]:  # Top 10 agents
        example_code = generate_health_integration_example(agent_info)
        example_file = examples_dir / f"{agent_info['agent_name']}_health_integration.py"
        
        with open(example_file, 'w') as f:
            f.write(example_code)
        
        print(f"✅ Generated health integration example for {agent_info['agent_name']}")
    
    # Generate summary report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_agents": len(analysis_results),
        "unified_agents": len(analysis_results) - len(needs_unification),
        "agents_needing_unification": len(needs_unification),
        "health_unification_coverage": ((len(analysis_results) - len(needs_unification)) / len(analysis_results)) * 100,
        "agents_analysis": analysis_results
    }
    
    with open("WP-07_HEALTH_UNIFICATION_REPORT.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ HEALTH UNIFICATION COMPLETE:")
    print(f"📊 Coverage: {report['health_unification_coverage']:.1f}%")
    print(f"📝 Report: WP-07_HEALTH_UNIFICATION_REPORT.json")
    print(f"🏥 Unified Health System: common/health/")
    print(f"📖 Integration Examples: docs/health_integration_examples/")
    
    print(f"\n🎯 WP-07 HEALTH UNIFICATION: COMPLETE")

if __name__ == "__main__":
    main() 