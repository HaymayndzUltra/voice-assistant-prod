#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# 0.  CONFIGURATION & VALIDATION                                              #
###############################################################################
export GHCR_USER="${GHCR_USER:-haymayndzultra}"
export GHCR_TOKEN="${GHCR_TOKEN:-}"
export REGISTRY="ghcr.io/${GHCR_USER}"
export GIT_SHA="$(git rev-parse --short HEAD)"
export OPENAI_KEY="${OPENAI_KEY:-}"

# Validate required environment variables
if [[ -z "$GHCR_TOKEN" ]]; then
    echo "❌ GHCR_TOKEN environment variable not set"
    echo "   Set it with: export GHCR_TOKEN='your_token_here'"
    exit 1
fi

if [[ -z "$OPENAI_KEY" ]]; then
    echo "❌ OPENAI_KEY environment variable not set"
    echo "   Set it with: export OPENAI_KEY='your_openai_key_here'"
    exit 1
fi

echo "✅ Configuration validated"
echo "   Registry: $REGISTRY"
echo "   Git SHA: $GIT_SHA"

###############################################################################
# 1.  LOGIN TO GHCR                                                           #
###############################################################################
echo "🔐 Logging into GitHub Container Registry..."
if ! echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin; then
    echo "❌ Docker login failed"
    exit 1
fi
echo "✅ Docker login successful"

###############################################################################
# 2.  BUILD & PUSH IMAGES                                                     #
###############################################################################
echo "🏗️  Building and pushing images..."

# A. Remote-API Adapter
echo "📦 Building remote-api-adapter..."
if [[ ! -f "remote_api_adapter/Dockerfile" ]]; then
    echo "❌ remote_api_adapter/Dockerfile not found"
    exit 1
fi

if ! docker build -t "$REGISTRY/remote-api-adapter:$GIT_SHA" \
                  -f remote_api_adapter/Dockerfile .; then
    echo "❌ Failed to build remote-api-adapter"
    exit 1
fi

if ! docker push "$REGISTRY/remote-api-adapter:$GIT_SHA"; then
    echo "❌ Failed to push remote-api-adapter"
    exit 1
fi
echo "✅ remote-api-adapter built and pushed"

# B. Tiny-Llama (GPU local model)
echo "📦 Building tiny-llama..."
if [[ ! -d "tiny_llama_context" ]]; then
    echo "❌ tiny_llama_context directory not found"
    exit 1
fi

if ! docker build -t "$REGISTRY/tiny-llama:$GIT_SHA" tiny_llama_context; then
    echo "❌ Failed to build tiny-llama"
    exit 1
fi

if ! docker push "$REGISTRY/tiny-llama:$GIT_SHA"; then
    echo "❌ Failed to push tiny-llama"
    exit 1
fi
echo "✅ tiny-llama built and pushed"

# C. Observability-Hub image
echo "📦 Building observability-hub..."
if [[ ! -f "docker/mainpc/Dockerfile.observability" ]]; then
    echo "❌ docker/mainpc/Dockerfile.observability not found"
    exit 1
fi

if ! docker build -t "$REGISTRY/observability-hub:$GIT_SHA" \
                  -f docker/mainpc/Dockerfile.observability docker/mainpc; then
    echo "❌ Failed to build observability-hub"
    exit 1
fi

if ! docker push "$REGISTRY/observability-hub:$GIT_SHA"; then
    echo "❌ Failed to push observability-hub"
    exit 1
fi
echo "✅ observability-hub built and pushed"

###############################################################################
# 3.  WRITE SECRETS                                                           #
###############################################################################
echo "🔒 Setting up secrets..."
mkdir -p secrets

# Create OpenAI key secret
echo "$OPENAI_KEY" > secrets/openai_api_key
chmod 600 secrets/openai_api_key
echo "✅ OpenAI API key secret created"

# Optional: Create Bedrock key if provided
if [[ -n "${BEDROCK_KEY:-}" ]]; then
    echo "$BEDROCK_KEY" > secrets/bedrock_key
    chmod 600 secrets/bedrock_key
    echo "✅ Bedrock key secret created"
fi

###############################################################################
# 4.  PATCH DOCKER COMPOSE FILES                                              #
###############################################################################
echo "📝 Updating docker-compose files..."

# Patch hybrid compose
if [[ -f "docker-compose.hybrid.yml" ]]; then
    sed -i "s|ghcr.io/.*/remote-api-adapter:.*|${REGISTRY}/remote-api-adapter:${GIT_SHA}|g" docker-compose.hybrid.yml
    sed -i "s|ghcr.io/.*/tiny-llama:.*|${REGISTRY}/tiny-llama:${GIT_SHA}|g" docker-compose.hybrid.yml
    sed -i "s|ghcr.io/.*/observability-hub:.*|${REGISTRY}/observability-hub:${GIT_SHA}|g" docker-compose.hybrid.yml
    echo "✅ docker-compose.hybrid.yml updated"
fi

# Patch mainpc compose if it exists
if [[ -f "docker/mainpc/docker-compose.mainpc.yml" ]]; then
    sed -i "s|ghcr.io/.*/observability-hub:.*|${REGISTRY}/observability-hub:${GIT_SHA}|g" docker/mainpc/docker-compose.mainpc.yml
    echo "✅ docker/mainpc/docker-compose.mainpc.yml updated"
fi

###############################################################################
# 5.  SET HUB_ENDPOINT FOR METRICS-FORWARDER                                  #
###############################################################################
export HUB_ENDPOINT="http://observability-hub-primary:9090/api/v1/write"

###############################################################################
# 6.  BRING UP THE STACK                                                      #
###############################################################################
echo "🚀 Starting the stack..."
if ! docker compose \
    -f docker/mainpc/docker-compose.mainpc.yml \
    -f docker-compose.hybrid.yml \
    up -d; then
    echo "❌ Failed to start stack"
    exit 1
fi

echo "✅ Stack started successfully"

###############################################################################
# 7.  HEALTH CHECKS                                                           #
###############################################################################
echo "🏥 Performing health checks..."

# Wait for containers to be ready
echo "⏳ Waiting for containers to be ready..."
sleep 30

# Check container status
echo "== Container status =="
if ! docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"; then
    echo "❌ Failed to get container status"
    exit 1
fi

# Check remote-api-adapter health
echo -e "\n== Remote-API adapter health =="
REMOTE_API_CONTAINER=$(docker ps -qf "ancestor=$REGISTRY/remote-api-adapter:$GIT_SHA")
if [[ -n "$REMOTE_API_CONTAINER" ]]; then
    if docker exec "$REMOTE_API_CONTAINER" \
        python -m remote_api_adapter.adapter health_check; then
        echo "✅ Remote-API adapter healthy"
    else
        echo "❌ Remote-API adapter health check failed"
        exit 1
    fi
else
    echo "❌ Remote-API adapter container not found"
    exit 1
fi

echo "🎉 Deployment completed successfully!" 