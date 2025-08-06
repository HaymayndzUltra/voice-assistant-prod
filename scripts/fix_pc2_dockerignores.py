#!/usr/bin/env python3
"""
Fix PC2 .dockerignore files for MASSIVE build speed improvement
===============================================================

Problem: PC2 builds taking 3+ hours due to 42,834 files and 72MB build context
Solution: Aggressive .dockerignore to exclude main_pc_code/, tests/, cache/, etc.

Usage:
    python3 scripts/fix_pc2_dockerignores.py --apply

This will fix all 23 PC2 .dockerignore files simultaneously.
"""

import os
from pathlib import Path

# Optimized .dockerignore content for PC2 containers
OPTIMIZED_DOCKERIGNORE = """# AGGRESSIVE BUILD OPTIMIZATION - PC2 Container
# Exclude everything except essential runtime files

# Version control (HUGE)
.git/
.svn/
.hg/
**/.git

# Python cache files (LARGE)
**/__pycache__/
**/*.py[cod]
**/*$py.class
**/.pytest_cache/
**/.coverage
htmlcov/
.tox/
.nox/
.hypothesis/

# Virtual environments (HUGE)
**/venv/
**/env/
**/.env
**/.venv/
**/ENV/
**/env.bak/
**/venv.bak/
**/pythonenv*

# IDE files (LARGE)
.idea/
.vscode/
*.sublime-project
*.sublime-workspace
**/.spyderproject
**/.spyproject
**/.ropeproject
.DS_Store

# Build artifacts (LARGE)
**/*.egg-info/
**/*.egg
**/dist/
**/build/

# Documentation (LARGE)
docs/
*.md
README*
LICENSE*
CONTRIBUTING*

# Test files (LARGE) - This is the BIGGEST space saver
tests/
test_*/
**/test_*.py
**/*_test.py
*_tests.py
test.py
**/*_tests/

# Log files
**/*.log
logs/
log_archives/

# Large/unnecessary directories (HUGE SAVINGS)
cache/
**/node_modules/
temp/
temp_test_context/
training_data/
test_reports/
models/*/
python_files_backup_*/
fine_tuned_models/
output/
artifacts/
backups/

# Archive files
**/*.zip
**/*.tar
**/*.gz
**/*.rar
**/*.7z

# Docker files themselves
Dockerfile*
.dockerignore
docker-compose*.yml

# CRITICAL: Exclude other machine code (MASSIVE SAVINGS)
main_pc_code/
phase1_implementation/
tools/
memory_system/
scripts/
validation/

# Temporary files
temp/
.tmp/
tmp/
"""

def fix_dockerignore(directory_path, apply=False):
    """Fix a single PC2 directory's .dockerignore"""
    dockerignore_path = directory_path / ".dockerignore"
    
    if apply:
        # Create backup
        if dockerignore_path.exists():
            backup_path = dockerignore_path.with_suffix(".dockerignore.backup")
            dockerignore_path.rename(backup_path)
            print(f"✅ Backup created: {backup_path}")
        
        # Write optimized version
        dockerignore_path.write_text(OPTIMIZED_DOCKERIGNORE.strip() + "\n")
        print(f"✅ Fixed: {dockerignore_path}")
        return True
    else:
        print(f"Would fix: {dockerignore_path}")
        return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix PC2 .dockerignore files for speed")
    parser.add_argument("--apply", action="store_true", help="Actually write changes")
    args = parser.parse_args()
    
    root = Path(__file__).parent.parent
    docker_dir = root / "docker"
    
    # Find all PC2 directories
    pc2_dirs = [d for d in docker_dir.iterdir() 
                if d.is_dir() and d.name.startswith("pc2_")]
    
    print(f"Found {len(pc2_dirs)} PC2 directories")
    
    fixed_count = 0
    for pc2_dir in sorted(pc2_dirs):
        if fix_dockerignore(pc2_dir, apply=args.apply):
            fixed_count += 1
    
    action = "Fixed" if args.apply else "Would fix"
    print(f"\n🎯 {action} {fixed_count}/{len(pc2_dirs)} PC2 .dockerignore files")
    
    if not args.apply:
        print("\n📋 To apply changes: python3 scripts/fix_pc2_dockerignores.py --apply")
    else:
        print("\n🚀 Build optimization complete! PC2 builds should be MUCH faster now.")

if __name__ == "__main__":
    main()
