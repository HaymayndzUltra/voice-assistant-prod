#!/usr/bin/env python3
"""
SLO Calculator for AI System
Calculates Service Level Objectives and exposes metrics to Prometheus
"""

import os
import time
import yaml
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import prometheus_client
from prometheus_client import Gauge, Counter, Histogram, CollectorRegistry, push_to_gateway
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

@dataclass
class SLOMetric:
    """SLO metric configuration"""
    name: str
    description: str
    query: str
    threshold: float
    window: str
    service: str
    type: str  # 'availability', 'latency', 'error_rate'

class SLOCalculator:
    """Calculate SLO metrics from Prometheus data"""
    
    def __init__(self, prometheus_url: str, config_path: str):
        self.prometheus_url = prometheus_url
        self.config_path = config_path
        self.registry = CollectorRegistry()
        self.slo_configs = self._load_slo_config()
        self._setup_metrics()
        
    def _load_slo_config(self) -> Dict[str, Any]:
        """Load SLO configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load SLO config: {e}")
            return {}
    
    def _setup_metrics(self):
        """Setup Prometheus metrics for SLO tracking"""
        self.slo_compliance_gauge = Gauge(
            'ai_system_slo_compliance',
            'SLO compliance percentage (0-100)',
            ['service', 'slo_type', 'window'],
            registry=self.registry
        )
        
        self.slo_error_budget_gauge = Gauge(
            'ai_system_slo_error_budget_remaining',
            'Error budget remaining percentage',
            ['service', 'slo_type', 'window'],
            registry=self.registry
        )
        
        self.slo_violations_counter = Counter(
            'ai_system_slo_violations_total',
            'Total SLO violations',
            ['service', 'slo_type'],
            registry=self.registry
        )
        
        self.response_time_p99 = Gauge(
            'ai_system_response_time_p99_seconds',
            '99th percentile response time',
            ['service'],
            registry=self.registry
        )
        
        self.availability_gauge = Gauge(
            'ai_system_availability_percentage',
            'Service availability percentage',
            ['service', 'window'],
            registry=self.registry
        )
        
        self.gpu_slo_compliance = Gauge(
            'ai_system_gpu_slo_compliance',
            'GPU utilization SLO compliance',
            ['gpu_type', 'service'],
            registry=self.registry
        )
        
        self.conversation_success_rate = Gauge(
            'ai_system_conversation_success_rate',
            'AI conversation success rate',
            ['service'],
            registry=self.registry
        )
    
    def _query_prometheus(self, query: str, time_range: Optional[str] = None) -> Dict[str, Any]:
        """Query Prometheus for metrics"""
        try:
            if time_range:
                # Range query
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=int(time_range.replace('h', '')))
                
                params = {
                    'query': query,
                    'start': start_time.isoformat() + 'Z',
                    'end': end_time.isoformat() + 'Z',
                    'step': '60s'
                }
                response = requests.get(f"{self.prometheus_url}/api/v1/query_range", params=params)
            else:
                # Instant query
                params = {'query': query}
                response = requests.get(f"{self.prometheus_url}/api/v1/query", params=params)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return {'data': {'result': []}}
    
    def calculate_availability_slo(self, service: str, window: str = '24h') -> float:
        """Calculate availability SLO for a service"""
        # Query for successful requests
        success_query = f'''
            sum(rate(ai_request_count{{service="{service}",status!~"5.."}}[{window}])) /
            sum(rate(ai_request_count{{service="{service}"}}[{window}])) * 100
        '''
        
        result = self._query_prometheus(success_query)
        if result['data']['result']:
            availability = float(result['data']['result'][0]['value'][1])
            self.availability_gauge.labels(service=service, window=window).set(availability)
            return availability
        return 0.0
    
    def calculate_latency_slo(self, service: str, percentile: str = '99') -> float:
        """Calculate latency SLO for a service"""
        latency_query = f'''
            histogram_quantile(0.{percentile}, 
                sum(rate(ai_request_duration_bucket{{service="{service}"}}[5m])) by (le)
            )
        '''
        
        result = self._query_prometheus(latency_query)
        if result['data']['result']:
            latency = float(result['data']['result'][0]['value'][1])
            if percentile == '99':
                self.response_time_p99.labels(service=service).set(latency)
            return latency
        return 0.0
    
    def calculate_error_rate_slo(self, service: str, window: str = '5m') -> float:
        """Calculate error rate SLO for a service"""
        error_query = f'''
            sum(rate(ai_request_count{{service="{service}",status=~"5.."}}[{window}])) /
            sum(rate(ai_request_count{{service="{service}"}}[{window}])) * 100
        '''
        
        result = self._query_prometheus(error_query)
        if result['data']['result']:
            error_rate = float(result['data']['result'][0]['value'][1])
            return error_rate
        return 0.0
    
    def calculate_gpu_utilization_slo(self, gpu_type: str, service: str) -> float:
        """Calculate GPU utilization SLO"""
        gpu_query = f'''
            avg(nvidia_smi_utilization_gpu_ratio{{gpu_type="{gpu_type}"}}) * 100
        '''
        
        result = self._query_prometheus(gpu_query)
        if result['data']['result']:
            utilization = float(result['data']['result'][0]['value'][1])
            
            # Check if within optimal range (60-85% for efficient usage)
            if 60 <= utilization <= 85:
                compliance = 100.0
            elif utilization < 60:
                compliance = max(0, (utilization / 60) * 100)
            else:  # utilization > 85
                compliance = max(0, (100 - utilization) / 15 * 100)
            
            self.gpu_slo_compliance.labels(gpu_type=gpu_type, service=service).set(compliance)
            return compliance
        return 0.0
    
    def calculate_conversation_success_slo(self, service: str) -> float:
        """Calculate AI conversation success rate SLO"""
        success_query = f'''
            sum(rate(ai_conversation_completed_total{{service="{service}"}}[5m])) /
            sum(rate(ai_conversation_started_total{{service="{service}"}}[5m])) * 100
        '''
        
        result = self._query_prometheus(success_query)
        if result['data']['result']:
            success_rate = float(result['data']['result'][0]['value'][1])
            self.conversation_success_rate.labels(service=service).set(success_rate)
            return success_rate
        return 0.0
    
    def calculate_slo_compliance(self, slo_metric: SLOMetric) -> Dict[str, float]:
        """Calculate SLO compliance for a specific metric"""
        if slo_metric.type == 'availability':
            current_value = self.calculate_availability_slo(slo_metric.service, slo_metric.window)
            compliance = min(100.0, (current_value / slo_metric.threshold) * 100)
            
        elif slo_metric.type == 'latency':
            current_value = self.calculate_latency_slo(slo_metric.service)
            # For latency, lower is better, so inverse calculation
            compliance = min(100.0, (slo_metric.threshold / current_value) * 100) if current_value > 0 else 100.0
            
        elif slo_metric.type == 'error_rate':
            current_value = self.calculate_error_rate_slo(slo_metric.service, slo_metric.window)
            # For error rate, lower is better
            compliance = max(0.0, (1 - current_value / slo_metric.threshold) * 100) if slo_metric.threshold > 0 else 100.0
            
        else:
            current_value = 0.0
            compliance = 0.0
        
        # Calculate error budget remaining
        error_budget_consumed = max(0, 100 - compliance)
        error_budget_remaining = max(0, 100 - error_budget_consumed)
        
        # Record metrics
        self.slo_compliance_gauge.labels(
            service=slo_metric.service,
            slo_type=slo_metric.type,
            window=slo_metric.window
        ).set(compliance)
        
        self.slo_error_budget_gauge.labels(
            service=slo_metric.service,
            slo_type=slo_metric.type,
            window=slo_metric.window
        ).set(error_budget_remaining)
        
        # Record violation if SLO is breached
        if compliance < 95.0:  # Alert threshold
            self.slo_violations_counter.labels(
                service=slo_metric.service,
                slo_type=slo_metric.type
            ).inc()
        
        return {
            'current_value': current_value,
            'compliance': compliance,
            'error_budget_remaining': error_budget_remaining,
            'threshold': slo_metric.threshold
        }
    
    def calculate_all_slos(self):
        """Calculate all configured SLOs"""
        logger.info("Starting SLO calculations...")
        
        slo_results = {}
        
        # Process configured SLOs
        for slo_name, slo_config in self.slo_configs.get('slos', {}).items():
            try:
                slo_metric = SLOMetric(
                    name=slo_name,
                    description=slo_config.get('description', ''),
                    query=slo_config.get('query', ''),
                    threshold=slo_config.get('threshold', 95.0),
                    window=slo_config.get('window', '5m'),
                    service=slo_config.get('service', 'unknown'),
                    type=slo_config.get('type', 'availability')
                )
                
                result = self.calculate_slo_compliance(slo_metric)
                slo_results[slo_name] = result
                
                logger.info(f"SLO {slo_name}: {result['compliance']:.2f}% compliance")
                
            except Exception as e:
                logger.error(f"Failed to calculate SLO {slo_name}: {e}")
        
        # Calculate additional service-specific SLOs
        services = ['coordination', 'memory-stack', 'vision-gpu', 'speech-gpu', 'language-stack']
        
        for service in services:
            try:
                # GPU utilization for GPU services
                if 'gpu' in service:
                    gpu_type = 'rtx-4090' if service in ['vision-gpu', 'speech-gpu'] else 'rtx-3060'
                    self.calculate_gpu_utilization_slo(gpu_type, service)
                
                # Conversation success rate for interactive services
                if service in ['coordination', 'language-stack']:
                    self.calculate_conversation_success_slo(service)
                    
            except Exception as e:
                logger.error(f"Failed to calculate additional SLOs for {service}: {e}")
        
        return slo_results
    
    def export_metrics(self):
        """Export metrics to Prometheus gateway or file"""
        try:
            # Try to push to Prometheus pushgateway if available
            pushgateway_url = os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'http://localhost:9091')
            
            try:
                push_to_gateway(
                    pushgateway_url,
                    job='slo-calculator',
                    registry=self.registry,
                    timeout=10
                )
                logger.info("Metrics pushed to Prometheus pushgateway")
            except Exception as e:
                logger.warning(f"Failed to push to pushgateway: {e}")
                
                # Fallback: write metrics to file
                metrics_file = '/tmp/slo_metrics.prom'
                with open(metrics_file, 'w') as f:
                    for family in self.registry.collect():
                        for sample in family.samples:
                            f.write(f"{sample.name} {sample.value}\n")
                logger.info(f"Metrics written to {metrics_file}")
                
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

def main():
    """Main execution function"""
    prometheus_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
    slo_config_path = os.getenv('SLO_CONFIG_PATH', '/config/slo-config.yaml')
    
    logger.info(f"Starting SLO Calculator - Prometheus: {prometheus_url}")
    
    try:
        calculator = SLOCalculator(prometheus_url, slo_config_path)
        
        # Calculate SLOs
        results = calculator.calculate_all_slos()
        
        # Export metrics
        calculator.export_metrics()
        
        # Log summary
        total_slos = len(results)
        compliant_slos = sum(1 for r in results.values() if r['compliance'] >= 95.0)
        
        logger.info(f"SLO Summary: {compliant_slos}/{total_slos} SLOs meeting target (≥95%)")
        
        # Alert on critical SLO violations
        critical_violations = [
            name for name, result in results.items() 
            if result['compliance'] < 90.0
        ]
        
        if critical_violations:
            logger.warning(f"Critical SLO violations: {critical_violations}")
        
    except Exception as e:
        logger.error(f"SLO calculation failed: {e}")
        raise

if __name__ == "__main__":
    main()