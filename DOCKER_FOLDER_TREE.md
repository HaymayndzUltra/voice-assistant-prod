# Docker Folder Tree Structure
## AI System Monorepo - Docker Architecture

```
AI_System_Monorepo/
├── 📁 voice-assistant-prod/
│   └── 📁 .cursor/
│
├── 📁 unified_observability_center/
│   ├── 📄 Dockerfile
│   ├── 📄 Dockerfile.optimized
│   ├── 📄 .dockerignore
│   ├── 📁 config/
│   ├── 📁 resiliency/
│   ├── 📁 tests/
│   ├── 📁 tools/
│   ├── 📁 api/
│   ├── 📁 bus/
│   ├── 📁 core/
│   ├── 📁 plugins/
│   ├── 📁 dashboards/
│   ├── 📄 pyproject.toml
│   ├── 📄 requirements.txt
│   ├── 📄 requirements-dev.txt
│   ├── 📄 requirements.noprophet.txt
│   ├── 📄 app.py
│   └── 📄 README.md
│
├── 📁 real_time_audio_pipeline/
│   ├── 📄 Dockerfile
│   ├── 📄 Dockerfile.optimized
│   ├── 📄 .dockerignore
│   ├── 📁 config/
│   ├── 📁 core/
│   ├── 📁 transport/
│   ├── 📁 docker/
│   ├── 📁 proto/
│   ├── 📁 resiliency/
│   ├── 📁 tests/
│   ├── 📄 pyproject.toml
│   ├── 📄 requirements.txt
│   ├── 📄 requirements.runtime.txt
│   ├── 📄 requirements.runtime.lock
│   ├── 📄 app.py
│   ├── 📄 deploy.sh
│   ├── 📄 docker-compose.yml
│   ├── 📄 README.md
│   ├── 📄 DEPLOYMENT_VERIFICATION.md
│   ├── 📄 LEGACY_DECOMMISSIONING_PLAN.md
│   ├── 📄 RISK_MITIGATION_CHECKLIST.md
│   └── 📄 __init__.py
│
├── 📁 memory_fusion_hub/
│   ├── 📄 Dockerfile
│   ├── 📄 Dockerfile.optimized
│   ├── 📁 core/
│   ├── 📁 proxy/
│   ├── 📁 resiliency/
│   ├── 📁 transport/
│   ├── 📁 adapters/
│   ├── 📁 config/
│   ├── 📁 tests/
│   ├── 📄 app.py
│   ├── 📄 docker-compose.yml
│   ├── 📄 memory_fusion.proto
│   ├── 📄 memory_fusion_pb2.py
│   ├── 📄 memory_fusion_pb2_grpc.py
│   ├── 📄 requirements.txt
│   ├── 📄 README.md
│   ├── 📄 DEPLOYMENT_CHECKLIST.md
│   └── 📄 __init__.py
│
├── 📁 model_ops_coordinator/
│   ├── 📄 Dockerfile
│   ├── 📄 Dockerfile.optimized
│   ├── 📄 .dockerignore
│   ├── 📁 adapters/
│   ├── 📁 config/
│   ├── 📁 core/
│   ├── 📁 resiliency/
│   ├── 📁 tests/
│   ├── 📁 transport/
│   ├── 📁 deploy/
│   ├── 📁 docs/
│   ├── 📁 proto/
│   ├── 📄 pyproject.toml
│   ├── 📄 requirements.txt
│   ├── 📄 requirements.lock
│   ├── 📄 app.py
│   ├── 📄 model_ops_pb2.py
│   ├── 📄 model_ops_pb2_grpc.py
│   ├── 📄 network_util.py
│   ├── 📄 README.md
│   ├── 📄 COMPLETE_PROJECT_REVIEW.md
│   ├── 📄 PHASE6_VERIFICATION.md
│   ├── 📄 PHASE7_VERIFICATION.md
│   ├── 📄 PROJECT_SUMMARY.md
│   └── 📄 __init__.py
│
├── 📁 affective_processing_center/
│   ├── 📄 Dockerfile
│   ├── 📄 Dockerfile.optimized
│   ├── 📄 .dockerignore
│   ├── 📁 config/
│   ├── 📁 core/
│   ├── 📁 modules/
│   ├── 📁 resiliency/
│   ├── 📁 tests/
│   ├── 📄 pyproject.toml
│   ├── 📄 requirements.txt
│   ├── 📄 app.py
│   ├── 📄 verification_gate.py
│   ├── 📄 docker-compose.yml
│   ├── 📄 README.md
│   ├── 📄 deployment_plan.md
│   └── 📄 __init__.py
│
├── 📁 common/
│   ├── 📁 utils/
│   ├── 📁 security/
│   ├── 📁 service_mesh/
│   ├── 📁 validation/
│   ├── 📁 api/
│   ├── 📁 audit/
│   ├── 📁 backends/
│   ├── 📁 config/
│   ├── 📁 core/
│   ├── 📁 error_bus/
│   ├── 📁 factories/
│   ├── 📁 health/
│   ├── 📁 lifecycle/
│   ├── 📁 logging/
│   ├── 📁 monitoring/
│   ├── 📁 observability/
│   ├── 📁 performance/
│   ├── 📁 pools/
│   ├── 📁 resiliency/
│   ├── 📁 resources/
│   ├── 📁 service_discovery/
│   ├── 📁 constants/
│   ├── 📄 pyproject.toml
│   ├── 📄 __init__.py
│   ├── 📄 config_manager.py
│   ├── 📄 env_helpers.py
│   ├── 📄 health.py
│   └── 📄 hybrid_api_manager.py
│
├── 📁 config/
│   ├── 📁 machine-profiles/
│   ├── 📁 observability/
│   ├── 📁 overrides/
│   ├── 📄 unified_startup.yaml
│   ├── 📄 unified_startup_core.yaml
│   ├── 📄 unified_startup_phase2.yaml
│   ├── 📄 default.yaml
│   ├── 📄 environment.yaml
│   ├── 📄 feature_flags.yaml
│   ├── 📄 machine_config.yaml
│   ├── 📄 main_pc.yaml
│   ├── 📄 mcp_servers.json
│   ├── 📄 memory_env.yaml
│   ├── 📄 nats_error_bus.json
│   ├── 📄 network_config.yaml
│   ├── 📄 pc2.yaml
│   ├── 📄 service_registry.json
│   ├── 📄 startup_config.v3.yaml
│   ├── 📄 startup_config.yaml
│   └── 📄 DEPRECATED_README.md
│
├── 📁 entrypoints/
│   ├── 📄 affective_processing_center_entrypoint.sh
│   ├── 📄 central_error_bus_entrypoint.sh
│   ├── 📄 model_ops_entrypoint.sh
│   ├── 📄 real_time_audio_pipeline_entrypoint.sh
│   ├── 📄 self_healing_supervisor_entrypoint.sh
│   └── 📄 unified_observability_center_entrypoint.sh
│
├── 📁 scripts/
│
├── 📁 requirements/
│
├── 📁 AI/
│
├── 📁 AI_System_Monolopi/
│
├── 📄 .dockerignore
├── 📄 DOCKER_WORKFLOW_README.md
├── 📄 docker_image_inventory.md
├── 📄 OPTIMIZED_DOCKER_COMPLETE.md
├── 📄 PARALLEL_BUILD_STRATEGY.md
├── 📄 SLIM_DOCKER_STRATEGY.md
├── 📄 STORAGE_SOLUTIONS.md
├── 📄 VERIFIED_DOCKER_PATHS.md
├── 📄 CREATE_ALL_DOCKERFILES.py
├── 📄 FIX_DOCKERFILES_PATHS.py
├── 📄 FIX_HEALTH_LABELS.py
├── 📄 build.sh
├── 📄 build2.sh
├── 📄 batch_containerize_foundation.sh
├── 📄 deploy_docker_desktop.sh
├── 📄 deploy_native_linux.sh
├── 📄 rebuild_all_images.sh
├── 📄 pull_and_deploy.sh
├── 📄 mainpc_execute.sh
├── 📄 execute_phase4_mainpc.sh
├── 📄 PC2_EXECUTE_NOW.sh
├── 📄 QUICK_FIX_MAINPC.sh
├── 📄 BUILD_ALL_OPTIMIZED.sh
├── 📄 BUILD_AND_PUSH.sh
├── 📄 BUILD_AND_PUSH_WITH_VERIFY.sh
├── 📄 BUILD_LOCAL_FIRST.sh
├── 📄 CLEANUP_IMAGES_PROPERLY.sh
├── 📄 DIAGNOSE_CONTAINERS.sh
├── 📄 DIAGNOSE_STARTUP_ISSUE.sh
├── 📄 DOCKER_DESKTOP_FIX.sh
├── 📄 EMERGENCY_CLEANUP.sh
├── 📄 FIX_MAINPC_DEPLOYMENT.sh
├── 📄 AGENT1_BUILD_BASE.sh
├── 📄 AGENT2_BUILD_FAMILY.sh
├── 📄 AGENT3_BUILD_CPU_SERVICES.sh
├── 📄 phase4_quick_build.sh
├── 📄 PULL_ESSENTIAL_IMAGES.sh
├── 📄 SHOW_ALL_DOCKER.sh
├── 📄 SMART_CLEANUP.sh
├── 📄 WSL2_FIX_DEPLOYMENT.sh
├── 📄 NUCLEAR_CLEANUP_NOW.sh
├── 📄 check_deployment_status.sh
├── 📄 validate_fleet.sh
├── 📄 verify_ghcr_images.sh
└── 📄 build_family_vision.log
```

## 📊 Docker Architecture Summary

### **Core Services with Dockerfiles:**
1. **unified_observability_center** - Monitoring & observability service
2. **real_time_audio_pipeline** - Audio processing pipeline
3. **memory_fusion_hub** - Memory management & fusion
4. **model_ops_coordinator** - Model operations coordination
5. **affective_processing_center** - Emotional processing service

### **Common Infrastructure:**
- **common/** - Shared utilities, security, health checks
- **config/** - Configuration files, machine profiles, startup configs
- **entrypoints/** - Container entrypoint scripts
- **scripts/** - Build, deployment, and management scripts

### **Key Docker Files:**
- **Dockerfile** - Standard container definition
- **Dockerfile.optimized** - Optimized container variants
- **.dockerignore** - Container build exclusions
- **docker-compose.yml** - Multi-container orchestration

### **Build & Deployment Scripts:**
- **build.sh** - Main build script
- **deploy_*.sh** - Platform-specific deployment
- **rebuild_all_images.sh** - Complete rebuild
- **cleanup_*.sh** - Maintenance and cleanup

### **Configuration Management:**
- **unified_startup.yaml** - Main startup configuration
- **machine_config.yaml** - Machine-specific settings
- **service_registry.json** - Service discovery configuration

---

**Total Docker Services:** 5 main services + common infrastructure  
**Containerization Level:** 100% containerized architecture  
**Build Strategy:** Multi-stage, optimized Dockerfiles  
**Orchestration:** Docker Compose + custom deployment scripts
