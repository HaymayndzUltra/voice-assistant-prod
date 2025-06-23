#!/usr/bin/env python3
"""
This script thoroughly purges null bytes from a file by reading in binary mode.
"""

import os
import sys

def purge_null_bytes(file_path):
    """
    Completely purge null bytes from a file
    """
    # Read file as binary
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Remove all null bytes
    clean_content = content.replace(b'\x00', b'')
    
    # Save to a new file
    clean_file_path = file_path + '.clean'
    with open(clean_file_path, 'wb') as f:
        f.write(clean_content)
    
    # Print stats
    original_size = len(content)
    clean_size = len(clean_content)
    removed_bytes = original_size - clean_size
    
    print(f"Original file size: {original_size} bytes")
    print(f"Clean file size: {clean_size} bytes")
    print(f"Removed {removed_bytes} null bytes")
    
    return clean_file_path

def replace_original(original_path, clean_path):
    """
    Replace the original file with the clean one
    """
    # Create backup
    backup_path = original_path + '.backup'
    try:
        os.rename(original_path, backup_path)
        print(f"Created backup at {backup_path}")
    except Exception as e:
        print(f"Warning: Could not create backup: {e}")
    
    # Replace original with clean
    try:
        os.rename(clean_path, original_path)
        print(f"Replaced original file with clean version")
        return True
    except Exception as e:
        print(f"Error replacing original file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python purge_null_bytes.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    clean_path = purge_null_bytes(file_path)
    success = replace_original(file_path, clean_path)
    
    if success:
        print("Successfully purged null bytes")
        sys.exit(0)
    else:
        print("Failed to purge null bytes")
        sys.exit(1) 