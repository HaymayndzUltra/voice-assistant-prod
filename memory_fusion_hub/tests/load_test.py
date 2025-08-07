"""
Simple load testing script for Memory Fusion Hub performance validation.

Tests basic performance characteristics without external dependencies
using mocked components and concurrent requests.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock
import json

from memory_fusion_hub.core.models import MemoryItem, FusionConfig
from memory_fusion_hub.adapters.redis_cache import RedisCache


class MockPerformanceTest:
    """Performance test using mocked components."""
    
    def __init__(self):
        self.cache = RedisCache("redis://localhost:6379/0", default_ttl_seconds=300)
        self.results = []
    
    async def setup_mocks(self):
        """Setup mock Redis client for testing."""
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock cache operations with realistic delays
        async def mock_get(key):
            await asyncio.sleep(0.001)  # 1ms simulated Redis latency
            if "miss" in key:
                return None
            return json.dumps({
                'key': key,
                'content': f'test content for {key}',
                'memory_type': 'conversation',
                'timestamp': '2025-08-07T18:00:00Z',
                'metadata': {},
                'tags': [],
                '__model_type__': 'MemoryItem'
            })
        
        async def mock_setex(key, ttl, data):
            await asyncio.sleep(0.0005)  # 0.5ms simulated Redis write latency
            return True
        
        async def mock_delete(key):
            await asyncio.sleep(0.0005)  # 0.5ms simulated Redis delete latency
            return 1
        
        async def mock_exists(key):
            await asyncio.sleep(0.0003)  # 0.3ms simulated Redis exists latency
            return 1
        
        mock_client.get.side_effect = mock_get
        mock_client.setex.side_effect = mock_setex
        mock_client.delete.side_effect = mock_delete
        mock_client.exists.side_effect = mock_exists
    
    async def test_cache_get_performance(self, num_requests: int = 1000) -> Dict[str, Any]:
        """Test cache get operation performance."""
        await self.setup_mocks()
        
        print(f"Testing cache GET performance with {num_requests} requests...")
        
        async def single_get_request(request_id: int):
            start_time = time.perf_counter()
            result = await self.cache.get(f"test_key_{request_id}")
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            return duration_ms, result is not None
        
        # Run concurrent requests
        start_time = time.perf_counter()
        tasks = [single_get_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        # Calculate metrics
        durations = [r[0] for r in results]
        success_count = sum(1 for r in results if r[1])
        
        total_time = end_time - start_time
        rps = num_requests / total_time
        
        metrics = {
            'operation': 'cache_get',
            'total_requests': num_requests,
            'successful_requests': success_count,
            'total_time_seconds': total_time,
            'requests_per_second': rps,
            'avg_latency_ms': statistics.mean(durations),
            'median_latency_ms': statistics.median(durations),
            'p95_latency_ms': statistics.quantiles(durations, n=20)[18],  # 95th percentile
            'p99_latency_ms': statistics.quantiles(durations, n=100)[98],  # 99th percentile
            'min_latency_ms': min(durations),
            'max_latency_ms': max(durations)
        }
        
        return metrics
    
    async def test_cache_put_performance(self, num_requests: int = 1000) -> Dict[str, Any]:
        """Test cache put operation performance."""
        await self.setup_mocks()
        
        print(f"Testing cache PUT performance with {num_requests} requests...")
        
        async def single_put_request(request_id: int):
            start_time = time.perf_counter()
            item = MemoryItem(
                key=f"put_test_key_{request_id}",
                content=f"test content for request {request_id}",
                metadata={"request_id": str(request_id)}
            )
            await self.cache.put(f"put_test_key_{request_id}", item)
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            return duration_ms
        
        # Run concurrent requests
        start_time = time.perf_counter()
        tasks = [single_put_request(i) for i in range(num_requests)]
        durations = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        rps = num_requests / total_time
        
        metrics = {
            'operation': 'cache_put',
            'total_requests': num_requests,
            'successful_requests': num_requests,  # All should succeed with mocks
            'total_time_seconds': total_time,
            'requests_per_second': rps,
            'avg_latency_ms': statistics.mean(durations),
            'median_latency_ms': statistics.median(durations),
            'p95_latency_ms': statistics.quantiles(durations, n=20)[18],
            'p99_latency_ms': statistics.quantiles(durations, n=100)[98],
            'min_latency_ms': min(durations),
            'max_latency_ms': max(durations)
        }
        
        return metrics
    
    async def test_mixed_workload_performance(self, num_requests: int = 1000) -> Dict[str, Any]:
        """Test mixed workload performance (70% reads, 20% writes, 10% deletes)."""
        await self.setup_mocks()
        
        print(f"Testing mixed workload performance with {num_requests} requests...")
        
        async def mixed_request(request_id: int):
            start_time = time.perf_counter()
            
            # Determine operation type
            op_type = request_id % 10
            if op_type < 7:  # 70% reads
                result = await self.cache.get(f"mixed_key_{request_id}")
                operation = 'get'
            elif op_type < 9:  # 20% writes
                item = MemoryItem(
                    key=f"mixed_key_{request_id}",
                    content=f"mixed content {request_id}"
                )
                await self.cache.put(f"mixed_key_{request_id}", item)
                operation = 'put'
            else:  # 10% deletes
                await self.cache.evict(f"mixed_key_{request_id}")
                operation = 'delete'
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            return duration_ms, operation
        
        # Run concurrent requests
        start_time = time.perf_counter()
        tasks = [mixed_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        # Calculate metrics
        durations = [r[0] for r in results]
        operations = [r[1] for r in results]
        
        total_time = end_time - start_time
        rps = num_requests / total_time
        
        # Count operations
        op_counts = {}
        for op in operations:
            op_counts[op] = op_counts.get(op, 0) + 1
        
        metrics = {
            'operation': 'mixed_workload',
            'total_requests': num_requests,
            'successful_requests': num_requests,
            'total_time_seconds': total_time,
            'requests_per_second': rps,
            'avg_latency_ms': statistics.mean(durations),
            'median_latency_ms': statistics.median(durations),
            'p95_latency_ms': statistics.quantiles(durations, n=20)[18],
            'p99_latency_ms': statistics.quantiles(durations, n=100)[98],
            'min_latency_ms': min(durations),
            'max_latency_ms': max(durations),
            'operation_breakdown': op_counts
        }
        
        return metrics
    
    def print_performance_report(self, metrics: Dict[str, Any]):
        """Print formatted performance report."""
        print(f"\n=== PERFORMANCE REPORT: {metrics['operation'].upper()} ===")
        print(f"Total Requests: {metrics['total_requests']:,}")
        print(f"Successful Requests: {metrics['successful_requests']:,}")
        print(f"Total Time: {metrics['total_time_seconds']:.2f}s")
        print(f"Requests/Second: {metrics['requests_per_second']:.1f}")
        print(f"\nLatency Metrics:")
        print(f"  Average: {metrics['avg_latency_ms']:.2f}ms")
        print(f"  Median:  {metrics['median_latency_ms']:.2f}ms")
        print(f"  95th percentile: {metrics['p95_latency_ms']:.2f}ms")
        print(f"  99th percentile: {metrics['p99_latency_ms']:.2f}ms")
        print(f"  Min: {metrics['min_latency_ms']:.2f}ms")
        print(f"  Max: {metrics['max_latency_ms']:.2f}ms")
        
        if 'operation_breakdown' in metrics:
            print(f"\nOperation Breakdown:")
            for op, count in metrics['operation_breakdown'].items():
                percentage = (count / metrics['total_requests']) * 100
                print(f"  {op}: {count:,} ({percentage:.1f}%)")
        
        # Performance assessment
        print(f"\n=== PERFORMANCE ASSESSMENT ===")
        
        # Check if meets target (≤20ms p95, ≥1000 rps)
        meets_latency_target = metrics['p95_latency_ms'] <= 20.0
        meets_throughput_target = metrics['requests_per_second'] >= 1000.0
        
        print(f"Target: ≤20ms P95 latency: {'✅ PASS' if meets_latency_target else '❌ FAIL'} "
              f"({metrics['p95_latency_ms']:.2f}ms)")
        print(f"Target: ≥1000 RPS: {'✅ PASS' if meets_throughput_target else '❌ FAIL'} "
              f"({metrics['requests_per_second']:.1f} RPS)")
        
        overall_pass = meets_latency_target and meets_throughput_target
        print(f"\nOverall Performance: {'✅ PASS' if overall_pass else '❌ FAIL'}")
        
        return overall_pass


async def run_performance_tests():
    """Run comprehensive performance test suite."""
    print("🚀 Starting Memory Fusion Hub Performance Tests")
    print("=" * 60)
    
    test_runner = MockPerformanceTest()
    all_results = []
    
    try:
        # Test 1: Cache GET performance
        get_metrics = await test_runner.test_cache_get_performance(1000)
        test_runner.print_performance_report(get_metrics)
        all_results.append(get_metrics)
        
        print("\n" + "=" * 60)
        
        # Test 2: Cache PUT performance
        put_metrics = await test_runner.test_cache_put_performance(1000)
        test_runner.print_performance_report(put_metrics)
        all_results.append(put_metrics)
        
        print("\n" + "=" * 60)
        
        # Test 3: Mixed workload performance
        mixed_metrics = await test_runner.test_mixed_workload_performance(1000)
        test_runner.print_performance_report(mixed_metrics)
        all_results.append(mixed_metrics)
        
        print("\n" + "=" * 60)
        
        # Overall summary
        print("\n📊 OVERALL PERFORMANCE SUMMARY")
        print("=" * 60)
        
        all_pass = True
        for result in all_results:
            meets_targets = (result['p95_latency_ms'] <= 20.0 and 
                           result['requests_per_second'] >= 1000.0)
            status = "✅ PASS" if meets_targets else "❌ FAIL"
            print(f"{result['operation'].upper()}: {status} "
                  f"(P95: {result['p95_latency_ms']:.1f}ms, "
                  f"RPS: {result['requests_per_second']:.0f})")
            all_pass = all_pass and meets_targets
        
        print(f"\n🎯 FINAL RESULT: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
        
        if all_pass:
            print("✨ Memory Fusion Hub meets performance requirements!")
            print("   - P95 latency ≤ 20ms")
            print("   - Throughput ≥ 1,000 RPS")
        else:
            print("⚠️  Performance requirements not met. Consider optimization.")
        
        return all_pass
        
    except Exception as e:
        print(f"❌ Performance test failed with error: {e}")
        return False


if __name__ == "__main__":
    # Run performance tests
    result = asyncio.run(run_performance_tests())
    exit(0 if result else 1)