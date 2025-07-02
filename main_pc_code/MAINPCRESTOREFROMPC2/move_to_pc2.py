import os
import shutil
from pathlib import Path

def ensure_dir(directory):
    """Ensure directory exists"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def move_file(source, destination):
    """Move file from source to destination"""
    try:
        shutil.copy2(source, destination)
        print(f"Copied {source} to {destination}")
    except Exception as e:
        print(f"Error copying {source}: {e}")

# Create ForPC2 directory
ensure_dir("ForPC2")

# Files to move from src/core
core_files = [
    "health_monitor.py",
    "task_router.py",
    "proactive_context_monitor.py",
    "rca_agent.py",
    "system_digital_twin.py"
]

# Files to move from src/agents
agent_files = [
    "unified_monitoring.py",
    "unified_utils_agent.py"
]

# Move core files
for file in core_files:
    source = os.path.join("src", "core", file)
    destination = os.path.join("ForPC2", file)
    if os.path.exists(source):
        move_file(source, destination)
    else:
        print(f"Warning: {source} not found")

# Move agent files
for file in agent_files:
    source = os.path.join("src", "agents", file)
    destination = os.path.join("ForPC2", file)
    if os.path.exists(source):
        move_file(source, destination)
    else:
        print(f"Warning: {source} not found")

print("\nFiles that need to be created (not found in source):")
print("- UnifiedErrorAgent.py")
print("- AuthenticationAgent.py") 