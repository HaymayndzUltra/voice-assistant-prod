# Planning Module Documentation

## Overview

The Planning Module combines multiple planning and execution capabilities into a unified agent that handles complex task decomposition, step-by-step reasoning, code generation, and safe execution. This module is designed to work seamlessly with the AutoGen framework and provides a robust foundation for autonomous task execution.

## Features

### 1. Task Planning
- Natural language task decomposition
- Multi-step plan generation
- Plan validation and verification
- Integration with AutoGen framework
- Plan execution monitoring

### 2. Chain of Thought
- Step-by-step reasoning
- Problem breakdown
- Solution verification
- Intermediate result validation
- Progress tracking

### 3. Code Generation
- Progressive code generation
- Test-driven development
- Multiple language support
- Code optimization
- Documentation generation

### 4. Safe Execution
- Isolated execution environment
- Resource monitoring
- Timeout handling
- Error recovery
- Output validation

## Configuration

The planning agent is configured in `config/system_config.py`:

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

## Usage

### Task Planning

```python
# Create a plan
request = {
    "action": "create_plan",
    "task": "Create a web scraper for e-commerce sites",
    "max_steps": 5
}

# Execute a plan
request = {
    "action": "execute_plan",
    "plan_id": "plan_123",
    "parameters": {
        "url": "https://example.com",
        "output_format": "csv"
    }
}
```

### Chain of Thought

```python
# Generate problem breakdown
request = {
    "action": "generate_problem_breakdown",
    "problem": "How to improve voice recognition accuracy?",
    "max_steps": 3
}

# Verify solution
request = {
    "action": "verify_solution",
    "problem": "Voice recognition accuracy",
    "solution": "Implement noise reduction",
    "criteria": ["accuracy", "latency", "resource_usage"]
}
```

### Code Generation

```python
# Generate code with tests
request = {
    "action": "generate_code",
    "task": "Create a Fibonacci calculator",
    "language": "python",
    "include_tests": True
}

# Optimize code
request = {
    "action": "optimize_code",
    "code_path": "path/to/code.py",
    "optimization_goals": ["performance", "readability"]
}
```

### Safe Execution

```python
# Execute code
request = {
    "action": "execute_code",
    "code": "print('Hello, World!')",
    "language": "python",
    "timeout": 5
}

# Monitor execution
request = {
    "action": "monitor_execution",
    "execution_id": "exec_123"
}
```

## Health Checks

The planning agent provides health check endpoints:

- `http://localhost:5563/health` - Basic health check
- `http://localhost:5563/metrics` - Performance metrics
- `http://localhost:5563/status` - Detailed status

## Error Handling

The agent implements comprehensive error handling:

1. Input Validation
   - Request format checking
   - Parameter validation
   - Resource availability

2. Execution Safety
   - Timeout management
   - Resource limits
   - Error recovery

3. Monitoring
   - Performance tracking
   - Error logging
   - Status reporting

## Testing

Run the test suite:

```bash
python tests/test_unified_planning_agent.py
```

The test suite covers:
- Task planning
- Chain of thought reasoning
- Code generation
- Safe execution
- Error handling

## Integration

The planning agent integrates with:

1. AutoGen Framework
   - Agent coordination
   - Task distribution
   - Result aggregation

2. Memory Module
   - Context tracking
   - History management
   - Knowledge persistence

3. Web Module
   - Web scraping
   - Data extraction
   - Browser automation

## Best Practices

1. Task Planning
   - Break down complex tasks
   - Validate each step
   - Monitor progress
   - Handle failures gracefully

2. Code Generation
   - Include tests
   - Add documentation
   - Follow style guides
   - Optimize performance

3. Safe Execution
   - Set timeouts
   - Monitor resources
   - Validate outputs
   - Handle errors

## Troubleshooting

Common issues and solutions:

1. Timeout Errors
   - Increase timeout in config
   - Optimize code
   - Check resource usage

2. Memory Issues
   - Clear cache
   - Reduce batch size
   - Monitor memory usage

3. Integration Problems
   - Check ZMQ ports
   - Verify dependencies
   - Review logs

## Future Improvements

1. Enhanced Planning
   - Multi-agent collaboration
   - Dynamic task decomposition
   - Adaptive execution

2. Code Generation
   - More language support
   - Better optimization
   - Enhanced testing

3. Execution Safety
   - Improved isolation
   - Better monitoring
   - Advanced recovery

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests
4. Submit a pull request

## License

This module is licensed under the MIT License - see the LICENSE file for details. 