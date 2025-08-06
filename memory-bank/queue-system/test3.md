COMPREHENSIVE DUAL-MACHINE AI SYSTEM OPTIMIZATION & VALIDATION

Claude, execute a comprehensive optimization and validation audit of this dual-machine AI system with the following critical requirements:

SYSTEM CONTEXT:

77 total containerized agents (54 MainPC + 23 PC2)

MainPC: RTX 4090 with power GPU processing

PC2: RTX 3060 (12GB VRAM) hitting performance limits

Recent migration to individual containers per agent

Cross-machine ZMQ communication architecture

Critical performance bottlenecks and technical debt identified

PHASE 1 - CONTAINER VALIDATION & BUILD OPTIMIZATION:
1.0 MANDATORY SYSTEM DISCOVERY (RUN FIRST):

CRITICAL: Execute this before any other analysis!

code
Bash
download
content_copy
expand_less

# Run the system discovery script to map the complete file structure

python system_discovery_script.py

# This will generate:

# - system_discovery_report.json (complete system mapping)

# - analysis_paths.json (specific file paths for analysis)

The background agent MUST start with system discovery to know exactly where all files are located!

1.1 SYSTEM DISCOVERY & CONTAINER ANALYSIS:

Complete File System Mapping:

code
Bash
download
content_copy
expand_less
IGNORE_WHEN_COPYING_START
IGNORE_WHEN_COPYING_END

# Primary locations to scan:

./docker/ # 77 Docker containers
./main_pc_code/agents/ # MainPC agent source code
./pc2_code/agents/ # PC2 agent source code
./common/ # Shared utilities and base classes
./phase1_implementation/ # Phase implementation code
./scripts/ # Build and utility scripts
./requirements*.txt # Root-level requirements
./docker-compose*.yml # System-level compose files

Container Discovery and Analysis:

Docker Container Locations: ./docker/\*/

Expected Files per Container:

./docker/\*/Dockerfile

./docker/\*/docker-compose.yml

./docker/\*/requirements.txt

./docker/_/requirements_.txt (variations)

Analysis Tasks:

Analyze all 77 Docker containers in ./docker/ directory

Validate each Dockerfile builds successfully without errors

Check docker-compose.yml files for proper configuration

Verify requirements.txt files have no conflicting dependencies

Test container startup sequences following startup_config.yaml dependencies

Document any containers that fail to build or start

Validate health check endpoints respond correctly across both machines

1.2 REQUIREMENTS DISCOVERY & COMPLETION (PREREQUISITE):

Agent Code Analysis:

TARGET LOCATIONS:

Docker containers: ./docker/\*/ (77 containers)

MainPC agents: ./main_pc_code/agents/\*/

PC2 agents: ./pc2_code/agents/\*/

Common utilities: ./common/\*/

Phase implementations: ./phase1_implementation/\*/

ANALYSIS TASKS:

Scan each agent's Python files for import statements

Trace all dependencies including indirect imports

Identify missing packages not listed in requirements.txt

Detect unused packages listed but not imported

Generate complete dependency tree for each agent

Requirements File Validation:

TARGET FILES:

Docker requirements: ./docker/\*/requirements.txt

Root requirements: ./requirements\*.txt

PC2 requirements: ./pc2_code/requirements\*.txt

MainPC requirements: ./main_pc_code/requirements\*.txt

VALIDATION TASKS:

Check all 77 containers for existing requirements.txt files

Identify containers with missing or incomplete requirements.txt

Generate missing requirements.txt files using static analysis

Validate that all imported packages are properly versioned

Create backup of original requirements before modification

Dynamic Dependency Detection:

TARGET CONFIGURATION FILES:

Startup configs: ./main_pc_code/config/startup_config\*.yaml

PC2 configs: ./pc2_code/config/startup_config\*.yaml

Docker compose: ./docker/\*/docker-compose.yml

Environment configs: ./config/_.yaml, ./env_config_.sh

DETECTION TASKS:

Analyze runtime imports (importlib, import, etc.)

Detect conditional imports based on environment/config

Identify optional dependencies that may be missing

Check for platform-specific requirements (Linux/Windows)

Trace dependencies through configuration files

Cross-Agent Dependency Mapping:

TARGET SHARED MODULES:

Common utilities: ./common/\*/ (all subdirectories)

Base agent classes: ./common/core/base_agent.py

Path managers: ./common/utils/path_manager.py

Config managers: ./common/config_manager.py

Error handling: ./common/utils/error_publisher.py

DEPENDENCY SOURCES:

Startup configs: ./main_pc_code/config/startup_config\*.yaml

PC2 configs: ./pc2_code/config/startup_config\*.yaml

Import statements in all agent Python files

MAPPING TASKS:

Map shared internal modules between agents

Identify common utility imports across agents

Document agent-to-agent communication dependencies

Create dependency graph showing inter-agent relationships

Validate startup order based on actual dependencies

Automated Requirements Generation Tools:

Use pipreqs for basic requirements generation from imports

Implement custom AST parser for complex import patterns

Use pip-tools for dependency resolution and version pinning

Employ safety for security vulnerability scanning

Create requirements.txt templates for different agent types

Generate requirements.common.txt for shared dependencies

Requirements Validation & Testing:

Test build each container with generated requirements.txt

Validate that all imports work correctly at runtime

Check for missing system-level dependencies (apt packages, etc.)

Ensure version compatibility across the entire ecosystem

Document any manual adjustments needed for complex agents

Create automated requirements testing pipeline

1.3 REQUIREMENTS OPTIMIZATION (CRITICAL - BUILD TIME REDUCTION):

Duplicate Requirements Analysis:

Scan all 77 requirements.txt files for duplicate packages

Identify version conflicts across containers

Find packages that appear in 10+ containers

Create shared requirements.common.txt for frequently used packages

Base Image Optimization:

Create optimized base images with common dependencies pre-installed

Group containers by requirement similarity (e.g., ML containers, API containers)

Implement multi-stage builds to reduce image sizes

Cache common layers to speed up builds

Dependency Consolidation:

Merge similar containers that have 80%+ requirement overlap

Create requirement profiles (minimal, standard, full)

Remove unused dependencies from each container

Standardize package versions across the system

Build Time Optimization:

Implement Docker layer caching strategy

Create requirement installation order optimization

Use .dockerignore to reduce build context

Parallel build strategy for independent containers

PHASE 2 - PERFORMANCE OPTIMIZATION IMPLEMENTATION:
2.1 GPU MEMORY OPTIMIZATION (CRITICAL - PC2 near OOM):

Implement int8 quantization for NLLB translation models

Move TTS inference from GPU to CPU containers (saves 1.8GB VRAM)

Enable predictive model unloading in vram_optimizer_agent

Add GPU memory monitoring with alerts at >90% usage

Optimize model sharing between containers to reduce memory duplication

2.2 MEMORY LEAK FIXES:

Fix translation_service.py missing torch.cuda.empty_cache() calls

Implement context-managed tensor lifecycle

Add periodic queue purging for dream_world_agent asyncio.Queue retention

Review all model loading/unloading sequences for proper cleanup

Add memory profiling for long-running containers

2.3 ALGORITHM OPTIMIZATION:

Replace O(N²) image comparison in face_recognition_agent with KD-tree

Cache spaCy model loading in learning_opportunity_detector at module level

Fix N+1 database queries in memory_orchestrator_service.py with batch operations

Convert synchronous I/O operations to async/await patterns

Implement efficient data serialization (msgpack/orjson vs JSON)

PHASE 3 - INFRASTRUCTURE HARDENING & EFFICIENCY:
3.1 Code Quality Issues:

Fix 4,117 bare exception handlers that mask critical errors

Resolve circular import dependencies between core modules

Standardize port allocation to prevent conflicts (5556/5581 reused 50+ times)

Replace hard-coded credentials with environment variables

Implement connection pooling for Redis and database connections

Add LRU caching for frequently accessed data

3.2 Runtime Optimization:

Container Resource Allocation:

Right-size containers based on actual usage patterns

Implement resource limits and requests

Use shared volumes for common data (models, configs)

Optimize container startup order for faster system boot

Network Optimization:

Implement ZMQ connection pooling

Reduce cross-container communication overhead

Optimize message serialization formats

Add network latency monitoring

PHASE 4 - COMPREHENSIVE TEST SUITE CREATION:
4.1 Automated Testing:

Generate automated test scripts for:

Individual container health checks

Cross-machine ZMQ communication validation

GPU memory usage monitoring and alerting

Load testing for translation pipeline under high VRAM usage

Dependency chain validation during startup/shutdown

Performance regression testing for optimization implementations

Build time and resource usage benchmarking

4.2 Monitoring Infrastructure:

Create monitoring dashboards for:

Real-time GPU utilization (both RTX 4090 and RTX 3060)

Memory usage patterns and leak detection

Inter-container communication latency

Error rate tracking across all 77 agents

Build times and resource consumption

Container startup sequence performance

SPECIFIC DELIVERABLES REQUIRED:

1. Container Optimization Report:

Complete container validation report with build/startup status for all 77 agents

Requirements Discovery Analysis: Complete dependency mapping for all 77 agents

Missing Requirements Report: Generated requirements.txt for incomplete containers

Requirements deduplication analysis with shared dependency recommendations

Base image optimization strategy with size reduction metrics

Build time optimization implementation with before/after comparisons

2. Performance Optimization Implementation:

GPU memory optimization with PC2 usage <85% target

Memory leak fixes with monitoring and alerting

Algorithm optimizations with performance benchmarks

Runtime efficiency improvements with resource utilization metrics

3. Production-Ready Infrastructure:

Automated test suite covering all critical system functions

Monitoring dashboard configuration for production deployment

Resource optimization recommendations for cost reduction

Scalability analysis for future growth

4. Technical Debt Remediation:

Technical debt remediation plan with priority matrix

Updated documentation reflecting optimized architecture

Best practices guide for future container development

Maintenance procedures for ongoing optimization

TECHNICAL CONSTRAINTS:

Maintain backward compatibility with existing ZMQ communication protocols

Preserve all existing functionality while optimizing performance

Ensure startup dependencies are respected during container orchestration

Test all changes on both RTX 4090 (MainPC) and RTX 3060 (PC2) configurations

Minimize storage footprint while maintaining functionality

SUCCESS CRITERIA:

All 77 containers build and start successfully

PC2 GPU utilization reduced to <85% during translation bursts

Memory leaks eliminated with stable long-running performance

Zero startup failures due to dependency issues

Comprehensive monitoring and alerting operational

Build times reduced by 40%+ through optimization

Storage footprint reduced by 30%+ through deduplication

Container startup time improved by 50%+

OPTIMIZATION PRIORITIES:

PREREQUISITE: Requirements discovery and completion for all 77 agents

CRITICAL: GPU memory optimization for PC2

HIGH: Requirements deduplication and build optimization

HIGH: Memory leak fixes and monitoring

MEDIUM: Algorithm and runtime optimizations

MEDIUM: Infrastructure hardening and monitoring

LOW: Documentation and maintenance procedures

Use all your available tools and capabilities. Analyze the existing codebase thoroughly, implement optimizations systematically, and provide production-ready solutions with proper testing and validation.
