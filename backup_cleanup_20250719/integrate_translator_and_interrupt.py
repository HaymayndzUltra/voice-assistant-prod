#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Translator and Interrupt Handler Integration Script
--------------------------------------------------
This script integrates:
1. Consolidated Translator with Task Router and Language Processing
2. Streaming Interrupt Handler with Audio Pipeline and TTS System

Usage:
    python integrate_translator_and_interrupt.py
"""

import os
import sys
import json
import logging
import subprocess
import time
import zmq
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IntegrationScript")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Add main_pc_code to path
sys.path.insert(0, str(MAIN_PC_CODE))
from utils.config_loader import load_config

# Load configuration
config = load_config()

class IntegrationTester:
    """Test and integrate components of the system."""
    
    def __init__(self):
        self.context = zmq.Context()
        self.translator_port = int(config.get("consolidated_translator_port", 5563))
        self.task_router_port = int(config.get("task_router_port", 7000))
        self.interrupt_handler_port = int(config.get("streaming_interrupt_handler_port", 5576))
        self.tts_port = int(config.get("streaming_tts_agent_port", 5562))
        self.stt_port = int(config.get("streaming_speech_recognition_port", 5575))
        
        self.translator_socket = None
        self.task_router_socket = None
        self.interrupt_pub_socket = None
        self.interrupt_sub_socket = None
        self.tts_socket = None
        
        self.test_results = {
            "translator_integration": {
                "status": "not_tested",
                "details": []
            },
            "interrupt_handler_integration": {
                "status": "not_tested",
                "details": []
            }
        }
        
        self.processes = []
    
    def start_required_services(self):
        """Start required services if they're not already running."""
        logger.info("Checking if required services are running...")
        
        # Check if translator is running
        if not self._is_service_running(self.translator_port):
            logger.info("Starting Consolidated Translator...")
            translator_path = MAIN_PC_CODE / "FORMAINPC" / "consolidated_translator.py"
            if translator_path.exists():
                process = subprocess.Popen(
                    [sys.executable, str(translator_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.processes.append(("Translator", process))
                logger.info("Consolidated Translator started")
                time.sleep(2)  # Give it time to initialize
            else:
                logger.error(f"Translator script not found at {translator_path}")
        else:
            logger.info("Consolidated Translator is already running")
        
        # Check if interrupt handler is running
        if not self._is_service_running(self.interrupt_handler_port):
            logger.info("Starting Streaming Interrupt Handler...")
            interrupt_path = MAIN_PC_CODE / "agents" / "streaming_interrupt_handler.py"
            if interrupt_path.exists():
                process = subprocess.Popen(
                    [sys.executable, str(interrupt_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.processes.append(("Interrupt Handler", process))
                logger.info("Streaming Interrupt Handler started")
                time.sleep(2)  # Give it time to initialize
            else:
                logger.error(f"Interrupt handler script not found at {interrupt_path}")
        else:
            logger.info("Streaming Interrupt Handler is already running")
    
    def _is_service_running(self, port: int) -> bool:
        """Check if a service is running on the specified port."""
        try:
            # Try to connect to the health check endpoint
            response = requests.get(f"http://localhost:{port+1}/health", timeout=1)
            return response.status_code == 200
        except:
            try:
                # If health check fails, try to connect with ZMQ
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, 1000)
                socket.connect(f"tcp://localhost:{port}")
                socket.send_string("ping")
                socket.recv_string()
                socket.close()
                return True
            except:
                return False
    
    def setup_connections(self):
        """Set up ZMQ connections to services."""
        logger.info("Setting up connections to services...")
        
        # Connect to translator
        self.translator_socket = self.context.socket(zmq.REQ)
        self.translator_socket.setsockopt(zmq.RCVTIMEO, 5000)
        self.translator_socket.connect(f"tcp://localhost:{self.translator_port}")
        
        # Connect to task router
        self.task_router_socket = self.context.socket(zmq.REQ)
        self.task_router_socket.setsockopt(zmq.RCVTIMEO, 5000)
        self.task_router_socket.connect(f"tcp://localhost:{self.task_router_port}")
        
        # Connect to interrupt handler (publisher)
        self.interrupt_pub_socket = self.context.socket(zmq.PUB)
        self.interrupt_pub_socket.connect(f"tcp://localhost:{self.interrupt_handler_port}")
        
        # Connect to interrupt handler (subscriber)
        self.interrupt_sub_socket = self.context.socket(zmq.SUB)
        self.interrupt_sub_socket.connect(f"tcp://localhost:{self.interrupt_handler_port}")
        self.interrupt_sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Connect to TTS agent
        self.tts_socket = self.context.socket(zmq.REQ)
        self.tts_socket.setsockopt(zmq.RCVTIMEO, 5000)
        self.tts_socket.connect(f"tcp://localhost:{self.tts_port}")
        
        logger.info("Connections set up successfully")
    
    def test_translator_integration(self):
        """Test the integration of the Consolidated Translator with Task Router."""
        logger.info("Testing Consolidated Translator integration...")
        
        # Test direct connection to translator
        try:
            # Test translation
            self.translator_socket.send_string(json.dumps({
                "action": "translate",
                "text": "Buksan ang file",
                "source_language": "tl",
                "target_language": "en"
            }))
            
            response = self.translator_socket.recv_string()
            response_data = json.loads(response)
            
            if response_data.get("status") == "success" and "open the file" in response_data.get("translated_text", "").lower():
                logger.info("Direct translator test successful")
                self.test_results["translator_integration"]["details"].append({
                    "test": "direct_connection",
                    "status": "success",
                    "response": response_data
                })
            else:
                logger.warning(f"Direct translator test failed: {response_data}")
                self.test_results["translator_integration"]["details"].append({
                    "test": "direct_connection",
                    "status": "failed",
                    "response": response_data
                })
        except Exception as e:
            logger.error(f"Error testing direct translator connection: {e}")
            self.test_results["translator_integration"]["details"].append({
                "test": "direct_connection",
                "status": "error",
                "error": str(e)
            })
        
        # Test task router integration
        try:
            # Send a task that requires translation
            self.task_router_socket.send_string(json.dumps({
                "action": "process",
                "task_type": "translation",
                "text": "Buksan ang file",
                "source_language": "tl",
                "target_language": "en"
            }))
            
            response = self.task_router_socket.recv_string()
            response_data = json.loads(response)
            
            if response_data.get("status") == "success":
                logger.info("Task router integration test successful")
                self.test_results["translator_integration"]["details"].append({
                    "test": "task_router_integration",
                    "status": "success",
                    "response": response_data
                })
            else:
                logger.warning(f"Task router integration test failed: {response_data}")
                self.test_results["translator_integration"]["details"].append({
                    "test": "task_router_integration",
                    "status": "failed",
                    "response": response_data
                })
        except Exception as e:
            logger.error(f"Error testing task router integration: {e}")
            self.test_results["translator_integration"]["details"].append({
                "test": "task_router_integration",
                "status": "error",
                "error": str(e)
            })
        
        # Determine overall status
        success_count = sum(1 for detail in self.test_results["translator_integration"]["details"] if detail["status"] == "success")
        if success_count == len(self.test_results["translator_integration"]["details"]):
            self.test_results["translator_integration"]["status"] = "success"
        elif success_count > 0:
            self.test_results["translator_integration"]["status"] = "partial_success"
        else:
            self.test_results["translator_integration"]["status"] = "failed"
    
    def test_interrupt_handler_integration(self):
        """Test the integration of the Streaming Interrupt Handler with Audio Pipeline and TTS."""
        logger.info("Testing Streaming Interrupt Handler integration...")
        
        # Test interrupt detection
        try:
            # Simulate STT sending a partial transcript with interruption keyword
            self.interrupt_pub_socket.send_string(json.dumps({
                "type": "partial_transcription",
                "text": "Stop talking please",
                "detected_language": "en"
            }))
            
            # Wait a moment for processing
            time.sleep(1)
            
            # Check if TTS received stop command
            self.tts_socket.send_string(json.dumps({
                "action": "status"
            }))
            
            response = self.tts_socket.recv_string()
            response_data = json.loads(response)
            
            if response_data.get("status") == "idle" or response_data.get("was_interrupted", False):
                logger.info("Interrupt detection test successful")
                self.test_results["interrupt_handler_integration"]["details"].append({
                    "test": "interrupt_detection",
                    "status": "success",
                    "response": response_data
                })
            else:
                logger.warning(f"Interrupt detection test failed: {response_data}")
                self.test_results["interrupt_handler_integration"]["details"].append({
                    "test": "interrupt_detection",
                    "status": "failed",
                    "response": response_data
                })
        except Exception as e:
            logger.error(f"Error testing interrupt detection: {e}")
            self.test_results["interrupt_handler_integration"]["details"].append({
                "test": "interrupt_detection",
                "status": "error",
                "error": str(e)
            })
        
        # Test direct interrupt command
        try:
            # Send direct interrupt command
            self.interrupt_pub_socket.send_string(json.dumps({
                "type": "interrupt",
                "timestamp": time.time()
            }))
            
            # Wait a moment for processing
            time.sleep(1)
            
            # Check if interrupt was received
            try:
                self.interrupt_sub_socket.setsockopt(zmq.RCVTIMEO, 1000)
                response = self.interrupt_sub_socket.recv_string()
                response_data = json.loads(response)
                
                if response_data.get("type") == "interrupt":
                    logger.info("Direct interrupt test successful")
                    self.test_results["interrupt_handler_integration"]["details"].append({
                        "test": "direct_interrupt",
                        "status": "success",
                        "response": response_data
                    })
                else:
                    logger.warning(f"Direct interrupt test failed: {response_data}")
                    self.test_results["interrupt_handler_integration"]["details"].append({
                        "test": "direct_interrupt",
                        "status": "failed",
                        "response": response_data
                    })
            except zmq.Again:
                logger.warning("No interrupt response received")
                self.test_results["interrupt_handler_integration"]["details"].append({
                    "test": "direct_interrupt",
                    "status": "failed",
                    "error": "No response received"
                })
        except Exception as e:
            logger.error(f"Error testing direct interrupt: {e}")
            self.test_results["interrupt_handler_integration"]["details"].append({
                "test": "direct_interrupt",
                "status": "error",
                "error": str(e)
            })
        
        # Determine overall status
        success_count = sum(1 for detail in self.test_results["interrupt_handler_integration"]["details"] if detail["status"] == "success")
        if success_count == len(self.test_results["interrupt_handler_integration"]["details"]):
            self.test_results["interrupt_handler_integration"]["status"] = "success"
        elif success_count > 0:
            self.test_results["interrupt_handler_integration"]["status"] = "partial_success"
        else:
            self.test_results["interrupt_handler_integration"]["status"] = "failed"
    
    def update_task_router_config(self):
        """Update Task Router configuration to include Consolidated Translator."""
        logger.info("Updating Task Router configuration...")
        
        try:
            # Path to task router config
            task_router_config_path = MAIN_PC_CODE / "config" / "task_router_config.json"
            
            # Create config if it doesn't exist
            if not task_router_config_path.exists():
                task_router_config = {
                    "services": {}
                }
            else:
                with open(task_router_config_path, 'r') as f:
                    task_router_config = json.load(f)
            
            # Add or update translator service
            task_router_config["services"]["translator"] = {
                "name": "ConsolidatedTranslator",
                "port": self.translator_port,
                "host": "localhost",
                "capabilities": ["translation", "language_detection"],
                "priority": 1
            }
            
            # Save updated config
            with open(task_router_config_path, 'w') as f:
                json.dump(task_router_config, f, indent=2)
            
            logger.info(f"Task Router configuration updated at {task_router_config_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating Task Router configuration: {e}")
            return False
    
    def update_audio_pipeline_config(self):
        """Update Audio Pipeline configuration to include Streaming Interrupt Handler."""
        logger.info("Updating Audio Pipeline configuration...")
        
        try:
            # Path to audio pipeline config
            audio_config_path = MAIN_PC_CODE / "config" / "audio_pipeline_config.json"
            
            # Create config if it doesn't exist
            if not audio_config_path.exists():
                audio_config = {
                    "components": {}
                }
            else:
                with open(audio_config_path, 'r') as f:
                    audio_config = json.load(f)
            
            # Add or update interrupt handler
            audio_config["components"]["interrupt_handler"] = {
                "name": "StreamingInterruptHandler",
                "port": self.interrupt_handler_port,
                "host": "localhost",
                "capabilities": ["interrupt", "streaming"],
                "priority": 1
            }
            
            # Save updated config
            with open(audio_config_path, 'w') as f:
                json.dump(audio_config, f, indent=2)
            
            logger.info(f"Audio Pipeline configuration updated at {audio_config_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating Audio Pipeline configuration: {e}")
            return False
    
    def generate_report(self):
        """Generate integration report."""
        logger.info("Generating integration report...")
        
        report = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "translator_integration": self.test_results["translator_integration"],
            "interrupt_handler_integration": self.test_results["interrupt_handler_integration"],
            "configurations_updated": {
                "task_router": self.update_task_router_config(),
                "audio_pipeline": self.update_audio_pipeline_config()
            }
        }
        
        # Save report to file
        report_path = OUTPUT_DIR / "integration_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Integration report saved to {report_path}")
        
        # Print summary
        print("\n=== Integration Report Summary ===")
        print(f"Translator Integration: {self.test_results['translator_integration']['status']}")
        print(f"Interrupt Handler Integration: {self.test_results['interrupt_handler_integration']['status']}")
        print(f"Task Router Config Updated: {report['configurations_updated']['task_router']}")
        print(f"Audio Pipeline Config Updated: {report['configurations_updated']['audio_pipeline']}")
        print(f"Full report saved to {report_path}")
        
        return report
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        
        # Close ZMQ sockets
        if hasattr(self, 'translator_socket') and self.translator_socket:
            self.translator_socket.close()
        
        if hasattr(self, 'task_router_socket') and self.task_router_socket:
            self.task_router_socket.close()
        
        if hasattr(self, 'interrupt_pub_socket') and self.interrupt_pub_socket:
            self.interrupt_pub_socket.close()
        
        if hasattr(self, 'interrupt_sub_socket') and self.interrupt_sub_socket:
            self.interrupt_sub_socket.close()
        
        if hasattr(self, 'tts_socket') and self.tts_socket:
            self.tts_socket.close()
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        # Stop processes we started
        for name, process in self.processes:
            logger.info(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} did not terminate gracefully, killing...")
                process.kill()
        
        logger.info("Cleanup complete")

def main():
    """Main function."""
    print("=== Translator and Interrupt Handler Integration ===")
    
    tester = IntegrationTester()
    
    try:
        # Start required services
        tester.start_required_services()
        
        # Set up connections
        tester.setup_connections()
        
        # Test translator integration
        tester.test_translator_integration()
        
        # Test interrupt handler integration
        tester.test_interrupt_handler_integration()
        
        # Generate report
        tester.generate_report()
    finally:
        # Clean up resources
        tester.cleanup()
    
    print("\nIntegration testing complete!")

if __name__ == "__main__":
    main() 