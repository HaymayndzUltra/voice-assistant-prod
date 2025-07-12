#!/usr/bin/env python3
"""
Example script demonstrating how to refactor code to remove sys.path.insert calls.
This is part of the packaging modernization effort.
"""

import os
import argparse
from pathlib import Path
from typing import List, Dict, Optional

def refactor_file(file_path: str, dry_run: bool = True) -> bool:
    """
    Refactor a file to remove sys.path.insert calls and replace with proper imports.
    
    Args:
        file_path: Path to the Python file to refactor
        dry_run: If True, only show changes without applying them
        
    Returns:
        True if changes were made, False otherwise
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Track if we made any changes
    made_changes = False
    
    # Track imports to add
    imports_to_add = set()
    
    # New content without sys.path.insert calls
    new_lines = []
    skip_lines = set()
    
    # First pass: identify sys.path.insert calls and what imports they enable
    for i, line in enumerate(lines):
        if 'sys.path.insert' in line:
            # This is a simplistic approach - in a real implementation you'd need more sophisticated parsing
            if 'MAIN_PC_CODE_DIR' in line or 'main_pc_code' in line:
                imports_to_add.add('from main_pc_code')
                skip_lines.add(i)
                made_changes = True
            elif 'PC2_CODE_DIR' in line or 'pc2_code' in line:
                imports_to_add.add('from pc2_code')
                skip_lines.add(i)
                made_changes = True
            elif 'PROJECT_ROOT' in line:
                # This might enable imports from multiple directories
                imports_to_add.add('# Imports now available via pip install -e .')
                skip_lines.add(i)
                made_changes = True
    
    # Second pass: build new file content
    import_section_end = 0
    for i, line in enumerate(lines):
        if i in skip_lines:
            continue
            
        # Find the end of the import section
        if line.startswith('import ') or line.startswith('from '):
            import_section_end = i + 1
            
        new_lines.append(line)
    
    # Insert new imports at the end of the import section
    if imports_to_add:
        for imp in sorted(imports_to_add):
            new_lines.insert(import_section_end, f"{imp}\n")
            import_section_end += 1
    
    # Print or write changes
    if made_changes:
        if dry_run:
            print(f"Changes for {file_path}:")
            print("".join(new_lines))
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")
    
    return made_changes

def main():
    parser = argparse.ArgumentParser(description='Refactor code to remove sys.path.insert calls')
    parser.add_argument('file', help='Python file to refactor')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    
    args = parser.parse_args()
    
    refactor_file(args.file, not args.apply)

if __name__ == '__main__':
    main() 