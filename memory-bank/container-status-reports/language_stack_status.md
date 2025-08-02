# Language Stack Group - Container Status Report
**Report Generated:** 2025-08-02 16:16:30

## Group Overview
- **Total Containers:** 12
- **Healthy:** 2
- **Unhealthy:** 3
- **Restarting:** 5
- **Stopped:** 1
- **Created but not started:** 1

## ✅ HEALTHY CONTAINERS

### proactive_agent
- **Status:** Up 3 seconds (health: starting)
- **Ports:** 0.0.0.0:5595->5595/tcp, 0.0.0.0:6595->6595/tcp
- **Issue:** None - Starting normally

### model_orchestrator
- **Status:** Up 20 seconds (health: starting)
- **Ports:** 0.0.0.0:5594->5594/tcp, 0.0.0.0:6594->6594/tcp
- **Issue:** None - Starting normally

## ⚠️ UNHEALTHY CONTAINERS (Running but failing health checks)

### dynamic_identity_agent
- **Status:** Up 8 hours (unhealthy)
- **Ports:** 0.0.0.0:5591->5591/tcp, 0.0.0.0:6591->6591/tcp
- **Issue:** SystemDigitalTwin communication failure, but agent is functional

**Logs:**
```
Timeout waiting for response from SystemDigitalTwin (attempt 1/3)
Timeout waiting for response from SystemDigitalTwin (attempt 2/3)
Timeout waiting for response from SystemDigitalTwin (attempt 3/3)
Failed to register with SystemDigitalTwin: Failed to communicate with SystemDigitalTwin after 3 attempts. Will continue without registration.
{"timestamp": "2025-08-01T23:55:12Z", "level": "INFO", "agent": "DynamicIdentityAgent", "message": "DynamicIdentityAgent started successfully"}
```

### intention_validator
- **Status:** Up 8 hours (unhealthy)
- **Ports:** 0.0.0.0:5586->5586/tcp, 0.0.0.0:6586->6586/tcp
- **Issue:** NATS service unavailable + SystemDigitalTwin communication failure

**Logs:**
```
Failed to setup streams: nats: ServiceUnavailableError: code=None err_code=None description='None'
Timeout waiting for response from SystemDigitalTwin (attempt 1/3)
Timeout waiting for response from SystemDigitalTwin (attempt 2/3)
Timeout waiting for response from SystemDigitalTwin (attempt 3/3)
Failed to register with SystemDigitalTwin: Failed to communicate with SystemDigitalTwin after 3 attempts. Will continue without registration.
{"timestamp": "2025-08-01T23:55:11Z", "level": "INFO", "agent": "IntentionValidatorAgent", "message": "IntentionValidatorAgent started successfully"}
```

### nlu_agent
- **Status:** Up 8 hours (unhealthy)
- **Ports:** 0.0.0.0:5585->5585/tcp, 0.0.0.0:6585->6585/tcp
- **Issue:** Similar NATS and SystemDigitalTwin connectivity issues

## ⚠️ RESTARTING CONTAINERS (Module not found errors)

### goal_manager
- **Status:** Restarting (1) 46 seconds ago
- **Issue:** Missing GoalManager module
- **Error:** `/usr/local/bin/python: No module named main_pc_code.agents.GoalManager`

### feedback_handler
- **Status:** Restarting (1) 43 seconds ago
- **Issue:** Missing FeedbackHandler module
- **Error:** `/usr/local/bin/python: No module named main_pc_code.agents.FeedbackHandler`

### advanced_command_handler
- **Status:** Restarting (1) 1 second ago
- **Issue:** Missing AdvancedCommandHandler module
- **Error:** `/usr/local/bin/python: No module named main_pc_code.agents.AdvancedCommandHandler`

### emotion_synthesis_agent
- **Status:** Restarting (1) 49 seconds ago
- **Issue:** Missing EmotionSynthesisAgent module

### chitchat_agent
- **Status:** Restarting (1) 36 seconds ago
- **Issue:** Missing ChitchatAgent module

## ❌ STOPPED/NOT STARTED CONTAINERS

### responder
- **Status:** Created (not started)
- **Issue:** Container created but never started

## Root Cause Analysis

### 1. Missing Agent Modules
- **GoalManager, FeedbackHandler, AdvancedCommandHandler** modules don't exist
- **EmotionSynthesisAgent, ChitchatAgent** modules missing
- Incorrect module paths in docker-compose.yml

### 2. Infrastructure Communication Issues
- **SystemDigitalTwin** not responding (affecting registration)
- **NATS** service unavailable errors
- **Health checks failing** due to external service dependencies

### 3. Container Orchestration Issues
- Some containers created but not started properly

## Required Fixes

### Module Path Issues:
1. Verify actual agent file names and module paths
2. Update docker-compose.yml with correct module imports
3. Create missing agent files or use placeholder modules

### Infrastructure Issues:
1. Fix NATS connectivity between language_stack and other groups
2. Ensure SystemDigitalTwin is accessible and responding
3. Review health check configurations

### Container Management:
1. Start stopped containers manually
2. Fix restart loop by resolving module issues

## Summary
Language Stack group is 17% functional. Major module path issues and infrastructure connectivity problems need resolution.
