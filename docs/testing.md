# Testing Guide

**Last Updated**: 2025-07-31  
**Version**: 3.4.0  
**Phase**: Phase 3.4 - Documentation & Developer Onboarding

## Table of Contents

1. [Overview](#overview)
2. [Testing Strategy](#testing-strategy)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Performance Testing](#performance-testing)
7. [Test Automation](#test-automation)
8. [Best Practices](#best-practices)

## Overview

The AI System Monorepo employs a comprehensive testing strategy to ensure reliability, performance, and maintainability across all components. This guide covers testing methodologies, frameworks, and best practices for the multi-machine AI system.

### Testing Philosophy

- **Test Early, Test Often**: Continuous testing throughout development
- **Comprehensive Coverage**: Unit, integration, and end-to-end testing
- **Real-World Scenarios**: Testing with realistic data and conditions
- **Performance Validation**: Regular performance and load testing
- **Cross-Machine Testing**: Validation of PC2 ↔ Main PC communication
- **Automated Testing**: CI/CD integration for continuous validation

### Testing Architecture

```
Testing Framework
├── Unit Tests (60%)
│   ├── Agent Logic Tests
│   ├── Configuration Tests
│   ├── Error Handling Tests
│   └── Utility Function Tests
├── Integration Tests (30%)
│   ├── Cross-Agent Communication
│   ├── Backend Integration
│   ├── Error Bus Integration
│   └── Configuration Integration
├── End-to-End Tests (10%)
│   ├── Full System Workflows
│   ├── Cross-Machine Communication
│   ├── Performance Scenarios
│   └── Failure Recovery Tests
└── Performance Tests
    ├── Load Testing
    ├── Stress Testing
    ├── Memory Profiling
    └── Network Performance
```

## Testing Strategy

### Test Pyramid

```
                /\
               /  \
              /E2E \     End-to-End Tests (10%)
             /______\    - Full system workflows
            /        \   - Cross-machine scenarios
           / INTEG.   \  Integration Tests (30%)
          /____________\ - Component interactions
         /              \
        /  UNIT TESTS    \ Unit Tests (60%)
       /________________\ - Individual functions
                          - Component logic
```

### Testing Levels

#### 1. Unit Tests (60% of test suite)
- **Scope**: Individual functions, methods, classes
- **Focus**: Logic validation, edge cases, error conditions
- **Execution**: Fast, isolated, no external dependencies
- **Coverage Target**: 90%+

#### 2. Integration Tests (30% of test suite)
- **Scope**: Component interactions, API contracts
- **Focus**: Data flow, communication protocols, backend integration
- **Execution**: Moderate speed, controlled dependencies
- **Coverage Target**: 80%+

#### 3. End-to-End Tests (10% of test suite)
- **Scope**: Complete user workflows, system scenarios
- **Focus**: Real-world usage, cross-machine communication
- **Execution**: Slower, full environment setup
- **Coverage Target**: Critical paths only

## Unit Testing

### Testing Framework Setup

```python
# tests/conftest.py
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch
from common.config import Config
from common.backends import BackendFactory

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock(spec=Config)
    config.str.return_value = "test_value"
    config.int.return_value = 8080
    config.bool.return_value = True
    config.float.return_value = 30.0
    return config

@pytest.fixture
def test_backend():
    """Create test backend for testing."""
    return BackendFactory.create_backend("memory", {"max_size": 100})

@pytest.fixture
def agent_test_environment():
    """Setup complete agent testing environment."""
    with patch('common.config.Config.for_agent') as mock_config, \
         patch('common.error_handling.ErrorPublisher') as mock_error_publisher:
        
        mock_config.return_value.str.return_value = "test"
        mock_config.return_value.int.return_value = 8080
        mock_config.return_value.bool.return_value = False
        
        yield {
            'config': mock_config.return_value,
            'error_publisher': mock_error_publisher.return_value
        }
```

### Agent Unit Tests

```python
# tests/unit/test_base_agent.py
import pytest
from unittest.mock import Mock, patch
from common.core.base_agent import BaseAgent

class TestBaseAgent:
    
    def test_agent_initialization(self, agent_test_environment):
        """Test agent initialization with configuration."""
        agent = BaseAgent(name="test_agent", port=8080)
        
        assert agent.name == "test_agent"
        assert agent.port == 8080
        assert agent.running is False
    
    def test_agent_startup(self, agent_test_environment):
        """Test agent startup process."""
        agent = BaseAgent(name="test_agent", port=8080)
        
        with patch.object(agent, 'setup_logging') as mock_setup_logging, \
             patch.object(agent, 'initialize_communications') as mock_init_comm, \
             patch.object(agent, 'load_configuration') as mock_load_config:
            
            agent.startup()
            
            mock_setup_logging.assert_called_once()
            mock_init_comm.assert_called_once()
            mock_load_config.assert_called_once()
            assert agent.running is True
    
    def test_health_check(self, agent_test_environment):
        """Test agent health check functionality."""
        agent = BaseAgent(name="test_agent", port=8080)
        agent.running = True
        
        health = agent.health_check()
        
        assert health['status'] == 'healthy'
        assert health['name'] == 'test_agent'
        assert 'uptime' in health
        assert 'memory_usage' in health
```

### Configuration Unit Tests

```python
# tests/unit/test_configuration.py
import pytest
import tempfile
import yaml
from common.config.unified_config_manager import ConfigManager
from common.config.validation import ConfigValidator

class TestConfigManager:
    
    def test_load_base_configuration(self, temp_dir):
        """Test loading base configuration."""
        config_file = f"{temp_dir}/base.yaml"
        config_data = {
            'system': {'name': 'Test System', 'environment': 'test'},
            'network': {'host': '0.0.0.0', 'port': 8080}
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = ConfigManager()
        config.load_config(config_file)
        
        assert config.get('system.name') == 'Test System'
        assert config.get('network.port') == 8080
    
    def test_environment_overlay(self, temp_dir):
        """Test environment-specific configuration overlay."""
        base_config = f"{temp_dir}/base.yaml"
        dev_config = f"{temp_dir}/dev.yaml"
        
        base_data = {'system': {'debug': False}, 'network': {'port': 8080}}
        dev_data = {'system': {'debug': True}, 'network': {'port': 8081}}
        
        with open(base_config, 'w') as f:
            yaml.dump(base_data, f)
        with open(dev_config, 'w') as f:
            yaml.dump(dev_data, f)
        
        config = ConfigManager()
        config.load_config_with_environment(base_config, 'dev', dev_config)
        
        assert config.get('system.debug') is True
        assert config.get('network.port') == 8081

class TestConfigValidator:
    
    def test_schema_validation_success(self):
        """Test successful schema validation."""
        validator = ConfigValidator()
        config_data = {
            'system': {'name': 'Test', 'environment': 'dev'},
            'logging': {'level': 'INFO'}
        }
        
        result = validator.validate_config(config_data)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_custom_validators(self):
        """Test custom validation rules."""
        validator = ConfigValidator()
        
        # Test port validation
        assert validator.validate_port(8080) is True
        assert validator.validate_port(70000) is False
        
        # Test IP address validation
        assert validator.validate_ip_address("192.168.1.1") is True
        assert validator.validate_ip_address("invalid.ip") is False
```

### Error Handling Unit Tests

```python
# tests/unit/test_error_handling.py
import pytest
from unittest.mock import Mock, patch
from common.error_handling import ErrorPublisher
from pc2_code.utils.pc2_error_publisher import PC2ErrorPublisher

class TestErrorPublisher:
    
    def test_error_reporting(self):
        """Test basic error reporting functionality."""
        with patch('zmq.Context') as mock_context:
            mock_socket = Mock()
            mock_context.return_value.socket.return_value = mock_socket
            
            publisher = ErrorPublisher()
            
            publisher.report_error(
                error_type="test_error",
                severity="medium",
                message="Test error message",
                context={"test": "data"}
            )
            
            # Verify socket operations
            mock_socket.send_json.assert_called_once()
            sent_data = mock_socket.send_json.call_args[0][0]
            
            assert sent_data['error_type'] == "test_error"
            assert sent_data['severity'] == "medium"
            assert sent_data['message'] == "Test error message"

class TestPC2ErrorPublisher:
    
    def test_cross_machine_propagation(self):
        """Test cross-machine error propagation."""
        with patch('zmq.Context') as mock_context:
            mock_local_socket = Mock()
            mock_cross_machine_socket = Mock()
            mock_context.return_value.socket.side_effect = [
                mock_local_socket, mock_cross_machine_socket
            ]
            
            publisher = PC2ErrorPublisher()
            
            publisher.report_error(
                error_type="pc2_critical_error",
                severity="critical",
                message="Critical PC2 error",
                cross_machine_propagate=True
            )
            
            # Verify cross-machine propagation
            mock_cross_machine_socket.send_json.assert_called_once()
            cross_machine_data = mock_cross_machine_socket.send_json.call_args[0][0]
            
            assert cross_machine_data['source_machine'] == "PC2"
            assert cross_machine_data['error_type'] == "pc2_critical_error"
```

## Integration Testing

### Cross-Agent Communication Tests

```python
# tests/integration/test_agent_communication.py
import pytest
import time
import threading
from unittest.mock import patch, Mock

class TestAgentCommunication:
    
    def test_agent_registration(self):
        """Test agent registration with service registry."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'status': 'registered',
                'agent_id': 'test_123'
            }
            
            from main_pc_code.agents.service_registry_agent import ServiceRegistryAgent
            
            registry = ServiceRegistryAgent()
            response = registry.register_agent({
                'name': 'test_agent',
                'port': 8081,
                'capabilities': ['testing']
            })
            
            assert response['status'] == 'registered'
            assert 'agent_id' in response
    
    def test_cross_machine_communication(self):
        """Test communication between Main PC and PC2 agents."""
        with patch('zmq.Context') as mock_context:
            mock_socket = Mock()
            mock_context.return_value.socket.return_value = mock_socket
            mock_socket.recv_json.return_value = {
                'status': 'success',
                'data': {'memory_usage': 45.2}
            }
            
            from pc2_code.utils.cross_machine_bridge import CrossMachineBridge
            
            bridge = CrossMachineBridge()
            response = bridge.send_to_main_pc({
                'type': 'memory_status_update',
                'data': {'current_usage': 45.2}
            })
            
            assert response['status'] == 'success'
            mock_socket.send_json.assert_called_once()
```

### Backend Integration Tests

```python
# tests/integration/test_backend_integration.py
import pytest
from common.backends import BackendFactory

class TestBackendIntegration:
    
    def test_backend_switching(self, temp_dir):
        """Test switching between different backend types."""
        # Start with memory backend
        memory_backend = BackendFactory.create_backend("memory", {"max_size": 100})
        memory_backend.set("test_key", "memory_value")
        
        # Switch to file backend
        file_config = {"file_path": f"{temp_dir}/switch_test.json"}
        file_backend = BackendFactory.create_backend("file", file_config)
        file_backend.set("test_key", "file_value")
        
        # Verify isolation
        assert memory_backend.get("test_key") == "memory_value"
        assert file_backend.get("test_key") == "file_value"
```

## End-to-End Testing

### System Workflow Tests

```python
# tests/e2e/test_system_workflows.py
import pytest
import time
import subprocess
import requests
from multiprocessing import Process

class TestSystemWorkflows:
    
    def test_full_agent_lifecycle(self):
        """Test complete agent lifecycle from startup to shutdown."""
        with patch.dict('os.environ', {'AI_SYSTEM_ENV': 'test'}):
            from main_pc_code.agents.service_registry_agent import ServiceRegistryAgent
            
            agent = ServiceRegistryAgent()
            
            # Test startup
            agent_process = Process(target=agent.run)
            agent_process.start()
            
            time.sleep(2)  # Allow agent to start
            
            try:
                # Test health check
                response = requests.get('http://localhost:8080/health', timeout=5)
                assert response.status_code == 200
                
                health_data = response.json()
                assert health_data['status'] == 'healthy'
                
            finally:
                # Cleanup
                agent_process.terminate()
                agent_process.join(timeout=5)
```

## Performance Testing

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import time
import concurrent.futures
from common.backends import BackendFactory

class TestPerformance:
    
    def test_backend_performance(self):
        """Test backend performance under load."""
        backend = BackendFactory.create_backend("memory", {"max_size": 10000})
        
        def worker(thread_id):
            start_time = time.time()
            for i in range(1000):
                key = f"perf_test_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                backend.set(key, value)
                retrieved = backend.get(key)
                assert retrieved == value
            return time.time() - start_time
        
        # Run with multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        # Performance assertions
        avg_time = sum(results) / len(results)
        assert avg_time < 5.0  # Should complete within 5 seconds per thread
        
        # Test throughput
        total_operations = 10 * 1000 * 2  # 10 threads * 1000 ops * 2 (set + get)
        total_time = max(results)
        throughput = total_operations / total_time
        
        assert throughput > 1000  # Should handle >1000 ops/second
```

## Test Automation

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=common --cov=main_pc_code --cov=pc2_code
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
      env:
        AI_REDIS_HOST: localhost
        AI_REDIS_PORT: 6379

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run E2E tests
      run: |
        pytest tests/e2e/ -v --timeout=300
```

### Test Execution Scripts

```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "Running AI System Test Suite..."

# Setup test environment
export AI_SYSTEM_ENV=test
export PYTHONPATH=$PWD

# Start test services
docker-compose -f tests/docker-compose.test.yml up -d

# Wait for services
sleep 10

# Run tests
echo "Running unit tests..."
pytest tests/unit/ -v --cov=common --cov=main_pc_code --cov=pc2_code --cov-report=html

echo "Running integration tests..."
pytest tests/integration/ -v

echo "Running E2E tests..."
pytest tests/e2e/ -v --timeout=300

echo "Running performance tests..."
pytest tests/performance/ -v

# Cleanup
docker-compose -f tests/docker-compose.test.yml down

echo "Test suite completed successfully!"
```

## Best Practices

### 1. Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_agents.py
│   ├── test_config.py
│   └── test_backends.py
├── integration/             # Integration tests
│   ├── test_communication.py
│   └── test_backends.py
├── e2e/                     # End-to-end tests
│   └── test_workflows.py
├── performance/             # Performance tests
│   └── test_load.py
└── fixtures/                # Test data
    ├── config/
    └── data/
```

### 2. Test Naming Conventions

```python
# Good: Descriptive test names
def test_agent_registers_successfully_with_valid_data():
    pass

def test_config_validation_fails_with_invalid_port():
    pass

def test_error_publisher_propagates_critical_errors_to_main_pc():
    pass

# Avoid: Generic test names
def test_agent():
    pass

def test_config():
    pass
```

### 3. Test Data Management

```python
# Use fixtures for reusable test data
@pytest.fixture
def valid_agent_config():
    return {
        'name': 'test_agent',
        'port': 8080,
        'capabilities': ['testing', 'validation']
    }

@pytest.fixture
def sample_error_data():
    return {
        'error_type': 'test_error',
        'severity': 'medium',
        'message': 'Test error for validation',
        'context': {'component': 'test_suite'}
    }
```

### 4. Mock Strategy

```python
# Good: Mock external dependencies, test your code
@patch('redis.Redis')
def test_redis_backend_operations(mock_redis):
    backend = RedisBackend(host='localhost')
    # Test your backend logic, not Redis

# Avoid: Testing external libraries
def test_redis_library():
    # Don't test Redis library functionality
    pass
```

### 5. Error Testing

```python
# Test both success and failure paths
def test_agent_startup_success():
    # Test successful startup
    pass

def test_agent_startup_failure_with_invalid_config():
    # Test startup failure handling
    pass

def test_agent_startup_failure_with_port_conflict():
    # Test specific error conditions
    pass
```

---

**Next**: See [development.md](development.md) for development workflow and [deployment.md](deployment.md) for deployment strategies.
