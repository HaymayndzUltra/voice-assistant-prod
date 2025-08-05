#!/bin/bash
# Builds all individual PC-2 agent services
docker-compose -f /workspace/docker-compose.individual.yml build $(docker-compose -f /workspace/docker-compose.individual.yml config --services | grep '^pc2_')