#!/usr/bin/env python3
"""
Hard-coded IP Address Migration Script
Replaces hard-coded IP addresses with environment-aware configuration
Uses existing common/env_helpers.py + new config_manager.py system
Target: All files with 192.168.100.x IP addresses
"""

import re
import os
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Set

class IPMigrator:
    """Intelligent IP address migration using config manager"""

    def __init__(self):
        """TODO: Add description for __init__."""
        self.ip_patterns = [
            r'192\.168\.100\.16',  # MainPC
            r'192\.168\.100\.17',  # PC2
            r'192\.168\.100\.10',  # Alternative MainPC
            r'127\.0\.0\.1',       # Localhost
            r'localhost'           # Localhost string
        ]

        # Map IP patterns to service names
        self.ip_to_service = {
            '192.168.100.16': 'mainpc',
            '192.168.100.10': 'mainpc',
            '192.168.100.17': 'pc2',
            '127.0.0.1': 'localhost',
            'localhost': 'localhost'
        }

        self.changes_made = []

    def find_hardcoded_ips(self, directory: str = '.') -> List[Tuple[str, int, str]]:
        """Find all hard-coded IP addresses in files"""
        results = []

        # File types to check
        extensions = ['.py', '.yaml', '.yml', '.txt', '.sh', '.env']

        for root, _, files in os.walk(directory):
            # Skip certain directories
            if any(skip in root for skip in ['.git', '__pycache__', '.venv', 'node_modules']):
                continue

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line_num, line in enumerate(f, 1):
                                for pattern in self.ip_patterns:
                                    if re.search(pattern, line):
                                        results.append((file_path, line_num, line.strip()))
                    except (UnicodeDecodeError, PermissionError):
                        continue

        return results

    def migrate_docker_compose(self, file_path: str) -> bool:
        """Migrate Docker Compose files to use environment variables"""
        print(f"\n🔧 Processing Docker Compose: {file_path}")

        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading {file_path}: {e}")
            return False

        original_content = content
        changes = []

        # Replace specific IP patterns in Docker Compose
        replacements = [
            # Environment variable assignments
            (r'MAINPC_IP=192\.168\.100\.16', 'MAINPC_IP=${MAINPC_IP:-192.168.100.16}'),
            (r'MAINPC_IP=192\.168\.100\.10', 'MAINPC_IP=${MAINPC_IP:-192.168.100.16}'),
            (r'PC2_IP=192\.168\.100\.17', 'PC2_IP=${PC2_IP:-192.168.100.17}'),
            (r'SERVICE_REGISTRY_HOST=192\.168\.100\.16', 'SERVICE_REGISTRY_HOST=${SERVICE_REGISTRY_HOST:-192.168.100.16}'),
            (r'REDIS_HOST=192\.168\.100\.16', 'REDIS_HOST=${REDIS_HOST:-192.168.100.16}'),

            # Direct IP references in URLs
            (r'"redis://192\.168\.100\.16:6379"', '"redis://${REDIS_HOST:-192.168.100.16}:${REDIS_PORT:-6379}"'),
            (r'tcp://192\.168\.100\.16:', 'tcp://${MAINPC_IP:-192.168.100.16}:'),
            (r'tcp://192\.168\.100\.17:', 'tcp://${PC2_IP:-192.168.100.17}:'),

            # Health check URLs
            (r'http://localhost:(\d+)', r'http://${LOCALHOST:-localhost}:\1'),
            (r'tcp://localhost:(\d+)', r'tcp://${LOCALHOST:-localhost}:\1'),
        ]

        for pattern, replacement in replacements:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced {pattern} with {replacement}")

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Migrated Docker Compose ({len(changes)} changes)")
            for change in changes:
                print(f"    • {change}")
            self.changes_made.extend(changes)
            return True
        else:
            print(f"  ⏭️  No changes needed")
            return False

    def migrate_python_file(self, file_path: str) -> bool:
        """Migrate Python files to use config manager"""
        print(f"\n🔧 Processing Python file: {file_path}")

        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading {file_path}: {e}")
            return False

        original_content = content
        changes = []

        # Add config manager import if not present and IPs are found
        has_hardcoded_ips = any(re.search(pattern, content) for pattern in self.ip_patterns)
        has_config_import = 'config_manager' in content or 'get_service_ip' in content

        if has_hardcoded_ips and not has_config_import:
            # Add import after existing imports
            import_pattern = r'((?:from|import)\s+[^\n]+\n)*'
            import_addition = 'from common.config_manager import get_service_ip, get_service_url, get_redis_url\n'

            if re.search(r'^(from|import)', content, re.MULTILINE):
                content = re.sub(r'(\n)((?!from|import))', r'\1' + import_addition + r'\2', content, count=1)
                changes.append("Added config_manager import")

        # Replace specific patterns
        replacements = [
            # Direct IP string replacements
            (r'"192\.168\.100\.16"', 'get_service_ip("mainpc")'),
            (r'"192\.168\.100\.17"', 'get_service_ip("pc2")'),
            (r'"127\.0\.0\.1"', '"localhost"'),  # Keep localhost as is

            # ZMQ URL patterns
            (r'"tcp://192\.168\.100\.16:(\d+)"', r'get_service_url("mainpc", \1)'),
            (r'"tcp://192\.168\.100\.17:(\d+)"', r'get_service_url("pc2", \1)'),
            (r'f"tcp://192\.168\.100\.16:{([^}]+)}"', r'get_service_url("mainpc", \1)'),
            (r'f"tcp://192\.168\.100\.17:{([^}]+)}"', r'get_service_url("pc2", \1)'),

            # Redis URL patterns
            (r'"redis://192\.168\.100\.16:6379/?\d*"', 'get_redis_url()'),
            (r'redis://192\.168\.100\.16:6379', 'get_redis_url()'),
        ]

        for pattern, replacement in replacements:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced {pattern} with {replacement}")

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Migrated Python file ({len(changes)} changes)")
            for change in changes:
                print(f"    • {change}")
            self.changes_made.extend(changes)
            return True
        else:
            print(f"  ⏭️  No changes needed")
            return False

    def migrate_yaml_file(self, file_path: str) -> bool:
        """Migrate YAML configuration files"""
        print(f"\n🔧 Processing YAML file: {file_path}")

        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading {file_path}: {e}")
            return False

        original_content = content
        changes = []

        # YAML-specific replacements
        replacements = [
            # Direct IP values
            (r'host:\s*["\']?192\.168\.100\.16["\']?', 'host: "${MAINPC_IP:-192.168.100.16}"'),
            (r'host:\s*["\']?192\.168\.100\.17["\']?', 'host: "${PC2_IP:-192.168.100.17}"'),
            (r'ip:\s*["\']?192\.168\.100\.16["\']?', 'ip: "${MAINPC_IP:-192.168.100.16}"'),
            (r'ip:\s*["\']?192\.168\.100\.17["\']?', 'ip: "${PC2_IP:-192.168.100.17}"'),

            # URL patterns
            (r'url:\s*["\']?redis://192\.168\.100\.16:6379["\']?', 'url: "redis://${REDIS_HOST:-192.168.100.16}:${REDIS_PORT:-6379}"'),
            (r'redis://192\.168\.100\.16:6379', 'redis://${REDIS_HOST:-192.168.100.16}:${REDIS_PORT:-6379}'),
        ]

        for pattern, replacement in replacements:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced {pattern} with {replacement}")

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Migrated YAML file ({len(changes)} changes)")
            for change in changes:
                print(f"    • {change}")
            self.changes_made.extend(changes)
            return True
        else:
            print(f"  ⏭️  No changes needed")
            return False

     """TODO: Add description for main."""
def main():
    migrator = IPMigrator()

    print("🚀 Starting Hard-coded IP Address Migration")
    print("=" * 60)

    # Find all hard-coded IPs
    print("🔍 Scanning for hard-coded IP addresses...")
    hardcoded_ips = migrator.find_hardcoded_ips()

    if not hardcoded_ips:
        print("✅ No hard-coded IP addresses found!")
        return

    print(f"📊 Found {len(hardcoded_ips)} hard-coded IP references")

    # Group by file type
    docker_files = []
    python_files = []
    yaml_files = []

    processed_files = set()

    for file_path, line_num, line_content in hardcoded_ips:
        if file_path in processed_files:
            continue

        if 'docker-compose' in file_path or file_path.endswith('.docker'):
            docker_files.append(file_path)
        elif file_path.endswith('.py'):
            python_files.append(file_path)
        elif file_path.endswith(('.yaml', '.yml')):
            yaml_files.append(file_path)

        processed_files.add(file_path)

    total_files_migrated = 0

    # Migrate Docker Compose files
    print(f"\n🐳 Migrating {len(docker_files)} Docker Compose files...")
    for file_path in docker_files:
        if migrator.migrate_docker_compose(file_path):
            total_files_migrated += 1

    # Migrate Python files
    print(f"\n🐍 Migrating {len(python_files)} Python files...")
    for file_path in python_files:
        if migrator.migrate_python_file(file_path):
            total_files_migrated += 1

    # Migrate YAML files
    print(f"\n📄 Migrating {len(yaml_files)} YAML files...")
    for file_path in yaml_files:
        if migrator.migrate_yaml_file(file_path):
            total_files_migrated += 1

    print("\n" + "=" * 60)
    print(f"🎯 IP ADDRESS MIGRATION COMPLETE!")
    print(f"📊 Results:")
    print(f"   • Files scanned: {len(processed_files)}")
    print(f"   • Files migrated: {total_files_migrated}")
    print(f"   • Total changes: {len(migrator.changes_made)}")

    print(f"\n✅ Benefits Achieved:")
    print(f"   • Environment-aware configuration enabled")
    print(f"   • Containerization unblocked")
    print(f"   • Cross-environment deployment enabled")
    print(f"   • Development/Production isolation")

    print(f"\n🚀 Next Steps:")
    print(f"   • Set ENV_TYPE environment variable (development/production/container)")
    print(f"   • Override IPs with MAINPC_IP, PC2_IP environment variables")
    print(f"   • Test deployment in different environments")

if __name__ == "__main__":
    main()
