#!/usr/bin/env python3
"""
Intelligent Query Optimizer - Advanced Database Query Optimization
Provides intelligent query optimization with caching, rewriting, and performance analysis.

Features:
- Intelligent query caching with TTL and invalidation
- Query plan analysis and optimization suggestions
- Automatic query rewriting for performance
- Result set caching with smart invalidation
- Query performance prediction and routing
- Index usage analysis and recommendations
"""
from __future__ import annotations
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
import json
import logging
import hashlib
import threading
import pickle
import gzip
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque, OrderedDict
from enum import Enum
import re

# Core imports
from common.core.base_agent import BaseAgent

# Database imports
from main_pc_code.database.async_connection_pool import (
    get_connection_pool
)

# Event system imports
from events.memory_events import (
    MemoryEventType, create_cache_event,
    CacheEvictionPolicy
)
from events.event_bus import publish_memory_event

class CacheStrategy(Enum):
    """Query caching strategies"""
    NO_CACHE = "no_cache"
    TTL_BASED = "ttl_based"
    INVALIDATION_BASED = "invalidation_based"
    ADAPTIVE = "adaptive"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"

class OptimizationLevel(Enum):
    """Query optimization levels"""
    NONE = "none"
    BASIC = "basic"
    AGGRESSIVE = "aggressive"
    EXPERIMENTAL = "experimental"

class QueryComplexity(Enum):
    """Query complexity classification"""
    SIMPLE = "simple"      # Single table, simple conditions
    MODERATE = "moderate"  # Joins, subqueries
    COMPLEX = "complex"    # Multiple joins, aggregations
    VERY_COMPLEX = "very_complex"  # Complex analytics, CTEs

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    compression_ratio: float = 1.0
    tags: Set[str] = field(default_factory=set)
    
    @property
    def is_expired(self) -> bool:
        if not self.ttl_seconds:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.now()
        self.access_count += 1

@dataclass
class QueryPlan:
    """Query execution plan analysis"""
    query_hash: str
    estimated_cost: float
    estimated_rows: int
    execution_time_ms: float
    index_usage: List[str]
    table_scans: List[str]
    join_operations: List[str]
    optimization_suggestions: List[str] = field(default_factory=list)
    complexity: QueryComplexity = QueryComplexity.SIMPLE

@dataclass
class QueryOptimizationRule:
    """Query optimization rule"""
    name: str
    pattern: str  # Regex pattern to match
    replacement: str
    description: str
    enabled: bool = True
    performance_impact: float = 0.0  # Expected performance improvement (%)

@dataclass
class CacheConfiguration:
    """Cache configuration settings"""
    max_size_mb: int = 512
    max_entries: int = 10000
    default_ttl_seconds: float = 3600  # 1 hour
    compression_enabled: bool = True
    compression_threshold_bytes: int = 1024  # 1KB
    eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU
    hit_ratio_target: float = 0.8  # 80% hit ratio target

class IntelligentQueryOptimizer(BaseAgent):
    """
    Intelligent Query Optimizer with advanced caching and optimization.
    
    Provides comprehensive query optimization including caching,
    rewriting, performance analysis, and intelligent routing.
    """
    
    def __init__(self, 
                 cache_config: Optional[CacheConfiguration] = None,
                 optimization_level: OptimizationLevel = OptimizationLevel.AGGRESSIVE,
                 enable_query_rewriting: bool = True,
                 **kwargs):
        super().__init__(name="IntelligentQueryOptimizer", **kwargs)
        
        # Configuration
        self.cache_config = cache_config or CacheConfiguration()
        self.optimization_level = optimization_level
        self.enable_query_rewriting = enable_query_rewriting
        
        # Query cache
        self.query_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size_bytes': 0,
            'compression_savings_bytes': 0
        }
        
        # Query optimization
        self.optimization_rules: List[QueryOptimizationRule] = []
        self.query_plans: Dict[str, QueryPlan] = {}
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Analysis and monitoring
        self.slow_query_threshold_ms = 1000.0
        self.optimization_suggestions: Dict[str, List[str]] = defaultdict(list)
        self.table_access_patterns: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Index recommendations
        self.index_candidates: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.missing_indexes: Set[str] = set()
        
        # Cache invalidation
        self.table_dependencies: Dict[str, Set[str]] = defaultdict(set)  # table -> cache_keys
        self.cache_invalidation_queue: deque = deque()
        
        # Initialize components
        self._initialize_optimization_rules()
        self._start_background_tasks()
        
        self.logger.info(f"Intelligent Query Optimizer initialized: {optimization_level.value} level")
    
    def _initialize_optimization_rules(self) -> None:
        """Initialize query optimization rules"""
        rules = [
            QueryOptimizationRule(
                name="remove_unnecessary_distinct",
                pattern=r"SELECT\s+DISTINCT\s+(.+?)\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*(.+)",
                replacement=r"SELECT \1 FROM \2 WHERE \3 = \4",
                description="Remove DISTINCT when WHERE clause ensures uniqueness",
                performance_impact=15.0
            ),
            QueryOptimizationRule(
                name="optimize_count_queries",
                pattern=r"SELECT\s+COUNT\(\*\)\s+FROM\s+(\w+)\s*$",
                replacement=r"SELECT reltuples::bigint FROM pg_class WHERE relname = '\1'",
                description="Use pg_class for approximate counts on large tables",
                performance_impact=80.0
            ),
            QueryOptimizationRule(
                name="limit_subqueries",
                pattern=r"SELECT\s+.+?\s+WHERE\s+\w+\s+IN\s*\(\s*SELECT\s+.+?\s+FROM\s+\w+\s*\)",
                replacement=r"",  # Complex replacement - would need actual implementation
                description="Convert IN subqueries to JOINs when possible",
                performance_impact=25.0
            ),
            QueryOptimizationRule(
                name="optimize_like_patterns",
                pattern=r"WHERE\s+(\w+)\s+LIKE\s+'(.+?)%'",
                replacement=r"WHERE \1 >= '\2' AND \1 < '\2\377'",
                description="Convert LIKE patterns to range queries when possible",
                performance_impact=30.0
            ),
            QueryOptimizationRule(
                name="add_limit_to_exists",
                pattern=r"WHERE\s+EXISTS\s*\(\s*SELECT\s+.+?\s+FROM\s+.+?\)",
                replacement=r"WHERE EXISTS (SELECT 1 FROM ... LIMIT 1)",
                description="Add LIMIT 1 to EXISTS subqueries",
                performance_impact=10.0
            )
        ]
        
        self.optimization_rules.extend(rules)
        self.logger.info(f"Loaded {len(self.optimization_rules)} optimization rules")
    
    def _start_background_tasks(self) -> None:
        """Start background optimization tasks"""
        # Cache maintenance thread
        cache_thread = threading.Thread(target=self._cache_maintenance_loop, daemon=True)
        cache_thread.start()
        
        # Performance analysis thread
        analysis_thread = threading.Thread(target=self._performance_analysis_loop, daemon=True)
        analysis_thread.start()
        
        # Index recommendation thread
        index_thread = threading.Thread(target=self._index_recommendation_loop, daemon=True)
        index_thread.start()
    
    def _cache_maintenance_loop(self) -> None:
        """Background cache maintenance"""
        while self.running:
            try:
                self._cleanup_expired_cache()
                self._enforce_cache_limits()
                self._update_cache_statistics()
                
                time.sleep(60)  # Maintenance every minute
                
            except Exception as e:
                self.logger.error(f"Cache maintenance error: {e}")
                time.sleep(120)
    
    def _performance_analysis_loop(self) -> None:
        """Background performance analysis"""
        while self.running:
            try:
                self._analyze_query_patterns()
                self._generate_optimization_suggestions()
                self._update_table_access_patterns()
                
                time.sleep(300)  # Analysis every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Performance analysis error: {e}")
                time.sleep(600)
    
    def _index_recommendation_loop(self) -> None:
        """Background index recommendation analysis"""
        while self.running:
            try:
                self._analyze_missing_indexes()
                self._generate_index_recommendations()
                
                time.sleep(600)  # Index analysis every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Index recommendation error: {e}")
                time.sleep(1200)
    
    async def optimize_query(self, query: str, parameters: Optional[List] = None, 
                           cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE) -> Tuple[str, Optional[List]]:
        """
        Optimize a query with caching and rewriting
        
        Returns: (optimized_query, optimized_parameters)
        """
        original_query = query
        
        # 1. Query normalization
        normalized_query = self._normalize_query(query)
        query_hash = self._hash_query(normalized_query)
        
        # 2. Check cache first
        cached_result = await self._get_cached_result(query_hash, cache_strategy)
        if cached_result is not None:
            self.logger.debug(f"Cache hit for query: {query[:100]}...")
            return original_query, parameters  # Return original since we have cached result
        
        # 3. Apply query rewriting rules
        optimized_query = query
        if self.enable_query_rewriting and self.optimization_level != OptimizationLevel.NONE:
            optimized_query = self._apply_optimization_rules(query)
        
        # 4. Analyze query complexity
        complexity = self._analyze_query_complexity(optimized_query)
        
        # 5. Generate execution plan recommendations
        if self.optimization_level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.EXPERIMENTAL]:
            plan = await self._analyze_query_plan(optimized_query, parameters)
            if plan:
                self.query_plans[query_hash] = plan
                
                # Apply plan-based optimizations
                further_optimized = self._apply_plan_optimizations(optimized_query, plan)
                if further_optimized != optimized_query:
                    optimized_query = further_optimized
                    self.logger.info(f"Plan-based optimization applied: {query[:50]}...")
        
        # 6. Record query for future analysis
        self._record_query_optimization(query_hash, original_query, optimized_query, complexity)
        
        return optimized_query, parameters
    
    async def execute_optimized_query(self, query: str, parameters: Optional[List] = None,
                                    cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                                    fetch_type: str = "fetch") -> Any:
        """
        Execute an optimized query with intelligent caching
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            cache_strategy: Caching strategy to use
            fetch_type: 'execute', 'fetch', 'fetchval', 'fetchrow'
        """
        start_time = time.time()
        
        # 1. Optimize the query
        optimized_query, optimized_params = await self.optimize_query(query, parameters, cache_strategy)
        
        # 2. Check cache
        query_hash = self._hash_query(self._normalize_query(query))
        cache_key = self._generate_cache_key(query_hash, parameters)
        
        cached_result = await self._get_cached_result(cache_key, cache_strategy)
        if cached_result is not None:
            self._record_cache_hit(cache_key)
            return cached_result
        
        # 3. Execute query
        pool = get_connection_pool()
        
        try:
            if fetch_type == "execute":
                result = await pool.execute_query(optimized_query, *(optimized_params or []))
            elif fetch_type == "fetch":
                result = await pool.fetch_query(optimized_query, *(optimized_params or []))
            elif fetch_type == "fetchval":
                result = await pool.fetchval_query(optimized_query, *(optimized_params or []))
            elif fetch_type == "fetchrow":
                result = await pool.fetchrow_query(optimized_query, *(optimized_params or []))
            else:
                raise ValueError(f"Unsupported fetch_type: {fetch_type}")
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # 4. Cache result if appropriate
            if self._should_cache_result(query, result, execution_time_ms, cache_strategy):
                await self._cache_result(cache_key, result, query, cache_strategy)
            
            # 5. Record performance metrics
            self._record_query_performance(query_hash, execution_time_ms, len(str(result)) if result else 0)
            
            self.logger.debug(f"Optimized query executed in {execution_time_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._record_cache_miss(cache_key)
            self.logger.error(f"Optimized query execution failed: {e}")
            raise
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent caching and analysis"""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Convert to lowercase for analysis (but preserve original case)
        # This is mainly for pattern matching
        return normalized
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query identification"""
        # Create a normalized version for hashing
        normalized = query.lower().strip()
        # Remove parameter placeholders for pattern matching
        normalized = re.sub(r'\$\d+', '?', normalized)
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _generate_cache_key(self, query_hash: str, parameters: Optional[List] = None) -> str:
        """Generate cache key including parameters"""
        if parameters:
            param_hash = hashlib.md5(str(parameters).encode()).hexdigest()[:8]
            return f"{query_hash}_{param_hash}"
        return query_hash
    
    async def _get_cached_result(self, cache_key: str, strategy: CacheStrategy) -> Optional[Any]:
        """Get result from cache if available and valid"""
        if strategy == CacheStrategy.NO_CACHE:
            return None
        
        if cache_key in self.query_cache:
            entry = self.query_cache[cache_key]
            
            # Check expiration
            if entry.is_expired:
                del self.query_cache[cache_key]
                self.cache_stats['evictions'] += 1
                return None
            
            # Update access statistics
            entry.update_access()
            
            # Move to end (LRU)
            self.query_cache.move_to_end(cache_key)
            
            # Decompress if needed
            result = entry.data
            if self.cache_config.compression_enabled and isinstance(result, bytes):
                result = pickle.loads(gzip.decompress(result))
            
            return result
        
        return None
    
    async def _cache_result(self, cache_key: str, result: Any, query: str, 
                           strategy: CacheStrategy) -> None:
        """Cache query result with appropriate strategy"""
        if strategy == CacheStrategy.NO_CACHE:
            return
        
        # Determine TTL based on strategy
        ttl = None
        if strategy == CacheStrategy.TTL_BASED:
            ttl = self.cache_config.default_ttl_seconds
        elif strategy == CacheStrategy.ADAPTIVE:
            # Adaptive TTL based on query complexity and data volatility
            ttl = self._calculate_adaptive_ttl(query, result)
        
        # Serialize and optionally compress data
        data = result
        size_bytes = len(str(result).encode())
        compression_ratio = 1.0
        
        if (self.cache_config.compression_enabled and 
            size_bytes > self.cache_config.compression_threshold_bytes):
            try:
                serialized = pickle.dumps(result)
                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized) * 0.9:  # Only use if >10% compression
                    data = compressed
                    compression_ratio = len(serialized) / len(compressed)
                    size_bytes = len(compressed)
                    self.cache_stats['compression_savings_bytes'] += len(serialized) - len(compressed)
            except Exception as e:
                self.logger.warning(f"Compression failed for cache entry: {e}")
        
        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            data=data,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl_seconds=ttl,
            size_bytes=size_bytes,
            compression_ratio=compression_ratio,
            tags=self._extract_table_tags(query)
        )
        
        # Add to cache
        self.query_cache[cache_key] = entry
        self.cache_stats['total_size_bytes'] += size_bytes
        
        # Track table dependencies for invalidation
        for table in entry.tags:
            self.table_dependencies[table].add(cache_key)
        
        # Enforce cache limits
        await self._enforce_cache_limits_async()
        
        # Publish cache event
        cache_event = create_cache_event(
            event_type=MemoryEventType.CACHE_WARMING,
            cache_key=cache_key,
            cache_level="L1",
            cache_size_bytes=self.cache_stats['total_size_bytes'],
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(cache_event)
    
    def _calculate_adaptive_ttl(self, query: str, result: Any) -> float:
        """Calculate adaptive TTL based on query and result characteristics"""
        base_ttl = self.cache_config.default_ttl_seconds
        
        # Adjust based on query type
        query_lower = query.lower().strip()
        
        if query_lower.startswith('select count'):
            # Count queries can be cached longer
            return base_ttl * 2
        elif 'join' in query_lower and len(query_lower) > 200:
            # Complex joins can be cached longer
            return base_ttl * 1.5
        elif any(table in query_lower for table in ['user', 'session', 'temp']):
            # Volatile tables should have shorter TTL
            return base_ttl * 0.5
        elif 'where' not in query_lower:
            # Full table scans can be cached longer
            return base_ttl * 3
        
        return base_ttl
    
    def _extract_table_tags(self, query: str) -> Set[str]:
        """Extract table names from query for cache invalidation"""
        tables = set()
        
        # Simple regex-based table extraction
        # This could be enhanced with proper SQL parsing
        query_lower = query.lower()
        
        # FROM clauses
        from_matches = re.findall(r'from\s+(\w+)', query_lower)
        tables.update(from_matches)
        
        # JOIN clauses
        join_matches = re.findall(r'join\s+(\w+)', query_lower)
        tables.update(join_matches)
        
        # UPDATE clauses
        update_matches = re.findall(r'update\s+(\w+)', query_lower)
        tables.update(update_matches)
        
        # INSERT INTO clauses
        insert_matches = re.findall(r'insert\s+into\s+(\w+)', query_lower)
        tables.update(insert_matches)
        
        return tables
    
    def _apply_optimization_rules(self, query: str) -> str:
        """Apply query optimization rules"""
        optimized_query = query
        applied_rules = []
        
        for rule in self.optimization_rules:
            if not rule.enabled:
                continue
            
            try:
                if re.search(rule.pattern, optimized_query, re.IGNORECASE):
                    if rule.replacement:  # Some rules might just be for analysis
                        new_query = re.sub(rule.pattern, rule.replacement, optimized_query, flags=re.IGNORECASE)
                        if new_query != optimized_query:
                            optimized_query = new_query
                            applied_rules.append(rule.name)
                            self.logger.debug(f"Applied optimization rule: {rule.name}")
            except Exception as e:
                self.logger.warning(f"Error applying optimization rule {rule.name}: {e}")
        
        if applied_rules:
            self.logger.info(f"Query optimization applied {len(applied_rules)} rules: {', '.join(applied_rules)}")
        
        return optimized_query
    
    def _analyze_query_complexity(self, query: str) -> QueryComplexity:
        """Analyze and classify query complexity"""
        query_lower = query.lower()
        
        # Count various complexity indicators
        join_count = len(re.findall(r'\bjoin\b', query_lower))
        subquery_count = len(re.findall(r'\(select\b', query_lower))
        union_count = len(re.findall(r'\bunion\b', query_lower))
        aggregate_count = len(re.findall(r'\b(count|sum|avg|max|min|group by)\b', query_lower))
        cte_count = len(re.findall(r'\bwith\b', query_lower))
        
        complexity_score = (join_count * 2 + subquery_count * 3 + 
                          union_count * 2 + aggregate_count + cte_count * 3)
        
        if complexity_score == 0:
            return QueryComplexity.SIMPLE
        elif complexity_score <= 3:
            return QueryComplexity.MODERATE
        elif complexity_score <= 8:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX
    
    async def _analyze_query_plan(self, query: str, parameters: Optional[List] = None) -> Optional[QueryPlan]:
        """Analyze query execution plan"""
        try:
            pool = get_connection_pool()
            
            # Get query plan using EXPLAIN
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            
            async with pool.acquire_connection() as connection:
                plan_result = await connection.fetch(explain_query, *(parameters or []))
                
            if plan_result:
                plan_data = plan_result[0]['QUERY PLAN'][0]
                
                # Extract plan information
                plan = QueryPlan(
                    query_hash=self._hash_query(query),
                    estimated_cost=plan_data.get('Total Cost', 0.0),
                    estimated_rows=plan_data.get('Plan Rows', 0),
                    execution_time_ms=plan_data.get('Actual Total Time', 0.0),
                    index_usage=self._extract_index_usage(plan_data),
                    table_scans=self._extract_table_scans(plan_data),
                    join_operations=self._extract_join_operations(plan_data)
                )
                
                # Generate optimization suggestions
                plan.optimization_suggestions = self._generate_plan_suggestions(plan_data)
                plan.complexity = self._analyze_query_complexity(query)
                
                return plan
                
        except Exception as e:
            self.logger.warning(f"Query plan analysis failed: {e}")
            return None
    
    def _extract_index_usage(self, plan_data: Dict) -> List[str]:
        """Extract index usage from query plan"""
        indexes = []
        
        def extract_recursive(node):
            if isinstance(node, dict):
                if node.get('Node Type') == 'Index Scan':
                    index_name = node.get('Index Name')
                    if index_name:
                        indexes.append(index_name)
                
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        extract_recursive(value)
            elif isinstance(node, list):
                for item in node:
                    extract_recursive(item)
        
        extract_recursive(plan_data)
        return indexes
    
    def _extract_table_scans(self, plan_data: Dict) -> List[str]:
        """Extract table scans from query plan"""
        scans = []
        
        def extract_recursive(node):
            if isinstance(node, dict):
                if node.get('Node Type') == 'Seq Scan':
                    relation_name = node.get('Relation Name')
                    if relation_name:
                        scans.append(relation_name)
                
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        extract_recursive(value)
            elif isinstance(node, list):
                for item in node:
                    extract_recursive(item)
        
        extract_recursive(plan_data)
        return scans
    
    def _extract_join_operations(self, plan_data: Dict) -> List[str]:
        """Extract join operations from query plan"""
        joins = []
        
        def extract_recursive(node):
            if isinstance(node, dict):
                node_type = node.get('Node Type', '')
                if 'Join' in node_type:
                    joins.append(node_type)
                
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        extract_recursive(value)
            elif isinstance(node, list):
                for item in node:
                    extract_recursive(item)
        
        extract_recursive(plan_data)
        return joins
    
    def _generate_plan_suggestions(self, plan_data: Dict) -> List[str]:
        """Generate optimization suggestions from query plan"""
        suggestions = []
        
        # Check for sequential scans on large tables
        def check_seq_scans(node):
            if isinstance(node, dict):
                if (node.get('Node Type') == 'Seq Scan' and 
                    node.get('Actual Rows', 0) > 10000):
                    table = node.get('Relation Name', 'unknown')
                    suggestions.append(f"Consider adding index for table {table}")
                
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        check_seq_scans(value)
            elif isinstance(node, list):
                for item in node:
                    check_seq_scans(item)
        
        check_seq_scans(plan_data)
        
        # Check for expensive joins
        def check_joins(node):
            if isinstance(node, dict):
                if ('Join' in node.get('Node Type', '') and 
                    node.get('Actual Total Time', 0) > 1000):
                    suggestions.append("Consider optimizing join conditions or adding indexes")
                
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        check_joins(value)
            elif isinstance(node, list):
                for item in node:
                    check_joins(item)
        
        check_joins(plan_data)
        
        return suggestions
    
    def _apply_plan_optimizations(self, query: str, plan: QueryPlan) -> str:
        """Apply optimizations based on query plan analysis"""
        optimized_query = query
        
        # Apply optimizations based on plan analysis
        if plan.table_scans and not plan.index_usage:
            # Query has table scans but no index usage
            # This could benefit from adding LIMIT if no specific ordering
            if 'order by' not in query.lower() and 'limit' not in query.lower():
                # Be conservative with automatic LIMIT addition
                pass  # Don't automatically add LIMIT
        
        # Add hints for expensive joins (PostgreSQL specific)
        if len(plan.join_operations) > 2 and plan.estimated_cost > 10000:
            # Could add join hints, but PostgreSQL doesn't support them directly
            pass
        
        return optimized_query
    
    def _should_cache_result(self, query: str, result: Any, execution_time_ms: float,
                           strategy: CacheStrategy) -> bool:
        """Determine if query result should be cached"""
        if strategy == CacheStrategy.NO_CACHE:
            return False
        
        # Don't cache very fast queries (overhead not worth it)
        if execution_time_ms < 10:
            return False
        
        # Don't cache if result is too large
        result_size = len(str(result).encode()) if result else 0
        if result_size > 10 * 1024 * 1024:  # 10MB limit
            return False
        
        # Don't cache write operations
        query_lower = query.lower().strip()
        if any(query_lower.startswith(op) for op in ['insert', 'update', 'delete', 'alter', 'drop', 'create']):
            return False
        
        # Cache expensive queries
        if execution_time_ms > 100:
            return True
        
        # Cache complex queries
        complexity = self._analyze_query_complexity(query)
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.VERY_COMPLEX]:
            return True
        
        return strategy in [CacheStrategy.TTL_BASED, CacheStrategy.ADAPTIVE]
    
    def _cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries"""
        expired_keys = [
            key for key, entry in self.query_cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            entry = self.query_cache[key]
            del self.query_cache[key]
            self.cache_stats['evictions'] += 1
            self.cache_stats['total_size_bytes'] -= entry.size_bytes
            
            # Remove from table dependencies
            for table in entry.tags:
                self.table_dependencies[table].discard(key)
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _enforce_cache_limits(self) -> None:
        """Enforce cache size and entry limits"""
        # Enforce entry count limit
        while len(self.query_cache) > self.cache_config.max_entries:
            self._evict_cache_entry()
        
        # Enforce size limit
        max_size_bytes = self.cache_config.max_size_mb * 1024 * 1024
        while self.cache_stats['total_size_bytes'] > max_size_bytes:
            self._evict_cache_entry()
    
    async def _enforce_cache_limits_async(self) -> None:
        """Async version of cache limit enforcement"""
        self._enforce_cache_limits()
    
    def _evict_cache_entry(self) -> None:
        """Evict a cache entry based on eviction policy"""
        if not self.query_cache:
            return
        
        if self.cache_config.eviction_policy == CacheEvictionPolicy.LRU:
            # Remove least recently used (first in OrderedDict)
            key, entry = self.query_cache.popitem(last=False)
        elif self.cache_config.eviction_policy == CacheEvictionPolicy.LFU:
            # Remove least frequently used
            min_access_key = min(self.query_cache.keys(), 
                               key=lambda k: self.query_cache[k].access_count)
            entry = self.query_cache.pop(min_access_key)
        else:  # FIFO
            # Remove oldest entry
            key, entry = self.query_cache.popitem(last=False)
        
        self.cache_stats['evictions'] += 1
        self.cache_stats['total_size_bytes'] -= entry.size_bytes
        
        # Remove from table dependencies
        for table in entry.tags:
            self.table_dependencies[table].discard(key)
    
    def _record_cache_hit(self, cache_key: str) -> None:
        """Record cache hit statistics"""
        self.cache_stats['hits'] += 1
        
        # Publish cache hit event
        cache_event = create_cache_event(
            event_type=MemoryEventType.CACHE_HIT,
            cache_key=cache_key,
            cache_level="L1",
            hit_ratio=self._calculate_hit_ratio(),
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(cache_event)
    
    def _record_cache_miss(self, cache_key: str) -> None:
        """Record cache miss statistics"""
        self.cache_stats['misses'] += 1
        
        # Publish cache miss event
        cache_event = create_cache_event(
            event_type=MemoryEventType.CACHE_MISS,
            cache_key=cache_key,
            cache_level="L1",
            hit_ratio=self._calculate_hit_ratio(),
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(cache_event)
    
    def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        if total_requests == 0:
            return 0.0
        return self.cache_stats['hits'] / total_requests
    
    def _record_query_optimization(self, query_hash: str, original: str, optimized: str, 
                                 complexity: QueryComplexity) -> None:
        """Record query optimization for analysis"""
        if original != optimized:
            self.logger.info(f"Query optimized (complexity: {complexity.value})")
    
    def _record_query_performance(self, query_hash: str, execution_time_ms: float, 
                                result_size: int) -> None:
        """Record query performance metrics"""
        self.performance_history[query_hash].append({
            'timestamp': datetime.now(),
            'execution_time_ms': execution_time_ms,
            'result_size': result_size
        })
    
    def _analyze_query_patterns(self) -> None:
        """Analyze query patterns for optimization opportunities"""
        # Analyze slow queries
        slow_queries = []
        for query_hash, history in self.performance_history.items():
            avg_time = sum(h['execution_time_ms'] for h in history) / len(history)
            if avg_time > self.slow_query_threshold_ms:
                slow_queries.append((query_hash, avg_time))
        
        if slow_queries:
            self.logger.info(f"Identified {len(slow_queries)} slow query patterns")
    
    def _generate_optimization_suggestions(self) -> None:
        """Generate optimization suggestions based on analysis"""
        # This would analyze patterns and generate suggestions
        # For now, just placeholder logic
    
    def _update_table_access_patterns(self) -> None:
        """Update table access pattern analysis"""
        # Analyze which tables are accessed together frequently
        # This could inform index recommendations
    
    def _analyze_missing_indexes(self) -> None:
        """Analyze for missing indexes based on query patterns"""
        # This would analyze query patterns to suggest missing indexes
    
    def _generate_index_recommendations(self) -> None:
        """Generate index recommendations"""
        # This would generate specific index recommendations
    
    def _update_cache_statistics(self) -> None:
        """Update and publish cache statistics"""
        hit_ratio = self._calculate_hit_ratio()
        
        # Check if hit ratio is below target
        if hit_ratio < self.cache_config.hit_ratio_target:
            self.logger.warning(f"Cache hit ratio ({hit_ratio:.2f}) below target ({self.cache_config.hit_ratio_target})")
    
    async def invalidate_cache_by_table(self, table_name: str) -> int:
        """Invalidate all cache entries that depend on a table"""
        if table_name not in self.table_dependencies:
            return 0
        
        cache_keys = list(self.table_dependencies[table_name])
        invalidated_count = 0
        
        for cache_key in cache_keys:
            if cache_key in self.query_cache:
                entry = self.query_cache.pop(cache_key)
                self.cache_stats['total_size_bytes'] -= entry.size_bytes
                self.cache_stats['evictions'] += 1
                invalidated_count += 1
        
        # Clear dependencies
        self.table_dependencies[table_name].clear()
        
        if invalidated_count > 0:
            self.logger.info(f"Invalidated {invalidated_count} cache entries for table {table_name}")
            
            # Publish cache invalidation event
            cache_event = create_cache_event(
                event_type=MemoryEventType.CACHE_INVALIDATION,
                cache_key=f"table_{table_name}",
                cache_level="L1",
                source_agent=self.name,
                machine_id=self._get_machine_id()
            )
            
            publish_memory_event(cache_event)
        
        return invalidated_count
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive optimization status"""
        hit_ratio = self._calculate_hit_ratio()
        
        return {
            'cache_stats': {
                **self.cache_stats,
                'hit_ratio': hit_ratio,
                'entry_count': len(self.query_cache),
                'size_mb': self.cache_stats['total_size_bytes'] / (1024 * 1024)
            },
            'optimization_config': {
                'level': self.optimization_level.value,
                'query_rewriting_enabled': self.enable_query_rewriting,
                'rules_count': len([r for r in self.optimization_rules if r.enabled])
            },
            'performance_analytics': {
                'tracked_queries': len(self.performance_history),
                'slow_query_threshold_ms': self.slow_query_threshold_ms,
                'query_plans_analyzed': len(self.query_plans)
            },
            'table_dependencies': {
                table: len(keys) for table, keys in self.table_dependencies.items()
            },
            'recommendations': {
                'optimization_suggestions': len(self.optimization_suggestions),
                'missing_indexes': len(self.missing_indexes)
            }
        }
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def shutdown(self):
        """Shutdown the query optimizer"""
        # Clear cache
        self.query_cache.clear()
        self.cache_stats['total_size_bytes'] = 0
        
        super().shutdown()

# Global optimizer instance
_global_optimizer: Optional[IntelligentQueryOptimizer] = None

def get_query_optimizer() -> IntelligentQueryOptimizer:
    """Get the global query optimizer instance"""
    global _global_optimizer
    if _global_optimizer is None:
        raise RuntimeError("Query optimizer not initialized. Call initialize_global_optimizer() first.")
    return _global_optimizer

def initialize_global_optimizer(cache_config: Optional[CacheConfiguration] = None,
                              optimization_level: OptimizationLevel = OptimizationLevel.AGGRESSIVE) -> IntelligentQueryOptimizer:
    """Initialize the global query optimizer"""
    global _global_optimizer
    
    if _global_optimizer is not None:
        _global_optimizer.shutdown()
    
    _global_optimizer = IntelligentQueryOptimizer(cache_config, optimization_level)
    return _global_optimizer

def close_global_optimizer() -> None:
    """Close the global query optimizer"""
    global _global_optimizer
    if _global_optimizer:
        _global_optimizer.shutdown()
        _global_optimizer = None

if __name__ == "__main__":
    # Example usage
    import asyncio
    import logging
    
    logger = configure_logging(__name__, level="INFO")
    
    async def test_optimizer():
        # Initialize optimizer
        config = CacheConfiguration(
            max_size_mb=256,
            max_entries=5000,
            default_ttl_seconds=1800  # 30 minutes
        )
        
        optimizer = initialize_global_optimizer(config, OptimizationLevel.AGGRESSIVE)
        
        try:
            # Test query optimization
            test_query = "SELECT DISTINCT u.* FROM users u WHERE u.id = $1"
            optimized_query, params = await optimizer.optimize_query(test_query, [123])
            
            print(f"Original: {test_query}")
            print(f"Optimized: {optimized_query}")
            
            # Test cache
            # Note: This would normally require a database connection
            # result = await optimizer.execute_optimized_query(optimized_query, params)
            
            # Print status
            status = optimizer.get_optimization_status()
            print(json.dumps(status, indent=2, default=str))
            
        finally:
            close_global_optimizer()
    
    asyncio.run(test_optimizer()) 