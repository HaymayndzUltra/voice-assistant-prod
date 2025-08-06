#!/usr/bin/env python3
"""
Docker Path Fixer Script

Fixes hardcoded paths to make them containerization-friendly.
Implements Blueprint.md Step 5: Docker Path Fixes.

This script:
1. Replaces /tmp/ with PathManager.get_temp_dir() 
2. Replaces logs/ with PathManager.get_logs_dir()
3. Replaces models/ with PathManager.get_models_dir()
4. Replaces data/ with PathManager.get_data_dir() 
5. Replaces cache/ with PathManager.get_cache_dir()
6. Replaces Windows WSL paths (/mnt/c/...) with container paths
7. Replaces absolute project paths with PathManager.get_project_root()

Usage:
    python tools/docker_path_fixer.py --dry-run    # Preview changes
    python tools/docker_path_fixer.py --apply      # Apply changes
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
class PathFixRule:
    """Rule for fixing hardcoded paths"""
    pattern: str
    replacement: str
    description: str
    requires_import: bool = False

class DockerPathFixer:
    """
    Fixes hardcoded paths to make them containerization-friendly.
    """
    
    # Path fixing rules
    PATH_FIX_RULES = [
        # Windows WSL paths (highest priority)
        PathFixRule(
            pattern=r'["\'][/\\]mnt[/\\]c[/\\]Users[/\\][^"\']+[/\\]models[/\\]([^"\']+)["\']',
            replacement=r'PathManager.get_models_dir() / "\1"',
            description="Windows WSL model paths",
            requires_import=True
        ),
        PathFixRule(
            pattern=r'["\'][/\\]mnt[/\\]c[/\\]Users[/\\][^"\']+["\']',
            replacement=r'str(PathManager.get_project_root())',
            description="Windows WSL paths",
            requires_import=True
        ),
        
        # Absolute project paths
        PathFixRule(
            pattern=r'["\'][/\\]home[/\\][^/\\]+[/\\]AI_System_Monorepo[/\\]([^"\']*)["\']',
            replacement=r'str(PathManager.get_project_root() / "\1")',
            description="Absolute project paths",
            requires_import=True
        ),
        
        # Temporary file paths
        PathFixRule(
            pattern=r'["\'][/\\]tmp[/\\]([^"\']+)["\']',
            replacement=r'str(PathManager.get_temp_dir() / "\1")',
            description="Temporary file paths",
            requires_import=True
        ),
        
        # Relative path patterns (be more careful with these)
        PathFixRule(
            pattern=r'(["\'])logs[/\\]([^"\']+)\1',
            replacement=r'str(PathManager.get_logs_dir() / "\2")',
            description="Logs directory paths",
            requires_import=True
        ),
        PathFixRule(
            pattern=r'(["\'])models[/\\]([^"\']+)\1',
            replacement=r'str(PathManager.get_models_dir() / "\2")',
            description="Models directory paths",
            requires_import=True
        ),
        PathFixRule(
            pattern=r'(["\'])data[/\\]([^"\']+)\1',
            replacement=r'str(PathManager.get_data_dir() / "\2")',
            description="Data directory paths",
            requires_import=True
        ),
        PathFixRule(
            pattern=r'(["\'])cache[/\\]([^"\']+)\1',
            replacement=r'str(PathManager.get_cache_dir() / "\2")',
            description="Cache directory paths",
            requires_import=True
        ),
        
        # Path.expanduser patterns (for cross-platform compatibility)
        PathFixRule(
            pattern=r'os\.path\.expanduser\(["\']~[/\\]\.cache[/\\]([^"\']+)["\']',
            replacement=r'str(PathManager.get_cache_dir() / "\1")',
            description="User cache directory paths",
            requires_import=True
        ),
        
        # Database path patterns
        PathFixRule(
            pattern=r'["\']([^"\']*\.db)["\']',
            replacement=r'str(PathManager.get_data_dir() / "\1")',
            description="Database file paths (*.db)",
            requires_import=True
        ),
        
        # Log file patterns
        PathFixRule(
            pattern=r'["\']([^"\']*\.log)["\']',
            replacement=r'str(PathManager.get_logs_dir() / "\1")',
            description="Log file paths (*.log)",
            requires_import=True
        ),
    ]
    
    # Special case patterns that need manual review
    MANUAL_REVIEW_PATTERNS = [
        r'tts_models[/\\]',  # TTS model identifiers, not file paths
        r'\.git[/\\]',       # Git directory references  
        r'__pycache__',      # Python cache references
        r'venv[/\\]',        # Virtual environment references
    ]
    
    # Import statement to add
    IMPORT_STATEMENT = "from common.utils.path_manager import PathManager"
    
    def __init__(self, project_root: Path):
        """Initialize fixer with project root."""
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
        Analyze a file for hardcoded paths that need fixing.
        
        Returns:
            Tuple of (issues_found, needs_fixing)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError) as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return [], False
        
        issues = []
        needs_fixing = False
        
        # Check for hardcoded path patterns
        for rule in self.PATH_FIX_RULES:
            matches = re.findall(rule.pattern, content)
            if matches:
                # Skip patterns that need manual review
                skip = False
                for manual_pattern in self.MANUAL_REVIEW_PATTERNS:
                    if re.search(manual_pattern, ''.join(str(m) for m in matches)):
                        skip = True
                        break
                
                if not skip:
                    issues.append(f"{rule.description}: {len(matches)} occurrence(s)")
                    needs_fixing = True
        
        return issues, needs_fixing
    
    def fix_file(self, file_path: Path, dry_run: bool = True) -> Tuple[str, int]:
        """
        Fix hardcoded paths in a single file.
        
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
        import_needed = False
        
        # Apply path fixing rules
        for rule in self.PATH_FIX_RULES:
            # Skip patterns that need manual review
            skip = False
            for manual_pattern in self.MANUAL_REVIEW_PATTERNS:
                if re.search(manual_pattern, content):
                    # Only skip if the match is within a manual review pattern
                    temp_matches = re.findall(rule.pattern, content)
                    if temp_matches and any(re.search(manual_pattern, str(match)) for match in temp_matches):
                        skip = True
                        break
            
            if not skip:
                new_content, num_replacements = re.subn(rule.pattern, rule.replacement, content)
                if num_replacements > 0:
                    logger.info(f"  {rule.description}: {num_replacements} replacement(s)")
                    content = new_content
                    changes_made += num_replacements
                    
                    if rule.requires_import:
                        import_needed = True
        
        # Add import statement if needed and not already present
        if import_needed and changes_made > 0:
            if self.IMPORT_STATEMENT not in content:
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
                    lines.insert(import_line_idx + 2, "# Containerization-friendly paths (Blueprint.md Step 5)")
                    lines.insert(import_line_idx + 3, self.IMPORT_STATEMENT)
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
    
    def run_fixing(self, dry_run: bool = True, file_patterns: List[str] = None) -> Dict[str, any]:
        """
        Run the path fixing process.
        
        Args:
            dry_run: If True, only preview changes without applying them
            file_patterns: List of file patterns to include (None for all)
            
        Returns:
            Dictionary with fixing results
        """
        logger.info(f"{'🔍 ANALYZING' if dry_run else '🔧 FIXING'} hardcoded paths for Docker compatibility...")
        
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
        files_needing_fixes = []
        total_changes = 0
        
        for file_path in python_files:
            # Analyze file
            issues, needs_fixing = self.analyze_file(file_path)
            
            if needs_fixing:
                rel_path = file_path.relative_to(self.project_root)
                
                if dry_run:
                    logger.info(f"📄 {rel_path}")
                    for issue in issues:
                        logger.info(f"  - {issue}")
                    files_needing_fixes.append((str(rel_path), issues))
                else:
                    logger.info(f"🔧 Fixing {rel_path}")
                    new_content, changes = self.fix_file(file_path, dry_run=False)
                    if changes > 0:
                        total_changes += changes
                        self.files_modified += 1
                        files_needing_fixes.append((str(rel_path), changes))
        
        # Summary
        if dry_run:
            logger.info(f"\n📊 PATH FIXING PREVIEW SUMMARY:")
            logger.info(f"Files needing fixes: {len(files_needing_fixes)}")
            logger.info(f"Total Python files scanned: {len(python_files)}")
            
            if files_needing_fixes:
                logger.info(f"\n📋 Files that will be modified:")
                for file_path, issues in files_needing_fixes:
                    logger.info(f"  • {file_path}")
        else:
            logger.info(f"\n✅ PATH FIXING COMPLETE!")
            logger.info(f"Files modified: {self.files_modified}")
            logger.info(f"Total changes made: {total_changes}")
        
        return {
            'files_processed': len(python_files),
            'files_needing_fixes': len(files_needing_fixes),
            'files_modified': self.files_modified if not dry_run else 0,
            'total_changes': total_changes,
            'files_list': files_needing_fixes
        }

def main():
    """Main entry point for the path fixer script."""
    parser = argparse.ArgumentParser(description="Fix hardcoded paths for Docker compatibility")
    parser.add_argument('--dry-run', action='store_true', help="Preview changes without applying them")
    parser.add_argument('--apply', action='store_true', help="Apply path fixing changes")
    parser.add_argument('--patterns', nargs='*', help="File patterns to include (e.g., main_pc_code pc2_code)")
    parser.add_argument('--project-root', default='.', help="Project root directory")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")
    
    # Initialize fixer
    project_root = Path(args.project_root).resolve()
    fixer = DockerPathFixer(project_root)
    
    # Run fixing
    try:
        results = fixer.run_fixing(
            dry_run=args.dry_run,
            file_patterns=args.patterns
        )
        
        # Display results
        if args.dry_run:
            logger.info(f"\n🚀 To apply these changes, run:")
            logger.info(f"python {__file__} --apply")
        
        return 0
        
    except Exception as e:
        logger.error(f"Path fixing failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 