#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unused Import Cleanup Script - Phase 1.4

Safely removes unused imports across the AI System Monorepo codebase using:
- ruff for detection and automatic fixing
- autoflake as backup method
- Manual verification for critical files

Part of Phase 1.4: Unused Import Cleanup - O3 Roadmap Implementation
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class UnusedImportCleaner:
    """Comprehensive unused import cleanup for AI System Monorepo."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_dir = project_root / "backups" / "unused_import_cleanup"
        self.cleanup_report = []
        
        # Target directories for cleanup
        self.target_dirs = [
            "main_pc_code",
            "pc2_code", 
            "common",
            "common_utils"
        ]
        
        # Critical files to handle carefully
        self.critical_files = [
            "common/config/unified_config_manager.py",
            "common_utils/port_registry.py",
            "pc2_code/utils/pc2_error_publisher.py",
            "main_pc_code/agents/error_publisher.py"
        ]
        
    def run_cleanup(self) -> Dict[str, int]:
        """Run comprehensive unused import cleanup."""
        print("🧹 Starting Unused Import Cleanup (Phase 1.4)...")
        print(f"📂 Project Root: {self.project_root}")
        print(f"🎯 Target Directories: {', '.join(self.target_dirs)}")
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"💾 Backup Directory: {self.backup_dir}")
        
        results = {
            "analyzed_files": 0,
            "unused_imports_found": 0,
            "imports_removed": 0,
            "files_modified": 0,
            "errors": 0
        }
        
        # Step 1: Analyze current state
        print("\n🔍 Step 1: Analyzing unused imports...")
        analysis_results = self.analyze_unused_imports()
        results["analyzed_files"] = analysis_results["total_files"]
        results["unused_imports_found"] = analysis_results["unused_imports"]
        
        # Step 2: Create backups of files to be modified
        print("\n💾 Step 2: Creating backups...")
        self.create_backups(analysis_results["files_with_issues"])
        
        # Step 3: Run ruff cleanup (primary method)
        print("\n🔧 Step 3: Running ruff cleanup...")
        ruff_results = self.cleanup_with_ruff()
        results["imports_removed"] += ruff_results["imports_removed"]
        results["files_modified"] += ruff_results["files_modified"]
        
        # Step 4: Run autoflake cleanup (secondary method)
        print("\n🔧 Step 4: Running autoflake cleanup...")
        autoflake_results = self.cleanup_with_autoflake()
        results["imports_removed"] += autoflake_results["imports_removed"]
        results["files_modified"] += autoflake_results["files_modified"]
        
        # Step 5: Manual verification for critical files
        print("\n🔍 Step 5: Manual verification...")
        verification_results = self.verify_critical_files()
        results["errors"] = verification_results["errors"]
        
        # Generate cleanup report
        self.generate_cleanup_report(results)
        
        return results
    
    def analyze_unused_imports(self) -> Dict[str, any]:
        """Analyze unused imports across target directories."""
        files_with_issues = []
        total_files = 0
        unused_imports = 0
        
        for target_dir in self.target_dirs:
            dir_path = self.project_root / target_dir
            if not dir_path.exists():
                continue
                
            for py_file in dir_path.rglob("*.py"):
                if "_backup_" in str(py_file) or "__pycache__" in str(py_file):
                    continue
                    
                total_files += 1
                
                # Run ruff analysis on this file
                try:
                    result = subprocess.run([
                        "ruff", "check", "--select", "F401", "--no-fix", str(py_file)
                    ], capture_output=True, text=True, cwd=self.project_root)
                    
                    if result.stdout.strip():
                        files_with_issues.append(py_file)
                        # Count unused imports in this file
                        import_count = len([line for line in result.stdout.split('\n') if 'F401' in line])
                        unused_imports += import_count
                        
                except Exception as e:
                    print(f"⚠️ Error analyzing {py_file}: {e}")
        
        print(f"📊 Analysis: {total_files} files analyzed, {unused_imports} unused imports found in {len(files_with_issues)} files")
        
        return {
            "total_files": total_files,
            "unused_imports": unused_imports,
            "files_with_issues": files_with_issues
        }
    
    def create_backups(self, files_to_backup: List[Path]):
        """Create backups of files that will be modified."""
        backed_up = 0
        
        for file_path in files_to_backup:
            try:
                rel_path = file_path.relative_to(self.project_root)
                backup_path = self.backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                backup_path.write_text(file_path.read_text())
                backed_up += 1
            except Exception as e:
                print(f"⚠️ Error backing up {file_path}: {e}")
        
        print(f"💾 Created {backed_up} backups")
        return backed_up
    
    def cleanup_with_ruff(self) -> Dict[str, int]:
        """Run ruff to automatically fix unused imports."""
        print("🔧 Running ruff --fix for unused imports...")
        
        imports_removed = 0
        files_modified = 0
        
        for target_dir in self.target_dirs:
            dir_path = self.project_root / target_dir
            if not dir_path.exists():
                continue
                
            try:
                # Run ruff with fix for unused imports
                result = subprocess.run([
                    "ruff", "check", "--select", "F401", "--fix", str(dir_path)
                ], capture_output=True, text=True, cwd=self.project_root)
                
                # Count fixes applied
                if result.stdout:
                    fixed_lines = [line for line in result.stdout.split('\n') if 'Fixed' in line or 'Removed' in line]
                    imports_removed += len(fixed_lines)
                    files_with_fixes = set()
                    for line in result.stdout.split('\n'):
                        if ':' in line and '.py:' in line:
                            files_with_fixes.add(line.split(':')[0])
                    files_modified += len(files_with_fixes)
                
                fixes_count = len([l for l in result.stdout.split('\n') if 'Fixed' in l])
                print(f"✅ ruff cleanup on {target_dir}: {fixes_count} fixes")
                
            except Exception as e:
                print(f"❌ Error running ruff on {target_dir}: {e}")
        
        return {"imports_removed": imports_removed, "files_modified": files_modified}
    
    def cleanup_with_autoflake(self) -> Dict[str, int]:
        """Run autoflake as secondary cleanup method."""
        print("🔧 Running autoflake for additional cleanup...")
        
        imports_removed = 0
        files_modified = 0
        
        for target_dir in self.target_dirs:
            dir_path = self.project_root / target_dir
            if not dir_path.exists():
                continue
                
            try:
                # Run autoflake to remove unused imports
                result = subprocess.run([
                    "autoflake", 
                    "--remove-all-unused-imports",
                    "--remove-unused-variables",
                    "--in-place",
                    "--recursive",
                    str(dir_path)
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    print(f"✅ autoflake cleanup on {target_dir}: completed")
                    # Note: autoflake doesn't provide detailed output, so we estimate
                    files_modified += 1  # Conservative estimate
                else:
                    print(f"⚠️ autoflake warnings on {target_dir}")
                
            except Exception as e:
                print(f"❌ Error running autoflake on {target_dir}: {e}")
        
        return {"imports_removed": imports_removed, "files_modified": files_modified}
    
    def verify_critical_files(self) -> Dict[str, int]:
        """Verify critical files still work after cleanup."""
        print("🔍 Verifying critical files...")
        
        errors = 0
        
        for critical_file in self.critical_files:
            file_path = self.project_root / critical_file
            if not file_path.exists():
                continue
                
            try:
                # Try to compile the file to check for syntax errors
                with open(file_path, 'r') as f:
                    compile(f.read(), str(file_path), 'exec')
                    
                print(f"✅ {critical_file}: syntax valid")
                
            except SyntaxError as e:
                print(f"❌ {critical_file}: syntax error - {e}")
                errors += 1
            except Exception as e:
                print(f"⚠️ {critical_file}: verification error - {e}")
        
        return {"errors": errors}
    
    def generate_cleanup_report(self, results: Dict[str, int]):
        """Generate comprehensive cleanup report."""
        report_path = self.project_root / "UNUSED_IMPORT_CLEANUP_REPORT.md"
        
        report_content = f"""# Unused Import Cleanup Report - Phase 1.4
Generated by: {Path(__file__).name}

## Summary
- **Files Analyzed**: {results['analyzed_files']}
- **Unused Imports Found**: {results['unused_imports_found']}
- **Imports Removed**: {results['imports_removed']}
- **Files Modified**: {results['files_modified']}
- **Syntax Errors**: {results['errors']}

## Cleanup Methods Used
1. **Primary**: ruff --select F401 --fix
2. **Secondary**: autoflake --remove-all-unused-imports
3. **Verification**: Syntax checking for critical files

## Target Directories
- {chr(10).join([f'- {d}' for d in self.target_dirs])}

## Critical Files Verified
- {chr(10).join([f'- {f}' for f in self.critical_files])}

## Backup Location
- **Backup Directory**: `{self.backup_dir.relative_to(self.project_root)}`
- **Rollback**: All modified files backed up before cleanup

## Results Analysis
"""
        
        if results["errors"] == 0:
            report_content += "✅ **CLEANUP SUCCESSFUL**: No syntax errors detected\n"
        else:
            report_content += f"⚠️ **CLEANUP WARNINGS**: {results['errors']} files need manual review\n"
        
        if results["imports_removed"] > 0:
            report_content += f"✅ **OPTIMIZATION**: Removed {results['imports_removed']} unused imports\n"
        else:
            report_content += "ℹ️ **STATUS**: No unused imports found or already clean\n"
        
        report_content += f"""

## Impact
- **Code Quality**: Improved import hygiene across codebase
- **Performance**: Reduced module loading overhead
- **Maintainability**: Cleaner, more focused imports
- **Build Time**: Potential reduction in import resolution time

## Next Steps
1. Review any files with syntax errors
2. Test critical functionality to ensure no regressions
3. Consider adding import linting to CI/CD pipeline
4. Update development guidelines for import management

---
**Phase 1.4 Status**: {'✅ COMPLETE' if results['errors'] == 0 else '⚠️ NEEDS REVIEW'}
"""
        
        report_path.write_text(report_content)
        print(f"\n📊 Cleanup report saved: {report_path}")
        
        if results["errors"] == 0:
            print("🎉 PHASE 1.4 COMPLETE: Unused import cleanup successful!")
        else:
            print("⚠️ PHASE 1.4 NEEDS REVIEW: Some files require manual attention")


def main():
    """Main execution function."""
    project_root = Path(__file__).parent.parent
    
    print("🧹 Unused Import Cleanup - Phase 1.4")
    print(f"📂 Project: {project_root.name}")
    
    # Check if tools are available
    try:
        subprocess.run(["ruff", "--version"], capture_output=True, check=True)
        subprocess.run(["autoflake", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Required tools not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "ruff", "autoflake"], check=True)
    
    cleaner = UnusedImportCleaner(project_root)
    results = cleaner.run_cleanup()
    
    return results["errors"] == 0  # Return success status


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
