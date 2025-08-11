#!/bin/bash

REPO_ROOT="/home/haymayndz/AI_System_Monorepo"

echo "📌 Action Checklist (auto-suggest) — $(date '+%Y-%m-%d %H:%M:%S')"
echo "Repo: $REPO_ROOT"
echo

# 1) Safety gate before marking a phase done
echo "➡️  Phase Gate (run before marking done):"
echo

# 2) PC2 Build sequence discovered from conversation (run on PC2 machine)
echo "➡️  PC2 Build — recommended order (run on PC2):"
echo "   cd $REPO_ROOT/docker/pc2_infra_core && docker compose up -d --build"
echo "   cd $REPO_ROOT/docker/pc2_memory_stack && docker compose up -d --build"
echo "   cd $REPO_ROOT/docker/pc2_async_pipeline && docker compose up -d --build"
echo "   cd $REPO_ROOT/docker/pc2_tutoring_cpu && docker compose up -d --build"
echo "   cd $REPO_ROOT/docker/pc2_utility_suite && docker compose up -d --build"
echo "   cd $REPO_ROOT/docker/pc2_vision_dream_gpu && docker compose up -d --build   # if GPU available"
echo "   cd $REPO_ROOT/docker/pc2_web_interface && docker compose up -d --build"
echo

# 3) Quick status checks
echo "➡️  Status checks:"
echo "   docker ps | grep pc2"
echo "   docker logs pc2_observability_hub --tail 20"
echo

# 4) Cleanup helpers
echo "➡️  Cleanup (use with care):"
echo "   docker system prune -f && docker volume prune -f"
echo

# 5) Observability/traceability (Phase 5 reminder)
echo "➡️  Observability (Phase 5 prep): ensure services report GIT_SHA + SBOM to UOC at startup"
echo

echo "💡 Tip: After the gate says 'Gate ok', you can mark as done:"
echo "   python3 $REPO_ROOT/todo_manager.py done docker_arch_impl_20250810 4"
echo

