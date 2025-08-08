"""Integration tests for ModelOps Coordinator - 500 concurrent gRPC calls."""

import pytest
import asyncio
import grpc
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from model_ops_pb2 import InferenceRequest, InferenceResponse
from model_ops_pb2_grpc import ModelOpsStub
from app import ModelOpsCoordinatorApp


class TestIntegration:
    """Integration tests for the ModelOps Coordinator."""
    
    @pytest.fixture(scope="class")
    async def running_app(self):
        """Start the ModelOps Coordinator app for testing."""
        app = ModelOpsCoordinatorApp()
        
        # Use a test configuration
        app.config = {
            'server': {
                'zmq_port': 17211,
                'grpc_port': 17212, 
                'rest_port': 18008,
                'max_workers': 16
            },
            'resources': {
                'gpu_poll_interval': 5,
                'vram_soft_limit_mb': 1000,
                'eviction_threshold_pct': 90
            },
            'models': {
                'preload': [],
                'default_dtype': 'float16',
                'quantization': True
            },
            'learning': {
                'enable_auto_tune': False,
                'max_parallel_jobs': 2,
                'job_store': 'test_jobs.db'
            },
            'goals': {
                'policy': 'priority_queue',
                'max_active_goals': 10
            },
            'resilience': {
                'circuit_breaker': {
                    'failure_threshold': 4,
                    'reset_timeout': 20
                },
                'bulkhead': {
                    'max_concurrent': 64,
                    'max_queue_size': 256
                }
            }
        }
        
        # Start the app
        task = asyncio.create_task(app.start())
        
        # Wait for servers to start
        await asyncio.sleep(2)
        
        yield app
        
        # Cleanup
        await app._shutdown_async()
        if not task.done():
            task.cancel()

    @pytest.mark.asyncio
    async def test_500_concurrent_grpc_infer_calls(self, running_app):
        """
        Test 500 concurrent gRPC Infer calls and verify p95 latency < 50ms.
        This is the core requirement for Phase 6 integration testing.
        """
        grpc_port = 17212
        channel = grpc.aio.insecure_channel(f'localhost:{grpc_port}')
        stub = ModelOpsStub(channel)
        
        # Test request payload
        test_request = InferenceRequest(
            model_name="test-model",
            input_text="Hello, world! This is a test inference request.",
            max_tokens=50,
            temperature=0.7
        )
        
        async def single_infer_call(request_id: int) -> tuple:
            """Make a single inference call and measure latency."""
            start_time = time.time()
            try:
                response = await stub.Infer(test_request)
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                return request_id, latency_ms, True, None
            except Exception as e:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                return request_id, latency_ms, False, str(e)
        
        # Execute 500 concurrent calls
        print(f"\n🚀 Starting 500 concurrent gRPC Infer calls...")
        start_time = time.time()
        
        tasks = [single_infer_call(i) for i in range(500)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        print(f"📊 Total execution time: {total_time:.2f}s")
        
        # Analyze results
        latencies = []
        successful_calls = 0
        failed_calls = 0
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_calls += 1
                errors.append(str(result))
                continue
                
            request_id, latency_ms, success, error = result
            if success:
                successful_calls += 1
                latencies.append(latency_ms)
            else:
                failed_calls += 1
                errors.append(f"Request {request_id}: {error}")
        
        # Calculate statistics
        if latencies:
            min_latency = min(latencies)
            max_latency = max(latencies)
            avg_latency = statistics.mean(latencies)
            p50_latency = statistics.median(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max_latency
        else:
            min_latency = max_latency = avg_latency = p50_latency = p95_latency = p99_latency = 0
        
        # Print detailed results
        print(f"📈 Performance Results:")
        print(f"   ✅ Successful calls: {successful_calls}/500 ({successful_calls/500*100:.1f}%)")
        print(f"   ❌ Failed calls: {failed_calls}/500 ({failed_calls/500*100:.1f}%)")
        print(f"   ⚡ Min latency: {min_latency:.2f}ms")
        print(f"   ⚡ Max latency: {max_latency:.2f}ms")
        print(f"   ⚡ Avg latency: {avg_latency:.2f}ms")
        print(f"   ⚡ P50 latency: {p50_latency:.2f}ms")
        print(f"   ⚡ P95 latency: {p95_latency:.2f}ms")
        print(f"   ⚡ P99 latency: {p99_latency:.2f}ms")
        print(f"   🎯 Throughput: {successful_calls/total_time:.2f} req/s")
        
        if failed_calls > 0:
            print(f"❌ Sample errors ({min(5, len(errors))} of {len(errors)}):")
            for error in errors[:5]:
                print(f"   - {error}")
        
        # Cleanup
        await channel.close()
        
        # Assertions for Phase 6 requirements
        assert successful_calls >= 400, f"Expected at least 400 successful calls, got {successful_calls}"
        assert p95_latency < 50, f"P95 latency {p95_latency:.2f}ms exceeds 50ms requirement"
        
        print(f"✅ Integration test PASSED - P95 latency: {p95_latency:.2f}ms < 50ms")

    @pytest.mark.asyncio
    async def test_grpc_server_connectivity(self):
        """Test basic gRPC server connectivity."""
        grpc_port = 17212
        
        try:
            channel = grpc.aio.insecure_channel(f'localhost:{grpc_port}')
            
            # Try to connect with a simple call
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            
            await channel.close()
            print("✅ gRPC server connectivity test passed")
            
        except asyncio.TimeoutError:
            pytest.fail("gRPC server failed to become ready within 5 seconds")
        except Exception as e:
            pytest.fail(f"gRPC connectivity test failed: {e}")

    @pytest.mark.asyncio 
    async def test_load_performance_under_stress(self, running_app):
        """Test system performance under load stress."""
        grpc_port = 17212
        channel = grpc.aio.insecure_channel(f'localhost:{grpc_port}')
        stub = ModelOpsStub(channel)
        
        # Smaller stress test - 100 calls in waves
        waves = 5
        calls_per_wave = 20
        
        print(f"\n🌊 Starting stress test: {waves} waves of {calls_per_wave} calls each")
        
        all_latencies = []
        
        for wave in range(waves):
            print(f"   Wave {wave + 1}/{waves}...")
            
            test_request = InferenceRequest(
                model_name=f"stress-test-model-{wave}",
                input_text=f"Stress test wave {wave + 1} input text for load testing.",
                max_tokens=30
            )
            
            # Execute wave of concurrent calls
            wave_start = time.time()
            tasks = []
            
            for i in range(calls_per_wave):
                async def call():
                    start = time.time()
                    try:
                        await stub.Infer(test_request)
                        return (time.time() - start) * 1000
                    except:
                        return None
                
                tasks.append(call())
            
            wave_results = await asyncio.gather(*tasks, return_exceptions=True)
            wave_time = time.time() - wave_start
            
            # Collect successful latencies
            wave_latencies = [r for r in wave_results if isinstance(r, (int, float)) and r is not None]
            all_latencies.extend(wave_latencies)
            
            print(f"     ⚡ Wave {wave + 1}: {len(wave_latencies)}/{calls_per_wave} successful, "
                  f"avg latency: {statistics.mean(wave_latencies):.2f}ms" if wave_latencies else "0ms")
            
            # Brief pause between waves
            await asyncio.sleep(0.5)
        
        await channel.close()
        
        # Final analysis
        if all_latencies:
            overall_p95 = statistics.quantiles(all_latencies, n=20)[18]
            overall_avg = statistics.mean(all_latencies)
            
            print(f"📊 Stress Test Summary:")
            print(f"   ✅ Total successful calls: {len(all_latencies)}/{waves * calls_per_wave}")
            print(f"   ⚡ Overall avg latency: {overall_avg:.2f}ms")
            print(f"   ⚡ Overall P95 latency: {overall_p95:.2f}ms")
            
            assert overall_p95 < 100, f"Stress test P95 latency {overall_p95:.2f}ms too high"
            print("✅ Stress test PASSED")
        else:
            pytest.fail("No successful calls in stress test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])