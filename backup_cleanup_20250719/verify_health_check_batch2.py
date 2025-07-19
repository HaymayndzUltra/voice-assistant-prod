#!/usr/bin/env python3
"""
Verify that all target files have the _get_health_status method.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict

def check_file_for_health_status(file_path: str) -> Dict:
    """Check if a file has the _get_health_status method."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if _get_health_status method exists
        has_method = bool(re.search(r"def\s+_get_health_status\s*\(", content))
        
        return {
            "file": file_path,
            "has_health_status_method": has_method
        }
    
    except Exception as e:
        return {
            "file": file_path,
            "has_health_status_method": False,
            "error": str(e)
        }

def main():
    # Target files for Batch 2
    target_files = [
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/mood_tracker_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_planning_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/MultiAgentSwarmManager.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_connector.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_cache.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_tts_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_agent.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_interrupt_handler.py",
        "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/code_generator_agent.py"
    ]
    
    results = []
    for file_path in target_files:
        result = check_file_for_health_status(file_path)
        results.append(result)
    
    # Print summary
    print("\n=== HEALTH CHECK METHOD VERIFICATION SUMMARY ===")
    
    compliant_files = []
    non_compliant_files = []
    
    for result in results:
        file_name = os.path.basename(result["file"])
        if result.get("has_health_status_method", False):
            compliant_files.append(file_name)
            print(f"✅ {file_name}: Has _get_health_status method")
        else:
            non_compliant_files.append(file_name)
            error = result.get("error", "Method not found")
            print(f"❌ {file_name}: {error}")
    
    # Print final summary
    print("\n=== FINAL SUMMARY ===")
    print(f"Total files checked: {len(results)}")
    print(f"Files with _get_health_status method: {len(compliant_files)}")
    print(f"Files missing _get_health_status method: {len(non_compliant_files)}")
    
    if non_compliant_files:
        print("\nNon-compliant files:")
        for file in non_compliant_files:
            print(f"  - {file}")
    
    # Return exit code based on compliance
    return 0 if len(non_compliant_files) == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 