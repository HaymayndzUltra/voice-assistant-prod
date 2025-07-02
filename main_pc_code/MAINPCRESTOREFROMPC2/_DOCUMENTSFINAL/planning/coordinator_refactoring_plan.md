# Coordinator Agent Refactoring Plan

This document outlines a detailed plan to fix the dead-end connections in the `agents/coordinator_agent.py` file. The plan is based on a thorough analysis of the codebase and aims to ensure the coordinator can properly communicate with all active agents in the system.

## Dead-End Connection Analysis

### 1. STT_PORT (5556) Connection

**Problem:**
- The coordinator connects to an STT (Speech-to-Text) service on port 5556
- No active agent is binding to this port
- This port is also referenced as MODEL_MANAGER_PORT in other agents, creating a conflict
- The connection is used in the `_process_audio` method to transcribe audio data

**Proposed Solution:**
- Remove the direct connection to the non-existent STT service
- Update the `_process_audio` method to route audio transcription requests through the task_router (port 5571), which can then forward them to the appropriate service
- Ensure PC2 agents (e.g., Unified Memory Reasoning Agent, DreamWorld Agent) are correctly referenced in the integration

```diff
# In constants section:
- STT_PORT = 5556
+ TASK_ROUTER_PORT = 5571  # Add if not already present

# In __init__ method:
- self.stt_socket = self.context.socket(zmq.REQ)
- self.stt_socket.connect(f"tcp://localhost:{STT_PORT}")
+ self.task_router_socket = self.context.socket(zmq.REQ)
+ self.task_router_socket.connect(f"tcp://localhost:{TASK_ROUTER_PORT}")

# In stop method:
- self.stt_socket.close()
+ self.task_router_socket.close()  # Add if not already present

# In _process_audio method:
- # Step 1: Send audio to STT Agent
- logger.info("Sending audio to STT Agent")
- self.stt_socket.send_json({
-     "action": "transcribe",
-     "audio_data": audio_data
- })
- stt_response = self.stt_socket.recv_json()
+ # Step 1: Send audio to Task Router for transcription
+ logger.info("Sending audio to Task Router for transcription")
+ self.task_router_socket.send_json({
+     "action": "route",
+     "target": "transcription",
+     "data": {
+         "audio_data": audio_data
+     }
+ })
+ stt_response = self.task_router_socket.recv_json()
```

### 2. TTS_PORT (5557) Connection

**Problem:**
- The coordinator connects to a TTS (Text-to-Speech) service on port 5557
- No active agent is binding to this port
- The connection is used in multiple methods to synthesize speech from text
- There is an active TTSConnector that binds to port 5563 for health checks

**Proposed Solution:**
- Update the connection to point to the active TTSConnector's port
- The TTSConnector is listening on port 5562 (TTS_AGENT_PORT) for synthesis requests

```diff
# In constants section:
- TTS_PORT = 5557
+ TTS_CONNECTOR_PORT = 5562  # Port where TTSConnector is listening

# In __init__ method:
- self.tts_socket = self.context.socket(zmq.REQ)
- self.tts_socket.connect(f"tcp://localhost:{TTS_PORT}")
+ self.tts_socket = self.context.socket(zmq.REQ)
+ self.tts_socket.connect(f"tcp://localhost:{TTS_CONNECTOR_PORT}")
```

### 3. NLU_PORT (5558) Connection

**Problem:**
- The coordinator connects to an NLU (Natural Language Understanding) service on port 5558
- No active agent is binding to this port
- The connection is used in the `_process_text` method to analyze text input

**Proposed Solution:**
- Remove the direct connection to the non-existent NLU service
- Update the `_process_text` method to route NLU requests through the task_router (port 5571), which can handle language processing

```diff
# In constants section:
- NLU_PORT = 5558

# In __init__ method:
- self.nlu_socket = self.context.socket(zmq.REQ)
- self.nlu_socket.connect(f"tcp://localhost:{NLU_PORT}")

# In stop method:
- self.nlu_socket.close()

# In _process_text method:
- # Step 1: Send text to NLU Agent
- logger.info("Sending text to NLU Agent")
- self.nlu_socket.send_json({
-     "action": "analyze",
-     "text": text
- })
- nlu_response = self.nlu_socket.recv_json()
+ # Step 1: Send text to Task Router for NLU processing
+ logger.info("Sending text to Task Router for NLU processing")
+ self.task_router_socket.send_json({
+     "action": "route",
+     "target": "nlu",
+     "data": {
+         "text": text
+     }
+ })
+ nlu_response = self.task_router_socket.recv_json()
```

### 4. DIALOG_PORT (5559) Connection

**Problem:**
- The coordinator connects to a Dialog service on port 5559
- No active agent is binding to this port
- The connection is used in the `_process_text` method to generate responses

**Proposed Solution:**
- Remove the direct connection to the non-existent Dialog service
- Update the `_process_text` method to route dialog generation requests through the task_router (port 5571)

```diff
# In constants section:
- DIALOG_PORT = 5559

# In __init__ method:
- self.dialog_socket = self.context.socket(zmq.REQ)
- self.dialog_socket.connect(f"tcp://localhost:{DIALOG_PORT}")

# In stop method:
- self.dialog_socket.close()

# In _process_text method:
- # Route to Dialog Agent for regular intents
- logger.info("Routing to Dialog Agent")
- self.dialog_socket.send_json({
-     "action": "generate_response",
-     "text": text,
-     "intent": intent,
-     "entities": entities
- })
- dialog_response = self.dialog_socket.recv_json()
+ # Route to Task Router for dialog generation
+ logger.info("Routing to Task Router for dialog generation")
+ self.task_router_socket.send_json({
+     "action": "route",
+     "target": "dialog",
+     "data": {
+         "text": text,
+         "intent": intent,
+         "entities": entities
+     }
+ })
+ dialog_response = self.task_router_socket.recv_json()
```

### 5. SELF_HEALING_PORT (5561) Connection

**Problem:**
- The coordinator connects to a Self-Healing service on port 5561
- No active agent is binding to this port
- The actual Self-Healing agent on PC2 is using port 5614
- The connection is used in the `_health_check` method

**Proposed Solution:**
- Update the connection to point to the Health Monitor on port 5584, which is the central point for health monitoring on the main PC
- The Health Monitor can then communicate with the Self-Healing agent on PC2 if needed

```diff
# In constants section:
- SELF_HEALING_PORT = 5561
+ HEALTH_MONITOR_PORT = 5584  # Port for the Health Monitor agent

# In __init__ method:
- self.self_healing_socket = self.context.socket(zmq.REQ)
- self.self_healing_socket.connect(f"tcp://localhost:{SELF_HEALING_PORT}")
+ self.health_monitor_socket = self.context.socket(zmq.REQ)
+ self.health_monitor_socket.connect(f"tcp://localhost:{HEALTH_MONITOR_PORT}")

# In stop method:
- self.self_healing_socket.close()
+ self.health_monitor_socket.close()

# In _health_check method:
- # Check Self-Healing Agent
- try:
-     self.self_healing_socket.send_json({"action": "health_check"})
-     response = self.self_healing_socket.recv_json()
-     health_status["self_healing"] = "ok" if response.get("status") == "ok" else "error"
- except:
-     health_status["self_healing"] = "error"
+ # Check Health Monitor
+ try:
+     self.health_monitor_socket.send_json({"action": "health_check"})
+     response = self.health_monitor_socket.recv_json()
+     health_status["health_monitor"] = "ok" if response.get("status") == "ok" else "error"
+ except:
+     health_status["health_monitor"] = "error"
```

### 6. VISION_CAPTURE_PORT (5587) Connection

**Problem:**
- The coordinator connects to a Vision Capture service on port 5587
- The vision_capture_agent.py file does bind to this port, but it's located in src/vision/ directory, not in agents/
- The connection is used in the `_process_vision` method

**Proposed Solution:**
- Keep the connection but ensure it points to the correct location
- No code changes needed if the vision_capture_agent is actually running and binding to port 5587

## Implementation Strategy

1. **Priority Order:**
   - First update the TTS connection (highest priority, as it's used for user interaction)
   - Then update the health monitoring connection
   - Finally update the STT, NLU, and Dialog connections

2. **Testing Strategy:**
   - After each connection update, test the specific functionality that uses that connection
   - Verify that the coordinator can still perform its core functions
   - Check logs for any connection errors or timeouts

3. **Rollback Plan:**
   - Keep a backup of the original coordinator_agent.py file
   - If any issues arise, revert to the original file and diagnose the problem

## Conclusion

This refactoring plan addresses all the dead-end connections in the coordinator_agent.py file. By implementing these changes, we'll ensure that the coordinator can properly communicate with all active agents in the system, improving overall system stability and reliability. 