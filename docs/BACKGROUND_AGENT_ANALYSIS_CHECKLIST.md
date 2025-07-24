# BACKGROUND AGENT ANALYSIS CHECKLIST

**Task:** Comprehensive analysis of dual-machine AI system  
**Scope:** MainPC (58 agents) + PC2 (27 agents) = 85 total agents  
**Instruction:** ANALYZE and REPORT findings - don't assume solutions  

---

## 📋 **ANALYSIS AREAS TO CHECK**

### **1. AGENT STARTUP SYSTEM**
**Files to analyze:**
- `main_pc_code/scripts/start_system.py`
- `main_pc_code/config/startup_config.yaml` 
- `pc2_code/config/startup_config.yaml`

**What to check:**
- Why do agents crash immediately after startup?
- Are there inheritance issues in base classes?
- Do the startup scripts handle both config schemas?
- Are dependency chains correctly resolved?

### **2. BASEAGENT INHERITANCE**
**Files to analyze:**
- `common/core/base_agent.py`
- Sample agent files that inherit from BaseAgent

**What to check:**
- Is the BaseAgent class constructor working correctly?
- Are there Python inheritance errors?
- Do agent subclasses call parent constructors properly?
- Are initialization parameters being passed correctly?

### **3. CONFIGURATION SCHEMA COMPATIBILITY**
**Files to compare:**
- MainPC: `agent_groups` structure
- PC2: `pc2_services` list structure

**What to check:**
- Can one parser handle both schemas?
- Are agent definitions complete and valid?
- Do dependency references point to actual agents?
- Are there schema inconsistencies between machines?

### **4. PORT ALLOCATION AND CONFLICTS**
**What to analyze:**
- MainPC port ranges vs PC2 port ranges
- Health check port calculations
- Cross-machine communication ports
- Any port conflicts or overlaps

### **5. DEPENDENCY VALIDATION**
**What to check:**
- Circular dependency chains
- Missing agent references
- Invalid dependency declarations
- Dependency resolution order

### **6. HEALTH CHECK SYSTEM**
**What to analyze:**
- Health check endpoint implementations
- Port calculation methods (different patterns?)
- Health check validation logic
- Timeout and retry configurations

### **7. SERVICE DISCOVERY ARCHITECTURE**
**What to check:**
- How do agents find each other?
- Cross-machine service discovery
- Service registry implementations
- Agent registration processes

### **8. CROSS-MACHINE INTEGRATION**
**What to analyze:**
- Network configuration between machines
- Service mesh or discovery protocol
- Communication patterns
- Isolation vs integration strategy

---

## 🔍 **SPECIFIC INVESTIGATION POINTS**

### **Agent Crash Investigation:**
- Examine actual error logs from agent startup attempts
- Trace the exact point of failure in agent initialization
- Identify root cause of immediate crashes

### **Configuration Analysis:**
- Validate all 85 agent definitions
- Check for missing or invalid configuration entries
- Verify script paths and file existence

### **Dependency Graph Analysis:**
- Build complete dependency graph for all agents
- Identify circular dependencies
- Validate startup phase ordering

### **Port and Network Analysis:**
- Map all port allocations across both machines
- Identify conflicts or potential conflicts
- Analyze health check patterns

### **Service Discovery Gaps:**
- How do PC2 agents discover MainPC services?
- Is there a unified discovery mechanism?
- What happens during cross-machine failures?

---

## 📊 **REPORTING REQUIREMENTS**

### **Provide for each analysis area:**
1. **Current Status:** What you found
2. **Issues Identified:** Specific problems discovered
3. **Root Causes:** Why the issues exist
4. **Impact Assessment:** How critical each issue is
5. **Recommendations:** What should be done (not implementation details)

### **Deliverables Expected:**
1. **AGENT_STARTUP_ANALYSIS.md** - Startup system investigation
2. **BASEAGENT_INVESTIGATION.md** - Inheritance and initialization issues
3. **CONFIGURATION_VALIDATION.md** - Config schema and validation results
4. **SERVICE_DISCOVERY_ARCHITECTURE.md** - Cross-machine discovery analysis
5. **PRIORITY_FIXES_ROADMAP.md** - Ordered list of what needs fixing

---

## ⚠️ **ANALYSIS GUIDELINES**

### **DO:**
- Examine actual code and configuration files
- Test hypotheses by running code where possible
- Provide specific file/line references for issues
- Categorize issues by severity and impact
- Give concrete evidence for your findings

### **DON'T:**
- Assume what the fixes should be without investigation
- Provide sample code unless you've verified it works
- Make claims about functionality without testing
- Skip analyzing files mentioned in the checklist

---

## 🎯 **SUCCESS CRITERIA**

**You have succeeded when:**
- All 85 agents can start without crashing
- Health checks pass for running agents
- Cross-machine service discovery works
- Dependency chains resolve correctly
- Configuration validation passes

**Background Agent: Use this checklist to guide your comprehensive analysis. Focus on finding real issues, not creating assumed solutions.** 