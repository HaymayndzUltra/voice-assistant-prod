#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to standardize imports across the codebase.

This script updates import statements to follow the standardized pattern:
- For scripts within main_pc_code, imports must start with 'from main_pc_code...'
- For scripts within pc2_code, imports must start with 'from pc2_code...'
"""

import os
import re
import sys
from pathlib import Path

# Regular expressions for matching import patterns
RELATIVE_IMPORT_PATTERN = re.compile(r'^from\s+\.(\S+)\s+import\s+(.+)$')
AMBIGUOUS_IMPORT_PATTERN = re.compile(r'^from\s+(utils|src|config|agents|integration)(\.\S+)?\s+import\s+(.+)$')
INTERNAL_IMPORT_PATTERN = re.compile(r'^from\s+(main_pc_code|pc2_code)(\.\S+)?\s+import\s+(.+)$')

# Directories to process
MAIN_PC_CODE_DIR = Path('main_pc_code')
PC2_CODE_DIR = Path('pc2_code')

# Count of files processed and modified
files_processed = 0
files_modified = 0
import_statements_updated = 0

def standardize_imports_in_file(file_path):
    """
    Standardize import statements in a single file.
    
    Args:
        file_path (Path): Path to the file to process
        
    Returns:
        bool: True if file was modified, False otherwise
    """
    global import_statements_updated
    
    # Determine the root package based on file location
    if 'main_pc_code' in str(file_path):
        root_package = 'main_pc_code'
    elif 'pc2_code' in str(file_path):
        root_package = 'pc2_code'
    else:
        # Skip files not in either directory
        return False
    
    # Read the file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"Warning: Could not read {file_path} as UTF-8, skipping")
        return False
    
    modified = False
    new_lines = []
    
    for line in lines:
        # Check for relative imports (.module)
        rel_match = RELATIVE_IMPORT_PATTERN.match(line.strip())
        if rel_match:
            # Get the relative module and imports
            rel_module = rel_match.group(1)
            imports = rel_match.group(2)
            
            # Calculate the absolute module path
            file_dir = file_path.parent
            rel_path = file_dir.relative_to(root_package)
            abs_module = f"{root_package}.{rel_path}.{rel_module}".replace('/', '.')
            
            # Create the new import statement
            new_line = f"from {abs_module} import {imports}\n"
            new_lines.append(new_line)
            modified = True
            import_statements_updated += 1
            continue
        
        # Check for ambiguous imports (utils, src, config, etc.)
        amb_match = AMBIGUOUS_IMPORT_PATTERN.match(line.strip())
        if amb_match and not INTERNAL_IMPORT_PATTERN.match(line.strip()):
            # Get the module and imports
            module = amb_match.group(1)
            submodule = amb_match.group(2) or ''
            imports = amb_match.group(3)
            
            # Create the new import statement
            new_line = f"from {root_package}.{module}{submodule} import {imports}\n"
            new_lines.append(new_line)
            modified = True
            import_statements_updated += 1
            continue
        
        # Keep other lines unchanged
        new_lines.append(line)
    
    # Write the file if modified
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    
    return modified

def process_directory(directory):
    """
    Process all Python files in a directory and its subdirectories.
    
    Args:
        directory (Path): Directory to process
    """
    global files_processed, files_modified
    
    for item in directory.glob('**/*.py'):
        if item.is_file():
            files_processed += 1
            if standardize_imports_in_file(item):
                files_modified += 1
                print(f"Updated imports in: {item}")

def main():
    """Main function to process both directories."""
    print("Starting import standardization...")
    
    # Process main_pc_code directory
    if MAIN_PC_CODE_DIR.exists():
        print(f"Processing {MAIN_PC_CODE_DIR}...")
        process_directory(MAIN_PC_CODE_DIR)
    else:
        print(f"Warning: {MAIN_PC_CODE_DIR} not found")
    
    # Process pc2_code directory
    if PC2_CODE_DIR.exists():
        print(f"Processing {PC2_CODE_DIR}...")
        process_directory(PC2_CODE_DIR)
    else:
        print(f"Warning: {PC2_CODE_DIR} not found")
    
    # Print summary
    print("\nImport standardization complete!")
    print(f"Files processed: {files_processed}")
    print(f"Files modified: {files_modified}")
    print(f"Import statements updated: {import_statements_updated}")

if __name__ == "__main__":
    main() 