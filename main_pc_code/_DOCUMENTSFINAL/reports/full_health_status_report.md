# Full System Health Status Report

## Full JSON Response
```json
{
  "status": "ok",
  "agents": {}
}
```

## Analysis
- **Expected agents (from docker-compose.yaml):** ['coordinator', 'health_monitor', 'system_digital_twin', 'rca_agent', 'proactive_context_monitor', 'task_router', 'vision_capture_agent', 'memory_orchestrator', 'session_memory_agent', 'fused_audio_preprocessor', 'vad_agent', 'unified_memory_reasoning_agent', 'dream_world_agent', 'vision_processing_agent']
- **Agents reported by HealthMonitor:** []
- **Missing agents:** ['coordinator', 'health_monitor', 'system_digital_twin', 'rca_agent', 'proactive_context_monitor', 'task_router', 'vision_capture_agent', 'memory_orchestrator', 'session_memory_agent', 'fused_audio_preprocessor', 'vad_agent', 'unified_memory_reasoning_agent', 'dream_world_agent', 'vision_processing_agent']
- **Unhealthy/Unreachable agents:** None
- **All agents healthy:** NO
