import json
import logging
import sqlite3
import time
import zmq
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ValidationError
import os
import redis

from common.core.base_agent import BaseAgent

# --- Pydantic Models ---
class MemoryRecord(BaseModel):
    memory_id: Optional[int] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None
    importance_score: float = 0.5
    created_at: Optional[str] = None

class AddMemoryRequest(BaseModel):
    action: str
    payload: MemoryRecord
    request_id: Optional[str] = None

class GetMemoryRequest(BaseModel):
    action: str
    memory_id: int
    request_id: Optional[str] = None

class SearchMemoryRequest(BaseModel):
    action: str
    query: str
    limit: int = 10
    request_id: Optional[str] = None

class UpdateMemoryRequest(BaseModel):
    action: str
    memory_id: int
    payload: Dict[str, Any]
    request_id: Optional[str] = None

class DeleteMemoryRequest(BaseModel):
    action: str
    memory_id: int
    request_id: Optional[str] = None

# --- Main Service ---
class MemoryOrchestratorService(BaseAgent):
    """
    MemoryOrchestratorService: Central memory hub. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, port: int = 7140, health_port: int = 7141, db_path: str = "memory_store.db"):
        super().__init__(name="MemoryOrchestratorService", port=port, health_check_port=health_port)
        self.db_path = db_path
        self.logger = logging.getLogger("MemoryOrchestratorService")
        
        # Initialize SQLite database
        self._init_database()
        
        # Initialize Redis for caching
        self._init_redis()
        
        # Initialize ZMQ sockets for pub/sub
        self._init_zmq_sockets()
        
        self.context = zmq.Context()
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
    
    def _init_database(self):
        """Initialize SQLite database with a simplified schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                metadata TEXT,
                importance_score REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        self.logger.info(f"SQLite database initialized at {self.db_path}")

    def _init_redis(self):
        """Initialize Redis connection for caching"""
        try:
            self.redis = redis.Redis(
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', 6379)),
                password=os.environ.get('REDIS_PASSWORD', None),
                decode_responses=False  # Keep as bytes for compatibility
            )
            self.redis.ping()  # Test connection
            self.logger.info("Connected to Redis server for caching")
            self.redis_available = True
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self.redis_available = False
            self.logger.warning("Running without cache - performance will be degraded")

    def _init_zmq_sockets(self):
        """Initialize ZMQ PUB socket for broadcasting updates"""
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{self.port+100}")
        self.logger.info(f"PUB socket bound to port {self.port+100}")

    def _broadcast_update(self, event_type: str, data: dict):
        """Broadcast memory updates to subscribers"""
        try:
            msg = event_type + ' ' + json.dumps(data)
            self.pub_socket.send_string(msg)
        except Exception as e:
            self.report_error('broadcast_error', str(e))

    def _cache_get(self, memory_id):
        """Get a memory from the Redis cache"""
        if not self.redis_available:
            return None
            
        try:
            key = f"memory:{memory_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
            return None

    def _cache_put(self, memory_id, data, ttl=3600):
        """Put a memory in the Redis cache"""
        if not self.redis_available:
            return
            
        try:
            key = f"memory:{memory_id}"
            self.redis.setex(key, ttl, json.dumps(data))
        except Exception as e:
            self.logger.error(f"Cache put error: {e}")

    def _cache_invalidate(self, memory_id):
        """Invalidate a memory in the Redis cache"""
        if not self.redis_available:
            return
            
        try:
            key = f"memory:{memory_id}"
            self.redis.delete(key)
        except Exception as e:
            self.logger.error(f"Cache invalidate error: {e}")

    def run(self):
        """Start the service"""
        self.logger.info("MemoryOrchestratorService started")
        super().run()  # Use BaseAgent's request loop

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests"""
        action = request.get("action")
        if action == "add_memory":
            return self.handle_add_memory(request)
        elif action == "get_memory":
            return self.handle_get_memory(request)
        elif action == "search_memory":
            return self.handle_search_memory(request)
        elif action == "update_memory":
            return self.handle_update_memory(request)
        elif action == "delete_memory":
            return self.handle_delete_memory(request)
        elif action in ["ping", "health", "health_check"]:
            return {"status": "ok"}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def handle_add_memory(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add memory request"""
        try:
            # Validate request
            add_request = AddMemoryRequest(**request)
            memory = add_request.payload
            
            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(memory.metadata) if memory.metadata else None
            
            cursor.execute(
                'INSERT INTO memory_entries (content, metadata, importance_score) VALUES (?, ?, ?)',
                (memory.content, metadata_json, memory.importance_score)
            )
            memory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Get the complete memory record
            result = self.handle_get_memory({"action": "get_memory", "memory_id": memory_id})
            
            # Broadcast update
            self._broadcast_update("memory_added", {"memory_id": memory_id})
            
            return {"status": "success", "memory_id": memory_id}
        except ValidationError as e:
            self.report_error('validation_error', str(e))
            return {"status": "error", "message": f"Validation error: {str(e)}"}
        except Exception as e:
            self.report_error('db_error', str(e))
            return {"status": "error", "message": str(e)}

    def handle_get_memory(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get memory request"""
        try:
            memory_id = request.get("memory_id")
            if not memory_id:
                return {"status": "error", "message": "Missing memory_id"}
            
            # Try to get from cache first
            cached_memory = self._cache_get(memory_id)
            if cached_memory:
                self.logger.debug(f"Cache hit for memory_id {memory_id}")
                return {"status": "success", "memory": cached_memory, "source": "cache"}
            
            # If not in cache, get from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memory_entries WHERE memory_id = ?', (memory_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"status": "error", "message": f"Memory with ID {memory_id} not found"}
            
            # Convert row to dictionary
            columns = ['memory_id', 'content', 'metadata', 'importance_score', 'created_at']
            memory = dict(zip(columns, row))
            
            # Parse metadata JSON if present
            if memory.get("metadata"):
                try:
                    memory["metadata"] = json.loads(memory["metadata"])
                except Exception:
                    memory["metadata"] = {}
            
            # Cache the result
            self._cache_put(memory_id, memory)
            
            return {"status": "success", "memory": memory, "source": "database"}
        except Exception as e:
            self.report_error('db_error', str(e))
            return {"status": "error", "message": str(e)}

    def handle_search_memory(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search memory request"""
        try:
            query = request.get("query", "")
            limit = request.get("limit", 10)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Simple text search using LIKE
            cursor.execute(
                'SELECT * FROM memory_entries WHERE content LIKE ? ORDER BY importance_score DESC LIMIT ?',
                (f'%{query}%', limit)
            )
            rows = cursor.fetchall()
            columns = ['memory_id', 'content', 'metadata', 'importance_score', 'created_at']
            
            results = []
            for row in rows:
                memory = dict(zip(columns, row))
                if memory.get("metadata"):
                    try:
                        memory["metadata"] = json.loads(memory["metadata"])
                    except Exception:
                        memory["metadata"] = {}
                results.append(memory)
            
            conn.close()
            return {"status": "success", "results": results}
        except Exception as e:
            self.report_error('db_error', str(e))
            return {"status": "error", "message": str(e)}

    def handle_update_memory(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update memory request"""
        try:
            memory_id = request.get("memory_id")
            updates = request.get("payload", {})
            
            if not memory_id or not updates:
                return {"status": "error", "message": "Missing memory_id or update payload"}
            
            # Validate that memory exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM memory_entries WHERE memory_id = ?', (memory_id,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                conn.close()
                return {"status": "error", "message": f"Memory with ID {memory_id} not found"}
            
            # Build update query
            set_clauses = []
            params = []
            
            if "content" in updates:
                set_clauses.append("content = ?")
                params.append(updates["content"])
            
            if "metadata" in updates:
                set_clauses.append("metadata = ?")
                params.append(json.dumps(updates["metadata"]))
            
            if "importance_score" in updates:
                set_clauses.append("importance_score = ?")
                params.append(updates["importance_score"])
            
            if not set_clauses:
                conn.close()
                return {"status": "error", "message": "No valid fields to update"}
            
            # Execute update
            query = f"UPDATE memory_entries SET {', '.join(set_clauses)} WHERE memory_id = ?"
            params.append(memory_id)
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            # Invalidate cache
            self._cache_invalidate(memory_id)
            
            # Broadcast update
            self._broadcast_update("memory_updated", {"memory_id": memory_id})
            
            return {"status": "success", "message": f"Memory {memory_id} updated successfully"}
        except Exception as e:
            self.report_error('db_error', str(e))
            return {"status": "error", "message": str(e)}

    def handle_delete_memory(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete memory request"""
        try:
            memory_id = request.get("memory_id")
            
            if not memory_id:
                return {"status": "error", "message": "Missing memory_id"}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM memory_entries WHERE memory_id = ?', (memory_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            # Invalidate cache
            self._cache_invalidate(memory_id)
            
            # Broadcast deletion
            if deleted:
                self._broadcast_update("memory_deleted", {"memory_id": memory_id})
                return {"status": "success", "message": f"Memory {memory_id} deleted successfully"}
            else:
                return {"status": "error", "message": f"Memory with ID {memory_id} not found"}
        except Exception as e:
            self.report_error('db_error', str(e))
            return {"status": "error", "message": str(e)}
    
    def stop(self):
        """Stop the service"""
        self.logger.info("Stopping MemoryOrchestratorService")
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'redis') and self.redis_available:
            self.redis.close()
        # BaseAgent may not have a stop method, so use try/except
        try:
            super().stop()
        except AttributeError:
            pass 

    def report_error(self, error_type, message, severity="ERROR", context=None):
        error_data = {
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        try:
            msg = json.dumps(error_data).encode('utf-8')
            self.error_bus_pub.send_multipart([b"ERROR:", msg])
        except Exception as e:
            print(f"Failed to publish error to Error Bus: {e}") 