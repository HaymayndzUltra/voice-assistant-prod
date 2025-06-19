import subprocess
import time
import os

# List of agent scripts to run (add/remove as needed)
agents = [
    'remote_connector_agent.py',
    'performance_monitor.py',
    'cache_manager.py',
    'async_processor.py',
    'tiered_responder.py',
    'self_healing_agent.py',
    'LearningAdjusterAgent.py',
    'DreamWorldAgent.py',
    'UnifiedMemoryReasoningAgent.py',
    'tutoring_service_agent.py',
    'tutor_agent.py',
    'enhanced_contextual_memory.py',
    'EpisodicMemoryAgent.py',
    'unified_memory_reasoning_agent.py',
    'unified_web_agent.py',
    'port_health_check.py',
    'DreamingModeAgent.py',
    'tutoring_agent.py',
    'rollback_web_ports.py',
    'monitor_web_ports.py',
    'filesystem_assistant_agent.py',
    'AgentTrustScorer.py',
    'memory_decay_manager.py',
]

AGENT_DIR = os.path.join(os.path.dirname(__file__), 'agents')

for agent in agents:
    agent_path = os.path.join(AGENT_DIR, agent)
    if not os.path.exists(agent_path):
        print(f"[SKIP] {agent} not found.")
        continue
    print(f"\n[RUNNING] {agent}")
    try:
        result = subprocess.run(['python', agent_path], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"[SUCCESS] {agent}")
        else:
            print(f"[ERROR] {agent} exited with code {result.returncode}")
        print(result.stdout)
        print(result.stderr)
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {agent} did not finish in 30 seconds.")
    except Exception as e:
        print(f"[EXCEPTION] {agent}: {e}")
    print("[WAIT] Waiting 10 seconds before next agent...")
    time.sleep(10)
print("\n[COMPLETE] All agents processed.") 