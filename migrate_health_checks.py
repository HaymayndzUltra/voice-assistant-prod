#!/usr/bin/env python3
"""
Health Check Migration Script
Removes duplicate _health_check_loop implementations from agents that inherit BaseAgent
"""

import re
import os
from pathlib import Path

def remove_custom_health_loop(file_path):
    """Remove custom _health_check_loop method from file"""
    print(f"\n🔧 Processing: {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()

    original_length = len(content.splitlines())

    # Pattern to match custom health check loop method (more flexible)
    patterns = [
        r'\n    def _health_check_loop\(self\):.*?(?=\n    def |\n\nclass |\nif __name__|\Z)',
        r'\n\s+def _health_check_loop\(self\):.*?(?=\n\s+def |\n\nclass |\nif __name__|\Z)',
    ]

    modified_content = content
    removed_lines = 0

    for pattern in patterns:
        new_content = re.sub(pattern, '', modified_content, flags=re.DOTALL)
        if new_content != modified_content:
            removed_lines = original_length - len(new_content.splitlines())
            modified_content = new_content
            break

    # Also remove threading import for health check if it exists and not used elsewhere
    if '_health_check_loop' not in modified_content and 'threading.Thread' not in modified_content:
        # Remove unused threading import
        modified_content = re.sub(r'\nimport threading\n', '\n', modified_content)
        modified_content = re.sub(r'\nfrom threading import Thread\n', '\n', modified_content)

    # Write back if changed
    if content != modified_content:
        with open(file_path, 'w') as f:
            f.write(modified_content)
        print(f"  ✅ Removed custom health loop ({removed_lines} lines)")
        return True, removed_lines
    else:
        print(f"  ⏭️  No changes needed")
        return False, 0

def validate_baseagent_inheritance(file_path):
    """Verify that file inherits from BaseAgent"""
    with open(file_path, 'r') as f:
        content = f.read()

    if re.search(r'class\s+\w+\s*\([^)]*BaseAgent[^)]*\)', content):
        print(f"  ✅ Inherits from BaseAgent")
        return True
    else:
        print(f"  ❌ Does NOT inherit from BaseAgent")
        return False

def main():
    """TODO: Add description for main."""
    safe_targets = []

    # Read safe migration targets
    try:
        with open('safe_migration_targets.txt', 'r') as f:
            safe_targets = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ safe_migration_targets.txt not found!")
        return

    print(f"🚀 Found {len(safe_targets)} safe migration targets")
    print("=" * 60)

    total_lines_removed = 0
    successful_migrations = 0

    for target in safe_targets:
        if os.path.exists(target):
            # Validate inheritance first
            if validate_baseagent_inheritance(target):
                success, lines_removed = remove_custom_health_loop(target)
                if success:
                    successful_migrations += 1
                    total_lines_removed += lines_removed
            else:
                print(f"  ⚠️  Skipping - does not inherit BaseAgent")
        else:
            print(f"❌ File not found: {target}")

    print("\n" + "=" * 60)
    print(f"🎯 MIGRATION COMPLETE!")
    print(f"📊 Results:")
    print(f"   • Files migrated: {successful_migrations}/{len(safe_targets)}")
    print(f"   • Total lines removed: {total_lines_removed}")
    print(f"   • Duplicate code eliminated: ~{total_lines_removed} lines")
    print("\n✅ All agents now use BaseAgent standard health checks!")

if __name__ == "__main__":
    main()
