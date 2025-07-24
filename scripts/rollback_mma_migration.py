#!/usr/bin/env python3
"""
ModelManagerAgent Migration Rollback Script
Emergency rollback for Week 4 migration
"""
import shutil
import subprocess
import time
from pathlib import Path

def emergency_rollback():
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "backups" / "week4_mma_migration"
    
    print("🚨 EMERGENCY ROLLBACK INITIATED")
    
    # Stop ModelManagerAgent
    try:
        subprocess.run(["pkill", "-f", "model_manager_agent"], check=False)
        print("⏹️ ModelManagerAgent stopped")
        time.sleep(2)
    except:
        print("⚠️ Could not stop ModelManagerAgent via pkill")
    
    # Restore files
    if (backup_dir / "model_manager_agent_original.py").exists():
        shutil.copy2(
            backup_dir / "model_manager_agent_original.py",
            project_root / "main_pc_code/agents/model_manager_agent.py"
        )
        print("✅ ModelManagerAgent restored from backup")
    
    if (backup_dir / "startup_config_original.yaml").exists():
        shutil.copy2(
            backup_dir / "startup_config_original.yaml",
            project_root / "main_pc_code/config/startup_config.yaml"
        )
        print("✅ Startup config restored from backup")
    
    print("🔄 Manual restart required for ModelManagerAgent")
    print("✅ Rollback complete")

if __name__ == "__main__":
    emergency_rollback()
