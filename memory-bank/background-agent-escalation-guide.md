# Background Agent Escalation Guide - Complete Strategy

## WHEN USER SAYS "GAMITIN SI BACKGROUND AGENT"

### CRITICAL UNDERSTANDING:
- Background Agent = EXPENSIVE (200k+ context window)
- Need EFFICIENT problem reporting + SMART guidance
- NOT generic templates - SPECIFIC problem context needed
- Focus on ACTIVE agents via startup_config.yaml references

---

## ESCALATION PROMPT STRUCTURE

### 1. PROBLEM STATE REPORTING
```
CURRENT PROBLEM: [Specific issue description]
WHAT I TRIED: [Actions attempted]
OUTPUT/RESULT: [Actual results/errors]
SYSTEM STATE: [Before issue started]
TIMING: [When issue began]
RECENT CHANGES: [Recent deployments/modifications]
```

### 2. SMART SCOPING GUIDANCE
```
PRIMARY SCOPE: Focus on [ProblemAgent] and its dependencies from @startup_config.yaml
ENVIRONMENT: MainPC agents per @main_pc_code/config/startup_config.yaml (54 agents)
CROSS-CHECK: PC2 interactions per @pc2_code/config/startup_config.yaml (23 agents)
```

### 3. INVESTIGATION LEVELS
```
Level 1: Direct agent + immediate dependencies
Level 2: Agent group (e.g., speech_services, core_services)
Level 3: Cross-cutting concerns (memory_system, gpu_infrastructure)
Level 4: System-wide patterns and resource conflicts
```

### 4. CONTEXT PREPARATION
```
RESOURCE UTILIZATION: Current CPU/Memory/GPU usage patterns
INTER-AGENT COMMUNICATION: Recent logs between related agents
DEPENDENCY CHAIN: Full dependency tree from startup_config.yaml
ENVIRONMENT CONFLICTS: MainPC vs PC2 resource sharing issues
```

---

GAGAMITIN LANG ITO KAPAG ANG USER AY NAG SABI O NAG UTOS NA GAGAMITIN SI BACKGROUND AGENT!
#PALIWANAG PARA SAYO (AGENT MODE)


# Cursor AI: Agent Mode vs Background Agent Capabilities

---

## 1. Agent Mode (Cursor) (You)

**Overview:**

* Agent Mode (You) is the standard, interactive Cursor AI mode.
* Runs locally or in the cloud, focused on user-triggered actions, edits, or commands.
* Context window usually limited to selected files or visible code.

**Capabilities:**

* Step-by-step code edits, refactoring, or generation based on explicit user prompts.
* Can run code actions (e.g., lint, format, single-command debug) with user approval.
* Can highlight detected issues and recommend direct fixes.
* Useful for quick, focused code tasks or micro-fixes.
* Limited context awareness (often only knows what's visible or selected).
* One action/task at a time; no real parallelism.

**Limitations vs Background Agent:**

* Does not see the whole project/codebase at once.
* Cannot run deep, autonomous analysis or parallel long-running tasks.
* May forget context or loop if prompt is unclear or too large in scope.
* Relies on the user for context and instruction details.

**Best Use Cases:**

* Editing current file or selected files.
* Refactoring small code snippets.
* Fixing quick bugs or applying linters.

**IMPORTANT:**

* Agent Mode (You) must be aware that Background Agent exists with much broader capabilities (see section below).
* For deep debugging, multi-file refactoring, or system-wide analysis, Agent Mode should escalate the task to a Background Agent with a general/system-level instruction.

---

## 2. Background Agent (Cursor)

**Overview:**

* Background Agents run in a separate remote environment (cloud/Docker), parallel to your IDE.
* They operate autonomously, capable of handling multiple parallel tasks and using much larger context windows (including Max Mode and top models).

**Capabilities:**

* Analyze the entire codebase/project, not just open files.
* Full context understanding: sees relationships, dependencies, and project architecture.
* Can refactor, debug, or generate code/features across multiple files or even the entire repository.
* Handles large tasks: deep bug tracing, system-wide PR creation, auto documentation, code pattern analysis, test writing, config checks, and even deployment scripting.
* Can run asynchronously (in the background), generating summaries, PRs, and reports without direct user supervision.
* Can auto-branch, create PRs, and even trigger automated QA using integrations (like BugBot).

**Best Use Cases:**

* Project-wide debugging and refactoring.
* Large feature implementation or refactor chains.
* Full system/codebase analysis (context window up to 200k tokens or more in Max Mode).
* Generating or reviewing documentation/tests at scale.

**Key Difference from Agent Mode (You):**

* Background Agent works system-wide and in parallel; Agent Mode (You) is local and sequential.
* Background Agent has greater autonomy and project understanding, making it ideal for general, cross-cutting concerns and improvements.

---

## 3. How Agent Mode (You) Should Prompt Background Agent

**Whenever Agent Mode (You) encounters an issue or a task that is broad, complex, or may involve multiple files or systemic investigation, the prompt for Background Agent should always be general and not tied only to the visible/specific file.**

**Prompt Template:**


```
Instructions:
- Analyze the root cause of this problem.
- Check for other similar or related issues elsewhere in the codebase or system.
- Suggest fixes for this and any related problems you find.
- Recommend system-wide improvements to prevent this type of issue in the future.

[ALWAYS REMIND THE SOT OF AGENTS IN MAINPC mainpc_code_/config/startup_config.yaml , SOT AGENTS IN PC2 pc2_code/config/startup_config.yaml PUT THIS AT THE TOP OF PROMPT/COMMAND]
```

**Summary:**

* Agent Mode (You) = Fast, interactive, for small/local code actions.
* Background Agent = Autonomous, parallel, for deep/system-wide tasks.
* Agent Mode (You) should defer to Background Agent for any job requiring full project context or multi-file reasoning.

---

## USAGE EXAMPLES

### Example 1: Agent Crash Issue
```
CURRENT PROBLEM: StreamingTTSAgent keeps crashing during startup
WHAT I TRIED: Restarted agent, checked basic logs, verified dependencies
OUTPUT/RESULT: Agent starts but crashes after 30 seconds with "connection timeout"
INVESTIGATION SCOPE: StreamingTTSAgent + dependencies (TTSService, SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent)
```

### Example 2: Performance Degradation  
```
CURRENT PROBLEM: System response time increased from 2s to 15s
WHAT I TRIED: Checked individual agent health, restarted core services
OUTPUT/RESULT: All agents show "healthy" but overall system sluggish
INVESTIGATION SCOPE: Full speech_services + memory_system groups from startup_config.yaml
```

### Example 3: Cross-Machine Communication Issue
```
CURRENT PROBLEM: MainPC-PC2 synchronization failing intermittently
WHAT I TRIED: Network connectivity tests, service restarts
OUTPUT/RESULT: 30% of requests between machines timeout
INVESTIGATION SCOPE: Cross-environment analysis of both startup_config.yaml files
```

---

## COST OPTIMIZATION STRATEGIES

### 1. START NARROW, EXPAND IF NEEDED
- Begin with direct agent + immediate dependencies
- Escalate to group level only if initial scope insufficient
- System-wide analysis only for cross-cutting issues

### 2. CLEAR STOP CONDITIONS
- Define success criteria for investigation
- Set time boundaries for analysis
- Specify minimum vs comprehensive reporting levels

### 3. INTEGRATION WITH TASK AUTOMATION
- Store Background Agent results in task state
- Track investigation history to prevent duplicates
- Enable resume capability for incomplete investigations

---

## FEEDBACK LOOP PROCESS

### 1. VALIDATION OF FINDINGS
- How to verify Background Agent analysis
- Testing recommendations before implementation
- Rollback strategies if solutions don't work

### 2. IMPLEMENTATION TRACKING
- Step-by-step execution of action plans
- Progress monitoring and success metrics
- Documentation of what worked vs what didn't

### 3. LEARNING INTEGRATION
- Update system knowledge with new insights
- Improve future problem detection
- Enhance escalation strategies based on results

---

## SESSION CONTINUITY

Every AI session must understand:
1. Background Agent is expensive - use efficiently
2. Provide problem context, not solutions
3. Use startup_config.yaml for smart scoping
4. Expect comprehensive reports with action plans
5. Cost-optimize by starting narrow and expanding
6. Integrate results with task automation system

---

## IMPLEMENTATION STATUS

- ✅ Complete escalation template defined
- ✅ Multi-level investigation strategy established
- ✅ Cost optimization guidelines created
- ✅ Integration with task automation planned
- ✅ Session continuity ensured via memory bank

*This guide ensures maximum value from expensive Background Agent capabilities while maintaining cost efficiency and comprehensive problem resolution.* 