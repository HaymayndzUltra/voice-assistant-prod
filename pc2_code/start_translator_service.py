#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Translator Service Deployment Script
- Starts the translator service as a managed background process
- Monitors health and automatically restarts if needed
- Provides logging and status information
"""
import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import json
import zmq
from pathlib import Path
from datetime import datetime
from common.env_helpers import get_env

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("translator_service.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("translator_service")

# Constants
HEALTH_CHECK_INTERVAL = 30  # seconds
ZMQ_PORT = int(os.getenv('TRANSLATOR_PORT', '5563'))
ZMQ_SERVER = "localhost"
MAX_RESTART_ATTEMPTS = 5
RESTART_COOLDOWN = 60  # seconds
SERVICE_SCRIPT = Path("agents/translator_fixed.py")

class TranslatorService:
    """Manager for the translator service process"""
    
    def __init__(self):
        """Initialize the service manager"""
        self.process = None
        self.start_time = None
        self.restart_count = 0
        self.last_restart = 0
        self.zmq_context = zmq.Context()
        self.running = False
        self.status = "Not started"
    
    def start(self):
        """Start the translator service"""
        if self.process and self.process.poll() is None:
            logger.info("Service is already running.")
            return True
        
        try:
            logger.info("Starting translator service...")
            
            # Create logs directory if it doesn't exist
            Path("logs").mkdir(exist_ok=True)
            
            # Start the process
            self.process = subprocess.Popen(
                [sys.executable, str(SERVICE_SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.start_time = time.time()
            self.running = True
            self.status = "Started"
            logger.info(f"Service started with PID {self.process.pid}")
            
            # Wait a bit to ensure it's actually running
            time.sleep(2)
            
            # Check if it's still running
            if self.process.poll() is not None:
                logger.error(f"Service failed to start. Exit code: {self.process.poll()}")
                self.running = False
                self.status = f"Failed to start (exit code {self.process.poll()})"
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error starting service: {str(e)}")
            self.status = f"Error: {str(e)}"
            return False
    
    def stop(self):
        """Stop the translator service"""
        if not self.process:
            logger.info("No service process to stop.")
            return True
        
        try:
            logger.info(f"Stopping service (PID {self.process.pid})...")
            
            # Try to terminate gracefully first
            self.process.terminate()
            
            # Wait for up to 5 seconds for graceful termination
            for _ in range(10):
                if self.process.poll() is not None:
                    logger.info("Service stopped gracefully.")
                    break
                time.sleep(0.5)
            
            # If still running, force kill
            if self.process.poll() is None:
                logger.warning("Service did not terminate gracefully, forcing kill...")
                self.process.kill()
                time.sleep(1)
            
            self.running = False
            self.status = "Stopped"
            return True
        except Exception as e:
            logger.error(f"Error stopping service: {str(e)}")
            self.status = f"Error stopping: {str(e)}"
            return False
    
    def restart(self):
        """Restart the translator service"""
        logger.info("Restarting translator service...")
        
        # Check if we're restarting too frequently
        current_time = time.time()
        if current_time - self.last_restart < RESTART_COOLDOWN:
            logger.warning("Attempting to restart too quickly. Enforcing cooldown.")
            time.sleep(RESTART_COOLDOWN - (current_time - self.last_restart))
        
        # Update restart tracking
        self.restart_count += 1
        self.last_restart = time.time()
        
        # Stop and start the service
        self.stop()
        return self.start()
    
    def check_health(self):
        """Check if the service is healthy"""
        # First check if process is running
        if not self.process or self.process.poll() is not None:
            logger.error("Service process is not running.")
            self.running = False
            self.status = "Process died"
            return False
        
        # Check if the service is responsive via ZMQ
        try:
            socket = self.zmq_context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket.connect(f"tcp://{ZMQ_SERVER}:{ZMQ_PORT}")
            
            # Send health check request
            request = {"action": "health_check"}
            socket.send_string(json.dumps(request))
            
            # Wait for response
            response_json = socket.recv_string()
            response = json.loads(response_json)
            
            # Check response
            if response.get("status") == "success":
                uptime = response.get("uptime_seconds", 0)
                cache_size = response.get("cache_size", 0)
                cache_hit_ratio = response.get("cache_hit_ratio", 0)
                
                self.status = "Healthy"
                logger.debug(f"Health check passed. Uptime: {uptime:.1f}s, Cache: {cache_size} items, Hit ratio: {cache_hit_ratio:.1f}%")
                return True
            else:
                logger.warning(f"Health check returned unexpected response: {response}")
                self.status = "Unhealthy response"
                return False
                
        except zmq.error.Again:
            logger.error("Health check timed out - service not responding")
            self.status = "Not responding"
            return False
        except Exception as e:
            logger.error(f"Error during health check: {str(e)}")
            self.status = f"Health check error: {str(e)}"
            return False
        finally:
            socket.close()
    
    def monitor(self):
        """Monitor the service health and restart if needed"""
        try:
            logger.info("Starting health monitoring...")
            
            while self.running:
                time.sleep(HEALTH_CHECK_INTERVAL)
                
                # Check the service health
                if not self.check_health():
                    logger.warning("Service is unhealthy!")
                    
                    if self.restart_count < MAX_RESTART_ATTEMPTS:
                        logger.info(f"Attempting restart ({self.restart_count + 1}/{MAX_RESTART_ATTEMPTS})...")
                        self.restart()
                    else:
                        logger.error(f"Maximum restart attempts ({MAX_RESTART_ATTEMPTS}) reached. Giving up.")
                        self.running = False
                        self.status = "Failed after max restarts"
                        break
                
                # Also check for any output from the process
                self._read_process_output()
        
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user.")
        except Exception as e:
            logger.error(f"Error in monitor loop: {str(e)}")
        finally:
            self.stop()
    
    def _read_process_output(self):
        """Read and log output from the service process"""
        if not self.process or not self.process.stdout:
            return
        
        while True:
            # Read a line if available (non-blocking)
            output = self.process.stdout.readline()
            if not output:
                break
            
            # Log the output
            output = output.strip()
            if output:
                logger.debug(f"Service output: {output}")
    
    def get_status(self):
        """Get detailed status information"""
        if not self.process:
            return {
                "status": self.status,
                "running": False,
                "uptime": 0,
                "pid": None,
                "restart_count": self.restart_count,
                "last_restart": self.last_restart
            }
        
        return {
            "status": self.status,
            "running": self.running and self.process.poll() is None,
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "pid": self.process.pid if self.process.poll() is None else None,
            "exit_code": self.process.poll(),
            "restart_count": self.restart_count,
            "last_restart": self.last_restart
        }

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Translator Service Manager")
    parser.add_argument('--start', action='store_true', help='Start the service')
    parser.add_argument('--stop', action='store_true', help='Stop the service')
    parser.add_argument('--restart', action='store_true', help='Restart the service')
    parser.add_argument('--status', action='store_true', help='Check service status')
    parser.add_argument('--monitor', action='store_true', help='Start and monitor the service')
    args = parser.parse_args()
    
    service = TranslatorService()
    
    if args.start:
        service.start()
        
    elif args.stop:
        service.stop()
        
    elif args.restart:
        service.restart()
        
    elif args.status:
        status = service.get_status()
        print("\nTranslator Service Status:")
        print(f"  Status: {status['status']}")
        print(f"  Running: {'Yes' if status.get('running') else 'No'}")
        if status.get('uptime'):
            print(f"  Uptime: {status['uptime']:.1f} seconds")
        if status.get('pid'):
            print(f"  PID: {status['pid']}")
        if status.get('restart_count'):
            print(f"  Restart count: {status['restart_count']}")
        
    elif args.monitor:
        # Start the service if it's not already running
        if service.start():
            # Monitor the service
            service.monitor()
            
    else:
        # Default action: print help
        parser.print_help()

if __name__ == "__main__":
    main()
