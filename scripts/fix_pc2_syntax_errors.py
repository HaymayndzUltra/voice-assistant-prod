#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick syntax fix script for PC2 agents after error bus integration."""

import os
import re
from pathlib import Path

def fix_syntax_errors(pc2_agents_dir: Path):
    """Fix common syntax errors in PC2 agents."""
    fixes_applied = 0
    
    for py_file in pc2_agents_dir.rglob("*.py"):
        if "_backup_" in str(py_file):
            continue
            
        try:
            content = py_file.read_text()
            original_content = content
            
            # Fix 1: Extra closing parenthesis in get_mainpc_ip() calls
            content = re.sub(r'get_mainpc_ip\(\)\)', 'get_mainpc_ip()', content)
            
            # Fix 2: Fix malformed constants with placeholders
            content = re.sub(r'\$\{SECRET_PLACEHOLDER\}', 'PLACEHOLDER_VAR =', content)
            
            # Fix 3: Fix misplaced imports in try-except blocks
            # Pattern: imports between except and the actual exception handling
            pattern = r'(except Exception as e:\s*import traceback\s*)(from common\.utils\.env_standardizer.*?\n)(.*?print\(f"An unexpected error occurred)'
            replacement = r'\1\3print(f"An unexpected error occurred'
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            # Fix 4: Move imports to proper location if they're misplaced
            if 'from pc2_code.utils.pc2_error_publisher import' in content:
                # Check if import is in wrong location (after main block)
                lines = content.split('\n')
                import_lines = []
                other_lines = []
                main_block_started = False
                
                for line in lines:
                    if 'if __name__ == "__main__":' in line:
                        main_block_started = True
                    
                    if ('from pc2_code.utils.pc2_error_publisher import' in line and 
                        main_block_started):
                        continue  # Skip misplaced import
                    else:
                        other_lines.append(line)
                
                content = '\n'.join(other_lines)
            
            if content != original_content:
                py_file.write_text(content)
                fixes_applied += 1
                print(f"✅ Fixed: {py_file.name}")
                
        except Exception as e:
            print(f"❌ Error fixing {py_file.name}: {e}")
    
    return fixes_applied

def main():
    """Main execution function."""
    project_root = Path(__file__).parent.parent
    pc2_agents_dir = project_root / "pc2_code" / "agents"
    
    print("🔧 Fixing PC2 agent syntax errors...")
    fixes = fix_syntax_errors(pc2_agents_dir)
    print(f"✅ Applied {fixes} syntax fixes")

if __name__ == "__main__":
    main()
