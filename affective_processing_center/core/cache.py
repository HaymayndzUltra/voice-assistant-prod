"""Feature cache implementation for emotion processing optimization."""

import hashlib
import time
from typing import Dict, List, Optional, Any, Union
from collections import OrderedDict
from datetime import datetime, timedelta
import threading
import logging

from .schemas import CacheEntry, Payload, AudioChunk, Transcript

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    LRU (Least Recently Used) cache for storing and retrieving emotion features.
    Thread-safe implementation with automatic cleanup and memory management.
    """
    
    def __init__(
        self, 
        max_size: int = 1000,
        ttl_minutes: int = 60,
        auto_cleanup_interval: int = 300  # 5 minutes
    ):
        """
        Initialize the embedding cache.
        
        Args:
            max_size: Maximum number of entries to store
            ttl_minutes: Time-to-live for entries in minutes
            auto_cleanup_interval: Automatic cleanup interval in seconds
        """
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.auto_cleanup_interval = auto_cleanup_interval
        
        # Thread-safe ordered dictionary for LRU behavior
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanup_runs': 0
        }
        
        # Start automatic cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._periodic_cleanup, 
            daemon=True,
            name="EmbeddingCache-Cleanup"
        )
        self._cleanup_thread.start()
        
        logger.info(f"EmbeddingCache initialized: max_size={max_size}, ttl={ttl_minutes}min")
    
    def _generate_key(self, payload: Payload, module_name: str) -> str:
        """
        Generate a unique cache key for the given payload and module.
        
        Args:
            payload: Input payload (AudioChunk or Transcript)
            module_name: Name of the processing module
            
        Returns:
            Unique cache key string
        """
        if isinstance(payload, AudioChunk):
            # For audio, hash the audio data + sample rate + module
            content = payload.data + str(payload.sample_rate).encode() + module_name.encode()
        elif isinstance(payload, Transcript):
            # For text, hash the text content + module
            content = payload.text.encode('utf-8') + module_name.encode()
        else:
            raise ValueError(f"Unsupported payload type: {type(payload)}")
        
        # Create SHA-256 hash for deterministic key generation
        key_hash = hashlib.sha256(content).hexdigest()
        return f"{module_name}:{key_hash[:16]}"  # Use first 16 chars for readability
    
    def get(self, payload: Payload, module_name: str) -> Optional[List[float]]:
        """
        Retrieve cached features for the given payload and module.
        
        Args:
            payload: Input payload to look up
            module_name: Processing module name
            
        Returns:
            Cached feature vector or None if not found
        """
        key = self._generate_key(payload, module_name)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            # Check if entry has expired
            if datetime.utcnow() - entry.timestamp > self.ttl:
                del self._cache[key]
                self._stats['misses'] += 1
                logger.debug(f"Cache entry expired: {key}")
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            # Update access statistics
            entry.access_count += 1
            self._stats['hits'] += 1
            
            logger.debug(f"Cache hit: {key} (access_count={entry.access_count})")
            return entry.features.copy()  # Return copy to prevent mutation
    
    def put(self, payload: Payload, module_name: str, features: List[float]) -> None:
        """
        Store features in the cache for the given payload and module.
        
        Args:
            payload: Input payload
            module_name: Processing module name
            features: Feature vector to cache
        """
        key = self._generate_key(payload, module_name)
        
        with self._lock:
            # Create new cache entry
            entry = CacheEntry(
                key=key,
                features=features.copy(),  # Store copy to prevent mutation
                timestamp=datetime.utcnow(),
                access_count=1
            )
            
            # Add to cache
            self._cache[key] = entry
            self._cache.move_to_end(key)  # Mark as most recently used
            
            # Evict oldest entries if over capacity
            while len(self._cache) > self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)  # Remove oldest (first)
                self._stats['evictions'] += 1
                logger.debug(f"Cache eviction: {oldest_key}")
            
            logger.debug(f"Cache store: {key} (features_len={len(features)})")
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {cleared_count} entries removed")
    
    def size(self) -> int:
        """Get current number of entries in cache."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests) if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'cleanup_runs': self._stats['cleanup_runs'],
                'ttl_minutes': self.ttl.total_seconds() / 60
            }
    
    def _periodic_cleanup(self) -> None:
        """Background thread for periodic cache cleanup."""
        while True:
            try:
                time.sleep(self.auto_cleanup_interval)
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from the cache."""
        with self._lock:
            current_time = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time - entry.timestamp > self.ttl
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self._stats['cleanup_runs'] += 1
                logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Estimate memory usage of the cache.
        
        Returns:
            Memory usage statistics in MB
        """
        with self._lock:
            total_features = sum(len(entry.features) for entry in self._cache.values())
            
            # Rough estimate: each float is 8 bytes, plus overhead
            features_mb = (total_features * 8) / (1024 * 1024)
            overhead_mb = len(self._cache) * 0.001  # Estimate 1KB overhead per entry
            
            return {
                'features_mb': features_mb,
                'overhead_mb': overhead_mb,
                'total_mb': features_mb + overhead_mb,
                'entries': len(self._cache)
            }
    
    def __len__(self) -> int:
        """Get number of entries in cache."""
        return self.size()
    
    def __contains__(self, payload_and_module: tuple) -> bool:
        """Check if payload and module combination exists in cache."""
        payload, module_name = payload_and_module
        key = self._generate_key(payload, module_name)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            # Check expiration
            return datetime.utcnow() - entry.timestamp <= self.ttl