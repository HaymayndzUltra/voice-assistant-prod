"""
WP-04 Async I/O Utilities
High-performance async file operations and data processing
"""

import asyncio
import aiofiles
import aiofiles.os
import json
import orjson
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
import logging
from pathlib import Path
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import functools

logger = logging.getLogger(__name__)

@dataclass
class IOMetrics:
    """I/O operation metrics for performance monitoring"""
    operation: str
    file_path: str
    size_bytes: int
    duration_ms: float
    success: bool
    error: Optional[str] = None

class AsyncIOManager:
    """High-performance async I/O manager with caching and metrics"""
    
    def __init__(self, 
                 max_workers: int = 4,
                 enable_metrics: bool = True,
                 cache_enabled: bool = True):
        self.max_workers = max_workers
        self.enable_metrics = enable_metrics
        self.cache_enabled = cache_enabled
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Metrics storage
        self.metrics: List[IOMetrics] = []
        self.metrics_lock = asyncio.Lock()
        
        # File content cache
        self._file_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()
        
        logger.info(f"AsyncIOManager initialized - max_workers: {max_workers}")
    
    async def read_file_async(self, 
                             file_path: Union[str, Path], 
                             encoding: str = 'utf-8',
                             use_cache: bool = True) -> str:
        """Async file reading with caching and metrics"""
        path_str = str(file_path)
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache and self.cache_enabled:
                cached_content = await self._get_cached_file(path_str)
                if cached_content is not None:
                    await self._record_metric("read_file_cached", path_str, 
                                            len(cached_content), time.time() - start_time, True)
                    return cached_content
            
            # Read file asynchronously
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            # Cache the content
            if use_cache and self.cache_enabled:
                await self._cache_file(path_str, content)
            
            # Record metrics
            await self._record_metric("read_file", path_str, 
                                    len(content), time.time() - start_time, True)
            
            return content
            
        except Exception as e:
            await self._record_metric("read_file", path_str, 
                                    0, time.time() - start_time, False, str(e))
            raise
    
    async def write_file_async(self, 
                              file_path: Union[str, Path], 
                              content: str,
                              encoding: str = 'utf-8',
                              create_dirs: bool = True) -> bool:
        """Async file writing with directory creation and metrics"""
        path_str = str(file_path)
        start_time = time.time()
        
        try:
            # Create directories if needed
            if create_dirs:
                path_obj = Path(file_path)
                if path_obj.parent != path_obj:
                    await aiofiles.os.makedirs(path_obj.parent, exist_ok=True)
            
            # Write file asynchronously
            async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            # Update cache
            if self.cache_enabled:
                await self._cache_file(path_str, content)
            
            # Record metrics
            await self._record_metric("write_file", path_str, 
                                    len(content), time.time() - start_time, True)
            
            return True
            
        except Exception as e:
            await self._record_metric("write_file", path_str, 
                                    len(content), time.time() - start_time, False, str(e))
            raise
    
    async def read_json_async(self, 
                             file_path: Union[str, Path],
                             use_orjson: bool = True,
                             use_cache: bool = True) -> Dict[str, Any]:
        """Async JSON reading with orjson optimization"""
        path_str = str(file_path)
        start_time = time.time()
        
        try:
            # Read file content
            content = await self.read_file_async(file_path, use_cache=use_cache)
            
            # Parse JSON
            if use_orjson:
                data = orjson.loads(content)
            else:
                data = json.loads(content)
            
            await self._record_metric("read_json", path_str, 
                                    len(content), time.time() - start_time, True)
            
            return data
            
        except Exception as e:
            await self._record_metric("read_json", path_str, 
                                    0, time.time() - start_time, False, str(e))
            raise
    
    async def write_json_async(self, 
                              file_path: Union[str, Path], 
                              data: Dict[str, Any],
                              use_orjson: bool = True,
                              indent: Optional[int] = None,
                              create_dirs: bool = True) -> bool:
        """Async JSON writing with orjson optimization"""
        path_str = str(file_path)
        start_time = time.time()
        
        try:
            # Serialize JSON
            if use_orjson:
                if indent:
                    content = orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()
                else:
                    content = orjson.dumps(data).decode()
            else:
                content = json.dumps(data, indent=indent)
            
            # Write file
            await self.write_file_async(file_path, content, create_dirs=create_dirs)
            
            await self._record_metric("write_json", path_str, 
                                    len(content), time.time() - start_time, True)
            
            return True
            
        except Exception as e:
            await self._record_metric("write_json", path_str, 
                                    0, time.time() - start_time, False, str(e))
            raise
    
    async def read_lines_async(self, 
                              file_path: Union[str, Path],
                              max_lines: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Async line-by-line file reading generator"""
        path_str = str(file_path)
        start_time = time.time()
        lines_read = 0
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                async for line in f:
                    if max_lines and lines_read >= max_lines:
                        break
                    yield line.rstrip('\n\r')
                    lines_read += 1
            
            await self._record_metric("read_lines", path_str, 
                                    lines_read, time.time() - start_time, True)
            
        except Exception as e:
            await self._record_metric("read_lines", path_str, 
                                    lines_read, time.time() - start_time, False, str(e))
            raise
    
    async def batch_process_files(self, 
                                 file_paths: List[Union[str, Path]],
                                 process_func: Callable,
                                 batch_size: int = 10,
                                 max_concurrent: int = 5) -> List[Any]:
        """Batch process multiple files with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def process_file(file_path):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(process_func):
                        return await process_func(file_path)
                    else:
                        # Run sync function in thread pool
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(self.executor, process_func, file_path)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    return None
        
        # Process files in batches
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            batch_tasks = [process_file(fp) for fp in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    async def file_exists_async(self, file_path: Union[str, Path]) -> bool:
        """Async file existence check"""
        try:
            return await aiofiles.os.path.exists(file_path)
        except Exception:
            return False
    
    async def get_file_size_async(self, file_path: Union[str, Path]) -> int:
        """Async file size retrieval"""
        try:
            stat_result = await aiofiles.os.stat(file_path)
            return stat_result.st_size
        except Exception:
            return 0
    
    async def copy_file_async(self, 
                             src_path: Union[str, Path], 
                             dst_path: Union[str, Path],
                             create_dirs: bool = True) -> bool:
        """Async file copy with directory creation"""
        try:
            if create_dirs:
                dst_dir = Path(dst_path).parent
                await aiofiles.os.makedirs(dst_dir, exist_ok=True)
            
            # Read source and write to destination
            content = await self.read_file_async(src_path, use_cache=False)
            await self.write_file_async(dst_path, content, create_dirs=False)
            
            return True
        except Exception as e:
            logger.error(f"Error copying {src_path} to {dst_path}: {e}")
            return False
    
    async def _get_cached_file(self, file_path: str) -> Optional[str]:
        """Get file content from cache if available and fresh"""
        async with self._cache_lock:
            if file_path in self._file_cache:
                cache_entry = self._file_cache[file_path]
                
                # Check if file has been modified
                try:
                    stat_result = await aiofiles.os.stat(file_path)
                    if stat_result.st_mtime <= cache_entry['mtime']:
                        return cache_entry['content']
                except Exception:
                    pass
                
                # Remove stale cache entry
                del self._file_cache[file_path]
        
        return None
    
    async def _cache_file(self, file_path: str, content: str) -> None:
        """Cache file content with modification time"""
        if not self.cache_enabled:
            return
        
        try:
            stat_result = await aiofiles.os.stat(file_path)
            async with self._cache_lock:
                self._file_cache[file_path] = {
                    'content': content,
                    'mtime': stat_result.st_mtime,
                    'cached_at': time.time()
                }
        except Exception:
            pass
    
    async def _record_metric(self, 
                            operation: str, 
                            file_path: str, 
                            size_bytes: int, 
                            duration_s: float, 
                            success: bool, 
                            error: Optional[str] = None) -> None:
        """Record I/O operation metrics"""
        if not self.enable_metrics:
            return
        
        metric = IOMetrics(
            operation=operation,
            file_path=file_path,
            size_bytes=size_bytes,
            duration_ms=duration_s * 1000,
            success=success,
            error=error
        )
        
        async with self.metrics_lock:
            self.metrics.append(metric)
            
            # Keep only last 1000 metrics to prevent memory growth
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get I/O metrics summary"""
        async with self.metrics_lock:
            if not self.metrics:
                return {}
            
            operations = {}
            total_operations = len(self.metrics)
            successful_operations = sum(1 for m in self.metrics if m.success)
            
            for metric in self.metrics:
                if metric.operation not in operations:
                    operations[metric.operation] = {
                        'count': 0,
                        'total_duration_ms': 0,
                        'total_bytes': 0,
                        'success_count': 0
                    }
                
                op_stats = operations[metric.operation]
                op_stats['count'] += 1
                op_stats['total_duration_ms'] += metric.duration_ms
                op_stats['total_bytes'] += metric.size_bytes
                if metric.success:
                    op_stats['success_count'] += 1
            
            # Calculate averages
            for op_stats in operations.values():
                op_stats['avg_duration_ms'] = op_stats['total_duration_ms'] / op_stats['count']
                op_stats['avg_bytes'] = op_stats['total_bytes'] / op_stats['count']
                op_stats['success_rate'] = op_stats['success_count'] / op_stats['count']
            
            return {
                'total_operations': total_operations,
                'success_rate': successful_operations / total_operations,
                'cache_size': len(self._file_cache),
                'operations': operations
            }
    
    async def clear_cache(self) -> None:
        """Clear file content cache"""
        async with self._cache_lock:
            self._file_cache.clear()
    
    def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)


# Global async I/O manager instance
_async_io_manager: Optional[AsyncIOManager] = None

def get_async_io_manager() -> AsyncIOManager:
    """Get global async I/O manager"""
    global _async_io_manager
    if _async_io_manager is None:
        _async_io_manager = AsyncIOManager()
    return _async_io_manager

# Convenience functions
async def read_file_async(file_path: Union[str, Path], **kwargs) -> str:
    """Async file reading convenience function"""
    manager = get_async_io_manager()
    return await manager.read_file_async(file_path, **kwargs)

async def write_file_async(file_path: Union[str, Path], content: str, **kwargs) -> bool:
    """Async file writing convenience function"""
    manager = get_async_io_manager()
    return await manager.write_file_async(file_path, content, **kwargs)

async def read_json_async(file_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
    """Async JSON reading convenience function"""
    manager = get_async_io_manager()
    return await manager.read_json_async(file_path, **kwargs)

async def write_json_async(file_path: Union[str, Path], data: Dict[str, Any], **kwargs) -> bool:
    """Async JSON writing convenience function"""
    manager = get_async_io_manager()
    return await manager.write_json_async(file_path, data, **kwargs) 