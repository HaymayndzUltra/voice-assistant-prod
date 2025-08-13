# 🚀 BACKGROUND AGENT DOCKER ARCHITECTURE ANALYSIS PROMPT
# Priority: CRITICAL | Date: 2025-01-13 | Agent: Claude Opus

## 📋 EXECUTIVE DIRECTIVE

You are tasked with performing a comprehensive Docker architecture audit comparing the implemented system against the frozen blueprint (memory-bank/DOCUMENTS/plan.md). Execute all tasks autonomously without user interaction.

## 🎯 PRIMARY OBJECTIVES

### 1. FOLDER STRUCTURE ANALYSIS (Priority: HIGH)
Analyze these critical service folders and identify consolidated agents:

```bash
# Required Analysis Targets:
- /workspace/unified_observability_center/
- /workspace/real_time_audio_pipeline/
- /workspace/model_ops_coordinator/
- /workspace/memory_fusion_hub/
- /workspace/affective_processing_center/
- /workspace/main_pc_code/services/
```

For each folder:
1. Map directory structure
2. Identify main service entry points
3. List all agent modules consolidated within
4. Check for Docker-related files (Dockerfile, entrypoint.sh)
5. Verify requirements.txt dependencies

### 2. AGENT CONSOLIDATION MAPPING (Priority: CRITICAL)

Execute these commands to identify agent consolidation:

```bash
# Find all agent references in service folders
grep -r "class.*Agent\|from.*agents import\|import.*Agent" unified_observability_center/ --include="*.py"
grep -r "class.*Agent\|from.*agents import\|import.*Agent" real_time_audio_pipeline/ --include="*.py"
grep -r "class.*Agent\|from.*agents import\|import.*Agent" model_ops_coordinator/ --include="*.py"
grep -r "class.*Agent\|from.*agents import\|import.*Agent" memory_fusion_hub/ --include="*.py"
grep -r "class.*Agent\|from.*agents import\|import.*Agent" affective_processing_center/ --include="*.py"

# Check startup configurations
cat main_pc_code/config/startup_config.yaml
cat pc2_code/config/startup_config.yaml

# Verify agent migration status
find main_pc_code/agents/ -name "*.py" -type f | wc -l
find pc2_code/agents/ -name "*.py" -type f | wc -l
```

### 3. DOCKER BLUEPRINT VALIDATION (Priority: CRITICAL)

Compare against plan.md (Fleet Coverage Table at lines 109-176):

```python
# Read and parse the blueprint
with open('memory-bank/DOCUMENTS/plan.md', 'r') as f:
    blueprint = f.read()

# Extract service definitions from lines 109-176
# Create validation matrix:
services_to_validate = {
    'ServiceRegistry': {'machine': '4090', 'base': 'family-web', 'ports': '7200/8200'},
    'ModelOpsCoordinator': {'machine': '4090', 'base': 'family-llm-cu121', 'ports': '7212/8212'},
    'MemoryFusionHub': {'machine': 'both', 'base': 'family-cpu-pydeps', 'ports': '5713/6713'},
    'UnifiedObservabilityCenter': {'machine': 'both', 'base': 'family-web', 'ports': '9100/9110'},
    'RealTimeAudioPipeline': {'machine': 'both', 'base': 'family-torch-cu121', 'ports': '5557/6557'},
    'AffectiveProcessingCenter': {'machine': '4090', 'base': 'family-torch-cu121', 'ports': '5560/6560'}
}
```

### 4. DOCKER CONTAINER STATUS CHECK (Priority: HIGH)

```bash
# Check current running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee docker_current_status.txt

# Check all containers (including stopped)
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee docker_all_status.txt

# Verify images match blueprint
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "family-|base-" | tee docker_images_status.txt

# Check docker-compose status
docker-compose ps
docker-compose config --services
```

### 5. ENTRYPOINT VALIDATION (Priority: MEDIUM)

```bash
# Find all entrypoints
find . -name "entrypoint*.sh" -o -name "*entrypoint.sh" | while read file; do
    echo "=== $file ==="
    cat "$file"
    echo ""
done > entrypoints_audit.txt

# Verify entrypoint patterns match blueprint
grep -E "tini|appuser|health" entrypoints_audit.txt
```

### 6. DOCKERFILE ANALYSIS (Priority: HIGH)

```bash
# Analyze all Dockerfiles
for dockerfile in $(find . -name "Dockerfile*" -type f); do
    echo "=== Analyzing: $dockerfile ==="
    
    # Check base image compliance
    grep "^FROM" "$dockerfile"
    
    # Verify multi-stage build
    grep -c "^FROM.*AS" "$dockerfile"
    
    # Check non-root user
    grep "USER appuser" "$dockerfile"
    
    # Verify health check
    grep "HEALTHCHECK" "$dockerfile"
    
    # Check tini usage
    grep "tini" "$dockerfile"
    
    echo "---"
done > dockerfile_compliance_report.txt
```

## 📊 EXPECTED DELIVERABLES

### 1. CONSOLIDATION MAPPING REPORT
```markdown
# Agent Consolidation Report

## unified_observability_center
- Consolidated Agents: [List all agents found]
- Entry Point: app.py
- Dependencies: [Key packages]
- Docker Base: family-web (per blueprint)
- Status: ✅/❌ Compliant

## real_time_audio_pipeline
- Consolidated Agents: [List]
- Entry Point: [Main file]
- Dependencies: [Audio-specific packages]
- Docker Base: family-torch-cu121
- Status: ✅/❌

[Continue for all services...]
```

### 2. DISCREPANCY REPORT
```markdown
# Critical Discrepancies Found

## 1. Missing Services
- [ ] Service X not found in containers
- [ ] Service Y image not built

## 2. Port Mismatches
- ServiceRegistry: Expected 7200/8200, Found: [actual]
- ModelOpsCoordinator: Expected 7212/8212, Found: [actual]

## 3. Base Image Violations
- Service using wrong base family
- Missing CUDA support where required

## 4. Health Check Issues
- Services without /health endpoint
- Failed health checks
```

### 3. ACTIONABLE REMEDIATION PLAN
```markdown
# Docker Architecture Remediation Plan

## Phase 1: Critical Fixes (Immediate)
1. **Fix Port Conflicts**
   ```bash
   # Update docker-compose.yml
   sed -i 's/7200:7200/7200:8200/' docker-compose.yml
   ```

2. **Rebuild Non-Compliant Images**
   ```bash
   # ModelOpsCoordinator needs GPU base
   docker build -f model_ops_coordinator/Dockerfile \
     --build-arg MACHINE=mainpc \
     -t ghcr.io/org/model-ops-coordinator:latest .
   ```

## Phase 2: Service Migration (24 hours)
1. **Migrate Standalone Agents**
   - Move IntentionValidatorAgent → unified_observability_center
   - Move NLUAgent → affective_processing_center
   
2. **Update Startup Configs**
   ```yaml
   # main_pc_code/config/startup_config.yaml
   services:
     unified_observability_center:
       agents:
         - IntentionValidatorAgent
         - ObservabilityDashboardAPI
   ```

## Phase 3: Validation (48 hours)
1. Run comprehensive health checks
2. Verify inter-service communication
3. Test GPU allocation
```

## 🔄 EXECUTION WORKFLOW

```python
# Auto-execution script
import os
import json
import subprocess
from datetime import datetime

def execute_analysis():
    results = {
        'timestamp': datetime.now().isoformat(),
        'folders_analyzed': [],
        'agents_found': {},
        'docker_status': {},
        'discrepancies': [],
        'action_items': []
    }
    
    # Step 1: Folder Analysis
    target_folders = [
        'unified_observability_center',
        'real_time_audio_pipeline',
        'model_ops_coordinator',
        'memory_fusion_hub',
        'affective_processing_center'
    ]
    
    for folder in target_folders:
        # Analyze structure
        # Map agents
        # Check Docker files
        pass
    
    # Step 2: Docker Validation
    # Compare with plan.md
    # Check running containers
    # Verify images
    
    # Step 3: Generate Reports
    # Create comprehensive summary
    # Identify action items
    # Priority ranking
    
    return results

# Execute
if __name__ == "__main__":
    analysis = execute_analysis()
    with open('docker_architecture_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
```

## ⚠️ CRITICAL CHECKS

1. **CUDA Compatibility**
   - Verify CUDA 12.1 support in GPU images
   - Check TORCH_CUDA_ARCH_LIST="8.9;8.6"

2. **Network Isolation**
   - Ensure proper network segmentation
   - Verify cross-machine communication

3. **Resource Limits**
   - Check memory limits per container
   - Verify GPU allocation

4. **Security Compliance**
   - Non-root user (10001:10001)
   - Read-only rootfs where applicable
   - Minimal attack surface

## 📈 SUCCESS METRICS

- [ ] 100% services mapped to blueprint
- [ ] All health endpoints responding (200 OK)
- [ ] Zero port conflicts
- [ ] All images using correct base family
- [ ] GPU services have CUDA support
- [ ] Multi-stage builds reducing size by >40%

## 🚨 ESCALATION TRIGGERS

If any of these conditions are met, immediately create critical alert:

1. Core services (ServiceRegistry, SystemDigitalTwin) not running
2. GPU allocation failures
3. >5 services with health check failures
4. Base image family violations in >3 services
5. Missing critical entrypoints

## 📝 FINAL OUTPUT FORMAT

Create file: `/workspace/docker_architecture_audit_[TIMESTAMP].md` containing:

1. Executive Summary (3-5 bullet points)
2. Consolidation Mapping Table
3. Compliance Matrix (✅/❌ per service)
4. Critical Issues (Ranked by severity)
5. Step-by-Step Remediation Plan
6. Validation Commands
7. Rollback Procedures

---

**EXECUTE THIS ANALYSIS IMMEDIATELY AND REPORT FINDINGS**