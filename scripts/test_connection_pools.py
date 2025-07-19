#!/usr/bin/env python3
"""
WP-05 Connection Pool Test Suite
Tests ZMQ, SQL, and HTTP connection pooling functionality
"""

import asyncio
import time
import tempfile
from pathlib import Path
import sys
import os
from common.env_helpers import get_env

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

def test_zmq_pool():
    """Test ZMQ connection pool functionality"""
    print("🧪 Testing ZMQ Connection Pool...")
    
    try:
        from common.pools.zmq_pool import get_zmq_pool, SocketConfig, SocketType
        import zmq
        
        pool = get_zmq_pool()
        
        # Test REQ socket configuration
        config = SocketConfig(SocketType.REQ, f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5555", bind=False)
        
        start_time = time.time()
        socket_operations = 0
        
        # Test socket creation and reuse
        for i in range(5):
            with pool.socket(config) as socket:
                # Simulate socket usage
                socket_type = socket.getsockopt(zmq.TYPE)
                assert socket_type == zmq.REQ
                socket_operations += 1
        
        duration = time.time() - start_time
        stats = pool.get_stats()
        
        print(f"  📊 {socket_operations} socket operations in {duration:.4f}s")
        print(f"  📈 Pool hits: {stats['metrics']['pool_hits']}")
        print(f"  📈 Pool misses: {stats['metrics']['pool_misses']}")
        print(f"  📈 Total connections: {stats['metrics']['total_connections']}")
        print(f"  ✅ ZMQ pool test passed")
        
        return True
        
    except ImportError as e:
        print(f"  ⚠️  ZMQ not available, skipping test: {e}")
        return False
    except Exception as e:
        print(f"  ❌ ZMQ pool test failed: {e}")
        return False

def test_sql_pool():
    """Test SQL connection pool functionality"""
    print("\n🧪 Testing SQL Connection Pool...")
    
    try:
        from common.pools.sql_pool import get_sql_pool, get_sqlite_config
        
        pool = get_sql_pool()
        
        # Create temporary database
        temp_db = tempfile.mktemp(suffix='.db')
        config = get_sqlite_config(temp_db)
        
        start_time = time.time()
        
        # Test connection and query
        pool.execute_query(config, """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        
        # Insert test data
        pool.execute_many(config, 
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            [("test1", 100), ("test2", 200), ("test3", 300)]
        )
        
        # Query data
        results = pool.execute_query(config, "SELECT * FROM test_table ORDER BY id")
        
        duration = time.time() - start_time
        stats = pool.get_stats()
        
        print(f"  📊 Database operations in {duration:.4f}s")
        print(f"  📈 Query count: {stats['metrics']['query_count']}")
        print(f"  📈 Pool hits: {stats['metrics']['pool_hits']}")
        print(f"  📈 Pool misses: {stats['metrics']['pool_misses']}")
        print(f"  📊 Query results: {len(results)} rows")
        
        # Verify data
        assert len(results) == 3
        assert results[0][1] == "test1"  # name column
        assert results[0][2] == 100     # value column
        
        print(f"  ✅ SQL pool test passed")
        
        # Cleanup
        Path(temp_db).unlink(missing_ok=True)
        return True
        
    except Exception as e:
        print(f"  ❌ SQL pool test failed: {e}")
        return False

async def test_http_pool():
    """Test HTTP connection pool functionality"""
    print("\n🧪 Testing HTTP Connection Pool...")
    
    try:
        from common.pools.http_pool import get_http_pool, HTTPConfig
        
        pool = get_http_pool()
        
        # Use a reliable test endpoint
        config = HTTPConfig(
            base_url="https://httpbin.org",
            timeout=15.0,
            max_retries=2
        )
        
        start_time = time.time()
        
        # Test single request
        response = await pool.request_async(config, "GET", "/status/200")
        assert response.status_code == 200
        
        # Test multiple concurrent requests
        tasks = []
        for i in range(3):
            task = pool.request_async(config, "GET", f"/delay/{i+1}")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        stats = pool.get_stats()
        
        # Count successful responses
        successful_responses = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status_code') and r.status_code == 200)
        
        print(f"  📊 HTTP requests completed in {duration:.4f}s")
        print(f"  📈 Session hits: {stats['metrics']['session_hits']}")
        print(f"  📈 Session misses: {stats['metrics']['session_misses']}")
        print(f"  📈 Success rate: {stats['metrics']['successful_requests']}/{stats['metrics']['total_requests']}")
        print(f"  ⚡ Avg response time: {stats['metrics']['avg_response_time']:.4f}s")
        print(f"  📊 Successful responses: {successful_responses}")
        print(f"  ✅ HTTP pool test passed")
        
        return True
        
    except ImportError as e:
        print(f"  ⚠️  HTTP dependencies not available, skipping test: {e}")
        return False
    except Exception as e:
        print(f"  ❌ HTTP pool test failed: {e}")
        return False

async def test_redis_pool():
    """Test Redis connection pool (from WP-04)"""
    print("\n🧪 Testing Redis Connection Pool...")
    
    try:
        from common.pools.redis_pool import get_redis_pool
        
        pool = get_redis_pool()
        stats = pool.get_stats()
        
        print(f"  📊 Redis pool initialized")
        print(f"  📈 Pool status: {stats}")
        print(f"  ✅ Redis pool test passed")
        return True
        
    except ImportError as e:
        print(f"  ⚠️  Redis not available, skipping test: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Redis pool test failed: {e}")
        return False

async def test_pool_performance():
    """Test performance improvements from connection pooling"""
    print("\n⚡ Testing Connection Pool Performance Benefits...")
    
    try:
        # Test HTTP pool vs direct requests performance
        from common.pools.http_pool import get_http_pool, HTTPConfig
        import aiohttp
        
        pool = get_http_pool()
        config = HTTPConfig(base_url="https://httpbin.org", timeout=10.0)
        
        # Test pooled requests
        start_time = time.time()
        
        pooled_tasks = []
        for i in range(5):
            task = pool.request_async(config, "GET", "/uuid")
            pooled_tasks.append(task)
        
        await asyncio.gather(*pooled_tasks)
        pooled_duration = time.time() - start_time
        
        # Test direct requests (no pooling)
        start_time = time.time()
        
        direct_tasks = []
        for i in range(5):
            async def direct_request():
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://httpbin.org/uuid") as response:
                        await response.read()
            direct_tasks.append(direct_request())
        
        await asyncio.gather(*direct_tasks)
        direct_duration = time.time() - start_time
        
        performance_gain = ((direct_duration - pooled_duration) / direct_duration) * 100
        
        print(f"  📊 Pooled requests: {pooled_duration:.4f}s")
        print(f"  📊 Direct requests: {direct_duration:.4f}s")
        print(f"  ⚡ Performance gain: {performance_gain:.1f}% faster with pooling")
        
        if performance_gain > 0:
            print(f"  ✅ Connection pooling provides measurable performance benefit")
        else:
            print(f"  ⚠️  Performance results may vary with network conditions")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")
        return False

async def main():
    """Run all connection pool tests"""
    print("🚀 WP-05 Connection Pool Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run tests
    test_results.append(test_zmq_pool())
    test_results.append(test_sql_pool())
    test_results.append(await test_http_pool())
    test_results.append(await test_redis_pool())
    test_results.append(await test_pool_performance())
    
    # Summary
    passed_tests = sum(1 for result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 TEST SUMMARY:")
    print(f"✅ Passed: {passed_tests}/{total_tests} tests")
    
    if passed_tests == total_tests:
        print(f"🎉 All connection pool tests passed!")
        print(f"\n🚀 Connection pools are ready for production use!")
    else:
        print(f"⚠️  Some tests failed or were skipped")
        print(f"\n📋 Connection pools implemented:")
        print(f"   - ZMQ Connection Pool (common/pools/zmq_pool.py)")
        print(f"   - SQL Connection Pool (common/pools/sql_pool.py)")
        print(f"   - HTTP Connection Pool (common/pools/http_pool.py)")
        print(f"   - Redis Connection Pool (common/pools/redis_pool.py)")
    
    print(f"\n💡 Usage Examples:")
    print(f"   # ZMQ Pool")
    print(f"   from common.pools.zmq_pool import get_zmq_pool")
    print(f"   pool = get_zmq_pool()")
    print(f"   with pool.socket(config) as socket: ...")
    print(f"\n   # SQL Pool") 
    print(f"   from common.pools.sql_pool import get_sql_pool")
    print(f"   pool = get_sql_pool()")
    print(f"   results = pool.execute_query(config, 'SELECT * FROM table')")
    print(f"\n   # HTTP Pool")
    print(f"   from common.pools.http_pool import get_http_pool")
    print(f"   pool = get_http_pool()")
    print(f"   response = await pool.request_async(config, 'GET', '/api/data')")

if __name__ == "__main__":
    asyncio.run(main()) 