#!/usr/bin/env python3
"""
WP-07 Resiliency Migration Script
Migrates agents to use circuit breakers, retry mechanisms, and bulkhead patterns
Target: Agents with high failure rates or external dependencies
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ResiliencyAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect resiliency pattern needs"""
    
    def __init__(self):
        self.external_calls = []
        self.error_handlers = []
        self.timeout_patterns = []
        self.retry_patterns = []
        self.concurrency_patterns = []
        self.resiliency_score = 0
        
    def visit_FunctionDef(self, node):
        # Look for async functions (potential concurrency)
        if node.name.startswith('async ') or any(
            isinstance(d, ast.Name) and d.id == 'asyncio' 
            for d in ast.walk(node)
        ):
            self.concurrency_patterns.append(f"Async function: {node.name} (line {node.lineno})")
            self.resiliency_score += 2
        
        # Look for error handling
        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler):
                self.error_handlers.append(f"Exception handler in {node.name} (line {child.lineno})")
                self.resiliency_score += 1
                
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Look for external API calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['get', 'post', 'put', 'delete', 'request']):
            self.external_calls.append(f"HTTP call (line {node.lineno})")
            self.resiliency_score += 3
        
        # Look for socket operations
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['connect', 'send', 'recv', 'bind']):
            self.external_calls.append(f"Socket operation (line {node.lineno})")
            self.resiliency_score += 3
        
        # Look for database calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['execute', 'query', 'connect', 'cursor']):
            self.external_calls.append(f"Database call (line {node.lineno})")
            self.resiliency_score += 2
        
        # Look for timeout patterns
        if (isinstance(node.func, ast.Name) and 
            'timeout' in node.func.id.lower()):
            self.timeout_patterns.append(f"Timeout usage (line {node.lineno})")
            self.resiliency_score += 1
        
        # Look for retry patterns
        if (isinstance(node.func, ast.Name) and 
            'retry' in node.func.id.lower()):
            self.retry_patterns.append(f"Retry pattern (line {node.lineno})")
            self.resiliency_score += 2
            
        self.generic_visit(node)
    
    def visit_With(self, node):
        # Look for connection context managers
        for item in node.items:
            if (isinstance(item.context_expr, ast.Call) and
                isinstance(item.context_expr.func, ast.Attribute) and
                item.context_expr.func.attr in ['connect', 'session', 'client']):
                self.external_calls.append(f"Connection context manager (line {node.lineno})")
                self.resiliency_score += 2
        
        self.generic_visit(node)

def find_resiliency_candidates() -> List[Path]:
    """Find agents that would benefit from resiliency patterns"""
    root = Path.cwd()
    agent_files = []
    
    search_dirs = [
        "main_pc_code/agents",
        "pc2_code/agents", 
        "common",
        "phase1_implementation",
        "phase2_implementation"
    ]
    
    for search_dir in search_dirs:
        search_path = root / search_dir
        if search_path.exists():
            for python_file in search_path.rglob("*.py"):
                if (python_file.name != "__init__.py" and 
                    not python_file.name.startswith("test_") and
                    "_test" not in python_file.name):
                    agent_files.append(python_file)
    
    return agent_files

def analyze_resiliency_needs(file_path: Path) -> Dict:
    """Analyze a file for resiliency pattern needs"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = ResiliencyAnalyzer()
        analyzer.visit(tree)
        
        # Additional pattern-based analysis
        content_lower = content.lower()
        
        # External dependency patterns
        external_patterns = len(re.findall(r'(requests\.|http|socket|zmq|redis|psycopg|mysql)', content_lower))
        
        # Error handling patterns
        error_patterns = len(re.findall(r'(try:|except:|raise|error|exception)', content_lower))
        
        # Concurrency patterns
        concurrency_patterns = len(re.findall(r'(async |await |asyncio|threading|concurrent)', content_lower))
        
        # Timeout patterns
        timeout_patterns = len(re.findall(r'(timeout|deadline|ttl)', content_lower))
        
        # Calculate needs
        needs_circuit_breaker = external_patterns > 3 or analyzer.resiliency_score > 15
        needs_retry = external_patterns > 2 and error_patterns < 5
        needs_bulkhead = concurrency_patterns > 3 or analyzer.resiliency_score > 20
        needs_health_monitor = analyzer.resiliency_score > 10
        
        return {
            'file_path': file_path,
            'external_calls': analyzer.external_calls,
            'error_handlers': analyzer.error_handlers,
            'timeout_patterns': analyzer.timeout_patterns,
            'retry_patterns': analyzer.retry_patterns,
            'concurrency_patterns': analyzer.concurrency_patterns,
            'external_count': external_patterns,
            'error_count': error_patterns,
            'concurrency_count': concurrency_patterns,
            'timeout_count': timeout_patterns,
            'resiliency_score': analyzer.resiliency_score + external_patterns + concurrency_patterns,
            'needs_circuit_breaker': needs_circuit_breaker,
            'needs_retry': needs_retry,
            'needs_bulkhead': needs_bulkhead,
            'needs_health_monitor': needs_health_monitor,
            'priority': 'high' if analyzer.resiliency_score > 20 else 'medium' if analyzer.resiliency_score > 10 else 'low'
        }
    
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e),
            'resiliency_score': 0,
            'needs_circuit_breaker': False,
            'needs_retry': False,
            'needs_bulkhead': False,
            'needs_health_monitor': False,
            'priority': 'low'
        }

def generate_circuit_breaker_integration(file_path: Path) -> str:
    """Generate circuit breaker integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-07 Circuit Breaker Integration for {agent_name}
# Add circuit breaker protection for external calls

from common.resiliency.circuit_breaker import (
    get_circuit_breaker, CircuitBreakerConfig, circuit_breaker
)

class {agent_name.title().replace("_", "")}CircuitBreakers:
    """Circuit breaker management for {agent_name}"""
    
    def __init__(self):
        # Configure circuit breakers for different services
        self.api_breaker = get_circuit_breaker(
            "{agent_name}_api",
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout_duration=60.0,
                request_timeout=30.0
            )
        )
        
        self.db_breaker = get_circuit_breaker(
            "{agent_name}_database",
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_duration=30.0,
                request_timeout=10.0
            )
        )
    
    async def make_api_call(self, endpoint, data=None):
        """Make API call with circuit breaker protection"""
        async def api_call():
            # Your original API call code here
            response = await some_api_client.post(endpoint, json=data)
            return response.json()
        
        return await self.api_breaker.call_async(api_call)
    
    async def query_database(self, query, params=None):
        """Query database with circuit breaker protection"""
        def db_query():
            # Your original database query code here
            with database.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        
        return await self.db_breaker.call_async(db_query)

# Using decorators for automatic protection
@circuit_breaker(name="{agent_name}_external_service")
async def call_external_service(data):
    """External service call with automatic circuit breaker"""
    # Your external service call here
    return await external_service.process(data)

# Example usage:
# breakers = {agent_name.title().replace("_", "")}CircuitBreakers()
# result = await breakers.make_api_call("/process", {{"data": "example"}})
# status = breakers.api_breaker.get_metrics()
'''
    
    return integration_example

def generate_retry_integration(file_path: Path) -> str:
    """Generate retry mechanism integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-07 Retry Integration for {agent_name}
# Add intelligent retry logic with exponential backoff

from common.resiliency.retry import (
    RetryManager, RetryConfig, RetryStrategy, JitterType, retry
)

class {agent_name.title().replace("_", "")}RetryManager:
    """Retry management for {agent_name}"""
    
    def __init__(self):
        # Configure retry strategies for different operations
        self.api_retry = RetryManager(RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter_type=JitterType.UNIFORM,
            retryable_exceptions=[ConnectionError, TimeoutError]
        ))
        
        self.critical_retry = RetryManager(RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=60.0,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        ))
    
    async def reliable_api_call(self, endpoint, data=None):
        """API call with retry logic"""
        async def api_operation():
            response = await api_client.post(endpoint, json=data)
            if response.status_code >= 500:
                raise ConnectionError("Server error")
            return response.json()
        
        return await self.api_retry.execute_async(api_operation)
    
    async def critical_operation(self, data):
        """Critical operation with aggressive retry"""
        def operation():
            result = process_critical_data(data)
            if not result.success:
                raise RuntimeError("Processing failed")
            return result
        
        return await self.critical_retry.execute_async(operation)

# Using decorators for automatic retry
@retry(
    max_attempts=3,
    base_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=[ConnectionError, TimeoutError]
)
async def network_operation(data):
    """Network operation with automatic retry"""
    return await network_service.send(data)

# Combined with circuit breaker
from common.resiliency.retry import retry_with_circuit_breaker

@retry_with_circuit_breaker(
    retry_config=RetryConfig(max_attempts=3),
    circuit_breaker_name="{agent_name}_combined"
)
async def resilient_operation(data):
    """Operation with both retry and circuit breaker"""
    return await external_service.process(data)

# Example usage:
# retry_manager = {agent_name.title().replace("_", "")}RetryManager()
# result = await retry_manager.reliable_api_call("/process", {{"data": "example"}})
'''
    
    return integration_example

def generate_bulkhead_integration(file_path: Path) -> str:
    """Generate bulkhead isolation integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-07 Bulkhead Integration for {agent_name}
# Add resource isolation to prevent cascading failures

from common.resiliency.bulkhead import (
    get_bulkhead, BulkheadConfig, IsolationStrategy, bulkhead
)

class {agent_name.title().replace("_", "")}Bulkheads:
    """Bulkhead isolation for {agent_name}"""
    
    def __init__(self):
        # Critical operations bulkhead
        self.critical_bulkhead = get_bulkhead(
            "{agent_name}_critical",
            max_concurrent=5,
            timeout=60.0,
            isolation_strategy=IsolationStrategy.SEMAPHORE
        )
        
        # Background tasks bulkhead
        self.background_bulkhead = get_bulkhead(
            "{agent_name}_background",
            max_concurrent=20,
            max_queue_size=100,
            timeout=30.0,
            isolation_strategy=IsolationStrategy.THREAD_POOL
        )
        
        # External API bulkhead
        self.api_bulkhead = get_bulkhead(
            "{agent_name}_api",
            max_concurrent=10,
            timeout=45.0,
            isolation_strategy=IsolationStrategy.ASYNC_SEMAPHORE
        )
    
    async def critical_processing(self, data):
        """Critical processing with resource isolation"""
        async def process():
            # Your critical processing logic here
            result = await process_important_data(data)
            return result
        
        return await self.critical_bulkhead.execute_async(process)
    
    async def background_task(self, task_data):
        """Background task with isolation"""
        def task():
            # Your background task logic here
            return perform_background_work(task_data)
        
        return await self.background_bulkhead.execute_async(task)
    
    async def api_call(self, endpoint, data):
        """API call with isolation"""
        async def call():
            response = await api_client.post(endpoint, json=data)
            return response.json()
        
        return await self.api_bulkhead.execute_async(call)

# Using decorators for automatic isolation
@bulkhead(
    name="{agent_name}_heavy_computation",
    max_concurrent=3,
    timeout=120.0,
    isolation_strategy=IsolationStrategy.THREAD_POOL
)
async def heavy_computation(data):
    """Heavy computation with automatic isolation"""
    return await compute_intensive_operation(data)

@bulkhead(
    name="{agent_name}_external_calls",
    max_concurrent=15,
    timeout=30.0
)
async def external_service_call(service_url, payload):
    """External service call with isolation"""
    return await external_service.request(service_url, payload)

# Example usage:
# bulkheads = {agent_name.title().replace("_", "")}Bulkheads()
# result = await bulkheads.critical_processing(important_data)
# metrics = bulkheads.critical_bulkhead.get_metrics()
'''
    
    return integration_example

def generate_health_monitoring_integration(file_path: Path) -> str:
    """Generate health monitoring integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-07 Health Monitoring Integration for {agent_name}
# Add health checks and monitoring

from common.resiliency.health_monitor import (
    get_health_monitor, HealthCheck, HealthStatus
)

class {agent_name.title().replace("_", "")}HealthMonitor:
    """Health monitoring for {agent_name}"""
    
    def __init__(self):
        self.monitor = get_health_monitor()
        self._register_health_checks()
    
    def _register_health_checks(self):
        """Register health checks for this agent"""
        
        # Basic connectivity check
        self.monitor.register_health_check(HealthCheck(
            name="{agent_name}_connectivity",
            check_function=self._check_connectivity,
            timeout=10.0,
            interval=30.0,
            critical=True,
            description="Check network connectivity"
        ))
        
        # Resource availability check
        self.monitor.register_health_check(HealthCheck(
            name="{agent_name}_resources",
            check_function=self._check_resources,
            timeout=5.0,
            interval=60.0,
            critical=False,
            description="Check resource availability"
        ))
        
        # Service dependency check
        self.monitor.register_health_check(HealthCheck(
            name="{agent_name}_dependencies",
            check_function=self._check_dependencies,
            timeout=15.0,
            interval=45.0,
            critical=True,
            description="Check service dependencies"
        ))
    
    async def _check_connectivity(self) -> bool:
        """Check if agent can connect to required services"""
        try:
            # Your connectivity check logic here
            response = await test_connection()
            return response.status == "ok"
        except Exception:
            return False
    
    async def _check_resources(self) -> bool:
        """Check if required resources are available"""
        try:
            # Your resource check logic here
            memory_usage = get_memory_usage()
            cpu_usage = get_cpu_usage()
            return memory_usage < 0.9 and cpu_usage < 0.8
        except Exception:
            return False
    
    async def _check_dependencies(self) -> bool:
        """Check if service dependencies are healthy"""
        try:
            # Your dependency check logic here
            services = ["database", "redis", "external_api"]
            for service in services:
                if not await check_service_health(service):
                    return False
            return True
        except Exception:
            return False
    
    async def get_health_status(self):
        """Get current health status"""
        return self.monitor.get_health_status()
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        await self.monitor.start_monitoring(interval=30.0)
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        await self.monitor.stop_monitoring()

# Example usage:
# health_monitor = {agent_name.title().replace("_", "")}HealthMonitor()
# await health_monitor.start_monitoring()
# status = await health_monitor.get_health_status()
'''
    
    return integration_example

def update_requirements_for_resiliency():
    """Update requirements.txt with resiliency dependencies"""
    requirements_path = Path("requirements.txt")
    
    try:
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        # Resiliency dependencies
        new_deps = [
            "# WP-07 Resiliency Dependencies",
            "tenacity==8.2.3",
            "pybreaker==0.7.0"
        ]
        
        # Add dependencies if not already present
        for dep in new_deps:
            dep_name = dep.split('==')[0].replace("# ", "")
            if dep_name not in content:
                content += f"\n{dep}"
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated requirements.txt with resiliency dependencies")
        return True
    
    except Exception as e:
        print(f"❌ Error updating requirements.txt: {e}")
        return False

def main():
    print("🚀 WP-07: RESILIENCY MIGRATION")
    print("=" * 50)
    
    # Update requirements first
    update_requirements_for_resiliency()
    
    # Find resiliency candidates
    agent_files = find_resiliency_candidates()
    print(f"📁 Found {len(agent_files)} agent files to analyze")
    
    # Analyze resiliency needs
    analysis_results = []
    for agent_file in agent_files:
        result = analyze_resiliency_needs(agent_file)
        analysis_results.append(result)
    
    # Sort by resiliency score
    analysis_results.sort(key=lambda x: x.get('resiliency_score', 0), reverse=True)
    
    # Filter candidates
    high_priority = [r for r in analysis_results if r.get('resiliency_score', 0) >= 20]
    circuit_breaker_candidates = [r for r in analysis_results if r.get('needs_circuit_breaker', False)]
    retry_candidates = [r for r in analysis_results if r.get('needs_retry', False)]
    bulkhead_candidates = [r for r in analysis_results if r.get('needs_bulkhead', False)]
    health_candidates = [r for r in analysis_results if r.get('needs_health_monitor', False)]
    
    print(f"\n📊 RESILIENCY ANALYSIS:")
    print(f"✅ High priority targets: {len(high_priority)}")
    print(f"🔌 Circuit breaker candidates: {len(circuit_breaker_candidates)}")
    print(f"🔄 Retry candidates: {len(retry_candidates)}")
    print(f"🛡️  Bulkhead candidates: {len(bulkhead_candidates)}")
    print(f"❤️  Health monitor candidates: {len(health_candidates)}")
    
    # Show top agents needing resiliency
    if high_priority:
        print(f"\n🎯 TOP RESILIENCY TARGETS:")
        for result in high_priority[:10]:  # Show top 10
            file_path = result['file_path']
            score = result.get('resiliency_score', 0)
            print(f"\n📄 {file_path} (Score: {score})")
            print(f"   🔌 External calls: {result.get('external_count', 0)}")
            print(f"   🔄 Error handlers: {result.get('error_count', 0)}")
            print(f"   🛡️  Concurrency: {result.get('concurrency_count', 0)}")
            print(f"   🎯 Priority: {result.get('priority', 'low')}")
    
    # Generate integration examples
    examples_dir = Path("docs/resiliency_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    for result in high_priority[:15]:  # Top 15 candidates
        file_path = result['file_path']
        agent_name = file_path.stem
        
        # Generate circuit breaker example
        if result.get('needs_circuit_breaker'):
            cb_example = generate_circuit_breaker_integration(file_path)
            cb_file = examples_dir / f"{agent_name}_circuit_breaker.py"
            with open(cb_file, 'w') as f:
                f.write(cb_example)
        
        # Generate retry example
        if result.get('needs_retry'):
            retry_example = generate_retry_integration(file_path)
            retry_file = examples_dir / f"{agent_name}_retry.py"
            with open(retry_file, 'w') as f:
                f.write(retry_example)
        
        # Generate bulkhead example
        if result.get('needs_bulkhead'):
            bulkhead_example = generate_bulkhead_integration(file_path)
            bulkhead_file = examples_dir / f"{agent_name}_bulkhead.py"
            with open(bulkhead_file, 'w') as f:
                f.write(bulkhead_example)
        
        # Generate health monitoring example
        if result.get('needs_health_monitor'):
            health_example = generate_health_monitoring_integration(file_path)
            health_file = examples_dir / f"{agent_name}_health.py"
            with open(health_file, 'w') as f:
                f.write(health_example)
        
        generated_count += 1
    
    print(f"\n✅ WP-07 RESILIENCY ANALYSIS COMPLETE!")
    print(f"🔌 Circuit breaker candidates: {len(circuit_breaker_candidates)} agents")
    print(f"🔄 Retry candidates: {len(retry_candidates)} agents")
    print(f"🛡️  Bulkhead candidates: {len(bulkhead_candidates)} agents")
    print(f"❤️  Health monitor candidates: {len(health_candidates)} agents")
    print(f"📝 Generated examples: {generated_count} agents")
    
    print(f"\n🚀 Resiliency Benefits:")
    print(f"🔌 Circuit breakers prevent cascading failures")
    print(f"🔄 Intelligent retry with exponential backoff")
    print(f"🛡️  Resource isolation prevents system overload")
    print(f"❤️  Health monitoring enables proactive maintenance")
    print(f"📊 Comprehensive metrics and monitoring")
    
    print(f"\n🚀 Next Steps:")
    print(f"1. Resiliency patterns implemented in common/resiliency/")
    print(f"2. Integration examples: docs/resiliency_examples/")
    print(f"3. Use: from common.resiliency.circuit_breaker import get_circuit_breaker")
    print(f"4. Use: from common.resiliency.retry import retry")
    print(f"5. Use: from common.resiliency.bulkhead import bulkhead")

if __name__ == "__main__":
    main() 