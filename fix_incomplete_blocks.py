import os
import re
from pathlib import Path

def fix_incomplete_if_blocks(file_path):
    """Fix incomplete if statements with TODO-FIXME comments"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: if hasattr(self, 'socket'): followed by TODO-FIXME
    content = re.sub(
        r'(\s+if hasattr\(self, [\'"]socket[\'"]\)[^:]*:)\s*\n\s*# TODO-FIXME.*\n',
        r'\1\n                self.socket.close()\n',
        content
    )
    
    # Pattern 2: if hasattr(self, 'context'): followed by TODO-FIXME
    content = re.sub(
        r'(\s+if hasattr\(self, [\'"]context[\'"]\)[^:]*:)\s*\n\s*# TODO-FIXME.*\n',
        r'\1\n                self.context.term()\n',
        content
    )
    
    # Pattern 3: other socket types
    content = re.sub(
        r'(\s+if hasattr\(self, [\'"]([^"\']*socket[^"\']*)[\'"][^:]*:)\s*\n\s*# TODO-FIXME.*\n',
        r'\1\n                self.\2.close()\n',
        content
    )
    
    # Pattern 4: incomplete self. assignments
    content = re.sub(
        r'(\s+)(self\.[a-zA-Z_][a-zA-Z0-9_]*_)\s*\n',
        r'\1\2close()\n',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Process all Python files in agents directory
agents_dir = Path('main_pc_code/agents')
fixed_count = 0

for py_file in agents_dir.glob('*.py'):
    if fix_incomplete_if_blocks(py_file):
        print(f"✅ Fixed: {py_file}")
        fixed_count += 1

print(f"\n📊 Fixed {fixed_count} files with incomplete code blocks")
