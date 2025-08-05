# Standardized Agent Directory Structure

## Target Structure for Each Agent

For each agent, the individual container structure will be:

```
/workspace/docker/AGENT_NAME/
├── Dockerfile
├── requirements.txt
└── docker-compose.yml
```

## Template Files

- **Dockerfile Template:** `/workspace/templates/Dockerfile.template`
- **Agent Data:** `/workspace/migration_data.json`

## Implementation Notes

1. **AGENT_NAME** will be replaced by the automation script with the actual agent name
2. **HEALTH_PORT** will be dynamically set based on the agent's health check port configuration
3. All 47 agents will use the same standardized Dockerfile template
4. The requirements.txt will be generated per-agent based on import analysis
5. The docker-compose.yml will be generated using the extracted port, environment, and dependency data

## Directory Creation Pattern

The automation script will create directories using this pattern:
- Source: `/workspace/migration_data.json`
- Target: `/workspace/docker/{agent_name}/`
- Template: `/workspace/templates/Dockerfile.template`

## Validation

The standardized structure ensures:
- Consistent build process across all agents
- Proper dependency management
- Health check standardization
- Simplified orchestration