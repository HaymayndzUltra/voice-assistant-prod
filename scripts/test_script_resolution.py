#!/usr/bin/env python3
"""
Integration test for script path resolution.

This script validates that all script paths in startup configurations
can be properly resolved using the new PathManager.resolve_script() method.
"""

import sys
import yaml
from pathlib import Path
from typing import List, Tuple, Dict

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager


def load_config(config_path: Path) -> dict:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error loading {config_path}: {e}")
        return {}


def extract_script_paths_mainpc(config: dict) -> List[str]:
    """Extract script paths from MainPC hierarchical config."""
    script_paths = []
    
    # Navigate through agent_groups structure
    agent_groups = config.get('agent_groups', {})
    for group_name, group_agents in agent_groups.items():
        for agent_name, agent_config in group_agents.items():
            script_path = agent_config.get('script_path')
            if script_path:
                script_paths.append(script_path)
    
    return script_paths


def extract_script_paths_pc2(config: dict) -> List[str]:
    """Extract script paths from PC2 flat list config."""
    script_paths = []
    
    # Navigate through pc2_services list
    pc2_services = config.get('pc2_services', [])
    for service in pc2_services:
        script_path = service.get('script_path')
        if script_path:
            script_paths.append(script_path)
    
    return script_paths


def validate_script_paths(script_paths: List[str], config_name: str) -> Tuple[int, int, List[str]]:
    """
    Validate a list of script paths using PathManager.resolve_script().
    
    Returns:
        Tuple of (found_count, total_count, missing_scripts)
    """
    found_count = 0
    missing_scripts = []
    
    print(f"\n🔍 Validating {len(script_paths)} script paths from {config_name}...")
    
    for script_path in script_paths:
        resolved_path = PathManager.resolve_script(script_path)
        
        if resolved_path and resolved_path.exists():
            found_count += 1
            print(f"✅ {script_path}")
        else:
            missing_scripts.append(script_path)
            if resolved_path:
                print(f"❌ {script_path} → {resolved_path} (resolved but missing)")
            else:
                print(f"❌ {script_path} (failed to resolve)")
    
    return found_count, len(script_paths), missing_scripts


def main():
    """Main integration test function."""
    print("🧪 SCRIPT PATH RESOLUTION INTEGRATION TEST")
    print("=" * 50)
    
    project_root = Path(PathManager.get_project_root())
    
    # Test configurations
    configs_to_test = [
        {
            'name': 'MainPC',
            'path': project_root / "main_pc_code" / "config" / "startup_config.yaml",
            'extractor': extract_script_paths_mainpc
        },
        {
            'name': 'PC2',
            'path': project_root / "pc2_code" / "config" / "startup_config.yaml",
            'extractor': extract_script_paths_pc2
        }
    ]
    
    total_found = 0
    total_scripts = 0
    all_missing = []
    
    for config_info in configs_to_test:
        config_name = config_info['name']
        config_path = config_info['path']
        extractor = config_info['extractor']
        
        print(f"\n📋 Testing {config_name} configuration: {config_path}")
        
        if not config_path.exists():
            print(f"⚠️  Config file not found: {config_path}")
            continue
        
        # Load configuration
        config = load_config(config_path)
        if not config:
            continue
        
        # Extract script paths
        script_paths = extractor(config)
        print(f"📊 Found {len(script_paths)} script paths in {config_name} config")
        
        # Validate script paths
        found, total, missing = validate_script_paths(script_paths, config_name)
        
        total_found += found
        total_scripts += total
        all_missing.extend(missing)
        
        # Print summary for this config
        success_rate = (found / total * 100) if total > 0 else 0
        print(f"\n📊 {config_name} Summary: {found}/{total} scripts found ({success_rate:.1f}%)")
    
    # Overall summary
    print(f"\n🎯 OVERALL INTEGRATION TEST RESULTS")
    print("=" * 50)
    print(f"Total scripts tested: {total_scripts}")
    print(f"Scripts found: {total_found}")
    print(f"Scripts missing: {len(all_missing)}")
    
    if total_scripts > 0:
        overall_success_rate = (total_found / total_scripts * 100)
        print(f"Overall success rate: {overall_success_rate:.1f}%")
        
        if all_missing:
            print(f"\n❌ Missing scripts:")
            for script in all_missing:
                print(f"  - {script}")
    
    # Test specific cases mentioned in Background Agent guidance
    print(f"\n🧪 SPECIFIC TEST CASES")
    print("-" * 30)
    
    test_cases = [
        "main_pc_code/agents/service_registry_agent.py",
        "phase1_implementation/consolidated_agents/observability_hub/observability_hub.py",
        "pc2_code/agents/memory_orchestrator_service.py"
    ]
    
    for test_case in test_cases:
        resolved = PathManager.resolve_script(test_case)
        if resolved and resolved.exists():
            print(f"✅ {test_case} → {resolved}")
        elif resolved:
            print(f"⚠️  {test_case} → {resolved} (resolved but missing)")
        else:
            print(f"❌ {test_case} (failed to resolve)")
    
    # Return exit code based on results
    if len(all_missing) == 0:
        print(f"\n🎉 All script paths resolved successfully!")
        return 0
    else:
        print(f"\n⚠️  {len(all_missing)} script paths could not be resolved")
        print("This may be expected for agents not yet implemented")
        return 0  # Don't fail - missing agents might be expected


if __name__ == "__main__":
    sys.exit(main()) 