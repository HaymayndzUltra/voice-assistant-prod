#!/usr/bin/env python3
"""
CI Test for Phase 1 - Foundation Consolidation
Validates that the unified configuration meets all requirements
"""

import unittest
import sys
import os
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validate_config import (
    load_config, extract_agents, check_circular_dependencies,
    check_missing_scripts, check_port_conflicts, check_missing_dependencies
)

class TestPhase1Foundation(unittest.TestCase):
    """Test suite for Phase 1 foundation requirements"""
    
    @classmethod
    def setUpClass(cls):
        """Load configuration once for all tests"""
        cls.config_path = Path("config/unified_startup.yaml")
        if not cls.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {cls.config_path}")
            
        cls.config = load_config(str(cls.config_path))
        cls.agents = extract_agents(cls.config)
        
    def test_configuration_exists(self):
        """Test that unified configuration file exists"""
        self.assertTrue(self.config_path.exists(), "Unified configuration file must exist")
        
    def test_essential_agents_count(self):
        """Test that we have exactly 23 essential agents"""
        self.assertEqual(len(self.agents), 23, "Must have exactly 23 essential agents")
        
    def test_required_agents_present(self):
        """Test that all required essential agents are present"""
        required_mainpc = {
            # Infrastructure
            'ServiceRegistry', 'SystemDigitalTwin', 'ObservabilityHub',
            # Coordination
            'RequestCoordinator', 'ModelManagerSuite', 'VRAMOptimizerAgent',
            # Memory
            'MemoryClient', 'SessionMemoryAgent', 'KnowledgeBase',
            # Speech I/O
            'AudioCapture', 'FusedAudioPreprocessor', 'StreamingSpeechRecognition',
            'StreamingTTSAgent', 'STTService', 'TTSService'
        }
        
        required_pc2 = {
            'ObservabilityHub_PC2', 'MemoryOrchestratorService', 'ResourceManager',
            'AsyncProcessor', 'ContextManager', 'UnifiedMemoryReasoningAgent',
            'TieredResponder', 'TaskScheduler'
        }
        
        all_required = required_mainpc | required_pc2
        present_agents = set(self.agents.keys())
        
        missing = all_required - present_agents
        self.assertEqual(len(missing), 0, f"Missing required agents: {missing}")
        
    def test_all_agents_required(self):
        """Test that all agents are marked as required=true"""
        optional_agents = []
        for name, config in self.agents.items():
            if not config.get('required', True):
                optional_agents.append(name)
                
        self.assertEqual(len(optional_agents), 0, 
                        f"All Phase 1 agents must be required=true, found optional: {optional_agents}")
        
    def test_no_circular_dependencies(self):
        """Test that there are no circular dependencies"""
        cycles = check_circular_dependencies(self.agents)
        self.assertEqual(len(cycles), 0, f"Circular dependencies detected: {cycles}")
        
    def test_no_missing_scripts(self):
        """Test that all script paths exist"""
        missing = check_missing_scripts(self.agents)
        self.assertEqual(len(missing), 0, 
                        f"Missing scripts: {[f'{name}: {path}' for name, path in missing]}")
        
    def test_no_port_conflicts(self):
        """Test that there are no port conflicts"""
        conflicts = check_port_conflicts(self.agents)
        self.assertEqual(len(conflicts), 0, f"Port conflicts detected: {conflicts}")
        
    def test_no_missing_dependencies(self):
        """Test that all dependencies exist"""
        missing = check_missing_dependencies(self.agents)
        self.assertEqual(len(missing), 0,
                        f"Missing dependencies: {[f'{agent} needs {dep}' for agent, dep in missing]}")
        
    def test_observability_hub_first(self):
        """Test that ObservabilityHub has no dependencies (starts first)"""
        obs_hub = self.agents.get('ObservabilityHub', {})
        deps = obs_hub.get('dependencies', [])
        self.assertEqual(len(deps), 1, "ObservabilityHub should only depend on ServiceRegistry")
        self.assertEqual(deps[0], 'ServiceRegistry', "ObservabilityHub should depend on ServiceRegistry")
        
    def test_port_ranges(self):
        """Test that ports follow the allocation strategy"""
        mainpc_agents = {
            'MemoryClient', 'SessionMemoryAgent', 'KnowledgeBase',
            'VRAMOptimizerAgent', 'AudioCapture', 'FusedAudioPreprocessor',
            'StreamingSpeechRecognition', 'StreamingTTSAgent', 'STTService', 'TTSService'
        }
        
        pc2_agents = {
            'MemoryOrchestratorService', 'TieredResponder', 'AsyncProcessor',
            'ContextManager', 'UnifiedMemoryReasoningAgent', 'ResourceManager',
            'TaskScheduler'
        }
        
        unified_agents = {
            'ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator',
            'ModelManagerSuite'
        }
        
        monitoring_agents = {'ObservabilityHub', 'ObservabilityHub_PC2'}
        
        for name, config in self.agents.items():
            port = int(str(config.get('port', '0')).replace('${PORT_OFFSET}+', ''))
            
            if name in mainpc_agents:
                self.assertTrue(5500 <= port <= 5999 or 6500 <= port <= 6999,
                              f"{name} port {port} not in MainPC range")
            elif name in pc2_agents:
                self.assertTrue(7100 <= port <= 7199,
                              f"{name} port {port} not in PC2 range")
            elif name in unified_agents:
                self.assertTrue(7200 <= port <= 7299,
                              f"{name} port {port} not in Unified range")
            elif name in monitoring_agents:
                self.assertTrue(9000 <= port <= 9199,
                              f"{name} port {port} not in Monitoring range")
                              
    def test_global_settings(self):
        """Test that global settings are properly configured"""
        self.assertIn('global_settings', self.config)
        settings = self.config['global_settings']
        
        # Check environment variables
        self.assertIn('environment', settings)
        env = settings['environment']
        self.assertIn('PYTHONPATH', env)
        self.assertIn('UNIFIED_HOST', env)
        self.assertIn('OBS_HUB_ENDPOINT', env)
        
        # Check resource limits (should use higher values)
        self.assertIn('resource_limits', settings)
        limits = settings['resource_limits']
        self.assertEqual(limits['memory_mb'], 4096, "Should use PC2's higher memory limit")
        self.assertEqual(limits['max_threads'], 8, "Should use PC2's higher thread limit")
        
    def test_deprecated_monitors_removed(self):
        """Test that deprecated monitoring agents are not present"""
        deprecated = {
            'PerformanceMonitor', 'HealthMonitor', 'SystemHealthManager',
            'PerformanceLoggerAgent'
        }
        
        present_deprecated = deprecated & set(self.agents.keys())
        self.assertEqual(len(present_deprecated), 0,
                        f"Deprecated monitors still present: {present_deprecated}")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)