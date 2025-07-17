#!/usr/bin/env python3
"""
Safe deletion script for files identified in the comprehensive audit.
This script will delete files marked as 'safe to delete' with priority >= 8.
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
PHASE3_JSON = BASE_DIR / 'output' / 'phase3_analysis.json'
BACKUP_DIR = BASE_DIR / 'cleanup_backup' / datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = BASE_DIR / 'output' / 'cleanup_log.txt'

def load_cleanup_candidates() -> List[Dict]:
    """Load cleanup candidates from Phase 3 analysis"""
    with open(PHASE3_JSON, 'r') as f:
        data = json.load(f)
    return data.get('cleanup_candidates', [])

def backup_file(file_path: Path) -> bool:
    """Backup file before deletion"""
    try:
        backup_path = BACKUP_DIR / file_path.relative_to(BASE_DIR)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        return True
    except Exception as e:
        print(f"Failed to backup {file_path}: {e}")
        return False

def delete_file(file_path: Path, dry_run: bool = False) -> bool:
    """Delete file with safety checks"""
    if dry_run:
        print(f"[DRY RUN] Would delete: {file_path}")
        return True
    
    try:
        # Backup first
        if backup_file(file_path):
            os.remove(file_path)
            print(f"✅ Deleted: {file_path}")
            return True
        else:
            print(f"❌ Skipped (backup failed): {file_path}")
            return False
    except Exception as e:
        print(f"❌ Failed to delete {file_path}: {e}")
        return False

def main(dry_run: bool = True):
    """Main cleanup function"""
    candidates = load_cleanup_candidates()
    safe_to_delete = [c for c in candidates if c.get('safe_to_delete', False)]
    
    print(f"Found {len(safe_to_delete)} files marked as safe to delete")
    
    if not dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Backup directory: {BACKUP_DIR}")
    
    deleted_count = 0
    failed_count = 0
    log_entries = []
    
    for candidate in safe_to_delete:
        file_path = BASE_DIR / candidate['file_path']
        
        if not file_path.exists():
            print(f"⚠️  Already deleted or moved: {file_path}")
            continue
        
        reasons = ', '.join(candidate['reasons'])
        log_entry = f"{datetime.now().isoformat()} - {file_path} - {reasons}"
        
        if delete_file(file_path, dry_run):
            deleted_count += 1
            log_entry += " - SUCCESS"
        else:
            failed_count += 1
            log_entry += " - FAILED"
        
        log_entries.append(log_entry)
    
    # Write log
    if not dry_run:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n--- Cleanup Run: {datetime.now().isoformat()} ---\n")
            f.write('\n'.join(log_entries))
            f.write(f"\n\nSummary: {deleted_count} deleted, {failed_count} failed\n")
    
    print(f"\nSummary:")
    print(f"- Files deleted: {deleted_count}")
    print(f"- Files failed: {failed_count}")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN. No files were actually deleted.")
        print("Run with --execute to perform actual deletion.")

if __name__ == '__main__':
    import sys
    dry_run = '--execute' not in sys.argv
    main(dry_run)