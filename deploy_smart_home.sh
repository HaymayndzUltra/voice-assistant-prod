#!/bin/bash
# Smart Home Integration Deployment Script for MainPC
# Integrates Tapo L520 smart light with utility_cpu group

set -e

echo "🏠 Deploying Smart Home Agent to MainPC utility_cpu group..."

# Check if environment variables are set
if [ -z "$TAPO_USERNAME" ] || [ -z "$TAPO_PASSWORD" ]; then
    echo "❌ Error: TAPO_USERNAME and TAPO_PASSWORD environment variables must be set"
    echo "Example:"
    echo "export TAPO_USERNAME='your_email@gmail.com'"
    echo "export TAPO_PASSWORD='your_password'"
    exit 1
fi

echo "✅ Environment variables configured"

# Navigate to utility_cpu directory
cd docker/utility_cpu

echo "🔨 Building utility_cpu image with smart home dependencies..."
docker-compose build

echo "🚀 Starting smart home agent..."
docker-compose up -d smart_home_agent

echo "⏳ Waiting for service to be ready..."
sleep 10

# Health check
echo "🔍 Performing health checks..."
if curl -s http://localhost:6599/devices/status > /dev/null 2>&1; then
    echo "✅ Smart Home Agent API is responding"
else
    echo "⚠️  API not responding yet, checking container status..."
    docker logs smart_home_agent --tail 20
fi

echo ""
echo "🎉 Smart Home Integration Deployed!"
echo ""
echo "📍 Service Information:"
echo "   - Container: smart_home_agent"
echo "   - Service Port: 5599"
echo "   - API Port: 6599"
echo "   - Group: utility_cpu (5 services total)"
echo ""
echo "🎯 Quick Tests:"
echo ""
echo "# Check device status"
echo "curl http://localhost:6599/devices/status | jq"
echo ""
echo "# Turn on your L520 light"
echo "curl -X POST http://localhost:6599/lights/control \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"device_id\": \"tapo_l520_main\", \"action\": {\"command\": \"turn_on\", \"brightness\": 70}}'"
echo ""
echo "# Set evening relaxation mode"
echo "curl -X POST http://localhost:6599/lights/intelligent \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"time_of_day\": \"evening\", \"activity\": \"relaxation\", \"mood\": \"calm\"}'"
echo ""
echo "# Voice command test"
echo "curl -X POST http://localhost:6599/voice/command \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"command\": \"Turn on the lights to 50% brightness\"}'"
echo ""
echo "🏠 Your Tapo L520 is now integrated with MainPC AI system!"