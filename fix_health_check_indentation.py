#!/usr/bin/env python3
"""
Fix indentation of health_check methods that are incorrectly formatted.
This script identifies Python files with health_check methods that have incorrect indentation
and fixes them to match the class level methods (4 spaces).
"""

import os
import re
import sys
import argparse
from pathlib import Path

# Regular expression to find health_check method with incorrect indentation
# This matches any indentation followed by "def health_check"
HEALTH_CHECK_PATTERN = re.compile(r'^(\s*)def\s+health_check\s*\(')

# Regular expression to find the docstring following the health_check definition
DOCSTRING_PATTERN = re.compile(r'^(\s*)(?:"""|\'\'\')(.+?)(?:"""|\'\'\')$', re.DOTALL | re.MULTILINE)

def fix_health_check_indentation(file_path):
    """Fix indentation of health_check method in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.splitlines()
        modified = False
        i = 0

        # Find the health_check method
        while i < len(lines):
            match = HEALTH_CHECK_PATTERN.match(lines[i])
            if match:
                # Found a health_check method
                current_indent = match.group(1)

                # Determine the correct indentation (4 spaces)
                correct_indent = "    "

                # If the indentation is already correct, skip
                if current_indent == correct_indent:
                    i += 1
                    continue

                # Fix the indentation for this line and all following indented lines
                j = i
                block_lines = []

                # Collect all lines that belong to the health_check method
                while j < len(lines):
                    if j == i:  # First line (method definition)
                        block_lines.append(correct_indent + lines[j].lstrip())
                        j += 1
                        continue

                    if lines[j].strip() == "":
                        block_lines.append(lines[j])
                        j += 1
                        continue

                    # If we encounter a line with less or equal indentation to the class level,
                    # we've reached the end of the method
                    if not lines[j].startswith(current_indent) and lines[j].strip():
                        # Check if this is actually part of the method but with wrong indentation
                        if j > i + 1 and lines[j-1].strip().endswith((":", "{", "[")):
                            # This is likely part of the method with incorrect indentation
                            block_lines.append(correct_indent + "    " + lines[j].lstrip())
                            j += 1
                            continue
                        else:
                            # End of method
                            break

                    # Fix indentation for method body
                    if lines[j].startswith(current_indent):
                        # For method body, add an extra level of indentation
                        block_lines.append(correct_indent + "    " + lines[j][len(current_indent):].lstrip())
                    else:
                        # Line with incorrect indentation
                        block_lines.append(correct_indent + "    " + lines[j].lstrip())

                    j += 1

                # Replace the original lines with the fixed ones
                lines = lines[:i] + block_lines + lines[j:]
                modified = True
                i = i + len(block_lines)
            else:
                i += 1

        if modified:
            # Write the fixed content back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"Fixed health_check indentation in {file_path}")
            return True
        else:
            print(f"No indentation issues found in {file_path}")
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
    """TODO: Add description for main."""
    parser = argparse.ArgumentParser(description='Fix indentation of health_check methods in agent files')
    parser.add_argument('--directory', '-d', default='.', help='Directory to search for agent files')
    parser.add_argument('--file', '-f', help='Process a specific file')
    args = parser.parse_args()

    if args.file:
        file_path = os.path.abspath(args.file)
        if os.path.isfile(file_path):
            fix_health_check_indentation(file_path)
        else:
            print(f"File not found: {file_path}")
    else:
        directory = os.path.abspath(args.directory)
        print(f"Searching for agent files in {directory}")

        agent_files = find_agent_files(directory)
        print(f"Found {len(agent_files)} potential agent files")

        fixed_count = 0
        for file_path in agent_files:
            if fix_health_check_indentation(file_path):
                fixed_count += 1

        print(f"Fixed health_check indentation in {fixed_count} files")

if __name__ == "__main__":
    main()
