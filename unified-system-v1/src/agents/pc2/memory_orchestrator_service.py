# File: main_pc_code/agents/memory_orchestrator_service.py
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# (O kung saan man dapat ilagay ang bagong central orchestrator)
#
# Ito ang FINAL at PINAHUSAY na bersyon ng Memory Orchestrator.
# Pinagsasama nito ang lahat ng memory-related features sa isang,
# central, at robust na serbisyo.

import sys
import os
import time
import logging
import threading
import json
import uuid
import sqlite3
import redis
import zmq  # Add missing import for ZMQ
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, cast, TypeVar, Literal
from pydantic import BaseModel, Field
from collections import defaultdict


# Import path manager for containerization-friendly paths
from common.utils.path_manager import PathManager
# --- Path Setup ---
# (I-adjust kung kinakailangan)
MAIN_PC_CODE_DIR = PathManager.get_project_root()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity

# ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
# Removed: from src.agents.pc2.error_bus_template import setup_error_reporting, report_error
# Now using: self.report_error() method from BaseAgent

from src.agents.pc2.utils.config_loader import Config, parse_agent_args
from common.env_helpers import get_env

# Load configuration at the module level
config = Config().get_config()



# --- Logging Setup ---
logger = logging.getLogger('MemoryOrchestratorService')

# --- Constants with Port Registry Integration ---
# Port registry removed - using environment variables with startup_config.yaml defaults
DEFAULT_PORT = int(os.getenv("MEMORY_ORCHESTRATOR_PORT", 7140))  # Port para sa Orchestrator
    
DB_PATH = Path(PathManager.get_project_root()) / "data" / str(PathManager.get_data_dir() / "unified_memory.db")
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
LIFECYCLE_INTERVAL = 3600 # 1 oras para sa decay/consolidation

# ===================================================================
#         INTERNAL DATA MODELS (Para sa Kalinawan)
# ===================================================================
class MemoryEntry(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem-{uuid.uuid4()}")
    content: str
    memory_type: str = "general" # e.g., 'interaction', 'episode', 'knowledge_fact'
    memory_tier: str = "short" # 'short', 'medium', 'long'
    importance: float = 0.5
    access_count: int = 0
    last_accessed_at: float = Field(default_factory=time.time)
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    relationships: Dict[str, List[str]] = Field(default_factory=dict) # e.g., {"parent_of": ["mem-xyz"]}
    parent_id: Optional[str] = None  # Explicit parent_id for hierarchical relationships

# ===================================================================
#         DATA ACCESS LAYER (DAL) / STORAGE MANAGER
#         (Pinagsamang logic mula sa MemoryManager PC2 at EpisodicMemoryAgent)
# ===================================================================
class MemoryStorageManager:
    """Handles all direct interactions with SQLite and Redis."""

    def __init__(self, db_path: str, redis_conn: Optional[redis.Redis]):
        self.db_path = db_path
        self.redis = redis_conn
        self.db_lock = threading.Lock()
        self._init_database()

    def _get_conn(self):
        """Creates a new database connection."""
        return sqlite3.connect(self.db_path, timeout=10)

    def _init_database(self):
        """CHECKLIST ITEM: Extend database schema & Add new tables"""
        with self.db_lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            # Main table for all memory entries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    memory_tier TEXT NOT NULL,
                    importance REAL,
                    access_count INTEGER,
                    last_accessed_at REAL,
                    created_at REAL,
                    expires_at REAL,
                    metadata TEXT,
                    tags TEXT,
                    relationships TEXT,
                    parent_id TEXT,
                    FOREIGN KEY(parent_id) REFERENCES memories(memory_id)
                )
            ''')
            
            # Create memory_relationships table for explicit relationships
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_memory_id TEXT NOT NULL,
                    target_memory_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    created_at REAL,
                    updated_at REAL,
                    FOREIGN KEY(source_memory_id) REFERENCES memories(memory_id),
                    FOREIGN KEY(target_memory_id) REFERENCES memories(memory_id)
                )
            ''')
            
            # Create context_groups table for organizing memories by context
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS context_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            ''')
            
            # Create memory_group_mappings for many-to-many relationships
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_group_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    created_at REAL,
                    FOREIGN KEY(memory_id) REFERENCES memories(memory_id),
                    FOREIGN KEY(group_id) REFERENCES context_groups(id)
                )
            ''')
            
            # Indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(memory_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mem_tier ON memories(memory_tier)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_id ON memories(parent_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_memory ON memory_relationships(source_memory_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_memory ON memory_relationships(target_memory_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_group ON memory_group_mappings(memory_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_memory ON memory_group_mappings(group_id)')
            
            conn.commit()
            conn.close()
            logger.info(f"Unified SQLite database initialized at {self.db_path}")

    def add_or_update_memory(self, memory: MemoryEntry) -> bool:
        """Adds a new memory or updates an existing one."""
        with self.db_lock:
            try:
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO memories (memory_id, content, memory_type, memory_tier, importance, access_count, last_accessed_at, created_at, expires_at, metadata, tags, relationships, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    memory.memory_id, memory.content, memory.memory_type, memory.memory_tier,
                    memory.importance, memory.access_count, memory.last_accessed_at,
                    memory.created_at, memory.expires_at,
                    json.dumps(memory.metadata), json.dumps(memory.tags), json.dumps(memory.relationships),
                    memory.parent_id
                ))
                conn.commit()
                self._cache_invalidate(memory.memory_id)
                return True
            except Exception as e:
                logger.error(f"DB Error on add/update: {e}")
                return False
            finally:
                conn.close()

    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieves a memory by its ID, using cache first."""
        cached = self._cache_get(memory_id)
        if cached:
            logger.debug(f"Cache HIT for memory_id: {memory_id}")
            return MemoryEntry(**cached)

        logger.debug(f"Cache MISS for memory_id: {memory_id}")
        with self.db_lock:
            try:
                conn = self._get_conn()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,))
                row = cursor.fetchone()
                if not row: return None

                memory_data = dict(row)
                # Deserialize JSON fields
                for field in ["metadata", "tags", "relationships"]:
                    if memory_data[field]: memory_data[field] = json.loads(memory_data[field])

                memory = MemoryEntry(**memory_data)
                self._cache_put(memory_id, memory.model_dump())
                return memory
            except Exception as e:
                logger.error(f"DB Error on get: {e}")
                return None
            finally:
                conn.close()
                
    def get_memory_children(self, parent_id: str) -> List[MemoryEntry]:
        """Get all child memories of a parent memory."""
        with self.db_lock:
            try:
                conn = self._get_conn()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM memories WHERE parent_id = ?", (parent_id,))
                rows = cursor.fetchall()
                
                children = []
                for row in rows:
                    memory_data = dict(row)
                    # Deserialize JSON fields
                    for field in ["metadata", "tags", "relationships"]:
                        if memory_data[field]: memory_data[field] = json.loads(memory_data[field])
                    children.append(MemoryEntry(**memory_data))
                return children
            except Exception as e:
                logger.error(f"DB Error on get_memory_children: {e}")
                return []
            finally:
                conn.close()
                
    def add_memory_relationship(self, source_id: str, target_id: str, relationship_type: str, strength: float = 1.0) -> bool:
        """Add an explicit relationship between two memories."""
        with self.db_lock:
            try:
                now = time.time()
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO memory_relationships 
                    (source_memory_id, target_memory_id, relationship_type, strength, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (source_id, target_id, relationship_type, strength, now, now))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"DB Error on add_memory_relationship: {e}")
                return False
            finally:
                conn.close()
                
    def get_related_memories(self, memory_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all memories related to the specified memory."""
        with self.db_lock:
            try:
                conn = self._get_conn()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if relationship_type:
                    query = '''
                        SELECT r.*, m.* FROM memory_relationships r
                        JOIN memories m ON r.target_memory_id = m.memory_id
                        WHERE r.source_memory_id = ? AND r.relationship_type = ?
                    '''
                    cursor.execute(query, (memory_id, relationship_type))
                else:
                    query = '''
                        SELECT r.*, m.* FROM memory_relationships r
                        JOIN memories m ON r.target_memory_id = m.memory_id
                        WHERE r.source_memory_id = ?
                    '''
                    cursor.execute(query, (memory_id,))
                
                rows = cursor.fetchall()
                related = []
                for row in rows:
                    row_dict = dict(row)
                    related.append({
                        "relationship": {
                            "type": row_dict["relationship_type"],
                            "strength": row_dict["strength"],
                            "created_at": row_dict["created_at"]
                        },
                        "memory": {
                            "memory_id": row_dict["memory_id"],
                            "content": row_dict["content"],
                            "memory_type": row_dict["memory_type"],
                            "memory_tier": row_dict["memory_tier"],
                            "importance": row_dict["importance"]
                        }
                    })
                return related
            except Exception as e:
                logger.error(f"DB Error on get_related_memories: {e}")
                return []
            finally:
                conn.close()

    def get_all_memories_for_lifecycle(self) -> List[MemoryEntry]:
        """Fetches all non-long-term memories for decay and consolidation."""
        with self.db_lock:
            try:
                conn = self._get_conn()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM memories WHERE memory_tier != 'long'")
                rows = cursor.fetchall()
                memories = []
                for row in rows:
                    memory_data = dict(row)
                    for field in ["metadata", "tags", "relationships"]:
                        if memory_data[field]: memory_data[field] = json.loads(memory_data[field])
                    memories.append(MemoryEntry(**memory_data))
                return memories
            except Exception as e:
                logger.error(f"DB Error on get_all_memories: {e}")
                return []
            finally:
                conn.close()
                
    def create_context_group(self, name: str, description: Optional[str] = None) -> Optional[int]:
        """Create a new context group."""
        with self.db_lock:
            try:
                now = time.time()
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO context_groups (name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (name, description, now, now))
                group_id = cursor.lastrowid
                conn.commit()
                return group_id
            except Exception as e:
                logger.error(f"DB Error on create_context_group: {e}")
                return None
            finally:
                conn.close()
                
    def add_memory_to_group(self, memory_id: str, group_id: int) -> bool:
        """Add a memory to a context group."""
        with self.db_lock:
            try:
                now = time.time()
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO memory_group_mappings (memory_id, group_id, created_at)
                    VALUES (?, ?, ?)
                ''', (memory_id, group_id, now))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"DB Error on add_memory_to_group: {e}")
                return False
            finally:
                conn.close()

    # --- Caching Logic (mula sa CacheManager) ---
    def _cache_get(self, memory_id: str) -> Optional[Dict]:
        try:
            if self.redis and self.redis.exists(f"mem:{memory_id}"):
                data = self.redis.get(f"mem:{memory_id}")
                if data:  # Check if data is not None
                    return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis GET error: {e}")
        return None

    def _cache_put(self, memory_id: str, data: Dict, ttl: int = 3600):
        try:
            if self.redis:
                self.redis.setex(f"mem:{memory_id}", ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Redis PUT error: {e}")

    def _cache_invalidate(self, memory_id: str):
        try:
            if self.redis:
                self.redis.delete(f"mem:{memory_id}")
        except Exception as e:
            logger.warning(f"Redis DELETE error: {e}")

# ===================================================================
#         MEMORY ORCHESTRATOR (Ang Final, Unified Agent)
# ===================================================================
class MemoryOrchestratorService(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()

    """
    The central, unified memory system.
    - Manages all memory types (interaction, episodic, knowledge).
    - Implements a hierarchical, tiered storage system (short, medium, long).
    - Handles memory lifecycle: decay, consolidation, and summarization.
    - Provides a unified API for all other agents.
    """

    def __init__(self, **kwargs):
        super().__init__(name="MemoryOrchestratorService", port=DEFAULT_PORT, **kwargs)

        # --- Backend Initialization ---
        self.redis_conn: Optional[redis.Redis] = None
        try:
            self.redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
            self.redis_conn.ping()
            logger.info("Successfully connected to Redis.")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Caching will be disabled.")

        # Initialize storage with Redis (which might be None, but the manager handles that case)
        self.storage = MemoryStorageManager(db_path=DB_PATH, redis_conn=self.redis_conn)
        
        # --- Memory Decay Configuration ---
        self.decay_rates = {
            "short": 0.1,   # 10% decay per day for short-term memories
            "medium": 0.05, # 5% decay per day for medium-term memories
            "long": 0.01    # 1% decay per day for long-term memories
        }
        
        # Thresholds for memory tier promotion/demotion
        self.tier_thresholds = {
            "short_to_medium": 0.4,  # When importance drops below 0.4, promote short -> medium
            "medium_to_long": 0.2    # When importance drops below 0.2, promote medium -> long
        }
        
        # ✅ Using BaseAgent's built-in error reporting (UnifiedErrorHandler)

        # --- Lifecycle Management ---
        self.lifecycle_thread = threading.Thread(target=self._run_lifecycle_management, daemon=True)
        self.lifecycle_thread.start()

        logger.info("Unified MemoryOrchestratorService initialized successfully.")

    # -------------------------------------------------
    # Health check override with real DB/Redis/ZMQ tests
    # -------------------------------------------------
    def _get_health_status(self) -> Dict[str, Any]:
        """Return detailed health diagnostics including database, cache and ZMQ checks."""
        base_status = super()._get_health_status()

        # SQLite check
        db_connected = False
        try:
            conn = sqlite3.connect(DB_PATH, timeout=2)
            conn.execute("SELECT 1")
            conn.close()
            db_connected = True
        except Exception as db_err:
            logger.error(f"Health check: SQLite connection error: {db_err}")

        # Redis check
        redis_connected = False
        if self.redis_conn:
            try:
                self.redis_conn.ping()
                redis_connected = True
            except Exception as redis_err:
                logger.error(f"Health check: Redis ping failed: {redis_err}")

        # Error bus (ZMQ) PUB socket presence
        error_bus_ready = self.error_bus_pub is not None

        # Aggregate status
        overall_status = "ok" if all([db_connected, redis_connected, error_bus_ready]) else "degraded"

        # Add details
        base_status.update({
            "status": overall_status,
            "db_connected": db_connected,
            "redis_connected": redis_connected,
            "error_bus_ready": error_bus_ready,
        })
        return base_status

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point. Dispatches requests to the correct handler."""
        action = request.get("action")
        data = request.get("data", {})
        handlers = {
            "add_memory": self.add_memory,
            "get_memory": self.get_memory,
            "get_children": self.get_memory_children,
            "add_relationship": self.add_memory_relationship,
            "get_related": self.get_related_memories,
            "search_memory": self.search_memory,
            "update_memory": self.update_memory,
            "delete_memory": self.delete_memory,
            "reinforce_memory": self.reinforce_memory,
            "create_context_group": self.create_context_group,
            "add_to_group": self.add_to_group,
            "get_memories_by_group": self.get_memories_by_group,
            "semantic_search": self.semantic_search,
            "batch_add_memories": self.batch_add_memories,
            "batch_get_memories": self.batch_get_memories
        }
        handler = handlers.get(action)
        if handler:
            return handler(data)
        return {"status": "error", "message": f"Unknown action: {action}"}

    # --- Public API Methods ---
    def add_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            memory_data = data.copy()
            # Set default values if not provided
            if "memory_tier" not in memory_data:
                memory_data["memory_tier"] = "short"
            if "importance" not in memory_data:
                memory_data["importance"] = 1.0  # Start with maximum importance
            
            memory = MemoryEntry(**memory_data)
            success = self.storage.add_or_update_memory(memory)
            if success:
                return {"status": "success", "memory_id": memory.memory_id}
            else:
                return {"status": "error", "message": "Failed to save memory to database."}
        except Exception as e:
            self.report_error("add_memory_error", str(e))
            return {"status": "error", "message": f"Invalid memory format: {e}"}

    def get_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        memory_id = data.get("memory_id")
        if not memory_id:
            return {"status": "error", "message": "memory_id is required."}
        memory = self.storage.get_memory(memory_id)
        if memory:
            # Update access count and last accessed time
            memory.access_count += 1
            memory.last_accessed_at = time.time()
            self.storage.add_or_update_memory(memory)
            return {"status": "success", "memory": memory.model_dump()}
        else:
            return {"status": "error", "message": f"Memory with ID {memory_id} not found."}
            
    def get_memory_children(self, data: Dict[str, Any]) -> Dict[str, Any]:
        parent_id = data.get("parent_id")
        if not parent_id:
            return {"status": "error", "message": "parent_id is required."}
        children = self.storage.get_memory_children(parent_id)
        return {
            "status": "success", 
            "children": [child.model_dump() for child in children]
        }
        
    def add_memory_relationship(self, data: Dict[str, Any]) -> Dict[str, Any]:
        source_id = data.get("source_id")
        target_id = data.get("target_id")
        relationship_type = data.get("relationship_type")
        strength = data.get("strength", 1.0)
        
        if not all([source_id, target_id, relationship_type]):
            return {"status": "error", "message": "source_id, target_id, and relationship_type are required."}
            
        # Type checking to ensure we have strings
        if not isinstance(source_id, str) or not isinstance(target_id, str) or not isinstance(relationship_type, str):
            return {"status": "error", "message": "source_id, target_id, and relationship_type must be strings."}
            
        success = self.storage.add_memory_relationship(source_id, target_id, relationship_type, strength)
        if success:
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Failed to create relationship."}
            
    def get_related_memories(self, data: Dict[str, Any]) -> Dict[str, Any]:
        memory_id = data.get("memory_id")
        relationship_type = data.get("relationship_type")
        
        if not memory_id:
            return {"status": "error", "message": "memory_id is required."}
            
        related = self.storage.get_related_memories(memory_id, relationship_type)
        return {"status": "success", "related_memories": related}
        
    def search_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for memories based on text query.
        This is a basic implementation using SQLite's LIKE operator.
        A more advanced implementation would use vector embeddings.
        """
        query = data.get("query")
        memory_type = data.get("memory_type")
        limit = data.get("limit", 10)
        
        if not query:
            return {"status": "error", "message": "query is required."}
            
        try:
            with self.storage.db_lock:
                conn = self.storage._get_conn()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build the query
                sql_query = "SELECT * FROM memories WHERE content LIKE ?"
                params = [f"%{query}%"]
                
                if memory_type:
                    sql_query += " AND memory_type = ?"
                    params.append(memory_type)
                    
                sql_query += " ORDER BY importance DESC, last_accessed_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    memory_data = dict(row)
                    for field in ["metadata", "tags", "relationships"]:
                        if memory_data[field]: 
                            memory_data[field] = json.loads(memory_data[field])
                    results.append(memory_data)
                
                return {"status": "success", "results": results, "count": len(results)}
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            self.report_error("search_error", str(e))
            return {"status": "error", "message": f"Failed to search memories: {e}"}
            
    def semantic_search(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Semantic search using vector embeddings.
        This is a placeholder for a more advanced implementation.
        """
        query = data.get("query")
        k = data.get("k", 5)
        
        if not query:
            return {"status": "error", "message": "query is required."}
            
        # In a production implementation, this would:
        # 1. Generate embedding for the query
        # 2. Find nearest neighbors in vector space
        # 3. Return the matching memories
        
        # For now, we'll fall back to text search
        search_results = self.search_memory({
            "query": query,
            "limit": k
        })
        
        if search_results["status"] == "success":
            return {
                "status": "success", 
                "message": "Semantic search not fully implemented, falling back to text search",
                "results": search_results["results"]
            }
        else:
            return search_results
            
    def batch_add_memories(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add multiple memories in a single batch operation.
        """
        memories = data.get("memories", [])
        
        if not memories:
            return {"status": "error", "message": "No memories provided."}
            
        try:
            memory_ids = []
            for memory_data in memories:
                # Create a MemoryEntry for each item
                try:
                    memory = MemoryEntry(**memory_data)
                    success = self.storage.add_or_update_memory(memory)
                    if success:
                        memory_ids.append(memory.memory_id)
                except Exception as e:
                    logger.warning(f"Failed to add memory in batch: {e}")
                    
            return {
                "status": "success", 
                "message": f"Added {len(memory_ids)} memories",
                "memory_ids": memory_ids
            }
        except Exception as e:
            logger.error(f"Error in batch add: {e}")
            self.report_error("batch_add_error", str(e))
            return {"status": "error", "message": f"Batch operation failed: {e}"}
            
    def batch_get_memories(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve multiple memories in a single batch operation.
        """
        memory_ids = data.get("memory_ids", [])
        
        if not memory_ids:
            return {"status": "error", "message": "No memory_ids provided."}
            
        try:
            memories = []
            for memory_id in memory_ids:
                memory = self.storage.get_memory(memory_id)
                if memory:
                    # Update access count and last accessed time
                    memory.access_count += 1
                    memory.last_accessed_at = time.time()
                    self.storage.add_or_update_memory(memory)
                    memories.append(memory.model_dump())
                    
            return {
                "status": "success", 
                "memories": memories,
                "count": len(memories)
            }
        except Exception as e:
            logger.error(f"Error in batch get: {e}")
            self.report_error("batch_get_error", str(e))
            return {"status": "error", "message": f"Batch operation failed: {e}"}
            
    def update_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        memory_id = data.get("memory_id")
        update_data = data.get("update_data", {})
        
        if not memory_id:
            return {"status": "error", "message": "memory_id is required."}
            
        # Get existing memory
        memory = self.storage.get_memory(memory_id)
        if not memory:
            return {"status": "error", "message": f"Memory with ID {memory_id} not found."}
            
        # Update fields
        for key, value in update_data.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
                
        # Save updated memory
        success = self.storage.add_or_update_memory(memory)
        if success:
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Failed to update memory."}
            
    def delete_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete a memory and its relationships.
        """
        memory_id = data.get("memory_id")
        cascade = data.get("cascade", False)
        
        if not memory_id:
            return {"status": "error", "message": "memory_id is required."}
            
        try:
            with self.storage.db_lock:
                conn = self.storage._get_conn()
                cursor = conn.cursor()
                
                # First, check if the memory exists
                cursor.execute("SELECT memory_id FROM memories WHERE memory_id = ?", (memory_id,))
                if not cursor.fetchone():
                    return {"status": "error", "message": f"Memory with ID {memory_id} not found."}
                
                # If cascade is true, also delete child memories
                if cascade:
                    # Get all children
                    cursor.execute("SELECT memory_id FROM memories WHERE parent_id = ?", (memory_id,))
                    children = [row[0] for row in cursor.fetchall()]
                    
                    # Delete children recursively
                    for child_id in children:
                        self.delete_memory({"memory_id": child_id, "cascade": True})
                
                # Delete relationships
                cursor.execute("DELETE FROM memory_relationships WHERE source_memory_id = ? OR target_memory_id = ?", 
                               (memory_id, memory_id))
                
                # Delete group mappings
                cursor.execute("DELETE FROM memory_group_mappings WHERE memory_id = ?", (memory_id,))
                
                # Finally, delete the memory itself
                cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
                
                conn.commit()
                
                # Invalidate cache
                if self.redis_conn:
                    self.redis_conn.delete(f"mem:{memory_id}")
                
                return {"status": "success", "message": f"Memory {memory_id} deleted successfully."}
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            self.report_error("delete_error", str(e))
            return {"status": "error", "message": f"Failed to delete memory: {e}"}
        
    def reinforce_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reinforce a memory by increasing its importance and resetting decay.
        Based on the UnifiedMemoryReasoningAgent implementation.
        """
        memory_id = data.get("memory_id")
        reinforcement_factor = data.get("reinforcement_factor", 1.2)
        
        if not memory_id:
            return {"status": "error", "message": "memory_id is required."}
            
        # Get existing memory
        memory = self.storage.get_memory(memory_id)
        if not memory:
            return {"status": "error", "message": f"Memory with ID {memory_id} not found."}
            
        # Update importance score
        current_importance = memory.importance
        new_importance = min(current_importance * reinforcement_factor, 1.0)
        memory.importance = new_importance
        memory.last_accessed_at = time.time()
        
        # Save updated memory
        success = self.storage.add_or_update_memory(memory)
        if success:
            return {"status": "success", "new_importance": new_importance}
        else:
            return {"status": "error", "message": "Failed to reinforce memory."}
            
    def create_context_group(self, data: Dict[str, Any]) -> Dict[str, Any]:
        name = data.get("name")
        description = data.get("description")
        
        if not name:
            return {"status": "error", "message": "name is required."}
            
        group_id = self.storage.create_context_group(name, description)
        if group_id:
            return {"status": "success", "group_id": group_id}
        else:
            return {"status": "error", "message": "Failed to create context group."}
            
    def add_to_group(self, data: Dict[str, Any]) -> Dict[str, Any]:
        memory_id = data.get("memory_id")
        group_id = data.get("group_id")
        
        if not all([memory_id, group_id]):
            return {"status": "error", "message": "memory_id and group_id are required."}
            
        # Type checking to ensure we have the correct types
        if not isinstance(memory_id, str):
            return {"status": "error", "message": "memory_id must be a string."}
        
        try:
            # Convert group_id to int if it's not already
            group_id_int = int(group_id)
            success = self.storage.add_memory_to_group(memory_id, group_id_int)
            if success:
                return {"status": "success"}
            else:
                return {"status": "error", "message": "Failed to add memory to group."}
        except (ValueError, TypeError):
            return {"status": "error", "message": "group_id must be convertible to an integer."}
            
    def get_memories_by_group(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for group query functionality
        return {"status": "error", "message": "Group query functionality not yet implemented."}

    # --- Background Lifecycle Management ---
    def _run_lifecycle_management(self):
        """Periodically runs decay, consolidation, and summarization."""
        logger.info("Memory Lifecycle Management thread started.")
        while self.running:
            try:
                time.sleep(LIFECYCLE_INTERVAL)
                logger.info("Starting memory lifecycle cycle...")
                all_memories = self.storage.get_all_memories_for_lifecycle()
                memories_to_update = []

                for memory in all_memories:
                    # CHECKLIST ITEM: Memory Decay & Consolidation
                    updated_memory = self._apply_decay_and_consolidation(memory)
                    memories_to_update.append(updated_memory)

                # Batch update
                for mem in memories_to_update:
                    self.storage.add_or_update_memory(mem)
                logger.info(f"Lifecycle cycle complete. Processed {len(memories_to_update)} memories.")

            except Exception as e:
                logger.error(f"Error in lifecycle management thread: {e}", exc_info=True)
                self.report_error("lifecycle_error", str(e))

    def _apply_decay_and_consolidation(self, memory: MemoryEntry) -> MemoryEntry:
        """
        Applies decay and promotes memory to a new tier if needed.
        Enhanced implementation based on UnifiedMemoryReasoningAgent.
        """
        # Calculate age in days
        age_days = (time.time() - memory.created_at) / (24 * 3600)
        
        # Get decay rate based on memory tier
        decay_rate = self.decay_rates.get(memory.memory_tier, 0.05)
        
        # Apply decay formula
        decay_factor = 1.0 - (decay_rate * age_days)
        memory.importance *= decay_factor
        memory.importance = max(0.0, min(1.0, memory.importance))  # Ensure it stays between 0 and 1
        
        # Check for tier promotion based on importance thresholds
        if memory.memory_tier == "short" and memory.importance < self.tier_thresholds["short_to_medium"]:
            # Find related memories for possible consolidation
            related_memories = self._find_related_memories(memory)
            
            if len(related_memories) >= 3:
                # If we have enough related memories, create a consolidated summary
                consolidated_memory = self._create_consolidated_memory(memory, related_memories)
                memory.memory_tier = "medium"
                
                # Link the original memory to the consolidated one
                if consolidated_memory:
                    self.storage.add_memory_relationship(
                        memory.memory_id,
                        consolidated_memory.memory_id,
                        "consolidated_into",
                        1.0
                    )
            else:
                # Just promote the tier without consolidation
                memory.memory_tier = "medium"
                memory.content = self._summarize_content(memory.content)
                logger.debug(f"Promoting memory {memory.memory_id} to medium tier.")
                
        elif memory.memory_tier == "medium" and memory.importance < self.tier_thresholds["medium_to_long"]:
            memory.memory_tier = "long"
            memory.content = self._summarize_content(memory.content)
            logger.debug(f"Promoting memory {memory.memory_id} to long tier.")

        return memory
        
    def _find_related_memories(self, memory: MemoryEntry) -> List[MemoryEntry]:
        """Find memories related to the given memory for consolidation."""
        # This is a simplified implementation
        # In a production system, this would use semantic similarity or other advanced techniques
        related = []
        
        # Check for memories with the same parent
        if memory.parent_id:
            siblings = self.storage.get_memory_children(memory.parent_id)
            related.extend([m for m in siblings if m.memory_id != memory.memory_id])
            
        # Check for memories with explicit relationships
        explicit_relationships = self.storage.get_related_memories(memory.memory_id)
        for rel in explicit_relationships:
            if "memory" in rel and "memory_id" in rel["memory"]:
                related_memory = self.storage.get_memory(rel["memory"]["memory_id"])
                if related_memory:
                    related.append(related_memory)
                    
        return related
        
    def _create_consolidated_memory(self, primary_memory: MemoryEntry, related_memories: List[MemoryEntry]) -> Optional[MemoryEntry]:
        """Create a consolidated memory from a group of related memories."""
        try:
            # Combine content from all memories
            contents = [primary_memory.content] + [m.content for m in related_memories]
            combined_content = "\n\n".join(contents)
            
            # Create a summary
            summary = self._summarize_content(combined_content)
            
            # Create the consolidated memory
            consolidated = MemoryEntry(
                content=summary,
                memory_type="consolidated",
                memory_tier="medium",
                importance=0.7,  # Start with higher importance for consolidated memories
                metadata={
                    "consolidated_from": [primary_memory.memory_id] + [m.memory_id for m in related_memories],
                    "consolidation_date": time.time()
                }
            )
            
            # Save the consolidated memory
            success = self.storage.add_or_update_memory(consolidated)
            if success:
                return consolidated
            return None
        except Exception as e:
            logger.error(f"Error creating consolidated memory: {e}")
            return None

    def _summarize_content(self, content: str) -> str:
        """
        A placeholder for a summarization call to an LLM.
        (Logic inspired by UnifiedMemoryReasoningAgent)
        """
        # In a real implementation, this would call a language model for summarization
        if len(content) > 200:
            return f"Summary: {content[:100]}... (length: {len(content)})"
        return content
        
    # ✅ Using BaseAgent.report_error() instead of custom method

if __name__ == '__main__':
    try:
        agent = MemoryOrchestratorService()
        agent.run()
    except KeyboardInterrupt:
        logger.info("MemoryOrchestratorService shutting down.")
    except Exception as e:
        logger.critical(f"MemoryOrchestratorService failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup()
