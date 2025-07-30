import yaml
import os
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
def validate_agent_paths():
    # Load the startup config
    with open(PathManager.join_path("config", "startup_config.yaml"), 'r') as f:
        config = yaml.safe_load(f)
    
    # Get the list of agents
    agents = config['main_pc_agents']
    
    # Prepare the report
    print("# `startup_config.yaml` File Validation Report\n")
    print("| Agent Name | Configured `script_path` | File Exists? | Status |")
    print("|------------|--------------------------|--------------|--------|")
    
    mismatches = []
    
    for agent in agents:
        name = agent['name']
        script_path = agent['script_path']
        exists = os.path.exists(script_path)
        status = "OK" if exists else "**MISMATCH**"
        exists_mark = "✅ Yes" if exists else "❌ NO"
        
        print(f"| {name:<20} | {script_path:<40} | {exists_mark:<12} | {status:<6} |")
        
        if not exists:
            mismatches.append((name, script_path))
    
    if mismatches:
        print("\n## Mismatched Files Analysis")
        for name, script_path in mismatches:
            # Try to find the file in common directories
            possible_locations = [
                'src/core/',
                'src/agents/',
                'agents/',
                'core/',
                'src/'
            ]
            
            found = False
            for base_dir in possible_locations:
                # Try with and without '_agent' suffix
                possible_names = [
                    script_path.split('/')[-1],
                    script_path.split('/')[-1].replace('_agent.py', '.py'),
                    script_path.split('/')[-1].replace('.py', '_agent.py')
                ]
                
                for possible_name in possible_names:
                    test_path = os.path.join(base_dir, possible_name)
                    if os.path.exists(test_path):
                        print(f"* **{name}:** Found at `{test_path}`")
                        found = True
                        break
                if found:
                    break
            
            if not found:
                print(f"* **{name}:** No matching file found in common directories")

if __name__ == "__main__":
    validate_agent_paths() 