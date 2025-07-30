#!/usr/bin/env python3
"""
Verify that all target files have been properly standardized for configuration loading.
This script checks for compliance with criteria C6, C7, C8, C9.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

def check_file_for_compliance(file_path: str) -> Dict:
    """Check if a file complies with configuration standardization criteria."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check C6: Canonical parse_agent_args import
        c6_compliant = bool(re.search(r"from\s+main_pc_code\.utils\.config_parser\s+import\s+parse_agent_args", content))

        # Check C7: Module-level _agent_args call
        c7_compliant = bool(re.search(r"^_agent_args\s*=\s*parse_agent_args\(\)", content, re.MULTILINE))

        # Check C8: Standardized __init__ method with port and name from _agent_args
        c8_pattern = r"def\s+__init__\s*\([^)]*\):\s*\n\s*agent_port\s*=\s*_agent_args\.get\('port',[^)]*\)"
        c8_compliant = bool(re.search(c8_pattern, content))

        # Check C9: super().__init__ with port and name
        c9_pattern = r"super\(\)\.__init__\(port=agent_port,\s*name=agent_name\)"
        c9_compliant = bool(re.search(c9_pattern, content))

        # Check if argparse is imported
        has_argparse = bool(re.search(r"import\s+argparse", content))

        return {
            "file": file_path,
            "c6_compliant": c6_compliant,
            "c7_compliant": c7_compliant,
            "c8_compliant": c8_compliant,
            "c9_compliant": c9_compliant,
            "has_argparse": has_argparse,
            "overall_compliant": c6_compliant and c7_compliant and c8_compliant and c9_compliant and not has_argparse
        }

    except Exception as e:
        return {
            "file": file_path,
            "error": str(e),
            "overall_compliant": False
        }

def main():
    """TODO: Add description for main."""
    # Target files for Batch 1
    target_files = [
        "main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py",
        "main_pc_code/FORMAINPC/NLLBAdapter.py",
        "main_pc_code/FORMAINPC/LearningAdjusterAgent.py",
        "main_pc_code/FORMAINPC/LocalFineTunerAgent.py",
        "main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py",
        "main_pc_code/FORMAINPC/CognitiveModelAgent.py",
        "main_pc_code/agents/model_manager_agent.py",
        "main_pc_code/agents/vram_optimizer_agent.py",
        "main_pc_code/agents/coordinator_agent.py",
        "main_pc_code/agents/GoalOrchestratorAgent.py"
    ]

    results = []
    for file_path in target_files:
        result = check_file_for_compliance(file_path)
        results.append(result)

    # Print summary
    print("\n=== CONFIGURATION STANDARDIZATION VERIFICATION SUMMARY ===")

    compliant_files = []
    non_compliant_files = []

    for result in results:
        file_name = os.path.basename(result["file"])
        if result.get("overall_compliant", False):
            compliant_files.append(file_name)
            print(f"✅ {file_name}: Compliant with all criteria")
        else:
            non_compliant_files.append((file_name, result))
            if "error" in result:
                print(f"❌ {file_name}: Error - {result['error']}")
            else:
                issues = []
                if not result.get("c6_compliant", False):
                    issues.append("C6 (canonical import)")
                if not result.get("c7_compliant", False):
                    issues.append("C7 (module-level _agent_args)")
                if not result.get("c8_compliant", False):
                    issues.append("C8 (standardized __init__)")
                if not result.get("c9_compliant", False):
                    issues.append("C9 (super().__init__)")
                if result.get("has_argparse", False):
                    issues.append("argparse import present")
                print(f"❌ {file_name}: Non-compliant with {', '.join(issues)}")

    # Print final summary
    print("\n=== FINAL SUMMARY ===")
    print(f"Total files checked: {len(results)}")
    print(f"Compliant files: {len(compliant_files)}")
    print(f"Non-compliant files: {len(non_compliant_files)}")

    if non_compliant_files:
        print("\nNon-compliant files:")
        for file_name, _ in non_compliant_files:
            print(f"  - {file_name}")

    # Return exit code based on compliance
    return 0 if len(non_compliant_files) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())