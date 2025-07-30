# Development Workflow Guide

**Last Updated**: 2025-07-31  
**Version**: 3.4.0  
**Phase**: Phase 3.4 - Documentation & Developer Onboarding

## Table of Contents

1. [Overview](#overview)
2. [Development Environment Setup](#development-environment-setup)
3. [Code Standards and Guidelines](#code-standards-and-guidelines)
4. [Development Workflow](#development-workflow)
5. [Agent Development](#agent-development)
6. [Testing Guidelines](#testing-guidelines)
7. [Code Review Process](#code-review-process)
8. [Release Management](#release-management)

## Overview

This guide provides comprehensive instructions for developers working on the AI System Monorepo. It covers development environment setup, coding standards, workflow processes, and best practices for maintaining high-quality, scalable code.

### Development Principles

- **Code Quality**: Maintain high standards through linting, testing, and reviews
- **Documentation**: Document code, APIs, and architectural decisions
- **Testing**: Write comprehensive tests for all new features
- **Performance**: Consider performance implications in all development
- **Security**: Follow security best practices and secure coding guidelines
- **Collaboration**: Use clear communication and efficient review processes

## Development Environment Setup

### Prerequisites

```bash
# System requirements
- Python 3.8+ (recommended: 3.9+)
- Git 2.20+
- Redis 6.0+ (for development)
- Docker and Docker Compose (optional)
- Visual Studio Code or PyCharm (recommended)

# Hardware recommendations
- CPU: 4+ cores
- RAM: 16GB+ (32GB recommended for full system development)
- Storage: 100GB+ available space
- Network: Stable internet connection for dependencies
```

### Initial Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd AI_System_Monorepo

# 2. Create virtual environment
python3 -m venv ai_system_env
source ai_system_env/bin/activate  # Linux/Mac
# or
ai_system_env\Scripts\activate     # Windows

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Setup pre-commit hooks
pre-commit install

# 5. Configure environment
cp config/dev.env.example .env
# Edit .env with your local settings

# 6. Initialize development database/services
docker-compose -f docker-compose.dev.yml up -d

# 7. Run initial tests
python -m pytest tests/unit/ -v

# 8. Verify setup
python scripts/verify_dev_environment.py
```

### IDE Configuration

#### Visual Studio Code

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./ai_system_env/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

## Code Standards and Guidelines

### Python Code Style

#### PEP 8 Compliance

```python
# Good: PEP 8 compliant code
class ServiceRegistryAgent(BaseAgent):
    """Service registry for managing agent lifecycle and discovery."""
    
    def __init__(self, name: str, port: int = 8080):
        super().__init__(name=name, port=port)
        self.registered_agents: Dict[str, AgentInfo] = {}
        self.health_check_interval: float = 30.0
    
    def register_agent(self, agent_info: AgentInfo) -> RegistrationResult:
        """Register a new agent with the service registry.
        
        Args:
            agent_info: Information about the agent to register
            
        Returns:
            Registration result with agent ID and status
            
        Raises:
            RegistrationError: If agent registration fails
        """
        if not self._validate_agent_info(agent_info):
            raise RegistrationError("Invalid agent information")
        
        agent_id = self._generate_agent_id(agent_info.name)
        self.registered_agents[agent_id] = agent_info
        
        return RegistrationResult(
            agent_id=agent_id,
            status="registered",
            timestamp=datetime.utcnow()
        )
```

#### Type Hints

```python
# Good: Comprehensive type hints
from typing import Dict, List, Optional, Union, Callable, Any
from dataclasses import dataclass

@dataclass
class AgentInfo:
    name: str
    port: int
    capabilities: List[str]
    health_endpoint: Optional[str] = None
    metadata: Dict[str, Any] = None

class AgentManager:
    def __init__(self) -> None:
        self.agents: Dict[str, AgentInfo] = {}
        self.health_checkers: Dict[str, Callable[[], bool]] = {}
    
    def add_agent(self, agent_info: AgentInfo) -> str:
        """Add agent and return agent ID."""
        agent_id = self._generate_id(agent_info.name)
        self.agents[agent_id] = agent_info
        return agent_id
    
    def get_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """Get all agents with specified capability."""
        return [
            agent for agent in self.agents.values()
            if capability in agent.capabilities
        ]
```

#### Documentation Standards

```python
# Good: Google-style docstrings
class AsyncTaskQueue:
    """Async priority queue for task processing.
    
    This class implements an async-safe priority queue using asyncio.PriorityQueue
    with additional features like task deduplication and metrics collection.
    
    Attributes:
        max_size: Maximum number of tasks in queue
        metrics: Performance metrics collector
        
    Example:
        >>> queue = AsyncTaskQueue(max_size=1000)
        >>> await queue.put(PriorityTask(priority=1, task_data=data))
        >>> task = await queue.get()
    """
    
    def __init__(self, max_size: int = 0, enable_metrics: bool = True):
        """Initialize async task queue.
        
        Args:
            max_size: Maximum queue size (0 = unlimited)
            enable_metrics: Whether to collect performance metrics
            
        Raises:
            ValueError: If max_size is negative
        """
        if max_size < 0:
            raise ValueError("max_size cannot be negative")
        
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._metrics = QueueMetrics() if enable_metrics else None
```

### Import Organization

```python
# Good: Organized imports
# Standard library imports
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

# Third-party imports
import redis
import zmq
import yaml
from prometheus_client import Counter, Gauge

# Local imports
from common.config import Config
from common.core.base_agent import BaseAgent
from common.error_handling import ErrorPublisher
from common.utils.fast_json import FastJSON
```

## Development Workflow

### Git Workflow

#### Branch Naming Conventions

```bash
# Feature branches
feature/agent-health-monitoring
feature/async-task-queue-refactor
feature/prometheus-integration

# Bug fix branches
bugfix/memory-leak-in-cache-manager
bugfix/config-validation-error

# Hotfix branches (for production)
hotfix/critical-security-patch
hotfix/performance-degradation-fix

# Release branches
release/v3.4.0
release/v3.5.0-beta

# Documentation branches
docs/api-reference-update
docs/deployment-guide-revision
```

#### Commit Message Format

```bash
# Format: <type>(<scope>): <description>
# 
# <body>
# 
# <footer>

# Examples:
feat(agents): add async task queue with priority support

- Implement AsyncTaskQueue using asyncio.PriorityQueue
- Add task deduplication and metrics collection
- Update AsyncProcessor to use new queue system
- Include comprehensive unit tests

Closes #123

fix(config): resolve environment variable override issue

- Fix bug where environment variables were not properly overriding config values
- Add validation for environment variable names
- Update documentation with correct variable naming convention

Fixes #456

docs(architecture): update system architecture documentation

- Add async task queue architecture section
- Update component interaction diagrams
- Include performance benchmarks and recommendations
```

### Development Cycles

#### Feature Development Cycle

```bash
# 1. Create feature branch
git checkout -b feature/new-monitoring-dashboard

# 2. Development iterations
# - Write failing tests
# - Implement feature
# - Make tests pass
# - Refactor if needed
# - Commit changes

# 3. Regular updates
git fetch origin
git rebase origin/develop

# 4. Testing
python -m pytest tests/ -v
python scripts/run_integration_tests.sh

# 5. Code quality checks
pre-commit run --all-files
mypy src/
flake8 src/

# 6. Create pull request
git push origin feature/new-monitoring-dashboard
# Create PR through GitHub/GitLab interface

# 7. Address review feedback
# - Make requested changes
# - Update tests
# - Push additional commits

# 8. Merge to develop
# After approval and CI passes

# 9. Clean up
git checkout develop
git pull origin develop
git branch -d feature/new-monitoring-dashboard
```

## Agent Development

### Agent Development Checklist

```markdown
# Agent Development Checklist

## Planning
- [ ] Define agent purpose and capabilities
- [ ] Identify required dependencies and integrations
- [ ] Design data structures and interfaces
- [ ] Plan error handling and monitoring requirements

## Implementation
- [ ] Create agent class inheriting from BaseAgent
- [ ] Implement configuration loading and validation
- [ ] Setup backend integration
- [ ] Implement core functionality
- [ ] Add error handling and logging
- [ ] Integrate monitoring and metrics

## Testing
- [ ] Write unit tests for core functionality
- [ ] Add integration tests for external dependencies
- [ ] Test error handling and edge cases
- [ ] Verify configuration loading and validation
- [ ] Test monitoring and health checks

## Documentation
- [ ] Add comprehensive docstrings
- [ ] Update architecture documentation
- [ ] Create usage examples
- [ ] Document configuration options

## Quality Assurance
- [ ] Run pre-commit hooks
- [ ] Verify type hints and mypy compliance
- [ ] Check code coverage
- [ ] Performance testing if applicable

## Integration
- [ ] Update startup configurations
- [ ] Add agent to service registry
- [ ] Update monitoring dashboards
- [ ] Test cross-agent communication
```

### Best Practices for Agent Development

```python
# Good: Following agent development patterns
from common.core.base_agent import BaseAgent
from common.config import Config
from common.error_handling import ErrorPublisher

class NewAgent(BaseAgent):
    def __init__(self, name: str = "new_agent", port: int = 8080):
        super().__init__(name=name, port=port)
        self.config = Config.for_agent(__file__)
        self.error_publisher = ErrorPublisher()
        
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Validate input
            if not self._validate_request(request_data):
                raise ValueError("Invalid request data")
            
            # Process request
            result = await self._process_request(request_data)
            
            # Return response
            return {"status": "success", "result": result}
            
        except Exception as e:
            self.error_publisher.report_error(
                error_type="request_processing_error",
                severity="medium",
                message=f"Failed to process request: {str(e)}",
                context={"agent_name": self.name, "request": request_data}
            )
            raise
```

## Testing Guidelines

### Test-Driven Development

```python
# 1. Write failing test first
def test_agent_processes_data_successfully():
    """Test that agent processes valid data correctly."""
    agent = YourAgent()
    
    test_data = {"input": "test_value", "type": "text"}
    expected_result = {"processed": True, "output": "PROCESSED: test_value"}
    
    result = await agent.handle_process_data({"data": test_data})
    
    assert result["status"] == "success"
    assert result["result"] == expected_result

# 2. Implement minimal code to make test pass
async def handle_process_data(self, request_data):
    data = request_data["data"]
    result = {"processed": True, "output": f"PROCESSED: {data['input']}"}
    return {"status": "success", "result": result}

# 3. Refactor and improve implementation
```

### Test Organization

```python
# tests/unit/test_new_agent.py
import pytest
from unittest.mock import Mock, patch
from your_module.new_agent import NewAgent

class TestNewAgent:
    @pytest.fixture
    def agent(self):
        return NewAgent(name="test_agent", port=8080)
    
    def test_initialization(self, agent):
        assert agent.name == "test_agent"
        assert agent.port == 8080
    
    async def test_handle_request_success(self, agent):
        request_data = {"type": "test", "data": "value"}
        result = await agent.handle_request(request_data)
        
        assert result["status"] == "success"
        assert "result" in result
```

## Code Review Process

### Review Checklist

```markdown
# Code Review Checklist

## Functionality
- [ ] Code does what it's supposed to do
- [ ] Edge cases are handled appropriately
- [ ] Error handling is comprehensive
- [ ] Performance considerations are addressed

## Code Quality
- [ ] Code follows project style guidelines
- [ ] Code is readable and well-organized
- [ ] Functions and classes are appropriately sized
- [ ] Variable and function names are clear

## Testing
- [ ] Adequate test coverage
- [ ] Tests are meaningful and thorough
- [ ] Tests follow testing best practices
- [ ] Integration tests where appropriate

## Documentation
- [ ] Code is properly documented
- [ ] API changes are documented
- [ ] README updates if needed
- [ ] Architecture docs updated if needed

## Security
- [ ] No obvious security vulnerabilities
- [ ] Input validation is present
- [ ] Secrets are handled properly
- [ ] Authentication/authorization as needed
```

## Release Management

### Release Process

```bash
# 1. Create release branch
git checkout -b release/v3.4.0

# 2. Update version numbers
# Update version in setup.py, __init__.py, etc.

# 3. Update changelog
# Document all changes since last release

# 4. Run full test suite
python scripts/run_all_tests.sh

# 5. Performance testing
python scripts/run_performance_tests.sh

# 6. Security scanning
python scripts/run_security_scan.sh

# 7. Create release candidate
git tag v3.4.0-rc1
git push origin v3.4.0-rc1

# 8. Deploy to staging
./scripts/deploy_to_staging.sh

# 9. User acceptance testing
# Manual testing and validation

# 10. Create final release
git tag v3.4.0
git push origin v3.4.0

# 11. Deploy to production
./scripts/deploy_to_production.sh

# 12. Update documentation
# Update deployment docs, API docs, etc.
```

### Version Management

```python
# Version numbering: MAJOR.MINOR.PATCH
# 
# MAJOR: Breaking changes
# MINOR: New features, backward compatible
# PATCH: Bug fixes, backward compatible
#
# Examples:
# v3.4.0 → v3.4.1 (bug fix)
# v3.4.1 → v3.5.0 (new features)
# v3.5.0 → v4.0.0 (breaking changes)
```

---

**Next**: See [deployment.md](deployment.md) for deployment strategies and [testing.md](testing.md) for comprehensive testing approaches.
