# 🎯 PHASE 0 ACTION PLAN: CRITICAL FOUNDATION
**Timeline:** Days 1-7 (Week 0-1)  
**Focus:** Infrastructure Setup & Critical Risk Mitigation  
**Status:** DETAILED PLANNING COMPLETE

---

## 📋 EXECUTIVE SUMMARY

**Goal:** Establish critical foundation for safe agent system evolution  
**Scope:** JSON Schema, PathManager fixes, port audit, secrets, logging, BaseAgent migration start  
**Agents Affected:** All 77 agents (54 MainPC + 23 PC2)  
**Risk Level:** LOW (incremental changes with full rollback capability)

**Success Criteria:**
- [ ] JSON schema validation active for both configs
- [ ] start_system_v2.py validation bug fixed and tested  
- [ ] Port conflicts identified and resolved
- [ ] Rotating file handlers deployed to prevent disk issues
- [ ] Secret leakage eliminated from process lists
- [ ] First 5 legacy agents migrated to BaseAgent
- [ ] Prometheus exporters active on all agents

---

## ⚠️ CRITICAL CONSTRAINTS

1. **Zero Downtime**: All 77 agents must remain operational
2. **Incremental Changes**: Single-issue commits with rollback capability
3. **Validation Required**: Every change has automated verification
4. **Rollback Ready**: 5-minute maximum rollback time
5. **Documentation**: All procedures executable by team members

---

## 📅 DAILY IMPLEMENTATION PLAN

### **DAY 1: JSON SCHEMA & VALIDATION FRAMEWORK**

#### **🎯 Objectives**
- Establish configuration validation foundation
- Prevent future config drift between MainPC and PC2

#### **📝 Tasks**

**Task 1A: Create JSON Schema Structure**
```bash
# Create schema directory
mkdir -p common/validation/schemas

# Create main schema file
touch common/validation/schemas/agent_config.schema.yaml
```

**Files to Create:**
- `common/validation/schemas/agent_config.schema.yaml`
- `scripts/validate_config.py`
- `common/validation/__init__.py`
- `common/validation/config_validator.py`

**Task 1B: Implement Schema Content**
```yaml
# Content for agent_config.schema.yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
title: "AI-Agent Startup Configuration"
type: object
required: [global_settings]
properties:
  global_settings:
    type: object
    properties:
      environment: {type: object, additionalProperties: {type: string}}
      resource_limits:
        type: object
        properties:
          cpu_percent: {type: number, minimum: 1, maximum: 100}
          memory_mb: {type: integer, minimum: 128}
          max_threads: {type: integer, minimum: 1}
      health_checks:
        type: object
        properties:
          interval_seconds: {type: integer, minimum: 5}
          timeout_seconds: {type: integer, minimum: 1}
          retries: {type: integer, minimum: 0}
  agent_groups:
    type: object
    additionalProperties:
      type: object
      additionalProperties: {$ref: "#/$defs/agent"}
  pc2_services:
    type: array
    items: {$ref: "#/$defs/agent"}
$defs:
  agent:
    type: object
    required: [script_path, port, health_check_port]
    properties:
      name: {type: string}
      script_path: {type: string}
      port: {type: integer, minimum: 1024, maximum: 65535}
      health_check_port: {type: integer, minimum: 1024, maximum: 65535}
      required: {type: boolean}
      dependencies: {type: array, items: {type: string}}
      config: {type: object}
      host: {type: string}
      env_vars: {type: object, additionalProperties: {type: string}}
```

**Task 1C: Create Validator Script**
```python
# scripts/validate_config.py
#!/usr/bin/env python3
import yaml
import jsonschema
import sys
from pathlib import Path

def validate_config(config_path, schema_path, warn_mode=False):
    # Implementation with proper error handling
    pass

if __name__ == "__main__":
    # CLI interface for CI integration
    pass
```

**Task 1D: CI Integration Setup**
```bash
# Add to CI pipeline (.github/workflows/config-validation.yml)
name: Config Validation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.10
      - name: Install dependencies
        run: pip install pyyaml jsonschema
      - name: Validate MainPC Config
        run: python scripts/validate_config.py main_pc_code/config/startup_config.yaml --warn
      - name: Validate PC2 Config  
        run: python scripts/validate_config.py pc2_code/config/startup_config.yaml --warn
```

**✅ Day 1 Checkpoint:**
- [ ] Schema files created and committed
- [ ] Validator script functional in warn mode
- [ ] CI pipeline green with warnings logged
- [ ] No existing agents affected

**🔄 Rollback Plan:** `git revert <commit-sha>` removes schema files only

---

### **DAY 2: SCRIPT PATH RESOLUTION FIX**

#### **🎯 Objectives**
- Fix start_system_v2.py validation bug
- Ensure all 77 agents can be properly located

#### **📝 Tasks**

**Task 2A: PathManager Enhancement**
```python
# Add to common/utils/path_manager.py
@staticmethod
def resolve_script(relative_path: str) -> Path:
    """Resolve any script_path in YAML to an absolute path under project root."""
    project_root = Path(PathManager.get_project_root())
    resolved_path = (project_root / relative_path).resolve()
    return resolved_path if resolved_path.exists() else None
```

**Task 2B: Update start_system_v2.py**
```python
# Modify main_pc_code/scripts/start_system_v2.py
# BEFORE:
# abs_script = self._resolve_script_path(script_path)
# if not abs_script.exists():

# AFTER:
from common.utils.path_manager import PathManager
abs_script = PathManager.resolve_script(script_path)
if abs_script is None or not abs_script.exists():
    logger.error(f"❌ Script not found for {agent_name}: {script_path}")
    return None
```

**Task 2C: Create Unit Tests**
```python
# tests/test_path_manager.py
def test_resolve_script_mainpc():
    """Test resolving MainPC agent script paths"""
    path = PathManager.resolve_script("main_pc_code/agents/service_registry_agent.py")
    assert path is not None
    assert path.exists()

def test_resolve_script_pc2():
    """Test resolving PC2 agent script paths"""
    path = PathManager.resolve_script("pc2_code/agents/memory_orchestrator_service.py")
    assert path is not None
    assert path.exists()

def test_resolve_script_missing():
    """Test handling of missing script paths"""
    path = PathManager.resolve_script("non_existent/script.py")
    assert path is None
```

**Task 2D: Integration Testing**
```bash
# Test dry-run on both systems
python main_pc_code/scripts/start_system_v2.py --dry-run
python pc2_code/scripts/start_system_v2.py --dry-run

# Expected: 77/77 scripts found message
```

**✅ Day 2 Checkpoint:**
- [ ] PathManager.resolve_script() implemented and tested
- [ ] start_system_v2.py patched on both machines
- [ ] Unit tests passing
- [ ] Dry-run validates all 77 scripts found
- [ ] No agents affected (change only affects startup validation)

**🔄 Rollback Plan:** `git revert <commit-sha>` restores original start_system_v2.py

---

### **DAY 3: PORT AUDIT & CONFLICT RESOLUTION**

#### **🎯 Objectives**
- Identify and resolve port conflicts
- Establish port allocation tracking

#### **📝 Tasks**

**Task 3A: Create Port Audit Script**
```python
# scripts/port_linter.py
#!/usr/bin/env python3
import yaml
from collections import defaultdict
from pathlib import Path

def audit_ports(config_path):
    """Scan config for port conflicts and gaps"""
    # Load YAML and extract all port assignments
    # Check for duplicates, gaps, and range violations
    # Generate report with recommendations
    pass

def main():
    mainpc_report = audit_ports("main_pc_code/config/startup_config.yaml")
    pc2_report = audit_ports("pc2_code/config/startup_config.yaml") 
    
    # Cross-machine conflict detection
    # Range optimization suggestions
    # Generate port allocation map
    pass
```

**Task 3B: Execute Port Audit**
```bash
python scripts/port_linter.py > port_audit_report.txt
```

**Expected Output Format:**
```
🔍 PORT AUDIT REPORT
==================

MainPC Port Usage:
- Range 5600-5699: 15 agents (15% utilization)
- Range 5700-5799: 8 agents (8% utilization) 
- Range 7200-7299: 31 agents (31% utilization)

PC2 Port Usage:
- Range 7100-7199: 23 agents (23% utilization)

⚠️ CONFLICTS DETECTED:
- None (cross-machine isolation confirmed)

📊 RECOMMENDATIONS:
- MainPC: Consolidate 5600 range agents to 7200 range
- PC2: Reserve 7200+ for future expansion
```

**Task 3C: Resolve Any Conflicts**
```bash
# If conflicts found, update configs with unique ports
# Priority: PC2 keeps current, MainPC adjusts
# Document changes in port_changes.log
```

**Task 3D: Add Port Validation to CI**
```yaml
# Add to .github/workflows/config-validation.yml
- name: Port Conflict Check
  run: python scripts/port_linter.py --fail-on-conflict
```

**✅ Day 3 Checkpoint:**
- [ ] Port audit completed and documented
- [ ] All conflicts (if any) resolved
- [ ] Port allocation map created
- [ ] CI includes port validation
- [ ] No service disruptions during config updates

**🔄 Rollback Plan:** Restore original ports from `port_changes.log` backup

---

### **DAY 4: LOGGING INFRASTRUCTURE UPGRADE**

#### **🎯 Objectives**
- Prevent disk space exhaustion from unbounded logs
- Deploy rotating file handlers safely

#### **📝 Tasks**

**Task 4A: Enhance JSON Logger**
```python
# Modify common/utils/json_logger.py or create enhanced version
from logging.handlers import RotatingFileHandler
import logging

def get_rotating_json_logger(name, log_file, max_bytes=10*1024*1024, backup_count=5):
    """Create logger with rotation to prevent disk issues"""
    logger = logging.getLogger(name)
    
    # Rotating file handler (10MB max, 5 backups)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    # JSON formatter
    formatter = JsonFormatter()
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger
```

**Task 4B: Update BaseAgent Template**
```python
# Modify common/core/base_agent.py logging initialization
# Replace static file logger with rotating version
self.logger = get_rotating_json_logger(
    self.name, 
    self.log_file,
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5           # Keep 5 old files
)
```

**Task 4C: Select Low-Risk Test Agents**
```python
# Target agents for initial deployment (low traffic, non-critical):
test_agents = [
    "pc2_code/agents/memory_orchestrator_service.py",
    "main_pc_code/agents/system_digital_twin.py", 
    "main_pc_code/agents/mood_tracker_agent.py",
    "pc2_code/agents/unified_web_agent.py",
    "main_pc_code/agents/face_recognition_agent.py"
]
```

**Task 4D: Gradual Deployment**
```bash
# Deploy to test agents one by one
# Monitor disk usage before/after each deployment
# Verify log rotation triggers at 10MB

for agent in test_agents:
    # Update agent to use rotating logger
    # Restart agent
    # Monitor for 2 hours
    # Verify logs rotate properly
    # Check disk usage stable
done
```

**✅ Day 4 Checkpoint:**
- [ ] Rotating file handler implemented
- [ ] 5 test agents successfully migrated
- [ ] Disk usage monitoring shows stable consumption
- [ ] Log rotation triggers verified at 10MB limit
- [ ] No logging errors or agent disruptions

**🔄 Rollback Plan:** Restart agents to revert to original logging configuration

---

### **DAY 5: SECRETS REMEDIATION**

#### **🎯 Objectives**
- Eliminate credential leakage in process lists
- Implement secure secret injection

#### **📝 Tasks**

**Task 5A: Secrets Discovery Scan**
```bash
# Find all hardcoded secrets in codebase
grep -R --line-number -E '(NATS_|REDIS_|API_KEY|TOKEN).*=' pc2_code main_pc_code > secrets_scan.txt
grep -R --line-number -E '("nats://.*:.*@)|(\snats_user:)|(\snats_password:)' *.yaml >> secrets_scan.txt

# Expected findings: NATS credentials in YAML env_vars
```

**Task 5B: Create SecretManager Utility**
```python
# common/utils/secret_manager.py
import os
from pathlib import Path
from typing import Optional

class SecretManager:
    """Secure secret access avoiding process list exposure"""
    
    @staticmethod
    def get_secret(secret_name: str) -> str:
        """Get secret from secure storage (env var, file, or vault)"""
        # 1. Try environment variable first
        env_value = os.getenv(secret_name)
        if env_value:
            return env_value
            
        # 2. Try secure file location
        secret_file = Path(f"/run/secrets/{secret_name}")
        if secret_file.exists():
            return secret_file.read_text().strip()
            
        # 3. Fallback for development
        dev_file = Path(f"secrets/{secret_name}")
        if dev_file.exists():
            return dev_file.read_text().strip()
            
        raise ValueError(f"Secret {secret_name} not found in any secure location")
    
    @staticmethod
    def get_nats_credentials() -> tuple[str, str]:
        """Get NATS username and password securely"""
        username = SecretManager.get_secret("NATS_USERNAME")
        password = SecretManager.get_secret("NATS_PASSWORD")
        return username, password
```

**Task 5C: Replace Hardcoded Credentials**
```yaml
# Identify 3 agents with YAML credential exposure
# Example: pc2_code/config/startup_config.yaml

# BEFORE:
env_vars:
  NATS_URL: "nats://admin:password123@localhost:4222"

# AFTER:  
env_vars:
  NATS_URL: "nats://${NATS_USERNAME}:${NATS_PASSWORD}@localhost:4222"
```

**Task 5D: Create Secure Injection for Development**
```bash
# Create development secrets directory
mkdir -p secrets
echo "admin" > secrets/NATS_USERNAME
echo "dev_password_change_in_prod" > secrets/NATS_PASSWORD
chmod 600 secrets/*

# Add to .gitignore
echo "secrets/" >> .gitignore
```

**Task 5E: Validation Testing**
```bash
# Test that credentials no longer appear in process list
ps aux | grep -i nats
# Should show no passwords

# Test that agents still authenticate successfully
curl http://localhost:9000/health
# Should return healthy status
```

**✅ Day 5 Checkpoint:**
- [ ] All hardcoded secrets identified and catalogued
- [ ] SecretManager utility implemented and tested
- [ ] 3 high-risk credential exposures remediated
- [ ] Process list scan shows no credential leakage
- [ ] Agent authentication still functional

**🔄 Rollback Plan:** Restore original YAML with hardcoded credentials

---

### **DAY 6: BASEAGENT MIGRATION (PHASE 1)**

#### **🎯 Objectives**
- Begin systematic migration of legacy agents
- Establish migration template and validation

#### **📝 Tasks**

**Task 6A: Identify Legacy Agents**
```bash
# Find agents not inheriting from BaseAgent
grep -R --include='*.py' -L 'class .*BaseAgent' main_pc_code pc2_code \
     | grep -E 'agents/.+\.py$' \
     | grep -v test \
     | grep -v __pycache__ > legacy_agents.txt

# Expected: ~29 legacy agents identified
```

**Task 6B: Select First 5 Migration Targets**
```python
# Priority: Low-risk, low-traffic agents
migration_batch_1 = [
    "pc2_code/agents/async_processor.py",           # Background processing
    "main_pc_code/agents/system_monitor.py",       # Monitoring only  
    "pc2_code/agents/cache_manager.py",            # Simple caching
    "main_pc_code/agents/file_watcher.py",         # File system events
    "pc2_code/agents/log_aggregator.py"            # Log collection
]
```

**Task 6C: Create Migration Template**
```python
# Migration template for legacy agent conversion

# STEP 1: Add BaseAgent import
from common.core.base_agent import BaseAgent

# STEP 2: Change class inheritance  
# BEFORE: class AsyncProcessor:
# AFTER:  class AsyncProcessor(BaseAgent):

# STEP 3: Update __init__ method
def __init__(self, **kwargs):
    super().__init__(name="AsyncProcessor", **kwargs)
    # Keep original initialization code...
    
# STEP 4: Replace custom health checks
# Remove custom socket health code
# BaseAgent provides standardized /health endpoint

# STEP 5: Update main block
if __name__ == '__main__':
    AsyncProcessor().run()
```

**Task 6D: Execute Migration**
```bash
# Migrate each agent individually with testing
for agent in migration_batch_1:
    # 1. Create backup
    cp $agent ${agent}.backup
    
    # 2. Apply migration template
    # 3. Test agent starts successfully
    # 4. Verify /health endpoint works
    # 5. Check ObservabilityHub receives metrics
    # 6. Monitor for 1 hour
    # 7. Proceed to next agent
done
```

**Task 6E: Validation Testing**
```bash
# For each migrated agent:
# 1. Health endpoint test
curl http://localhost:[agent_port]/health

# 2. Service registry test  
curl http://localhost:8500/v1/health/service/[agent_name]

# 3. ObservabilityHub metrics test
curl http://localhost:9000/metrics | grep [agent_name]

# 4. Log validation
tail -f [agent_log] | grep -E "(ERROR|WARN)"
```

**✅ Day 6 Checkpoint:**
- [ ] 29 legacy agents identified and documented
- [ ] 5 low-risk agents successfully migrated to BaseAgent
- [ ] All health endpoints responding correctly
- [ ] ServiceRegistry shows all agents as healthy
- [ ] ObservabilityHub receiving metrics from migrated agents
- [ ] No functionality regressions detected

**🔄 Rollback Plan:** `cp [agent].backup [agent]` and restart affected agents

---

### **DAY 7: PROMETHEUS EXPORTERS & PHASE REVIEW**

#### **🎯 Objectives**
- Deploy Prometheus exporters to all agents
- Conduct Phase 0 completion review

#### **📝 Tasks**

**Task 7A: Prometheus Exporter Integration**
```python
# Add to common/core/base_agent.py or create side-car
from prometheus_client import Counter, Histogram, generate_latest

class PrometheusExporter:
    """Standardized metrics exporter for all agents"""
    
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.request_count = Counter(
            'agent_requests_total', 
            'Total requests handled',
            ['agent', 'method']
        )
        self.request_duration = Histogram(
            'agent_request_duration_seconds',
            'Request duration',
            ['agent', 'method']
        )
    
    def export_metrics(self):
        """Generate metrics in Prometheus format"""
        return generate_latest()
```

**Task 7B: Environment Flag Deployment**
```bash
# Add to agent configurations
# For agents not yet migrated to BaseAgent, use environment flag
export ENABLE_PROMETHEUS_METRICS=true

# For BaseAgent agents, automatic inclusion
```

**Task 7C: Metrics Validation**
```bash
# Test metrics endpoint on each agent
for port in $(grep -E "health_check_port|port" */config/startup_config.yaml | grep -o "[0-9]\+"); do
    echo "Testing metrics on port $port"
    curl -s http://localhost:$port/metrics | head -5
done
```

**Task 7D: Phase 0 Completion Review**
```bash
# Generate completion report
cat > phase_0_completion_report.md << 'EOF'
# PHASE 0 COMPLETION REPORT

## ✅ SUCCESS CRITERIA MET
- [x] JSON schema validation active for both configs
- [x] start_system_v2.py validation bug fixed and tested
- [x] Port conflicts identified and resolved  
- [x] Rotating file handlers deployed (5 agents)
- [x] Secret leakage eliminated from process lists
- [x] First 5 legacy agents migrated to BaseAgent
- [x] Prometheus exporters active on all agents

## 📊 METRICS
- Legacy agents migrated: 5/29 (17%)
- Agents with rotating logs: 5/77 (6%)
- Secrets remediated: 3 critical exposures
- Port conflicts resolved: 0 detected
- Schema validation: 100% pass rate

## 🎯 READY FOR PHASE 1
System foundation is stable and ready for path management standardization.
EOF
```

**✅ Day 7 Checkpoint:**
- [ ] Prometheus metrics available on all 77 agents
- [ ] ObservabilityHub collecting comprehensive metrics
- [ ] Phase 0 completion report generated
- [ ] All success criteria validated
- [ ] System health confirmed at 99.9% uptime
- [ ] Go/No-Go decision for Phase 1 approved

**🔄 Rollback Plan:** Disable metrics collection via environment flags

---

## 🚨 EMERGENCY PROTOCOLS

### **Fast Rollback Procedures**

**Single Agent Rollback (< 2 minutes):**
```bash
# Restore from backup
cp [agent_file].backup [agent_file]
supervisorctl restart [agent_name]
curl http://localhost:[port]/health  # Verify recovery
```

**Configuration Rollback (< 3 minutes):**
```bash
git revert [commit_sha]
git push origin main
# Restart affected agents
supervisorctl restart all
```

**System-Wide Rollback (< 5 minutes):**
```bash
# Nuclear option - restore entire Phase 0 changes
git reset --hard [phase_0_start_commit]
git push --force-with-lease origin main
supervisorctl restart all
```

### **Health Monitoring**

**Critical Health Checks:**
```bash
# Agent health status
curl -f http://localhost:9000/health || echo "ObservabilityHub DOWN"

# Service registry status  
curl -f http://localhost:8500/v1/health/state/passing | wc -l

# Disk space monitoring
df -h / | awk 'NR==2 {if ($5 > 85) print "DISK SPACE CRITICAL: " $5}'

# Memory usage
free -m | awk 'NR==2{if ($3*100/$2 > 85) print "MEMORY CRITICAL: " $3*100/$2 "%"}'
```

**Escalation Triggers:**
- 🟡 **Warning**: Single agent down > 5 minutes
- 🟠 **Alert**: >3 agents down OR ObservabilityHub down
- 🔴 **Critical**: >10 agents down OR system-wide failure

### **Communication Plan**

**Incident Response:**
1. **Immediate** (0-5 min): Assess scope and attempt fast rollback
2. **Short-term** (5-15 min): Escalate to Lead SRE if rollback fails  
3. **Extended** (15+ min): Engage CTO and vendor support

**Notification Channels:**
- Slack #ops-alerts for warnings and updates
- PagerDuty for critical incidents
- Email for post-incident reviews

---

## 📈 SUCCESS METRICS & KPIs

### **Phase 0 Success Indicators**

**Technical Metrics:**
- ✅ Agent Uptime: >99.9% maintained during all changes
- ✅ Configuration Validation: 100% schema compliance
- ✅ Security Posture: 0 credentials visible in process lists
- ✅ Monitoring Coverage: 100% agents reporting metrics
- ✅ Deployment Safety: 0 failed rollbacks required

**Operational Metrics:**
- ✅ Change Velocity: 7 days for complete foundation
- ✅ Risk Mitigation: 8/8 critical risks have active mitigation
- ✅ Team Readiness: All procedures documented and tested
- ✅ Knowledge Transfer: Migration templates proven effective

**Phase 1 Readiness Indicators:**
- ✅ PathManager foundation established
- ✅ BaseAgent migration proven (5 successful conversions)
- ✅ CI/CD validation pipeline active
- ✅ Emergency protocols tested and documented

---

## 🔄 TODO INTEGRATION

### **Progressive Planning Workflow**

**Phase 0 Completion Trigger:**
```markdown
TODO: Phase 0 Completion & Phase 1 Planning
1. [COMPLETED] Execute all Day 1-7 tasks
2. [PENDING] Validate all success criteria  
3. [PENDING] Generate completion report
4. [PENDING] Re-read BACKGROUND_AGENT_GUIDE.md
5. [PENDING] Review Phase 0 lessons learned
6. [PENDING] Create detailed Phase 1 Action Plan
7. [PENDING] Execute Phase 1 (Path Management Standardization)
```

**Daily Task Management:**
```markdown
TODO: Day [X] Tasks - [DATE]
1. [STATUS] Task XA: [Description]
2. [STATUS] Task XB: [Description]  
3. [STATUS] Task XC: [Description]
4. [STATUS] Daily Checkpoint Validation
5. [STATUS] Rollback Procedures Tested
```

### **Continuity Assurance**

**Session Handoff Protocol:**
1. Update todo status before session end
2. Document any deviations or issues
3. Note specific validation steps completed
4. Mark rollback procedures tested
5. Prepare next session entry point

**Context Recovery Steps:**
1. Re-read implementation_roadmap/BACKGROUND_AGENT_GUIDE.md
2. Review current phase action plan
3. Check todo status and completion
4. Validate system health before proceeding
5. Resume at marked checkpoint

---

## ✅ PHASE 0 EXECUTION READY

**All systems prepared for systematic execution of 7-day foundation plan.**

**Next Action:** Execute Day 1 tasks with todo management integration. 