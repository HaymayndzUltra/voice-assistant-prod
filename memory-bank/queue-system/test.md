============================================================
🎮 TASK COMMAND & CONTROL CENTER
============================================================

📋 ALL OPEN TASKS:
========================================

1. 🗒️  20240524_dual_machine_optimization
   Description: A comprehensive plan to optimize, validate, and harden a dual-machine AI system ...
   Status: in_progress
   Created: 2024-05-24T12:00:00Z
   TODO Items (6):
      [✗] 0. PHASE 0: SETUP & PROTOCOL (READ FIRST)

**Explanations:**
This initial step contains the user manual for this task plan. It outlines the commands to interact with the plan and the critical safety workflow that must be followed for all subsequent phases.

**Technical Artifacts:**
**HOW TO USE THIS TASK PLAN (COMMANDS & PROTOCOL)**

**I. COMMANDS:**
1.  **TO VIEW DETAILS:** `python3 todo_manager.py show 20240524_dual_machine_optimization`
2.  **TO MARK AS DONE:** `python3 todo_manager.py done 20240524_dual_machine_optimization <step_number>`

**II. WORKFLOW & SAFETY PROTOCOL (CRUCIAL):**
1.  **FOCUS ON CURRENT STEP:** In each Phase, always read and understand the `IMPORTANT NOTE` first.
2.  **REVIEW-CONFIRM-PROCEED LOOP:** After completing a Phase, review your work and the next Phase. If your confidence score is below 90%, REPEAT the review.

──────────────────────────────────
IMPORTANT NOTE: This phase contains the operating manual for the entire plan. Understanding these protocols is mandatory before proceeding to Phase 1. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 1. PHASE 1: System Discovery & Dependency Analysis

**Explanations:**
This phase focuses on mapping the entire system, analyzing all 77 containers, and conducting a deep dive into code dependencies. The goal is to create a complete and accurate picture of the system's current state, which is a mandatory prerequisite for any optimization.

**Technical Artifacts / Tasks:**
**1. Mandatory System Discovery (RUN FIRST):**
*CRITICAL: Execute this before any other analysis! The background agent MUST start with system discovery to know exactly where all files are located!* 
```bash
# Run the system discovery script to map the complete file structure
python system_discovery_script.py

# This will generate:
# - system_discovery_report.json (complete system mapping)
# - analysis_paths.json (specific file paths for analysis)
```

**2. System Discovery & Container Analysis:**
*   **Complete File System Mapping:** Scan the primary locations:
    ```
    ./docker/                                    # 77 Docker containers
    ./main_pc_code/agents/                      # MainPC agent source code
    ./pc2_code/agents/                          # PC2 agent source code
    ./common/                                   # Shared utilities and base classes
    ./phase1_implementation/                    # Phase implementation code
    ./scripts/                                  # Build and utility scripts
    ./requirements*.txt                         # Root-level requirements
    ./docker-compose*.yml                       # System-level compose files
    ```
*   **Container Discovery and Analysis (`./docker/*/`):**
    *   Validate each of the 77 Dockerfiles builds successfully.
    *   Check `docker-compose.yml` files for proper configuration.
    *   Verify `requirements.txt` files have no conflicting dependencies.
    *   Test container startup sequences against `startup_config.yaml`.
    *   Document any containers that fail to build or start.
    *   Validate health check endpoints respond correctly.

**3. Requirements Discovery & Completion:**
*   **Agent Code Analysis:** Scan Python files in all target locations (`./docker/*/`, `./main_pc_code/agents/*/`, `./pc2_code/agents/*/`, `./common/*/`, `./phase1_implementation/*/`) to:
    *   Trace all direct and indirect import statements.
    *   Identify missing packages not listed in `requirements.txt`.
    *   Detect unused packages listed but not imported.
    *   Generate a complete dependency tree for each agent.
*   **Requirements File Validation:** Check all `requirements.txt` files across the project to:
    *   Identify containers with missing or incomplete files.
    *   Generate missing `requirements.txt` files using static analysis.
    *   Validate all imported packages are properly versioned.
    *   Create backups of original requirements files before modification.
*   **Dynamic & Cross-Agent Dependency Mapping:**
    *   Analyze configuration files (`startup_config*.yaml`, `docker-compose.yml`, `env_config*.sh`) for runtime imports and platform-specific requirements.
    *   Map shared internal modules from `./common/*/` between agents.
    *   Create a dependency graph showing inter-agent relationships and validate startup order.

**4. Tooling for Automated Requirements Generation:**
*   Utilize `pipreqs` for basic requirements generation.
*   Implement a custom AST parser for complex import patterns.
*   Use `pip-tools` for dependency resolution and version pinning.
*   Employ `safety` for security vulnerability scanning.

**5. Requirements Validation & Testing:**
*   Test-build each container with its generated `requirements.txt`.
*   Validate all imports work correctly at runtime.
*   Check for missing system-level dependencies (e.g., apt packages).
*   Ensure version compatibility across the ecosystem.

──────────────────────────────────
IMPORTANT NOTE: This discovery phase is the foundation for the entire project. Inaccuracies or incomplete analysis here will lead to failures in subsequent optimization and implementation phases. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 2. PHASE 2: Optimization Strategy & Remediation Planning

**Explanations:**
Based on the findings from Phase 1, this phase involves creating a detailed strategy for all optimization and remediation tasks. This includes planning for build time reduction, performance enhancements, and infrastructure hardening. The output of this phase is a clear, prioritized action plan.

**Technical Artifacts / Tasks:**
**1. Formulate Requirements Optimization Strategy:**
*   **Duplicate Analysis:** Analyze all 77 `requirements.txt` files to find duplicate packages and version conflicts. Plan a `requirements.common.txt` for packages appearing in 10+ containers.
*   **Base Image Optimization:** Design optimized base images with common dependencies pre-installed. Group containers by requirement similarity (e.g., ML, API) and plan for multi-stage builds.
*   **Dependency Consolidation:** Identify containers with 80%+ requirement overlap for potential merging. Define requirement profiles (minimal, standard, full) and plan the removal of unused dependencies.
*   **Build Time Optimization:** Develop a strategy for Docker layer caching, optimized requirement installation order, and using `.dockerignore` to reduce build context.

**2. Plan Performance Optimization Implementation:**
*   **GPU Memory (PC2):** Plan the implementation of int8 quantization for NLLB models, moving TTS to CPU, and enabling predictive model unloading.
*   **Memory Leaks:** Outline the steps to fix missing `torch.cuda.empty_cache()` calls, implement context-managed tensor lifecycles, and add periodic queue purging.
*   **Algorithm Optimization:** Plan the replacement of O(N²) image comparison, caching of spaCy models, fixing N+1 DB queries, and converting sync I/O to async.

**3. Plan Infrastructure Hardening & Efficiency Improvements:**
*   **Code Quality:** Create a task list to fix bare exceptions, resolve circular imports, standardize port allocation, replace hard-coded credentials, and implement connection pooling.
*   **Runtime Optimization:** Plan the right-sizing of container resources, implementation of ZMQ connection pooling, and optimization of message serialization.

**4. Review and Prioritize:**
*   Formalize the action plan according to the specified priorities:
    1.  **CRITICAL:** GPU memory optimization for PC2.
    2.  **HIGH:** Requirements deduplication and build optimization.
    3.  **HIGH:** Memory leak fixes and monitoring.
    4.  **MEDIUM:** Algorithm and runtime optimizations.
    5.  **MEDIUM:** Infrastructure hardening and monitoring.
    6.  **LOW:** Documentation and maintenance procedures.

──────────────────────────────────
IMPORTANT NOTE: A clear and well-defined strategy is crucial for success. Rushing into implementation without a solid plan will result in wasted effort and potential system instability. Ensure all stakeholders agree on the priorities and planned actions. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 3. PHASE 3: Code & Infrastructure Implementation

**Explanations:**
This is the execution phase where the strategies defined in Phase 2 are implemented. It involves hands-on coding to optimize algorithms, fix memory leaks, improve code quality, and harden the system's infrastructure.

**Technical Artifacts / Tasks:**
**1. Implement GPU Memory Optimizations (CRITICAL - PC2):**
*   Implement int8 quantization for NLLB translation models.
*   Move TTS inference from GPU to CPU containers to save ~1.8GB VRAM.
*   Enable predictive model unloading in `vram_optimizer_agent`.
*   Add GPU memory monitoring with alerts for usage >90%.
*   Optimize model sharing between containers to reduce memory duplication.

**2. Implement Memory Leak Fixes:**
*   Fix `translation_service.py` by adding missing `torch.cuda.empty_cache()` calls.
*   Implement context-managed tensor lifecycles for all GPU tensors.
*   Add periodic queue purging for the `dream_world_agent`'s `asyncio.Queue` retention issue.
*   Review and fix all model loading/unloading sequences for proper cleanup.
*   Add memory profiling for long-running containers.

**3. Implement Algorithm Optimizations:**
*   Replace O(N²) image comparison in `face_recognition_agent` with a KD-tree implementation.
*   Cache spaCy model loading in `learning_opportunity_detector` at the module level.
*   Fix N+1 database queries in `memory_orchestrator_service.py` with batch operations.
*   Convert synchronous I/O operations to async/await patterns where applicable.
*   Implement efficient data serialization (e.g., msgpack or orjson) instead of standard JSON.

**4. Implement Infrastructure Hardening & Efficiency:**
*   **Code Quality:**
    *   Refactor the 4,117 identified bare `except:` handlers to be specific.
    *   Resolve circular import dependencies between core modules.
    *   Standardize port allocation to fix conflicts (e.g., 5556/5581).
    *   Replace hard-coded credentials with environment variables.
    *   Implement connection pooling for Redis and database connections.
    *   Add LRU caching for frequently accessed data.
*   **Runtime Optimization:**
    *   Right-size container resource limits and requests based on profiling data.
    *   Use shared volumes for common data like models and configs.
    *   Implement ZMQ connection pooling and optimize message serialization.

──────────────────────────────────
IMPORTANT NOTE: This phase involves significant changes to the codebase and infrastructure. Work on a dedicated feature branch and commit changes incrementally. Thoroughly unit-test each change before moving to the next. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 4. PHASE 4: Test Suite & Monitoring Infrastructure Development

**Explanations:**
To validate the optimizations from Phase 3 and ensure long-term stability, this phase focuses on creating a comprehensive, automated test suite and robust monitoring infrastructure.

**Technical Artifacts / Tasks:**
**1. Generate Automated Test Scripts:**
*   Create scripts for individual container health checks.
*   Develop tests for cross-machine ZMQ communication validation.
*   Implement tests for GPU memory usage monitoring and alerting.
*   Build a load test for the translation pipeline to validate performance under high VRAM usage on PC2.
*   Create a test to validate the dependency chain during system startup and shutdown.
*   Establish performance regression tests for all optimization implementations.
*   Develop benchmarks for build time and resource usage to track improvements.

**2. Create Monitoring Infrastructure:**
*   Set up monitoring dashboards to provide real-time visibility into:
    *   GPU utilization on both RTX 4090 (MainPC) and RTX 3060 (PC2).
    *   Memory usage patterns and leak detection metrics.
    *   Inter-container communication latency.
    *   Error rate tracking across all 77 agents.
    *   Build times and resource consumption over time.
    *   Container startup sequence performance.

──────────────────────────────────
IMPORTANT NOTE: A system is only as reliable as its tests and monitoring. Ensure the test suite has high coverage of critical paths and that the monitoring dashboards provide actionable insights, not just data. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
      [✗] 5. PHASE 5: Validation, Reporting, and Final Review

**Explanations:**
This final phase involves validating the entire effort against the defined success criteria, generating all required reports and deliverables, and preparing the system for production deployment.

**Technical Artifacts / Tasks:**
**1. Final Validation Against Success Criteria:**
*   Confirm all 77 containers build and start successfully.
*   Verify PC2 GPU utilization is reduced to <85% during translation bursts.
*   Confirm memory leaks are eliminated via stable long-running performance tests.
*   Ensure zero startup failures due to dependency issues.
*   Validate that comprehensive monitoring and alerting are fully operational.
*   Measure and confirm build times are reduced by 40%+.
*   Measure and confirm storage footprint is reduced by 30%+.
*   Measure and confirm container startup time is improved by 50%+.

**2. Generate Specific Deliverables:**
*   **Container Optimization Report:**
    *   Final container validation report (build/startup status for all 77 agents).
    *   Complete dependency mapping and missing requirements report.
    *   Requirements deduplication analysis and base image optimization strategy with final size reduction metrics.
    *   Build time optimization report with before/after comparisons.
*   **Performance Optimization Report:**
    *   GPU memory optimization results (PC2 usage <85% target).
    *   Memory leak fix validation with monitoring data.
    *   Algorithm optimization performance benchmarks.
*   **Production-Ready Infrastructure Documentation:**
    *   Documentation for the automated test suite.
    *   Configuration files and guides for the monitoring dashboards.
*   **Technical Debt Remediation Plan:**
    *   Finalized technical debt remediation plan with a priority matrix.
    *   Updated architectural documentation.
    *   A best practices guide for future container development.
    *   Maintenance procedures for ongoing optimization.

──────────────────────────────────
IMPORTANT NOTE: This is the final acceptance phase. All deliverables must be complete and all success criteria must be met before the project is considered finished. A final peer review of the code, documentation, and reports is mandatory. Do not proceed until the current step is complete. Before moving forward, review the completed step and the next one. Repeat the review if your confidence score is below 90%.
