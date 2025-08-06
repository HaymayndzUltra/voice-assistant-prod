#!/usr/bin/env python3
"""
Mass fix for logging configuration corruption
Fixes all files with corrupted configure_logging calls
"""

import os
import re
import glob

def fix_logging_corruption():
    """Fix corrupted configure_logging calls in all Python files"""
    
    # Pattern to match corrupted logging calls
    pattern = r"configure_logging\(__name__\)[^)]*%\([^)]*\)[^']*'[^)]*\)"
    
    # Replacement
    replacement = "configure_logging(__name__)"
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    fixed_count = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file has corruption
            if re.search(pattern, content):
                # Fix the corruption
                fixed_content = re.sub(pattern, replacement, content)
                
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print(f"✅ Fixed: {file_path}")
                fixed_count += 1
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n🎉 Fixed {fixed_count} files with logging corruption")

if __name__ == "__main__":
    fix_logging_corruption()
