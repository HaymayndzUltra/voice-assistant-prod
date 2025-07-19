#!/usr/bin/env python3
"""
System Stability Validation Script

This script validates the stability of the AI system by:
1. Running the cleanup script to terminate existing agent processes
2. Starting the Agent Supervisor with the startup configuration
3. Allowing time for system stabilization
4. Performing health checks on all agents
5. Generating a comprehensive health report

Usage:
    python validate_stability_fixed.py [--config CONFIG_PATH] [--stabilize-time SECONDS]
"""

import os
import sys
import time
import json
import argparse
import subprocess
import signal
import logging
from pathlib import Path
from datetime import datetime
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('validate_stability.log')
    ]
)
logger = logging.getLogger('validate_stability')

# Add project root to Python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Default paths - CORRECTED
DEFAULT_CONFIG_PATH = "main_pc_code/NEWMUSTFOLLOW/minimal_system_config_local.yaml"  # Use the minimal config
DEFAULT_CLEANUP_SCRIPT = "cleanup_agents.py"  # Root directory
DEFAULT_SUPERVISOR_SCRIPT = "main_pc_code/utils/agent_supervisor.py"
DEFAULT_HEALTH_CHECK_SCRIPT = "main_pc_code/NEWMUSTFOLLOW/check_mvs_health.py"  # Corrected path
DEFAULT_STABILIZE_TIME = 60  # seconds

def run_command(cmd, timeout=None, shell=False):
    """Run a command and return the output."""
    logger.info(f"Running command: {cmd}")
    try:
        if shell:
            process = subprocess.Popen(
                cmd, 
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        stdout, stderr = process.communicate(timeout=timeout)
        
        if process.returncode != 0:
            logger.warning(f"Command exited with code {process.returncode}")
            logger.warning(f"STDERR: {stderr}")
        
        return {
            'returncode': process.returncode,
            'stdout': stdout,
            'stderr': stderr
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        process.kill()
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': 'Command timed out'
        }
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e)
        }

def cleanup_agents():
    """Run the cleanup script to terminate existing agent processes."""
    logger.info("Step 1: Cleaning up existing agent processes")
    
    cleanup_script = Path(DEFAULT_CLEANUP_SCRIPT).resolve()
    
    if not cleanup_script.exists():
        logger.error(f"Cleanup script not found at {cleanup_script}")
        logger.info("Attempting manual cleanup instead")
        return manual_cleanup()
    
    result = run_command([sys.executable, str(cleanup_script)])
    
    if result['returncode'] != 0:
        logger.warning("Cleanup script failed, attempting manual cleanup")
        return manual_cleanup()
    
    logger.info("Cleanup completed successfully")
    return True

def manual_cleanup():
    """Manually terminate agent processes if the cleanup script fails."""
    logger.info("Performing manual cleanup of agent processes")
    
    # Keywords to identify agent processes
    agent_keywords = [
        "agent", "Agent", 
        "service", "Service",
        "monitor", "Monitor",
        "orchestrator", "Orchestrator"
    ]
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if this is a Python process
            if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                # Check if it matches any agent keywords
                if any(keyword in cmdline for keyword in agent_keywords):
                    logger.info(f"Killing process {proc.info['pid']}: {cmdline}")
                    try:
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        killed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to kill process {proc.info['pid']}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    logger.info(f"Manual cleanup completed: killed {killed_count} processes")
    return True

def start_agent_supervisor(config_path):
    """Start the Agent Supervisor with the specified configuration."""
    logger.info("Step 2: Starting Agent Supervisor")
    
    supervisor_script = Path(DEFAULT_SUPERVISOR_SCRIPT).resolve()
    
    if not supervisor_script.exists():
        logger.error(f"Agent Supervisor script not found at {supervisor_script}")
        return None
    
    # Start the supervisor in a new process
    cmd = [sys.executable, str(supervisor_script), "--config", config_path]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Agent Supervisor started with PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start Agent Supervisor: {e}")
        return None

def wait_for_stabilization(seconds):
    """Wait for the system to stabilize."""
    logger.info(f"Step 3: Waiting {seconds} seconds for system stabilization")
    
    # Display a countdown
    for i in range(seconds, 0, -1):
        if i % 10 == 0 or i <= 5:  # Show every 10 seconds and final 5 seconds
            logger.info(f"Stabilization: {i} seconds remaining")
        time.sleep(1)
    
    logger.info("Stabilization period completed")

def check_agent_health():
    """Perform health checks on all agents."""
    logger.info("Step 4: Performing health checks on all agents")
    
    health_check_script = Path(DEFAULT_HEALTH_CHECK_SCRIPT).resolve()
    
    if not health_check_script.exists():
        logger.error(f"Health check script not found at {health_check_script}")
        return None
    
    result = run_command([sys.executable, str(health_check_script)], timeout=120)  # 2 minute timeout
    
    if result['returncode'] != 0:
        logger.warning("Health check script returned non-zero exit code")
    
    return result

def generate_health_report(health_check_result):
    """Generate a comprehensive health report."""
    logger.info("Step 5: Generating health report")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# System Stability Health Report
Generated: {timestamp}

## Health Check Output
```
{health_check_result['stdout']}
```

## Errors/Warnings
```
{health_check_result['stderr']}
```

## Summary
Exit Code: {health_check_result['returncode']}
"""
    
    # Save the report to a file
    report_file = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Health report saved to {report_file}")
    return report, report_file

def update_task_report(report_file):
    """Update the task and report markdown file."""
    logger.info("Updating task&report.md")
    
    task_report_path = Path("main_pc_code/NEWMUSTFOLLOW/documents/task&report.md")
    
    # Create the directory if it doesn't exist
    task_report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read the health report
    with open(report_file, 'r') as f:
        health_report = f.read()
    
    # Extract summary information
    summary = "See full report for details."
    if "HEALTHY" in health_report and "UNHEALTHY" in health_report:
        # Try to extract counts
        healthy_count = 0
        total_count = 0
        
        for line in health_report.split('\n'):
            if "Healthy Agents:" in line or "Healthy:" in line:
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        healthy_count = int(parts[1].strip().split()[0])
                except:
                    pass
            elif "Total Agents:" in line:
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        total_count = int(parts[1].strip())
                except:
                    pass
        
        if total_count > 0:
            summary = f"{healthy_count} out of {total_count} agents are healthy."
    
    # Create or update the task report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    task_report_content = f"""
## System Stability Validation with Agent Supervisor
*Executed on: {timestamp}*

### Task Summary
Validated system stability using the newly implemented Agent Supervisor.

### Process
1. Ran cleanup script to ensure a clean environment
2. Started Agent Supervisor with startup_config.yaml
3. Allowed 60 seconds for system stabilization
4. Ran health check on all agents
5. Generated health report

### Results
{summary}

### Full Report
See [{report_file}]({report_file}) for the complete health check results.
"""
    
    # Append to existing file or create new one
    if task_report_path.exists():
        with open(task_report_path, 'a') as f:
            f.write(task_report_content)
    else:
        with open(task_report_path, 'w') as f:
            f.write("# Task and Report Log\n")
            f.write(task_report_content)
    
    logger.info(f"Updated task report at {task_report_path}")

def main():
    """Main function to run the validation process."""
    parser = argparse.ArgumentParser(description="Validate system stability")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to configuration file")
    parser.add_argument("--stabilize-time", type=int, default=DEFAULT_STABILIZE_TIME, help="Stabilization time in seconds")
    args = parser.parse_args()
    
    logger.info("Starting system stability validation")
    logger.info(f"Configuration file: {args.config}")
    logger.info(f"Stabilization time: {args.stabilize_time} seconds")
    
    # Step 1: Clean up existing agent processes
    if not cleanup_agents():
        logger.error("Failed to clean up existing agent processes")
        return 1
    
    # Step 2: Start the Agent Supervisor
    supervisor_process = start_agent_supervisor(args.config)
    if not supervisor_process:
        logger.error("Failed to start Agent Supervisor")
        return 1
    
    try:
        # Step 3: Wait for system stabilization
        wait_for_stabilization(args.stabilize_time)
        
        # Step 4: Perform health checks
        health_check_result = check_agent_health()
        if not health_check_result:
            logger.error("Failed to perform health checks")
            return 1
        
        # Step 5: Generate health report
        report, report_file = generate_health_report(health_check_result)
        
        # Step 6: Update task report
        update_task_report(report_file)
        
        # Print the report to stdout
        print("\n" + "="*80)
        print("HEALTH CHECK REPORT")
        print("="*80)
        print(report)
        
        return 0
    finally:
        # Terminate the supervisor process
        logger.info("Terminating Agent Supervisor")
        try:
            supervisor_process.terminate()
            supervisor_process.wait(timeout=5)
        except:
            logger.warning("Failed to terminate Agent Supervisor gracefully, killing it")
            try:
                supervisor_process.kill()
            except:
                pass

if __name__ == "__main__":
    sys.exit(main()) 