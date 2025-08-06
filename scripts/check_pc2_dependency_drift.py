#!/usr/bin/env python3
"""
PC2 Dependency Drift Guard
Prevents agent requirements.txt from duplicating base image dependencies
"""

import sys
import json
import subprocess
import pathlib
from typing import Set, List

def get_base_packages(base_image: str) -> Set[str]:
    """Get list of packages installed in base image"""
    try:
        cmd = [
            "docker", "run", "--rm", base_image, 
            "python", "-c", 
            "import json, pkg_resources; print(json.dumps([d.key for d in pkg_resources.working_set]))"
        ]
        result = subprocess.check_output(cmd, text=True)
        return set(json.loads(result))
    except Exception as e:
        print(f"Warning: Could not query base image {base_image}: {e}")
        return set()

def check_agent_requirements(agent_reqs_file: str, base_image: str) -> List[str]:
    """Check for duplicate dependencies between agent and base"""
    if not pathlib.Path(agent_reqs_file).exists():
        return []
    
    # Get base packages
    base_pkgs = get_base_packages(base_image)
    
    # Get agent requirements
    agent_reqs = []
    with open(agent_reqs_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                agent_reqs.append(pkg_name)
    
    # Find duplicates
    duplicates = set(agent_reqs) & base_pkgs
    return list(duplicates)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: check_pc2_dependency_drift.py <requirements.txt> <base_image>")
        sys.exit(1)
    
    agent_reqs_file = sys.argv[1]
    base_image = sys.argv[2]
    
    duplicates = check_agent_requirements(agent_reqs_file, base_image)
    
    if duplicates:
        print("❌ Duplicate dependencies found:")
        for dup in sorted(duplicates):
            print(f"   - {dup}")
        print(f"
These packages are already in base image: {base_image}")
        print("Remove them from requirements.txt to avoid build inefficiency.")
        sys.exit(1)
    else:
        print("✅ No duplicate dependencies found")
        sys.exit(0)
