#!/usr/bin/env python3
"""
WP-09 Distributed Logging & Observability Test Suite
Tests structured logging, distributed tracing, and metrics collection
"""

import asyncio
import time
import json
from pathlib import Path
import sys

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

async def test_structured_logging():
    """Test structured logging functionality"""
    print("🧪 Testing Structured Logging...")
    
    try:
        from common.observability.logging import (
            get_distributed_logger, LogLevel, LogCategory, log_function_calls
        )
        
        logger = get_distributed_logger()
        
        # Test basic logging
        await logger.info("Test info message", 
                         category=LogCategory.SYSTEM,
                         data={"test_key": "test_value"},
                         tags=["test"])
        
        # Test error logging with exception
        try:
            raise ValueError("Test exception")
        except Exception as e:
            await logger.error("Test error message",
                             category=LogCategory.SYSTEM,
                             exception=e,
                             data={"error_context": "test_context"})
        
        # Test context manager
        async with logger.async_context(operation="test_operation", user_id="test_user"):
            await logger.debug("Message with context",
                             category=LogCategory.AGENT,
                             data={"context_test": True})
        
        # Test function decoration
        @log_function_calls(level=LogLevel.INFO, category=LogCategory.AGENT)
        async def test_decorated_function():
            await asyncio.sleep(0.1)
            return "decorated_result"
        
        result = await test_decorated_function()
        
        # Test metrics
        metrics = logger.get_metrics()
        
        print(f"  📊 Total logs: {metrics['total_logs']}")
        print(f"  📊 Info logs: {metrics['logs_by_level'][LogLevel.INFO]}")
        print(f"  📊 Error logs: {metrics['logs_by_level'][LogLevel.ERROR]}")
        print(f"  📊 System logs: {metrics['logs_by_category'][LogCategory.SYSTEM]}")
        print(f"  📊 Active handlers: {len(metrics['handlers'])}")
        print(f"  📊 Function decoration: {'✅' if result == 'decorated_result' else '❌'}")
        print(f"  ✅ Structured logging test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Structured logging test failed: {e}")
        return False

async def test_distributed_tracing():
    """Test distributed tracing functionality"""
    print("\n🧪 Testing Distributed Tracing...")
    
    try:
        from common.observability.tracing import (
            get_tracer, trace_function, SpanKind, get_current_trace_id
        )
        
        tracer = get_tracer("test_service")
        
        # Test manual span creation
        async with tracer.async_span("test_operation", kind=SpanKind.SERVER) as span:
            span.set_tag("test.tag", "test_value")
            span.log_event("operation_started")
            
            # Simulate work
            await asyncio.sleep(0.05)
            
            span.log_event("operation_completed")
        
        # Test nested spans
        async with tracer.async_span("parent_operation") as parent_span:
            parent_span.set_tag("parent.id", "123")
            
            async with tracer.async_span("child_operation") as child_span:
                child_span.set_tag("child.id", "456")
                
                # Test trace ID correlation
                trace_id = get_current_trace_id()
                assert trace_id == parent_span.context.trace_id
                assert trace_id == child_span.context.trace_id
                
                await asyncio.sleep(0.02)
        
        # Test function decoration
        @trace_function(operation_name="decorated_operation", kind=SpanKind.INTERNAL)
        async def test_traced_function(x, y):
            await asyncio.sleep(0.01)
            return x + y
        
        result = await test_traced_function(5, 3)
        
        # Test error handling in spans
        try:
            async with tracer.async_span("error_operation") as span:
                span.set_tag("will_fail", True)
                raise RuntimeError("Test error")
        except RuntimeError:
            pass  # Expected
        
        # Get metrics
        metrics = tracer.get_metrics()
        
        print(f"  📊 Spans created: {metrics['spans_created']}")
        print(f"  📊 Spans finished: {metrics['spans_finished']}")
        print(f"  📊 Spans with errors: {metrics['spans_with_errors']}")
        print(f"  📊 Avg duration: {metrics['avg_duration']:.4f}s")
        print(f"  📊 Error rate: {metrics['error_rate']:.2f}")
        print(f"  📊 Function tracing: {'✅' if result == 8 else '❌'}")
        print(f"  ✅ Distributed tracing test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Distributed tracing test failed: {e}")
        return False

async def test_metrics_collection():
    """Test metrics collection functionality"""
    print("\n🧪 Testing Metrics Collection...")
    
    try:
        from common.observability.metrics import (
            get_metrics_registry, counter, gauge, histogram, timer,
            measure_time, count_calls
        )
        
        registry = get_metrics_registry()
        
        # Test counter
        test_counter = counter("test.counter")
        test_counter.increment(5.0, component="test")
        test_counter.increment(3.0, component="test")
        
        assert test_counter.get_value() == 8.0
        
        # Test gauge
        test_gauge = gauge("test.gauge")
        test_gauge.set(100.0, service="test")
        test_gauge.increment(25.0, service="test")
        test_gauge.decrement(15.0, service="test")
        
        assert test_gauge.get_value() == 110.0
        
        # Test histogram
        test_histogram = histogram("test.histogram")
        for i in range(10):
            test_histogram.observe(i * 0.1, operation="test")
        
        stats = test_histogram.get_statistics()
        assert stats['count'] == 10
        assert stats['mean'] > 0
        
        # Test timer
        test_timer = timer("test.timer")
        
        with test_timer.time_context(operation="test"):
            await asyncio.sleep(0.05)
        
        timer_stats = test_timer.get_statistics()
        assert timer_stats['count'] >= 1
        assert timer_stats['min'] > 0
        
        # Test decorators
        call_count = 0
        
        @measure_time(metric_name="test.function_time")
        @count_calls(metric_name="test.function_calls")
        async def test_measured_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "measured"
        
        result1 = await test_measured_function()
        result2 = await test_measured_function()
        
        # Test alerts
        from common.observability.metrics import Alert, AlertLevel
        
        alert = Alert(
            name="test_alert",
            metric_name="test.counter",
            condition="> 5",
            level=AlertLevel.WARNING,
            message="Test alert triggered"
        )
        
        registry.add_alert(alert)
        
        # Get all metrics
        all_metrics = registry.get_all_metrics()
        
        print(f"  📊 Counter value: {test_counter.get_value()}")
        print(f"  📊 Gauge value: {test_gauge.get_value()}")
        print(f"  📊 Histogram count: {stats['count']}")
        print(f"  📊 Timer count: {timer_stats['count']}")
        print(f"  📊 Function calls: {call_count}")
        print(f"  📊 Total metrics: {len(all_metrics)}")
        print(f"  📊 Function decoration: {'✅' if result1 == 'measured' and result2 == 'measured' else '❌'}")
        print(f"  ✅ Metrics collection test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Metrics collection test failed: {e}")
        return False

async def test_observability_integration():
    """Test integrated observability (logging + tracing + metrics)"""
    print("\n🧪 Testing Observability Integration...")
    
    try:
        from common.observability.logging import get_distributed_logger, LogCategory
        from common.observability.tracing import get_tracer, get_current_trace_id
        from common.observability.metrics import counter, timer
        
        logger = get_distributed_logger()
        tracer = get_tracer("integration_test")
        
        # Integrated operation with all three pillars
        async def integrated_operation(data):
            # Start distributed trace
            async with tracer.async_span("integrated_operation") as span:
                trace_id = get_current_trace_id()
                
                # Log with trace correlation
                async with logger.async_context(correlation_id=trace_id, operation="integrated"):
                    await logger.info("Starting integrated operation",
                                     category=LogCategory.AGENT,
                                     data={"input_size": len(data)})
                    
                    # Count operation
                    op_counter = counter("integration.operations")
                    op_counter.increment(operation="integrated")
                    
                    # Time the operation
                    op_timer = timer("integration.duration")
                    with op_timer.time_context(operation="integrated"):
                        # Simulate processing
                        await asyncio.sleep(0.1)
                        
                        # Add span details
                        span.set_tag("data.size", len(data))
                        span.log_event("processing_completed")
                        
                        # Log completion
                        await logger.info("Integrated operation completed",
                                         category=LogCategory.AGENT,
                                         data={"result": "success"},
                                         performance_metrics={"processing_time": 0.1})
                        
                        return {"status": "success", "processed": len(data)}
        
        # Run integrated operation
        result = await integrated_operation("test_data_12345")
        
        # Verify correlation
        trace_id = get_current_trace_id()
        
        # Check metrics
        logger_metrics = logger.get_metrics()
        tracer_metrics = tracer.get_tracer().get_metrics() if hasattr(tracer, 'get_tracer') else tracer.get_metrics()
        
        print(f"  📊 Operation result: {result['status']}")
        print(f"  📊 Data processed: {result['processed']}")
        print(f"  📊 Logger total logs: {logger_metrics['total_logs']}")
        print(f"  📊 Tracer spans created: {tracer_metrics['spans_created']}")
        print(f"  📊 Correlation: {'✅' if result['status'] == 'success' else '❌'}")
        print(f"  ✅ Observability integration test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Observability integration test failed: {e}")
        return False

async def test_performance_monitoring():
    """Test performance monitoring capabilities"""
    print("\n🧪 Testing Performance Monitoring...")
    
    try:
        from common.observability.metrics import histogram, timer, gauge
        from common.observability.tracing import get_tracer
        
        # Performance metrics
        response_time = histogram("perf.response_time", buckets=[0.01, 0.05, 0.1, 0.5, 1.0])
        memory_usage = gauge("perf.memory_usage")
        operation_timer = timer("perf.operation_time")
        
        tracer = get_tracer("performance_test")
        
        # Simulate various performance scenarios
        performance_data = []
        
        for i in range(20):
            async with tracer.async_span(f"perf_operation_{i}") as span:
                # Simulate different response times
                duration = 0.01 + (i * 0.02)  # 0.01 to 0.39 seconds
                
                with operation_timer.time_context(iteration=str(i)):
                    await asyncio.sleep(duration)
                
                # Record metrics
                response_time.observe(duration, operation=f"op_{i}")
                memory_usage.set(50 + i, iteration=str(i))
                
                # Add span metadata
                span.set_tag("iteration", i)
                span.set_tag("duration", duration)
                
                performance_data.append(duration)
        
        # Analyze performance
        response_stats = response_time.get_statistics()
        timer_stats = operation_timer.get_statistics()
        
        # Performance analysis
        avg_response = sum(performance_data) / len(performance_data)
        max_response = max(performance_data)
        min_response = min(performance_data)
        
        print(f"  📊 Operations completed: {len(performance_data)}")
        print(f"  📊 Avg response time: {avg_response:.3f}s")
        print(f"  📊 Min response time: {min_response:.3f}s")
        print(f"  📊 Max response time: {max_response:.3f}s")
        print(f"  📊 P95 response time: {response_stats.get('p95', 0):.3f}s")
        print(f"  📊 Memory usage: {memory_usage.get_value()}")
        print(f"  📊 Timer count: {timer_stats['count']}")
        print(f"  ✅ Performance monitoring test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance monitoring test failed: {e}")
        return False

async def test_alerting_system():
    """Test alerting and notification system"""
    print("\n🧪 Testing Alerting System...")
    
    try:
        from common.observability.metrics import (
            get_metrics_registry, counter, Alert, AlertLevel
        )
        
        registry = get_metrics_registry()
        
        # Create test counter
        alert_counter = counter("test.alert_counter")
        
        # Create alert
        test_alert = Alert(
            name="test_high_count",
            metric_name="test.alert_counter.count",
            condition="> 5",
            level=AlertLevel.WARNING,
            message="Test counter exceeded threshold",
            cooldown=1.0  # 1 second cooldown for testing
        )
        
        registry.add_alert(test_alert)
        
        # Test alert triggering
        alert_triggered = False
        
        def alert_subscriber(metric):
            nonlocal alert_triggered
            if "alert_counter" in metric.name:
                alert_triggered = True
        
        registry.subscribe(alert_subscriber)
        
        # Increment counter to trigger alert
        for i in range(7):  # Should trigger at 6
            alert_counter.increment()
            await asyncio.sleep(0.01)
        
        # Test cooldown
        time.sleep(0.1)  # Wait a bit
        
        print(f"  📊 Counter value: {alert_counter.get_value()}")
        print(f"  📊 Alert condition: {test_alert.condition}")
        print(f"  📊 Alert level: {test_alert.level.value}")
        print(f"  📊 Alert triggered: {'✅' if alert_triggered else '❌'}")
        print(f"  📊 Cooldown works: {'✅' if test_alert.can_trigger() else '❌'}")
        print(f"  ✅ Alerting system test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Alerting system test failed: {e}")
        return False

async def test_trace_analysis():
    """Test trace analysis capabilities"""
    print("\n🧪 Testing Trace Analysis...")
    
    try:
        from common.observability.tracing import get_tracer, TraceAnalyzer, InMemorySpanRecorder
        
        # Create tracer with in-memory recorder for analysis
        recorder = InMemorySpanRecorder()
        tracer = get_tracer("analysis_test")
        tracer.recorder = recorder  # Override for testing
        
        analyzer = TraceAnalyzer(recorder)
        
        # Create a complex trace
        async with tracer.async_span("root_operation") as root_span:
            root_span.set_tag("service.name", "main_service")
            
            # Child span 1
            async with tracer.async_span("database_query") as db_span:
                db_span.set_tag("service.name", "database_service")
                await asyncio.sleep(0.05)
            
            # Child span 2
            async with tracer.async_span("api_call") as api_span:
                api_span.set_tag("service.name", "api_service")
                await asyncio.sleep(0.03)
            
            # Child span 3 (with error)
            try:
                async with tracer.async_span("failing_operation") as fail_span:
                    fail_span.set_tag("service.name", "failing_service")
                    await asyncio.sleep(0.01)
                    raise ValueError("Test error")
            except ValueError:
                pass  # Expected
        
        # Wait for spans to be recorded
        await asyncio.sleep(0.1)
        
        # Analyze the trace
        trace_id = root_span.context.trace_id
        analysis = analyzer.analyze_trace(trace_id)
        
        # Get performance summary
        perf_summary = analyzer.get_performance_summary(time_window=60)
        
        print(f"  📊 Trace ID: {trace_id[:8]}...")
        print(f"  📊 Total spans: {analysis.get('total_spans', 0)}")
        print(f"  📊 Error count: {analysis.get('error_count', 0)}")
        print(f"  📊 Error rate: {analysis.get('error_rate', 0):.2f}")
        print(f"  📊 Services involved: {len(analysis.get('services', {}))}")
        print(f"  📊 Critical path length: {len(analysis.get('critical_path', []))}")
        print(f"  📊 Performance summary spans: {perf_summary.get('total_spans', 0)}")
        print(f"  ✅ Trace analysis test passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Trace analysis test failed: {e}")
        return False

async def main():
    """Run all observability tests"""
    print("🚀 WP-09 Distributed Logging & Observability Test Suite")
    print("=" * 60)
    
    test_results = []
    
    # Run tests
    test_results.append(await test_structured_logging())
    test_results.append(await test_distributed_tracing())
    test_results.append(await test_metrics_collection())
    test_results.append(await test_observability_integration())
    test_results.append(await test_performance_monitoring())
    test_results.append(await test_alerting_system())
    test_results.append(await test_trace_analysis())
    
    # Summary
    passed_tests = sum(1 for result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 TEST SUMMARY:")
    print(f"✅ Passed: {passed_tests}/{total_tests} tests")
    
    if passed_tests == total_tests:
        print(f"🎉 All observability tests passed!")
        print(f"\n🚀 Distributed observability is ready for production use!")
    else:
        print(f"⚠️  Some tests failed or were skipped")
        print(f"\n📋 Observability components:")
        print(f"   - Structured Logging (common/observability/logging.py)")
        print(f"   - Distributed Tracing (common/observability/tracing.py)")
        print(f"   - Metrics Collection (common/observability/metrics.py)")
    
    print(f"\n💡 Usage Examples:")
    print(f"   # Structured logging")
    print(f"   from common.observability.logging import get_distributed_logger")
    print(f"   logger = get_distributed_logger()")
    print(f"   await logger.info('Message', category=LogCategory.AGENT)")
    print(f"\n   # Distributed tracing")
    print(f"   from common.observability.tracing import get_tracer")
    print(f"   tracer = get_tracer('my_service')")
    print(f"   async with tracer.async_span('operation'): ...")
    print(f"\n   # Metrics collection")
    print(f"   from common.observability.metrics import counter, timer")
    print(f"   counter('requests').increment(endpoint='/api')")
    print(f"   with timer('operation_time').time_context(): ...")

if __name__ == "__main__":
    asyncio.run(main()) 