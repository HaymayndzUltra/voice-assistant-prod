# 🎯 PHASE 1 ACTION PLAN: STANDARDIZATION

## 📅 TIMELINE: Weeks 1-4

## 🎯 FOCUS: PATH MANAGEMENT & BASEAGENT MIGRATION

### **SCOPE**
Standardize path management across all agents and migrate remaining legacy agents to BaseAgent pattern.

### **RISKS ADDRESSED**
- D: Partial BaseAgent adoption (29/77 agents bypass health checks)
- E: File-based logging race (77 agents, no rotation, disk quota risk)
- H: Security leakage (NATS credentials in YAML → ps aux visible)

---

## 📋 PLACEHOLDER - DETAILED PLAN TO BE CREATED

**STATUS**: 🔄 AWAITING PHASE 0 COMPLETION + DETAILED PLANNING

**PREREQUISITES**: Phase 0 successfully completed and validated

**NEXT ACTION**: After Phase 0 completion, re-read Background Agent guide and create detailed Week 1-4 implementation plan.

### **PLANNED DELIVERABLES**
- [ ] Path management standardization (shim path_env → PathManager)
- [ ] CI enforcement rules for path patterns
- [ ] Remaining 24 legacy agents → BaseAgent migration
- [ ] Templated health mixin for old agents
- [ ] Comprehensive logging rotation across all 77 agents

### **SUCCESS CRITERIA**
- 100% agents inherit from BaseAgent or use health shim
- Unified path management across all agents
- Log rotation active, disk usage under control
- Zero credential leaks in production environment

---

**⚠️ AWAITING PHASE 0 COMPLETION TO PROCEED** 