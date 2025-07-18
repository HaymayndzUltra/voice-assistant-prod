# 🔄 MemoryHub Migration Guide

**Complete migration guide from legacy agents to MemoryHub Unified v2.0.0**

## 🎯 Overview

This guide provides step-by-step instructions for migrating from the legacy multi-agent architecture to MemoryHub Unified. It covers data migration, configuration updates, and deployment strategies to ensure a smooth transition.

---

## 📊 Migration Strategy

### Migration Approach Options

#### 1. Blue-Green Deployment (Recommended)

**Advantages**:
- ✅ Zero downtime migration
- ✅ Easy rollback capability  
- ✅ Full validation before cutover
- ✅ Minimal risk

**Process**:
1. Deploy MemoryHub Unified alongside legacy agents (Green)
2. Migrate data from legacy agents to MemoryHub
3. Validate all functionality in MemoryHub
4. Switch traffic from legacy (Blue) to unified (Green)
5. Decommission legacy agents after validation period

#### 2. Rolling Migration

**Advantages**:
- ✅ Gradual migration reduces risk
- ✅ Resource-efficient
- ✅ Allows phased validation

**Process**:
1. Migrate agents in logical groups
2. Update dependencies to point to MemoryHub
3. Validate each migration phase
4. Continue until all agents migrated

#### 3. Big Bang Migration

**Advantages**:
- ✅ Simplest approach
- ✅ Clean cutover

**Disadvantages**:
- ❌ Higher risk
- ❌ Potential downtime
- ❌ Difficult rollback

---

## 📋 Pre-Migration Assessment

### Legacy Agent Inventory

| **Agent** | **Port** | **Storage** | **Data Volume** | **Dependencies** |
|-----------|----------|-------------|-----------------|------------------|
| MemoryClient | 5713 | Redis db0 | ~1GB | Core system |
| SessionMemoryAgent | 5574 | SQLite | ~500MB | User sessions |
| KnowledgeBase | 5715 | SQLite | ~2GB | Documents |
| MemoryOrchestratorService | 7140 | Redis + SQLite | ~800MB | Orchestration |
| UnifiedMemoryReasoningAgent | 7105 | Custom storage | ~1.5GB | AI reasoning |
| ContextManager | 7111 | SQLite | ~300MB | Context tracking |
| ExperienceTracker | 7112 | SQLite | ~400MB | Learning data |
| CacheManager | 7102 | Redis | ~600MB | Cache data |

### Data Assessment Script

```bash
#!/bin/bash
# assess_legacy_data.sh - Assess legacy agent data

echo "📊 Legacy Agent Data Assessment"
echo "=============================="

# MemoryClient (Redis)
echo "MemoryClient (Redis db0):"
redis-cli -n 0 info keyspace | grep db0

# SessionMemoryAgent (SQLite)
echo "SessionMemoryAgent:"
if [ -f "data/sessions.db" ]; then
    sqlite3 data/sessions.db "SELECT COUNT(*) as sessions FROM sessions;"
    ls -lh data/sessions.db
fi

# KnowledgeBase (SQLite)
echo "KnowledgeBase:"
if [ -f "data/knowledge.db" ]; then
    sqlite3 data/knowledge.db "SELECT COUNT(*) as documents FROM documents;"
    ls -lh data/knowledge.db
fi

# Check for custom storage locations
echo "Checking for custom storage locations..."
find . -name "*.db" -type f
find . -name "*.json" -type f | grep -E "(memory|session|knowledge|cache)"
```

### Dependency Mapping

```python
#!/usr/bin/env python3
# analyze_dependencies.py - Analyze agent dependencies

import re
import os
import subprocess

def find_agent_references():
    """Find references to legacy agents in codebase."""
    
    legacy_agents = [
        "MemoryClient", "SessionMemoryAgent", "KnowledgeBase",
        "MemoryOrchestratorService", "UnifiedMemoryReasoningAgent",
        "ContextManager", "ExperienceTracker", "CacheManager"
    ]
    
    references = {}
    
    for agent in legacy_agents:
        references[agent] = []
        
        # Search for references in Python files
        try:
            result = subprocess.run(
                ["grep", "-r", "-n", agent, ".", "--include=*.py"],
                capture_output=True, text=True
            )
            
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        references[agent].append(line)
        except:
            pass
    
    return references

def analyze_port_usage():
    """Analyze port usage of legacy agents."""
    
    ports = {
        5713: "MemoryClient",
        5574: "SessionMemoryAgent", 
        5715: "KnowledgeBase",
        7140: "MemoryOrchestratorService",
        7105: "UnifiedMemoryReasoningAgent",
        7111: "ContextManager",
        7112: "ExperienceTracker",
        7102: "CacheManager"
    }
    
    active_ports = []
    
    for port, agent in ports.items():
        try:
            result = subprocess.run(
                ["netstat", "-tuln"], capture_output=True, text=True
            )
            if f":{port}" in result.stdout:
                active_ports.append((port, agent))
        except:
            pass
    
    return active_ports

if __name__ == "__main__":
    print("🔍 Analyzing Legacy Agent Dependencies")
    print("=====================================")
    
    # Find code references
    references = find_agent_references()
    for agent, refs in references.items():
        if refs:
            print(f"\n{agent} references ({len(refs)}):")
            for ref in refs[:5]:  # Show first 5
                print(f"  {ref}")
            if len(refs) > 5:
                print(f"  ... and {len(refs) - 5} more")
    
    # Check active ports
    active_ports = analyze_port_usage()
    if active_ports:
        print("\n🌐 Active Legacy Agent Ports:")
        for port, agent in active_ports:
            print(f"  Port {port}: {agent}")
```

---

## 🗄️ Data Migration

### 1. MemoryClient (Redis) Migration

**Legacy**: Redis database 0 with direct keys
**Target**: MemoryHub Redis database 0 with namespaced keys

```bash
#!/bin/bash
# migrate_memory_client.sh - Migrate MemoryClient data

SOURCE_DB=0
TARGET_DB=0
NAMESPACE="memory_client"

echo "🔄 Migrating MemoryClient data..."

# Export legacy keys
redis-cli -n $SOURCE_DB KEYS "*" > /tmp/memory_client_keys.txt

# Migrate each key with namespacing
while IFS= read -r key; do
    if [[ "$key" != "mc:*" ]]; then  # Skip already namespaced keys
        value=$(redis-cli -n $SOURCE_DB GET "$key")
        ttl=$(redis-cli -n $SOURCE_DB TTL "$key")
        
        # Create namespaced key
        namespaced_key="mc:$key"
        
        # Set value in target
        redis-cli -n $TARGET_DB SET "$namespaced_key" "$value"
        
        # Set TTL if exists
        if [ "$ttl" -gt 0 ]; then
            redis-cli -n $TARGET_DB EXPIRE "$namespaced_key" "$ttl"
        fi
        
        echo "Migrated: $key -> $namespaced_key"
    fi
done < /tmp/memory_client_keys.txt

echo "✅ MemoryClient migration completed"
```

### 2. SessionMemoryAgent (SQLite) Migration

**Legacy**: Separate SQLite database
**Target**: MemoryHub unified SQLite with namespace column

```python
#!/usr/bin/env python3
# migrate_sessions.py - Migrate SessionMemoryAgent data

import sqlite3
import json
from datetime import datetime

def migrate_sessions():
    """Migrate session data to unified database."""
    
    # Connect to legacy database
    legacy_conn = sqlite3.connect('data/sessions.db')
    legacy_conn.row_factory = sqlite3.Row
    
    # Connect to unified database  
    unified_conn = sqlite3.connect('data/memory_hub.db')
    
    try:
        # Get legacy sessions
        legacy_cursor = legacy_conn.cursor()
        legacy_cursor.execute("SELECT * FROM sessions")
        sessions = legacy_cursor.fetchall()
        
        # Insert into unified database with namespace
        unified_cursor = unified_conn.cursor()
        
        for session in sessions:
            # Convert legacy data to unified format
            session_data = {
                "legacy_id": session["id"],
                "data": json.loads(session["data"]) if session["data"] else {}
            }
            
            unified_cursor.execute("""
                INSERT INTO sessions 
                (namespace, session_id, user_id, data, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "session_memory",  # namespace
                session["session_id"],
                session["user_id"],
                json.dumps(session_data),
                session["expires_at"],
                session["created_at"],
                session["updated_at"]
            ))
        
        unified_conn.commit()
        print(f"✅ Migrated {len(sessions)} sessions")
        
    except Exception as e:
        print(f"❌ Session migration failed: {e}")
        unified_conn.rollback()
    
    finally:
        legacy_conn.close()
        unified_conn.close()

if __name__ == "__main__":
    migrate_sessions()
```

### 3. KnowledgeBase Migration

**Legacy**: SQLite documents table
**Target**: MemoryHub documents + auto-generated embeddings

```python
#!/usr/bin/env python3
# migrate_knowledge.py - Migrate KnowledgeBase with embedding generation

import sqlite3
import json
import asyncio
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

async def migrate_knowledge():
    """Migrate knowledge base with embedding generation."""
    
    # Initialize embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Connect to databases
    legacy_conn = sqlite3.connect('data/knowledge.db')
    legacy_conn.row_factory = sqlite3.Row
    
    unified_conn = sqlite3.connect('data/memory_hub.db')
    
    try:
        # Get legacy documents
        legacy_cursor = legacy_conn.cursor()
        legacy_cursor.execute("SELECT * FROM documents")
        documents = legacy_cursor.fetchall()
        
        # Prepare embedding index
        embeddings = []
        embedding_metadata = []
        
        # Migrate documents and generate embeddings
        unified_cursor = unified_conn.cursor()
        
        for doc in documents:
            # Insert document into unified database
            doc_metadata = json.loads(doc["metadata"]) if doc["metadata"] else {}
            doc_metadata["legacy_id"] = doc["id"]
            
            unified_cursor.execute("""
                INSERT INTO documents 
                (namespace, doc_id, title, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "knowledge_base",  # namespace
                doc["doc_id"],
                doc["title"],
                doc["content"],
                json.dumps(doc_metadata),
                doc["created_at"],
                doc["updated_at"]
            ))
            
            # Generate embedding
            content_text = f"{doc['title']}\n{doc['content']}"
            embedding = model.encode(content_text)
            embeddings.append(embedding)
            
            # Store embedding metadata
            embedding_id = f"knowledge_base:{doc['doc_id']}"
            embedding_metadata.append({
                "id": embedding_id,
                "namespace": "knowledge_base",
                "content": content_text,
                "doc_id": doc["doc_id"],
                "category": "migrated_document",
                "metadata": doc_metadata,
                "created_at": doc["created_at"]
            })
            
            print(f"Migrated document: {doc['doc_id']}")
        
        # Save FAISS index
        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            # Normalize for cosine similarity
            embeddings_array = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            
            # Create FAISS index
            index = faiss.IndexFlatIP(embeddings_array.shape[1])
            index.add(embeddings_array)
            
            # Save index and metadata
            faiss.write_index(index, "data/embeddings.index")
            
            with open("data/embeddings_metadata.json", "w") as f:
                json.dump(embedding_metadata, f, indent=2)
        
        unified_conn.commit()
        print(f"✅ Migrated {len(documents)} documents with embeddings")
        
    except Exception as e:
        print(f"❌ Knowledge migration failed: {e}")
        unified_conn.rollback()
    
    finally:
        legacy_conn.close()
        unified_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_knowledge())
```

### 4. Experience Tracker Migration

```python
#!/usr/bin/env python3
# migrate_experiences.py - Migrate ExperienceTracker data

import sqlite3
import json

def migrate_experiences():
    """Migrate experience data to unified database."""
    
    legacy_conn = sqlite3.connect('data/experiences.db')
    legacy_conn.row_factory = sqlite3.Row
    
    unified_conn = sqlite3.connect('data/memory_hub.db')
    
    try:
        legacy_cursor = legacy_conn.cursor()
        legacy_cursor.execute("SELECT * FROM experiences")
        experiences = legacy_cursor.fetchall()
        
        unified_cursor = unified_conn.cursor()
        
        for exp in experiences:
            # Convert legacy experience to unified format
            context_data = json.loads(exp["context"]) if exp["context"] else {}
            
            unified_cursor.execute("""
                INSERT INTO experiences 
                (namespace, experience_id, category, context, outcome, learning, confidence_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "experience_tracker",  # namespace
                exp["experience_id"],
                exp["category"],
                json.dumps(context_data),
                exp["outcome"],
                exp["learning"],
                exp["confidence_score"],
                exp["created_at"]
            ))
        
        unified_conn.commit()
        print(f"✅ Migrated {len(experiences)} experiences")
        
    except Exception as e:
        print(f"❌ Experience migration failed: {e}")
        unified_conn.rollback()
    
    finally:
        legacy_conn.close()
        unified_conn.close()

if __name__ == "__main__":
    migrate_experiences()
```

---

## ⚙️ Configuration Migration

### Legacy Configuration Mapping

```bash
#!/bin/bash
# migrate_config.sh - Migrate legacy configurations

echo "📝 Migrating Configuration..."

# Create unified environment file
cat > .env << EOF
# MemoryHub Unified Configuration
# Migrated from legacy agents $(date)

# Redis Configuration (from MemoryClient, CacheManager)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=${LEGACY_REDIS_PASSWORD:-}

# Storage Configuration
SQLITE_PATH=data/memory_hub.db

# Embedding Configuration (from UnifiedMemoryReasoningAgent)
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_INDEX_PATH=data/embeddings.index
EMBEDDING_METADATA_PATH=data/embeddings_metadata.json

# Authentication (from AuthenticationAgent)
JWT_SECRET=${LEGACY_JWT_SECRET:-$(openssl rand -hex 32)}
REQUIRE_AUTH=true

# Monitoring (from ProactiveContextMonitor)
MONITOR_ENABLED=true
LOG_LEVEL=INFO

# Performance Settings
APP_WORKERS=4
EOF

echo "✅ Configuration migrated to .env"

# Backup legacy configurations
mkdir -p migration_backup
cp -r config/ migration_backup/ 2>/dev/null || true
cp *.env migration_backup/ 2>/dev/null || true
cp *.yaml migration_backup/ 2>/dev/null || true

echo "✅ Legacy configurations backed up to migration_backup/"
```

### Port Migration Strategy

```yaml
# port_migration.yaml - Port migration mapping

legacy_ports:
  MemoryClient: 5713
  SessionMemoryAgent: 5574
  KnowledgeBase: 5715
  MemoryOrchestratorService: 7140
  UnifiedMemoryReasoningAgent: 7105
  ContextManager: 7111
  ExperienceTracker: 7112
  CacheManager: 7102

unified_port: 7010

migration_strategy:
  phase1:
    # Keep legacy agents running
    # Deploy MemoryHub on port 7010
    # Update health checks to include MemoryHub
    
  phase2:
    # Update client applications to use port 7010
    # Use load balancer to gradually shift traffic
    
  phase3:
    # Disable legacy agent endpoints
    # Monitor for any remaining traffic
    
  phase4:
    # Shutdown legacy agents
    # Free up legacy ports
```

---

## 🔄 Deployment Migration

### Blue-Green Migration Script

```bash
#!/bin/bash
# blue_green_migration.sh - Blue-Green deployment for MemoryHub

set -e

LEGACY_ENV="blue"
UNIFIED_ENV="green"
HEALTH_CHECK_URL="http://localhost:7010/health"
VALIDATION_SCRIPT="./validate_migration.sh"

echo "🔄 Starting Blue-Green Migration"
echo "==============================="

# Phase 1: Deploy Green (MemoryHub Unified)
echo "📦 Phase 1: Deploying MemoryHub Unified (Green)"

# Create data directory
mkdir -p data logs

# Install dependencies
pip install -r requirements.txt

# Run data migration
echo "📊 Running data migration..."
./migrate_all_data.sh

# Start MemoryHub Unified
echo "🚀 Starting MemoryHub Unified..."
python -m memory_hub.memory_hub &
MEMORYHUB_PID=$!

# Wait for startup
echo "⏳ Waiting for MemoryHub to start..."
for i in {1..30}; do
    if curl -s "$HEALTH_CHECK_URL" > /dev/null; then
        echo "✅ MemoryHub is healthy"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Phase 2: Validation
echo "🧪 Phase 2: Validating MemoryHub functionality"
if $VALIDATION_SCRIPT; then
    echo "✅ Validation passed"
else
    echo "❌ Validation failed - rolling back"
    kill $MEMORYHUB_PID
    exit 1
fi

# Phase 3: Traffic cutover (manual step)
echo "🔀 Phase 3: Ready for traffic cutover"
echo "Manual step: Update load balancer to point to MemoryHub (port 7010)"
echo "Press Enter when traffic has been switched..."
read

# Phase 4: Monitor and cleanup
echo "📊 Phase 4: Monitoring and cleanup"
echo "Monitoring MemoryHub for 5 minutes..."

for i in {1..150}; do  # 5 minutes
    if ! curl -s "$HEALTH_CHECK_URL" > /dev/null; then
        echo "❌ MemoryHub health check failed"
        exit 1
    fi
    sleep 2
done

echo "🎉 Blue-Green migration completed successfully!"
echo "You can now shutdown legacy agents manually"
echo "MemoryHub PID: $MEMORYHUB_PID"
```

### Rolling Migration Script

```bash
#!/bin/bash
# rolling_migration.sh - Rolling migration strategy

AGENTS_TO_MIGRATE=(
    "MemoryClient:5713"
    "SessionMemoryAgent:5574"
    "KnowledgeBase:5715"
    "CacheManager:7102"
    "ExperienceTracker:7112"
    "ContextManager:7111"
    "UnifiedMemoryReasoningAgent:7105"
    "MemoryOrchestratorService:7140"
)

echo "🔄 Starting Rolling Migration"
echo "============================="

# Start MemoryHub if not running
if ! curl -s http://localhost:7010/health > /dev/null; then
    echo "🚀 Starting MemoryHub Unified..."
    python -m memory_hub.memory_hub &
    sleep 10
fi

# Migrate each agent
for agent_port in "${AGENTS_TO_MIGRATE[@]}"; do
    agent=$(echo $agent_port | cut -d: -f1)
    port=$(echo $agent_port | cut -d: -f2)
    
    echo "📦 Migrating $agent (port $port)..."
    
    # Check if agent is running
    if netstat -tuln | grep ":$port" > /dev/null; then
        echo "  Agent is running on port $port"
        
        # Update configuration to disable agent
        echo "  Disabling $agent..."
        # Agent-specific disable logic here
        
        # Wait for graceful shutdown
        sleep 5
        
        # Verify agent is stopped
        if ! netstat -tuln | grep ":$port" > /dev/null; then
            echo "  ✅ $agent stopped successfully"
        else
            echo "  ⚠️  $agent still running - manual intervention required"
        fi
    else
        echo "  Agent not running - skipping"
    fi
    
    # Validate MemoryHub still healthy
    if curl -s http://localhost:7010/health > /dev/null; then
        echo "  ✅ MemoryHub health check passed"
    else
        echo "  ❌ MemoryHub health check failed - aborting migration"
        exit 1
    fi
    
    echo "  Migration of $agent completed"
    echo
done

echo "🎉 Rolling migration completed successfully!"
```

---

## ✅ Validation and Testing

### Migration Validation Script

```bash
#!/bin/bash
# validate_migration.sh - Comprehensive migration validation

BASE_URL="http://localhost:7010"
FAILED=0

echo "🧪 Validating MemoryHub Migration"
echo "================================="

# Test 1: Health Check
echo "1. Testing health endpoint..."
if curl -s "$BASE_URL/health" | grep -q "healthy"; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    FAILED=$((FAILED + 1))
fi

# Test 2: Authentication
echo "2. Testing authentication..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/token" \
    -H "Content-Type: application/json" \
    -d '{"username": "migration_test", "password": "test123"}' | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "   ✅ Authentication passed"
else
    echo "   ❌ Authentication failed"
    FAILED=$((FAILED + 1))
fi

# Test 3: Data Migration Validation
echo "3. Validating migrated data..."

# Check key-value data
echo "   Testing key-value data..."
KV_RESULT=$(curl -s "$BASE_URL/kv/memory_client/test_migration_key" \
    -H "Authorization: Bearer $TOKEN")

if echo "$KV_RESULT" | grep -q "exists"; then
    echo "   ✅ Key-value data accessible"
else
    echo "   ❌ Key-value data not found"
    FAILED=$((FAILED + 1))
fi

# Check document data
echo "   Testing document data..."
DOC_RESULT=$(curl -s "$BASE_URL/doc/knowledge_base/migration_test_doc" \
    -H "Authorization: Bearer $TOKEN")

if echo "$DOC_RESULT" | grep -q "doc_id"; then
    echo "   ✅ Document data accessible"
else
    echo "   ❌ Document data not found"
    FAILED=$((FAILED + 1))
fi

# Check session data
echo "   Testing session data..."
SESSION_RESULT=$(curl -s "$BASE_URL/session/session_memory/migration_test_session" \
    -H "Authorization: Bearer $TOKEN")

if echo "$SESSION_RESULT" | grep -q "session_id"; then
    echo "   ✅ Session data accessible"
else
    echo "   ❌ Session data not found"
    FAILED=$((FAILED + 1))
fi

# Test 4: Semantic Search
echo "4. Testing semantic search..."
SEARCH_RESULT=$(curl -s -X POST "$BASE_URL/embedding/search" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query": "migration test document", "namespace": "knowledge_base", "limit": 5}')

if echo "$SEARCH_RESULT" | grep -q "results"; then
    echo "   ✅ Semantic search working"
else
    echo "   ❌ Semantic search failed"
    FAILED=$((FAILED + 1))
fi

# Test 5: Performance Test
echo "5. Testing performance..."
START_TIME=$(date +%s%N)
for i in {1..10}; do
    curl -s "$BASE_URL/health" > /dev/null
done
END_TIME=$(date +%s%N)
DURATION=$(( (END_TIME - START_TIME) / 1000000 ))  # Convert to ms

if [ $DURATION -lt 1000 ]; then  # Less than 1 second for 10 requests
    echo "   ✅ Performance test passed (${DURATION}ms for 10 requests)"
else
    echo "   ⚠️  Performance test warning (${DURATION}ms for 10 requests)"
fi

# Summary
echo
echo "📊 Migration Validation Summary"
echo "==============================="
if [ $FAILED -eq 0 ]; then
    echo "🎉 All tests passed! Migration successful."
    echo "✅ MemoryHub is ready for production use."
    exit 0
else
    echo "⚠️  $FAILED test(s) failed."
    echo "❌ Please review and fix issues before proceeding."
    exit 1
fi
```

### Performance Comparison

```python
#!/usr/bin/env python3
# performance_comparison.py - Compare legacy vs unified performance

import time
import requests
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor

class PerformanceTest:
    def __init__(self):
        self.legacy_endpoints = {
            "memory": "http://localhost:5713",
            "session": "http://localhost:5574", 
            "knowledge": "http://localhost:5715"
        }
        self.unified_endpoint = "http://localhost:7010"
        self.auth_token = self._get_auth_token()
    
    def _get_auth_token(self):
        """Get authentication token for unified API."""
        try:
            response = requests.post(f"{self.unified_endpoint}/auth/token", json={
                "username": "performance_test",
                "password": "test123"
            })
            return response.json()["access_token"]
        except:
            return None
    
    def test_response_time(self, url, iterations=100):
        """Test response time for endpoint."""
        times = []
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        
        for _ in range(iterations):
            start = time.time()
            try:
                response = requests.get(f"{url}/health", headers=headers, timeout=5)
                if response.status_code == 200:
                    times.append((time.time() - start) * 1000)  # Convert to ms
            except:
                pass
        
        if times:
            return {
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "p95": sorted(times)[int(len(times) * 0.95)],
                "min": min(times),
                "max": max(times)
            }
        return None
    
    def test_throughput(self, url, duration=30):
        """Test throughput for endpoint."""
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        successful_requests = 0
        start_time = time.time()
        
        def make_request():
            try:
                response = requests.get(f"{url}/health", headers=headers, timeout=5)
                return response.status_code == 200
            except:
                return False
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            while time.time() - start_time < duration:
                futures = [executor.submit(make_request) for _ in range(10)]
                successful_requests += sum(f.result() for f in futures if f.result())
        
        return successful_requests / duration  # Requests per second
    
    def run_comparison(self):
        """Run performance comparison."""
        print("🏃 Performance Comparison: Legacy vs Unified")
        print("=" * 50)
        
        # Test legacy agents
        print("\n📊 Legacy Agents Performance:")
        legacy_results = {}
        for name, url in self.legacy_endpoints.items():
            print(f"\nTesting {name} ({url})...")
            response_time = self.test_response_time(url)
            throughput = self.test_throughput(url, 10)  # 10 second test
            
            if response_time:
                legacy_results[name] = {
                    "response_time": response_time,
                    "throughput": throughput
                }
                print(f"  Response time: {response_time['mean']:.2f}ms avg")
                print(f"  Throughput: {throughput:.2f} req/s")
            else:
                print(f"  ❌ {name} not responding")
        
        # Test unified system
        print(f"\n📊 MemoryHub Unified Performance:")
        print(f"\nTesting unified ({self.unified_endpoint})...")
        unified_response_time = self.test_response_time(self.unified_endpoint)
        unified_throughput = self.test_throughput(self.unified_endpoint, 10)
        
        if unified_response_time:
            print(f"  Response time: {unified_response_time['mean']:.2f}ms avg")
            print(f"  Throughput: {unified_throughput:.2f} req/s")
            
            # Comparison
            print("\n📈 Performance Comparison Summary:")
            print("-" * 40)
            
            avg_legacy_response = statistics.mean([
                r["response_time"]["mean"] for r in legacy_results.values()
            ]) if legacy_results else float('inf')
            
            avg_legacy_throughput = statistics.mean([
                r["throughput"] for r in legacy_results.values()
            ]) if legacy_results else 0
            
            response_improvement = ((avg_legacy_response - unified_response_time['mean']) / avg_legacy_response) * 100
            throughput_improvement = ((unified_throughput - avg_legacy_throughput) / avg_legacy_throughput) * 100
            
            print(f"Response time: {response_improvement:+.1f}% improvement")
            print(f"Throughput: {throughput_improvement:+.1f}% improvement")
            
            if response_improvement > 0 and throughput_improvement > 0:
                print("✅ Unified system outperforms legacy agents")
            else:
                print("⚠️  Performance needs optimization")
        else:
            print("❌ Unified system not responding")

if __name__ == "__main__":
    test = PerformanceTest()
    test.run_comparison()
```

---

## 🚨 Rollback Strategy

### Rollback Plan

```bash
#!/bin/bash
# rollback_migration.sh - Emergency rollback from unified to legacy

echo "🔙 Emergency Rollback to Legacy Agents"
echo "======================================"

# Stop MemoryHub Unified
echo "🛑 Stopping MemoryHub Unified..."
pkill -f "memory_hub.memory_hub" || true

# Restore legacy configurations
echo "📋 Restoring legacy configurations..."
if [ -d "migration_backup" ]; then
    cp -r migration_backup/config/* config/ 2>/dev/null || true
    cp migration_backup/*.env . 2>/dev/null || true
fi

# Start legacy agents
echo "🚀 Starting legacy agents..."

# MemoryClient
echo "Starting MemoryClient on port 5713..."
python legacy_agents/memory_client.py &

# SessionMemoryAgent  
echo "Starting SessionMemoryAgent on port 5574..."
python legacy_agents/session_memory_agent.py &

# KnowledgeBase
echo "Starting KnowledgeBase on port 5715..."
python legacy_agents/knowledge_base.py &

# Other agents...
# Add startup commands for other legacy agents

# Wait for agents to start
echo "⏳ Waiting for legacy agents to start..."
sleep 10

# Validate legacy agents
echo "🧪 Validating legacy agents..."
FAILED=0

for port in 5713 5574 5715; do
    if netstat -tuln | grep ":$port" > /dev/null; then
        echo "✅ Port $port is active"
    else
        echo "❌ Port $port is not responding"
        FAILED=$((FAILED + 1))
    fi
done

if [ $FAILED -eq 0 ]; then
    echo "✅ Rollback completed successfully"
    echo "Legacy agents are running normally"
else
    echo "❌ Rollback failed - manual intervention required"
fi
```

---

## 📝 Migration Checklist

### Pre-Migration Checklist

- [ ] **Data Assessment Complete**
  - [ ] Legacy agent data volumes documented
  - [ ] Storage requirements calculated  
  - [ ] Custom schemas identified
  - [ ] Dependencies mapped

- [ ] **Environment Prepared**
  - [ ] MemoryHub requirements installed
  - [ ] Redis server configured (4 databases)
  - [ ] SQLite storage directory created
  - [ ] Backup storage available

- [ ] **Migration Scripts Ready**
  - [ ] Data migration scripts tested
  - [ ] Configuration migration complete
  - [ ] Validation scripts prepared
  - [ ] Rollback plan documented

### Migration Execution Checklist

- [ ] **Data Migration**
  - [ ] MemoryClient data migrated with namespacing
  - [ ] SessionMemoryAgent data migrated to unified SQLite
  - [ ] KnowledgeBase documents migrated + embeddings generated
  - [ ] ExperienceTracker data migrated with namespacing
  - [ ] Other agent data migrated as needed

- [ ] **System Deployment**
  - [ ] MemoryHub Unified deployed and started
  - [ ] Health checks passing
  - [ ] All endpoints responding
  - [ ] Authentication working
  - [ ] Background monitoring active

- [ ] **Validation**
  - [ ] Data accessibility verified
  - [ ] Functionality tests passed
  - [ ] Performance benchmarks met
  - [ ] Security validation complete
  - [ ] Integration tests passed

### Post-Migration Checklist

- [ ] **Monitoring Setup**
  - [ ] Health monitoring configured
  - [ ] Performance metrics collection active
  - [ ] Log aggregation working
  - [ ] Alert thresholds set

- [ ] **Documentation Updated**
  - [ ] API documentation updated
  - [ ] Deployment guides revised
  - [ ] Configuration references updated
  - [ ] Migration notes documented

- [ ] **Legacy Cleanup**
  - [ ] Legacy agents stopped
  - [ ] Legacy configurations archived
  - [ ] Port assignments updated
  - [ ] Dependencies removed

---

## 🎯 Migration Timeline

### Recommended Timeline (Production)

**Week 1: Planning and Preparation**
- Days 1-2: Data assessment and dependency mapping
- Days 3-4: Migration script development and testing
- Days 5-7: Environment preparation and validation

**Week 2: Migration Execution**
- Day 8: Deploy MemoryHub in parallel (Blue-Green)
- Day 9: Data migration execution
- Day 10: Functionality validation and testing
- Day 11: Performance testing and optimization
- Day 12: Security validation

**Week 3: Cutover and Stabilization**
- Day 13: Traffic cutover to MemoryHub
- Days 14-16: Monitoring and issue resolution
- Days 17-19: Performance optimization
- Days 20-21: Legacy agent shutdown

**Week 4: Cleanup and Documentation**
- Days 22-24: Legacy system cleanup
- Days 25-26: Documentation updates
- Day 27: Migration review and lessons learned
- Day 28: Final validation and sign-off

---

**MemoryHub Migration Guide v2.0.0** - Complete migration reference ✅🔄 