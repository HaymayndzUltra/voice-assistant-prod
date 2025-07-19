#!/usr/bin/env python3
"""
Comprehensive Duplicate Class Detector
Finds all duplicate class definitions across the codebase
"""

import ast
import os
import collections
from pathlib import Path

def find_duplicate_classes():
    """Find all duplicate class definitions"""
    root = Path('.')
    class_definitions = collections.defaultdict(list)
    
    # Scan all Python files
    for py_file in root.rglob('*.py'):
        # Skip certain directories
        if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'venv', 'env']):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find class definitions
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_definitions[node.name].append(str(py_file))
                    
        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors or encoding issues
            continue
    
    # Find duplicates
    duplicates = {class_name: locations for class_name, locations in class_definitions.items() 
                 if len(locations) > 1}
    
    return duplicates

def main():
    print("🔍 Scanning for duplicate class definitions...")
    duplicates = find_duplicate_classes()
    
    if not duplicates:
        print("✅ No duplicate classes found!")
        return
    
    print(f"🚨 Found {len(duplicates)} duplicate classes:")
    print()
    
    for class_name, locations in sorted(duplicates.items()):
        print(f"📍 {class_name}:")
        for location in locations:
            print(f"   - {location}")
        print()

if __name__ == "__main__":
    main() 