#!/bin/bash

# Health check script for PC2 tutoring CPU services
# Checks if the service is responding on its health port

# Get health port from environment or use default
HEALTH_PORT=${HEALTH_PORT:-8108}

# Try to curl the health endpoint
curl -f http://localhost:${HEALTH_PORT}/health >/dev/null 2>&1
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Health check passed"
    exit 0
else
    echo "Health check failed"
    exit 1
fi
