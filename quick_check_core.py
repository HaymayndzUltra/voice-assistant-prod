#!/usr/bin/env python3
"""
Quick Check of Core Agents
-------------------------
Checks the most important core agents for basic issues.
"""
import os
from pathlib import Path

# Core agents to check
CORE_AGENTS = [
    ("TaskRouter", "main_pc_code/src/core/task_router.py"),
    ("ModelManagerAgent", "main_pc_code/agents/model_manager_agent.py"),
    ("ChainOfThoughtAgent", "main_pc_code/FORMAINPC/ChainOfThoughtAgent.py"),
    ("CoordinatorAgent", "main_pc_code/agents/coordinator_agent.py"),
    ("ConsolidatedTranslator", "main_pc_code/FORMAINPC/consolidated_translator.py"),
    ("StreamingInterruptHandler", "main_pc_code/agents/streaming_interrupt_handler.py")
]

# Quick check function
def quick_check(name, path):
    full_path = Path(path)
    
    # Check if file exists
    if not full_path.exists():
        return f"[MISSING] {name}: File not found at {path}"
    
    # Try to open and read the file
    try:
        with open(full_path, 'r') as f:
            content = f.read()
            
        # Look for common issues
        issues = []
        
        # Check for indentation errors (common Python syntax error)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and line.startswith(' ') and not line.startswith('    '):
                issues.append(f"Line {i+1}: Possible indentation error")
        
        # Check for missing imports
        if "import " not in content:
            issues.append("No imports found")
        
        # Check for class definition
        if "class " not in content:
            issues.append("No class definition found")
        
        # Check for health_check method (needed for test framework)
        if "health_check" not in content and "def _get_health_status" not in content:
            issues.append("No health_check or _get_health_status method found")
        
        if issues:
            return f"[ISSUES] {name}: {', '.join(issues)}"
        else:
            return f"[OK] {name}: No basic issues found"
    except Exception as e:
        return f"[ERROR] {name}: Error reading file: {e}"

# Main function
def main():
    print("\n=== Quick Check of Core Agents ===\n")
    
    for name, path in CORE_AGENTS:
        result = quick_check(name, path)
        print(result)
    
    print("\nCheck complete. Next steps:")
    print("1. Try running each core agent directly to see specific errors")
    print("2. Fix any issues found")
    print("3. Re-run the test framework with fixed agents")

if __name__ == "__main__":
    main() 