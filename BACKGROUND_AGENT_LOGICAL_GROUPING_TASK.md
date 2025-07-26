# Background Agent Task - Logical Agent Grouping Analysis

**BACKGROUND AGENT PROMPT FOR COMPREHENSIVE LOGICAL GROUPING ANALYSIS:**

```
/agent
COMPREHENSIVE LOGICAL AGENT GROUPING ANALYSIS FOR CROSS-MACHINE DOCKER DEPLOYMENT:

SYSTEM ARCHITECTURE ANALYSIS:
- **MainPC (RTX 4090)**: 54 agents from main_pc_code/config/startup_config.yaml  
- **PC2 (RTX 3060)**: 23 agents from pc2_code/config/startup_config.yaml
- **Goal**: Optimal Docker container grouping for cross-machine deployment

DEEP CODEBASE ANALYSIS REQUIRED:

1. DEPENDENCY GRAPH ANALYSIS:
   - Parse all agent dependencies from startup_config.yaml files
   - Analyze actual Python imports and function calls across all 77 agent files
   - Map inter-agent communication patterns (ZMQ, HTTP, Redis)
   - Identify tight coupling vs loose coupling between agents
   - Detect circular dependencies that could cause container startup issues

2. RESOURCE USAGE PATTERN ANALYSIS:
   - Scan all agent files for GPU usage patterns (CUDA, torch operations)
   - Identify CPU-intensive vs I/O-intensive vs memory-intensive agents
   - Analyze shared resource usage (Redis, databases, file systems)
   - Map agents that share models or large memory objects
   - Categorize by resource requirements: HIGH_GPU, MEDIUM_GPU, CPU_ONLY, I/O_BOUND

3. COMMUNICATION TOPOLOGY MAPPING:
   - Extract all ZMQ socket binding patterns from agent code
   - Map HTTP endpoint dependencies between agents
   - Identify agents that must be co-located for performance
   - Find agents that can be distributed across machines safely
   - Detect cross-machine communication requirements

4. HARDWARE OPTIMIZATION ANALYSIS:
   - RTX 4090 (MainPC): Identify agents requiring 24GB VRAM or high compute
   - RTX 3060 (PC2): Identify agents suitable for 12GB VRAM or lighter compute
   - Analyze CPU usage patterns for optimal distribution
   - Consider memory requirements and shared resource access

5. DOCKER CONTAINER GROUPING STRATEGY:
   - Group agents by resource similarity and communication patterns
   - Consider container restart impact (critical vs non-critical services)
   - Optimize for minimal cross-container network latency
   - Plan for container scaling and resource limits
   - Design for failure isolation (don't put all critical services in one container)

AUTOMATED DELIVERABLES:

A. GENERATE OPTIMAL CONTAINER GROUPS:
   ```yaml
   # MainPC Container Groups (RTX 4090)
   mainpc_core_services:
     agents: [ServiceRegistry, SystemDigitalTwin, RequestCoordinator]
     resources: { cpu: 2, memory: 4GB, gpu: false }
   
   mainpc_gpu_intensive:
     agents: [ModelManagerSuite, ChainOfThoughtAgent, VRAMOptimizerAgent]
     resources: { cpu: 4, memory: 8GB, gpu: true, vram: 16GB }
   
   # PC2 Container Groups (RTX 3060)  
   pc2_memory_processing:
     agents: [MemoryOrchestratorService, CacheManager, ContextManager]
     resources: { cpu: 2, memory: 6GB, gpu: false }
   ```

B. CROSS-MACHINE COMMUNICATION MAP:
   - List agents requiring cross-machine coordination
   - Define network topology and port allocation
   - Plan service discovery and health check strategy

C. DEPLOYMENT DEPENDENCY ORDER:
   - Container startup sequence across both machines
   - Health check dependencies and readiness probes
   - Rollback strategy if deployment fails

D. RESOURCE ALLOCATION OPTIMIZATION:
   - Memory limits per container group
   - GPU allocation strategy (4090 vs 3060)
   - CPU pinning recommendations
   - Storage volume planning

SUCCESS CRITERIA:
- All 77 agents grouped into logical Docker containers
- Optimal resource utilization for RTX 4090 + RTX 3060 setup
- Minimal cross-container network overhead
- Clear separation of concerns and failure isolation
- Production-ready docker-compose files for both machines

ANALYSIS SCOPE:
- Read all agent Python files in main_pc_code/agents/ and pc2_code/agents/
- Parse startup_config.yaml dependencies completely
- Analyze common/ shared modules usage patterns
- Consider Docker networking and volume requirements
- Account for cross-machine Redis, ZMQ, and HTTP communication

Generate comprehensive report with container grouping recommendations, resource allocation matrix, deployment order, and docker-compose.yml templates optimized for dual-machine RTX setup.
```

---

**READY TO EXECUTE BACKGROUND AGENT ANALYSIS**

This prompt will leverage the background agent's deep codebase analysis to:

✅ **Automatically analyze all 77 agent files** for dependencies and resource usage  
✅ **Map actual communication patterns** from the code (not just config)  
✅ **Optimize for hardware setup** (RTX 4090 vs RTX 3060)  
✅ **Generate production-ready Docker configs** with proper groupings  
✅ **Consider cross-machine networking** and failure scenarios  

Gusto mo ba i-execute na ito? O may additional requirements ka pa for the analysis? 