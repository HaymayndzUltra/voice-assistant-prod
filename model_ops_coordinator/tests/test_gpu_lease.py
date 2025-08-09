"""
Unit tests for GPU Lease API implementation.

Tests the core GPU lease functionality including:
- Lease acquisition and release
- TTL expiration
- VRAM capacity management
- Priority handling
- Concurrent lease operations
"""

import asyncio
import time
import threading
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from concurrent import futures

import grpc
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import after modifying path
from transport.grpc_server import ModelOpsGRPCServicer, GRPCServer
from core.kernel import Kernel
from core.schemas import Config, Resources
import model_ops_pb2 as pb2


class TestGPULeaseAPI(unittest.TestCase):
    """Test suite for GPU Lease API functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock config
        self.config = Mock(spec=Config)
        self.config.resources = Mock(spec=Resources)
        self.config.resources.vram_soft_limit_mb = 24000  # 24GB VRAM
        
        # Create mock kernel
        self.kernel = Mock(spec=Kernel)
        self.kernel.cfg = self.config
        self.kernel.telemetry = Mock()
        self.kernel.gpu_manager = Mock()
        
        # Create servicer instance
        self.servicer = ModelOpsGRPCServicer(self.kernel)
        
        # Create mock context
        self.context = Mock()
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop the lease sweeper thread
        if hasattr(self.servicer, '_lease_sweeper_stop'):
            self.servicer._lease_sweeper_stop.set()
            if hasattr(self.servicer, '_lease_sweeper'):
                self.servicer._lease_sweeper.join(timeout=1)
    
    def test_lease_acquisition_success(self):
        """Test successful GPU lease acquisition."""
        # Create lease request
        request = pb2.GpuLeaseRequest(
            client="test_client",
            model_name="llama-7b",
            vram_estimate_mb=8000,  # 8GB
            priority=1,
            ttl_seconds=30
        )
        
        # Acquire lease
        response = self.servicer.AcquireGpuLease(request, self.context)
        
        # Verify response
        self.assertTrue(response.granted)
        self.assertIsNotNone(response.lease_id)
        self.assertEqual(response.vram_reserved_mb, 8000)
        
        # Verify internal state
        self.assertEqual(self.servicer._used_mb, 8000)
        self.assertIn(response.lease_id, self.servicer._leases)
        
    def test_lease_acquisition_insufficient_vram(self):
        """Test lease denial when insufficient VRAM available."""
        # Create large lease request
        request = pb2.GpuLeaseRequest(
            client="test_client",
            model_name="llama-70b",
            vram_estimate_mb=30000,  # 30GB (exceeds capacity)
            priority=1,
            ttl_seconds=30
        )
        
        # Attempt to acquire lease
        response = self.servicer.AcquireGpuLease(request, self.context)
        
        # Verify denial
        self.assertFalse(response.granted)
        self.assertEqual(response.reason, "Insufficient VRAM")
        self.assertEqual(response.retry_after_ms, 250)
        
        # Verify no allocation was made
        self.assertEqual(self.servicer._used_mb, 0)
        self.assertEqual(len(self.servicer._leases), 0)
    
    def test_lease_release(self):
        """Test GPU lease release."""
        # First acquire a lease
        request = pb2.GpuLeaseRequest(
            client="test_client",
            model_name="bert-base",
            vram_estimate_mb=2000,
            priority=2,
            ttl_seconds=60
        )
        
        acquire_response = self.servicer.AcquireGpuLease(request, self.context)
        self.assertTrue(acquire_response.granted)
        lease_id = acquire_response.lease_id
        
        # Release the lease
        release_request = pb2.GpuLeaseRelease(lease_id=lease_id)
        release_response = self.servicer.ReleaseGpuLease(release_request, self.context)
        
        # Verify release
        self.assertTrue(release_response.success)
        self.assertEqual(self.servicer._used_mb, 0)
        self.assertNotIn(lease_id, self.servicer._leases)
    
    def test_lease_ttl_expiration(self):
        """Test automatic lease expiration after TTL."""
        # Acquire lease with short TTL
        request = pb2.GpuLeaseRequest(
            client="test_client",
            model_name="gpt2",
            vram_estimate_mb=1500,
            priority=2,
            ttl_seconds=1  # 1 second TTL
        )
        
        response = self.servicer.AcquireGpuLease(request, self.context)
        self.assertTrue(response.granted)
        lease_id = response.lease_id
        
        # Verify lease exists
        self.assertIn(lease_id, self.servicer._leases)
        self.assertEqual(self.servicer._used_mb, 1500)
        
        # Wait for TTL to expire
        time.sleep(1.5)
        
        # Trigger reaping (normally done by sweeper thread)
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        with self.servicer._lease_lock:
            self.servicer._reap_locked(now_ms)
        
        # Verify lease was expired
        self.assertNotIn(lease_id, self.servicer._leases)
        self.assertEqual(self.servicer._used_mb, 0)
    
    def test_multiple_lease_management(self):
        """Test managing multiple concurrent leases."""
        leases = []
        
        # Acquire multiple leases
        models = [
            ("bert-base", 2000),
            ("gpt2", 1500),
            ("resnet50", 3000),
            ("whisper-small", 2500)
        ]
        
        total_vram = 0
        for model_name, vram_mb in models:
            request = pb2.GpuLeaseRequest(
                client=f"client_{model_name}",
                model_name=model_name,
                vram_estimate_mb=vram_mb,
                priority=2,
                ttl_seconds=60
            )
            
            response = self.servicer.AcquireGpuLease(request, self.context)
            self.assertTrue(response.granted)
            leases.append(response.lease_id)
            total_vram += vram_mb
        
        # Verify total allocation
        self.assertEqual(self.servicer._used_mb, total_vram)
        self.assertEqual(len(self.servicer._leases), len(models))
        
        # Release some leases
        for lease_id in leases[:2]:
            release_request = pb2.GpuLeaseRelease(lease_id=lease_id)
            self.servicer.ReleaseGpuLease(release_request, self.context)
        
        # Verify partial release
        remaining_vram = sum(vram for _, vram in models[2:])
        self.assertEqual(self.servicer._used_mb, remaining_vram)
        self.assertEqual(len(self.servicer._leases), 2)
    
    def test_lease_priority_metadata(self):
        """Test that priority is stored in lease metadata."""
        # Acquire high-priority lease
        request = pb2.GpuLeaseRequest(
            client="high_priority_client",
            model_name="critical_model",
            vram_estimate_mb=5000,
            priority=1,  # Highest priority
            ttl_seconds=120
        )
        
        response = self.servicer.AcquireGpuLease(request, self.context)
        self.assertTrue(response.granted)
        
        # Check lease metadata
        lease_meta = self.servicer._leases[response.lease_id]
        self.assertEqual(lease_meta['priority'], 1)
        self.assertEqual(lease_meta['client'], "high_priority_client")
        self.assertEqual(lease_meta['model'], "critical_model")
        self.assertEqual(lease_meta['mb'], 5000)
    
    def test_concurrent_lease_operations(self):
        """Test thread-safe concurrent lease operations."""
        num_threads = 10
        barrier = threading.Barrier(num_threads)
        results = []
        
        def acquire_and_release():
            # Synchronize thread start
            barrier.wait()
            
            # Acquire lease
            request = pb2.GpuLeaseRequest(
                client=f"thread_{threading.current_thread().ident}",
                model_name="concurrent_model",
                vram_estimate_mb=1000,
                priority=2,
                ttl_seconds=10
            )
            
            response = self.servicer.AcquireGpuLease(request, self.context)
            results.append(response.granted)
            
            if response.granted:
                # Hold briefly
                time.sleep(0.1)
                
                # Release
                release_request = pb2.GpuLeaseRelease(lease_id=response.lease_id)
                self.servicer.ReleaseGpuLease(release_request, self.context)
        
        # Start threads
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=acquire_and_release)
            t.start()
            threads.append(t)
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify results
        # With 21600MB capacity (90% of 24000) and 1000MB per lease,
        # we should be able to grant 21 leases
        granted_count = sum(1 for r in results if r)
        self.assertLessEqual(granted_count, 21)
        
        # Verify all leases were released
        self.assertEqual(self.servicer._used_mb, 0)
    
    def test_lease_with_zero_vram(self):
        """Test lease request with zero VRAM estimate."""
        request = pb2.GpuLeaseRequest(
            client="zero_client",
            model_name="tiny_model",
            vram_estimate_mb=0,
            priority=3,
            ttl_seconds=30
        )
        
        response = self.servicer.AcquireGpuLease(request, self.context)
        
        # Should grant with 0 VRAM
        self.assertTrue(response.granted)
        self.assertEqual(response.vram_reserved_mb, 0)
        self.assertEqual(self.servicer._used_mb, 0)
    
    def test_lease_capacity_calculation(self):
        """Test that lease capacity is 90% of configured soft limit."""
        # Capacity should be 90% of 24000MB = 21600MB
        expected_capacity = int(24000 * 0.9)
        self.assertEqual(self.servicer._capacity_mb, expected_capacity)
        
        # Try to allocate exactly the capacity
        request = pb2.GpuLeaseRequest(
            client="capacity_test",
            model_name="max_model",
            vram_estimate_mb=expected_capacity,
            priority=1,
            ttl_seconds=30
        )
        
        response = self.servicer.AcquireGpuLease(request, self.context)
        self.assertTrue(response.granted)
        
        # Try to allocate 1MB more - should fail
        request2 = pb2.GpuLeaseRequest(
            client="overflow_test",
            model_name="tiny",
            vram_estimate_mb=1,
            priority=1,
            ttl_seconds=30
        )
        
        response2 = self.servicer.AcquireGpuLease(request2, self.context)
        self.assertFalse(response2.granted)
    
    def test_lease_error_handling(self):
        """Test error handling in lease operations."""
        # Test with malformed request (negative VRAM)
        request = pb2.GpuLeaseRequest(
            client="error_client",
            model_name="error_model",
            vram_estimate_mb=-1000,  # Negative VRAM
            priority=2,
            ttl_seconds=30
        )
        
        response = self.servicer.AcquireGpuLease(request, self.context)
        
        # Should handle gracefully and treat as 0
        self.assertTrue(response.granted)
        self.assertEqual(response.vram_reserved_mb, 0)
        
        # Test release with non-existent lease ID
        release_request = pb2.GpuLeaseRelease(lease_id="non_existent_lease")
        release_response = self.servicer.ReleaseGpuLease(release_request, self.context)
        
        # Should still return success (idempotent)
        self.assertTrue(release_response.success)
    
    def test_lease_metadata_timestamps(self):
        """Test that lease metadata includes proper timestamps."""
        request = pb2.GpuLeaseRequest(
            client="timestamp_test",
            model_name="test_model",
            vram_estimate_mb=1000,
            priority=2,
            ttl_seconds=60
        )
        
        before_ms = int(datetime.utcnow().timestamp() * 1000)
        response = self.servicer.AcquireGpuLease(request, self.context)
        after_ms = int(datetime.utcnow().timestamp() * 1000)
        
        self.assertTrue(response.granted)
        
        # Check lease metadata
        lease_meta = self.servicer._leases[response.lease_id]
        self.assertIn('created_ms', lease_meta)
        self.assertIn('expires_ms', lease_meta)
        
        # Verify timestamps are reasonable
        self.assertGreaterEqual(lease_meta['created_ms'], before_ms)
        self.assertLessEqual(lease_meta['created_ms'], after_ms)
        self.assertEqual(
            lease_meta['expires_ms'],
            lease_meta['created_ms'] + (60 * 1000)
        )
    
    def test_default_ttl_handling(self):
        """Test default TTL when not specified."""
        request = pb2.GpuLeaseRequest(
            client="default_ttl_test",
            model_name="test_model",
            vram_estimate_mb=1000,
            priority=2
            # ttl_seconds not specified
        )
        
        response = self.servicer.AcquireGpuLease(request, self.context)
        self.assertTrue(response.granted)
        
        # Check that default TTL of 30 seconds was applied
        lease_meta = self.servicer._leases[response.lease_id]
        expected_expires = lease_meta['created_ms'] + (30 * 1000)
        self.assertEqual(lease_meta['expires_ms'], expected_expires)


class TestGPULeaseIntegration(unittest.TestCase):
    """Integration tests for GPU Lease with full server."""
    
    @patch('transport.grpc_server.grpc.aio.server')
    def test_grpc_server_initialization(self, mock_grpc_server):
        """Test that gRPC server properly initializes with GPU Lease support."""
        # Create mock kernel
        kernel = Mock(spec=Kernel)
        kernel.cfg = Mock()
        kernel.cfg.resources = Mock()
        kernel.cfg.resources.vram_soft_limit_mb = 24000
        kernel.cfg.server = Mock()
        kernel.cfg.server.grpc_port = 50051
        kernel.cfg.server.max_workers = 10
        
        # Create server instance
        server = GRPCServer(kernel, port=50051, max_workers=10)
        
        # Verify servicer was created
        self.assertIsNotNone(server.servicer)
        self.assertIsInstance(server.servicer, ModelOpsGRPCServicer)
        
        # Verify GPU lease methods exist
        self.assertTrue(hasattr(server.servicer, 'AcquireGpuLease'))
        self.assertTrue(hasattr(server.servicer, 'ReleaseGpuLease'))


if __name__ == "__main__":
    unittest.main()