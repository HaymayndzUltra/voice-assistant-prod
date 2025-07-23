#!/usr/bin/env python3
"""
ModelManagerAgent Environment Backup Script
Automated backup for Week 4 migration
"""
import shutil
import os
from pathlib import Path
from datetime import datetime

def create_backup():
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "backups" / "week4_mma_migration"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup targets
    targets = [
        ("main_pc_code/agents/model_manager_agent.py", "model_manager_agent_original.py"),
        ("main_pc_code/config/startup_config.yaml", "startup_config_original.yaml"),
        ("main_pc_code/config/llm_config.yaml", "llm_config_original.yaml")
    ]
    
    print(f"🔄 Creating backup at {backup_dir}")
    for source, backup_name in targets:
        source_path = project_root / source
        backup_path = backup_dir / backup_name
        if source_path.exists():
            shutil.copy2(source_path, backup_path)
            print(f"✅ Backed up {source}")
        else:
            print(f"⚠️ Warning: {source} not found")
    
    # Create backup manifest
    manifest = {
        "created": datetime.now().isoformat(),
        "files": targets,
        "original_file_size": (project_root / "main_pc_code/agents/model_manager_agent.py").stat().st_size if (project_root / "main_pc_code/agents/model_manager_agent.py").exists() else 0
    }
    
    with open(backup_dir / "backup_manifest.json", 'w') as f:
        import json
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Backup complete with manifest")

if __name__ == "__main__":
    create_backup()
