# QUICK REFERENCE CARD - Agent Consolidation
## Mga Pinaka-importanteng Reminder

### 🚨 BAGO KA MAGSIMULA NG KAHIT ANO:

```
ASK YOURSELF:
1. Na-extract ko na ba ang ACTUAL CODE?
2. Naintindihan ko na ba ang BAWAT method?
3. May test cases na ba ako?
4. May rollback plan na ba?
```

### 📋 CORRECT CONSOLIDATION FLOW:

```
1. EXTRACT → Read actual source code
2. ANALYZE → Understand every method
3. MAP → Document all dependencies  
4. MERGE → Combine actual logic (NOT generic)
5. TEST → Shadow mode first
6. MIGRATE → Gradual traffic shift
7. VALIDATE → Compare all outputs
8. CLEANUP → Only after validation
```

### ⚠️ RED FLAGS - STOP IF YOU SEE:

```python
# MALI - Generic implementation
def route_task(self, task):
    return {"status": "routed"}  # NO ACTUAL LOGIC!

# TAMA - Actual logic preserved
def _calculate_priority(self, task_type, request):
    # From RequestCoordinator line 524
    base_priority = {
        'audio_processing': 1,
        'text_processing': 2,
        'vision_processing': 3,
        'background_task': 5
    }
    # ... actual calculation logic
```

### 🎯 GOLDEN RULES:

1. **EXTRACT FIRST** - Wag implement agad
2. **PRESERVE EVERYTHING** - Every method, every algorithm
3. **TEST IN PARALLEL** - Old & new together
4. **GRADUAL MIGRATION** - 5% → 25% → 50% → 100%
5. **INSTANT ROLLBACK** - One command to revert

### 🔧 EMERGENCY COMMANDS:

```bash
# ROLLBACK NOW
sed -i 's/TaskRouter/RequestCoordinator/g' main_pc_code/config/startup_config.yaml
sed -i 's/HealthSuite/PredictiveHealthMonitor/g' main_pc_code/config/startup_config.yaml
systemctl restart ai-agents

# CHECK SYSTEM HEALTH
curl http://localhost:7100/health
curl http://localhost:26002/health
tail -f logs/*error*.log

# VERIFY ROLLBACK
grep -r "TaskRouter" --include="*.yaml" . | wc -l  # Should be 0
```

### 📊 VALIDATION METRICS:

```
BEFORE DECLARING SUCCESS:
□ Error rate < 0.1%? 
□ Response time same or better?
□ All endpoints responding?
□ No memory leaks?
□ 24-hour stable run?
□ Rollback tested?
```

### 💡 REMEMBER:

**"Hindi speed ang importante - ACCURACY ang kailangan!"**

Better to take 1 month and do it right than 1 week and break production.

---

## TEMPLATE UTOS PARA SA AI:

**EXTRACTION:**
```
"Show me the COMPLETE source code of [agent_name], not a summary. I need to see every method, every algorithm, every data structure."
```

**IMPLEMENTATION:**
```
"Create [consolidated_agent] using the EXACT logic extracted from [list of agents]. Do not create generic methods - use the actual code we extracted."
```

**VALIDATION:**
```
"Compare the output of [new_agent] vs [old_agents] for these test cases: [list]. Show me any differences."
```

---

Print this and keep it beside you during implementation! 🎯 