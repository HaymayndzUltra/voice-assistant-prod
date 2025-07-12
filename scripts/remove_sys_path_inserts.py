#!/usr/bin/env python3
"""
Script to help identify and remove sys.path.insert calls from the codebase.
This is part of the packaging modernization effort.
"""

import os
import re
import argparse
from pathlib import Path
import ast
import sys
from typing import List, Dict, Tuple, Optional

# Directories to exclude from scanning
EXCLUDED_DIRS = [
    '.venv',
    'venv',
    '.git',
    'python_files_backup',
    '__pycache__',
    'cache',
    'logs',
    'temp',
]

class SysPathVisitor(ast.NodeVisitor):
    """AST visitor to find sys.path.insert calls"""
    
    def __init__(self):
        self.sys_path_inserts = []
        
    def visit_Call(self, node):
        # Check if this is a sys.path.insert call
        if (isinstance(node.func, ast.Attribute) and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'sys' and
            node.func.attr == 'path' and
            hasattr(node.func, 'attr') and
            node.func.attr == 'insert'):
            
            self.sys_path_inserts.append(node)
        
        self.generic_visit(node)

def should_exclude(path: str) -> bool:
    """Check if a path should be excluded from scanning"""
    for excluded in EXCLUDED_DIRS:
        if f'/{excluded}/' in path or path.endswith(f'/{excluded}'):
            return True
    return False

def find_files_with_sys_path_insert(directory: str) -> Dict[str, List[Tuple[int, str]]]:
    """Find all Python files with sys.path.insert calls"""
    result = {}
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if should_exclude(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Simple regex check first for efficiency
                    if re.search(r'sys\.path\.insert', content):
                        matches = []
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'sys.path.insert' in line:
                                matches.append((i + 1, line.strip()))
                        
                        if matches:
                            result[file_path] = matches
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return result

def analyze_directory(directory: str) -> None:
    """Analyze a directory for sys.path.insert calls"""
    files_with_inserts = find_files_with_sys_path_insert(directory)
    
    if not files_with_inserts:
        print(f"No sys.path.insert calls found in {directory}")
        return
    
    print(f"Found {len(files_with_inserts)} files with sys.path.insert calls:")
    for file_path, matches in files_with_inserts.items():
        print(f"\n{file_path}:")
        for line_num, line in matches:
            print(f"  Line {line_num}: {line}")

def main():
    parser = argparse.ArgumentParser(description='Find and analyze sys.path.insert calls')
    parser.add_argument('directory', nargs='?', default='.', 
                        help='Directory to analyze (default: current directory)')
    parser.add_argument('--count', action='store_true',
                        help='Only show the count of affected files')
    
    args = parser.parse_args()
    
    if args.count:
        files = find_files_with_sys_path_insert(args.directory)
        print(f"Found {len(files)} files with sys.path.insert calls")
    else:
        analyze_directory(args.directory)

if __name__ == '__main__':
    main() 