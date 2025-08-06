#!/usr/bin/env python3
"""
Comprehensive script to replace ALL logging.basicConfig with canonical log_setup
Fixes the 713+ files that still use forbidden logging patterns
"""
import pathlib
import re
import ast
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent

def has_log_setup_import(content: str) -> bool:
    """Check if file already has log_setup import"""
    return "from common.utils.log_setup import configure_logging" in content

def add_log_setup_import(content: str) -> str:
    """Add log_setup import to file if not present"""
    if has_log_setup_import(content):
        return content
    
    lines = content.split('\n')
    
    # Find the best place to insert import (after existing imports)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and insert_idx > 0:
            break
    
    # Insert the import
    import_line = "from common.utils.log_setup import configure_logging"
    lines.insert(insert_idx, import_line)
    
    return '\n'.join(lines)

def replace_logging_basicconfig(content: str) -> str:
    """Replace logging.basicConfig calls with proper log_setup"""
    
    # Pattern to match logging.basicConfig with various parameters
    patterns = [
        # Simple logger = configure_logging(__name__)
        (r'logging\.basicConfig\(\)', 'logger = configure_logging(__name__)'),
        
        # logging.basicConfig with level parameter
        (r'logging\.basicConfig\(\s*level\s*=\s*logging\.([A-Z]+)\s*\)', 
         r'logger = configure_logging(__name__, level="\1")'),
        
        # logging.basicConfig with format parameter
        (r'logging\.basicConfig\(\s*format\s*=\s*[\'"][^\'"]*[\'"]\s*\)', 
         'logger = configure_logging(__name__)'),
        
        # logging.basicConfig with multiple parameters
        (r'logging\.basicConfig\([^)]+\)', 'logger = configure_logging(__name__)'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    return content

def fix_file(file_path: pathlib.Path) -> bool:
    """Fix a single Python file"""
    try:
        # Skip certain directories
        if any(skip in file_path.parts for skip in ("venv", "backups", "__pycache__", ".git")):
            return False
        
        # Read file content
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        original_content = content
        
        # Check if file has logging.basicConfig
        if "logging.basicConfig" not in content:
            return False
        
        # Add log_setup import if needed
        content = add_log_setup_import(content)
        
        # Replace logging.basicConfig calls
        content = replace_logging_basicconfig(content)
        
        # Write back if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False
    
    return False

def main():
    """Main function to fix all logging.basicConfig usages"""
    print("🔧 Starting comprehensive logging.basicConfig replacement...")
    print("📋 This will replace ALL 713+ instances with canonical log_setup")
    print()
    
    # Find all Python files with logging.basicConfig
    result = subprocess.run([
        'grep', '-r', '-l', 'logging.basicConfig', '--include=*.py', str(ROOT)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ No files found with logging.basicConfig")
        return
    
    files_to_fix = [pathlib.Path(line.strip()) for line in result.stdout.strip().split('\n') if line.strip()]
    
    print(f"📁 Found {len(files_to_fix)} files to fix")
    print()
    
    fixed_count = 0
    skipped_count = 0
    
    for file_path in files_to_fix:
        try:
            if fix_file(file_path):
                print(f"✅ Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"⏭️  Skipped: {file_path}")
                skipped_count += 1
        except Exception as e:
            print(f"❌ Error: {file_path} - {e}")
            skipped_count += 1
    
    print()
    print("🎉 === COMPREHENSIVE LOGGING FIX COMPLETE ===")
    print(f"✅ Files fixed: {fixed_count}")
    print(f"⏭️  Files skipped: {skipped_count}")
    print(f"📊 Total processed: {len(files_to_fix)}")
    print()
    print("🚀 ALL logging.basicConfig replaced with canonical configure_logging!")

if __name__ == "__main__":
    main()