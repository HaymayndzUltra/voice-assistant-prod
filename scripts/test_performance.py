#!/usr/bin/env python3
"""
WP-04 Performance Test Suite
Tests async I/O, orjson performance, and caching improvements
"""

import asyncio
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, Any

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

from common.utils.async_io import AsyncIOManager
from common.pools.redis_pool import RedisConnectionPool

async def test_json_performance():
    """Test orjson vs json performance"""
    print("🧪 Testing JSON Performance...")
    
    # Test data
    test_data = {
        "users": [
            {"id": i, "name": f"User{i}", "data": {"value": i * 100, "active": i % 2 == 0}}
            for i in range(1000)
        ],
        "metadata": {
            "timestamp": time.time(),
            "version": "1.0.0",
            "nested": {"deep": {"very": {"data": list(range(100))}}}
        }
    }
    
    # Test json.dumps
    start_time = time.time()
    for _ in range(100):
        json.dumps(test_data)
    json_time = time.time() - start_time
    
    # Test orjson.dumps
    orjson_time = 0
    if ORJSON_AVAILABLE:
        start_time = time.time()
        for _ in range(100):
            orjson.dumps(test_data)
        orjson_time = time.time() - start_time
    
    print(f"  📊 json.dumps: {json_time:.4f}s")
    if ORJSON_AVAILABLE:
        print(f"  📊 orjson.dumps: {orjson_time:.4f}s")
        speedup = json_time / orjson_time if orjson_time > 0 else 0
        print(f"  ⚡ Speedup: {speedup:.2f}x faster")
    else:
        print("  ⚠️  orjson not available")

async def test_async_io_performance():
    """Test async I/O performance"""
    print("\n🧪 Testing Async I/O Performance...")
    
    async_manager = AsyncIOManager()
    
    # Create test files
    test_dir = Path(tempfile.mkdtemp())
    test_files = []
    
    # Generate test data
    for i in range(10):
        file_path = test_dir / f"test_file_{i}.txt"
        content = f"Test content {i}\n" * 1000
        test_files.append((file_path, content))
    
    # Test sync writing
    start_time = time.time()
    for file_path, content in test_files:
        with open(file_path, 'w') as f:
            f.write(content)
    sync_write_time = time.time() - start_time
    
    # Test async writing
    start_time = time.time()
    write_tasks = [
        async_manager.write_file_async(file_path, content)
        for file_path, content in test_files
    ]
    await asyncio.gather(*write_tasks)
    async_write_time = time.time() - start_time
    
    # Test sync reading
    start_time = time.time()
    for file_path, _ in test_files:
        with open(file_path, 'r') as f:
            f.read()
    sync_read_time = time.time() - start_time
    
    # Test async reading
    start_time = time.time()
    read_tasks = [
        async_manager.read_file_async(file_path)
        for file_path, _ in test_files
    ]
    await asyncio.gather(*read_tasks)
    async_read_time = time.time() - start_time
    
    print(f"  📊 Sync write: {sync_write_time:.4f}s")
    print(f"  📊 Async write: {async_write_time:.4f}s")
    print(f"  📊 Sync read: {sync_read_time:.4f}s")
    print(f"  📊 Async read: {async_read_time:.4f}s")
    
    write_speedup = sync_write_time / async_write_time if async_write_time > 0 else 0
    read_speedup = sync_read_time / async_read_time if async_read_time > 0 else 0
    
    print(f"  ⚡ Write speedup: {write_speedup:.2f}x")
    print(f"  ⚡ Read speedup: {read_speedup:.2f}x")
    
    # Cleanup
    for file_path, _ in test_files:
        file_path.unlink(missing_ok=True)
    test_dir.rmdir()

async def test_redis_cache_performance():
    """Test Redis caching performance"""
    print("\n🧪 Testing Redis Cache Performance...")
    
    try:
        redis_pool = RedisConnectionPool()
        
        # Test data
        test_data = {"key": f"value_{i}" for i in range(100)}
        
        # Test cache miss (fetch from source)
        start_time = time.time()
        for i in range(50):
            await redis_pool.get_cached(f"test_key_{i}", lambda: f"computed_value_{i}")
        cache_miss_time = time.time() - start_time
        
        # Test cache hit
        start_time = time.time()
        for i in range(50):
            await redis_pool.get_cached(f"test_key_{i}")
        cache_hit_time = time.time() - start_time
        
        print(f"  📊 Cache miss: {cache_miss_time:.4f}s")
        print(f"  📊 Cache hit: {cache_hit_time:.4f}s")
        
        speedup = cache_miss_time / cache_hit_time if cache_hit_time > 0 else 0
        print(f"  ⚡ Cache speedup: {speedup:.2f}x faster")
        
        # Test cache stats
        stats = redis_pool.get_pool_stats()
        print(f"  📈 Cache stats: {stats['cache_stats']}")
        
    except Exception as e:
        print(f"  ⚠️  Redis cache test failed: {e}")

async def main():
    """Run all performance tests"""
    print("🚀 WP-04 Performance Test Suite")
    print("=" * 50)
    
    await test_json_performance()
    await test_async_io_performance()
    await test_redis_cache_performance()
    
    print("\n🎉 Performance testing complete!")

if __name__ == "__main__":
    asyncio.run(main())
