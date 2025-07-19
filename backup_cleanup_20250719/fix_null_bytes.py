#!/usr/bin/env python3
"""
Script to detect and fix null bytes in the memory_orchestrator.py file
"""

import os
import sys
import re
import codecs

def fix_file(file_path):
    """
    Fix null bytes in a file and save a clean version
    """
    print(f"Processing file: {file_path}")
    
    try:
        # Try reading with different encodings
        encodings = ['utf-8', 'latin-1', 'ascii', 'utf-16']
        file_content = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    file_content = f.read()
                print(f"Successfully read file with {encoding} encoding")
                break
            except Exception as e:
                print(f"Failed to read with {encoding}: {e}")
        
        if file_content is None:
            print("Could not read file with any encoding, trying binary mode")
            with open(file_path, 'rb') as f:
                binary_content = f.read()
                # Replace null bytes with spaces
                binary_content = binary_content.replace(b'\x00', b' ')
                file_content = binary_content.decode('utf-8', errors='replace')
        
        # Count null bytes in the content
        null_byte_count = file_content.count('\x00')
        print(f"Found {null_byte_count} null bytes in the file content")
        
        # Replace null bytes with spaces
        clean_content = file_content.replace('\x00', ' ')
        
        # Remove any remaining control characters
        clean_content = re.sub(r'[\x00-\x1F\x7F]', ' ', clean_content)
        
        # Create a backup
        backup_path = file_path + '.backup'
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
        
        # Write the clean content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        
        print(f"Successfully cleaned the file: {file_path}")
        print(f"Removed {null_byte_count} null bytes")
        return True
        
    except Exception as e:
        print(f"Error fixing file: {e}")
        return False

if __name__ == "__main__":
    file_path = 'main_pc_code/src/memory/memory_orchestrator.py'
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    success = fix_file(file_path)
    
    if success:
        print("File successfully fixed")
        sys.exit(0)
    else:
        print("Failed to fix file")
        sys.exit(1) 