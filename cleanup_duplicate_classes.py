#!/usr/bin/env python3
"""
Duplicate Class Cleanup Script
=============================
Removes duplicate class definitions safely while keeping the working versions.
"""

import os
import shutil
import sys
from pathlib import Path

# Duplicate directories/files to remove (keeping working versions)
DUPLICATE_PATHS_TO_DELETE = [
    # ModelManagerSuite duplicates (keep main_pc_code/11.py as working version)
    "phase1_implementation/group_02_model_manager_suite/",
    "phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/",
    
    # ErrorBusSuite duplicates (keep newer phase1 version)  
    "phase0_implementation/group_02_resource_scheduling/error_bus/",
    
    # Duplicate BaseAgent implementation (keep common.core.base_agent as source of truth)
    "main_pc_code/agents/base_agent.py",
    
    # Other duplicate restore functions
    "scripts/pc2_restore_functionality.py",
    "scripts/restore_all_agents.py",
]

# Individual files with duplicate functions to clean
FILES_WITH_DUPLICATE_FUNCTIONS = [
    # Files with local get_main_pc_code() definitions (should use common.utils.path_env version)
    {
        "file": "main_pc_code/agents/gguf_model_manager.py",
        "function": "get_main_pc_code",
        "lines_to_remove": (12, 16)  # Approximate lines, will need verification
    },
    {
        "file": "main_pc_code/agents/tone_detector.py", 
        "function": "get_main_pc_code",
        "lines_to_remove": (5, 9)
    },
    {
        "file": "main_pc_code/11.py",
        "function": "get_main_pc_code", 
        "lines_to_remove": (47, 52)
    }
]

def backup_before_delete(path: str) -> str:
    """Create a backup before deleting."""
    backup_dir = "CLEANUP_BACKUPS"
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.isfile(path):
        backup_path = os.path.join(backup_dir, os.path.basename(path))
        shutil.copy2(path, backup_path)
    elif os.path.isdir(path):
        backup_path = os.path.join(backup_dir, os.path.basename(path.rstrip('/')))
        shutil.copytree(path, backup_path, dirs_exist_ok=True)
    
    return backup_path

def remove_duplicate_path(path: str) -> bool:
    """Remove a duplicate directory or file."""
    if not os.path.exists(path):
        print(f"⚠️  Path not found (already clean): {path}")
        return True
    
    try:
        # Create backup first
        backup_path = backup_before_delete(path)
        print(f"📁 Backed up to: {backup_path}")
        
        # Remove the duplicate
        if os.path.isfile(path):
            os.remove(path)
            print(f"🗑️  Removed duplicate file: {path}")
        elif os.path.isdir(path):
            shutil.rmtree(path)
            print(f"🗑️  Removed duplicate directory: {path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error removing {path}: {e}")
        return False

def fix_duplicate_function(file_info: dict) -> bool:
    """Remove duplicate function from a file."""
    file_path = file_info["file"]
    function_name = file_info["function"]
    
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the function definition
        if f"def {function_name}(" not in content:
            print(f"ℹ️  Function {function_name} not found in {file_path}")
            return True
            
        # Add import statement if removing get_main_pc_code
        if function_name == "get_main_pc_code":
            if "from common.utils.path_env import get_main_pc_code" not in content:
                # Add the proper import
                import_lines = []
                other_lines = []
                in_imports = True
                
                for line in content.split('\n'):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_lines.append(line)
                    elif line.strip() == '':
                        if in_imports:
                            import_lines.append(line)
                        else:
                            other_lines.append(line)
                    else:
                        in_imports = False
                        other_lines.append(line)
                
                # Add the correct import
                import_lines.append("from common.utils.path_env import get_main_pc_code")
                
                # Remove local definition (simple approach - remove def block)
                content = '\n'.join(import_lines + other_lines)
                
                # Remove the local function definition
                import re
                pattern = rf'def {function_name}\([^)]*\):.*?(?=\n\S|\n*$)'
                content = re.sub(pattern, '', content, flags=re.DOTALL)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Fixed duplicate {function_name} in: {file_path}")
                return True
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing {function_name} in {file_path}: {e}")
        return False

def main():
    """Main execution function."""
    print("🧹 Duplicate Class Cleanup Script")
    print("=" * 50)
    
    # Phase 1: Remove duplicate directories/files
    print("\n📂 Phase 1: Removing duplicate directories/files...")
    removed_paths = 0
    for path in DUPLICATE_PATHS_TO_DELETE:
        if remove_duplicate_path(path):
            removed_paths += 1
    
    # Phase 2: Fix duplicate functions
    print("\n🔧 Phase 2: Fixing duplicate functions...")
    fixed_functions = 0
    for file_info in FILES_WITH_DUPLICATE_FUNCTIONS:
        if fix_duplicate_function(file_info):
            fixed_functions += 1
    
    print("\n" + "=" * 50)
    print(f"📊 CLEANUP SUMMARY:")
    print(f"   Duplicate paths removed: {removed_paths}/{len(DUPLICATE_PATHS_TO_DELETE)}")
    print(f"   Duplicate functions fixed: {fixed_functions}/{len(FILES_WITH_DUPLICATE_FUNCTIONS)}")
    
    print("\n✅ Duplicate cleanup complete!")
    print("📌 Working versions preserved:")
    print("   - BaseAgent: common.core.base_agent")
    print("   - ModelManagerSuite: main_pc_code/11.py") 
    print("   - get_main_pc_code: common.utils.path_env")

if __name__ == "__main__":
    main() 