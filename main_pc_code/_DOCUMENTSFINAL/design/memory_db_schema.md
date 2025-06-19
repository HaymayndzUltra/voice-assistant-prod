# Memory Orchestrator Database Schema

## Overview

This document defines the database schema for the Memory Orchestrator, which will serve as the unified storage system for all voice assistant memory components. The schema is designed to accommodate data currently stored in separate systems including `SessionMemoryAgent`, `contextual_memory_pc2`, and `jarvis_memory_pc2`.

## Database Technology

The Memory Orchestrator will use PostgreSQL for the primary database. PostgreSQL offers:

1. Robust ACID compliance
2. Advanced indexing capabilities
3. JSON/JSONB support for flexible data storage
4. Vector extension support (e.g., pgvector) for semantic search functionality
5. Mature replication and backup solutions
6. Excellent performance for our expected workload

## Schema Definition

### 1. Sessions Table

Stores information about user interaction sessions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `session_id` | VARCHAR(64) | No | Primary key, unique session identifier |
| `user_id` | VARCHAR(64) | Yes | Reference to user if authenticated |
| `created_at` | TIMESTAMP | No | When the session was created |
| `updated_at` | TIMESTAMP | No | When the session was last updated |
| `ended_at` | TIMESTAMP | Yes | When the session ended (null if active) |
| `metadata` | JSONB | Yes | Session context (device info, location, etc.) |
| `summary` | TEXT | Yes | Generated summary of the session |
| `is_archived` | BOOLEAN | No | Whether the session has been archived |
| `session_type` | VARCHAR(32) | No | Type of session (conversation, task, etc.) |

```sql
CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    metadata JSONB,
    summary TEXT,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    session_type VARCHAR(32) NOT NULL
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_session_type ON sessions(session_type);
```

### 2. Memory Entries Table

Stores the core memory entries including conversations, context, and preferences.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `memory_id` | VARCHAR(64) | No | Primary key, unique memory identifier |
| `session_id` | VARCHAR(64) | Yes | Reference to the session (if applicable) |
| `memory_type` | VARCHAR(32) | No | Type of memory (conversation, context, user_preference, agent_state) |
| `content` | JSONB | No | The actual memory content |
| `text_content` | TEXT | Yes | Extracted text for indexing and search |
| `source_agent` | VARCHAR(64) | Yes | The agent that created this memory |
| `created_at` | TIMESTAMP | No | When the memory was created |
| `updated_at` | TIMESTAMP | No | When the memory was last updated |
| `expires_at` | TIMESTAMP | Yes | When the memory expires (null for permanent) |
| `priority` | INTEGER | No | Importance score (1-10) |
| `is_active` | BOOLEAN | No | Whether the memory is active or soft-deleted |

```sql
CREATE TABLE memory_entries (
    memory_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) REFERENCES sessions(session_id) ON DELETE CASCADE,
    memory_type VARCHAR(32) NOT NULL,
    content JSONB NOT NULL,
    text_content TEXT GENERATED ALWAYS AS (content->>'text') STORED,
    source_agent VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    priority INTEGER NOT NULL DEFAULT 5,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    CONSTRAINT valid_priority CHECK (priority BETWEEN 1 AND 10)
);

CREATE INDEX idx_memory_entries_session_id ON memory_entries(session_id);
CREATE INDEX idx_memory_entries_memory_type ON memory_entries(memory_type);
CREATE INDEX idx_memory_entries_created_at ON memory_entries(created_at);
CREATE INDEX idx_memory_entries_expires_at ON memory_entries(expires_at);
CREATE INDEX idx_memory_entries_source_agent ON memory_entries(source_agent);
CREATE INDEX idx_memory_entries_text_content ON memory_entries USING GIN (to_tsvector('english', text_content));
CREATE INDEX idx_memory_entries_priority ON memory_entries(priority);
CREATE INDEX idx_memory_entries_content ON memory_entries USING GIN (content);
```

### 3. Memory Tags Table

Stores tags associated with memory entries for improved search and filtering.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `tag_id` | SERIAL | No | Primary key, auto-incremented |
| `memory_id` | VARCHAR(64) | No | Reference to the memory entry |
| `tag` | VARCHAR(64) | No | The tag value |

```sql
CREATE TABLE memory_tags (
    tag_id SERIAL PRIMARY KEY,
    memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    tag VARCHAR(64) NOT NULL,
    
    CONSTRAINT unique_memory_tag UNIQUE (memory_id, tag)
);

CREATE INDEX idx_memory_tags_memory_id ON memory_tags(memory_id);
CREATE INDEX idx_memory_tags_tag ON memory_tags(tag);
```

### 4. Vector Embeddings Table

Stores vector embeddings for semantic search capabilities.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `embedding_id` | SERIAL | No | Primary key, auto-incremented |
| `memory_id` | VARCHAR(64) | No | Reference to the memory entry |
| `embedding` | VECTOR(1536) | No | The vector embedding (using pgvector extension) |
| `embedding_model` | VARCHAR(64) | No | The model used to generate the embedding |
| `created_at` | TIMESTAMP | No | When the embedding was created |

```sql
-- Requires pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE vector_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    embedding VECTOR(1536) NOT NULL,
    embedding_model VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_memory_embedding UNIQUE (memory_id, embedding_model)
);

CREATE INDEX idx_vector_embeddings_memory_id ON vector_embeddings(memory_id);
CREATE INDEX idx_vector_embeddings_embedding_model ON vector_embeddings(embedding_model);
-- Create vector index for similarity search
CREATE INDEX idx_vector_embeddings_embedding ON vector_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 5. User Profiles Table

Stores user-specific data and preferences.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `user_id` | VARCHAR(64) | No | Primary key, unique user identifier |
| `created_at` | TIMESTAMP | No | When the user profile was created |
| `updated_at` | TIMESTAMP | No | When the user profile was last updated |
| `profile_data` | JSONB | Yes | User profile information |
| `preferences` | JSONB | Yes | User preferences |
| `is_active` | BOOLEAN | No | Whether the user is active |

```sql
CREATE TABLE user_profiles (
    user_id VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    profile_data JSONB,
    preferences JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_user_profiles_is_active ON user_profiles(is_active);
CREATE INDEX idx_user_profiles_preferences ON user_profiles USING GIN (preferences);
```

### 6. Agent States Table

Stores persistent state information for voice assistant agents.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `state_id` | SERIAL | No | Primary key, auto-incremented |
| `agent_id` | VARCHAR(64) | No | Identifier of the agent |
| `session_id` | VARCHAR(64) | Yes | Associated session if applicable |
| `state_data` | JSONB | No | The agent's state data |
| `created_at` | TIMESTAMP | No | When the state was created |
| `updated_at` | TIMESTAMP | No | When the state was last updated |
| `expires_at` | TIMESTAMP | Yes | When the state expires (null for permanent) |

```sql
CREATE TABLE agent_states (
    state_id SERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) REFERENCES sessions(session_id) ON DELETE SET NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    CONSTRAINT unique_agent_session UNIQUE (agent_id, session_id)
);

CREATE INDEX idx_agent_states_agent_id ON agent_states(agent_id);
CREATE INDEX idx_agent_states_session_id ON agent_states(session_id);
CREATE INDEX idx_agent_states_expires_at ON agent_states(expires_at);
```

### 7. Memory Relationships Table

Stores relationships between memory entries (e.g., reply to, reference, follow-up).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `relationship_id` | SERIAL | No | Primary key, auto-incremented |
| `source_memory_id` | VARCHAR(64) | No | Source memory ID |
| `target_memory_id` | VARCHAR(64) | No | Target memory ID |
| `relationship_type` | VARCHAR(32) | No | Type of relationship |
| `metadata` | JSONB | Yes | Additional relationship metadata |
| `created_at` | TIMESTAMP | No | When the relationship was created |

```sql
CREATE TABLE memory_relationships (
    relationship_id SERIAL PRIMARY KEY,
    source_memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    target_memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    relationship_type VARCHAR(32) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_memory_relationship UNIQUE (source_memory_id, target_memory_id, relationship_type)
);

CREATE INDEX idx_memory_relationships_source ON memory_relationships(source_memory_id);
CREATE INDEX idx_memory_relationships_target ON memory_relationships(target_memory_id);
CREATE INDEX idx_memory_relationships_type ON memory_relationships(relationship_type);
```

### 8. Memory Access Log Table

Records all access to memory entries for auditing and security.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `log_id` | SERIAL | No | Primary key, auto-incremented |
| `memory_id` | VARCHAR(64) | Yes | The memory being accessed |
| `session_id` | VARCHAR(64) | Yes | The session making the request |
| `agent_id` | VARCHAR(64) | Yes | The agent making the request |
| `operation` | VARCHAR(16) | No | Operation (create, read, update, delete, search) |
| `timestamp` | TIMESTAMP | No | When the access occurred |
| `request_data` | JSONB | Yes | The request data (sanitized) |
| `success` | BOOLEAN | No | Whether the operation succeeded |
| `error_message` | TEXT | Yes | Error message if the operation failed |
| `ip_address` | VARCHAR(45) | Yes | IP address of the requester |

```sql
CREATE TABLE memory_access_logs (
    log_id SERIAL PRIMARY KEY,
    memory_id VARCHAR(64) REFERENCES memory_entries(memory_id) ON DELETE SET NULL,
    session_id VARCHAR(64) REFERENCES sessions(session_id) ON DELETE SET NULL,
    agent_id VARCHAR(64),
    operation VARCHAR(16) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_data JSONB,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    ip_address VARCHAR(45)
);

CREATE INDEX idx_memory_access_logs_memory_id ON memory_access_logs(memory_id);
CREATE INDEX idx_memory_access_logs_session_id ON memory_access_logs(session_id);
CREATE INDEX idx_memory_access_logs_agent_id ON memory_access_logs(agent_id);
CREATE INDEX idx_memory_access_logs_timestamp ON memory_access_logs(timestamp);
CREATE INDEX idx_memory_access_logs_operation ON memory_access_logs(operation);
CREATE INDEX idx_memory_access_logs_success ON memory_access_logs(success);
```

## Data Migration Mappings

This section defines how data from existing memory systems will map to the new schema.

### SessionMemoryAgent Mapping

| Source Field | Target Table | Target Field |
|--------------|--------------|--------------|
| `session_id` | `sessions` | `session_id` |
| `conversation_history` | `memory_entries` | Multiple entries with `memory_type = 'conversation'` |
| `session_data` | `sessions` | `metadata` |
| `session_summary` | `sessions` | `summary` |
| `created_at` | `sessions` | `created_at` |
| `last_interaction` | `sessions` | `updated_at` |

### contextual_memory_pc2 Mapping

| Source Field | Target Table | Target Field |
|--------------|--------------|--------------|
| `context_id` | `memory_entries` | `memory_id` |
| `session_id` | `sessions` | `session_id` |
| `context_data` | `memory_entries` | `content` |
| `embedding` | `vector_embeddings` | `embedding` |
| `created_at` | `memory_entries` | `created_at` |
| `expires_at` | `memory_entries` | `expires_at` |
| `source_agent` | `memory_entries` | `source_agent` |
| `tags` | `memory_tags` | Multiple entries in `tag` |

### jarvis_memory_pc2 Mapping

| Source Field | Target Table | Target Field |
|--------------|--------------|--------------|
| `user_id` | `user_profiles` | `user_id` |
| `preferences` | `user_profiles` | `preferences` |
| `entity_knowledge` | `memory_entries` | Multiple entries with `memory_type = 'entity'` |
| `interaction_history` | `memory_entries` | Multiple entries with `memory_type = 'interaction'` |
| `skill_states` | `agent_states` | Multiple entries for different `agent_id` values |

## Indexes and Performance Optimizations

The schema includes several indexes to optimize the most common query patterns:

1. **Primary Key Indexes**: On all ID fields for direct lookups
2. **Foreign Key Indexes**: On all relationship fields for join operations
3. **Timestamp Indexes**: For filtering by time ranges and expiration
4. **Full-Text Search Indexes**: On text content for keyword searching
5. **JSON Indexes**: On JSONB fields for querying specific properties
6. **Vector Indexes**: On embeddings for efficient similarity search
7. **Tag Indexes**: For filtering by tags

## Partitioning Strategy

For production deployment with large amounts of data, the following partitioning strategy is recommended:

1. **Time-Based Partitioning** for `memory_entries` and `memory_access_logs` tables by month or quarter
2. **Hash Partitioning** for `vector_embeddings` table by `memory_id` to distribute vector search load

## Data Lifecycle Management

1. **TTL-Based Expiration**: `expires_at` field determines when memories can be purged
2. **Archiving**: Old sessions marked with `is_archived = true` can be moved to cold storage
3. **Soft Deletion**: `is_active = false` marks memories as deleted without physical removal
4. **Prioritization**: `priority` field helps determine which memories to keep when space is limited

## Database Sizing Estimates

Based on the current system usage:

1. **Memory Entries**: ~10,000 new entries per day, ~3.65 million per year
2. **Vector Embeddings**: ~5,000 new embeddings per day, ~1.83 million per year
3. **Storage Requirements**: ~100GB per year with proper archiving policies
4. **RAM Requirements**: ~16GB for optimal performance with caching
5. **CPU Requirements**: 4-8 cores for vector search operations

## PC2 Memory Services

- Unified Memory Reasoning Agent (port 5596)
- DreamWorld Agent (port 5598-PUB)
- Other PC2 memory services 