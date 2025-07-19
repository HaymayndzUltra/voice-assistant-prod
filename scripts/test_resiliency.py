#!/usr/bin/env python3
"""
WP-07 Resiliency Test Suite
Tests circuit breakers, retry mechanisms, bulkheads, and health monitoring
"""

import asyncio
import time
import random
import threading
from pathlib import Path
import sys

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("🧪 Testing Circuit Breaker...")
    
    try:
        from common.resiliency.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState, 
            CircuitBreakerException
        )
        
        # Create circuit breaker
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_duration=2.0,
            request_timeout=1.0
        )
        breaker = CircuitBreaker("test_breaker", config)
        
        # Test function that sometimes fails
        call_count = 0
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError("Service unavailable")
            return f"Success on call {call_count}"
        
        # Test failure accumulation
        for i in range(3):
            try:
                await breaker.call_async(flaky_service)
            except Exception:
                pass
        
        # Circuit should be open now
        assert breaker.is_open, "Circuit should be open after failures"
        
        # Test that calls are blocked
        try:
            await breaker.call_async(flaky_service)
            assert False, "Call should be blocked when circuit is open"
        except CircuitBreakerException:
            pass
        
        # Wait for circuit to transition to half-open
        await asyncio.sleep(2.1)
        
        # Test recovery
        result = await breaker.call_async(flaky_service)
        assert "Success" in result
        
        # More successful calls should close the circuit
        for _ in range(2):
            await breaker.call_async(flaky_service)
        
        assert breaker.is_closed, "Circuit should be closed after successful calls"
        
        # Test metrics
        metrics = breaker.get_metrics()
        assert metrics['total_calls'] > 0
        assert metrics['failed_calls'] > 0
        assert metrics['successful_calls'] > 0
        
        print(f"  📊 Circuit state: {breaker.state.value}")
        print(f"  📊 Total calls: {metrics['total_calls']}")
        print(f"  📊 Failed calls: {metrics['failed_calls']}")
        print(f"  📊 Success rate: {metrics['successful_calls'] / metrics['total_calls']:.2f}")
        print(f"  ✅ Circuit breaker test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Circuit breaker test failed: {e}")
        return False

async def test_retry_mechanism():
    """Test retry mechanism with exponential backoff"""
    print("\n🧪 Testing Retry Mechanism...")
    
    try:
        from common.resiliency.retry import (
            RetryManager, RetryConfig, RetryStrategy, 
            JitterType, RetryExhaustedException
        )
        
        # Create retry manager
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter_type=JitterType.UNIFORM
        )
        retry_manager = RetryManager(config)
        
        # Test successful retry after failures
        attempt_count = 0
        async def sometimes_fail():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError(f"Attempt {attempt_count} failed")
            return f"Success on attempt {attempt_count}"
        
        result = await retry_manager.execute_async(sometimes_fail)
        assert "Success" in result
        assert attempt_count == 3
        
        # Test retry exhaustion
        attempt_count = 0
        async def always_fail():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError(f"Always fails - attempt {attempt_count}")
        
        try:
            await retry_manager.execute_async(always_fail)
            assert False, "Should have thrown RetryExhaustedException"
        except RetryExhaustedException as e:
            assert len(e.attempts) == 3
            assert attempt_count == 3
        
        # Test metrics
        metrics = retry_manager.get_metrics()
        
        print(f"  📊 Total operations: {metrics['total_operations']}")
        print(f"  📊 Successful operations: {metrics['successful_operations']}")
        print(f"  📊 Failed operations: {metrics['failed_operations']}")
        print(f"  📊 Average attempts: {metrics['avg_attempts_per_operation']:.1f}")
        print(f"  ✅ Retry mechanism test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Retry mechanism test failed: {e}")
        return False

async def test_bulkhead_isolation():
    """Test bulkhead resource isolation"""
    print("\n🧪 Testing Bulkhead Isolation...")
    
    try:
        from common.resiliency.bulkhead import (
            Bulkhead, BulkheadConfig, IsolationStrategy,
            BulkheadFullException, BulkheadTimeoutException
        )
        
        # Create bulkhead with limited concurrency
        config = BulkheadConfig(
            name="test_bulkhead",
            max_concurrent=2,
            max_queue_size=5,
            timeout=2.0,
            isolation_strategy=IsolationStrategy.ASYNC_SEMAPHORE
        )
        bulkhead = Bulkhead(config)
        
        # Test concurrent execution limits
        execution_times = []
        
        async def slow_operation(duration, operation_id):
            start_time = time.time()
            await asyncio.sleep(duration)
            execution_times.append((operation_id, start_time, time.time()))
            return f"Operation {operation_id} completed"
        
        # Launch multiple operations
        tasks = []
        for i in range(4):
            task = asyncio.create_task(
                bulkhead.execute_async(slow_operation, 0.5, i)
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 4
        assert all("completed" in result for result in results)
        
        # Test timeout
        try:
            await bulkhead.execute_async(slow_operation, 5.0, "timeout_test")
            assert False, "Should have timed out"
        except BulkheadTimeoutException:
            pass
        
        # Test metrics
        metrics = bulkhead.get_metrics()
        health = bulkhead.get_health_status()
        
        print(f"  📊 Total operations: {metrics['total_operations']}")
        print(f"  📊 Successful operations: {metrics['successful_operations']}")
        print(f"  📊 Max concurrent reached: {metrics['max_concurrent_reached']}")
        print(f"  📊 Success rate: {metrics['success_rate']:.2f}")
        print(f"  📊 Health status: {health['health']}")
        print(f"  ✅ Bulkhead isolation test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Bulkhead isolation test failed: {e}")
        return False

async def test_health_monitoring():
    """Test health monitoring system"""
    print("\n🧪 Testing Health Monitoring...")
    
    try:
        from common.resiliency.health_monitor import (
            HealthMonitor, HealthCheck, HealthStatus
        )
        
        # Create health monitor
        monitor = HealthMonitor("test_system")
        
        # Register health checks
        check_results = {"connectivity": True, "resources": True}
        
        async def connectivity_check():
            return check_results["connectivity"]
        
        async def resource_check():
            return check_results["resources"]
        
        async def flaky_check():
            return random.random() > 0.3  # 70% success rate
        
        monitor.register_health_check(HealthCheck(
            name="connectivity",
            check_function=connectivity_check,
            timeout=1.0,
            critical=True,
            description="Test connectivity"
        ))
        
        monitor.register_health_check(HealthCheck(
            name="resources",
            check_function=resource_check,
            timeout=1.0,
            critical=False,
            description="Test resources"
        ))
        
        monitor.register_health_check(HealthCheck(
            name="flaky_service",
            check_function=flaky_check,
            timeout=1.0,
            critical=False,
            description="Flaky service"
        ))
        
        # Test all checks passing
        results = await monitor.run_all_health_checks()
        status = monitor.get_health_status()
        
        assert len(results) == 3
        assert status['overall_status'] in ['healthy', 'degraded']  # Flaky service might fail
        
        # Test critical failure
        check_results["connectivity"] = False
        results = await monitor.run_all_health_checks()
        status = monitor.get_health_status()
        
        assert status['overall_status'] == 'unhealthy'
        
        # Test recovery
        check_results["connectivity"] = True
        results = await monitor.run_all_health_checks()
        status = monitor.get_health_status()
        
        # Test metrics
        metrics = monitor.get_metrics()
        
        print(f"  📊 Overall status: {status['overall_status']}")
        print(f"  📊 Total checks: {status['summary']['total_checks']}")
        print(f"  📊 Healthy checks: {status['summary']['healthy_checks']}")
        print(f"  📊 Unhealthy checks: {status['summary']['unhealthy_checks']}")
        print(f"  📊 Health check metrics: {len(metrics['timers'])} timers")
        print(f"  ✅ Health monitoring test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Health monitoring test failed: {e}")
        return False

async def test_combined_resiliency():
    """Test combined resiliency patterns"""
    print("\n🧪 Testing Combined Resiliency Patterns...")
    
    try:
        from common.resiliency.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
        from common.resiliency.retry import RetryManager, RetryConfig
        from common.resiliency.bulkhead import get_bulkhead, IsolationStrategy
        
        # Create combined protection
        circuit_breaker = get_circuit_breaker(
            "combined_test",
            CircuitBreakerConfig(failure_threshold=2, timeout_duration=1.0)
        )
        
        retry_manager = RetryManager(RetryConfig(
            max_attempts=2,
            base_delay=0.1
        ))
        
        bulkhead = get_bulkhead(
            "combined_bulkhead",
            max_concurrent=3,
            timeout=2.0,
            isolation_strategy=IsolationStrategy.ASYNC_SEMAPHORE
        )
        
        # Test service with all protections
        call_count = 0
        async def protected_service():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise ConnectionError("Service down")
            return f"Success after {call_count} calls"
        
        async def resilient_call():
            async def circuit_protected_call():
                return await circuit_breaker.call_async(protected_service)
            
            async def retry_protected_call():
                return await retry_manager.execute_async(circuit_protected_call)
            
            return await bulkhead.execute_async(retry_protected_call)
        
        # This should succeed after retries
        result = await resilient_call()
        assert "Success" in result
        
        # Test metrics from all components
        cb_metrics = circuit_breaker.get_metrics()
        retry_metrics = retry_manager.get_metrics()
        bulkhead_metrics = bulkhead.get_metrics()
        
        print(f"  📊 Circuit breaker calls: {cb_metrics['total_calls']}")
        print(f"  📊 Retry operations: {retry_metrics['total_operations']}")
        print(f"  📊 Bulkhead operations: {bulkhead_metrics['total_operations']}")
        print(f"  📊 Combined success: {'✅' if 'Success' in result else '❌'}")
        print(f"  ✅ Combined resiliency test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Combined resiliency test failed: {e}")
        return False

async def test_decorator_patterns():
    """Test decorator-based resiliency patterns"""
    print("\n🧪 Testing Decorator Patterns...")
    
    try:
        from common.resiliency.circuit_breaker import circuit_breaker
        from common.resiliency.retry import retry, RetryStrategy
        from common.resiliency.bulkhead import bulkhead, IsolationStrategy
        
        # Test decorated functions
        call_count = 0
        
        @circuit_breaker(name="decorator_test")
        @retry(max_attempts=2, base_delay=0.1, strategy=RetryStrategy.FIXED_DELAY)
        @bulkhead(name="decorator_bulkhead", max_concurrent=2)
        async def decorated_service():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("First call fails")
            return f"Decorated success on call {call_count}"
        
        # Test the decorated function
        result = await decorated_service()
        assert "Decorated success" in result
        assert call_count == 2  # Should retry once
        
        # Test multiple concurrent calls
        tasks = []
        call_count = 0  # Reset for concurrent test
        
        for i in range(3):
            task = asyncio.create_task(decorated_service())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_calls = sum(1 for r in results if isinstance(r, str) and "success" in r)
        
        print(f"  📊 Decorated function calls: {call_count}")
        print(f"  📊 Successful concurrent calls: {successful_calls}")
        print(f"  📊 Decorator integration: {'✅' if successful_calls > 0 else '❌'}")
        print(f"  ✅ Decorator patterns test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Decorator patterns test failed: {e}")
        return False

async def test_registry_management():
    """Test registry management for resiliency components"""
    print("\n🧪 Testing Registry Management...")
    
    try:
        from common.resiliency.circuit_breaker import get_circuit_breaker_registry
        from common.resiliency.bulkhead import get_bulkhead_registry
        
        # Test circuit breaker registry
        cb_registry = get_circuit_breaker_registry()
        
        # Create some circuit breakers
        cb1 = get_circuit_breaker("test_service_1")
        cb2 = get_circuit_breaker("test_service_2")
        
        # Test registry functions
        breaker_list = cb_registry.list_breakers()
        assert len(breaker_list) >= 2
        
        all_metrics = cb_registry.get_all_metrics()
        health_summary = cb_registry.get_health_summary()
        
        # Test bulkhead registry
        bulkhead_registry = get_bulkhead_registry()
        
        # Create some bulkheads
        from common.resiliency.bulkhead import get_bulkhead
        bh1 = get_bulkhead("test_bulkhead_1", max_concurrent=5)
        bh2 = get_bulkhead("test_bulkhead_2", max_concurrent=10)
        
        bulkhead_list = bulkhead_registry.list_bulkheads()
        bulkhead_metrics = bulkhead_registry.get_all_metrics()
        bulkhead_health = bulkhead_registry.get_all_health_status()
        
        print(f"  📊 Circuit breakers registered: {len(breaker_list)}")
        print(f"  📊 Overall CB health: {health_summary['overall_health']}")
        print(f"  📊 Bulkheads registered: {len(bulkhead_list)}")
        print(f"  📊 Healthy bulkheads: {sum(1 for h in bulkhead_health.values() if h['health'] == 'healthy')}")
        print(f"  ✅ Registry management test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Registry management test failed: {e}")
        return False

async def main():
    """Run all resiliency tests"""
    print("🚀 WP-07 Resiliency Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run tests
    test_results.append(await test_circuit_breaker())
    test_results.append(await test_retry_mechanism())
    test_results.append(await test_bulkhead_isolation())
    test_results.append(await test_health_monitoring())
    test_results.append(await test_combined_resiliency())
    test_results.append(await test_decorator_patterns())
    test_results.append(await test_registry_management())
    
    # Summary
    passed_tests = sum(1 for result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 TEST SUMMARY:")
    print(f"✅ Passed: {passed_tests}/{total_tests} tests")
    
    if passed_tests == total_tests:
        print(f"🎉 All resiliency tests passed!")
        print(f"\n🚀 Resiliency patterns are ready for production use!")
    else:
        print(f"⚠️  Some tests failed or were skipped")
        print(f"\n📋 Resiliency components:")
        print(f"   - Circuit Breakers (common/resiliency/circuit_breaker.py)")
        print(f"   - Retry Mechanisms (common/resiliency/retry.py)")
        print(f"   - Bulkhead Isolation (common/resiliency/bulkhead.py)")
        print(f"   - Health Monitoring (common/resiliency/health_monitor.py)")
    
    print(f"\n💡 Usage Examples:")
    print(f"   # Circuit breaker protection")
    print(f"   from common.resiliency.circuit_breaker import circuit_breaker")
    print(f"   @circuit_breaker(name='my_service')")
    print(f"   async def call_service(): ...")
    print(f"\n   # Retry with exponential backoff")
    print(f"   from common.resiliency.retry import retry")
    print(f"   @retry(max_attempts=3, base_delay=1.0)")
    print(f"   async def network_call(): ...")
    print(f"\n   # Resource isolation")
    print(f"   from common.resiliency.bulkhead import bulkhead")
    print(f"   @bulkhead(name='heavy_task', max_concurrent=5)")
    print(f"   async def process_data(): ...")
    print(f"\n   # Health monitoring")
    print(f"   from common.resiliency.health_monitor import get_health_monitor")
    print(f"   monitor = get_health_monitor()")
    print(f"   await monitor.start_monitoring()")

if __name__ == "__main__":
    asyncio.run(main()) 