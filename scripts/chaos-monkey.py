#!/usr/bin/env python3
"""
AI System Chaos Monkey
Implements chaos engineering for resilience testing across MainPC and PC2

Features:
- Service fault injection (latency, errors, crashes)
- Network partitioning and packet loss
- Resource exhaustion (CPU, memory, GPU)
- Dependency failures
- Gradual degradation scenarios
- Recovery validation
"""

import os
import sys
import time
import json
import random
import logging
import argparse
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import requests
import yaml
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChaosType(Enum):
    """Types of chaos experiments"""
    LATENCY_INJECTION = "latency_injection"
    ERROR_INJECTION = "error_injection"
    SERVICE_KILL = "service_kill"
    NETWORK_PARTITION = "network_partition"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"
    GPU_SATURATION = "gpu_saturation"
    MEMORY_PRESSURE = "memory_pressure"
    DISK_PRESSURE = "disk_pressure"

class ChaosScope(Enum):
    """Scope of chaos impact"""
    SINGLE_SERVICE = "single_service"
    SERVICE_GROUP = "service_group"
    ENTIRE_SYSTEM = "entire_system"
    CROSS_SYSTEM = "cross_system"  # MainPC + PC2

@dataclass
class ChaosExperiment:
    """Chaos experiment configuration"""
    name: str
    type: ChaosType
    scope: ChaosScope
    target: str
    duration: int  # seconds
    intensity: float  # 0.0 to 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    steady_state_hypothesis: Dict[str, Any] = field(default_factory=dict)
    rollback_strategy: str = "immediate"
    
class ChaosMonkey:
    """Main chaos engineering controller"""
    
    def __init__(self, config_path: str = "config/chaos/chaos-config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.active_experiments: Dict[str, ChaosExperiment] = {}
        self.experiment_history: List[Dict[str, Any]] = []
        self.monitoring_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
        
    def _load_config(self) -> Dict[str, Any]:
        """Load chaos configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default chaos configuration"""
        return {
            'global': {
                'max_concurrent_experiments': 3,
                'safety_checks': True,
                'auto_rollback_timeout': 300,
                'metrics_collection_interval': 30
            },
            'targets': {
                'mainpc_services': [
                    'coordination', 'memory-stack', 'vision-gpu', 
                    'speech-gpu', 'learning-gpu', 'reasoning-gpu',
                    'language-stack', 'observability'
                ],
                'pc2_services': [
                    'pc2-memory-stack', 'pc2-async-pipeline', 
                    'pc2-tutoring-cpu', 'pc2-vision-dream-gpu',
                    'pc2-web-interface'
                ]
            },
            'experiments': {}
        }
    
    def check_steady_state(self, hypothesis: Dict[str, Any]) -> bool:
        """Check if system is in steady state"""
        try:
            for check in hypothesis.get('checks', []):
                metric = check['metric']
                threshold = check['threshold']
                operator = check.get('operator', 'lt')
                
                # Query Prometheus for metric
                query = f"query?query={metric}"
                response = requests.get(f"{self.monitoring_url}/api/v1/{query}")
                
                if response.status_code != 200:
                    logger.error(f"Failed to query metric {metric}")
                    return False
                
                data = response.json()
                if not data['data']['result']:
                    logger.warning(f"No data for metric {metric}")
                    continue
                
                value = float(data['data']['result'][0]['value'][1])
                
                # Check threshold
                if operator == 'lt' and value >= threshold:
                    return False
                elif operator == 'gt' and value <= threshold:
                    return False
                elif operator == 'eq' and abs(value - threshold) > 0.01:
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Steady state check failed: {e}")
            return False
    
    def inject_latency(self, target: str, duration: int, latency_ms: int):
        """Inject network latency"""
        logger.info(f"Injecting {latency_ms}ms latency to {target} for {duration}s")
        
        try:
            # Using tc (traffic control) for latency injection
            subprocess.run([
                'docker', 'exec', target,
                'tc', 'qdisc', 'add', 'dev', 'eth0', 'root', 'netem', 
                'delay', f'{latency_ms}ms'
            ], check=True)
            
            # Wait for duration
            time.sleep(duration)
            
            # Remove latency
            subprocess.run([
                'docker', 'exec', target,
                'tc', 'qdisc', 'del', 'dev', 'eth0', 'root'
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Latency injection failed: {e}")
    
    def inject_errors(self, target: str, duration: int, error_rate: float):
        """Inject HTTP errors"""
        logger.info(f"Injecting {error_rate*100}% error rate to {target} for {duration}s")
        
        try:
            # Create error injection script
            error_script = f"""
import time
import random
import os
import signal

def inject_errors():
    # Set environment variable for error injection
    os.environ['CHAOS_ERROR_RATE'] = '{error_rate}'
    time.sleep({duration})
    # Clean up
    if 'CHAOS_ERROR_RATE' in os.environ:
        del os.environ['CHAOS_ERROR_RATE']

if __name__ == "__main__":
    inject_errors()
"""
            
            # Write script to container
            with open('/tmp/error_injection.py', 'w') as f:
                f.write(error_script)
            
            subprocess.run([
                'docker', 'cp', '/tmp/error_injection.py', 
                f'{target}:/tmp/error_injection.py'
            ], check=True)
            
            # Execute error injection
            subprocess.run([
                'docker', 'exec', '-d', target,
                'python3', '/tmp/error_injection.py'
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error injection failed: {e}")
    
    def kill_service(self, target: str, duration: int):
        """Kill and restart service"""
        logger.info(f"Killing service {target} for {duration}s")
        
        try:
            # Stop container
            subprocess.run(['docker', 'stop', target], check=True)
            
            # Wait for duration
            time.sleep(duration)
            
            # Restart container
            subprocess.run(['docker', 'start', target], check=True)
            
            # Wait for service to be ready
            self._wait_for_service_ready(target)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Service kill failed: {e}")
    
    def create_network_partition(self, targets: List[str], duration: int):
        """Create network partition between services"""
        logger.info(f"Creating network partition for {targets} for {duration}s")
        
        try:
            # Block traffic between targets
            for i, target1 in enumerate(targets):
                for target2 in targets[i+1:]:
                    # Get container IPs
                    ip1 = self._get_container_ip(target1)
                    ip2 = self._get_container_ip(target2)
                    
                    if ip1 and ip2:
                        # Block traffic using iptables
                        subprocess.run([
                            'docker', 'exec', target1,
                            'iptables', '-A', 'OUTPUT', '-d', ip2, '-j', 'DROP'
                        ], check=True)
                        
                        subprocess.run([
                            'docker', 'exec', target2,
                            'iptables', '-A', 'OUTPUT', '-d', ip1, '-j', 'DROP'
                        ], check=True)
            
            # Wait for duration
            time.sleep(duration)
            
            # Restore connectivity
            for target in targets:
                subprocess.run([
                    'docker', 'exec', target,
                    'iptables', '-F', 'OUTPUT'
                ], check=True)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Network partition failed: {e}")
    
    def exhaust_resources(self, target: str, resource_type: str, duration: int, intensity: float):
        """Exhaust system resources"""
        logger.info(f"Exhausting {resource_type} on {target} at {intensity*100}% intensity for {duration}s")
        
        try:
            if resource_type == 'cpu':
                # CPU stress using stress-ng
                cpu_cores = int(intensity * 8)  # Assuming 8 cores max
                subprocess.run([
                    'docker', 'exec', '-d', target,
                    'stress-ng', '--cpu', str(cpu_cores), '--timeout', f'{duration}s'
                ], check=True)
                
            elif resource_type == 'memory':
                # Memory stress
                memory_mb = int(intensity * 8192)  # Max 8GB
                subprocess.run([
                    'docker', 'exec', '-d', target,
                    'stress-ng', '--vm', '1', '--vm-bytes', f'{memory_mb}M', 
                    '--timeout', f'{duration}s'
                ], check=True)
                
            elif resource_type == 'gpu':
                # GPU stress using nvidia-ml-py
                gpu_script = f"""
import time
import subprocess
import threading

def gpu_stress():
    # Run GPU computation to saturate
    subprocess.run([
        'python3', '-c', 
        '''
import torch
if torch.cuda.is_available():
    device = torch.cuda.current_device()
    for _ in range({duration}):
        x = torch.randn(1000, 1000).cuda()
        y = torch.randn(1000, 1000).cuda()
        z = torch.mm(x, y)
        time.sleep(0.1)
'''
    ])

if __name__ == "__main__":
    gpu_stress()
"""
                
                with open('/tmp/gpu_stress.py', 'w') as f:
                    f.write(gpu_script)
                
                subprocess.run([
                    'docker', 'cp', '/tmp/gpu_stress.py', 
                    f'{target}:/tmp/gpu_stress.py'
                ], check=True)
                
                subprocess.run([
                    'docker', 'exec', '-d', target,
                    'python3', '/tmp/gpu_stress.py'
                ], check=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Resource exhaustion failed: {e}")
    
    def simulate_dependency_failure(self, service: str, dependency: str, duration: int):
        """Simulate external dependency failure"""
        logger.info(f"Simulating {dependency} failure for {service} for {duration}s")
        
        try:
            # Block access to dependency
            if dependency == 'redis':
                # Block Redis port
                subprocess.run([
                    'docker', 'exec', service,
                    'iptables', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '6379', '-j', 'DROP'
                ], check=True)
            elif dependency == 'postgres':
                # Block PostgreSQL port
                subprocess.run([
                    'docker', 'exec', service,
                    'iptables', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '5432', '-j', 'DROP'
                ], check=True)
            elif dependency == 'prometheus':
                # Block Prometheus port
                subprocess.run([
                    'docker', 'exec', service,
                    'iptables', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '9090', '-j', 'DROP'
                ], check=True)
            
            # Wait for duration
            time.sleep(duration)
            
            # Restore access
            subprocess.run([
                'docker', 'exec', service,
                'iptables', '-F', 'OUTPUT'
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Dependency failure simulation failed: {e}")
    
    def _get_container_ip(self, container_name: str) -> Optional[str]:
        """Get container IP address"""
        try:
            result = subprocess.run([
                'docker', 'inspect', '-f', 
                '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
                container_name
            ], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def _wait_for_service_ready(self, service: str, timeout: int = 60):
        """Wait for service to become ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try health check
                result = subprocess.run([
                    'docker', 'exec', service,
                    'curl', '-f', 'http://localhost:8080/health'
                ], capture_output=True, check=True)
                if result.returncode == 0:
                    logger.info(f"Service {service} is ready")
                    return True
            except subprocess.CalledProcessError:
                pass
            time.sleep(5)
        
        logger.warning(f"Service {service} not ready after {timeout}s")
        return False
    
    def run_experiment(self, experiment: ChaosExperiment) -> Dict[str, Any]:
        """Run a chaos experiment"""
        logger.info(f"Starting chaos experiment: {experiment.name}")
        
        start_time = datetime.now()
        experiment_id = f"{experiment.name}_{int(start_time.timestamp())}"
        
        # Check steady state before experiment
        if experiment.steady_state_hypothesis:
            if not self.check_steady_state(experiment.steady_state_hypothesis):
                logger.error("System not in steady state, aborting experiment")
                return {
                    'experiment_id': experiment_id,
                    'status': 'aborted',
                    'reason': 'steady_state_failed'
                }
        
        # Record experiment start
        self.active_experiments[experiment_id] = experiment
        
        result = {
            'experiment_id': experiment_id,
            'name': experiment.name,
            'type': experiment.type.value,
            'target': experiment.target,
            'start_time': start_time.isoformat(),
            'status': 'running'
        }
        
        try:
            # Execute chaos based on type
            if experiment.type == ChaosType.LATENCY_INJECTION:
                self.inject_latency(
                    experiment.target,
                    experiment.duration,
                    experiment.parameters.get('latency_ms', 1000)
                )
            elif experiment.type == ChaosType.ERROR_INJECTION:
                self.inject_errors(
                    experiment.target,
                    experiment.duration,
                    experiment.intensity
                )
            elif experiment.type == ChaosType.SERVICE_KILL:
                self.kill_service(experiment.target, experiment.duration)
            elif experiment.type == ChaosType.NETWORK_PARTITION:
                targets = experiment.parameters.get('targets', [experiment.target])
                self.create_network_partition(targets, experiment.duration)
            elif experiment.type == ChaosType.RESOURCE_EXHAUSTION:
                resource_type = experiment.parameters.get('resource_type', 'cpu')
                self.exhaust_resources(
                    experiment.target, resource_type, 
                    experiment.duration, experiment.intensity
                )
            elif experiment.type == ChaosType.DEPENDENCY_FAILURE:
                dependency = experiment.parameters.get('dependency', 'redis')
                self.simulate_dependency_failure(
                    experiment.target, dependency, experiment.duration
                )
            
            result['status'] = 'completed'
            
        except Exception as e:
            logger.error(f"Experiment {experiment.name} failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
        
        finally:
            end_time = datetime.now()
            result['end_time'] = end_time.isoformat()
            result['duration'] = (end_time - start_time).total_seconds()
            
            # Remove from active experiments
            if experiment_id in self.active_experiments:
                del self.active_experiments[experiment_id]
            
            # Add to history
            self.experiment_history.append(result)
            
            # Check steady state after experiment
            if experiment.steady_state_hypothesis:
                time.sleep(30)  # Wait for system to stabilize
                steady_state_recovered = self.check_steady_state(experiment.steady_state_hypothesis)
                result['steady_state_recovered'] = steady_state_recovered
                
                if not steady_state_recovered:
                    logger.warning("System did not return to steady state after experiment")
        
        logger.info(f"Experiment {experiment.name} completed with status: {result['status']}")
        return result
    
    def run_chaos_schedule(self, schedule_path: str):
        """Run scheduled chaos experiments"""
        try:
            with open(schedule_path, 'r') as f:
                schedule = yaml.safe_load(f)
            
            for experiment_config in schedule.get('experiments', []):
                # Create experiment object
                experiment = ChaosExperiment(
                    name=experiment_config['name'],
                    type=ChaosType(experiment_config['type']),
                    scope=ChaosScope(experiment_config.get('scope', 'single_service')),
                    target=experiment_config['target'],
                    duration=experiment_config['duration'],
                    intensity=experiment_config.get('intensity', 0.5),
                    parameters=experiment_config.get('parameters', {}),
                    steady_state_hypothesis=experiment_config.get('steady_state_hypothesis', {}),
                    rollback_strategy=experiment_config.get('rollback_strategy', 'immediate')
                )
                
                # Run experiment
                result = self.run_experiment(experiment)
                
                # Wait between experiments
                wait_time = experiment_config.get('wait_after', 60)
                if wait_time > 0:
                    logger.info(f"Waiting {wait_time}s before next experiment")
                    time.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Failed to run chaos schedule: {e}")
    
    def emergency_stop(self):
        """Emergency stop all active experiments"""
        logger.warning("Emergency stop triggered - stopping all active experiments")
        
        for experiment_id, experiment in self.active_experiments.items():
            try:
                # Restore services/networks
                if experiment.type == ChaosType.SERVICE_KILL:
                    subprocess.run(['docker', 'start', experiment.target], check=False)
                elif experiment.type in [ChaosType.NETWORK_PARTITION, ChaosType.DEPENDENCY_FAILURE]:
                    subprocess.run([
                        'docker', 'exec', experiment.target,
                        'iptables', '-F', 'OUTPUT'
                    ], check=False)
                elif experiment.type == ChaosType.LATENCY_INJECTION:
                    subprocess.run([
                        'docker', 'exec', experiment.target,
                        'tc', 'qdisc', 'del', 'dev', 'eth0', 'root'
                    ], check=False)
                
            except Exception as e:
                logger.error(f"Failed to stop experiment {experiment_id}: {e}")
        
        self.active_experiments.clear()
        logger.info("All experiments stopped")

def main():
    parser = argparse.ArgumentParser(description='AI System Chaos Monkey')
    parser.add_argument('--config', default='config/chaos/chaos-config.yaml',
                        help='Chaos configuration file')
    parser.add_argument('--schedule', help='Run experiments from schedule file')
    parser.add_argument('--experiment', help='Run single experiment by name')
    parser.add_argument('--list-experiments', action='store_true',
                        help='List available experiments')
    parser.add_argument('--emergency-stop', action='store_true',
                        help='Emergency stop all running experiments')
    
    args = parser.parse_args()
    
    chaos_monkey = ChaosMonkey(args.config)
    
    if args.emergency_stop:
        chaos_monkey.emergency_stop()
    elif args.list_experiments:
        experiments = chaos_monkey.config.get('experiments', {})
        print("Available experiments:")
        for name, config in experiments.items():
            print(f"  {name}: {config.get('description', 'No description')}")
    elif args.schedule:
        chaos_monkey.run_chaos_schedule(args.schedule)
    elif args.experiment:
        # Run single experiment
        experiment_config = chaos_monkey.config.get('experiments', {}).get(args.experiment)
        if not experiment_config:
            logger.error(f"Experiment {args.experiment} not found")
            sys.exit(1)
        
        experiment = ChaosExperiment(
            name=args.experiment,
            type=ChaosType(experiment_config['type']),
            scope=ChaosScope(experiment_config.get('scope', 'single_service')),
            target=experiment_config['target'],
            duration=experiment_config['duration'],
            intensity=experiment_config.get('intensity', 0.5),
            parameters=experiment_config.get('parameters', {}),
            steady_state_hypothesis=experiment_config.get('steady_state_hypothesis', {})
        )
        
        result = chaos_monkey.run_experiment(experiment)
        print(json.dumps(result, indent=2))
    else:
        print("Please specify --schedule, --experiment, or --list-experiments")

if __name__ == "__main__":
    main()