# GEMINI + CURSOR AI WORKFLOW: SYSTEM MONOREPO MANAGEMENT
=======================================================

## 🔍 STRATEGY OVERVIEW:
- Si Gemini ang "brain" (planner, memory, instruction generator)
- Si Cursor (Claude 3.7 Sonnet) ang "executor" (coding, debugging, automation)
- Lahat ng context, requirements, at instructions ay dapat explicit at self-contained
- "Trust but verify" approach: hayaan si Cursor mag-decide ng best implementation, pero laging may malinaw na goal at success criteria

## 🛠️ INITIAL PROJECT ASSESSMENT CHECKLIST:
Sa bagong session, unang ipagawa kay Cursor ang mga sumusunod para magkaroon ng clear understanding sa project:

1. **Check Repository Structure:**
   ```
   find /home/haymayndz/AI_System_Monorepo -type d -name "agents" | sort
   find /home/haymayndz/AI_System_Monorepo -type d -name "src" | sort
   ```

2. **Check Agent Inventory Status:**
   ```
   head -n 5 /home/haymayndz/AI_System_Monorepo/master_agent_list.csv
   wc -l /home/haymayndz/AI_System_Monorepo/master_agent_list.csv
   grep -c "PENDING\|FAIL\|SUCCESS" /home/haymayndz/AI_System_Monorepo/master_agent_list.csv
   ```

3. **Check Configuration Files:**
   ```
   ls -la /home/haymayndz/AI_System_Monorepo/main_pc_code/config/
   ls -la /home/haymayndz/AI_System_Monorepo/pc2_code/config/
   head -n 20 /home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml
   ```

4. **Check Available Scripts:**
   ```
   ls -la /home/haymayndz/AI_System_Monorepo/scripts/
   ```

5. **Check Recent Work:**
   ```
   find /home/haymayndz/AI_System_Monorepo -type f -name "*.py" -mtime -2 | sort
   ```

6. **Check System Requirements:**
   ```
   cat /home/haymayndz/AI_System_Monorepo/main_pc_code/_DOCUMENTSFINAL/system_overview.md
   ```

## 🎯 BAKIT EFFECTIVE ANG STRATEGY NA ITO:
- Division of labor: Gemini = strategic planning, Cursor = technical execution
- Source of truth management: Gemini ang knowledge base, Cursor ang worker
- Bridging the gap: Nililinaw muna ni Gemini ang instructions bago ipasa kay Cursor
- Awareness of model limitations: Alam na walang persistent memory si Cursor, kaya inuulit lahat ng context

## 🚀 MAJOR BENEFITS:
- Mas mabilis at accurate ang project completion
- Bawas trial-and-error
- Consistent workflow kahit bagong session
- Autonomous pero controlled execution

## ⚠️ POTENTIAL ISSUES AT SOLUSYON:
- **Hallucination Risk**: Cursor may create fictional reports or solutions
  - **Solusyon**: Require specific verification outputs (e.g., exact command outputs, screenshots)
  - **Solusyon**: Hatiin ang complex tasks sa smaller steps na may verification checkpoints
  - **Solusyon**: Maglagay ng "VERIFICATION REQUIRED" sections sa instructions

- **Inefficient Serial Processing**: One-by-one agent verification is too slow
  - **Solusyon**: Create batch processing scripts that can test multiple agents simultaneously
  - **Solusyon**: Automate CSV updates instead of manual editing for each agent

- **Unclear Instructions**: Ambiguous tasks lead to incorrect implementations
  - **Solusyon**: Use structured templates with clear ACTION vs EXPECTED OUTPUT sections
  - **Solusyon**: Always specify verification methods and success criteria

## 🧠 SYSTEM ARCHITECTURE OVERVIEW:
- MainPC (RTX 4090, 24GB VRAM): Core agents, audio/video processing, primary UI
- PC2 (RTX 3060, 12GB VRAM): Memory services, web agents, digital twin
- Distributed architecture: Agents communicate via ZMQ sockets
- Configuration management: YAML files for startup, JSON for runtime config
- Health monitoring: All agents have health check endpoints

## 📊 CURRENT SYSTEM STATUS:
- **Agent Inventory**: Completed - 88 total agents cataloged (59 MainPC, 29 PC2)
- **Agent Health Verification**: In progress - 5 FAIL, 0 SUCCESS, 83 PENDING
- **Next Task**: Create automated batch verification script to accelerate testing
- **Target**: Containerize verified agents using Podman

## 📝 OPTIMIZED INSTRUCTION TEMPLATE FOR CURSOR:

```
### TASK: [Clear task title]

**CONTEXT:**
- Current status: [Brief summary of where we are]
- Relevant files: [List of key files involved]
- System components: [Which part of system is affected - MainPC/PC2]

**ACTION STEPS:**
1. **[Step 1 Title]**
   - **ACTION:** [Specific action for Cursor to take]
   - **VERIFICATION:** [How to verify this step was completed correctly]
   - **OUTPUT:** [What Cursor should show after this step]

2. **[Step 2 Title]**
   - **ACTION:** [Specific action for Cursor to take]
   - **VERIFICATION:** [How to verify this step was completed correctly]
   - **OUTPUT:** [What Cursor should show after this step]

**DELIVERABLES:**
- [Specific file or output expected]
- [Any changes that should be made]

**SUCCESS CRITERIA:**
- [How to know the task is complete]
- [Specific tests or checks to run]

**PERMISSIONS:**
- [What Cursor is allowed to modify]
- [What requires confirmation before proceeding]
```

## 📂 PRIORITY TASKS:

### 1. SYSTEM-WIDE AGENT CONFIGURATION LOADING STANDARDIZATION (IN PROGRESS)
**TASK:** Audit and standardize how all agents load their configuration for maintainability and robustness.

**CONTEXT:**
- Phase 2 of system refactor: Standardization
- Goal: All agents must use `parse_agent_args` for config, eliminate hardcoded values, and follow a single pattern
- Relevant files: All agent scripts listed in `main_pc_code/config/startup_config.yaml`
- System components: MainPC and PC2 agents

**ACTION STEPS:**
1. **Audit All Agent Config Loading**
   - **ACTION:** For each agent, check if it uses `parse_agent_args`, has canonical import, no hardcoded config, and passes config to `super().__init__`.
   - **VERIFICATION:** Generate a per-agent checklist (see template below) and fill for all agents.
   - **OUTPUT:** Copy-friendly checklist table with compliance status for each agent.

2. **Propose and Document Standardization Plan**
   - **ACTION:** Summarize findings and propose a step-by-step plan for standardization.
   - **VERIFICATION:** Plan is clear, actionable, and covers all edge cases.
   - **OUTPUT:** Block-formatted standardization plan and agent config template.

3. **Refactor Non-Compliant Agents**
   - **ACTION:** For each non-compliant agent, refactor to follow the standard config loading pattern.
   - **VERIFICATION:** Show code diff for each refactor and run agent health check script.
   - **OUTPUT:** Code diffs and health check results for each agent.

4. **Automate Compliance Checking**
   - **ACTION:** Implement a linter/CI rule to enforce config loading standards for all agents.
   - **VERIFICATION:** Linter/CI fails on non-compliant agents, passes on compliant ones.
   - **OUTPUT:** Linter/CI script and sample output.

**DELIVERABLES:**
- Per-agent compliance checklist (table)
- Standardization plan and config template
- Refactored agent scripts
- Linter/CI rule for config loading

**SUCCESS CRITERIA:**
- 100% of agents use the standard config loading pattern
- No hardcoded config values remain in agent classes
- Linter/CI enforces compliance for all future changes

**PERMISSIONS:**
- Cursor may analyze and refactor all agent scripts
- Major refactors or changes to shared utilities require Gemini approval

**VERIFICATION REQUIRED:**
- All checklist items must be filled and verified for each agent
- All code changes must be shown and tested

**CHECKLIST TEMPLATE:**
| Agent Name | Script Path | parse_agent_args | Canonical Import | All Config from _agent_args | No Hardcoded Values | Passes to super() |
|------------|------------|------------------|------------------|----------------------------|---------------------|-------------------|
| ...        | ...        | [ ]              | [ ]              | [ ]                        | [ ]                 | [ ]               |

---

<!--
### 2. CREATE AUTOMATED AGENT VERIFICATION SYSTEM
### 3. CONTAINERIZE VERIFIED AGENTS
(These tasks are commented out to avoid confusion. Focus only on agent config standardization for now.)
-->

## BEST PRACTICES FOR CURSOR INSTRUCTIONS:

1. **Always specify verification methods**
   - BAD: "Fix the TaskRouter port conflict"
   - GOOD: "Modify TaskRouter code, then verify by running 'python scripts/verify_agent_health_checks.py TaskRouter' and showing the output"

2. **Provide step-by-step instructions with checkpoints**
   - BAD: "Debug and fix all agent issues"
   - GOOD: "1) Analyze TaskRouter code (show findings), 2) Propose solution (wait for approval), 3) Implement fix (show code changes), 4) Verify fix (show test output)"

3. **Require evidence for all claims**
   - BAD: "Report if the agent is working"
   - GOOD: "Run the health check and include the raw JSON response in your report"

4. **Set clear permission boundaries**
   - BAD: "Fix the system"
   - GOOD: "You may analyze files in src/core/ but do not modify BaseAgent.py without approval"

5. **Use templates for complex tasks**
   - Consistent structure makes instructions clearer
   - Always include context, action steps, verification methods, and success criteria
