#!/bin/sh
# This script runs as root before the main command.

# Create necessary directories if they don't exist
mkdir -p /app/logs /app/models /app/data

# Ensure proper permissions for the appuser
chown -R appuser:appuser /app/logs /app/data

# Execute the command passed to this script (the original docker-compose command)
# This will run as the 'appuser' because of the USER directive in the Dockerfile.
exec "$@"
