# Unified Agents Architecture

This document describes the unified agents architecture, which combines multiple specialized agents into cohesive, feature-rich modules. The architecture is designed to improve maintainability, reduce code duplication, and provide a more streamlined development experience.

## Overview

The unified agents architecture consists of four main components:

1. **Unified Utilities Agent** (`unified_utils_agent.py`)
2. **Unified Error Agent** (`unified_error_agent.py`)
3. **Unified System Agent** (`unified_system_agent.py`)
4. **Unified Planning Agent** (`unified_planning_agent.py`)

Each unified agent combines related functionalities from multiple legacy agents, providing a more integrated and efficient solution.

## Unified Utilities Agent

The Unified Utilities Agent combines model voting, runtime tools, and module loading functionalities.

### Features

- **Model Voting**: Selects the most appropriate model for a given task
- **Runtime Tools**: Manages and provides access to runtime tools
- **Module Loading**: Dynamically loads and manages Python modules
- **Tool Discovery**: Lists and manages available tools

### Configuration

```python
"utils_agents": {
    "unified_utils_agent": {
        "enabled": True,
        "port": 5564,
        "health_check_port": 5565,
        "model": "gpt-4",
        "temperature": 0.7,
        "timeout": 30,
        "max_retries": 3
    }
}
```

### Usage

```python
# Get model votes
request = {
    "action": "get_model_votes",
    "query": "Generate a Python function",
    "models": ["gpt-4", "gpt-3.5-turbo"]
}

# Get runtime tools
request = {
    "action": "get_runtime_tools",
    "tool_type": "code_generation"
}

# Load module
request = {
    "action": "load_module",
    "module_path": "path/to/module.py"
}
```

## Unified Error Agent

The Unified Error Agent combines error logging, pattern detection, health monitoring, and error history management.

### Features

- **Error Logging**: Centralized error logging with severity levels
- **Pattern Detection**: Identifies recurring error patterns
- **Health Monitoring**: Tracks system health metrics
- **Error History**: Maintains and queries error history

### Configuration

```python
"error_agents": {
    "unified_error_agent": {
        "enabled": True,
        "port": 5566,
        "health_check_port": 5567,
        "db_path": "agents/error_database.db",
        "log_retention_days": 7,
        "cleanup_interval": 3600
    }
}
```

### Usage

```python
# Log error
request = {
    "action": "log_error",
    "error_type": "runtime_error",
    "message": "Error message",
    "severity": "warning"
}

# Add error pattern
request = {
    "action": "add_error_pattern",
    "pattern": {
        "error_type": "pattern_name",
        "message_pattern": "error.*pattern",
        "severity": "warning",
        "threshold": 3
    }
}

# Get health metrics
request = {
    "action": "get_health_metrics"
}
```

## Unified System Agent

The Unified System Agent combines service management, system cleanup, and system information retrieval.

### Features

- **Service Management**: Start, stop, and monitor services
- **System Cleanup**: Clean up temporary files and logs
- **System Information**: Retrieve system metrics and status
- **Service Discovery**: Discover running services

### Configuration

```python
"system_agents": {
    "unified_system_agent": {
        "enabled": True,
        "port": 5568,
        "health_check_port": 5569,
        "service_check_interval": 30,
        "cleanup_interval": 3600,
        "log_retention_days": 7
    }
}
```

### Usage

```python
# List services
request = {
    "action": "list_services"
}

# Start service
request = {
    "action": "start_service",
    "service_name": "service_name",
    "command": "command_to_run"
}

# Cleanup system
request = {
    "action": "cleanup_system",
    "options": {
        "cleanup_dirs": ["dir1", "dir2"],
        "max_age_days": 7
    }
}
```

## Unified Planning Agent

The Unified Planning Agent combines task planning, chain of thought reasoning, and code generation.

### Features

- **Task Planning**: Break down complex tasks into steps
- **Chain of Thought**: Step-by-step reasoning for complex problems
- **Code Generation**: Generate and test code solutions
- **Safe Execution**: Execute code in a controlled environment

### Configuration

```python
"planning_agents": {
    "unified_planning_agent": {
        "enabled": True,
        "port": 5562,
        "health_check_port": 5563,
        "model": "gpt-4",
        "temperature": 0.7,
        "timeout": 30,
        "max_retries": 3,
        "cache_size": 1000
    }
}
```

### Usage

```python
# Create plan
request = {
    "action": "create_plan",
    "task": "Task description",
    "constraints": ["constraint1", "constraint2"]
}

# Generate code
request = {
    "action": "generate_code",
    "description": "Code description",
    "language": "python",
    "include_tests": True
}

# Execute code
request = {
    "action": "execute_code",
    "code": "print('Hello, World!')",
    "language": "python"
}
```

## Testing

Each unified agent has its own test suite in the `tests` directory:

- `tests/test_unified_utils_agent.py`
- `tests/test_unified_error_agent.py`
- `tests/test_unified_system_agent.py`
- `tests/test_unified_planning_agent.py`

Run the tests using:

```bash
python -m pytest tests/test_unified_*.py -v
```

## Health Checks

Each unified agent provides health check endpoints:

- Utilities Agent: Port 5565
- Error Agent: Port 5567
- System Agent: Port 5569
- Planning Agent: Port 5563

Health check requests should be sent to these ports with the following format:

```python
request = {
    "action": "health_check"
}
```

## Error Handling

All unified agents follow a consistent error handling pattern:

1. Input validation
2. Error logging
3. Pattern detection
4. Response formatting

Error responses follow this format:

```python
{
    "status": "error",
    "error": {
        "type": "error_type",
        "message": "Error message",
        "details": {}
    }
}
```

## Best Practices

1. **Configuration Management**
   - Use the centralized configuration in `config/system_config.py`
   - Keep sensitive information in environment variables
   - Use appropriate logging levels

2. **Error Handling**
   - Log all errors with appropriate severity
   - Use error patterns for recurring issues
   - Implement proper cleanup in error cases

3. **Service Management**
   - Monitor service health regularly
   - Implement graceful shutdown
   - Use appropriate timeouts

4. **Code Generation**
   - Always include tests
   - Use safe execution environment
   - Validate generated code

## Troubleshooting

Common issues and solutions:

1. **Connection Issues**
   - Check if the agent is running
   - Verify port numbers
   - Check firewall settings

2. **Performance Issues**
   - Monitor system resources
   - Check for memory leaks
   - Review logging levels

3. **Error Patterns**
   - Check error database
   - Review error patterns
   - Monitor system health

## Future Improvements

1. **Enhanced Monitoring**
   - Real-time metrics
   - Predictive analytics
   - Automated alerts

2. **Improved Error Handling**
   - Machine learning for pattern detection
   - Automated recovery
   - Better error categorization

3. **Service Management**
   - Load balancing
   - Auto-scaling
   - Service mesh integration

4. **Code Generation**
   - Multi-language support
   - Better test generation
   - Code optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Update documentation
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 