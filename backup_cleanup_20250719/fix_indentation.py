#!/usr/bin/env python3
"""
Fix indentation of health_check methods that are incorrectly nested inside other methods.
This script identifies health_check methods that are indented at 8 spaces or more
(indicating they're nested inside another method) and fixes their indentation to match
the class level methods (4 spaces).
"""

import os
import re
import sys
import argparse
from pathlib import Path

# Regular expression to find health_check method with excessive indentation
# This matches 8 or more spaces followed by "def health_check"
HEALTH_CHECK_PATTERN = re.compile(r'^(\s{8,})def\s+health_check\s*\(')

# Regular expression to capture the entire health_check method block
# This captures the method signature and all indented lines that follow
def extract_health_check_block(content, start_index):
    """Extract the entire health_check method block starting from start_index."""
    lines = content.splitlines()
    if start_index >= len(lines):
        return None, (start_index, start_index)
    
    # Get the indentation of the health_check method
    match = HEALTH_CHECK_PATTERN.match(lines[start_index])
    if not match:
        return None, (start_index, start_index)
    
    indentation = match.group(1)
    indent_level = len(indentation)
    
    # Extract the method block
    block_lines = [lines[start_index]]
    i = start_index + 1
    
    while i < len(lines):
        line = lines[i]
        # If we encounter a line with same or less indentation than the method,
        # we've reached the end of the block
        if line.strip() and len(line) - len(line.lstrip()) <= indent_level:
            break
        block_lines.append(lines[i])
        i += 1
    
    # Join the block lines
    block = '\n'.join(block_lines)
    
    return block, (start_index, i)

def fix_indentation(content):
    """Fix indentation of health_check methods in the content."""
    lines = content.splitlines()
    modified = False
    
    # Find all occurrences of health_check methods with excessive indentation
    i = 0
    while i < len(lines):
        match = HEALTH_CHECK_PATTERN.match(lines[i])
        if match:
            # Extract the health_check method block
            block, (start, end) = extract_health_check_block(content, i)
            if block:
                # Fix the indentation (change to 4 spaces)
                fixed_block = re.sub(r'^(\s{8,})', '    ', block, flags=re.MULTILINE)
                
                # Replace the block in the content
                new_lines = lines[:start] + fixed_block.splitlines() + lines[end:]
                content = '\n'.join(new_lines)
                lines = new_lines
                modified = True
                
                # Skip ahead to avoid processing the same block again
                i = end
                continue
        i += 1
    
    return content, modified

def process_file(file_path):
    """Process a single file to fix health_check method indentation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed_content, modified = fix_indentation(content)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"Fixed indentation in {file_path}")
            return True
        else:
            print(f"No changes needed in {file_path}")
            return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def find_agent_files(directory):
    """Find all Python files that might be agent files."""
    agent_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                # Simple heuristic: check if the file contains 'Agent' in the name
                # or if it's in an 'agents' directory
                if ('agent' in file.lower() or 
                    'agents' in os.path.basename(root).lower() or
                    'src/core' in os.path.join(root, file).lower()):
                    agent_files.append(file_path)
    return agent_files

def main():
    parser = argparse.ArgumentParser(description='Fix indentation of health_check methods in agent files')
    parser.add_argument('--directory', '-d', default='.', help='Directory to search for agent files')
    args = parser.parse_args()
    
    directory = os.path.abspath(args.directory)
    print(f"Searching for agent files in {directory}")
    
    agent_files = find_agent_files(directory)
    print(f"Found {len(agent_files)} potential agent files")
    
    fixed_count = 0
    for file_path in agent_files:
        if process_file(file_path):
            fixed_count += 1
    
    print(f"Fixed indentation in {fixed_count} files")

if __name__ == "__main__":
    main() 