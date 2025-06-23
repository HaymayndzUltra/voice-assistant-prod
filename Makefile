# Makefile for AI System Monorepo

# Docker-related variables
DOCKER_COMPOSE_FILE = docker/docker-compose.voice_pipeline.yml
DOCKER_COMPOSE = docker-compose -f $(DOCKER_COMPOSE_FILE)

# Default target
.PHONY: help
help:
	@echo "AI System Monorepo Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  help                 - Show this help message"
	@echo "  docker-build         - Build Docker images"
	@echo "  docker-up            - Start Docker containers"
	@echo "  docker-down          - Stop Docker containers"
	@echo "  docker-logs          - Show Docker logs"
	@echo "  docker-ps            - Show Docker container status"
	@echo "  docker-restart       - Restart Docker containers"
	@echo "  docker-clean         - Clean Docker resources"
	@echo "  generate-certs       - Generate ZMQ certificates"
	@echo "  deploy-voice-pipeline - Deploy voice pipeline with Docker"
	@echo ""

# Docker targets
.PHONY: docker-build
docker-build:
	$(DOCKER_COMPOSE) build

.PHONY: docker-up
docker-up:
	$(DOCKER_COMPOSE) up -d

.PHONY: docker-down
docker-down:
	$(DOCKER_COMPOSE) down

.PHONY: docker-logs
docker-logs:
	$(DOCKER_COMPOSE) logs -f

.PHONY: docker-ps
docker-ps:
	$(DOCKER_COMPOSE) ps

.PHONY: docker-restart
docker-restart:
	$(DOCKER_COMPOSE) restart

.PHONY: docker-clean
docker-clean:
	$(DOCKER_COMPOSE) down -v --rmi local
	docker system prune -f

# Certificate generation
.PHONY: generate-certs
generate-certs:
	python scripts/generate_zmq_certificates.py

# Voice pipeline deployment
.PHONY: deploy-voice-pipeline
deploy-voice-pipeline:
	bash scripts/deploy_voice_pipeline_docker.sh

# Individual service targets
.PHONY: start-system-digital-twin
start-system-digital-twin:
	$(DOCKER_COMPOSE) up -d system-digital-twin

.PHONY: start-task-router
start-task-router:
	$(DOCKER_COMPOSE) up -d task-router

.PHONY: start-streaming-tts
start-streaming-tts:
	$(DOCKER_COMPOSE) up -d streaming-tts-agent

.PHONY: start-tts
start-tts:
	$(DOCKER_COMPOSE) up -d tts-agent

.PHONY: start-responder
start-responder:
	$(DOCKER_COMPOSE) up -d responder

.PHONY: start-interrupt-handler
start-interrupt-handler:
	$(DOCKER_COMPOSE) up -d streaming-interrupt-handler

# Service logs
.PHONY: logs-system-digital-twin
logs-system-digital-twin:
	$(DOCKER_COMPOSE) logs -f system-digital-twin

.PHONY: logs-task-router
logs-task-router:
	$(DOCKER_COMPOSE) logs -f task-router

.PHONY: logs-streaming-tts
logs-streaming-tts:
	$(DOCKER_COMPOSE) logs -f streaming-tts-agent

.PHONY: logs-tts
logs-tts:
	$(DOCKER_COMPOSE) logs -f tts-agent

.PHONY: logs-responder
logs-responder:
	$(DOCKER_COMPOSE) logs -f responder

.PHONY: logs-interrupt-handler
logs-interrupt-handler:
	$(DOCKER_COMPOSE) logs -f streaming-interrupt-handler

# Health checks
.PHONY: check-health
check-health:
	python scripts/docker_health_check.py --service system-digital-twin
	python scripts/docker_health_check.py --service task-router
	python scripts/docker_health_check.py --service streaming-tts-agent
	python scripts/docker_health_check.py --service tts-agent
	python scripts/docker_health_check.py --service responder
	python scripts/docker_health_check.py --service streaming-interrupt-handler 