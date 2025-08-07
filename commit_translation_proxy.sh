#!/bin/bash
set -euo pipefail

echo "🔄 Adding files to git..."
git add services/streaming_translation_proxy/
git add tests/test_translation_proxy_import.py
git add main_pc_code/config/startup_config.yaml

echo "📝 Committing changes..."
git commit -m "feat: Add Streaming Translation Proxy service

- Create FastAPI/WebSocket-based translation proxy
- Add real-time translation via WebSocket endpoint /ws
- Include health check endpoint /health
- Integrate Prometheus metrics on port 9106
- Add OpenAI GPT-4o translation backend
- Update startup_config.yaml with service configuration
- Add translation_proxy docker group for deployment
- Dependencies: CloudTranslationService, SystemDigitalTwin

Service Features:
- WebSocket endpoint for real-time translation
- JSON request format: {\"text\": \"...\", \"target_lang\": \"...\"}
- JSON response format: {\"translated\": \"...\"}
- Prometheus metrics tracking by target language
- Docker containerization with Python 3.10-slim
- Auto-startup integration with MainPC system

Files:
- services/streaming_translation_proxy/proxy.py
- services/streaming_translation_proxy/Dockerfile
- services/streaming_translation_proxy/requirements.txt
- tests/test_translation_proxy_import.py
- Updated main_pc_code/config/startup_config.yaml"

echo "⬆️ Pushing to remote branch..."
git push origin HEAD

echo "✅ All changes committed and pushed successfully!"