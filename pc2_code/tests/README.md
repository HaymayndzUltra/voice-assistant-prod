# Memory System Integration Tests

This directory contains integration tests for the distributed memory system components.

## Recent Refactoring (2025-07-03)

We've completely refactored the MemoryOrchestratorService to address several critical architectural issues:

### 1. Direct Redis Integration

- **Before**: The service delegated caching to an external CacheManager service via ZMQ, creating an unnecessary dependency
- **After**: The service now directly integrates with Redis for caching, eliminating the dependency on CacheManager

### 2. Simplified Schema

- **Before**: The SQLite schema was overly complex with many unrequested columns
- **After**: Streamlined schema with only essential columns: memory_id, content, metadata, importance_score, created_at

### 3. Removed Advanced Features

- **Before**: The service was bloated with numerous advanced features from the entire Phase 2 plan
- **After**: Removed all unrequested features:
  - Vector search (faiss, sentence-transformers)
  - Memory decay process
  - Memory reinforcement
  - Hierarchical memory structure

### 4. Focused Scope

- **Before**: The service tried to implement too many features at once
- **After**: Now follows a lean design focused only on persistence, caching, and a basic API

## Running the Tests

To run the memory integration tests:

```bash
python3 -m pc2_code.tests.test_memory_integration
```

## Architecture

The distributed memory system now follows a proper tiered architecture:

1. **MemoryOrchestratorService (PC2)** - Central memory service with:
   - Direct Redis integration for caching
   - SQLite for persistence
   - Simple API for add/get/update/delete/search operations
   - ZMQ pub/sub for broadcasting memory changes

2. **MemoryClient (Main PC)** - Client interface for Main PC agents to access the memory system

This architecture ensures high performance through caching while maintaining data consistency and persistence. 