============================================================
🎮 TASK COMMAND & CONTROL CENTER
============================================================

📋 ALL OPEN TASKS:
========================================

1. 🗒️  dual_ai_system_optimization
   Description: Action plan for a comprehensive optimization and validation audit of a dual-mach...
   Status: in_progress
   Created: 2024-05-24T12:00:00Z
   TODO Items (8):
      [✗] 0. PHASE 0: SETUP & PROTOCOL (READ FIRST)

**Explanations:**
This initial step contains the user manual for this task plan. It outlines the commands to interact with the plan and the critical safety workflow that must be followed for all subsequent phases.

**Technical Artifacts:**
**HOW TO USE THIS TASK PLAN (COMMANDS & PROTOCOL)**

**I. COMMANDS:**
1.  **TO VIEW DETAILS:** `python3 todo_manager.py show dual_ai_system_optimization`
2.  **TO MARK AS DONE:** `python3 todo_manager.py done dual_ai_system_optimization <step_number>`

**II. WORKFLOW & SAFETY PROTOCOL (CRUCIAL):**
1.  **FOCUS ON CURRENT STEP:** In each Phase, always read and understand the `IMPORTANT NOTE` first.
2.  **REVIEW-CONFIRM-PROCEED LOOP:** After completing a Phase, review your work and the next Phase. If your confidence score is below 90%, REPEAT the review.

──────────────────────────────────
IMPORTANT NOTE: This phase contains the operating manual for the entire plan. Understanding these protocols is mandatory before proceeding to Phase 1. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 1. PHASE 1: MANDATORY SYSTEM DISCOVERY & CONTAINER VALIDATION

**Explanations:**
This phase begins with the mandatory system discovery script to map the entire file structure. Following the discovery, all 77 Docker containers will be analyzed to validate their structure, build process, and health.

**Technical Artifacts / Tasks:**
**1.0 MANDATORY SYSTEM DISCOVERY (RUN FIRST):**
CRITICAL: Execute this before any other analysis!
```bash
# Run the system discovery script to map the complete file structure
python system_discovery_script.py

# This will generate:
# - system_discovery_report.json (complete system mapping)
# - analysis_paths.json (specific file paths for analysis)
```

**1.1 SYSTEM DISCOVERY & CONTAINER ANALYSIS:**
**Container Discovery and Analysis:**
*   Docker Container Locations: `./docker/*/`
*   Expected Files per Container: `./docker/*/Dockerfile`, `./docker/*/docker-compose.yml`, `./docker/*/requirements.txt`, `./docker/*/requirements*.txt` (variations)

**Analysis Tasks:**
*   Analyze all 77 Docker containers in `./docker/` directory.
*   Validate each Dockerfile builds successfully without errors.
*   Check `docker-compose.yml` files for proper configuration.
*   Verify `requirements.txt` files have no conflicting dependencies.
*   Test container startup sequences following `startup_config.yaml` dependencies.
*   Document any containers that fail to build or start.
*   Validate health check endpoints respond correctly across both machines.

──────────────────────────────────
IMPORTANT NOTE: This phase is foundational. The system discovery script is mandatory and must be run first. All 77 containers must be validated before proceeding to dependency analysis. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 2. PHASE 2: REQUIREMENTS DISCOVERY & COMPLETION (PREREQUISITE)

**Explanations:**
This phase involves a deep analysis of all codebases to trace every dependency, identify missing or unused packages, and generate complete, accurate `requirements.txt` files for all 77 containers.

**Technical Artifacts / Tasks:**
**Agent Code Analysis:**
*   TARGET LOCATIONS: `./docker/*/`, `./main_pc_code/agents/*/`, `./pc2_code/agents/*/`, `./common/*/`, `./phase1_implementation/*/`
*   TASKS: Scan for imports, trace dependencies, identify missing/unused packages, generate dependency trees.

**Requirements File Validation:**
*   TARGET FILES: `./docker/*/requirements.txt`, `./requirements*.txt`, `./pc2_code/requirements*.txt`, `./main_pc_code/requirements*.txt`
*   TASKS: Check for existence, identify incomplete files, generate missing files, validate versioning, back up originals.

**Dynamic Dependency Detection:**
*   TARGET CONFIGS: `startup_config*.yaml`, `docker-compose.yml`, `config/*.yaml`, `env_config*.sh`
*   TASKS: Analyze runtime/conditional imports, identify optional/platform-specific dependencies.

**Cross-Agent Dependency Mapping:**
*   TARGET MODULES: `./common/*/`, `./common/core/base_agent.py`, etc.
*   TASKS: Map shared modules, document communication dependencies, create dependency graph, validate startup order.

**Automated Requirements Generation Tools:**
*   Use `pipreqs`, custom AST parsers, `pip-tools`, and `safety`.
*   Generate `requirements.common.txt` for shared dependencies.

**Requirements Validation & Testing:**
*   Test build each container with generated `requirements.txt`.
*   Validate runtime imports and check for missing system-level dependencies.
*   Ensure version compatibility and create an automated testing pipeline.

──────────────────────────────────
IMPORTANT NOTE: This phase is a critical prerequisite for build optimization. Accuracy is paramount. Every container must have a complete and validated `requirements.txt` file before moving on. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 3. PHASE 3: REQUIREMENTS OPTIMIZATION & BUILD ACCELERATION

**Explanations:**
With complete requirements, this phase focuses on optimizing them by deduplicating packages, creating efficient base images, and consolidating dependencies to significantly reduce build times and image sizes.

**Technical Artifacts / Tasks:**
**Duplicate Requirements Analysis:**
*   Scan all 77 `requirements.txt` files for duplicates and version conflicts.
*   Identify packages in 10+ containers and create a shared `requirements.common.txt`.

**Base Image Optimization:**
*   Create optimized base images with common dependencies pre-installed.
*   Group containers by requirement similarity (e.g., ML, API).
*   Implement multi-stage builds and cache common layers.

**Dependency Consolidation:**
*   Merge similar containers with 80%+ requirement overlap.
*   Create requirement profiles (minimal, standard, full).
*   Remove unused dependencies and standardize versions.

**Build Time Optimization:**
*   Implement Docker layer caching strategy.
*   Optimize requirement installation order.
*   Use `.dockerignore` to reduce build context and implement parallel builds.

──────────────────────────────────
IMPORTANT NOTE: The goal of this phase is a measurable reduction in build time and storage footprint. All changes must be benchmarked against the originals. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 4. PHASE 4: PERFORMANCE OPTIMIZATION (GPU, MEMORY & ALGORITHM)

**Explanations:**
This phase addresses critical performance bottlenecks, focusing on reducing GPU memory usage on PC2, fixing identified memory leaks, and optimizing inefficient algorithms.

**Technical Artifacts / Tasks:**
**GPU Memory Optimization (CRITICAL - PC2 near OOM):**
*   Implement int8 quantization for NLLB translation models.
*   Move TTS inference from GPU to CPU containers (saves 1.8GB VRAM).
*   Enable predictive model unloading in `vram_optimizer_agent`.
*   Add GPU memory monitoring with alerts at >90% usage.
*   Optimize model sharing between containers.

**Memory Leak Fixes:**
*   Fix `translation_service.py` missing `torch.cuda.empty_cache()` calls.
*   Implement context-managed tensor lifecycle.
*   Add periodic queue purging for `dream_world_agent` asyncio.Queue retention.
*   Review all model loading/unloading sequences for proper cleanup.
*   Add memory profiling for long-running containers.

**Algorithm Optimization:**
*   Replace O(N²) image comparison in `face_recognition_agent` with KD-tree.
*   Cache spaCy model loading in `learning_opportunity_detector`.
*   Fix N+1 database queries in `memory_orchestrator_service.py` with batch operations.
*   Convert synchronous I/O to async/await patterns.
*   Implement efficient data serialization (msgpack/orjson).

──────────────────────────────────
IMPORTANT NOTE: The primary success criterion for this phase is reducing PC2 GPU utilization to <85% during translation bursts. All fixes must be validated with profiling and monitoring. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 5. PHASE 5: INFRASTRUCTURE HARDENING & EFFICIENCY

**Explanations:**
This phase focuses on improving the overall stability and efficiency of the system by addressing code quality issues and optimizing runtime resource allocation and networking.

**Technical Artifacts / Tasks:**
**Code Quality Issues:**
*   Fix 4,117 bare exception handlers.
*   Resolve circular import dependencies.
*   Standardize port allocation (5556/5581 reused 50+ times).
*   Replace hard-coded credentials with environment variables.
*   Implement connection pooling for Redis and databases.
*   Add LRU caching for frequently accessed data.

**Runtime Optimization:**
*   **Container Resource Allocation:** Right-size containers, implement resource limits, use shared volumes.
*   **Optimize container startup order** for faster system boot.
*   **Network Optimization:** Implement ZMQ connection pooling, reduce overhead, optimize serialization, add latency monitoring.

──────────────────────────────────
IMPORTANT NOTE: This phase hardens the system for production. Changes should result in a more stable, secure, and efficient runtime environment, with faster startup times. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 6. PHASE 6: COMPREHENSIVE TEST SUITE & MONITORING CREATION

**Explanations:**
This phase involves creating the automated tests and monitoring infrastructure required to validate all previous optimizations and ensure the ongoing health and performance of the system.

**Technical Artifacts / Tasks:**
**Automated Testing:**
*   Generate automated test scripts for:
    *   Individual container health checks.
    *   Cross-machine ZMQ communication validation.
    *   GPU memory usage monitoring and alerting.
    *   Load testing for translation pipeline under high VRAM usage.
    *   Dependency chain validation during startup/shutdown.
    *   Performance regression testing for optimization implementations.
    *   Build time and resource usage benchmarking.

**Monitoring Infrastructure:**
*   Create monitoring dashboards for:
    *   Real-time GPU utilization (both RTX 4090 and RTX 3060).
    *   Memory usage patterns and leak detection.
    *   Inter-container communication latency.
    *   Error rate tracking across all 77 agents.
    *   Build times and resource consumption.
    *   Container startup sequence performance.

──────────────────────────────────
IMPORTANT NOTE: A robust test suite and comprehensive monitoring are non-negotiable for production readiness. These systems must be in place to validate the success of all prior phases. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 7. PHASE 7: FINAL VALIDATION & SIGN-OFF

**Explanations:**
This final phase is a checklist to verify that all success criteria have been met, all deliverables are complete, and all constraints have been respected.

**Technical Artifacts / Tasks:**
**Verify Success Criteria:**
*   All 77 containers build and start successfully.
*   PC2 GPU utilization reduced to <85% during translation bursts.
*   Memory leaks eliminated with stable long-running performance.
*   Zero startup failures due to dependency issues.
*   Comprehensive monitoring and alerting operational.
*   Build times reduced by 40%+.
*   Storage footprint reduced by 30%+.
*   Container startup time improved by 50%+.

**Verify Deliverables:**
*   Container Optimization Report produced.
*   Performance Optimization Implementation documented with benchmarks.
*   Production-Ready Infrastructure (test suite, dashboards) is complete.
*   Technical Debt Remediation plan is created and documented.

**Check Constraints:**
*   Backward compatibility with ZMQ protocols maintained.
*   All existing functionality preserved.
*   Startup dependencies respected.
*   Changes tested on both RTX 4090 and RTX 3060.

──────────────────────────────────
IMPORTANT NOTE: This is the final sign-off phase. Systematically verify each item on this checklist. The project is complete only when every success criterion is met and every deliverable is accounted for. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.