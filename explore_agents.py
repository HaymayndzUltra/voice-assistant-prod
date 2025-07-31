#!/usr/bin/env python3
"""Explore agent configurations in the AI_System_Monorepo."""

import os
import json
import yaml
from pathlib import Path

def explore_workspace():
    """Explore the workspace structure and find agent configurations."""
    
    print("=== Workspace Structure ===")
    
    # Main directories to explore
    main_dirs = ['main_pc_code', 'pc2_code', 'common', 'unified-system-v1']
    
    for main_dir in main_dirs:
        if os.path.exists(main_dir):
            print(f"\n{main_dir}/")
            
            # Look for config directory
            config_dir = os.path.join(main_dir, 'config')
            if os.path.exists(config_dir):
                print(f"  config/ found")
                # List config files
                for file in os.listdir(config_dir):
                    if file.endswith(('.yaml', '.yml', '.json')):
                        print(f"    - {file}")
            
            # Look for agents directory
            agents_dir = os.path.join(main_dir, 'agents')
            if os.path.exists(agents_dir):
                print(f"  agents/ found")
                # List agent subdirectories
                try:
                    subdirs = [d for d in os.listdir(agents_dir) if os.path.isdir(os.path.join(agents_dir, d))]
                    for subdir in subdirs[:10]:  # Limit output
                        print(f"    - {subdir}/")
                except:
                    pass
    
    # Find startup scripts
    print("\n=== Startup Scripts ===")
    startup_scripts = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if 'start' in file.lower() and file.endswith('.py'):
                startup_scripts.append(os.path.join(root, file))
    
    for script in sorted(startup_scripts)[:15]:
        print(f"  {script}")
    
    # Find agent-related Python files
    print("\n=== Agent Files ===")
    agent_files = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if 'agent' in file.lower() and file.endswith('.py'):
                agent_files.append(os.path.join(root, file))
    
    for agent_file in sorted(agent_files)[:15]:
        print(f"  {agent_file}")

if __name__ == "__main__":
    explore_workspace()