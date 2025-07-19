import os
import shutil
import logging
from datetime import datetime
from common.core.base_agent import BaseAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_ports_rollback.log'),
        logging.StreamHandler()
    ]
)

class WebPortRollback:
    def __init__(self):

        super().__init__(*args, **kwargs)        self.backup_dir = "port_changes_backup"
        self.files_to_rollback = {
            'autonomous_web_assistant.py': {
                'port': 5604,
                'path': '_PC2 SOURCE OF TRUTH LATEST/autonomous_web_assistant.py'
            },
            'unified_web_agent.py': {
                'port': 5604,
                'path': '_PC2 SOURCE OF TRUTH LATEST/unified_web_agent.py'
            }
        }
        self.docs_to_rollback = {
            'active_pc2_agents.md': {
                'path': '_DOCUMENTSFINAL/active_pc2_agents.md'
            }
        }

    def create_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.backup_dir}_{timestamp}"
        os.makedirs(backup_path, exist_ok=True)
        
        # Backup source files
        for file_info in self.files_to_rollback.values():
            if os.path.exists(file_info['path']):
                shutil.copy2(file_info['path'], f"{backup_path}/{os.path.basename(file_info['path'])}")
                logging.info(f"Backed up {file_info['path']}")
        
        # Backup documentation
        for doc_info in self.docs_to_rollback.values():
            if os.path.exists(doc_info['path']):
                shutil.copy2(doc_info['path'], f"{backup_path}/{os.path.basename(doc_info['path'])}")
                logging.info(f"Backed up {doc_info['path']}")
        
        return backup_path

    def rollback(self, backup_path):
        # Rollback source files
        for file_info in self.files_to_rollback.values():
            backup_file = f"{backup_path}/{os.path.basename(file_info['path'])}"
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, file_info['path'])
                logging.info(f"Rolled back {file_info['path']} to port {file_info['port']}")
        
        # Rollback documentation
        for doc_info in self.docs_to_rollback.values():
            backup_file = f"{backup_path}/{os.path.basename(doc_info['path'])}"
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, doc_info['path'])
                logging.info(f"Rolled back {doc_info['path']}")

def main():
    rollback = WebPortRollback()
    try:
        backup_path = rollback.create_backup()
        logging.info(f"Created backup in {backup_path}")
        
        rollback.rollback(backup_path)
        logging.info("Rollback completed successfully")
        
    except Exception as e:
        logging.error(f"Rollback failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 