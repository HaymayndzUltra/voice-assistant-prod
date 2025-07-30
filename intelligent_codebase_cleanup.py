#!/usr/bin/env python3
"""
🧠 Intelligent Codebase Cleanup Strategy
=====================================

A smart, multi-phase approach to cleaning up the AI System Monorepo
while maintaining safety and functionality.

Author: AI Assistant
Date: 2025-07-30
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class IntelligentCleanup:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.backup_dir = self.root_dir / "cleanup_backups"
        self.log_file = self.root_dir / f"cleanup_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.cleanup_log = []
        
        # Safety lists
        self.critical_files = {
            'requirements.txt', 'pyproject.toml', 'setup.py',
            'docker-compose.yml', 'Dockerfile', 'Makefile',
            '.gitignore', 'README.md', '.env'
        }
        
        self.safe_to_delete_patterns = {
            # Cache directories
            '__pycache__', '.pytest_cache', '.ruff_cache', 'node_modules',
            # Log files  
            '*.log',
            # Backup files
            '*.backup', '*.backup2', '*.bak',
            # Temporary files
            'temp*', '*.tmp', '*.temp',
            # OS generated
            '.DS_Store', 'Thumbs.db'
        }
        
        self.suspicious_patterns = {
            # Potential duplicates
            '*_copy*', '*_old*', '*_backup*', '*_test*',
            # Date-stamped reports (might be old)
            '*_20[0-9][0-9][0-1][0-9][0-3][0-9]*',
            # Legacy files
            '*legacy*', '*deprecated*'
        }

    def create_backup(self) -> bool:
        """Create full system backup before cleanup."""
        print("🛡️  Creating safety backup...")
        self.backup_dir.mkdir(exist_ok=True)
        
        backup_name = f"pre_cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        backup_path = self.backup_dir / backup_name
        
        try:
            import tarfile
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(self.root_dir, arcname=".", 
                       exclude=lambda x: '.git' in x or 'cleanup_backups' in x)
            
            print(f"✅ Backup created: {backup_path}")
            self.log_action("backup_created", str(backup_path))
            return True
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False

    def analyze_disk_usage(self) -> Dict[str, int]:
        """Analyze disk usage by file category."""
        categories = {
            'logs': 0, 'caches': 0, 'backups': 0, 'temp': 0, 
            'docs': 0, 'configs': 0, 'scripts': 0, 'other': 0
        }
        
        for file_path in self.root_dir.rglob('*'):
            if file_path.is_file():
                size = file_path.stat().st_size
                name = file_path.name.lower()
                
                if name.endswith('.log'):
                    categories['logs'] += size
                elif any(cache in str(file_path) for cache in ['__pycache__', '.pytest_cache', '.ruff_cache']):
                    categories['caches'] += size  
                elif any(backup in name for backup in ['.backup', '.bak']):
                    categories['backups'] += size
                elif name.startswith('temp') or name.endswith('.tmp'):
                    categories['temp'] += size
                elif name.endswith(('.md', '.txt', '.rst')):
                    categories['docs'] += size
                elif name.endswith(('.yml', '.yaml', '.json', '.toml')):
                    categories['configs'] += size
                elif name.endswith('.py'):
                    categories['scripts'] += size
                else:
                    categories['other'] += size
                    
        return categories

    def find_duplicates(self) -> Dict[str, List[Path]]:
        """Find duplicate files by content hash."""
        print("🔍 Analyzing for duplicate files...")
        hashes = defaultdict(list)
        
        for file_path in self.root_dir.rglob('*'):
            if file_path.is_file() and file_path.stat().st_size > 0:
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                        hashes[file_hash].append(file_path)
                except (IOError, OSError):
                    continue
        
        # Return only groups with duplicates
        duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
        print(f"📊 Found {len(duplicates)} groups of duplicate files")
        return duplicates

    def find_orphaned_files(self) -> List[Path]:
        """Find Python files not imported anywhere."""
        print("🔍 Finding orphaned Python files...")
        
        # Get all Python files
        py_files = set(self.root_dir.rglob('*.py'))
        
        # Get all imports
        imported_files = set()
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple import extraction (could be enhanced)
                    import re
                    imports = re.findall(r'from\s+(\S+)\s+import|import\s+(\S+)', content)
                    for imp in imports:
                        module = imp[0] or imp[1]
                        if '.' in module:
                            module = module.split('.')[0]
                        # Convert module to potential file path
                        potential_file = self.root_dir / f"{module}.py"
                        if potential_file.exists():
                            imported_files.add(potential_file)
            except (UnicodeDecodeError, IOError):
                continue
        
        orphaned = py_files - imported_files
        print(f"📊 Found {len(orphaned)} potentially orphaned files")
        return list(orphaned)

    def phase1_safe_cleanup(self, dry_run: bool = True) -> List[Path]:
        """Phase 1: Clean up guaranteed-safe files."""
        print("\n🚀 Phase 1: Safe Automated Cleanup")
        files_to_delete = []
        
        # Cache directories
        for cache_dir in ['__pycache__', '.pytest_cache', '.ruff_cache', 'node_modules']:
            for path in self.root_dir.rglob(cache_dir):
                if path.is_dir():
                    files_to_delete.append(path)
        
        # Log files  
        for log_file in self.root_dir.rglob('*.log'):
            if log_file.is_file():
                files_to_delete.append(log_file)
        
        # Backup files
        for backup_file in self.root_dir.rglob('*.backup*'):
            if backup_file.is_file():
                files_to_delete.append(backup_file)
                
        # Temp files
        for temp_file in self.root_dir.rglob('temp*'):
            if temp_file.is_file() or temp_file.is_dir():
                files_to_delete.append(temp_file)
        
        total_size = sum(self._get_size(path) for path in files_to_delete)
        print(f"📊 Found {len(files_to_delete)} items ({total_size/1024/1024:.1f}MB)")
        
        if not dry_run:
            self._delete_files(files_to_delete, "Phase 1")
            
        return files_to_delete

    def phase2_analysis_cleanup(self, dry_run: bool = True) -> Dict[str, List[Path]]:
        """Phase 2: Analysis-driven cleanup."""
        print("\n🎯 Phase 2: Analysis-Driven Cleanup")
        
        results = {
            'duplicates': [],
            'orphaned': [],
            'old_reports': []
        }
        
        # Find duplicates
        duplicates = self.find_duplicates()
        for file_hash, paths in duplicates.items():
            # Keep the first one, mark others for deletion  
            results['duplicates'].extend(paths[1:])
        
        # Find orphaned files
        results['orphaned'] = self.find_orphaned_files()
        
        # Find old reports (files with dates older than 30 days)
        import re
        date_pattern = re.compile(r'20\d{2}[01]\d[0-3]\d')
        cutoff_date = datetime.now().timestamp() - (30 * 24 * 3600)
        
        for file_path in self.root_dir.rglob('*.md'):
            if date_pattern.search(file_path.name):
                if file_path.stat().st_mtime < cutoff_date:
                    results['old_reports'].append(file_path)
        
        total_files = sum(len(files) for files in results.values())
        print(f"📊 Found {total_files} files for analysis-based cleanup")
        
        if not dry_run:
            for category, files in results.items():
                if files:
                    self._delete_files(files, f"Phase 2 - {category}")
                    
        return results

    def phase3_manual_review(self) -> Dict[str, List[Path]]:
        """Phase 3: Generate manual review list."""
        print("\n👁️  Phase 3: Manual Review Required")
        
        review_items = {
            'config_duplicates': [],
            'script_duplicates': [], 
            'documentation': []
        }
        
        # Find potential config duplicates
        config_files = defaultdict(list)
        yml_files = list(self.root_dir.rglob('*.yml'))
        yaml_files = list(self.root_dir.rglob('*.yaml')) 
        docker_files = list(self.root_dir.rglob('docker-compose*'))
        for config_file in yml_files + yaml_files + docker_files:
            base_name = config_file.stem.replace('-', '_').lower()
            config_files[base_name].append(config_file)
            
        for base_name, files in config_files.items():
            if len(files) > 1:
                review_items['config_duplicates'].extend(files[1:])
        
        # Find similar scripts
        script_files = defaultdict(list)
        for script_file in self.root_dir.rglob('*.py'):
            if any(word in script_file.name.lower() for word in ['test', 'check', 'validate', 'fix']):
                base_name = script_file.name.lower().replace('_', '').replace('test', '').replace('check', '')
                script_files[base_name].append(script_file)
                
        for base_name, files in script_files.items():
            if len(files) > 2:  # More than 2 similar scripts
                review_items['script_duplicates'].extend(files[2:])
        
        # Documentation review
        doc_files = list(self.root_dir.rglob('README*')) + list(self.root_dir.rglob('*GUIDE*')) + list(self.root_dir.rglob('*REPORT*'))
        review_items['documentation'] = [f for f in doc_files if f.stat().st_mtime < datetime.now().timestamp() - (7 * 24 * 3600)]
        
        total_review = sum(len(files) for files in review_items.values()) 
        print(f"📊 {total_review} items require manual review")
        return review_items

    def _get_size(self, path: Path) -> int:
        """Get size of file or directory."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return 0

    def _delete_files(self, files: List[Path], phase: str):
        """Actually delete files with logging."""
        deleted_count = 0
        deleted_size = 0
        
        for file_path in files:
            try:
                size = self._get_size(file_path)
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                    
                deleted_count += 1
                deleted_size += size
                self.log_action("deleted", str(file_path), {"phase": phase, "size": size})
                
            except Exception as e:
                self.log_action("delete_failed", str(file_path), {"error": str(e), "phase": phase})
        
        print(f"✅ {phase}: Deleted {deleted_count} items ({deleted_size/1024/1024:.1f}MB)")

    def log_action(self, action: str, target: str, metadata: dict = None):
        """Log cleanup action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "metadata": metadata or {}
        }
        self.cleanup_log.append(entry)

    def save_log(self):
        """Save cleanup log to file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.cleanup_log, f, indent=2)
        print(f"📝 Cleanup log saved: {self.log_file}")

    def run_full_analysis(self) -> Dict:
        """Run complete analysis without deletion."""
        print("🔬 Running Full Codebase Analysis...")
        
        analysis = {
            "disk_usage": self.analyze_disk_usage(),
            "phase1_candidates": self.phase1_safe_cleanup(dry_run=True),
            "phase2_candidates": self.phase2_analysis_cleanup(dry_run=True),  
            "phase3_candidates": self.phase3_manual_review()
        }
        
        # Calculate potential savings
        total_savings = 0
        total_savings += sum(self._get_size(f) for f in analysis["phase1_candidates"])
        for files in analysis["phase2_candidates"].values():
            total_savings += sum(self._get_size(f) for f in files)
            
        analysis["potential_savings_mb"] = total_savings / 1024 / 1024
        
        return analysis

def main():
    parser = argparse.ArgumentParser(description="Intelligent Codebase Cleanup")
    parser.add_argument("--root", default=".", help="Root directory to clean")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without doing it")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Run specific phase only")
    parser.add_argument("--analyze-only", action="store_true", help="Only run analysis")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    
    args = parser.parse_args()
    
    cleanup = IntelligentCleanup(args.root)
    
    if args.analyze_only:
        analysis = cleanup.run_full_analysis()
        print("\n📊 Analysis Summary:")
        print(f"   Potential space savings: {analysis['potential_savings_mb']:.1f}MB")
        print(f"   Phase 1 candidates: {len(analysis['phase1_candidates'])} items")
        print(f"   Phase 2 candidates: {sum(len(v) for v in analysis['phase2_candidates'].values())} items")
        print(f"   Phase 3 candidates: {sum(len(v) for v in analysis['phase3_candidates'].values())} items")
        return
    
    if not args.no_backup and not args.dry_run:
        if not cleanup.create_backup():
            print("❌ Cannot proceed without backup. Use --no-backup to override.")
            return
    
    try:
        if args.phase == 1 or not args.phase:
            cleanup.phase1_safe_cleanup(dry_run=args.dry_run)
            
        if args.phase == 2 or not args.phase:
            cleanup.phase2_analysis_cleanup(dry_run=args.dry_run)
            
        if args.phase == 3 or not args.phase:
            results = cleanup.phase3_manual_review()
            if results:
                print("\n⚠️  Items requiring manual review:")
                for category, files in results.items():
                    if files:
                        print(f"   {category}: {len(files)} files")
                        for f in files[:3]:  # Show first 3
                            print(f"     - {f}")
                        if len(files) > 3:
                            print(f"     ... and {len(files) - 3} more")
    
    finally:
        cleanup.save_log()
        print("\n🎉 Cleanup completed!")

if __name__ == "__main__":
    main()
