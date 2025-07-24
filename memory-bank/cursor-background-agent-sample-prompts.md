# Cursor Background Agent Sample Prompts - AI System Monorepo

**System Architecture**: Dual-machine setup sa iisang repository
- **MainPC (RTX 4090)**: 54 agents - GPU inference, model management, heavy processing
- **PC2 (RTX 3060)**: 23 agents - Task processing, memory orchestration, light GPU work
- **Total**: 77 agents across two machines in single repository

Based sa real codebase issues ng AI System Monorepo, here are enhanced sample prompts:

## 🔥 **SAMPLE 1: MASSIVE CODEBASE CLEANUP (PROJECT-WIDE)**

### **Basic Prompt:**
```
/agent
Clean up the duplicate .bak files in main_pc_code/agents/ folder and standardize the codebase.
```

### **🚀 ENHANCED PROMPT:**
```
/agent
Execute comprehensive codebase cleanup for AI System Monorepo (77 agents across MainPC RTX 4090 + PC2 RTX 3060):

1. DUPLICATE FILE CLEANUP:
   - Scan main_pc_code/agents/ for .bak, .backup, .bak.bak.bak files
   - Delete ALL backup files (keep only the main versions)
   - Remove files with excessive .bak extensions (e.g., chitchat_agent.py.bak.bak.bak.bak.bak)
   - Generate deletion report with file sizes recovered

2. IMPORT STANDARDIZATION:
   - Fix all BaseAgent imports to use "from common.core.base_agent import BaseAgent"
   - Update any remaining circular import issues
   - Standardize ZMQ imports across all agent files

3. SYNTAX VALIDATION:
   - Run syntax check on all Python files in main_pc_code/ and pc2_code/
   - Fix any indentation errors, extra parentheses, or missing imports
   - Validate all agent files can be imported without errors

4. PORT CONFLICT RESOLUTION:
   - Scan startup_config.yaml files for duplicate port assignments
   - Generate new port allocation matrix avoiding conflicts between machines
   - Update hardcoded ports in agent files to match config

SUCCESS CRITERIA: All 77 agents import cleanly, no backup files remain, all ports unique across both machines, 100% syntax valid.
Run full test suite and commit changes with message "Major codebase cleanup: removed duplicates, fixed syntax, standardized imports"
```

## 🐛 **SAMPLE 2: DEPLOYMENT BLOCKER RESOLUTION (CRITICAL DEBUG)**

### **Basic Prompt:**
```
/agent
Fix the Docker container startup issues where agents crash immediately.
```

### **🚀 ENHANCED PROMPT:**
```
/agent
DEBUG AND FIX CRITICAL DOCKER DEPLOYMENT BLOCKERS (Dual-machine: MainPC RTX 4090 + PC2 RTX 3060):

ROOT CAUSE ANALYSIS:
1. CONTAINER STARTUP INVESTIGATION:
   - Analyze docker-compose.mainpc.yml startup commands (54 agents)
   - Analyze docker-compose.pc2.yml startup commands (23 agents)
   - Check all Dockerfile CMD entries for correct Python module paths
   - Trace startup_config.yaml loading mechanism in start_system.py
   - Identify why "No module named main_pc_code.startup" error occurs

2. DEPENDENCY CHAIN VALIDATION:
   - Verify all agent script_path entries point to existing files
   - Check for missing Python dependencies causing import failures
   - Validate ZMQ socket binding in container environment (0.0.0.0 vs localhost)
   - Test Redis and NATS connectivity between containers across machines

3. CONFIGURATION SYNCHRONIZATION:
   - Ensure environment variables are properly passed to containers
   - Fix any hardcoded localhost references that break container networking
   - Validate port mappings between docker-compose and startup_config.yaml
   - Check volume mount permissions and file accessibility on both machines

AUTOMATED FIXES:
- Update all localhost bindings to 0.0.0.0 for container compatibility
- Fix Docker CMD entries to use correct Python module syntax
- Add missing environment variables to docker-compose files
- Create startup validation script that runs before agent initialization
- Configure GPU access for RTX 4090 (MainPC) and RTX 3060 (PC2) containers

TEST PROTOCOL:
- Build all containers and verify no build failures on both machines
- Start containers individually and capture startup logs
- Test inter-container communication via ZMQ between machines
- Validate health check endpoints respond correctly across dual setup

DELIVERABLE: Working Docker deployment with all 77 agents (54 MainPC + 23 PC2) starting successfully, health checks green, commit with "CRITICAL: Fixed Docker deployment blockers - all containers operational on dual-machine setup"
```

## ⚡ **SAMPLE 3: PERFORMANCE OPTIMIZATION (SYSTEM-WIDE)**

### **Basic Prompt:**
```
/agent
Optimize the performance of the AI System Monorepo.
```

### **🚀 ENHANCED PROMPT:**
```
/agent
COMPREHENSIVE PERFORMANCE OPTIMIZATION - AI SYSTEM MONOREPO (Dual RTX Setup):

PERFORMANCE AUDIT SCOPE:
1. MEMORY LEAK DETECTION:
   - Scan ModelManagerAgent (229KB, 4821 lines) for memory management issues on RTX 4090
   - Check VRAMOptimizerAgent for GPU memory leaks across both RTX cards
   - Analyze all 77 agent startup/shutdown sequences for resource cleanup
   - Identify unclosed ZMQ sockets, file handles, database connections

2. CPU OPTIMIZATION ANALYSIS:
   - Profile model loading operations in ModelManagerAgent (RTX 4090 heavy processing)
   - Find synchronous file I/O that should be async (streaming agents)
   - Identify inefficient loops in StreamingAudioCapture (49KB)
   - Locate CPU-intensive operations that could be vectorized
   - Optimize load balancing between RTX 4090 and RTX 3060

3. NETWORK & I/O BOTTLENECKS:
   - Analyze ZMQ socket patterns for blocking operations between machines
   - Check Redis connection pooling in memory management
   - Review file system operations for unnecessary disk access
   - Optimize JSON serialization in high-frequency cross-machine communication

AUTOMATED OPTIMIZATIONS:
- Implement connection pooling for Redis, databases
- Add LRU caching for frequently accessed data
- Convert blocking I/O to async/await patterns
- Optimize model loading with lazy initialization
- Add memory usage monitoring and automatic cleanup
- Configure optimal GPU utilization (RTX 4090 for heavy models, RTX 3060 for lighter tasks)

PERFORMANCE TESTING:
- Create benchmark suite for critical agent operations
- Measure memory usage before/after optimizations on both machines
- Test system performance under load (multiple agents across GPUs)
- Generate performance report with metrics improvement

TARGET METRICS:
- Reduce memory usage by 30% across both machines
- Improve startup time by 50% 
- Eliminate memory leaks (stable memory usage over 24 hours)
- Achieve <100ms response time for critical operations
- Optimize GPU utilization: RTX 4090 >80%, RTX 3060 >70%

DELIVERABLE: Optimized codebase with performance benchmarks, memory leak fixes, async I/O implementation, GPU optimization, commit "PERFORMANCE: Major optimization - 30% memory reduction, 50% faster startup, optimized dual-GPU setup"
```

## 🔒 **SAMPLE 4: SECURITY HARDENING (ENTERPRISE-GRADE)**

### **Basic Prompt:**
```
/agent
Improve security in the codebase.
```

### **🚀 ENHANCED PROMPT:**
```
/agent
ENTERPRISE SECURITY HARDENING - COMPREHENSIVE SECURITY AUDIT (Dual-Machine Setup):

SECURITY VULNERABILITY SCAN:
1. SECRET DETECTION & REMOVAL:
   - Scan entire codebase for hardcoded API keys, passwords, tokens
   - Check for committed certificates, private keys, .env files
   - Identify hardcoded database credentials or ZMQ CURVE keys
   - Search for TODO comments containing sensitive information
   - Secure cross-machine communication between RTX 4090 and RTX 3060 systems

2. AUTHENTICATION & AUTHORIZATION:
   - Audit ZMQ socket security configurations across machines
   - Review agent-to-agent communication security (77 agents total)
   - Check for unprotected admin endpoints
   - Validate input sanitization across all agents
   - Implement secure inter-machine authentication

3. CONTAINER SECURITY:
   - Ensure all Dockerfiles use non-root users
   - Scan for privileged container configurations
   - Check volume mount security and permissions
   - Validate network isolation between services
   - Secure GPU access for both RTX cards

AUTOMATED SECURITY FIXES:
- Move all secrets to environment variables
- Implement proper ZMQ CURVE authentication
- Add input validation decorators to all agent endpoints
- Configure secure container runtime (non-root, read-only filesystems)
- Enable Docker secrets management for sensitive data
- Implement encrypted communication between MainPC and PC2

SECURITY MONITORING:
- Add security headers to all HTTP endpoints
- Implement audit logging for sensitive operations
- Create security metrics dashboard
- Set up automated vulnerability scanning in CI/CD
- Monitor cross-machine communication for anomalies

COMPLIANCE VALIDATION:
- Generate security compliance report
- Document all security measures implemented
- Create security incident response procedures
- Validate against OWASP Top 10 security practices

DELIVERABLE: Enterprise-grade security implementation with zero secrets in code, encrypted communications, security monitoring, compliance documentation, dual-machine security protocols, commit "SECURITY: Enterprise hardening - encrypted comms, zero secrets, OWASP compliant, dual-machine secured"
```

## 📊 **SAMPLE 5: AUTOMATED DOCUMENTATION (KNOWLEDGE CAPTURE)**

### **Basic Prompt:**
```
/agent
Create documentation for the agents.
```

### **🚀 ENHANCED PROMPT:**
```
/agent
COMPREHENSIVE AUTOMATED DOCUMENTATION GENERATION (Dual-Machine Architecture):

ARCHITECTURE DOCUMENTATION:
1. SYSTEM ARCHITECTURE MAPPING:
   - Generate complete system dependency graph from startup_config.yaml
   - Create agent interaction diagrams (77 agents total)
   - Document data flow between MainPC RTX 4090 (54 agents) and PC2 RTX 3060 (23 agents)
   - Map port allocation matrix and service discovery patterns across dual-machine setup
   - Document GPU workload distribution and resource allocation

2. API DOCUMENTATION GENERATION:
   - Extract all agent endpoints and create OpenAPI specifications
   - Document ZMQ message schemas and communication patterns
   - Generate client SDK documentation for each service
   - Create integration examples and usage patterns
   - Document cross-machine communication protocols

3. CONFIGURATION DOCUMENTATION:
   - Document all environment variables and configuration options
   - Create deployment guides for Docker and bare metal (dual-machine)
   - Generate troubleshooting guides for common issues
   - Document monitoring and health check procedures
   - Create GPU-specific configuration guides (RTX 4090 vs RTX 3060)

CODE DOCUMENTATION ENHANCEMENT:
- Add comprehensive docstrings to all classes and methods
- Generate type hints for all function parameters and returns
- Create inline documentation for complex algorithms
- Add usage examples for public APIs
- Document GPU utilization patterns and best practices

AUTOMATED DELIVERABLES:
- Generate README.md files for each major component
- Create API reference documentation (Sphinx/MkDocs)
- Generate architecture diagrams (Mermaid/PlantUML)
- Create deployment runbooks and operational guides
- Document dual-machine setup and maintenance procedures

KNOWLEDGE CAPTURE:
- Extract business logic documentation from code
- Create developer onboarding guides
- Document design decisions and architectural choices
- Generate troubleshooting playbooks from error patterns
- Create GPU optimization guides for dual-RTX setup

SUCCESS CRITERIA: Complete documentation coverage with examples, automated doc generation pipeline, developer-friendly API docs, comprehensive deployment guides, dual-machine operational documentation

DELIVERABLE: Full documentation suite with automated generation, dual-machine architecture guides, GPU optimization docs, commit "DOCS: Complete documentation overhaul - API docs, architecture guides, deployment runbooks, dual-RTX setup guides"
```

## 💡 **ENHANCED PROMPTING STRATEGIES**

### **1. Specificity & Context**
```
BAD:  "Fix the port issues"
GOOD: "Resolve port conflicts in startup_config.yaml between MainPC RTX 4090 (54 agents) and PC2 RTX 3060 (23 agents) ranges, update hardcoded ports in agent files, validate no duplicates across machines"
```

### **2. Chain Multiple Operations**
```
BAD:  "Clean up files"
GOOD: "Clean up backup files → Run syntax validation → Fix import errors → Test agent loading on both machines → Commit changes if all tests pass"
```

### **3. Define Success Criteria**
```
BAD:  "Optimize performance"
GOOD: "Achieve <100ms response time, reduce memory by 30%, eliminate blocking I/O, pass 24-hour stability test across RTX 4090 + RTX 3060 setup"
```

### **4. Include Error Recovery**
```
BAD:  "Deploy to production"
GOOD: "Deploy with health checks, rollback if any service fails, retry up to 3 times, notify via Slack on completion/failure, handle dual-machine scenarios"
```

### **5. Scope & Constraints**
```
BAD:  "Update all files"
GOOD: "Update files in main_pc_code/agents/ and pc2_code/agents/ only, preserve existing .bak files in archive/, skip test files, maintain dual-machine compatibility"
```

## 🎯 **BACKGROUND AGENT BEST PRACTICES FOR THIS CODEBASE**

1. **Always specify file patterns**: `main_pc_code/agents/*.py`, `pc2_code/agents/*.py`, `config/*.yaml`
2. **Include validation steps**: "Test imports work", "Validate syntax", "Check port conflicts across machines"
3. **Define rollback procedures**: "If tests fail, restore from backup"
4. **Set success metrics**: "All 77 agents start successfully", "Zero syntax errors", "Both RTX cards operational"
5. **Chain related operations**: Cleanup → Fix → Test → Commit
6. **Include monitoring**: "Generate report", "Log all changes", "Notify completion"
7. **Consider dual-machine architecture**: Always account for MainPC (RTX 4090) and PC2 (RTX 3060) differences

## ⚠️ **COMMON PITFALLS TO AVOID**

❌ **TOO VAGUE**: "Fix the system"
✅ **SPECIFIC**: "Fix BaseAgent circular import in common/core/base_agent.py line 41, update affected agent files across both machines"

❌ **NO VALIDATION**: "Delete backup files"  
✅ **WITH VALIDATION**: "Delete .bak files but preserve main versions, verify all 77 agents still import correctly on both machines"

❌ **NO ROLLBACK**: "Update all configs"
✅ **WITH ROLLBACK**: "Update configs, test startup sequence on both machines, rollback if any agent fails to start"

❌ **IGNORE DUAL-MACHINE**: "Deploy containers"
✅ **DUAL-MACHINE AWARE**: "Deploy containers ensuring RTX 4090 gets GPU-intensive agents, RTX 3060 gets lighter workload, test cross-machine communication"

---

**Remember**: Background agent thrives on detailed, specific instructions with clear success criteria and validation steps! Always consider the dual-machine architecture (MainPC RTX 4090 + PC2 RTX 3060) in your prompts. 