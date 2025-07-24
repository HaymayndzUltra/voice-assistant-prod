import os
import sys
import time
import json
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ServiceManager")

class ServiceManager:
    def __init__(self):
        self.services = {
            "remote_connector_agent": {
                "port": 5557,
                "script": "agents/remote_connector_agent.py"
            },
            "contextual_memory_agent": {
                "port": 5596,
                "script": "agents/contextual_memory_agent.py"
            },
            "digital_twin_agent": {
                "port": 5597,
                "script": "agents/digital_twin_agent.py"
            },
            "error_pattern_memory": {
                "port": 5611,
                "script": "agents/error_pattern_memory.py"
            },
            "nllb_translation_adapter": {
                "port": 5581,
                "script": "agents/nllb_translation_adapter.py"
            },
            "consolidated_translator": {
                "port": 5563,
                "script": "agents/consolidated_translator.py"
            },
            "tinyllama_service": {
                "port": 5615,
                "script": "agents/tinyllama_service_enhanced.py"
            },
            "chain_of_thought_agent": {
                "port": 5612,
                "script": "agents/chain_of_thought_agent.py"
            },
            "context_summarizer": {
                "port": 5610,
                "script": "agents/context_summarizer.py"
            }
        }
        
        self.logs_dir = Path("logs")
        self.archive_dir = self.logs_dir / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def stop_services(self):
        """Stop all running services"""
        logger.info("Stopping all services...")
        for service_name, service_info in self.services.items():
            try:
                # Find and kill process using the port
                if sys.platform == "win32":
                    cmd = f'netstat -ano | findstr :{service_info["port"]}'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.stdout:
                        pid = result.stdout.strip().split()[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                else:
                    cmd = f'lsof -i :{service_info["port"]} -t'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.stdout:
                        pid = result.stdout.strip()
                        subprocess.run(f'kill -9 {pid}', shell=True)
                logger.info(f"Stopped {service_name}")
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {str(e)}")
        
        # Give services time to shut down
        time.sleep(2)
    
    def archive_logs(self):
        """Archive all logs"""
        logger.info("Archiving logs...")
        try:
            # Create archive directory
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Move all log files
            for log_file in self.logs_dir.glob(str(PathManager.get_logs_dir() / "*.log")):
                try:
                    shutil.move(str(log_file), str(self.archive_dir / log_file.name))
                except Exception as e:
                    logger.error(f"Error moving {log_file}: {str(e)}")
            
            # Move all JSON files except configs
            for json_file in self.logs_dir.glob("*.json"):
                if not json_file.name.startswith("config_"):
                    try:
                        shutil.move(str(json_file), str(self.archive_dir / json_file.name))
                    except Exception as e:
                        logger.error(f"Error moving {json_file}: {str(e)}")
            
            logger.info(f"Logs archived to {self.archive_dir}")
        except Exception as e:
            logger.error(f"Error archiving logs: {str(e)}")
    
    def start_services(self):
        """Start all services in the correct order"""
        logger.info("Starting services...")
        
        # Start core services first
        core_services = [
            "remote_connector_agent",
            "contextual_memory_agent",
            "digital_twin_agent",
            "error_pattern_memory"
        ]
        
        for service_name in core_services:
            service_info = self.services[service_name]
            try:
                subprocess.Popen([sys.executable, service_info["script"]], 
                               stdout=open(fPathManager.join_path("logs", str(PathManager.get_logs_dir() / "{service_name}.log")), "a"),
                               stderr=subprocess.STDOUT)
                logger.info(f"Started {service_name}")
                time.sleep(1)  # Give service time to initialize
            except Exception as e:
                logger.error(f"Error starting {service_name}: {str(e)}")
        
        # Start translation services
        translation_services = [
            "nllb_translation_adapter",
            "consolidated_translator",
            "tinyllama_service"
        ]
        
        for service_name in translation_services:
            service_info = self.services[service_name]
            try:
                subprocess.Popen([sys.executable, service_info["script"]],
                               stdout=open(fPathManager.join_path("logs", str(PathManager.get_logs_dir() / "{service_name}.log")), "a"),
                               stderr=subprocess.STDOUT)
                logger.info(f"Started {service_name}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error starting {service_name}: {str(e)}")
        
        # Start remaining services
        remaining_services = [
            "chain_of_thought_agent",
            "context_summarizer"
        ]
        
        for service_name in remaining_services:
            service_info = self.services[service_name]
            try:
                subprocess.Popen([sys.executable, service_info["script"]],
                               stdout=open(fPathManager.join_path("logs", str(PathManager.get_logs_dir() / "{service_name}.log")), "a"),
                               stderr=subprocess.STDOUT)
                logger.info(f"Started {service_name}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error starting {service_name}: {str(e)}")
        
        logger.info("All services started")
    
    def verify_services(self):
        """Verify all services are running and healthy"""
        logger.info("Verifying services...")
        time.sleep(5)  # Give services time to fully initialize
        
        try:
            result = subprocess.run([sys.executable, "healthcheck_all_services.py"],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                with open("healthcheck_all_services_results.json", "r") as f:
                    health_results = json.load(f)
                
                all_healthy = True
                for service in health_results:
                    if service["Health Check Result"] != "Healthy":
                        logger.error(f"{service['Service Name']} is not healthy: {service['Health Check Result']}")
                        all_healthy = False
                
                if all_healthy:
                    logger.info("All services are healthy")
                else:
                    logger.error("Some services are not healthy")
            else:
                logger.error("Health check failed")
        except Exception as e:
            logger.error(f"Error verifying services: {str(e)}")

def main():
    manager = ServiceManager()
    
    # Stop all services
    manager.stop_services()
    
    # Archive logs
    manager.archive_logs()
    
    # Start services
    manager.start_services()
    
    # Verify services
    manager.verify_services()

if __name__ == "__main__":
    main() 