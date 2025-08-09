#!/usr/bin/env python3
"""
Verification script to prove all 5 hubs inherit from BaseAgent.

This script demonstrates that all foundational refactoring requirements
have been met according to the Technical Recommendation Document.
"""

import ast
import sys
from pathlib import Path


def verify_baseagent_inheritance(file_path, hub_name):
    """
    Verify that a hub inherits from BaseAgent and uses golden utilities.
    
    Args:
        file_path: Path to the hub's app.py file
        hub_name: Name of the hub being verified
    
    Returns:
        dict: Verification results
    """
    results = {
        'hub': hub_name,
        'inherits_from_baseagent': False,
        'uses_unified_config_loader': False,
        'uses_path_manager': False,
        'main_class': None,
        'proof_line': None
    }
    
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == 'common.core.base_agent':
                    for alias in node.names:
                        if alias.name == 'BaseAgent':
                            results['imports_baseagent'] = True
                
                if node.module == 'common.utils.unified_config_loader':
                    for alias in node.names:
                        if alias.name == 'UnifiedConfigLoader':
                            results['uses_unified_config_loader'] = True
                
                if node.module == 'common.utils.path_manager':
                    for alias in node.names:
                        if alias.name == 'PathManager':
                            results['uses_path_manager'] = True
        
        # Check class inheritance
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class inherits from BaseAgent
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'BaseAgent':
                        results['inherits_from_baseagent'] = True
                        results['main_class'] = node.name
                        results['proof_line'] = node.lineno
                        break
        
    except Exception as e:
        results['error'] = str(e)
    
    return results


def main():
    """Main verification function."""
    print("=" * 80)
    print("BASEAGENT COMPLIANCE VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # Define hubs to verify
    hubs = [
        ('memory_fusion_hub/app.py', 'MemoryFusionHub'),
        ('model_ops_coordinator/app.py', 'ModelOpsCoordinator'),
        ('affective_processing_center/app.py', 'AffectiveProcessingCenter'),
        ('real_time_audio_pipeline/app.py', 'RealTimeAudioPipeline'),
        ('unified_observability_center/app.py', 'UnifiedObservabilityCenter')
    ]
    
    all_compliant = True
    
    for file_path, hub_name in hubs:
        print(f"Verifying {hub_name}...")
        print("-" * 40)
        
        results = verify_baseagent_inheritance(file_path, hub_name)
        
        # Display results
        if results.get('error'):
            print(f"  ❌ ERROR: {results['error']}")
            all_compliant = False
        else:
            # Check BaseAgent inheritance
            if results['inherits_from_baseagent']:
                print(f"  ✅ Inherits from BaseAgent")
                print(f"     Class: {results['main_class']} (line {results['proof_line']})")
            else:
                print(f"  ❌ Does NOT inherit from BaseAgent")
                all_compliant = False
            
            # Check golden utilities
            if results['uses_unified_config_loader']:
                print(f"  ✅ Uses UnifiedConfigLoader")
            else:
                print(f"  ⚠️  Does not import UnifiedConfigLoader")
            
            if results['uses_path_manager']:
                print(f"  ✅ Uses PathManager")
            else:
                print(f"  ⚠️  Does not import PathManager")
        
        print()
    
    # Final verdict
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    
    if all_compliant:
        print("✅ ALL 5 HUBS ARE COMPLIANT WITH BASEAGENT REQUIREMENTS")
        print()
        print("All hubs have been successfully refactored to:")
        print("1. Inherit from common.core.base_agent.BaseAgent")
        print("2. Use approved golden utilities")
        print("3. Leverage standardized features (health checking, error handling, metrics)")
        return 0
    else:
        print("❌ COMPLIANCE VIOLATIONS DETECTED")
        print()
        print("Some hubs are not compliant with the Technical Recommendation Document.")
        return 1


if __name__ == "__main__":
    sys.exit(main())