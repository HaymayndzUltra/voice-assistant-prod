#!/usr/bin/env python3
import ast
import sys

file_path = 'main_pc_code/FORMAINPC/consolidated_translator.py'

# First, try to read the file
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"Successfully read file: {file_path}")
    print(f"File has {len(lines)} lines")
    
    # Try to parse in chunks to find the problematic section
    chunk_size = 200
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i:i+chunk_size]
        chunk_text = ''.join(chunk)
        try:
            ast.parse(chunk_text)
            print(f"Chunk from line {i+1} to {i+len(chunk)} parses successfully")
        except SyntaxError as e:
            line_in_chunk = e.lineno if hasattr(e, 'lineno') else '?'
            actual_line = i + line_in_chunk if hasattr(e, 'lineno') else '?'
            print(f"Syntax error in chunk from line {i+1} to {i+len(chunk)}")
            print(f"Error at line {actual_line}: {e}")
            
            # Print the problematic lines for context
            if hasattr(e, 'lineno') and e.lineno > 5:
                start = max(0, e.lineno - 5)
                end = min(len(chunk), e.lineno + 5)
                print("\nContext:")
                for j in range(start, end):
                    if j < len(chunk):
                        print(f"{i+j+1}: {chunk[j].rstrip()}")
            
except Exception as e:
    print(f'File read failed: {e}')
    sys.exit(1) 