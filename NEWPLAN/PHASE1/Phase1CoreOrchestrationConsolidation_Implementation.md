# PHASE 1: Core Orchestration Consolidation - Detailed Implementation Plan

## 1. Executive Summary

Phase 1 focuses on consolidating the core orchestration components of our system to reduce redundancy, clarify responsibility boundaries, and improve maintainability. This phase addresses critical architectural issues by merging related agents with overlapping functionality.

Key consolidations:
- **RequestCoordinator**: Merges CoordinatorAgent and TaskRouter
- **ModelOrchestrator**: Merges EnhancedModelRouter and UnifiedPlanningAgent
- **GoalManager**: Merges GoalOrchestratorAgent and MultiAgentSwarmManager

These consolidations will create a cleaner hierarchical structure with clear separation of concerns while preserving all essential functionality.

## 2. Critical Functional Requirements

### 2.1 RequestCoordinator (CoordinatorAgent + TaskRouter merger)

The RequestCoordinator must preserve ALL of these critical functions:

#### From CoordinatorAgent:
- Receiving and processing user requests (text/audio/vision)
- Memory storage and retrieval operations
- User session management
- Basic request routing
- User interruption handling
- Proactive suggestion processing

#### From TaskRouter:
- Advanced priority-based task queuing
- Circuit breaker pattern implementation for resilient connections
- Service discovery integration
- Comprehensive error handling and reporting
- Task categorization and routing
- Dynamic agent selection based on task requirements
- Request timeout management
- Response processing and formatting

### 2.2 ModelOrchestrator (EnhancedModelRouter + UnifiedPlanningAgent merger)

The ModelOrchestrator must preserve ALL of these critical functions:

#### From EnhancedModelRouter:
- Task classification and routing
- Context-aware prompting via Context Summarizer
- Chain-of-Thought integration for complex reasoning
- Multi-step reasoning capabilities
- Model selection based on task characteristics
- Context management for conversations
- Interaction recording for memory
- Multiple socket polling for efficient communication

#### From UnifiedPlanningAgent:
- Decomposition of complex tasks into executable steps
- Comprehensive planning for multi-step processes
- Iterative code generation and refinement process
- Code verification capabilities
- Safe code execution in controlled environments
- Plan verification and adaptation
- Dynamic dependency resolution in plans
- Error handling and recovery for long-running plans

### 2.3 GoalManager (GoalOrchestratorAgent + MultiAgentSwarmManager merger)

The GoalManager must preserve ALL of these critical functions:

#### From GoalOrchestratorAgent:
- High-level goal tracking and management
- Task dependency resolution
- Progress monitoring and reporting
- Goal prioritization and scheduling
- Goal state persistence
- Task status updates

#### From MultiAgentSwarmManager:
- Agent capability discovery
- Agent team composition for complex tasks
- Distributed task assignment and monitoring
- Cross-agent coordination
- Result aggregation from multiple agents
- Resource allocation for agent teams
- Dynamic agent recruitment based on task needs

## 3. Implementation Steps

### 3.1 RequestCoordinator Implementation

1. **Create baseline structure**:
   - Start with BaseAgent implementation
   - Add ZMQ socket initialization for all required connections
   - Implement basic request handling loop

2. **Add core request handling**:
   - Implement handlers for text, audio, and vision requests
   - Add standardized data models using Pydantic for request/response

3. **Implement circuit breaker pattern**:
   - Add CircuitBreaker class from TaskRouter
   - Integrate with all external service connections
   - Add service health monitoring

4. **Implement advanced task queuing**:
   - Add priority-based task queue using heapq
   - Implement task dispatcher thread
   - Add task status tracking

5. **Integrate memory operations**:
   - Add connection to MemoryClient
   - Implement memory storage methods
   - Add context retrieval functionality

6. **Add standardized error reporting**:
   - Implement Error Bus integration
   - Add comprehensive error categorization
   - Implement error recovery strategies

7. **Implement additional features**:
   - Add proactive suggestion handling
   - Implement interrupt listener
   - Add inactivity detection

8. **Add health check and monitoring**:
   - Implement health check endpoints
   - Add resource usage monitoring
   - Implement service discovery registration

### 3.2 ModelOrchestrator Implementation

1. **Create baseline structure**:
   - Start with BaseAgent implementation
   - Add ZMQ socket initialization for all required connections
   - Implement basic request handling loop

2. **Implement task classification**:
   - Add detect_task_type function
   - Implement rules-based and LLM-based classification
   - Add task routing based on classification

3. **Add context management**:
   - Implement conversation history tracking
   - Add context retrieval from memory services
   - Implement context-aware prompting

4. **Implement specialized tool integration**:
   - Add connections to Chain-of-Thought agent
   - Implement Tree-of-Thought integration
   - Add connections to web and code agents

5. **Add code generation capabilities**:
   - Implement iterative code generation flow
   - Add code verification functionality
   - Implement safe code execution environment

6. **Implement planning capabilities**:
   - Add plan generation functionality
   - Implement plan validation
   - Add plan execution and monitoring

7. **Add comprehensive error handling**:
   - Implement Error Bus integration
   - Add fallback mechanisms for service failures
   - Implement error recovery strategies

8. **Add health check and monitoring**:
   - Implement health check endpoints
   - Add resource usage monitoring
   - Implement service discovery registration

### 3.3 GoalManager Implementation

1. **Create baseline structure**:
   - Start with BaseAgent implementation
   - Add ZMQ socket initialization for all required connections
   - Implement basic request handling loop

2. **Implement goal management**:
   - Add goal tracking data structures
   - Implement goal creation and status tracking
   - Add goal prioritization

3. **Add task management**:
   - Implement task dependency tracking
   - Add task assignment functionality
   - Implement task status updates

4. **Implement agent management**:
   - Add agent discovery functionality
   - Implement agent capability tracking
   - Add agent team composition

5. **Add progress monitoring**:
   - Implement goal progress tracking
   - Add task completion monitoring
   - Implement notification system for goal status changes

6. **Add comprehensive error handling**:
   - Implement Error Bus integration
   - Add fallback mechanisms for agent failures
   - Implement error recovery strategies

7. **Add health check and monitoring**:
   - Implement health check endpoints
   - Add resource usage monitoring
   - Implement service discovery registration

## 4. File Structure Updates

After implementing Phase 1, the file structure should look like this:

```
main_pc_code/
  agents/
    request_coordinator.py  (merged CoordinatorAgent + TaskRouter)
    model_orchestrator.py   (merged EnhancedModelRouter + UnifiedPlanningAgent)
    goal_manager.py         (merged GoalOrchestratorAgent + MultiAgentSwarmManager)
    _archive/               (place original agents here for reference)
      coordinator_agent.py
      task_router.py
      enhanced_model_router.py
      unified_planning_agent.py
      goal_orchestrator_agent.py
      multi_agent_swarm_manager.py
```

## 5. Configuration Updates

The following configuration files must be updated to reflect the new consolidated agents:

1. **main_pc_code/config/startup_config.yaml**:
   - Remove entries for CoordinatorAgent, TaskRouter, EnhancedModelRouter, UnifiedPlanningAgent, GoalOrchestratorAgent, MultiAgentSwarmManager
   - Add entries for RequestCoordinator, ModelOrchestrator, GoalManager
   - Update all dependencies references to use new agent names

2. **NEWPLAN/ALLINFOMAINAGENTS2_ORDERED.MD**:
   - Update agent documentation to reflect the new consolidated agents
   - Remove entries for merged agents
   - Add detailed descriptions of the new agents' responsibilities

3. **main_pc_code/config/agent_ports.py**:
   - Update port assignments for the new consolidated agents
   - Remove port definitions for the merged agents

4. **Any scripts that launch agents directly**:
   - Update to use the new agent paths and names

## 6. Reference Agents Code

### 6.1 CoordinatorAgent
```python
# PASTE ORIGINAL CoordinatorAgent CODE HERE
```

### 6.2 TaskRouter
```python
# PASTE ORIGINAL TaskRouter CODE HERE
```

### 6.3 EnhancedModelRouter
```python
# PASTE ORIGINAL EnhancedModelRouter CODE HERE
```

### 6.4 UnifiedPlanningAgent
```python
# PASTE ORIGINAL UnifiedPlanningAgent CODE HERE
```

### 6.5 GoalOrchestratorAgent
```python
# PASTE ORIGINAL GoalOrchestratorAgent CODE HERE
```

### 6.6 MultiAgentSwarmManager
```python
# PASTE ORIGINAL MultiAgentSwarmManager CODE HERE
```

## 7. Critical Logic Reference

### 7.1 RequestCoordinator Critical Logic

```python
# Key methods from CoordinatorAgent that MUST be preserved:
def _process_text(self, request):
    # Logic for processing text requests...

def _process_audio(self, request):
    # Logic for processing audio requests...

def _process_vision(self, request):
    # Logic for processing vision requests...

# Key methods from TaskRouter that MUST be preserved:
class CircuitBreaker:
    # Circuit breaker implementation...

def _route_task(self, task):
    # Task routing logic...

def _handle_response(self, response):
    # Response processing logic...
```

### 7.2 ModelOrchestrator Critical Logic

```python
# Key methods from EnhancedModelRouter that MUST be preserved:
def detect_task_type(self, prompt):
    # Task classification logic...

def get_context_summary(self, user_id, project, max_tokens):
    # Context retrieval logic...

def record_interaction(self, interaction_type, content, user_id, project, metadata):
    # Interaction recording logic...

# Key methods from UnifiedPlanningAgent that MUST be preserved:
def _generate_solution_for_step(self, step, context):
    # Solution generation logic...

def _verify_solution(self, solution, requirements):
    # Solution verification logic...

def _execute_code(self, code, language, timeout):
    # Safe code execution logic...
```

### 7.3 GoalManager Critical Logic

```python
# Key methods from GoalOrchestratorAgent that MUST be preserved:
def set_goal(self, goal_data):
    # Goal creation logic...

def update_task_status(self, goal_id, task_id, status):
    # Task status update logic...

def get_goal_status(self, goal_id):
    # Goal status retrieval logic...

# Key methods from MultiAgentSwarmManager that MUST be preserved:
def _discover_agents(self):
    # Agent discovery logic...

def _select_agents_for_task(self, task):
    # Agent selection logic...

def _coordinate_agents(self, task, agents):
    # Agent coordination logic...
```

## 8. Testing Strategy

### 8.1 Unit Testing
- Create unit tests for each critical function in the consolidated agents
- Test circuit breaker functionality in isolation
- Test task classification with various inputs
- Test goal breakdown with sample goals

### 8.2 Integration Testing
- Test RequestCoordinator with ModelOrchestrator
- Test ModelOrchestrator with GoalManager
- Test the full request flow from receipt to completion

### 8.3 System Testing
- End-to-end test with text, audio, and vision inputs
- Test error scenarios and recovery
- Test with high load to verify performance

### 8.4 Verification Checklist
- All critical functionality is preserved
- Performance is equal to or better than previous implementation
- Error handling covers all critical failure modes
- Configuration is properly updated in all places

## 9. Post-Implementation Verification

After implementing all consolidations, verify the following:

1. All agents start successfully without dependency errors
2. System can process all request types (text, audio, vision)
3. Task routing functions correctly based on task type
4. Circuit breakers operate as expected when services fail
5. Goals are properly tracked and decomposed into tasks
6. Error reporting works for all critical error types
7. Memory operations function correctly
8. All documentation is updated to reflect new structure

## 10. Rollback Plan

In case of critical issues during implementation:

1. Keep a full backup of all original agent code
2. Maintain copies of all configuration files before modification
3. Document a step-by-step rollback procedure
4. Test the rollback procedure before implementing changes 