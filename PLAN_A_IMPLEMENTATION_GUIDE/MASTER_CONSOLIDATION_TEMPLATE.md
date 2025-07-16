# MASTER CONSOLIDATION TEMPLATE
## Complete Implementation Guide for ANY Agent Consolidation

### CRITICAL: BEFORE STARTING - VERIFY ACTUAL AGENTS EXIST
```bash
# ALWAYS CHECK FIRST - Replace with actual agent names
find main_pc_code/agents/ -name "*ACTUAL_AGENT_NAME*.py" -type f
find pc2_code/agents/ -name "*ACTUAL_AGENT_NAME*.py" -type f
grep -r "ACTUAL_AGENT_NAME" main_pc_code/agents/ pc2_code/agents/
```

### TEMPLATE STRUCTURE
**REPLACE ALL PLACEHOLDERS WITH ACTUAL VALUES FROM YOUR SYSTEM**

---

## PHASE: [CONSOLIDATION_NAME]
### OVERVIEW
Consolidate [LIST_OF_ACTUAL_AGENTS] into unified [NEW_AGENT_NAME]:

**MAIN_PC AGENTS TO CONSOLIDATE:**
- `[ACTUAL_AGENT_1].py` (main_pc) - [VERIFIED EXISTS: YES/NO]
- `[ACTUAL_AGENT_2].py` (main_pc) - [VERIFIED EXISTS: YES/NO]
- `[ACTUAL_AGENT_3].py` (main_pc) - [VERIFIED EXISTS: YES/NO]

**PC2 AGENTS TO CONSOLIDATE:**
- `[ACTUAL_AGENT_4].py` (pc2) - [VERIFIED EXISTS: YES/NO]
- `[ACTUAL_AGENT_5].py` (pc2) - [VERIFIED EXISTS: YES/NO]
- `[ACTUAL_AGENT_6].py` (pc2) - [VERIFIED EXISTS: YES/NO]

### PRE-IMPLEMENTATION VERIFICATION
```bash
# STEP 1: VERIFY ALL AGENTS EXIST
echo "=== VERIFYING AGENT EXISTENCE ==="
for agent in "[ACTUAL_AGENT_1]" "[ACTUAL_AGENT_2]" "[ACTUAL_AGENT_3]"; do
    if [ -f "main_pc_code/agents/${agent}.py" ]; then
        echo "✓ main_pc: ${agent}.py EXISTS"
    else
        echo "✗ main_pc: ${agent}.py MISSING - ABORT CONSOLIDATION"
        exit 1
    fi
done

for agent in "[ACTUAL_AGENT_4]" "[ACTUAL_AGENT_5]" "[ACTUAL_AGENT_6]"; do
    if [ -f "pc2_code/agents/${agent}.py" ]; then
        echo "✓ pc2: ${agent}.py EXISTS"
    else
        echo "✗ pc2: ${agent}.py MISSING - ABORT CONSOLIDATION"
        exit 1
    fi
done
```

### STEP-BY-STEP INSTRUCTIONS

#### Step 1: Backup Original Agents
```bash
# Create timestamped backup directory
BACKUP_DIR="backups/[CONSOLIDATION_NAME]_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup main_pc agents
cp main_pc_code/agents/[ACTUAL_AGENT_1].py $BACKUP_DIR/main_pc_[ACTUAL_AGENT_1].py
cp main_pc_code/agents/[ACTUAL_AGENT_2].py $BACKUP_DIR/main_pc_[ACTUAL_AGENT_2].py
cp main_pc_code/agents/[ACTUAL_AGENT_3].py $BACKUP_DIR/main_pc_[ACTUAL_AGENT_3].py

# Backup pc2 agents
cp pc2_code/agents/[ACTUAL_AGENT_4].py $BACKUP_DIR/pc2_[ACTUAL_AGENT_4].py
cp pc2_code/agents/[ACTUAL_AGENT_5].py $BACKUP_DIR/pc2_[ACTUAL_AGENT_5].py
cp pc2_code/agents/[ACTUAL_AGENT_6].py $BACKUP_DIR/pc2_[ACTUAL_AGENT_6].py

echo "Backup created at: $BACKUP_DIR"
```

#### Step 2: Extract All Logic from Original Agents
**CRITICAL: Extract EVERY method, class, and function**

**FROM `main_pc_code/agents/[ACTUAL_AGENT_1].py`:**
```python
# READ THE ACTUAL FILE AND LIST ALL:
# - Classes
# - Methods
# - Functions
# - Configuration parameters
# - Import statements
# - Helper functions
# - Data structures
# - Algorithms
```

**FROM `main_pc_code/agents/[ACTUAL_AGENT_2].py`:**
```python
# READ THE ACTUAL FILE AND LIST ALL:
# - Classes
# - Methods
# - Functions
# - Configuration parameters
# - Import statements
# - Helper functions
# - Data structures
# - Algorithms
```

**FROM `main_pc_code/agents/[ACTUAL_AGENT_3].py`:**
```python
# READ THE ACTUAL FILE AND LIST ALL:
# - Classes
# - Methods
# - Functions
# - Configuration parameters
# - Import statements
# - Helper functions
# - Data structures
# - Algorithms
```

**FROM `pc2_code/agents/[ACTUAL_AGENT_4].py`:**
```python
# READ THE ACTUAL FILE AND LIST ALL:
# - Classes
# - Methods
# - Functions
# - Configuration parameters
# - Import statements
# - Helper functions
# - Data structures
# - Algorithms
```

**FROM `pc2_code/agents/[ACTUAL_AGENT_5].py`:**
```python
# READ THE ACTUAL FILE AND LIST ALL:
# - Classes
# - Methods
# - Functions
# - Configuration parameters
# - Import statements
# - Helper functions
# - Data structures
# - Algorithms
```

**FROM `pc2_code/agents/[ACTUAL_AGENT_6].py`:**
```python
# READ THE ACTUAL FILE AND LIST ALL:
# - Classes
# - Methods
# - Functions
# - Configuration parameters
# - Import statements
# - Helper functions
# - Data structures
# - Algorithms
```

#### Step 3: Create Unified [NEW_AGENT_NAME]
```python
# Create main_pc_code/agents/[NEW_AGENT_NAME].py
class [NEW_AGENT_NAME]:
    def __init__(self, machine_type="main_pc"):
        self.machine_type = machine_type
        # Initialize ALL extracted components
        self.[COMPONENT_1] = [COMPONENT_1_CLASS]()
        self.[COMPONENT_2] = [COMPONENT_2_CLASS]()
        self.[COMPONENT_3] = [COMPONENT_3_CLASS]()
        
    # Include ALL extracted methods with proper namespacing
    def [METHOD_1](self):
        # Original logic from [ACTUAL_AGENT_1]
        pass
        
    def [METHOD_2](self):
        # Original logic from [ACTUAL_AGENT_2]
        pass
        
    def [METHOD_3](self):
        # Original logic from [ACTUAL_AGENT_3]
        pass
        
    # ... ALL other extracted methods
```

#### Step 4: Implement Machine-Specific Logic
```python
class [NEW_AGENT_NAME]:
    def __init__(self, machine_type="main_pc"):
        self.machine_type = machine_type
        
    def process_request(self, request):
        if self.machine_type == "main_pc":
            return self.process_main_pc_request(request)
        elif self.machine_type == "pc2":
            return self.process_pc2_request(request)
            
    def process_main_pc_request(self, request):
        # Execute ALL main_pc specific operations
        results = {}
        results.update(self.[METHOD_1](request))
        results.update(self.[METHOD_2](request))
        results.update(self.[METHOD_3](request))
        return results
        
    def process_pc2_request(self, request):
        # Execute ALL pc2 specific operations
        results = {}
        results.update(self.[METHOD_4](request))
        results.update(self.[METHOD_5](request))
        results.update(self.[METHOD_6](request))
        return results
```

#### Step 5: Update Configuration Files
```yaml
# Update config/[CONSOLIDATION_NAME]_config.yaml
[NEW_AGENT_NAME_LOWER]:
  enabled: true
  machine_type: "main_pc"  # or "pc2"
  [FEATURE_1]:
    enabled: true
    [PARAMETER_1]: true
    [PARAMETER_2]: true
  [FEATURE_2]:
    enabled: true
    [PARAMETER_3]: true
    [PARAMETER_4]: true
  # Include ALL original configuration parameters
```

#### Step 6: Update Agent Dependencies
```python
# Update ALL agents that import [CONSOLIDATION_NAME] services
# Replace individual imports with:
from agents.[NEW_AGENT_NAME_LOWER] import [NEW_AGENT_NAME]

# Update initialization:
[NEW_AGENT_NAME_LOWER] = [NEW_AGENT_NAME](machine_type="main_pc")  # or "pc2"
```

#### Step 7: Test in Shadow Mode
```python
# Create test script: test_[NEW_AGENT_NAME_LOWER]_shadow.py
def test_[NEW_AGENT_NAME_LOWER]_shadow():
    # Run original agents and [NEW_AGENT_NAME] in parallel
    # Compare outputs to ensure 100% functionality preservation
    original_results = run_original_[CONSOLIDATION_NAME]_agents()
    [NEW_AGENT_NAME_LOWER]_results = run_[NEW_AGENT_NAME_LOWER]()
    
    assert original_results == [NEW_AGENT_NAME_LOWER]_results, "Functionality mismatch detected!"
```

#### Step 8: Gradual Migration
```python
# Phase 1: Run both systems in parallel
# Phase 2: Route 50% of requests to [NEW_AGENT_NAME]
# Phase 3: Route 100% of requests to [NEW_AGENT_NAME]
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
- [ ] ALL [SPECIFIC_FEATURES] logic
- [ ] ALL [SPECIFIC_ALGORITHMS] mechanisms
- [ ] ALL [SPECIFIC_PROCEDURES] methods

#### MUST TEST:
- [ ] [FEATURE_1] accuracy
- [ ] [FEATURE_2] performance
- [ ] [FEATURE_3] quality
- [ ] [FEATURE_4] functionality
- [ ] [FEATURE_5] coordination
- [ ] Error handling
- [ ] Performance metrics
- [ ] Configuration loading
- [ ] Logging functionality
- [ ] [SPECIFIC_TEST_1]
- [ ] [SPECIFIC_TEST_2]
- [ ] [SPECIFIC_TEST_3]

#### ROLLBACK PLAN:
```bash
# If issues detected:
cp $BACKUP_DIR/main_pc_[ACTUAL_AGENT_1].py main_pc_code/agents/
cp $BACKUP_DIR/pc2_[ACTUAL_AGENT_4].py pc2_code/agents/
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
- [ ] [SPECIFIC_VALIDATION_1] verified
- [ ] [SPECIFIC_VALIDATION_2] validated
- [ ] [SPECIFIC_VALIDATION_3] confirmed
- [ ] [SPECIFIC_VALIDATION_4] tested

### COMPLETION CRITERIA
- [ ] [NEW_AGENT_NAME] handles 100% of original functionality
- [ ] No performance degradation
- [ ] All operations return identical results
- [ ] All features work correctly
- [ ] All logic preserved
- [ ] All communication patterns maintained
- [ ] All error scenarios handled
- [ ] All configuration options available
- [ ] All logging patterns preserved
- [ ] All algorithms maintained
- [ ] All data structures preserved
- [ ] All functionality

### NEXT PHASE PREPARATION
- [ ] Document any issues encountered
- [ ] Update dependency mappings
- [ ] Prepare for next consolidation phase
- [ ] Update system documentation
- [ ] Create [NEW_AGENT_NAME] usage guide

---

## USAGE INSTRUCTIONS FOR THIS TEMPLATE

1. **COPY THIS TEMPLATE** for each consolidation phase
2. **REPLACE ALL PLACEHOLDERS** with actual values:
   - `[CONSOLIDATION_NAME]` → actual consolidation name
   - `[ACTUAL_AGENT_1]` → actual agent filename (without .py)
   - `[NEW_AGENT_NAME]` → new consolidated agent class name
   - `[NEW_AGENT_NAME_LOWER]` → lowercase version
   - `[METHOD_1]` → actual method names from agents
   - `[FEATURE_1]` → actual features being consolidated
   - `[SPECIFIC_FEATURES]` → specific features for this consolidation

3. **VERIFY EVERYTHING EXISTS** before starting
4. **READ ACTUAL FILES** to extract real logic
5. **TEST EVERYTHING** before proceeding

### ANTI-HALLUCINATION CHECKLIST
- [ ] All agent names verified to exist in filesystem
- [ ] All method names extracted from actual code
- [ ] All configuration parameters from real config files
- [ ] All dependencies mapped from actual imports
- [ ] All file paths verified to exist
- [ ] All port numbers from actual config files
- [ ] All class names from actual source code
- [ ] All functionality verified in actual agents 