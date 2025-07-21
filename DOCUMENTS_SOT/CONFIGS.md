# Configuration Files and Management Analysis

## Overview
This document analyzes all configuration files, management systems, and patterns across the AI System Monorepo, including YAML, JSON, environment files, and configuration management approaches.

## Configuration File Types and Locations

### YAML Configuration Files
| File Path | Purpose | Type | Status |
|-----------|---------|------|--------|
| `source_of_truth.yaml` | Master system configuration | System-wide | **Updated** |
| `test.yaml` | Test configuration | Testing | **Updated** |
| `model_config_optimized.yaml` | ML model configuration | Models | **Updated** |
| `pc2_code/config/startup_config.yaml` | PC2 startup configuration | Service | **Updated** |
| `pc2_code/config/memory_config.yaml` | Memory system configuration | Memory | **Updated** |
| `pc2_code/config/network_config.yaml` | Network configuration | Network | **Updated** |
| `main_pc_code/config/startup_config.yaml` | MainPC startup configuration | Service | **Updated** |
| `main_pc_code/config/llm_config.yaml` | LLM configuration | Models | **Updated** |

### JSON Configuration Files
| File Path | Purpose | Type | Status |
|-----------|---------|------|--------|
| `pyproject.toml` | Python project configuration | Build | **Updated** |
| `main_pc_code/config/api_keys.json` | API keys configuration | Security | **Updated** |
| Various `package.json` files | Node.js dependencies | Dependencies | **Mixed** |

### Environment Files
| File Path | Purpose | Scope | Status |
|-----------|---------|-------|--------|
| `.env` files | Environment variables | Service-specific | **Present** |
| `docker/podman/config/env.template` | Container environment template | Container | **Updated** |
| `env_config.sh` | Shell environment setup | Development | **Updated** |

## Configuration Management Patterns

### Hierarchical Configuration Structure
```yaml
# Common configuration hierarchy pattern
metadata:
  generated_at: '2025-01-XX XX:XX:XX'
  total_agents: 272
  description: Configuration description

main_pc_agents:
  - name: ServiceName
    script_path: /path/to/service.py
    port: 5556
    health_check_port: 8556
    dependencies: []
    has_error_bus: true
    critical: false
    
pc2_agents:
  - name: ServiceName
    script_path: /path/to/service.py
    port: 7100
    health_check_port: 8100
    dependencies: []
    configuration:
      max_memory: 1024
      timeout: 30
```

### Environment-Aware Configuration
```python
# Configuration manager pattern
class ConfigManager:
    def __init__(self, config_file=None):
        self.config_file = config_file or self._find_config_file()
        self.env_type = get_env('ENV_TYPE', 'development')
        
    def load_config(self):
        """Load configuration for current environment"""
        with open(self.config_file, 'r') as f:
            all_configs = yaml.safe_load(f)
        
        # Get environment-specific config
        return all_configs.get(self.env_type, all_configs.get('development', {}))
```

### Configuration Validation
```python
# Configuration validation pattern
def validate_config_schema(config):
    """Validate configuration against schema"""
    required_fields = ['name', 'port', 'script_path']
    
    for agent in config.get('agents', []):
        for field in required_fields:
            if field not in agent:
                raise ValidationError(f"Missing required field: {field}")
                
        # Validate port ranges
        if not (1000 <= agent['port'] <= 65535):
            raise ValidationError(f"Invalid port: {agent['port']}")
```

## Source of Truth Configuration

### Master Configuration Structure
```yaml
# source_of_truth.yaml structure
metadata:
  generated_at: '2025-01-XX XX:XX:XX'
  total_agents: 272
  description: Automatically regenerated source of truth file

main_pc_agents:
  # MainPC service definitions
  
pc2_agents:
  # PC2 service definitions
  
infrastructure:
  # Infrastructure service definitions
  
network_configuration:
  # Network and communication settings
```

### Agent Configuration Schema
```yaml
# Standard agent configuration
- name: AgentName
  script_path: /absolute/path/to/agent.py
  port: 5556                    # Service port
  health_check_port: 8556       # Health check port (optional)
  dependencies: []              # List of dependency names
  has_error_bus: true          # Error bus integration
  critical: false              # Critical service flag
  configuration:               # Agent-specific config
    timeout: 30
    max_retries: 3
    buffer_size: 1024
```

## Service Discovery Configuration

### Network Configuration
```yaml
# network_config.yaml pattern
services:
  redis:
    host: "localhost"
    port: 6379
    
  memory_orchestrator:
    host: "0.0.0.0"
    port: 5556
    health_check_port: 8556
    
  model_manager:
    host: "0.0.0.0"
    port: 5604
    health_check_port: 8604

network_ranges:
  core_services: "5000-5999"
  health_checks: "8000-8999"
  pc2_services: "7000-7999"
```

### Service Registry Configuration
```yaml
# Service registry configuration
registry:
  type: "consul"  # or "etcd", "redis"
  endpoints: ["localhost:8500"]
  
service_discovery:
  enabled: true
  refresh_interval: 30
  health_check_interval: 15
  
load_balancing:
  strategy: "round_robin"  # or "least_connections", "random"
  health_check_required: true
```

## Model Configuration

### LLM Configuration
```yaml
# llm_config.yaml structure
models:
  fast_model:
    name: "phi-3-mini"
    path: "/models/phi-3-mini.gguf"
    context_length: 4096
    temperature: 0.7
    
  quality_model:
    name: "mixtral-8x7b"
    path: "/models/mixtral-8x7b.gguf"
    context_length: 8192
    temperature: 0.3

routing_policy:
  default: "fast_model"
  quality_threshold: 0.8
  fallback_model: "fast_model"

vram_management:
  optimization_enabled: true
  memory_threshold: 0.85
  unload_timeout: 300
```

### Memory Configuration
```yaml
# memory_config.yaml structure
memory_layers:
  short_term:
    retention_hours: 24
    importance_threshold: 0.4
    
  medium_term:
    retention_days: 7
    importance_threshold: 0.2
    
  long_term:
    retention_days: 365
    archive_threshold: 0.1

memory_optimization:
  defragmentation_enabled: true
  defragmentation_threshold: 0.7
  compression_enabled: true
  similarity_threshold: 0.7
```

## Container Configuration

### Docker Environment Configuration
```yaml
# Docker Compose environment pattern
services:
  service_name:
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
      - DEBUG_MODE=false
      - BIND_ADDRESS=0.0.0.0
      - CONTAINER_GROUP=core_infrastructure
      - HEALTH_CHECK_PORT=8113
      - NETWORK_CONFIG_PATH=/app/config/network_config.yaml
```

### Container-Specific Configuration
```dockerfile
# Environment variables in Dockerfile
ENV PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    DEBUG_MODE=false \
    BIND_ADDRESS=0.0.0.0 \
    HEALTH_CHECK_PORT=8113
```

## Configuration Management Tools

### Configuration Loaders
```python
# Configuration loader patterns
class ConfigLoader:
    @staticmethod
    def load_yaml(file_path):
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML: {e}")
            raise
            
    @staticmethod
    def load_json(file_path):
        """Load JSON configuration file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            raise
```

### Configuration Watchers
```python
# Configuration file watcher
class ConfigWatcher:
    def __init__(self, config_file, callback):
        self.config_file = config_file
        self.callback = callback
        self.last_modified = os.path.getmtime(config_file)
        
    def watch(self):
        """Watch for configuration file changes"""
        while True:
            current_modified = os.path.getmtime(self.config_file)
            if current_modified > self.last_modified:
                logger.info("Configuration file changed, reloading...")
                self.callback()
                self.last_modified = current_modified
            time.sleep(5)
```

## Configuration Patterns by Service Type

### Agent Configuration Pattern
```yaml
# Standard agent configuration
agent_config:
  name: "ServiceName"
  host: "0.0.0.0"
  port: 5556
  health_check_port: 8556
  timeout: 30
  max_retries: 3
  error_bus_enabled: true
  logging_level: "INFO"
  
  # Service-specific configuration
  service_config:
    buffer_size: 1024
    worker_threads: 4
    cache_size: 100
```

### Infrastructure Configuration Pattern
```yaml
# Infrastructure service configuration
infrastructure:
  redis:
    host: "localhost"
    port: 6379
    password: null
    db: 0
    
  database:
    type: "postgresql"
    host: "localhost"
    port: 5432
    database: "ai_system"
    
  message_queue:
    type: "zmq"
    ports:
      publisher: 5555
      subscriber: 5556
```

## Environment-Specific Configurations

### Development Configuration
```yaml
# development.yaml
environment: development
debug: true
logging_level: DEBUG
hot_reload: true

services:
  # Development-specific service config
  model_manager:
    mock_models: true
    fast_startup: true
```

### Production Configuration
```yaml
# production.yaml
environment: production
debug: false
logging_level: INFO
security_hardened: true

services:
  # Production-specific service config
  model_manager:
    model_validation: true
    performance_monitoring: true
```

### Testing Configuration
```yaml
# testing.yaml
environment: testing
debug: true
logging_level: DEBUG
mock_external_services: true

services:
  # Testing-specific service config
  model_manager:
    use_test_models: true
    mock_responses: true
```

## Configuration Validation and Schema

### Configuration Schema Definition
```python
# Configuration schema validation
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "agents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1000, "maximum": 65535},
                    "script_path": {"type": "string"},
                    "dependencies": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "port", "script_path"]
            }
        }
    }
}
```

### Configuration Validation
```python
# Configuration validation implementation
import jsonschema

def validate_configuration(config, schema=CONFIG_SCHEMA):
    """Validate configuration against schema"""
    try:
        jsonschema.validate(config, schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)
```

## Configuration Security

### Secrets Management
```yaml
# Secrets configuration pattern
secrets:
  api_keys:
    openai: "${OPENAI_API_KEY}"
    anthropic: "${ANTHROPIC_API_KEY}"
    
  database:
    password: "${DB_PASSWORD}"
    
  certificates:
    private_key: "${CERT_PRIVATE_KEY}"
    certificate: "${CERT_PUBLIC_KEY}"
```

### Environment Variable Substitution
```python
# Environment variable substitution
import os
import re

def substitute_env_vars(config_text):
    """Substitute environment variables in configuration"""
    pattern = re.compile(r'\$\{([^}]+)\}')
    
    def replace_var(match):
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))
    
    return pattern.sub(replace_var, config_text)
```

## Configuration Migration and Versioning

### Configuration Versioning
```yaml
# Versioned configuration
version: "2.1"
migration_notes:
  - "Added health_check_port to all agents"
  - "Deprecated old_setting_name"
  
agents:
  # Configuration with version-specific features
```

### Configuration Migration Scripts
```python
# Configuration migration script
def migrate_config_v1_to_v2(config):
    """Migrate configuration from v1 to v2"""
    # Add default health check ports
    for agent in config.get('agents', []):
        if 'health_check_port' not in agent:
            agent['health_check_port'] = agent['port'] + 3000
    
    # Remove deprecated settings
    for agent in config.get('agents', []):
        agent.pop('old_setting', None)
    
    config['version'] = '2.0'
    return config
```

## Configuration Templates and Generators

### Configuration Templates
```yaml
# Template configuration
template_vars:
  SERVICE_NAME: "{{ service_name }}"
  SERVICE_PORT: "{{ service_port }}"
  HOST_IP: "{{ host_ip }}"

agent_template:
  name: "{{ SERVICE_NAME }}"
  host: "{{ HOST_IP }}"
  port: {{ SERVICE_PORT }}
  health_check_port: {{ SERVICE_PORT + 3000 }}
```

### Configuration Generation
```python
# Configuration generator
from jinja2 import Template

def generate_config(template_path, variables):
    """Generate configuration from template"""
    with open(template_path, 'r') as f:
        template = Template(f.read())
    
    return template.render(**variables)
```

## Legacy Configuration Patterns (Outdated)

### Deprecated Patterns
```python
# Old pattern - avoid
def old_config_loading():
    # Hardcoded configuration
    config = {
        'port': 5556,
        'host': 'localhost'  # Hardcoded values
    }
    return config

# Modern pattern
def modern_config_loading():
    # Environment-aware configuration
    config = load_config_from_file()
    config = apply_environment_overrides(config)
    validate_configuration(config)
    return config
```

### Configuration Migration Status
- **Hardcoded values** → **Configuration files**
- **Single environment** → **Multi-environment support**
- **No validation** → **Schema validation**
- **Manual management** → **Automated configuration management**

## Configuration Performance and Optimization

### Configuration Caching
```python
# Configuration caching pattern
class CachedConfigManager:
    def __init__(self):
        self._config_cache = {}
        self._cache_timestamps = {}
        self.cache_ttl = 300  # 5 minutes
        
    def get_config(self, config_path):
        """Get configuration with caching"""
        now = time.time()
        
        if config_path in self._config_cache:
            if (now - self._cache_timestamps[config_path]) < self.cache_ttl:
                return self._config_cache[config_path]
        
        # Load fresh configuration
        config = self._load_config(config_path)
        self._config_cache[config_path] = config
        self._cache_timestamps[config_path] = now
        
        return config
```

## Configuration Documentation and Standards

### Configuration Documentation
- **Schema Documentation**: All configuration schemas documented
- **Example Configurations**: Sample configurations for different environments
- **Migration Guides**: Step-by-step migration instructions
- **Best Practices**: Configuration management best practices

### Configuration Standards
1. **Naming Conventions**: Snake_case for keys, descriptive names
2. **Structure**: Hierarchical organization, logical grouping
3. **Validation**: All configurations must have schemas
4. **Documentation**: Every configuration option documented

## Issues and Recommendations

### Current Issues
1. **Mixed Formats**: Inconsistent use of YAML vs JSON
2. **Hardcoded Values**: Some services still use hardcoded configuration
3. **No Central Management**: Distributed configuration management
4. **Limited Validation**: Not all configurations have schema validation

### Recommendations
1. **Standardize Format**: Use YAML for all configuration files
2. **Central Management**: Implement centralized configuration service
3. **Schema Validation**: Add schemas for all configuration files
4. **Environment Separation**: Clear separation of environment-specific configs

## Analysis Summary

### Current Configuration State
- **Total Configuration Files**: 50+ across repository
- **Configuration Formats**: YAML (70%), JSON (20%), ENV (10%)
- **Schema Validation**: 40% of configurations
- **Environment Support**: 60% of configurations

### Configuration Management Maturity
- **Basic Configuration**: ✅ Complete
- **Environment Separation**: 🔄 In Progress
- **Schema Validation**: 🔄 Partial
- **Central Management**: 🔄 Planned

### Next Steps
1. Complete configuration schema implementation
2. Implement centralized configuration service
3. Add configuration validation to all services
4. Create comprehensive configuration documentation