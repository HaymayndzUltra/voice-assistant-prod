#!/usr/bin/env python3
"""
Python-based Markdown table formatter specifically for the AI System Monorepo.
This handles table formatting without requiring Node.js/Prettier.
"""

import re
import sys
from pathlib import Path

def format_markdown_table(content: str, max_width: int = 120) -> str:
    """Format Markdown tables to be properly aligned and readable."""
    lines = content.split('\n')
    formatted_lines = []
    in_table = False
    table_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this is a table line
        if stripped and '|' in stripped and not stripped.startswith('```'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
        else:
            # Process accumulated table if we were in one
            if in_table and table_lines:
                formatted_table = format_table_section(table_lines, max_width)
                formatted_lines.extend(formatted_table)
                table_lines = []
                in_table = False
            
            # Add non-table line
            formatted_lines.append(line)
    
    # Handle table at end of file
    if in_table and table_lines:
        formatted_table = format_table_section(table_lines, max_width)
        formatted_lines.extend(formatted_table)
    
    return '\n'.join(formatted_lines)

def format_table_section(table_lines: list, max_width: int = 120) -> list:
    """Format a section of table lines."""
    if not table_lines:
        return []
    
    # Parse table data
    rows = []
    for line in table_lines:
        # Clean up the line and split by |
        cells = [cell.strip() for cell in line.split('|')]
        # Remove empty cells at start/end
        if cells and not cells[0]:
            cells = cells[1:]
        if cells and not cells[-1]:
            cells = cells[:-1]
        if cells:  # Only add non-empty rows
            rows.append(cells)
    
    if not rows:
        return table_lines
    
    # Calculate column widths
    max_cols = max(len(row) for row in rows)
    col_widths = [0] * max_cols
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < max_cols:
                col_widths[i] = max(col_widths[i], len(cell))
    
    # Ensure minimum width and respect max_width
    min_width = 3
    for i in range(len(col_widths)):
        col_widths[i] = max(min_width, col_widths[i])
    
    # Adjust if total width exceeds max_width
    total_width = sum(col_widths) + (max_cols - 1) * 3 + 4  # | and spaces
    if total_width > max_width:
        # Proportionally reduce column widths
        excess = total_width - max_width
        for i in range(len(col_widths)):
            if col_widths[i] > min_width:
                reduction = min(excess, col_widths[i] - min_width)
                col_widths[i] -= reduction
                excess -= reduction
                if excess <= 0:
                    break
    
    # Format the table
    formatted_rows = []
    for row_idx, row in enumerate(rows):
        formatted_cells = []
        for i in range(max_cols):
            cell = row[i] if i < len(row) else ""
            
            # Handle long cell content
            if len(cell) > col_widths[i]:
                # For very long paths, try to break intelligently
                if '/' in cell and col_widths[i] > 20:
                    # Break on path separators
                    parts = cell.split('/')
                    if len(parts) > 2:
                        cell = '/'.join(parts[:2]) + '/...' + parts[-1]
                        if len(cell) > col_widths[i]:
                            cell = cell[:col_widths[i]-3] + "..."
                else:
                    cell = cell[:col_widths[i]-3] + "..."
            
            formatted_cells.append(cell.ljust(col_widths[i]))
        
        formatted_row = "| " + " | ".join(formatted_cells) + " |"
        formatted_rows.append(formatted_row)
        
        # Add separator after header (first row)
        if row_idx == 0:
            separator_cells = ["-" * width for width in col_widths]
            separator = "| " + " | ".join(separator_cells) + " |"
            formatted_rows.append(separator)
    
    return formatted_rows

def clean_markdown_formatting(content: str) -> str:
    """Clean up general Markdown formatting."""
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Fix common spacing issues
        line = re.sub(r'^(#{1,6})\s*', r'\1 ', line)  # Fix header spacing
        line = re.sub(r'\s+$', '', line)  # Remove trailing whitespace
        cleaned_lines.append(line)
    
    # Remove excessive blank lines
    result_lines = []
    blank_count = 0
    for line in cleaned_lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:  # Allow max 2 consecutive blank lines
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)
    
    return '\n'.join(result_lines)

def format_markdown_file(file_path: str, max_width: int = 120) -> bool:
    """Format a single Markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Format tables first
        formatted_content = format_markdown_table(content, max_width)
        
        # Clean up general formatting
        formatted_content = clean_markdown_formatting(formatted_content)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        print(f"✅ Formatted: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error formatting {file_path}: {e}")
        return False

def main():
    """Main function."""
    print("🔧 Python Markdown Table Formatter")
    print("")
    
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/format_markdown_tables.py <file1.md> [file2.md] ...")
        print("   or: python3 scripts/format_markdown_tables.py --width 100 <file1.md>")
        print("")
        print("Examples:")
        print("  python3 scripts/format_markdown_tables.py main_pc_code/agent_batch_list.md")
        print("  python3 scripts/format_markdown_tables.py --width 100 *.md")
        return 1
    
    # Parse arguments
    max_width = 120
    files = []
    i = 1
    
    while i < len(sys.argv):
        if sys.argv[i] == '--width' and i + 1 < len(sys.argv):
            max_width = int(sys.argv[i + 1])
            i += 2
        else:
            files.append(sys.argv[i])
            i += 1
    
    if not files:
        print("❌ No files specified")
        return 1
    
    success_count = 0
    for file_path in files:
        if Path(file_path).exists():
            if format_markdown_file(file_path, max_width):
                success_count += 1
        else:
            print(f"❌ File not found: {file_path}")
    
    print(f"\n✅ Successfully formatted {success_count} out of {len(files)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 