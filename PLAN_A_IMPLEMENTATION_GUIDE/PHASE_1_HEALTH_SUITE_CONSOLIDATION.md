# PHASE 1: HEALTH SUITE CONSOLIDATION
## Complete Implementation Guide

### OVERVIEW
Consolidate all health monitoring agents into a unified HealthSuite as specified in PLAN_A.md:
- `PredictiveHealthMonitor` (main_pc)
- `HealthMonitor` (pc2)
- `SystemHealthManager` (pc2)
- `PerformanceMonitor` (pc2)
- `PerformanceLoggerAgent` (pc2)

### PRE-IMPLEMENTATION CHECKLIST
- [ ] Backup all original health monitoring agents
- [ ] Document current health check patterns
- [ ] Identify all health check endpoints and configurations
- [ ] Map agent dependencies on health monitoring
- [ ] Create rollback plan

### STEP-BY-STEP INSTRUCTIONS

#### Step 1: Backup Original Agents
```bash
# Create backup directory
mkdir -p backups/health_agents_$(date +%Y%m%d_%H%M%S)

# Backup main_pc health agents
cp main_pc_code/agents/predictive_health_monitor.py backups/health_agents_*/main_pc_predictive_health_monitor.py

# Backup pc2 health agents
cp pc2_code/agents/health_monitor.py backups/health_agents_*/pc2_health_monitor.py
cp pc2_code/agents/ForPC2/system_health_manager.py backups/health_agents_*/pc2_system_health_manager.py
cp pc2_code/agents/performance_monitor.py backups/health_agents_*/pc2_performance_monitor.py
cp pc2_code/agents/PerformanceLoggerAgent.py backups/health_agents_*/pc2_performance_logger_agent.py
```

#### Step 2: Extract All Logic from Original Agents
**CRITICAL: Extract EVERY method, class, and function**

From `main_pc_code/agents/predictive_health_monitor.py`:
- Extract `PredictiveHealthMonitor` class
- Extract `check_agent_health()` method
- Extract `predict_failures()` method
- Extract `monitor_system_resources()` method
- Extract `generate_health_report()` method
- Extract `send_health_alert()` method
- Extract `start_monitoring()` method
- Extract `stop_monitoring()` method
- Extract ALL configuration parameters
- Extract ALL import statements
- Extract ALL helper functions

From `pc2_code/agents/health_monitor.py`:
- Extract `HealthMonitor` class
- Extract `check_pc2_agents()` method
- Extract `monitor_gpu_usage()` method
- Extract `check_network_connectivity()` method
- Extract `validate_translation_services()` method
- Extract ALL configuration parameters
- Extract ALL import statements
- Extract ALL helper functions

From `pc2_code/agents/ForPC2/system_health_manager.py`:
- Extract `SystemHealthManager` class
- Extract `manage_system_health()` method
- Extract `coordinate_health_checks()` method
- Extract `generate_system_report()` method
- Extract ALL configuration parameters
- Extract ALL import statements
- Extract ALL helper functions

From `pc2_code/agents/performance_monitor.py`:
- Extract `PerformanceMonitor` class
- Extract `monitor_performance()` method
- Extract `track_metrics()` method
- Extract `analyze_performance()` method
- Extract `generate_performance_report()` method
- Extract ALL configuration parameters
- Extract ALL import statements
- Extract ALL helper functions

From `pc2_code/agents/PerformanceLoggerAgent.py`:
- Extract `PerformanceLoggerAgent` class
- Extract `log_performance()` method
- Extract `aggregate_logs()` method
- Extract `generate_log_report()` method
- Extract ALL configuration parameters
- Extract ALL import statements
- Extract ALL helper functions

#### Step 3: Create Unified HealthSuite
```python
# Create pc2_code/agents/health_suite.py
class HealthSuite:
    def __init__(self, machine_type="pc2"):
        self.machine_type = machine_type
        # Initialize ALL extracted components
        self.predictive_health_monitor = PredictiveHealthMonitor()
        self.health_monitor = HealthMonitor()
        self.system_health_manager = SystemHealthManager()
        self.performance_monitor = PerformanceMonitor()
        self.performance_logger_agent = PerformanceLoggerAgent()
        
    # Include ALL extracted methods with proper namespacing
    def check_agent_health(self):
        # Original logic from PredictiveHealthMonitor
        pass
        
    def check_pc2_agents(self):
        # Original logic from HealthMonitor
        pass
        
    def manage_system_health(self):
        # Original logic from SystemHealthManager
        pass
        
    def monitor_performance(self):
        # Original logic from PerformanceMonitor
        pass
        
    def log_performance(self):
        # Original logic from PerformanceLoggerAgent
        pass
        
    # ... ALL other extracted methods
```

#### Step 4: Implement Machine-Specific Logic
```python
class HealthSuite:
    def __init__(self, machine_type="pc2"):
        self.machine_type = machine_type
        
    def run_health_checks(self):
        if self.machine_type == "main_pc":
            return self.run_main_pc_checks()
        elif self.machine_type == "pc2":
            return self.run_pc2_checks()
            
    def run_main_pc_checks(self):
        # Execute ALL main_pc specific health checks
        results = {}
        results.update(self.check_agent_health())
        results.update(self.predict_failures())
        return results
        
    def run_pc2_checks(self):
        # Execute ALL pc2 specific health checks
        results = {}
        results.update(self.check_pc2_agents())
        results.update(self.manage_system_health())
        results.update(self.monitor_performance())
        results.update(self.log_performance())
        return results
```

#### Step 5: Update Configuration Files
```yaml
# Update config/health_config.yaml
health_suite:
  enabled: true
  machine_type: "pc2"  # Primary location as per PLAN_A.md
  check_interval: 30
  alert_threshold: 0.8
  # Include ALL original configuration parameters
```

#### Step 6: Update Agent Dependencies
```python
# Update ALL agents that import health monitoring
# Replace individual imports with:
from agents.health_suite import HealthSuite

# Update initialization:
health_suite = HealthSuite(machine_type="pc2")  # Primary location
```

#### Step 7: Test in Shadow Mode
```python
# Create test script: test_health_suite_shadow.py
def test_health_suite_shadow():
    # Run original agents and HealthSuite in parallel
    # Compare outputs to ensure 100% functionality preservation
    original_results = run_original_health_agents()
    health_suite_results = run_health_suite()
    
    assert original_results == health_suite_results, "Functionality mismatch detected!"
```

#### Step 8: Gradual Migration
```python
# Phase 1: Run both systems in parallel
# Phase 2: Route 50% of requests to HealthSuite
# Phase 3: Route 100% of requests to HealthSuite
# Phase 4: Remove original agents
```

### CRITICAL REMINDERS

#### MUST PRESERVE:
- [ ] ALL method signatures and return types
- [ ] ALL configuration parameters
- [ ] ALL error handling logic
- [ ] ALL logging patterns
- [ ] ALL communication protocols
- [ ] ALL data structures
- [ ] ALL algorithms and business logic
- [ ] ALL import dependencies
- [ ] ALL environment variable usage
- [ ] ALL file paths and locations

#### MUST TEST:
- [ ] Health check accuracy
- [ ] Alert generation
- [ ] Resource monitoring
- [ ] Agent validation
- [ ] Cross-machine communication
- [ ] Error handling
- [ ] Performance metrics
- [ ] Configuration loading
- [ ] Logging functionality

#### ROLLBACK PLAN:
```bash
# If issues detected:
cp backups/health_agents_*/main_pc_predictive_health_monitor.py main_pc_code/agents/
cp backups/health_agents_*/pc2_health_monitor.py pc2_code/agents/
cp backups/health_agents_*/pc2_system_health_manager.py pc2_code/agents/ForPC2/
cp backups/health_agents_*/pc2_performance_monitor.py pc2_code/agents/
cp backups/health_agents_*/pc2_performance_logger_agent.py pc2_code/agents/
# ... restore all original agents
```

### VALIDATION CHECKLIST
- [ ] All original methods extracted and preserved
- [ ] All configuration parameters included
- [ ] Machine-specific logic properly implemented
- [ ] Shadow mode testing passed
- [ ] Performance benchmarks met
- [ ] Error handling verified
- [ ] Logging functionality confirmed
- [ ] Integration tests passed
- [ ] Rollback plan tested

### COMPLETION CRITERIA
- [ ] HealthSuite handles 100% of original functionality
- [ ] No performance degradation
- [ ] All health checks return identical results
- [ ] All alerts generated correctly
- [ ] All monitoring features work
- [ ] All validation logic preserved
- [ ] All communication patterns maintained
- [ ] All error scenarios handled
- [ ] All configuration options available
- [ ] All logging patterns preserved

### NEXT PHASE PREPARATION
- [ ] Document any issues encountered
- [ ] Update dependency mappings
- [ ] Prepare for Phase 2 (MemoryProxy consolidation)
- [ ] Update system documentation
- [ ] Create HealthSuite usage guide 