#!/usr/bin/env python3
"""
PC2 BaseAgent Import Cleanup Script
==================================
Fixes BaseAgent imports in PC2 agents to use the standard path
"""

import os
import re

# PC2 files that need BaseAgent import fixes  
PC2_FILES_TO_FIX = [
    "pc2_code/agents/LearningAdjusterAgent.py",
    "pc2_code/agents/test_compliant_agent.py",
    "pc2_code/agents/VisionProcessingAgent.py", 
    "pc2_code/agents/utils/pc2_agent_helpers.py"
]

# Import patterns to fix
PC2_IMPORT_FIXES = [
    # Fix wrong BaseAgent imports
    (
        r'from main_pc_code\.src\.core\.base_agent import BaseAgent',
        'from common.core.base_agent import BaseAgent'
    ),
    (
        r'from agents\.agent_utils import BaseAgent',
        'from common.core.base_agent import BaseAgent'
    ),
]

def fix_pc2_imports_in_file(file_path: str) -> bool:
    """Fix imports in a single PC2 file."""
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply import fixes
        for pattern, replacement in PC2_IMPORT_FIXES:
            content = re.sub(pattern, replacement, content)
        
        # Check if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed imports in: {file_path}")
            return True
        else:
            print(f"ℹ️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main execution function."""
    print("🔧 PC2 BaseAgent Import Cleanup Script")
    print("=" * 50)
    
    total_files = len(PC2_FILES_TO_FIX)
    files_fixed = 0
    
    for file_path in PC2_FILES_TO_FIX:
        if fix_pc2_imports_in_file(file_path):
            files_fixed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 PC2 SUMMARY:")
    print(f"   Total files processed: {total_files}")
    print(f"   Files fixed: {files_fixed}")
    
    print("\n✅ PC2 BaseAgent import cleanup complete!")
    print("📌 All PC2 agents now use: from common.core.base_agent import BaseAgent")

if __name__ == "__main__":
    main() 