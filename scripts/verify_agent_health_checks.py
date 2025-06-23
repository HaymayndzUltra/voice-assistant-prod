#!/usr/bin/env python3
"""
Verify Agent Health Checks

This script scans the codebase to identify all active agents and verify that they
have proper health check implementations. It reports agents without health checks
that need to be updated.

Usage:
    python scripts/verify_agent_health_checks.py
"""

import os
import re
import sys
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Define paths to scan
MAIN_PC_PATHS = [
    "main_pc_code/agents",
    "main_pc_code/src",
    "main_pc_code/FORMAINPC"
]

PC2_PATHS = [
    "pc2_code/agents",
    "pc2_code/agents/core_agents",
    "pc2_code/agents/ForPC2"
]

# Patterns to identify health check implementations
HEALTH_CHECK_PATTERNS = [
    r'def\s+_start_health',
    r'def\s+_health_check',
    r'health_socket\s*=',
    r'\.bind\(.*health_port',
    r'\.bind\(.*\+\s*1\)',  # Common pattern where health port is main port + 1
]

# Patterns to identify agent classes
AGENT_CLASS_PATTERNS = [
    r'class\s+\w+Agent',
    r'class\s+\w+Service',
]

# Files to exclude (known non-agent files or utility files)
EXCLUDE_FILES = [
    "__init__.py",
    "__pycache__",
    "test_",
    "utils.py",
    "agent_utils.py",
]

def is_agent_file(file_path: str) -> bool:
    """Check if a file is likely an agent implementation file."""
    filename = os.path.basename(file_path)
    
    # Skip excluded files
    for exclude in EXCLUDE_FILES:
        if exclude in filename:
            return False
    
    # Must be a Python file
    if not filename.endswith('.py'):
        return False
    
    # Check file content for agent class patterns
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in AGENT_CLASS_PATTERNS:
            if re.search(pattern, content):
                return True
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return False

def has_health_check(file_path: str) -> Tuple[bool, str]:
    """Check if a file has health check implementation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for pattern in HEALTH_CHECK_PATTERNS:
            if re.search(pattern, content):
                return True, "Found health check pattern"
        
        # Check for base class inheritance that might provide health check
        if "BaseAgent" in content and ("super().__init__" in content or "super()" in content):
            return True, "Inherits from BaseAgent which provides health check"
            
        return False, "No health check implementation found"
    except Exception as e:
        return False, f"Error analyzing file: {e}"

def extract_class_names(file_path: str) -> List[str]:
    """Extract agent class names from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        return [node.name for node in ast.walk(tree) 
                if isinstance(node, ast.ClassDef) and 
                ('Agent' in node.name or 'Service' in node.name)]
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

def scan_directory(directory: str) -> List[Dict]:
    """Scan a directory for agent files and check health implementations."""
    results = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            if is_agent_file(file_path):
                has_health, reason = has_health_check(file_path)
                class_names = extract_class_names(file_path)
                
                results.append({
                    "file": file_path,
                    "classes": class_names,
                    "has_health_check": has_health,
                    "reason": reason
                })
    
    return results

def main():
    """Main function to scan both main PC and PC2 code."""
    print("=" * 80)
    print("AGENT HEALTH CHECK VERIFICATION")
    print("=" * 80)
    
    # Scan Main PC code
    print("\nScanning Main PC code...")
    main_pc_results = []
    for path in MAIN_PC_PATHS:
        full_path = os.path.join(project_root, path)
        if os.path.exists(full_path):
            main_pc_results.extend(scan_directory(full_path))
    
    # Scan PC2 code
    print("\nScanning PC2 code...")
    pc2_results = []
    for path in PC2_PATHS:
        full_path = os.path.join(project_root, path)
        if os.path.exists(full_path):
            pc2_results.extend(scan_directory(full_path))
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    # Main PC results
    print("\nMAIN PC AGENTS:")
    print("-" * 80)
    print(f"{'File':<50} {'Classes':<30} {'Health Check':<10} {'Reason'}")
    print("-" * 80)
    
    main_pc_missing = []
    for result in main_pc_results:
        status = "✅" if result["has_health_check"] else "❌"
        classes = ", ".join(result["classes"]) if result["classes"] else "No agent classes"
        print(f"{os.path.basename(result['file']):<50} {classes[:30]:<30} {status:<10} {result['reason'][:40]}")
        
        if not result["has_health_check"]:
            main_pc_missing.append(result)
    
    # PC2 results
    print("\nPC2 AGENTS:")
    print("-" * 80)
    print(f"{'File':<50} {'Classes':<30} {'Health Check':<10} {'Reason'}")
    print("-" * 80)
    
    pc2_missing = []
    for result in pc2_results:
        status = "✅" if result["has_health_check"] else "❌"
        classes = ", ".join(result["classes"]) if result["classes"] else "No agent classes"
        print(f"{os.path.basename(result['file']):<50} {classes[:30]:<30} {status:<10} {result['reason'][:40]}")
        
        if not result["has_health_check"]:
            pc2_missing.append(result)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Main PC: {len(main_pc_results)} agents found, {len(main_pc_missing)} missing health checks")
    print(f"PC2: {len(pc2_results)} agents found, {len(pc2_missing)} missing health checks")
    
    # Agents missing health checks
    if main_pc_missing or pc2_missing:
        print("\n" + "=" * 80)
        print("AGENTS MISSING HEALTH CHECKS")
        print("=" * 80)
        
        if main_pc_missing:
            print("\nMain PC agents missing health checks:")
            for result in main_pc_missing:
                print(f"- {result['file']} ({', '.join(result['classes'])})")
        
        if pc2_missing:
            print("\nPC2 agents missing health checks:")
            for result in pc2_missing:
                print(f"- {result['file']} ({', '.join(result['classes'])})")
        
        print("\nRecommendation: Add health check implementations to these agents.")
        print("Use the following template:")
        print("""
def _start_health_check(self):
    def health_check_loop():
        health_socket = create_socket(zmq.Context.instance(), zmq.REP, server=True)
        health_socket.bind(f"tcp://0.0.0.0:{self.port + 1}")  # Health port is main port + 1
        while self.running:
            try:
                if health_socket.poll(timeout=100, flags=zmq.POLLIN):
                    _ = health_socket.recv()
                    health_socket.send_json({
                        "agent": self.name,
                        "status": "ok",
                        "timestamp": datetime.now().isoformat()
                    })
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"Health check error: {e}")
                time.sleep(1)
    
    self.health_thread = threading.Thread(target=health_check_loop, daemon=True)
    self.health_thread.start()
        """)
    else:
        print("\nAll agents have health check implementations! ✅")

if __name__ == "__main__":
    main() 