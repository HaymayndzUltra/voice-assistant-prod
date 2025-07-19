#!/usr/bin/env python3
"""
WP-09 Distributed Logging & Observability Migration Script
Migrates agents to use structured logging, distributed tracing, and metrics collection
Target: All agents for comprehensive observability
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ObservabilityAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect observability opportunities"""
    
    def __init__(self):
        self.logging_patterns = []
        self.error_handling_patterns = []
        self.api_endpoints = []
        self.function_calls = []
        self.async_operations = []
        self.database_operations = []
        self.observability_score = 0
        
    def visit_FunctionDef(self, node):
        # Check for existing logging
        has_logging = False
        has_error_handling = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['info', 'debug', 'warning', 'error', 'critical']):
                    has_logging = True
                    self.logging_patterns.append(f"Existing logging in {node.name} (line {child.lineno})")
                
                # Look for API calls
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['get', 'post', 'put', 'delete', 'request']):
                    self.api_endpoints.append(f"API call in {node.name} (line {child.lineno})")
                    self.observability_score += 3
                
                # Look for database operations
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['execute', 'query', 'insert', 'update', 'delete', 'find']):
                    self.database_operations.append(f"Database operation in {node.name} (line {child.lineno})")
                    self.observability_score += 2
            
            # Check for try/except blocks
            if isinstance(child, ast.Try):
                has_error_handling = True
                self.error_handling_patterns.append(f"Error handling in {node.name} (line {child.lineno})")
        
        # Check if function is async
        if isinstance(node, ast.AsyncFunctionDef):
            self.async_operations.append(f"Async function: {node.name} (line {node.lineno})")
            self.observability_score += 1
        
        # Score based on complexity
        if not has_logging and len(list(ast.walk(node))) > 10:
            self.observability_score += 2  # Complex function without logging
        
        if not has_error_handling:
            self.observability_score += 1  # No error handling
        
        self.function_calls.append(f"Function: {node.name} (line {node.lineno})")
        
        self.generic_visit(node)
    
    def visit_With(self, node):
        # Look for context managers that could be traced
        if isinstance(node, ast.With):
            self.observability_score += 1
        
        self.generic_visit(node)

def find_observability_candidates() -> List[Path]:
    """Find agents that would benefit from observability"""
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

def analyze_observability_needs(file_path: Path) -> Dict:
    """Analyze a file for observability needs"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = ObservabilityAnalyzer()
        analyzer.visit(tree)
        
        # Additional pattern-based analysis
        content_lower = content.lower()
        
        # Logging patterns
        existing_logging = len(re.findall(r'(logger\.|logging\.|print\()', content_lower))
        
        # Error handling patterns
        error_handling = len(re.findall(r'(try:|except|raise|error)', content_lower))
        
        # Performance patterns
        performance_patterns = len(re.findall(r'(time\.|timer|benchmark|measure)', content_lower))
        
        # API patterns
        api_patterns = len(re.findall(r'(requests\.|http|api|endpoint)', content_lower))
        
        # Database patterns
        db_patterns = len(re.findall(r'(select|insert|update|delete|query|database)', content_lower))
        
        # Calculate needs
        needs_logging = (analyzer.observability_score > 5 or 
                        existing_logging < 3 and len(analyzer.function_calls) > 5)
        
        needs_tracing = (len(analyzer.api_endpoints) > 0 or 
                        len(analyzer.async_operations) > 3 or
                        api_patterns > 2)
        
        needs_metrics = (len(analyzer.database_operations) > 0 or 
                        api_patterns > 1 or
                        performance_patterns > 0)
        
        needs_monitoring = (analyzer.observability_score > 10 or 
                           len(analyzer.function_calls) > 10)
        
        return {
            'file_path': file_path,
            'logging_patterns': analyzer.logging_patterns,
            'error_handling_patterns': analyzer.error_handling_patterns,
            'api_endpoints': analyzer.api_endpoints,
            'function_calls': analyzer.function_calls,
            'async_operations': analyzer.async_operations,
            'database_operations': analyzer.database_operations,
            'existing_logging_count': existing_logging,
            'error_handling_count': error_handling,
            'api_count': api_patterns,
            'db_count': db_patterns,
            'observability_score': analyzer.observability_score + existing_logging + error_handling,
            'needs_logging': needs_logging,
            'needs_tracing': needs_tracing,
            'needs_metrics': needs_metrics,
            'needs_monitoring': needs_monitoring,
            'priority': 'high' if analyzer.observability_score > 15 else 'medium' if analyzer.observability_score > 8 else 'low'
        }
    
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e),
            'observability_score': 0,
            'needs_logging': False,
            'needs_tracing': False,
            'needs_metrics': False,
            'needs_monitoring': False,
            'priority': 'low'
        }

def generate_logging_integration(file_path: Path) -> str:
    """Generate logging integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-09 Distributed Logging Integration for {agent_name}
# Add structured logging with correlation IDs and comprehensive observability

from common.observability.logging import (
    get_distributed_logger, LogLevel, LogCategory, log_function_calls, log_exceptions
)

class {agent_name.title().replace("_", "")}LoggingIntegration:
    """Logging integration for {agent_name}"""
    
    def __init__(self):
        self.logger = get_distributed_logger()
        
        # Set default context for this agent
        self.logger.set_default_context(
            agent_id="{agent_name}",
            source="{agent_name}",
            environment="production"
        )
    
    @log_function_calls(level=LogLevel.INFO, category=LogCategory.AGENT)
    async def main_operation(self, data):
        """Main operation with automatic logging"""
        
        # Structured logging with context
        async with self.logger.async_context(operation="main_operation", user_id="user123"):
            await self.logger.info(
                "Starting main operation",
                category=LogCategory.AGENT,
                data={{"input_size": len(data), "operation": "main_operation"}},
                tags=["operation_start"]
            )
            
            try:
                result = await self.process_data(data)
                
                # Log success with performance metrics
                await self.logger.info(
                    "Main operation completed successfully",
                    category=LogCategory.AGENT,
                    data={{"result_size": len(result)}},
                    performance_metrics={{"processing_time": 1.23}},
                    tags=["operation_success"]
                )
                
                return result
                
            except Exception as e:
                # Structured error logging
                await self.logger.error(
                    "Main operation failed",
                    category=LogCategory.AGENT,
                    exception=e,
                    data={{"input_data": str(data)[:100]}},
                    tags=["operation_error"]
                )
                raise
    
    @log_exceptions(level=LogLevel.ERROR, category=LogCategory.API)
    async def api_call(self, endpoint: str, params: dict):
        """API call with automatic error logging"""
        
        # Log API request
        async with self.logger.async_context(operation="api_call", endpoint=endpoint):
            await self.logger.debug(
                f"Making API call to {{endpoint}}",
                category=LogCategory.API,
                data={{"endpoint": endpoint, "params": params}},
                tags=["api_request"]
            )
            
            # Your API call logic here
            response = await make_api_call(endpoint, params)
            
            # Log API response
            await self.logger.info(
                f"API call successful",
                category=LogCategory.API,
                data={{"status_code": response.status_code, "response_size": len(response.text)}},
                tags=["api_response", "success"]
            )
            
            return response
    
    async def database_operation(self, query: str, params: list):
        """Database operation with performance logging"""
        
        async with self.logger.async_context(operation="database", query_type="select"):
            start_time = time.time()
            
            await self.logger.debug(
                "Executing database query",
                category=LogCategory.SYSTEM,
                data={{"query": query[:100], "param_count": len(params)}},
                tags=["db_query"]
            )
            
            try:
                result = await execute_query(query, params)
                duration = time.time() - start_time
                
                await self.logger.info(
                    "Database query completed",
                    category=LogCategory.SYSTEM,
                    data={{"rows_affected": len(result)}},
                    performance_metrics={{"query_duration": duration}},
                    tags=["db_success"]
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                await self.logger.error(
                    "Database query failed",
                    category=LogCategory.SYSTEM,
                    exception=e,
                    data={{"query": query[:100]}},
                    performance_metrics={{"query_duration": duration}},
                    tags=["db_error"]
                )
                raise
    
    async def business_logic(self, user_id: str, action: str, data: dict):
        """Business logic with business category logging"""
        
        async with self.logger.async_context(user_id=user_id, operation=action):
            await self.logger.info(
                f"User {{user_id}} performing {{action}}",
                category=LogCategory.BUSINESS,
                data={{"action": action, "data_keys": list(data.keys())}},
                tags=["user_action", action]
            )
            
            # Your business logic here
            result = await process_business_logic(user_id, action, data)
            
            await self.logger.info(
                f"Business action {{action}} completed for user {{user_id}}",
                category=LogCategory.BUSINESS,
                data={{"success": True, "result_type": type(result).__name__}},
                tags=["business_success", action]
            )
            
            return result

# Example usage:
# logging_integration = {agent_name.title().replace("_", "")}LoggingIntegration()
# result = await logging_integration.main_operation(data)
# response = await logging_integration.api_call("/users", {{"limit": 10}})
'''
    
    return integration_example

def generate_tracing_integration(file_path: Path) -> str:
    """Generate tracing integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-09 Distributed Tracing Integration for {agent_name}
# Add request correlation and performance analysis across operations

from common.observability.tracing import (
    get_tracer, trace_function, SpanKind, get_current_trace_id
)

class {agent_name.title().replace("_", "")}TracingIntegration:
    """Tracing integration for {agent_name}"""
    
    def __init__(self):
        self.tracer = get_tracer("{agent_name}_service")
    
    @trace_function(operation_name="{agent_name}_main_flow", kind=SpanKind.SERVER)
    async def main_flow(self, request_data):
        """Main flow with distributed tracing"""
        
        # The decorator automatically creates a span
        # We can access the current trace ID for logging correlation
        trace_id = get_current_trace_id()
        print(f"Processing request with trace ID: {{trace_id}}")
        
        # Process the request
        result = await self.process_request(request_data)
        return result
    
    async def process_request(self, request_data):
        """Process request with manual span creation"""
        
        async with self.tracer.async_span("process_request", kind=SpanKind.INTERNAL) as span:
            # Add tags to span
            span.set_tags({{
                "request.size": len(str(request_data)),
                "request.type": type(request_data).__name__,
                "agent.name": "{agent_name}"
            }})
            
            # Log events to span
            span.log_event("request_validation_started")
            
            # Validate request
            if not self.validate_request(request_data):
                span.log_event("request_validation_failed", reason="invalid_format")
                span.set_tag("error", True)
                raise ValueError("Invalid request format")
            
            span.log_event("request_validation_completed")
            
            # Process data
            span.log_event("data_processing_started")
            result = await self.process_data(request_data)
            span.log_event("data_processing_completed")
            
            # Set result metadata
            span.set_tag("result.size", len(str(result)))
            span.set_tag("success", True)
            
            return result
    
    async def external_api_call(self, endpoint: str, data: dict):
        """External API call with client span"""
        
        async with self.tracer.async_span(
            f"http_call_{{endpoint.split('/')[-1]}}", 
            kind=SpanKind.CLIENT
        ) as span:
            
            # Set HTTP-specific tags
            span.set_tags({{
                "http.method": "POST",
                "http.url": endpoint,
                "http.user_agent": "{agent_name}_client",
                "component": "http_client"
            }})
            
            try:
                # Make API call
                response = await make_http_request(endpoint, data)
                
                # Set response tags
                span.set_tags({{
                    "http.status_code": response.status_code,
                    "http.response_size": len(response.content)
                }})
                
                if response.status_code >= 400:
                    span.log_event("http_error", 
                                 status_code=response.status_code,
                                 error_body=response.text[:200])
                    span.set_tag("error", True)
                
                return response
                
            except Exception as e:
                span.log_error(e)
                span.set_tag("error", True)
                raise
    
    async def database_query(self, query: str, params: list):
        """Database query with tracing"""
        
        async with self.tracer.async_span("db_query", kind=SpanKind.CLIENT) as span:
            # Set database-specific tags
            span.set_tags({{
                "db.type": "postgresql",
                "db.statement": query[:100] + "..." if len(query) > 100 else query,
                "db.params_count": len(params),
                "component": "database"
            }})
            
            try:
                result = await execute_database_query(query, params)
                
                span.set_tags({{
                    "db.rows_affected": len(result),
                    "db.success": True
                }})
                
                return result
                
            except Exception as e:
                span.log_error(e, query=query, params_count=len(params))
                span.set_tag("db.success", False)
                raise
    
    async def message_processing(self, message: dict):
        """Message processing with producer/consumer spans"""
        
        # Consumer span for receiving message
        async with self.tracer.async_span("message_consume", kind=SpanKind.CONSUMER) as consume_span:
            consume_span.set_tags({{
                "message.queue": "processing_queue",
                "message.id": message.get("id", "unknown"),
                "message.type": message.get("type", "unknown")
            }})
            
            # Process message
            processed_data = await self.process_message_data(message)
            
            # Producer span for sending result
            async with self.tracer.async_span("message_produce", kind=SpanKind.PRODUCER) as produce_span:
                produce_span.set_tags({{
                    "message.queue": "results_queue",
                    "message.result_type": type(processed_data).__name__
                }})
                
                await send_result_message(processed_data)
                
                produce_span.log_event("message_sent", 
                                     queue="results_queue",
                                     message_size=len(str(processed_data)))
        
        return processed_data

# Example usage:
# tracing = {agent_name.title().replace("_", "")}TracingIntegration()
# result = await tracing.main_flow(request_data)
# response = await tracing.external_api_call("/api/process", data)
'''
    
    return integration_example

def generate_metrics_integration(file_path: Path) -> str:
    """Generate metrics integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-09 Metrics Integration for {agent_name}
# Add comprehensive metrics collection and monitoring

from common.observability.metrics import (
    get_metrics_registry, counter, gauge, histogram, timer, 
    measure_time, count_calls, measure_errors
)

class {agent_name.title().replace("_", "")}MetricsIntegration:
    """Metrics integration for {agent_name}"""
    
    def __init__(self):
        self.registry = get_metrics_registry()
        
        # Create agent-specific metrics
        self.request_counter = counter("{agent_name}.requests")
        self.active_connections = gauge("{agent_name}.active_connections") 
        self.response_time = histogram("{agent_name}.response_time")
        self.operation_timer = timer("{agent_name}.operation_duration")
        
        # Add default tags for this agent
        self.request_counter.add_tags(agent="{agent_name}", version="1.0")
    
    @measure_time(metric_name="{agent_name}.main_operation_time")
    @count_calls(metric_name="{agent_name}.main_operation_calls")
    @measure_errors(metric_name="{agent_name}.main_operation_errors")
    async def main_operation(self, data):
        """Main operation with automatic metrics"""
        
        # Increment active connections
        self.active_connections.increment()
        
        try:
            # Count request by type
            self.request_counter.increment(request_type="main_operation", data_size=len(str(data)))
            
            # Time the operation manually
            with self.operation_timer.time_context(operation="main_processing"):
                result = await self.process_data(data)
            
            # Record response time
            response_time_ms = 123.45  # Your actual measurement
            self.response_time.observe(response_time_ms / 1000, operation="main")
            
            # Success metrics
            counter("{agent_name}.operations").increment(status="success", operation="main")
            
            return result
            
        finally:
            # Decrement active connections
            self.active_connections.decrement()
    
    async def api_request_metrics(self, endpoint: str, method: str, status_code: int, duration: float):
        """Collect API request metrics"""
        
        # Request counter with detailed tags
        counter("{agent_name}.api.requests").increment(
            endpoint=endpoint,
            method=method,
            status=str(status_code),
            status_class=f"{{status_code // 100}}xx"
        )
        
        # Response time histogram
        histogram("{agent_name}.api.response_time", 
                 buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]).observe(
            duration,
            endpoint=endpoint,
            method=method
        )
        
        # Error counter
        if status_code >= 400:
            counter("{agent_name}.api.errors").increment(
                endpoint=endpoint,
                status=str(status_code)
            )
    
    async def database_metrics(self, operation: str, table: str, duration: float, rows: int):
        """Collect database operation metrics"""
        
        # Query counter
        counter("{agent_name}.db.queries").increment(
            operation=operation,
            table=table
        )
        
        # Query duration
        histogram("{agent_name}.db.query_duration",
                 buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]).observe(
            duration,
            operation=operation,
            table=table
        )
        
        # Rows affected
        histogram("{agent_name}.db.rows_affected",
                 buckets=[1, 10, 100, 1000, 10000]).observe(
            rows,
            operation=operation,
            table=table
        )
    
    async def business_metrics(self, user_id: str, action: str, success: bool):
        """Collect business logic metrics"""
        
        # User action counter
        counter("{agent_name}.business.actions").increment(
            action=action,
            success=str(success)
        )
        
        # Active users gauge (simplified)
        gauge("{agent_name}.business.active_users").set(get_active_user_count())
        
        # Success rate tracking
        if success:
            counter("{agent_name}.business.successes").increment(action=action)
        else:
            counter("{agent_name}.business.failures").increment(action=action)
    
    def setup_alerts(self):
        """Setup metric-based alerts"""
        from common.observability.metrics import Alert, AlertLevel
        
        # High error rate alert
        error_rate_alert = Alert(
            name="{agent_name}_high_error_rate",
            metric_name="{agent_name}.api.errors",
            condition="> 10",  # More than 10 errors per minute
            level=AlertLevel.ERROR,
            message="High error rate detected in {agent_name}",
            cooldown=300.0  # 5 minutes
        )
        
        # Slow response time alert
        slow_response_alert = Alert(
            name="{agent_name}_slow_response",
            metric_name="{agent_name}.api.response_time",
            condition="> 5.0",  # Responses slower than 5 seconds
            level=AlertLevel.WARNING,
            message="Slow response times detected in {agent_name}",
            cooldown=600.0  # 10 minutes
        )
        
        # High memory usage alert
        memory_alert = Alert(
            name="{agent_name}_high_memory",
            metric_name="{agent_name}.memory.usage",
            condition="> 0.8",  # More than 80% memory usage
            level=AlertLevel.CRITICAL,
            message="High memory usage in {agent_name}",
            cooldown=300.0  # 5 minutes
        )
        
        # Add alerts to registry
        self.registry.add_alert(error_rate_alert)
        self.registry.add_alert(slow_response_alert)
        self.registry.add_alert(memory_alert)
    
    def get_health_metrics(self) -> dict:
        """Get current health metrics"""
        return {{
            "active_connections": self.active_connections.get_value(),
            "total_requests": self.request_counter.get_value(),
            "response_time_stats": self.response_time.get_statistics(),
            "operation_stats": self.operation_timer.get_statistics()
        }}

# Example usage:
# metrics = {agent_name.title().replace("_", "")}MetricsIntegration()
# await metrics.main_operation(data)
# await metrics.api_request_metrics("/api/test", "GET", 200, 0.123)
# await metrics.business_metrics("user123", "purchase", True)
# health = metrics.get_health_metrics()
'''
    
    return integration_example

def update_requirements_for_observability():
    """Update requirements.txt with observability dependencies"""
    requirements_path = Path("requirements.txt")
    
    try:
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        # Observability dependencies
        new_deps = [
            "# WP-09 Distributed Logging & Observability Dependencies",
            "structlog==23.2.0",
            "python-json-logger==2.0.7",
            "opentelemetry-api==1.21.0",
            "opentelemetry-sdk==1.21.0",
            "prometheus-client==0.19.0"
        ]
        
        # Add dependencies if not already present
        for dep in new_deps:
            dep_name = dep.split('==')[0].replace("# ", "")
            if dep_name not in content:
                content += f"\n{dep}"
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated requirements.txt with observability dependencies")
        return True
    
    except Exception as e:
        print(f"❌ Error updating requirements.txt: {e}")
        return False

def main():
    print("🚀 WP-09: DISTRIBUTED LOGGING & OBSERVABILITY MIGRATION")
    print("=" * 60)
    
    # Update requirements first
    update_requirements_for_observability()
    
    # Find observability candidates
    agent_files = find_observability_candidates()
    print(f"📁 Found {len(agent_files)} agent files to analyze")
    
    # Analyze observability needs
    analysis_results = []
    for agent_file in agent_files:
        result = analyze_observability_needs(agent_file)
        analysis_results.append(result)
    
    # Sort by observability score
    analysis_results.sort(key=lambda x: x.get('observability_score', 0), reverse=True)
    
    # Filter candidates
    high_priority = [r for r in analysis_results if r.get('observability_score', 0) >= 15]
    logging_candidates = [r for r in analysis_results if r.get('needs_logging', False)]
    tracing_candidates = [r for r in analysis_results if r.get('needs_tracing', False)]
    metrics_candidates = [r for r in analysis_results if r.get('needs_metrics', False)]
    monitoring_candidates = [r for r in analysis_results if r.get('needs_monitoring', False)]
    
    print(f"\n📊 OBSERVABILITY ANALYSIS:")
    print(f"✅ High priority targets: {len(high_priority)}")
    print(f"📝 Logging candidates: {len(logging_candidates)}")
    print(f"🔍 Tracing candidates: {len(tracing_candidates)}")
    print(f"📊 Metrics candidates: {len(metrics_candidates)}")
    print(f"🖥️  Monitoring candidates: {len(monitoring_candidates)}")
    
    # Show top agents needing observability
    if high_priority:
        print(f"\n🎯 TOP OBSERVABILITY TARGETS:")
        for result in high_priority[:10]:  # Show top 10
            file_path = result['file_path']
            score = result.get('observability_score', 0)
            print(f"\n📄 {file_path} (Score: {score})")
            print(f"   📝 Logging: {'✅' if result.get('needs_logging') else '❌'}")
            print(f"   🔍 Tracing: {'✅' if result.get('needs_tracing') else '❌'}")
            print(f"   📊 Metrics: {'✅' if result.get('needs_metrics') else '❌'}")
            print(f"   🖥️  Monitoring: {'✅' if result.get('needs_monitoring') else '❌'}")
            print(f"   🎯 Priority: {result.get('priority', 'low')}")
    
    # Generate integration examples
    examples_dir = Path("docs/observability_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    for result in high_priority[:15]:  # Top 15 candidates
        file_path = result['file_path']
        agent_name = file_path.stem
        
        # Generate logging example
        if result.get('needs_logging'):
            logging_example = generate_logging_integration(file_path)
            logging_file = examples_dir / f"{agent_name}_logging.py"
            with open(logging_file, 'w') as f:
                f.write(logging_example)
        
        # Generate tracing example
        if result.get('needs_tracing'):
            tracing_example = generate_tracing_integration(file_path)
            tracing_file = examples_dir / f"{agent_name}_tracing.py"
            with open(tracing_file, 'w') as f:
                f.write(tracing_example)
        
        # Generate metrics example
        if result.get('needs_metrics'):
            metrics_example = generate_metrics_integration(file_path)
            metrics_file = examples_dir / f"{agent_name}_metrics.py"
            with open(metrics_file, 'w') as f:
                f.write(metrics_example)
        
        generated_count += 1
    
    print(f"\n✅ WP-09 OBSERVABILITY ANALYSIS COMPLETE!")
    print(f"📝 Logging candidates: {len(logging_candidates)} agents")
    print(f"🔍 Tracing candidates: {len(tracing_candidates)} agents")
    print(f"📊 Metrics candidates: {len(metrics_candidates)} agents")
    print(f"🖥️  Monitoring candidates: {len(monitoring_candidates)} agents")
    print(f"📝 Generated examples: {generated_count} agents")
    
    print(f"\n🚀 Observability Benefits:")
    print(f"📝 Structured logging with correlation IDs")
    print(f"🔍 Distributed tracing across agents")
    print(f"📊 Comprehensive metrics collection")
    print(f"🚨 Real-time alerting and monitoring")
    print(f"🔍 Root cause analysis capabilities")
    
    print(f"\n🚀 Next Steps:")
    print(f"1. Observability system implemented in common/observability/")
    print(f"2. Integration examples: docs/observability_examples/")
    print(f"3. Use: from common.observability.logging import get_distributed_logger")
    print(f"4. Use: from common.observability.tracing import get_tracer")
    print(f"5. Use: from common.observability.metrics import counter, gauge, histogram")

if __name__ == "__main__":
    main() 