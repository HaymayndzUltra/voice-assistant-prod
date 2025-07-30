import subprocess
import time
import os
import sys

PC2_AGENTS = [
    "agents/ForPC2/rca_agent.py",
    "agents/ForPC2/system_digital_twin.py",
    "agents/ForPC2/proactive_context_monitor.py",
    "agents/ForPC2/unified_utils_agent.py",
    "agents/ForPC2/UnifiedErrorAgent.py",
    "agents/ForPC2/AuthenticationAgent.py",
    "agents/ForPC2/health_monitor.py",
    "agents/ForPC2/unified_monitoring.py",
    "agents/self_healing_agent.py",
    "agents/DreamingModeAgent.py",
    "agents/unified_web_agent.py",
    "agents/task_scheduler.py",
    "agents/resource_manager.py",
    "agents/experience_tracker.py",
    "agents/memory_manager.py",
    "agents/context_manager.py",
    "agents/EpisodicMemoryAgent.py",
    "agents/unified_memory_reasoning_agent.py",
    "agents/DreamWorldAgent.py",
    "agents/cache_manager.py",
    "agents/tiered_responder.py",
    "agents/LearningAdjusterAgent.py",
    "agents/remote_connector_agent.py",
    "agents/tutor_agent.py",
    "agents/tutoring_service_agent.py",
    "agents/UnifiedMemoryReasoningAgent.py",
    "agents/performance_monitor.py",
    "agents/async_processor.py",
    "agents/enhanced_contextual_memory.py",
    "agents/tutoring_agent.py",
    "agents/advanced_router.py",
    "agents/PerformanceLoggerAgent.py",
    "agents/AgentTrustScorer.py",
    "agents/memory_decay_manager.py",
    "agents/auto_fixer_agent.py",
    "agents/filesystem_assistant_agent.py"
]

HEALTHY_AGENTS = []
FAILED_AGENTS = {}

def run_agent_health_check(agent_script, duration=15):
    print(f"\n--- Testing {agent_script} ---")
    process = None
    error_output = ""
    try:
        # Using sys.executable to ensure the script runs with the same Python interpreter
        command = [sys.executable, agent_script]
        # Set the PYTHONPATH for the subprocess to ensure correct module imports
        env = os.environ.copy()
        project_root = os.getcwd()
        current_pythonpath = env.get("PYTHONPATH", "")
        if current_pythonpath:
            env["PYTHONPATH"] = f"{project_root}{os.pathsep}{current_pythonpath}"
        else:
            env["PYTHONPATH"] = project_root

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        start_time = time.time()
        while process.poll() is None and (time.time() - start_time < duration):
            time.sleep(1)

        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        
        stdout, stderr = process.communicate(timeout=5) # Capture stdout and stderr
        
        if process.returncode == 0:
            error_output = stderr.decode(errors='ignore').strip() if stderr else "No specific error message captured."
            return True, error_output
        else:
            error_output = stderr.decode(errors='ignore').strip() if stderr else "No specific error message captured."
            return False, error_output

    except Exception as e:
        error_output = str(e)
        print(f"Error running agent {agent_script}: {e}")
        return False, error_output
    finally:
        if process and process.poll() is None:
            process.kill() # Ensure no zombie processes
            print(f"Agent {agent_script} ensured terminated in finally block.")


def generate_report():
    report_content = "# PC2 Agent Health Check Report\n\n"
    report_content += "## HEALTHY AGENTS\n"
    if HEALTHY_AGENTS:
        for agent in HEALTHY_AGENTS:
            report_content += f"- {agent}\n"
    else:
        report_content += "No agents passed the health check.\n"

    report_content += "\n## FAILED AGENTS\n"
    if FAILED_AGENTS:
        for agent, error in FAILED_AGENTS.items():
            report_content += f"- {agent}: FAILED\n"
            report_content += "  Error Log:\n"
            report_content += f"    ```\n{error.strip()}\n    ```\n"
    else:
        report_content += "No agents failed the health check.\n"

    report_file_path = "pc2_focused_health_check_report.md"
    with open(report_file_path, "w") as f:
        f.write(report_content)
    print(f"\nHealth check report generated at {report_file_path}")

if __name__ == "__main__":
    for agent in PC2_AGENTS:
        is_healthy, error = run_agent_health_check(agent)
        if is_healthy:
            HEALTHY_AGENTS.append(agent)
            print(f"{agent} - HEALTHY")
        else:
            FAILED_AGENTS[agent] = error
            print(f"{agent} - FAILED")

    generate_report() 