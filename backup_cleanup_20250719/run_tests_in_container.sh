#!/bin/bash

# Run tests in Docker container

echo "=== Building test container ==="
docker-compose -f docker-compose.test.yml build

echo "=== Starting test container ==="
docker-compose -f docker-compose.test.yml up -d

echo "=== Waiting for container to initialize (5 seconds) ==="
sleep 5

echo "=== Installing pytest in container ==="
docker exec testrunner pip install pytest pytest-xdist

echo "=== Running tests in container ==="
docker exec -it testrunner bash -c "cd /app && python -m pytest tests/ -v"

echo "=== Test run complete ==="

echo "=== Stopping test container ==="
docker-compose -f docker-compose.test.yml down 