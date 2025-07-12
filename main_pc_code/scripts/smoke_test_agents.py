import yaml
import subprocess
import os
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
def load_config():
    with open(join_path("config", "startup_config.yaml"), 'r') as f:
        return yaml.safe_load(f)

def smoke_test_agents():
    config = load_config()
    failed_scripts = []
    
    for agent in config['main_pc_agents']:
        script_path = agent['script_path']
        print(f"\nTesting: {agent['name']} ({script_path})")
        
        # Verify script path exists
        if not os.path.exists(script_path):
            failed_scripts.append({
                'name': agent['name'],
                'path': script_path,
                'error': f"Script file does not exist at path: {script_path}"
            })
            continue
            
        try:
            print(f"Compiling: {script_path}")
            result = subprocess.run(['python3', '-m', 'py_compile', script_path],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error in {script_path}:")
                print(result.stderr.strip())
                failed_scripts.append({
                    'name': agent['name'],
                    'path': script_path,
                    'error': result.stderr.strip()
                })
        except Exception as e:
            print(f"Exception in {script_path}:")
            print(str(e))
            failed_scripts.append({
                'name': agent['name'],
                'path': script_path,
                'error': str(e)
            })
    
    return failed_scripts

def main():
    print("Starting smoke test for all agent scripts...")
    failed_scripts = smoke_test_agents()
    
    if not failed_scripts:
        print("\nAll agent scripts passed the smoke test successfully!")
        return
    
    print("\nFailed Scripts:")
    for script in failed_scripts:
        print(f"\nAgent: {script['name']}")
        print(f"Path: {script['path']}")
        print(f"Error: {script['error']}")

if __name__ == "__main__":
    main()
