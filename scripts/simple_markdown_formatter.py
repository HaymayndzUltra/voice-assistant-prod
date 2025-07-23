#!/usr/bin/env python3
"""
Simple Markdown formatter that fixes basic formatting without breaking tables.
Perfect for agent_batch_list.md and similar files.
"""

import re
import sys
from pathlib import Path

def fix_markdown_formatting(content: str) -> str:
    """Fix basic Markdown formatting without breaking complex tables."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix header spacing
        if line.strip().startswith('#'):
            # Ensure proper spacing after hashtags
            line = re.sub(r'^(#{1,6})\s*', r'\1 ', line)
        
        # Remove trailing whitespace
        line = line.rstrip()
        
        # Fix table alignment (basic cleanup without restructuring)
        if '|' in line and not line.strip().startswith('```'):
            # Clean up extra spaces around pipes
            parts = line.split('|')
            cleaned_parts = []
            for part in parts:
                cleaned_parts.append(part.strip())
            line = ' | '.join(cleaned_parts)
            
            # Ensure table lines start and end with |
            if line.strip() and not line.strip().startswith('|'):
                line = '| ' + line.strip()
            if line.strip() and not line.strip().endswith('|'):
                line = line.strip() + ' |'
        
        fixed_lines.append(line)
    
    # Remove excessive blank lines (keep max 2 consecutive)
    result_lines = []
    blank_count = 0
    
    for line in fixed_lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)
    
    return '\n'.join(result_lines)

def format_file(file_path: str) -> bool:
    """Format a single Markdown file with basic cleanup."""
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Format
        formatted_content = fix_markdown_formatting(content)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        print(f"✅ Fixed formatting: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error formatting {file_path}: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🔧 Simple Markdown Formatter")
        print("")
        print("Usage: python3 scripts/simple_markdown_formatter.py <file1.md> [file2.md] ...")
        print("")
        print("This formatter will:")
        print("  ✅ Fix header spacing (# Header)")
        print("  ✅ Clean up table pipe alignment")
        print("  ✅ Remove trailing whitespace")
        print("  ✅ Reduce excessive blank lines")
        print("  ✅ Preserve all content and table structure")
        print("")
        print("Examples:")
        print("  python3 scripts/simple_markdown_formatter.py main_pc_code/agent_batch_list.md")
        print("  python3 scripts/simple_markdown_formatter.py *.md")
        return 1
    
    files = sys.argv[1:]
    success_count = 0
    
    for file_path in files:
        if Path(file_path).exists():
            if format_file(file_path):
                success_count += 1
        else:
            print(f"❌ File not found: {file_path}")
    
    print(f"\n✅ Successfully formatted {success_count} out of {len(files)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 