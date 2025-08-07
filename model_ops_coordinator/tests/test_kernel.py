"""Unit tests for Kernel module."""

import pytest
import asyncio
import threading
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.kernel import Kernel
from core.schemas import Config, ServerConfig, ResourceConfig, ModelConfig, LearningConfig, GoalConfig, ResilienceConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        server=ServerConfig(zmq_port=7211, grpc_port=7212, rest_port=8008, max_workers=4),
        resources=ResourceConfig(gpu_poll_interval=5, vram_soft_limit_mb=1000, eviction_threshold_pct=90),
        models=ModelConfig(preload=[], default_dtype="float16", quantization=True),
        learning=LearningConfig(enable_auto_tune=False, max_parallel_jobs=1, job_store="test.db"),
        goals=GoalConfig(policy="priority_queue", max_active_goals=5),
        resilience=ResilienceConfig(circuit_breaker={}, bulkhead={})
    )


@pytest.fixture
def kernel_with_mocks(mock_config):
    """Create a Kernel instance with mocked dependencies."""
    with patch('core.kernel.Telemetry') as mock_telemetry, \
         patch('core.kernel.GPUManager') as mock_gpu_manager, \
         patch('core.kernel.LifecycleModule') as mock_lifecycle, \
         patch('core.kernel.InferenceModule') as mock_inference, \
         patch('core.kernel.LearningModule') as mock_learning, \
         patch('core.kernel.GoalManager') as mock_goals:
        
        kernel = Kernel(mock_config)
        
        # Set up return values for mocked methods
        kernel.telemetry.get_metrics.return_value = {}
        kernel.gpu_manager.get_stats.return_value = {"total_vram_mb": 1000, "used_vram_mb": 500}
        kernel.lifecycle.get_status.return_value = {"loaded_models": []}
        
        return kernel


class TestKernel:
    """Test cases for the Kernel class."""
    
    def test_kernel_initialization(self, mock_config):
        """Test that Kernel initializes all components correctly."""
        with patch('core.kernel.Telemetry') as mock_telemetry, \
             patch('core.kernel.GPUManager') as mock_gpu_manager, \
             patch('core.kernel.LifecycleModule') as mock_lifecycle, \
             patch('core.kernel.InferenceModule') as mock_inference, \
             patch('core.kernel.LearningModule') as mock_learning, \
             patch('core.kernel.GoalManager') as mock_goals:
            
            kernel = Kernel(mock_config)
            
            # Verify all components are initialized
            assert kernel.cfg == mock_config
            assert isinstance(kernel.executor, ThreadPoolExecutor)
            assert kernel.executor._max_workers == 4
            assert kernel.telemetry is not None
            assert kernel.gpu_manager is not None
            assert kernel.lifecycle is not None
            assert kernel.inference is not None
            assert kernel.learning is not None
            assert kernel.goals is not None
            
            # Verify components are initialized with correct dependencies
            mock_gpu_manager.assert_called_once_with(mock_config, kernel.telemetry)
            mock_lifecycle.assert_called_once_with(mock_config, kernel.gpu_manager, kernel.telemetry)
            mock_inference.assert_called_once_with(mock_config, kernel.lifecycle, kernel.telemetry)
            mock_learning.assert_called_once_with(mock_config, kernel.lifecycle, kernel.telemetry)
            mock_goals.assert_called_once_with(mock_config, kernel.learning, kernel.telemetry)

    @pytest.mark.asyncio
    async def test_kernel_start_stop(self, kernel_with_mocks):
        """Test kernel start and stop lifecycle."""
        kernel = kernel_with_mocks
        
        # Mock the start methods
        kernel.gpu_manager.start = Mock()
        kernel.lifecycle.start = Mock()
        kernel.learning.start = Mock()
        kernel.goals.start = Mock()
        
        # Mock the stop methods
        kernel.gpu_manager.stop = Mock()
        kernel.lifecycle.stop = Mock()
        kernel.learning.stop = Mock()
        kernel.goals.stop = Mock()
        
        # Test start
        await kernel.start()
        
        kernel.gpu_manager.start.assert_called_once()
        kernel.lifecycle.start.assert_called_once()
        kernel.learning.start.assert_called_once()
        kernel.goals.start.assert_called_once()
        
        assert kernel.is_running
        
        # Test stop
        await kernel.stop()
        
        kernel.gpu_manager.stop.assert_called_once()
        kernel.lifecycle.stop.assert_called_once()
        kernel.learning.stop.assert_called_once()
        kernel.goals.stop.assert_called_once()
        
        assert not kernel.is_running

    def test_health_check(self, kernel_with_mocks):
        """Test kernel health check functionality."""
        kernel = kernel_with_mocks
        kernel._running = True
        
        health = kernel.health_check()
        
        assert health["status"] == "healthy"
        assert health["components"]["kernel"] == "running"
        assert "gpu_manager" in health["components"]
        assert "lifecycle" in health["components"]
        assert "inference" in health["components"]
        assert "learning" in health["components"]
        assert "goals" in health["components"]

    def test_get_status(self, kernel_with_mocks):
        """Test kernel status reporting."""
        kernel = kernel_with_mocks
        kernel._running = True
        
        status = kernel.get_status()
        
        assert status["running"] == True
        assert "thread_pool" in status
        assert "components" in status
        assert "gpu_manager" in status["components"]
        assert "lifecycle" in status["components"]

    @pytest.mark.asyncio
    async def test_shutdown_graceful(self, kernel_with_mocks):
        """Test graceful shutdown functionality."""
        kernel = kernel_with_mocks
        kernel._running = True
        
        # Mock the shutdown methods
        kernel.gpu_manager.stop = Mock()
        kernel.lifecycle.stop = Mock()
        kernel.learning.stop = Mock()
        kernel.goals.stop = Mock()
        
        await kernel.shutdown()
        
        # Verify all components are stopped
        kernel.gpu_manager.stop.assert_called_once()
        kernel.lifecycle.stop.assert_called_once()
        kernel.learning.stop.assert_called_once()
        kernel.goals.stop.assert_called_once()
        
        # Verify executor is shutdown
        assert kernel.executor._shutdown
        assert not kernel.is_running

    def test_thread_pool_execution(self, kernel_with_mocks):
        """Test that kernel can execute tasks in thread pool."""
        kernel = kernel_with_mocks
        
        def test_task():
            return "task_result"
        
        future = kernel.executor.submit(test_task)
        result = future.result(timeout=5)
        
        assert result == "task_result"

    def test_kernel_context_manager(self, mock_config):
        """Test kernel as context manager."""
        with patch('core.kernel.Telemetry'), \
             patch('core.kernel.GPUManager'), \
             patch('core.kernel.LifecycleModule'), \
             patch('core.kernel.InferenceModule'), \
             patch('core.kernel.LearningModule'), \
             patch('core.kernel.GoalManager'):
            
            with Kernel(mock_config) as kernel:
                assert kernel.is_running
            
            assert not kernel.is_running

if __name__ == "__main__":
    pytest.main([__file__])