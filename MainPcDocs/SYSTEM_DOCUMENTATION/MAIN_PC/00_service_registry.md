# Service Registry

## Overview

The Service Registry is a lightweight, highly-available service discovery component that enables agents to register themselves and discover other agents in the system. It serves as the primary service discovery mechanism, replacing the previous implementation in the SystemDigitalTwin.

## Features

- **Service Registration**: Agents can register their endpoints (host, port, health check port)
- **Service Discovery**: Agents can query for endpoints of other agents
- **Health Checks**: Standard health check endpoints for monitoring
- **High Availability**: Optional Redis backend for persistence and HA deployment
- **Zero External Dependencies** (in memory mode): Can start before other components

## API

### Register Agent

```json
{
  "action": "register_agent",
  "agent_id": "MyAgent",
  "host": "localhost",
  "port": 5000,
  "health_check_port": 6000,
  "agent_type": "service",
  "capabilities": ["feature1", "feature2"],
  "metadata": { "version": "1.0.0" }
}
```

Response:

```json
{
  "status": "success"
}
```

### Get Agent Endpoint

```json
{
  "action": "get_agent_endpoint",
  "agent_name": "MyAgent"
}
```

Response:

```json
{
  "status": "success",
  "host": "localhost",
  "port": 5000,
  "health_check_port": 6000,
  "agent_type": "service",
  "capabilities": ["feature1", "feature2"],
  "metadata": { "version": "1.0.0" },
  "last_registered": "2025-07-03T12:34:56.789Z"
}
```

### List Agents

```json
{
  "action": "list_agents"
}
```

Response:

```json
{
  "status": "success",
  "agents": ["MyAgent", "AnotherAgent", "ThirdAgent"]
}
```

## Ports

- **ZMQ Port**: 7100 (configurable via `SERVICE_REGISTRY_PORT` environment variable)
- **Health Check Port**: 8100 (configurable via `SERVICE_REGISTRY_HEALTH_PORT` environment variable)

## Backend Storage Options

The Service Registry supports two backend storage options:

### In-Memory (Default)

- Fast and lightweight
- No external dependencies
- Data is lost on restart
- Suitable for development and simple deployments

### Redis

- Persistent storage
- High availability support
- Data survives restarts
- Suitable for production deployments

## Configuration

### Environment Variables

- `SERVICE_REGISTRY_PORT`: ZMQ port (default: 7100)
- `SERVICE_REGISTRY_HEALTH_PORT`: Health check port (default: 8100)
- `SERVICE_REGISTRY_BACKEND`: Storage backend, "memory" or "redis" (default: "memory")
- `SERVICE_REGISTRY_REDIS_URL`: Redis connection URL (default: "redis://localhost:6379/0")
- `SERVICE_REGISTRY_REDIS_PREFIX`: Key prefix for Redis storage (default: "service_registry:")

### Command Line Arguments

```bash
python main_pc_code/agents/service_registry_agent.py --backend redis --redis-url redis://localhost:6379/0
```

## High Availability Deployment

For high availability, you can run multiple instances of the Service Registry with a Redis backend. All instances will share the same data through Redis.

Example docker-compose configuration:

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  service-registry-1:
    build: .
    command: python main_pc_code/agents/service_registry_agent.py --backend redis --redis-url redis://redis:6379/0
    ports:
      - "7100:7100"
      - "8100:8100"
    depends_on:
      - redis

  service-registry-2:
    build: .
    command: python main_pc_code/agents/service_registry_agent.py --backend redis --redis-url redis://redis:6379/0
    ports:
      - "7101:7100"
      - "8101:8100"
    depends_on:
      - redis
```

## Health Check

The Service Registry provides a health check endpoint at `/health` on the health check port:

```bash
curl http://localhost:8100/health
```

Response:

```json
{
  "status": "ok",
  "message": "ServiceRegistry is healthy",
  "timestamp": "2025-07-03T12:34:56.789Z"
}
```

## Example curl Requests

### Register an agent

```bash
curl -X POST http://localhost:7100 \
  -H "Content-Type: application/json" \
  -d '{
    "action": "register_agent",
    "agent_id": "TestAgent",
    "host": "localhost",
    "port": 5000,
    "health_check_port": 6000,
    "agent_type": "service",
    "capabilities": ["test"],
    "metadata": {}
  }'
```

### Get an agent endpoint

```bash
curl -X POST http://localhost:7100 \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_agent_endpoint",
    "agent_name": "TestAgent"
  }'
```

### List all agents

```bash
curl -X POST http://localhost:7100 \
  -H "Content-Type: application/json" \
  -d '{"action": "list_agents"}'
```

### Health check

```bash
curl http://localhost:8100/health
``` 