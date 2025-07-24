#!/usr/bin/env python3
"""
Enhanced IP Address Migration Script V2
Targets os.environ.get patterns with hardcoded IP fallbacks that were missed
Uses existing common/env_helpers.py + config_manager.py system
Focus: error_bus_host and similar patterns
"""

import re
import os
from pathlib import Path
from typing import List, Tuple

class EnhancedIPMigrator:
    """Enhanced IP address migration focusing on missed patterns"""
    
    def __init__(self):
        self.changes_made = []
        
    def find_environ_get_patterns(self, directory: str = '.') -> List[Tuple[str, int, str]]:
        """Find os.environ.get patterns with hardcoded IP fallbacks"""
        results = []
        
        for root, _, files in os.walk(directory):
            if any(skip in root for skip in ['.git', '__pycache__', '.venv', 'node_modules']):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line_num, line in enumerate(f, 1):
                                # Match os.environ.get with hardcoded IP fallbacks
                                if re.search(r"os\.environ\.get.*IP.*192\.168", line):
                                    results.append((file_path, line_num, line.strip()))
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return results
    
    def migrate_environ_get_patterns(self, file_path: str) -> bool:
        """Migrate os.environ.get patterns to use config manager"""
        print(f"\n🔧 Processing environ.get patterns: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading {file_path}: {e}")
            return False
        
        original_content = content
        changes = []
        
        # Add config manager import if not present
        has_config_import = 'config_manager' in content or 'get_service_ip' in content
        
        if not has_config_import:
            # Add import after existing imports
            if re.search(r'^(from|import)', content, re.MULTILINE):
                content = re.sub(
                    r'(\n)((?!from|import))', 
                    r'\1from common.config_manager import get_service_ip\n\2', 
                    content, 
                    count=1
                )
                changes.append("Added config_manager import")
        
        # Replace specific os.environ.get patterns
        replacements = [
            # Error bus host patterns
            (r"os\.environ\.get\('PC2_IP',\s*'192\.168\.100\.17'\)", 'get_service_ip("pc2")'),
            (r'os\.environ\.get\("PC2_IP",\s*"192\.168\.100\.17"\)', 'get_service_ip("pc2")'),
            (r"os\.environ\.get\('MAINPC_IP',\s*'192\.168\.100\.16'\)", 'get_service_ip("mainpc")'),
            (r'os\.environ\.get\("MAINPC_IP",\s*"192\.168\.100\.16"\)', 'get_service_ip("mainpc")'),
            (r"os\.environ\.get\('MAINPC_IP',\s*'192\.168\.100\.10'\)", 'get_service_ip("mainpc")'),
            (r'os\.environ\.get\("MAINPC_IP",\s*"192\.168\.100\.10"\)', 'get_service_ip("mainpc")'),
            
            # Service registry patterns
            (r"os\.environ\.get\('SERVICE_REGISTRY_HOST',\s*'192\.168\.100\.16'\)", 'get_service_ip("service_registry")'),
            (r'os\.environ\.get\("SERVICE_REGISTRY_HOST",\s*"192\.168\.100\.16"\)', 'get_service_ip("service_registry")'),
            
            # Redis host patterns  
            (r"os\.environ\.get\('REDIS_HOST',\s*'192\.168\.100\.16'\)", 'get_service_ip("redis")'),
            (r'os\.environ\.get\("REDIS_HOST",\s*"192\.168\.100\.16"\)', 'get_service_ip("redis")'),
            
            # Generic IP patterns with config.get fallback
            (r"os\.environ\.get\('PC2_IP',\s*config\.get\([^)]+,\s*'192\.168\.100\.17'\)\)", 'get_service_ip("pc2")'),
            (r'os\.environ\.get\("PC2_IP",\s*config\.get\([^)]+,\s*"192\.168\.100\.17"\)\)', 'get_service_ip("pc2")'),
        ]
        
        for pattern, replacement in replacements:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced {pattern[:50]}... with {replacement}")
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Migrated environ.get patterns ({len(changes)} changes)")
            for change in changes:
                print(f"    • {change}")
            self.changes_made.extend(changes)
            return True
        else:
            print(f"  ⏭️  No changes needed")
            return False


def main():
    migrator = EnhancedIPMigrator()
    
    print("🚀 Starting Enhanced IP Address Migration V2")
    print("🎯 Target: os.environ.get patterns with hardcoded IP fallbacks")
    print("=" * 70)
    
    # Find all os.environ.get patterns
    print("🔍 Scanning for os.environ.get patterns with hardcoded IPs...")
    patterns = migrator.find_environ_get_patterns()
    
    if not patterns:
        print("✅ No os.environ.get patterns with hardcoded IPs found!")
        return
    
    print(f"📊 Found {len(patterns)} os.environ.get patterns to migrate")
    
    # Group by file
    files_to_process = set()
    for file_path, line_num, line_content in patterns:
        files_to_process.add(file_path)
        print(f"  📍 {file_path}:{line_num} - {line_content[:80]}...")
    
    print(f"\n🔧 Processing {len(files_to_process)} files...")
    
    files_migrated = 0
    for file_path in files_to_process:
        if migrator.migrate_environ_get_patterns(file_path):
            files_migrated += 1
    
    print("\n" + "=" * 70)
    print(f"🎯 ENHANCED IP MIGRATION V2 COMPLETE!")
    print(f"📊 Results:")
    print(f"   • Patterns found: {len(patterns)}")
    print(f"   • Files processed: {len(files_to_process)}")
    print(f"   • Files migrated: {files_migrated}")
    print(f"   • Total changes: {len(migrator.changes_made)}")
    
    print(f"\n✅ Benefits Achieved:")
    print(f"   • Environment-aware error bus connections")
    print(f"   • Consistent service discovery patterns")
    print(f"   • Containerization ready for deployment")
    
    print(f"\n🚀 Next Steps:")
    print(f"   • Test error bus connectivity across environments")
    print(f"   • Verify service discovery in container mode")
    print(f"   • Deploy with environment variable overrides")

if __name__ == "__main__":
    main() 