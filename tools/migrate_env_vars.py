#!/usr/bin/env python3
"""
Environment Variable Migration Script

Migrates legacy environment variable usage to standardized format.
Implements Blueprint.md Step 4: Environment Variable Standardization.

This script:
1. Finds all files using legacy environment variable patterns
2. Replaces them with standardized environment variable calls
3. Updates imports to use the new env_standardizer
4. Provides a summary of changes made

Usage:
    python tools/migrate_env_vars.py --dry-run    # Preview changes
    python tools/migrate_env_vars.py --apply      # Apply changes
"""

import os
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

@dataclass
class MigrationRule:
    """Rule for migrating environment variable usage"""
    pattern: str
    replacement: str
    description: str

class EnvVarMigrator:
    """
    Migrates legacy environment variable usage to standardized format.
    """
    
    # Migration rules for different types of environment variable usage
    MIGRATION_RULES = [
        # Direct os.environ.get() calls
        MigrationRule(
            pattern=r'os\.environ\.get\(["\']MAIN_PC_IP["\']([^)]*)\)',
            replacement=r'get_mainpc_ip()',
            description="Direct MAIN_PC_IP os.environ.get() calls"
        ),
        MigrationRule(
            pattern=r'os\.environ\.get\(["\']PC2_IP["\']([^)]*)\)',
            replacement=r'get_pc2_ip()',
            description="Direct PC2_IP os.environ.get() calls"
        ),
        MigrationRule(
            pattern=r'os\.environ\.get\(["\']MACHINE_ROLE["\']([^)]*)\)',
            replacement=r'get_current_machine()',
            description="Direct MACHINE_ROLE os.environ.get() calls"
        ),
        
        # Variable assignments
        MigrationRule(
            pattern=r'(\w+)\s*=\s*os\.environ\.get\(["\']MAIN_PC_IP["\']([^)]*)\)',
            replacement=r'\1 = get_mainpc_ip()',
            description="MAIN_PC_IP variable assignments"
        ),
        MigrationRule(
            pattern=r'(\w+)\s*=\s*os\.environ\.get\(["\']PC2_IP["\']([^)]*)\)',
            replacement=r'\1 = get_pc2_ip()',
            description="PC2_IP variable assignments"
        ),
        
        # Network config patterns
        MigrationRule(
            pattern=r'network_config\.get\(["\']main_pc_ip["\']([^)]*)\)',
            replacement=r'get_mainpc_ip()',
            description="network_config main_pc_ip access"
        ),
        
        # Legacy service_ip function calls
        MigrationRule(
            pattern=r'get_service_ip\(["\']mainpc["\']([^)]*)\)',
            replacement=r'get_mainpc_ip()',
            description="get_service_ip mainpc calls"
        ),
        MigrationRule(
            pattern=r'get_service_ip\(["\']pc2["\']([^)]*)\)',
            replacement=r'get_pc2_ip()',
            description="get_service_ip pc2 calls"
        ),
    ]
    
    # Import statements to add
    IMPORT_STATEMENTS = [
        "from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env",
        "# Legacy imports can be removed after migration:",
        "# from common.config_manager import get_service_ip",
    ]
    
    def __init__(self, project_root: Path):
        """Initialize migrator with project root."""
        self.project_root = Path(project_root)
        self.files_modified = 0
        self.changes_made = 0
        
    def find_python_files(self, exclude_dirs: Set[str] = None) -> List[Path]:
        """Find all Python files in the project."""
        if exclude_dirs is None:
            exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules'}
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> Tuple[List[str], bool]:
        """
        Analyze a file for legacy environment variable usage.
        
        Returns:
            Tuple of (issues_found, needs_migration)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError) as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return [], False
        
        issues = []
        needs_migration = False
        
        # Check for legacy patterns
        for rule in self.MIGRATION_RULES:
            matches = re.findall(rule.pattern, content)
            if matches:
                issues.append(f"{rule.description}: {len(matches)} occurrence(s)")
                needs_migration = True
        
        # Check for legacy environment variable names
        legacy_vars = [
            "MAIN_PC_IP", "MACHINE_ROLE", "MACHINE_NAME",
            "BIND_IP", "LISTEN_ADDRESS", "REGISTRY_HOST"
        ]
        
        for var in legacy_vars:
            if var in content:
                issues.append(f"Legacy environment variable '{var}' found")
                needs_migration = True
        
        return issues, needs_migration
    
    def migrate_file(self, file_path: Path, dry_run: bool = True) -> Tuple[str, int]:
        """
        Migrate a single file to use standardized environment variables.
        
        Returns:
            Tuple of (new_content, changes_made)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError) as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return content, 0
        
        original_content = content
        changes_made = 0
        
        # Apply migration rules
        for rule in self.MIGRATION_RULES:
            new_content, num_replacements = re.subn(rule.pattern, rule.replacement, content)
            if num_replacements > 0:
                logger.info(f"  {rule.description}: {num_replacements} replacement(s)")
                content = new_content
                changes_made += num_replacements
        
        # Add import statement if changes were made and import not present
        if changes_made > 0:
            import_needed = False
            
            # Check if standardized functions are used but import is missing
            if ('get_mainpc_ip(' in content or 'get_pc2_ip(' in content or 'get_current_machine(' in content):
                if 'from common.utils.env_standardizer import' not in content:
                    import_needed = True
            
            if import_needed:
                # Find appropriate place to add import (after existing imports)
                lines = content.split('\n')
                import_line_idx = 0
                
                # Find last import line
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                        import_line_idx = i
                
                # Insert new import after last import
                if import_line_idx > 0:
                    lines.insert(import_line_idx + 1, "")
                    lines.insert(import_line_idx + 2, "# Standardized environment variables (Blueprint.md Step 4)")
                    lines.insert(import_line_idx + 3, self.IMPORT_STATEMENTS[0])
                    content = '\n'.join(lines)
                    changes_made += 1
        
        # Write changes if not dry run
        if not dry_run and content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ Updated {file_path}")
            except PermissionError as e:
                logger.error(f"Could not write {file_path}: {e}")
        
        return content, changes_made
    
    def run_migration(self, dry_run: bool = True, file_patterns: List[str] = None) -> Dict[str, any]:
        """
        Run the migration process.
        
        Args:
            dry_run: If True, only preview changes without applying them
            file_patterns: List of file patterns to include (None for all)
            
        Returns:
            Dictionary with migration results
        """
        logger.info(f"{'🔍 ANALYZING' if dry_run else '🔧 MIGRATING'} environment variable usage...")
        
        # Find Python files
        python_files = self.find_python_files()
        if file_patterns:
            # Filter by patterns
            filtered_files = []
            for pattern in file_patterns:
                filtered_files.extend([f for f in python_files if pattern in str(f)])
            python_files = list(set(filtered_files))
        
        logger.info(f"Found {len(python_files)} Python files to process")
        
        # Process files
        files_needing_migration = []
        total_changes = 0
        
        for file_path in python_files:
            # Analyze file
            issues, needs_migration = self.analyze_file(file_path)
            
            if needs_migration:
                rel_path = file_path.relative_to(self.project_root)
                
                if dry_run:
                    logger.info(f"📄 {rel_path}")
                    for issue in issues:
                        logger.info(f"  - {issue}")
                    files_needing_migration.append((str(rel_path), issues))
                else:
                    logger.info(f"🔧 Migrating {rel_path}")
                    new_content, changes = self.migrate_file(file_path, dry_run=False)
                    if changes > 0:
                        total_changes += changes
                        self.files_modified += 1
                        files_needing_migration.append((str(rel_path), changes))
        
        # Summary
        if dry_run:
            logger.info(f"\n📊 MIGRATION PREVIEW SUMMARY:")
            logger.info(f"Files needing migration: {len(files_needing_migration)}")
            logger.info(f"Total Python files scanned: {len(python_files)}")
            
            if files_needing_migration:
                logger.info(f"\n📋 Files that will be modified:")
                for file_path, issues in files_needing_migration:
                    logger.info(f"  • {file_path}")
        else:
            logger.info(f"\n✅ MIGRATION COMPLETE!")
            logger.info(f"Files modified: {self.files_modified}")
            logger.info(f"Total changes made: {total_changes}")
        
        return {
            'files_processed': len(python_files),
            'files_needing_migration': len(files_needing_migration),
            'files_modified': self.files_modified if not dry_run else 0,
            'total_changes': total_changes,
            'files_list': files_needing_migration
        }

def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Migrate environment variables to standardized format")
    parser.add_argument('--dry-run', action='store_true', help="Preview changes without applying them")
    parser.add_argument('--apply', action='store_true', help="Apply migration changes")
    parser.add_argument('--patterns', nargs='*', help="File patterns to include (e.g., main_pc_code pc2_code)")
    parser.add_argument('--project-root', default='.', help="Project root directory")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")
    
    # Initialize migrator
    project_root = Path(args.project_root).resolve()
    migrator = EnvVarMigrator(project_root)
    
    # Run migration
    try:
        results = migrator.run_migration(
            dry_run=args.dry_run,
            file_patterns=args.patterns
        )
        
        # Display results
        if args.dry_run:
            logger.info(f"\n🚀 To apply these changes, run:")
            logger.info(f"python {__file__} --apply")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 