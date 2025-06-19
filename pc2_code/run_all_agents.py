import subprocess
import sys
import os
import signal
import time
import platform
from pathlib import Path

# Check if running in a virtual environment
def is_venv_active():
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

if not is_venv_active():
    print("WARNING: Virtual environment is not activated. It's recommended to run this script in a virtual environment.")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        print("Exiting. Please activate your virtual environment and try again.")
        sys.exit(1)

# Get a list of all agent files in the agents directory
agent_files = []
for file in os.listdir("agents"):
    # All agents are now fixed and should run properly
    # This is just a placeholder for future problematic agents
    if file in []:
        continue
        
    # Make sure context_bridge_agent.py is included even if it doesn't follow the standard naming convention
    if file == "context_bridge_agent.py":
        agent_name = "Context_Bridge"
        agent_files.append((agent_name, os.path.join("agents", file)))
        continue
        
    if file.endswith("_agent.py") and os.path.isfile(os.path.join("agents", file)):
        agent_name = file.replace("_agent.py", "").title()
        agent_files.append((agent_name, os.path.join("agents", file)))

# Add dashboard to the list of agents
dashboard_path = os.path.join("dashboard", "dashboard.py")
if os.path.isfile(dashboard_path):
    agent_files.append(("Dashboard", dashboard_path))

# Add any additional agents that are not in the standard naming format
AGENTS = agent_files + [
    ("Auto_Fixer", os.path.join("agents", "auto_fixer_agent.py")),
    ("Code_Command_Handler", os.path.join("agents", "code_command_handler.py")),
    ("Translator", os.path.join("agents", "translator_agent.py")),
    # Add any other agents that don't follow the standard naming convention
]

# Agent port configuration to avoid conflicts
AGENT_PORTS = {
    "Model_Manager": 5556,
    "Remote_Connector": 5557,
    "Task_Router": 5558,
    "Context_Bridge": 5595,  # Receives from Face Recognition
    "Contextual_Memory": 5596,  # Changed from 5595 to avoid conflict
    "Digital_Twin": 5597,  # Changed from 5596 to avoid conflict
    "Filesystem_Assistant": 5594,  # Changed from 5597 to avoid conflict
    "Face_Recognition": 5560,
    "Jarvis_Memory": 5598,
    "Learning_Mode": 5599,
    "Translator": 5559,  # New translator port
    "Dashboard": 8080
}

# Make sure agents start in the correct order (dependencies first)
AGENT_ORDER = [
    "Model_Manager",  # Start first as other agents depend on it
    "Remote_Connector",  # Start second as Task Router depends on it
    "Task_Router",  # Start third as it depends on Model Manager and Remote Connector
    "Contextual_Memory",  # Start before context bridge
    "Digital_Twin",  # Start before face recognition
    "Filesystem_Assistant",  # Start early as other agents may need it
    "Context_Bridge",  # Start context bridge after contextual memory
    "Face_Recognition",  # Face recognition depends on context bridge and digital twin
    "Listener",  # Listener should start after model manager and task router
    "Translator",  # Translator should start after listener but before task router
    "Tts",  # TTS agent can start anytime
    "Jarvis_Memory",  # Memory agent can start anytime
    "Learning_Mode",  # Learning mode agent can start anytime
    "Auto_Fixer",  # Start auto-fixer after core agents
    "Code_Command_Handler",  # Start code command handler after auto-fixer
    "Dashboard",  # Start dashboard last so it can monitor all other agents
    # Other agents can start in any order
]

# Sort the agents based on the preferred order
def agent_sort_key(agent_tuple):
    name, _ = agent_tuple
    try:
        return AGENT_ORDER.index(name)
    except ValueError:
        return len(AGENT_ORDER)  # Put agents not in the list at the end

# Sort agents by dependency order
AGENTS.sort(key=agent_sort_key)

processes = []


def start_agent(name, path):
    # For dashboard, open in a browser automatically if possible
    if name == "Dashboard":
        print(f"\n[{name}] Starting dashboard. Access it at http://localhost:8080 in your browser.")
        # Start the dashboard process
        proc = subprocess.Popen(
            [sys.executable, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        
        # Try to open the browser automatically, but don't fail if it doesn't work
        try:
            # Wait a moment for the server to start
            time.sleep(2)
            # Try to open the browser if possible
            try:
                # Use the built-in webbrowser module
                import webbrowser
                webbrowser.open('http://localhost:8080')
            except:
                print(f"[{name}] Could not automatically open browser. Please navigate to http://localhost:8080 manually.")
        except:
            pass
            
        return proc
    
    # For agents that need to run in server mode
    if name in ["Auto_Fixer", "Self_Healing"]:
        return subprocess.Popen(
            [sys.executable, path, "--server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
    
    # For all other agents, start normally
    return subprocess.Popen(
        [sys.executable, path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    )


def print_agent_logs(name, process):
    for line in iter(process.stdout.readline, ''):
        print(f"[{name}] {line}", end='')


def main():
    import threading
    
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("cache", exist_ok=True)
    os.makedirs(os.path.join("config"), exist_ok=True)
    
    try:
        threads = []
        for name, path in AGENTS:
            print(f"Starting {name} Agent...")
            # Add a small delay between starting agents to avoid port conflicts
            proc = start_agent(name, path)
            processes.append((name, proc))
            t = threading.Thread(
                target=print_agent_logs, args=(
                    name, proc), daemon=True)
            t.start()
            threads.append(t)
            # Wait a bit between starting agents to avoid race conditions
            time.sleep(1)
            
        print("\nAll agents started successfully!")
        print("\nDashboard is available at: http://localhost:8080")
        print("\nPress Ctrl+C to stop all agents.")
        
        while True:
            time.sleep(1)
            # Check if any process has exited unexpectedly
            for name, proc in processes:
                if proc.poll() is not None:
                    print(
                        f"[{name}] exited with code {proc.returncode}. Shutting down all agents.")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("\nShutting down all agents...")
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        # Wait for all to exit
        for name, proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All agents stopped.")
    except Exception as e:
        print(f"[Orchestrator] Unexpected error: {e}")
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for name, proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All agents stopped due to error.")


if __name__ == "__main__":
    main()
