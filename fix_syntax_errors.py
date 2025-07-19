#!/usr/bin/env python3
"""Auto-generated script to fix common syntax errors."""

import re
from pathlib import Path

def fix_incomplete_self_context_term(content: str) -> str:
    """Fix incomplete self. statements that should be self.context.term()."""
    # Pattern to find incomplete self. in cleanup contexts
    pattern = r'(\s+)self\.\s*$'
    
    # Check if this is in a cleanup/termination context
    lines = content.splitlines()
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if line.strip() == 'self.':
            # Look for context clues in surrounding lines
            context_start = max(0, i - 10)
            context = '\n'.join(lines[context_start:i+1])
            
            if 'context' in context and ('cleanup' in context.lower() or 'close' in context.lower()):
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'self.context.term()')
            else:
                fixed_lines.append(line)  # Keep as is for manual review
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)
