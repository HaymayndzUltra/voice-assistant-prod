"""GPU resource management and VRAM allocation for ModelOps Coordinator."""

import time
import json
import psutil
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import redis

from .errors import GPUUnavailable, VRAMExhausted, ConfigurationError
from .telemetry import Telemetry
from .schemas import Config


@dataclass
class GPUInfo:
    """GPU information structure."""
    gpu_id: int
    name: str
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int
    utilization_percent: float
    temperature_celsius: int


@dataclass
class ModelAllocation:
    """Model VRAM allocation record."""
    model_name: str
    vram_mb: int
    allocated_at: datetime
    last_accessed: datetime
    access_count: int


class GPUManager:
    """GPU resource manager with VRAM allocation tracking."""
    
    def __init__(self, config: Config, telemetry: Telemetry):
        """Initialize GPU manager with configuration and telemetry."""
        self.config = config
        self.telemetry = telemetry
        self._lock = threading.RLock()
        self._stop_polling = threading.Event()
        self._polling_thread: Optional[threading.Thread] = None
        
        # Redis connection for allocation map
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            raise ConfigurationError("redis_connection", f"Failed to connect to Redis: {e}")
        
        # GPU state
        self._gpu_info: List[GPUInfo] = []
        self._allocations: Dict[str, ModelAllocation] = {}
        self._total_vram_mb = 0
        self._used_vram_mb = 0
        
        # Initialize GPU detection
        self._detect_gpus()
        self._start_polling()
    
    def _detect_gpus(self):
        """Detect available GPUs and their capabilities."""
        try:
            # Try to import GPUtil for GPU detection
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            self._gpu_info = []
            total_vram = 0
            
            for gpu in gpus:
                gpu_info = GPUInfo(
                    gpu_id=gpu.id,
                    name=gpu.name,
                    total_memory_mb=int(gpu.memoryTotal),
                    used_memory_mb=int(gpu.memoryUsed),
                    free_memory_mb=int(gpu.memoryFree),
                    utilization_percent=gpu.load * 100,
                    temperature_celsius=int(gpu.temperature) if gpu.temperature else 0
                )
                self._gpu_info.append(gpu_info)
                total_vram += gpu_info.total_memory_mb
            
            self._total_vram_mb = total_vram
            
        except ImportError:
            # Fallback: Mock GPU for development/testing
            mock_gpu = GPUInfo(
                gpu_id=0,
                name="Mock GPU",
                total_memory_mb=24000,  # 24GB mock GPU
                used_memory_mb=1000,
                free_memory_mb=23000,
                utilization_percent=5.0,
                temperature_celsius=45
            )
            self._gpu_info = [mock_gpu]
            self._total_vram_mb = mock_gpu.total_memory_mb
    
    def _start_polling(self):
        """Start GPU polling thread."""
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            name="GPU-Poller",
            daemon=True
        )
        self._polling_thread.start()
    
    def _polling_loop(self):
        """GPU polling loop to update metrics."""
        while not self._stop_polling.wait(self.config.resources.gpu_poll_interval):
            try:
                self._update_gpu_metrics()
                self._check_eviction_threshold()
            except Exception as e:
                self.telemetry.record_error("gpu_polling_error", "gpu_manager")
    
    def _update_gpu_metrics(self):
        """Update GPU metrics and telemetry."""
        with self._lock:
            total_used = 0
            total_free = 0
            avg_utilization = 0.0
            
            for i, gpu_info in enumerate(self._gpu_info):
                # Update GPU info (in production, would query actual GPU)
                if gpu_info.name != "Mock GPU":
                    try:
                        import GPUtil
                        gpu = GPUtil.getGPUs()[i]
                        gpu_info.used_memory_mb = int(gpu.memoryUsed)
                        gpu_info.free_memory_mb = int(gpu.memoryFree)
                        gpu_info.utilization_percent = gpu.load * 100
                        gpu_info.temperature_celsius = int(gpu.temperature) if gpu.temperature else 0
                    except:
                        pass  # Keep existing values on error
                
                total_used += gpu_info.used_memory_mb
                total_free += gpu_info.free_memory_mb
                avg_utilization += gpu_info.utilization_percent
            
            if self._gpu_info:
                avg_utilization /= len(self._gpu_info)
            
            self._used_vram_mb = total_used
            
            # Update telemetry
            self.telemetry.update_gpu_metrics(
                gpu_percent=avg_utilization,
                vram_used=total_used * 1024 * 1024,  # Convert to bytes
                vram_total=self._total_vram_mb * 1024 * 1024
            )
    
    def _check_eviction_threshold(self):
        """Check if VRAM usage exceeds eviction threshold."""
        if self._total_vram_mb == 0:
            return
        
        usage_percent = (self._used_vram_mb / self._total_vram_mb) * 100
        threshold = self.config.resources.eviction_threshold_pct
        
        if usage_percent > threshold:
            # Trigger eviction of least recently used models
            self._evict_lru_models(target_percent=threshold * 0.8)  # Evict to 80% of threshold
    
    def _evict_lru_models(self, target_percent: float):
        """Evict least recently used models to free VRAM."""
        target_vram_mb = (target_percent / 100.0) * self._total_vram_mb
        current_allocated = sum(alloc.vram_mb for alloc in self._allocations.values())
        
        if current_allocated <= target_vram_mb:
            return  # Already below target
        
        # Sort allocations by last access time (LRU first)
        sorted_allocs = sorted(
            self._allocations.items(),
            key=lambda x: x[1].last_accessed
        )
        
        freed_mb = 0
        for model_name, allocation in sorted_allocs:
            if current_allocated - freed_mb <= target_vram_mb:
                break
            
            # Free this model's allocation
            self._free_allocation(model_name)
            freed_mb += allocation.vram_mb
            
            self.telemetry.record_error("model_evicted", "gpu_manager")
    
    def allocate_vram(self, model_name: str, required_mb: int) -> bool:
        """
        Allocate VRAM for a model.
        
        Args:
            model_name: Name of the model
            required_mb: Required VRAM in MB
            
        Returns:
            True if allocation successful, False otherwise
            
        Raises:
            GPUUnavailable: If insufficient VRAM available
        """
        with self._lock:
            # Check if model already has allocation
            if model_name in self._allocations:
                allocation = self._allocations[model_name]
                allocation.last_accessed = datetime.utcnow()
                allocation.access_count += 1
                return True
            
            # Calculate available VRAM
            currently_allocated = sum(alloc.vram_mb for alloc in self._allocations.values())
            soft_limit_mb = self.config.resources.vram_soft_limit_mb
            available_mb = min(self._total_vram_mb, soft_limit_mb) - currently_allocated
            
            if required_mb > available_mb:
                # Try eviction to free space
                needed_space = required_mb - available_mb
                self._try_evict_for_space(needed_space)
                
                # Recalculate available space
                currently_allocated = sum(alloc.vram_mb for alloc in self._allocations.values())
                available_mb = min(self._total_vram_mb, soft_limit_mb) - currently_allocated
                
                if required_mb > available_mb:
                    raise GPUUnavailable(required_mb, available_mb)
            
            # Create allocation
            allocation = ModelAllocation(
                model_name=model_name,
                vram_mb=required_mb,
                allocated_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=1
            )
            
            self._allocations[model_name] = allocation
            
            # Store in Redis for persistence
            self._store_allocation_in_redis(allocation)
            
            return True
    
    def free_vram(self, model_name: str) -> int:
        """
        Free VRAM allocation for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Amount of VRAM freed in MB
        """
        with self._lock:
            return self._free_allocation(model_name)
    
    def _free_allocation(self, model_name: str) -> int:
        """Internal method to free allocation."""
        if model_name not in self._allocations:
            return 0
        
        allocation = self._allocations[model_name]
        freed_mb = allocation.vram_mb
        
        # Remove from memory and Redis
        del self._allocations[model_name]
        self._remove_allocation_from_redis(model_name)
        
        return freed_mb
    
    def _try_evict_for_space(self, needed_mb: int):
        """Try to evict models to free the specified amount of space."""
        # Sort by access patterns (least recently used first)
        candidates = sorted(
            self._allocations.items(),
            key=lambda x: (x[1].last_accessed, x[1].access_count)
        )
        
        freed_mb = 0
        for model_name, allocation in candidates:
            if freed_mb >= needed_mb:
                break
            
            freed_mb += self._free_allocation(model_name)
    
    def access_model(self, model_name: str):
        """Record model access for LRU tracking."""
        with self._lock:
            if model_name in self._allocations:
                allocation = self._allocations[model_name]
                allocation.last_accessed = datetime.utcnow()
                allocation.access_count += 1
                
                # Update Redis
                self._store_allocation_in_redis(allocation)
    
    def get_vram_usage(self) -> Dict[str, int]:
        """Get current VRAM usage summary."""
        with self._lock:
            total_allocated = sum(alloc.vram_mb for alloc in self._allocations.values())
            
            return {
                'total_vram_mb': self._total_vram_mb,
                'allocated_mb': total_allocated,
                'available_mb': self._total_vram_mb - total_allocated,
                'soft_limit_mb': self.config.resources.vram_soft_limit_mb,
                'usage_percent': (total_allocated / self._total_vram_mb * 100) if self._total_vram_mb > 0 else 0
            }
    
    def get_model_allocations(self) -> Dict[str, int]:
        """Get VRAM allocations per model."""
        with self._lock:
            return {name: alloc.vram_mb for name, alloc in self._allocations.items()}
    
    def get_gpu_info(self) -> List[GPUInfo]:
        """Get current GPU information."""
        with self._lock:
            return self._gpu_info.copy()
    
    def _store_allocation_in_redis(self, allocation: ModelAllocation):
        """Store allocation in Redis for persistence."""
        try:
            key = f"moc:allocation:{allocation.model_name}"
            data = {
                'vram_mb': allocation.vram_mb,
                'allocated_at': allocation.allocated_at.isoformat(),
                'last_accessed': allocation.last_accessed.isoformat(),
                'access_count': allocation.access_count
            }
            self.redis_client.setex(key, 86400, json.dumps(data))  # 24h TTL
        except Exception as e:
            self.telemetry.record_error("redis_store_error", "gpu_manager")
    
    def _remove_allocation_from_redis(self, model_name: str):
        """Remove allocation from Redis."""
        try:
            key = f"moc:allocation:{model_name}"
            self.redis_client.delete(key)
        except Exception as e:
            self.telemetry.record_error("redis_delete_error", "gpu_manager")
    
    def _load_allocations_from_redis(self):
        """Load existing allocations from Redis on startup."""
        try:
            pattern = "moc:allocation:*"
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                try:
                    data = json.loads(self.redis_client.get(key))
                    model_name = key.split(':')[-1]
                    
                    allocation = ModelAllocation(
                        model_name=model_name,
                        vram_mb=data['vram_mb'],
                        allocated_at=datetime.fromisoformat(data['allocated_at']),
                        last_accessed=datetime.fromisoformat(data['last_accessed']),
                        access_count=data['access_count']
                    )
                    
                    self._allocations[model_name] = allocation
                    
                except Exception as e:
                    # Skip corrupted entries
                    self.redis_client.delete(key)
                    
        except Exception as e:
            self.telemetry.record_error("redis_load_error", "gpu_manager")
    
    def shutdown(self):
        """Shutdown GPU manager and cleanup resources."""
        self._stop_polling.set()
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=5.0)
        
        # Clear Redis allocations
        try:
            pattern = "moc:allocation:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception:
            pass