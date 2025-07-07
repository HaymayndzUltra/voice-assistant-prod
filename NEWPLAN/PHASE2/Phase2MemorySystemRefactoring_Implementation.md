# PHASE 2: Distributed Memory System Refactoring - Detailed Implementation Plan

## 1. Executive Summary

Phase 2 focuses on refactoring and modernizing the distributed memory system, consolidating fragmented memory-related components into a centralized MemoryOrchestratorService with a consistent interface. However, the initial implementation has critical missing functionality that must be addressed.

Key issues to resolve:
- **Intelligent Memory Features**: Memory decay, reinforcement, hierarchical relationships, and summarization capabilities were lost
- **Architectural Standardization**: Integration with Phase 0 standards like service discovery and error reporting is incomplete
- **Advanced Caching**: Specialized caching policies for different data types are missing

This detailed implementation plan outlines how to preserve and restore all critical memory functionality while maintaining a clean, centralized architecture.

## 2. Critical Functional Requirements

### 2.1 Memory Decay & Consolidation

The memory system must implement a decay mechanism that:
- Assigns a freshness/importance score to each memory entry
- Gradually decreases this score over time (configurable rate)
- Promotes memories from short-term to medium-term to long-term based on reinforcement
- Consolidates related memories as they age
- Implements forgetting (archiving or deletion) of low-importance memories

### 2.2 Hierarchical & Relational Memory

The memory system must support:
- Parent-child relationships between memory entries (parent_id)
- Cross-referencing between related memories (memory_relationships table)
- Grouping memories by context (context_groups)
- Efficient querying of memory hierarchies and relationships
- Maintaining relational integrity when memories are modified or deleted

### 2.3 Advanced Context Management & Summarization

The memory system must provide:
- Automatic summarization of conversation histories
- Code context summarization
- Dynamic adjustment of summary detail based on importance
- Retention of both full content and summaries
- Progressive summarization as memories age

### 2.4 Advanced Caching Policies

The memory system must implement:
- Type-specific caching policies (different for queries, model results, etc.)
- Configurable TTL per cache type
- Size limits per cache type
- Cache invalidation strategies
- Distributed cache coherence across machines

### 2.5 Memory Reinforcement & Reasoning

The memory system must support:
- Reinforcement of memories based on usage frequency
- Reinforcement based on explicit importance signals
- Basic reasoning over memory collections
- Pattern recognition in memory access
- Integration with LLM for complex reasoning tasks

## 3. Implementation Steps

### 3.1 Schema Enhancement

1. **Extend memory_entries table**:
   - Add parent_id column (foreign key to memory_entries.id)
   - Add freshness_score column (float, default 1.0)
   - Add last_access_time column
   - Add memory_type column (short_term, medium_term, long_term)
   - Add importance_score column (float)

2. **Create memory_relationships table**:
   - id (primary key)
   - source_memory_id (foreign key to memory_entries.id)
   - target_memory_id (foreign key to memory_entries.id)
   - relationship_type (string)
   - strength (float)
   - created_at, updated_at timestamps

3. **Create context_groups table**:
   - id (primary key)
   - name (string)
   - description (text)
   - created_at, updated_at timestamps

4. **Create memory_group_mappings table**:
   - id (primary key)
   - memory_id (foreign key to memory_entries.id)
   - group_id (foreign key to context_groups.id)

### 3.2 Memory Decay Implementation

1. **Create memory decay scheduler**:
   - Implement a background thread for periodic decay processing
   - Add configurable decay rates for different memory types
   - Implement decay function to reduce freshness_score
   - Add promotion logic between memory types based on thresholds

2. **Add memory reinforcement**:
   - Implement methods to increase freshness_score on access
   - Add explicit reinforcement API
   - Implement importance calculations based on access patterns

3. **Implement memory consolidation**:
   - Add logic to detect related memories
   - Create summarization of related memories
   - Implement archival of old, low-importance memories

### 3.3 Advanced Caching Implementation

1. **Enhance caching system**:
   - Implement type-based cache partitioning
   - Add configurable TTL per cache type
   - Implement size-based eviction policies
   - Add cache statistics and monitoring

2. **Distributed cache coherence**:
   - Implement cache invalidation messaging
   - Add version tracking for cached entries
   - Create cache synchronization between instances

### 3.4 Memory API Enhancement

1. **Extend CRUD operations**:
   - Update add_memory to support parent_id and relationships
   - Enhance get_memory to retrieve full hierarchies
   - Add relationship management methods
   - Implement memory consolidation triggers

2. **Add specialized query methods**:
   - Add hierarchical search
   - Implement relationship traversal
   - Add context-based grouping queries
   - Create temporal pattern recognition

### 3.5 Integration with Phase 0 Standards

1. **Standardize communication**:
   - Implement BaseAgent's send_request_to_agent method for all external calls
   - Use SystemDigitalTwin for service discovery
   - Standardize error reporting through central Error Bus
   - Use Pydantic models for all data validation

2. **Enhance MemoryClient**:
   - Refactor to be a thin client rather than middleware
   - Remove duplicated logic
   - Implement proper error propagation

## 4. Critical Logic Reference

### 4.1 Memory Decay Logic

```python
# Memory decay implementation from MemoryDecayManager
def apply_decay(self, memory_id, decay_factor=0.95):
    """
    Apply decay to a memory's freshness score.
    
    Args:
        memory_id: The ID of the memory to decay
        decay_factor: How much to decay (0.95 = 5% decay)
    """
    # Retrieve the current memory
    memory = self._get_memory_entry(memory_id)
    if not memory:
        return False
        
    # Apply the decay
    new_freshness = memory["freshness_score"] * decay_factor
    
    # Update the memory entry
    self._update_memory_entry(
        memory_id, 
        {"freshness_score": new_freshness}
    )
    
    # Check if memory should change type based on freshness
    if new_freshness < 0.3 and memory["memory_type"] == "short_term":
        self._promote_to_medium_term(memory_id)
    elif new_freshness < 0.1 and memory["memory_type"] == "medium_term":
        self._promote_to_long_term(memory_id)
    elif new_freshness < 0.05 and memory["memory_type"] == "long_term":
        self._archive_memory(memory_id)
        
    return True

def _promote_to_medium_term(self, memory_id):
    """
    Promote a short-term memory to medium-term.
    This typically involves consolidation with related memories.
    """
    # Find related memories
    related = self._find_related_memories(memory_id)
    
    # Create a consolidated summary if needed
    if len(related) > 3:
        summary = self._create_consolidated_summary(
            [memory_id] + related
        )
        
        # Store the summary as a new medium-term memory
        # with links to the original memories
        new_id = self._add_memory_entry({
            "content": summary,
            "memory_type": "medium_term",
            "freshness_score": 0.7,
            "original_memories": [memory_id] + related
        })
        
        # Update the original memories to link to this summary
        for rel_id in [memory_id] + related:
            self._add_memory_relationship(
                rel_id, 
                new_id, 
                "consolidated_into"
            )
    else:
        # Just update the type if not enough related memories
        # to warrant consolidation
        self._update_memory_entry(
            memory_id, 
            {"memory_type": "medium_term"}
        )
```

### 4.2 Hierarchical Memory Logic

```python
# Hierarchical memory implementation from EpisodicMemoryAgent
def add_child_memory(self, parent_id, content, metadata=None):
    """
    Add a memory as a child of an existing memory.
    
    Args:
        parent_id: ID of the parent memory
        content: Content of the new memory
        metadata: Additional data about the memory
        
    Returns:
        ID of the newly created child memory
    """
    # Verify parent exists
    parent = self._get_memory_entry(parent_id)
    if not parent:
        raise ValueError(f"Parent memory {parent_id} not found")
    
    # Create child memory
    child_id = self._add_memory_entry({
        "content": content,
        "parent_id": parent_id,
        "memory_type": parent["memory_type"],
        "freshness_score": 1.0,
        "metadata": metadata or {}
    })
    
    return child_id
    
def get_memory_tree(self, root_id, max_depth=3):
    """
    Retrieve a memory and all its descendants up to max_depth.
    
    Args:
        root_id: ID of the root memory
        max_depth: Maximum depth of children to retrieve
        
    Returns:
        Dictionary with the memory tree structure
    """
    root = self._get_memory_entry(root_id)
    if not root:
        return None
        
    result = dict(root)
    
    # Stop recursion at max depth
    if max_depth <= 0:
        return result
        
    # Get all direct children
    children = self._get_memory_children(root_id)
    
    # Recursively get their children
    result["children"] = [
        self.get_memory_tree(child["id"], max_depth - 1)
        for child in children
    ]
    
    return result
```

### 4.3 Advanced Caching Logic

```python
# Advanced caching from CacheManager
class TypedCache:
    """
    Cache implementation with type-specific policies.
    """
    def __init__(self):
        self.caches = {}
        self.config = {
            "nlu_results": {
                "ttl": 600,  # 10 minutes
                "max_size": 1000,
            },
            "model_outputs": {
                "ttl": 3600,  # 1 hour
                "max_size": 500,
            },
            "semantic_search": {
                "ttl": 300,  # 5 minutes
                "max_size": 200,
            },
            "default": {
                "ttl": 1800,  # 30 minutes
                "max_size": 1000,
            }
        }
        
        # Initialize caches
        for cache_type, settings in self.config.items():
            self.caches[cache_type] = {
                "data": {},
                "expiry": {},
                "access_count": {},
                "last_access": {},
            }
    
    def get(self, key, cache_type="default"):
        """Get an item from the cache."""
        cache = self.caches.get(
            cache_type, 
            self.caches["default"]
        )
        
        if key not in cache["data"]:
            return None
            
        # Check expiry
        if time.time() > cache["expiry"].get(key, 0):
            # Expired
            self._remove_key(key, cache_type)
            return None
            
        # Update stats
        cache["access_count"][key] = cache["access_count"].get(key, 0) + 1
        cache["last_access"][key] = time.time()
        
        return cache["data"][key]
        
    def put(self, key, value, cache_type="default"):
        """Add an item to the cache."""
        if cache_type not in self.caches:
            cache_type = "default"
            
        cache = self.caches[cache_type]
        config = self.config[cache_type]
        
        # Check if we need to evict
        if len(cache["data"]) >= config["max_size"]:
            self._evict_one(cache_type)
            
        # Store the item
        cache["data"][key] = value
        cache["expiry"][key] = time.time() + config["ttl"]
        cache["access_count"][key] = 0
        cache["last_access"][key] = time.time()
        
    def _evict_one(self, cache_type):
        """Evict one item from the cache based on policy."""
        cache = self.caches[cache_type]
        
        # Find least recently used item
        oldest_access = float('inf')
        oldest_key = None
        
        for key, last_access in cache["last_access"].items():
            if last_access < oldest_access:
                oldest_access = last_access
                oldest_key = key
                
        if oldest_key:
            self._remove_key(oldest_key, cache_type)
```

### 4.4 Memory Reinforcement Logic

```python
# Memory reinforcement from UnifiedMemoryReasoningAgent
def reinforce_memory(self, memory_id, reinforcement_factor=1.2):
    """
    Reinforce a memory by increasing its importance.
    
    Args:
        memory_id: ID of the memory to reinforce
        reinforcement_factor: Factor to multiply importance by
    """
    memory = self._get_memory_entry(memory_id)
    if not memory:
        return False
        
    current_importance = memory.get("importance_score", 1.0)
    new_importance = min(current_importance * reinforcement_factor, 10.0)
    
    # Update the importance score
    self._update_memory_entry(
        memory_id, 
        {
            "importance_score": new_importance,
            "last_access_time": datetime.now().isoformat()
        }
    )
    
    # Reset the decay timer
    self._update_memory_freshness(
        memory_id, 
        1.0  # Reset to full freshness
    )
    
    return True

def reason_over_memories(self, query, context, max_memories=5):
    """
    Apply reasoning over a set of memories to answer a query.
    
    Args:
        query: The question or task to reason about
        context: Additional context
        max_memories: Maximum number of memories to consider
        
    Returns:
        Reasoning result based on memories
    """
    # Find relevant memories
    memories = self._search_memories(query, limit=max_memories)
    
    if not memories:
        return {
            "result": "No relevant memories found",
            "confidence": 0.0
        }
        
    # Prepare reasoning context
    reasoning_context = {
        "query": query,
        "user_context": context,
        "relevant_memories": [m["content"] for m in memories]
    }
    
    # Use an LLM to perform reasoning
    reasoning_prompt = self._build_reasoning_prompt(reasoning_context)
    reasoning_result = self._send_to_reasoning_model(reasoning_prompt)
    
    # Reinforce the memories that were used
    for memory in memories:
        self.reinforce_memory(memory["id"], 1.1)
        
    return reasoning_result
```

## 5. File Structure Updates

After implementing Phase 2, the file structure should look like this:

```
pc2_code/
  agents/
    memory_orchestrator_service.py  (enhanced with all memory features)
    memory_scheduler.py             (new - handles background memory processes)
    typed_cache_manager.py          (new - implements advanced caching)
main_pc_code/
  agents/
    memory_client.py                (simplified client)
common/
  utils/
    memory_models.py                (shared Pydantic models for memory)
```

## 6. Configuration Updates

The following configuration files must be updated:

1. **pc2_code/config/memory_config.yaml** (new file):
   - Decay rates and thresholds
   - Cache TTLs and size limits
   - Memory type definitions
   - Consolidation policies

2. **pc2_code/config/startup_config.yaml**:
   - Add memory_scheduler entry
   - Update memory_orchestrator_service dependencies

3. **Database schema migrations**:
   - Script to add new columns to memory_entries
   - Scripts to create new tables

## 7. Testing Strategy

### 7.1 Unit Testing
- Test each memory feature in isolation
- Mock dependencies for all memory operations
- Test decay and promotion logic with time simulation
- Validate caching policies

### 7.2 Integration Testing
- Test MemoryOrchestratorService with MemoryClient
- Test hierarchical operations end-to-end
- Verify memory decay over simulated time
- Test cache invalidation across services

### 7.3 System Testing
- Full end-to-end memory workflow testing
- Performance testing with large memory sets
- Stress testing of cache eviction
- Cross-machine memory operations

## 8. Post-Implementation Verification

After implementation, verify:

1. All memory operations support hierarchy and relationships
2. Memory decay functions correctly over time
3. Cache policies work as expected for each data type
4. Memory consolidation properly summarizes and links related memories
5. All communication follows Phase 0 standards

## 9. Rollback Plan

In case of issues:

1. Keep database schema migration backups
2. Document step-by-step rollback procedures
3. Maintain backward compatibility layer during transition 