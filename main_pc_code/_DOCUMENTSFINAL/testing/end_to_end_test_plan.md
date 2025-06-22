# Voice Assistant End-to-End Test Plan

## Overview

This document outlines the comprehensive end-to-end test plan for the Voice Assistant system. These tests validate that all individual components work together as a single, cohesive system after the completion of the core enhancement plan (Steps 1-15).

## Test Environment Setup

### Prerequisites

- All Docker containers are running (use `docker-compose up -d`)
- PostgreSQL database is properly initialized
- ZMQ CURVE certificates are generated
- Network connectivity between all components is established
- Microphone and speakers are properly configured

### Monitoring Tools

- Terminal windows showing logs from key components:
  - CoordinatorAgent
  - MemoryOrchestrator
  - FusedAudioPreprocessor
  - TaskRouter
- Grafana dashboard accessible at `http://localhost:3000`

## Test Scenarios

### Test Scenario 1: Full Pipeline & Contextual Memory Integrity

#### Objective
To verify that a spoken command flows through the entire enhanced pipeline (Audio > NR/VAD > ASR > Coordinator > Memory > PC2 > Response) and correctly uses context.

#### Setup
- Ensure all core system components are running:
  - FusedAudioPreprocessor
  - VAD Agent
  - CoordinatorAgent
  - MemoryOrchestrator
  - SessionMemoryAgent
  - PC2 Agent
  - TaskRouter
  - HealthMonitor

#### Execution Steps
1. Start the voice assistant system and wait for all components to initialize
2. Verify that the wake word detection is active
3. Trigger the wake word (e.g., "Hey Assistant")
4. When prompted, speak: "What is the capital of the Philippines?"
5. Wait for the complete response
6. After the AI responds, wait 2-3 seconds
7. Without using the wake word again, speak a follow-up: "What is the population there?"
8. Wait for the complete response
9. Check the MemoryOrchestrator logs to verify memory storage and retrieval
10. Check the performance metrics in the logs

#### Expected Outcomes
- The wake word detection should activate the system correctly
- The AI should correctly answer "Manila" to the first question
- The AI should understand that "there" in the second question refers to Manila and provide its population
- The `MemoryOrchestrator` logs should show:
  - The first interaction being stored with a unique memory_id
  - The context being retrieved when processing the second question
  - The relationship between the two questions being established
- The `PERF_METRIC` logs should show:
  - Audio processing time < 500ms
  - ASR processing time < 2 seconds
  - Total response time < 5 seconds
- The conversation should flow naturally without errors or timeouts

### Test Scenario 2: Fault Tolerance & Failover

#### Objective
To verify that the Redundant ZMQ Bridge and the Task Router's Circuit Breaker work as designed.

#### Setup
- Ensure all system components are running, including:
  - Primary and secondary redundant_zmq_bridge instances
  - TaskRouter with Circuit Breaker pattern implemented
  - consolidated_translator on PC2
  - All monitoring components

#### Execution Steps
1. Verify that the system is fully operational by sending a simple request
2. Identify the "active" `redundant_zmq_bridge` container/process by checking the logs
3. Manually kill the "active" `redundant_zmq_bridge` using `docker stop` or process termination
4. Immediately send a request that needs to go to PC2: "Tell me a short story"
5. Monitor the logs to observe the failover process
6. Wait for the system to recover and verify that the passive bridge has taken over
7. Manually kill the `consolidated_translator` container on PC2
8. Send a request that requires translation: "Translate 'hello' to Spanish"
9. Observe the TaskRouter's response and circuit breaker behavior
10. Restart the translator service and verify recovery

#### Expected Outcomes
- The "short story" request should still succeed after a brief delay (under 5 seconds) as the passive bridge takes over
- The system logs should show:
  - Detection of the primary bridge failure
  - Automatic promotion of the secondary bridge to primary
  - Successful routing of the request through the new primary bridge
- The `TaskRouter` logs should show:
  - Circuit breaker "tripping" for the translator service
  - A graceful error message returned to the user
  - No system hang or crash
- After restarting the translator service, the circuit breaker should reset after its timeout period
- Subsequent translation requests should succeed once the service is restored

### Test Scenario 3: Security & Monitoring Validation

#### Objective
To verify that CURVE security is active and that the monitoring stack is receiving data.

#### Setup
- Ensure the system is running with security enabled (`SECURE_ZMQ=1`)
- Prepare a simple Python script that attempts to connect to a ZMQ port without security credentials
- Have access to the Grafana dashboard

#### Execution Steps
1. Create a simple Python script (`test_unsecured_connection.py`) with the following content:
   ```python
   import zmq
   context = zmq.Context()
   socket = context.socket(zmq.REQ)
   socket.connect("tcp://localhost:5570")  # Memory Orchestrator port
   socket.send_json({"action": "read", "payload": {"memory_id": "test"}})
   try:
       socket.recv_json(zmq.NOBLOCK)
       print("Connection succeeded (security issue)")
   except zmq.Again:
       print("Connection timed out (expected with security)")
   ```
2. Run the script: `python test_unsecured_connection.py`
3. Check the MemoryOrchestrator logs for security-related messages
4. Access the Grafana dashboard at `http://localhost:3000` (login with admin/admin if prompted)
5. Navigate to the system metrics dashboard
6. Observe the real-time metrics for at least 5 minutes
7. Make several voice requests to generate metrics data
8. Check the CoordinatorAgent metrics panel specifically

#### Expected Outcomes
- The un-secured connection attempt must:
  - Fail to establish a connection
  - Be rejected by the ZMQ authenticator
  - Generate security warning logs in the MemoryOrchestrator
- The Grafana dashboard should:
  - Successfully connect to Prometheus
  - Display live, updating metrics from the `CoordinatorAgent`
  - Show task latency metrics
  - Display system resource usage (CPU, memory)
  - Show no connection errors to the data source
- The security logs should indicate:
  - CURVE authentication is active
  - Unauthorized connection attempts are being blocked

### Test Scenario 4: Database Migration & Persistence Validation

#### Objective
To verify that the PostgreSQL database migration was successful and that data persists across system restarts.

#### Setup
- Ensure the system is running with the PostgreSQL database
- Have access to database inspection tools (e.g., psql or a database client)

#### Execution Steps
1. Start the voice assistant system if not already running
2. Make several voice interactions that should be stored in memory:
   - "Remember that my favorite color is blue"
   - "What's the weather in Tokyo?"
   - "Set a reminder for tomorrow at 9 AM"
3. Verify that these interactions are logged in the MemoryOrchestrator
4. Stop the entire system: `docker-compose down`
5. Start the system again: `docker-compose up -d`
6. Wait for all services to initialize
7. Ask: "What is my favorite color?"
8. Connect to the PostgreSQL database and inspect the tables:
   ```bash
   docker exec -it voice_assistant_postgres psql -U voiceassistant -d memory_db
   ```
9. Run queries to check the data:
   ```sql
   SELECT * FROM memory_entries ORDER BY created_at DESC LIMIT 10;
   SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;
   ```

#### Expected Outcomes
- The system should correctly recall that your favorite color is blue
- The database inspection should show:
  - Properly structured tables as defined in the schema
  - Memory entries for all the test interactions
  - Session records with appropriate metadata
  - Vector embeddings if semantic search was used
- The data should persist across the system restart
- Query performance should be reasonable (< 100ms for simple queries)
- No database connection errors should appear in the logs

### Test Scenario 5: Multi-Component Integration Test

#### Objective
To verify that all newly implemented components work together correctly, especially focusing on the refactored ModelManagerAgent components and the secure communication layer.

#### Setup
- Ensure all system components are running
- Have access to all component logs

#### Execution Steps
1. Start the voice assistant system if not already running
2. Trigger a health check cycle: "Check system status"
3. Monitor the HealthMonitor logs
4. Ask a question that requires multiple component coordination: "What's the weather in Paris, and translate that information to Spanish"
5. This request should trigger:
   - TaskRouter to coordinate multiple services
   - PC2 services for both weather information and translation
   - Memory components to store the interaction
6. Monitor the logs of all involved components
7. Intentionally use an unsupported language: "Translate this to Klingon"
8. Check how the TaskRouter and Circuit Breaker handle this edge case

#### Expected Outcomes
- The health check should:
  - Report the status of all components
  - Show all critical services as operational
  - Complete within a reasonable timeframe (< 10 seconds)
- The complex request should:
  - Be properly parsed into subtasks
  - Execute all subtasks in the correct order
  - Return a coherent response in Spanish
  - Show proper coordination in the logs
- The unsupported language request should:
  - Be gracefully handled
  - Return an appropriate error message
  - Not crash any components
  - Show proper circuit breaker behavior
- All communications should be secure (check for CURVE logs)
- Performance metrics should be within acceptable ranges

## Test Reporting

For each test scenario, document:

1. **Test Result**: Pass/Fail/Partial
2. **Actual Outcome**: What actually happened
3. **Discrepancies**: Any differences from expected outcomes
4. **Performance Metrics**: Actual measured times
5. **Log Snippets**: Relevant portions of logs
6. **Screenshots**: If applicable, especially for Grafana dashboards
7. **Issues Found**: Any bugs or unexpected behavior
8. **Recommendations**: Suggestions for improvements

## Conclusion

This test plan provides a comprehensive validation of the Voice Assistant system after completing all core enhancement steps. Successful execution of these tests confirms that the system operates as a cohesive whole, with all components properly integrated, secured, and monitored. 