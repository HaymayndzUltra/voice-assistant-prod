#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to automatically fix common errors found in the test execution.
This script addresses:
1. Syntax errors (missing except blocks, indentation)
2. Common import errors
"""

import os
import re
import sys
from pathlib import Path
import argparse

def fix_missing_except_blocks(file_path):
    """Fix missing except blocks in try statements"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern: 'try:' followed by an import, but no except
    pattern = r'(try:\s*\n\s*)(from|import)([^\n]*\n)(?!\s*except)'
    
    # Replace with try-except block
    replacement = r'\1\2\3    except ImportError as e:\n        print(f"Import error: {e}")\n'
    
    modified_content = re.sub(pattern, replacement, content)
    
    if content != modified_content:
        print(f"Fixing missing except block in {file_path}")
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    return False

def fix_indentation_errors(file_path):
    """Fix common indentation errors"""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for if statements without blocks
        if re.match(r'^\s*if.*:\s*$', line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            # If next line doesn't have more indentation, it's an error
            if not re.match(r'^\s+', next_line) and not next_line.strip().startswith(('else:', 'elif')):
                print(f"Fixing indentation error in {file_path} at line {i+1}")
                fixed_lines.append(line)
                fixed_lines.append('    pass  # Auto-fixed indentation error\n')
                modified = True
                i += 1
                continue
        
        fixed_lines.append(line)
        i += 1
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(fixed_lines)
        return True
    return False

def fix_common_import_errors(file_path):
    """Fix common import errors"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: 'import sy' -> 'import sys'
    pattern1 = r'import\s+sy\b'
    replacement1 = 'import sys'
    
    # Fix 2: Fix BaseAgentlogger.error syntax error
    pattern2 = r'from main_pc_code\.src\.core\.base_agent import BaseAgentlogger\.error'
    replacement2 = 'from main_pc_code.src.core.base_agent import BaseAgent\n# Fixed import error'
    
    # Apply fixes
    modified_content = re.sub(pattern1, replacement1, content)
    modified_content = re.sub(pattern2, replacement2, modified_content)
    
    if content != modified_content:
        print(f"Fixing import errors in {file_path}")
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    return False

def fix_consolidated_translator_imports(file_path):
    """Fix imports for consolidated_translator module"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix import paths for consolidated_translator
    pattern1 = r'from consolidated_translator import'
    replacement1 = 'from pc2_code.translation_components.consolidated_translator import'
    
    pattern2 = r'from pc2_code\.agents\.consolidated_translator import'
    replacement2 = 'from pc2_code.translation_components.consolidated_translator import'
    
    # Apply fixes
    modified_content = re.sub(pattern1, replacement1, content)
    modified_content = re.sub(pattern2, replacement2, modified_content)
    
    if content != modified_content:
        print(f"Fixing consolidated_translator imports in {file_path}")
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    return False

def process_file(file_path):
    """Process a single file and apply all fixes"""
    fixes_applied = 0
    
    if fix_missing_except_blocks(file_path):
        fixes_applied += 1
    
    if fix_indentation_errors(file_path):
        fixes_applied += 1
    
    if fix_common_import_errors(file_path):
        fixes_applied += 1
    
    if 'translator' in file_path.lower() and fix_consolidated_translator_imports(file_path):
        fixes_applied += 1
    
    return fixes_applied

def find_and_fix_files(directory, file_pattern=None):
    """Find and fix files in the given directory"""
    if file_pattern is None:
        file_pattern = r'.*\.(py)$'
    
    pattern = re.compile(file_pattern)
    total_fixes = 0
    files_fixed = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if pattern.match(file):
                file_path = os.path.join(root, file)
                fixes = process_file(file_path)
                if fixes > 0:
                    files_fixed += 1
                    total_fixes += fixes
    
    return files_fixed, total_fixes

def main():
    parser = argparse.ArgumentParser(description='Fix common errors in test files')
    parser.add_argument('--dir', default=None, help='Directory to process (default: main_pc_code and pc2_code)')
    parser.add_argument('--pattern', default=r'.*\.(py)$', help='File pattern to match (default: *.py)')
    args = parser.parse_args()
    
    if args.dir:
        directories = [args.dir]
    else:
        directories = ['main_pc_code', 'pc2_code']
    
    total_files_fixed = 0
    total_fixes_applied = 0
    
    for directory in directories:
        print(f"\nProcessing directory: {directory}")
        files_fixed, fixes_applied = find_and_fix_files(directory, args.pattern)
        total_files_fixed += files_fixed
        total_fixes_applied += fixes_applied
        print(f"Applied {fixes_applied} fixes to {files_fixed} files in {directory}")
    
    print(f"\nSummary: Applied {total_fixes_applied} fixes to {total_files_fixed} files")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 