#!/usr/bin/env python3
"""
AI System Load Testing Suite
Comprehensive load testing with progressive traffic patterns and GPU stress scenarios

Features:
- Progressive load testing (ramp-up, steady-state, ramp-down)
- AI-specific workload simulation (conversation, inference, training)
- GPU stress testing with memory pressure
- Cross-system load testing (MainPC + PC2)
- Real-time metrics collection
- Automated performance regression detection
"""

import os
import sys
import time
import json
import asyncio
import aiohttp
import logging
import argparse
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import yaml
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LoadPattern(Enum):
    """Load testing patterns"""
    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    STEP = "step"
    SINE_WAVE = "sine_wave"
    BURST = "burst"

class WorkloadType(Enum):
    """AI workload types"""
    CONVERSATION = "conversation"
    VISION_INFERENCE = "vision_inference"
    SPEECH_PROCESSING = "speech_processing"
    MEMORY_RETRIEVAL = "memory_retrieval"
    REASONING = "reasoning"
    LEARNING = "learning"
    DREAM_GENERATION = "dream_generation"
    MIXED = "mixed"

@dataclass
class LoadTestConfig:
    """Load test configuration"""
    name: str
    pattern: LoadPattern
    workload: WorkloadType
    target_service: str
    max_users: int
    duration: int  # seconds
    ramp_up_time: int = 30
    ramp_down_time: int = 30
    think_time: float = 1.0  # seconds between requests
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_criteria: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LoadTestResult:
    """Load test results"""
    test_name: str
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float  # requests per second
    error_rate: float
    gpu_utilization: Dict[str, float]
    memory_usage: Dict[str, float]
    cpu_usage: Dict[str, float]
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)

class AIWorkloadGenerator:
    """Generate AI-specific workloads"""
    
    def __init__(self):
        self.conversation_templates = [
            "What is the weather like today?",
            "Can you help me solve this math problem: {problem}?",
            "Tell me a story about {topic}.",
            "What are the benefits of {subject}?",
            "How do I {action}?",
            "Explain {concept} in simple terms.",
            "What's the difference between {item1} and {item2}?",
            "Give me advice on {situation}.",
        ]
        
        self.vision_tasks = [
            {"type": "object_detection", "complexity": "medium"},
            {"type": "face_recognition", "complexity": "high"},
            {"type": "scene_analysis", "complexity": "high"},
            {"type": "text_extraction", "complexity": "low"},
            {"type": "image_classification", "complexity": "medium"},
            {"type": "art_generation", "complexity": "very_high"},
        ]
        
        self.speech_tasks = [
            {"type": "transcription", "length": "short"},
            {"type": "translation", "length": "medium"},
            {"type": "synthesis", "voice": "natural"},
            {"type": "emotion_detection", "length": "long"},
        ]
    
    def generate_conversation_payload(self) -> Dict[str, Any]:
        """Generate conversation request payload"""
        import random
        template = random.choice(self.conversation_templates)
        
        # Fill in template variables
        replacements = {
            'problem': '2x + 5 = 15',
            'topic': random.choice(['space', 'ocean', 'forest', 'city']),
            'subject': random.choice(['exercise', 'meditation', 'reading', 'coding']),
            'action': random.choice(['cook pasta', 'learn guitar', 'write code', 'garden']),
            'concept': random.choice(['blockchain', 'AI', 'quantum computing', 'genetics']),
            'item1': 'cats',
            'item2': 'dogs',
            'situation': random.choice(['job interview', 'first date', 'public speaking'])
        }
        
        for key, value in replacements.items():
            template = template.replace(f'{{{key}}}', value)
        
        return {
            'message': template,
            'conversation_id': f'load_test_{int(time.time() * 1000000)}',
            'user_id': f'test_user_{random.randint(1, 1000)}',
            'session_id': f'session_{random.randint(1, 100)}'
        }
    
    def generate_vision_payload(self) -> Dict[str, Any]:
        """Generate vision processing request payload"""
        import random
        task = random.choice(self.vision_tasks)
        
        # Generate synthetic image data (base64 encoded dummy)
        image_sizes = {
            'low': (224, 224),
            'medium': (512, 512),
            'high': (1024, 1024),
            'very_high': (2048, 2048)
        }
        
        size = image_sizes.get(task['complexity'], (512, 512))
        
        return {
            'task_type': task['type'],
            'image_width': size[0],
            'image_height': size[1],
            'format': 'RGB',
            'model_preference': random.choice(['fast', 'accurate', 'balanced']),
            'request_id': f'vision_test_{int(time.time() * 1000000)}'
        }
    
    def generate_speech_payload(self) -> Dict[str, Any]:
        """Generate speech processing request payload"""
        import random
        task = random.choice(self.speech_tasks)
        
        durations = {
            'short': 5,
            'medium': 30,
            'long': 120
        }
        
        return {
            'task_type': task['type'],
            'duration_seconds': durations.get(task.get('length', 'medium'), 30),
            'language': random.choice(['en', 'es', 'fr', 'de', 'ja']),
            'quality': random.choice(['standard', 'high', 'premium']),
            'request_id': f'speech_test_{int(time.time() * 1000000)}'
        }
    
    def generate_memory_payload(self) -> Dict[str, Any]:
        """Generate memory retrieval request payload"""
        import random
        
        queries = [
            "Previous conversations about artificial intelligence",
            "User preferences for music recommendations",
            "Historical data about weather patterns",
            "Knowledge about programming languages",
            "Information about cooking recipes",
            "Details about travel destinations"
        ]
        
        return {
            'query': random.choice(queries),
            'search_type': random.choice(['semantic', 'keyword', 'hybrid']),
            'max_results': random.randint(5, 20),
            'include_metadata': random.choice([True, False]),
            'request_id': f'memory_test_{int(time.time() * 1000000)}'
        }

class LoadTestRunner:
    """Main load testing runner"""
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.workload_generator = AIWorkloadGenerator()
        self.active_tests: Dict[str, threading.Thread] = {}
        self.test_results: List[LoadTestResult] = []
        self.metrics_collector = None
        
    def get_service_endpoint(self, service: str) -> str:
        """Get service endpoint URL"""
        service_ports = {
            'coordination': 'http://localhost:7200',
            'memory-stack': 'http://localhost:7201',
            'vision-gpu': 'http://localhost:7202',
            'speech-gpu': 'http://localhost:7203',
            'reasoning-gpu': 'http://localhost:7204',
            'language-stack': 'http://localhost:7205',
            'pc2-vision-dream-gpu': 'http://localhost:7210',
            'pc2-tutoring-cpu': 'http://localhost:7211',
            'pc2-web-interface': 'http://localhost:7212'
        }
        return service_ports.get(service, 'http://localhost:8080')
    
    def generate_workload_payload(self, workload_type: WorkloadType) -> Dict[str, Any]:
        """Generate payload for specific workload type"""
        if workload_type == WorkloadType.CONVERSATION:
            return self.workload_generator.generate_conversation_payload()
        elif workload_type == WorkloadType.VISION_INFERENCE:
            return self.workload_generator.generate_vision_payload()
        elif workload_type == WorkloadType.SPEECH_PROCESSING:
            return self.workload_generator.generate_speech_payload()
        elif workload_type == WorkloadType.MEMORY_RETRIEVAL:
            return self.workload_generator.generate_memory_payload()
        else:
            return {'request_id': f'test_{int(time.time() * 1000000)}'}
    
    def calculate_user_count(self, pattern: LoadPattern, current_time: float, 
                           max_users: int, duration: int, ramp_up_time: int, 
                           ramp_down_time: int) -> int:
        """Calculate current user count based on load pattern"""
        if pattern == LoadPattern.CONSTANT:
            return max_users
        
        elif pattern == LoadPattern.RAMP_UP:
            if current_time <= ramp_up_time:
                return int(max_users * (current_time / ramp_up_time))
            elif current_time <= duration - ramp_down_time:
                return max_users
            else:
                remaining_time = duration - current_time
                return int(max_users * (remaining_time / ramp_down_time))
        
        elif pattern == LoadPattern.SPIKE:
            spike_start = duration * 0.3
            spike_duration = duration * 0.1
            if spike_start <= current_time <= spike_start + spike_duration:
                return max_users
            else:
                return max_users // 4
        
        elif pattern == LoadPattern.STEP:
            step_duration = duration // 4
            step = int(current_time // step_duration)
            return min(max_users * (step + 1) // 4, max_users)
        
        elif pattern == LoadPattern.SINE_WAVE:
            cycle_time = duration / 2  # 2 full cycles
            amplitude = max_users * 0.4
            baseline = max_users * 0.6
            return int(baseline + amplitude * np.sin(2 * np.pi * current_time / cycle_time))
        
        elif pattern == LoadPattern.BURST:
            burst_interval = 60  # 60 second bursts
            if int(current_time) % burst_interval < 10:  # 10 second bursts
                return max_users
            else:
                return max_users // 10
        
        return max_users
    
    async def send_request(self, session: aiohttp.ClientSession, endpoint: str, 
                          payload: Dict[str, Any], timeout: int = 30) -> Tuple[bool, float, str]:
        """Send individual request"""
        start_time = time.time()
        try:
            async with session.post(endpoint, json=payload, timeout=timeout) as response:
                response_time = time.time() - start_time
                success = response.status < 400
                error_msg = "" if success else f"HTTP {response.status}"
                return success, response_time, error_msg
        except asyncio.TimeoutError:
            return False, time.time() - start_time, "Timeout"
        except Exception as e:
            return False, time.time() - start_time, str(e)
    
    async def user_simulation(self, user_id: int, endpoint: str, workload_type: WorkloadType,
                            duration: int, think_time: float, results: List[Dict[str, Any]]):
        """Simulate single user behavior"""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration:
                payload = self.generate_workload_payload(workload_type)
                success, response_time, error = await self.send_request(session, endpoint, payload)
                
                results.append({
                    'user_id': user_id,
                    'request_id': request_count,
                    'timestamp': time.time(),
                    'success': success,
                    'response_time': response_time,
                    'error': error
                })
                
                request_count += 1
                
                # Apply think time
                if think_time > 0:
                    await asyncio.sleep(think_time)
    
    def collect_system_metrics(self, duration: int) -> Dict[str, List[float]]:
        """Collect system metrics during test"""
        metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'gpu_utilization': [],
            'gpu_memory': [],
            'network_io': [],
            'disk_io': []
        }
        
        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                # Query Prometheus for metrics
                queries = {
                    'cpu_usage': '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
                    'memory_usage': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
                    'gpu_utilization': 'nvidia_smi_utilization_gpu_ratio * 100',
                    'gpu_memory': 'nvidia_smi_memory_used_bytes / nvidia_smi_memory_total_bytes * 100'
                }
                
                for metric_name, query in queries.items():
                    try:
                        response = requests.get(
                            f"{self.prometheus_url}/api/v1/query",
                            params={'query': query},
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data['data']['result']:
                                value = float(data['data']['result'][0]['value'][1])
                                metrics[metric_name].append(value)
                            else:
                                metrics[metric_name].append(0.0)
                        else:
                            metrics[metric_name].append(0.0)
                    except:
                        metrics[metric_name].append(0.0)
                
                time.sleep(5)  # Collect metrics every 5 seconds
                
            except Exception as e:
                logger.warning(f"Failed to collect metrics: {e}")
                break
        
        return metrics
    
    async def run_load_test(self, config: LoadTestConfig) -> LoadTestResult:
        """Run load test with specified configuration"""
        logger.info(f"Starting load test: {config.name}")
        start_time = datetime.now()
        
        endpoint = self.get_service_endpoint(config.target_service)
        if config.workload == WorkloadType.CONVERSATION:
            endpoint += "/api/conversation"
        elif config.workload == WorkloadType.VISION_INFERENCE:
            endpoint += "/api/vision/analyze"
        elif config.workload == WorkloadType.SPEECH_PROCESSING:
            endpoint += "/api/speech/process"
        elif config.workload == WorkloadType.MEMORY_RETRIEVAL:
            endpoint += "/api/memory/search"
        else:
            endpoint += "/api/process"
        
        # Start metrics collection
        metrics_future = asyncio.get_event_loop().run_in_executor(
            None, self.collect_system_metrics, config.duration
        )
        
        # Track all request results
        all_results: List[Dict[str, Any]] = []
        active_users: List[asyncio.Task] = []
        
        test_start = time.time()
        
        # Main test loop
        while time.time() - test_start < config.duration:
            current_time = time.time() - test_start
            target_users = self.calculate_user_count(
                config.pattern, current_time, config.max_users,
                config.duration, config.ramp_up_time, config.ramp_down_time
            )
            
            # Adjust active user count
            while len(active_users) < target_users:
                user_id = len(active_users)
                remaining_time = config.duration - current_time
                
                user_task = asyncio.create_task(
                    self.user_simulation(
                        user_id, endpoint, config.workload,
                        remaining_time, config.think_time, all_results
                    )
                )
                active_users.append(user_task)
            
            while len(active_users) > target_users:
                if active_users:
                    task = active_users.pop()
                    task.cancel()
            
            # Remove completed tasks
            active_users = [task for task in active_users if not task.done()]
            
            logger.info(f"Time: {current_time:.1f}s, Active users: {len(active_users)}, Target: {target_users}")
            await asyncio.sleep(1)
        
        # Cancel remaining tasks
        for task in active_users:
            task.cancel()
        
        # Wait for metrics collection to complete
        system_metrics = await metrics_future
        
        end_time = datetime.now()
        
        # Analyze results
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r['success'])
        failed_requests = total_requests - successful_requests
        
        if total_requests > 0:
            response_times = [r['response_time'] for r in all_results if r['success']]
            avg_response_time = np.mean(response_times) if response_times else 0
            p95_response_time = np.percentile(response_times, 95) if response_times else 0
            p99_response_time = np.percentile(response_times, 99) if response_times else 0
            error_rate = (failed_requests / total_requests) * 100
            throughput = successful_requests / config.duration
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
            error_rate = 100.0
            throughput = 0
        
        # Check success criteria
        success = True
        if config.success_criteria:
            if 'max_error_rate' in config.success_criteria:
                if error_rate > config.success_criteria['max_error_rate']:
                    success = False
            if 'min_throughput' in config.success_criteria:
                if throughput < config.success_criteria['min_throughput']:
                    success = False
            if 'max_response_time_p95' in config.success_criteria:
                if p95_response_time > config.success_criteria['max_response_time_p95']:
                    success = False
        
        result = LoadTestResult(
            test_name=config.name,
            start_time=start_time,
            end_time=end_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput=throughput,
            error_rate=error_rate,
            gpu_utilization={
                'avg': np.mean(system_metrics['gpu_utilization']) if system_metrics['gpu_utilization'] else 0,
                'max': np.max(system_metrics['gpu_utilization']) if system_metrics['gpu_utilization'] else 0
            },
            memory_usage={
                'avg': np.mean(system_metrics['memory_usage']) if system_metrics['memory_usage'] else 0,
                'max': np.max(system_metrics['memory_usage']) if system_metrics['memory_usage'] else 0
            },
            cpu_usage={
                'avg': np.mean(system_metrics['cpu_usage']) if system_metrics['cpu_usage'] else 0,
                'max': np.max(system_metrics['cpu_usage']) if system_metrics['cpu_usage'] else 0
            },
            success=success,
            details={
                'config': config.__dict__,
                'raw_results': all_results[-100:],  # Keep last 100 for analysis
                'system_metrics': system_metrics
            }
        )
        
        self.test_results.append(result)
        logger.info(f"Load test completed: {config.name}, Success: {success}")
        return result
    
    def generate_report(self, output_file: str = "load_test_report.html"):
        """Generate comprehensive load test report"""
        if not self.test_results:
            logger.warning("No test results to report")
            return
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>AI System Load Test Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test-result { border: 1px solid #ddd; margin: 20px 0; padding: 15px; }
        .success { border-color: #4CAF50; }
        .failure { border-color: #f44336; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>AI System Load Test Report</h1>
    <p>Generated: {timestamp}</p>
    
    <h2>Summary</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Success</th>
            <th>Total Requests</th>
            <th>Error Rate (%)</th>
            <th>Avg Response Time (s)</th>
            <th>P95 Response Time (s)</th>
            <th>Throughput (req/s)</th>
            <th>Max GPU Util (%)</th>
        </tr>
""".format(timestamp=datetime.now().isoformat())
        
        for result in self.test_results:
            status_class = "success" if result.success else "failure"
            html_content += f"""
        <tr class="{status_class}">
            <td>{result.test_name}</td>
            <td>{'✓' if result.success else '✗'}</td>
            <td>{result.total_requests}</td>
            <td>{result.error_rate:.2f}</td>
            <td>{result.avg_response_time:.3f}</td>
            <td>{result.p95_response_time:.3f}</td>
            <td>{result.throughput:.2f}</td>
            <td>{result.gpu_utilization['max']:.1f}</td>
        </tr>
"""
        
        html_content += """
    </table>
    
    <h2>Detailed Results</h2>
"""
        
        for result in self.test_results:
            status_class = "success" if result.success else "failure"
            html_content += f"""
    <div class="test-result {status_class}">
        <h3>{result.test_name}</h3>
        <div class="metric">
            <strong>Duration:</strong> {(result.end_time - result.start_time).total_seconds():.1f}s
        </div>
        <div class="metric">
            <strong>Success Rate:</strong> {((result.successful_requests / result.total_requests) * 100):.2f}%
        </div>
        <div class="metric">
            <strong>Avg CPU:</strong> {result.cpu_usage['avg']:.1f}%
        </div>
        <div class="metric">
            <strong>Avg Memory:</strong> {result.memory_usage['avg']:.1f}%
        </div>
        <div class="metric">
            <strong>Avg GPU:</strong> {result.gpu_utilization['avg']:.1f}%
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Load test report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='AI System Load Testing Suite')
    parser.add_argument('--config', help='Load test configuration file')
    parser.add_argument('--test-name', help='Run specific test by name')
    parser.add_argument('--pattern', choices=[p.value for p in LoadPattern], 
                        default='ramp_up', help='Load pattern')
    parser.add_argument('--workload', choices=[w.value for w in WorkloadType],
                        default='conversation', help='Workload type')
    parser.add_argument('--service', default='coordination', help='Target service')
    parser.add_argument('--max-users', type=int, default=50, help='Maximum concurrent users')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--output', default='load_test_report.html', help='Output report file')
    
    args = parser.parse_args()
    
    runner = LoadTestRunner()
    
    if args.config:
        # Run from configuration file
        try:
            with open(args.config, 'r') as f:
                config_data = yaml.safe_load(f)
            
            async def run_config_tests():
                for test_config in config_data.get('tests', []):
                    config = LoadTestConfig(
                        name=test_config['name'],
                        pattern=LoadPattern(test_config['pattern']),
                        workload=WorkloadType(test_config['workload']),
                        target_service=test_config['service'],
                        max_users=test_config['max_users'],
                        duration=test_config['duration'],
                        ramp_up_time=test_config.get('ramp_up_time', 30),
                        ramp_down_time=test_config.get('ramp_down_time', 30),
                        think_time=test_config.get('think_time', 1.0),
                        parameters=test_config.get('parameters', {}),
                        success_criteria=test_config.get('success_criteria', {})
                    )
                    
                    await runner.run_load_test(config)
                    
                    # Wait between tests
                    wait_time = test_config.get('wait_after', 60)
                    if wait_time > 0:
                        logger.info(f"Waiting {wait_time}s before next test")
                        await asyncio.sleep(wait_time)
            
            asyncio.run(run_config_tests())
            
        except Exception as e:
            logger.error(f"Failed to run config tests: {e}")
            return
    else:
        # Run single test
        config = LoadTestConfig(
            name=f"adhoc_test_{int(time.time())}",
            pattern=LoadPattern(args.pattern),
            workload=WorkloadType(args.workload),
            target_service=args.service,
            max_users=args.max_users,
            duration=args.duration
        )
        
        async def run_single_test():
            await runner.run_load_test(config)
        
        asyncio.run(run_single_test())
    
    # Generate report
    runner.generate_report(args.output)

if __name__ == "__main__":
    main()