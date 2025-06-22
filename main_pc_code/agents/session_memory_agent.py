from src.core.base_agent import BaseAgent
"""
Session Memory Agent
------------------
Maintains context memory and session awareness:
- Stores conversation history
- Provides context for LLM prompts
- Manages user sessions
- Supports semantic search of past interactions
"""

import zmq
import json
import logging
import time
import threading
import os
import sys
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Import the MemoryClient for new orchestrator
try:
    from src.memory.memory_client import MemoryClient
except Exception as import_error:
    import logging, uuid, time
    logging.warning(f"[SessionMemoryAgent] Falling back to stub MemoryClient due to import error: {import_error}")
    class MemoryClient:  # type: ignore
        """Lightweight stub when full MemoryClient cannot be imported."""
        def __init__(self):
            self._agent_id = "stub"
            self._session_id = None
        # API mirrors expected methods but only logs actions.
        def set_agent_id(self, agent_id):
            self._agent_id = agent_id
        def set_session_id(self, session_id):
            self._session_id = session_id
        def create_session(self, user_id, session_metadata=None, session_type="conversation"):
            sid = self._session_id or str(uuid.uuid4())
            return {"status": "success", "data": {"session_id": sid}}
        def create_memory(self, memory_type, content, tags=None):
            return {"status": "success"}
        def batch_read(self, memory_type, limit=50, sort_field="created_at", sort_order="desc"):
            return {"status": "success", "data": {"memories": []}}
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('session_memory_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
ZMQ_MEMORY_PORT = 5574  # Port for session memory requests
ZMQ_HEALTH_PORT = 6583  # Health status

# Memory settings
MAX_CONTEXT_TOKENS = 2000  # Maximum tokens for context
MAX_SESSIONS = 100  # Maximum number of active sessions
SESSION_TIMEOUT = 3600  # Session timeout in seconds (1 hour)
DB_PATH = "data/session_memory.db"  # SQLite database path

class SessionMemoryAgent(BaseAgent):
    def _get_default_port(self) -> int:
        """Return default port for SessionMemoryAgent."""
        return ZMQ_MEMORY_PORT
    """Agent for maintaining context memory and session awareness."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="SessionMemoryAgent")
        self.port = port or ZMQ_MEMORY_PORT
        # Define health broadcast port
        self.health_port = ZMQ_HEALTH_PORT
        self.running = True
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {"core": False}
        }
        # Ensure sessions dict exists before any background thread starts
        self.sessions = {}
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        logger.info("SessionMemoryAgent basic init complete, async init started")
        
        # Initialize state
        self.sessions = {}  # Session ID -> session data
        self.health_thread = None
        self.cleanup_thread = None
        
        # Initialize Memory Orchestrator client
        self.memory_client = MemoryClient()
        self.memory_client.set_agent_id("session_memory_agent")
        
        # Initialize database for dual-write during migration
        self._init_database()
    
    def _perform_initialization(self):
        try:
            # Initialize core components (sockets, threads, etc.)
            self._init_components()
            self.initialization_status["components"]["core"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logger.info("SessionMemoryAgent initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logger.error(f"Initialization error: {e}")

    def _init_components(self):
        """Initialize core runtime components (runs in background thread)."""
        # Start cleanup loop thread
        self.cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("SessionMemoryAgent cleanup loop started")
        # Initialize custom sockets for memory and health broadcast
        self._setup_sockets()
        # Start health broadcast loop
        self.health_thread = threading.Thread(target=self.health_broadcast_loop, daemon=True)
        self.health_thread.start()
        logger.info("SessionMemoryAgent health broadcast loop started")
    
    def _setup_sockets(self):
        """Set up ZMQ sockets."""
        try:
            # Main REP socket already created by BaseAgent; only create PUB health socket here.
            # Create dedicated PUB socket for broadcast (separate from BaseAgent REP)
            if not hasattr(self, 'health_pub_socket'):
                self.health_pub_socket = self.context.socket(zmq.PUB)
                self.health_pub_socket.bind(f"tcp://*:{self.health_port}")
                logger.info(f"SessionMemoryAgent health PUB bound on port {self.health_port}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
    def _init_database(self):
        """Initialize the SQLite database."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            
            # Connect to database
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT,
                    last_active TEXT,
                    metadata TEXT
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            self.conn.commit()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def _create_session(self, session_id, user_id, metadata=None):
        """Create a new session."""
        try:
            now = datetime.now().isoformat()
            
            # Use Memory Orchestrator
            try:
                # If we already have a session ID, set it for the client
                if session_id:
                    self.memory_client.set_session_id(session_id)
                
                # Create session in orchestrator (will create a new one if no session_id)
                response = self.memory_client.create_session(
                    user_id=user_id,
                    session_metadata=metadata or {},
                    session_type="conversation"
                )
                
                # If no session_id was provided, get the one from the response
                if not session_id and response.get("status") == "success":
                    session_id = response.get("data", {}).get("session_id")
                    self.memory_client.set_session_id(session_id)
            except Exception as orch_e:
                logger.error(f"Error creating session in orchestrator: {str(orch_e)}")
                # Continue with local storage as fallback
            
            # DUAL-WRITE: Also insert into database during migration
            self.cursor.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, now, now, json.dumps(metadata or {}))
            )
            self.conn.commit()
            
            # Add to in-memory cache
            self.sessions[session_id] = {
                "user_id": user_id,
                "created_at": now,
                "last_active": now,
                "metadata": metadata or {},
                "interactions": []
            }
            
            logger.info(f"Created new session {session_id} for user {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None
    
    def _get_session(self, session_id):
        """Get a session by ID."""
        # Check in-memory cache first
        if session_id in self.sessions:
            # Update last active time
            now = datetime.now().isoformat()
            self.sessions[session_id]["last_active"] = now
            
            # Update database
            self.cursor.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (now, session_id)
            )
            self.conn.commit()
            
            return self.sessions[session_id]
        
        # Try to load from database
        try:
            self.cursor.execute(
                "SELECT user_id, created_at, last_active, metadata FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = self.cursor.fetchone()
            
            if row:
                user_id, created_at, last_active, metadata_json = row
                
                # Update last active time
                now = datetime.now().isoformat()
                self.cursor.execute(
                    "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                    (now, session_id)
                )
                self.conn.commit()
                
                # Load interactions
                self.cursor.execute(
                    "SELECT timestamp, role, content, metadata FROM interactions WHERE session_id = ? ORDER BY timestamp",
                    (session_id,)
                )
                interactions = []
                for interaction_row in self.cursor.fetchall():
                    timestamp, role, content, interaction_metadata_json = interaction_row
                    interactions.append({
                        "timestamp": timestamp,
                        "role": role,
                        "content": content,
                        "metadata": json.loads(interaction_metadata_json)
                    })
                
                # Add to in-memory cache
                self.sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": created_at,
                    "last_active": now,
                    "metadata": json.loads(metadata_json),
                    "interactions": interactions
                }
                
                return self.sessions[session_id]
            
            return None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {str(e)}")
            return None
    
    def _add_interaction(self, session_id, role, content, metadata=None):
        """Add an interaction to a session."""
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Validate session
            if session_id not in self.sessions:
                session = self._get_session(session_id)
                if not session:
                    raise ValueError(f"Session {session_id} not found")
            
            # Get current time
            now = datetime.now().isoformat()
            
            # Use Memory Orchestrator
            try:
                # Ensure client has the correct session ID
                self.memory_client.set_session_id(session_id)
                
                # Create memory in orchestrator
                memory_content = {
                    "text": content,
                    "role": role,
                    "timestamp": now,
                    "source_agent": "session_memory_agent",
                    "metadata": metadata or {}
                }
                
                tags = ["conversation", role]
                if metadata and "tags" in metadata:
                    tags.extend(metadata["tags"])
                
                response = self.memory_client.create_memory(
                    memory_type="conversation",
                    content=memory_content,
                    tags=tags
                )
                
                if response.get("status") != "success":
                    logger.warning(f"Failed to add interaction to orchestrator: {response}")
            except Exception as orch_e:
                logger.error(f"Error adding interaction to orchestrator: {str(orch_e)}")
                # Continue with local storage as fallback
            
            # DUAL-WRITE: Also insert into database during migration
            self.cursor.execute(
                "INSERT INTO interactions (session_id, timestamp, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, now, role, content, json.dumps(metadata or {}))
            )
            self.conn.commit()
            
            # Add to in-memory cache
            interaction = {
                "timestamp": now,
                "role": role,
                "content": content,
                "metadata": metadata or {}
            }
            self.sessions[session_id]["interactions"].append(interaction)
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [SessionMemoryAgent] - [DatabaseWrite] - Duration: {duration_ms:.2f}ms")
            
            return True
        except Exception as e:
            logger.error(f"Error adding interaction: {str(e)}")
            return False
    
    def _get_context(self, session_id, max_tokens=MAX_CONTEXT_TOKENS):
        """Get conversation context for a session."""
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Try to get context from the Memory Orchestrator first
            try:
                # Ensure client has the correct session ID
                self.memory_client.set_session_id(session_id)
                
                # Search for recent conversations in this session
                response = self.memory_client.batch_read(
                    memory_type="conversation",
                    limit=50,  # Get enough interactions to cover our token limit
                    sort_field="created_at",
                    sort_order="desc"
                )
                
                if response.get("status") == "success":
                    memories = response.get("data", {}).get("memories", [])
                    
                    # Transform to our expected format
                    context = []
                    token_count = 0
                    
                    for memory in memories:
                        content = memory.get("content", {})
                        if "text" in content and "role" in content:
                            # Estimate tokens (rough approximation: 4 chars ~ 1 token)
                            interaction_tokens = len(content["text"]) // 4
                            
                            if token_count + interaction_tokens > max_tokens:
                                break
                            
                            context.append({
                                "role": content["role"],
                                "content": content["text"],
                                "timestamp": content.get("timestamp", memory.get("created_at"))
                            })
                            token_count += interaction_tokens
                    
                    # Reverse to get chronological order (since we sorted desc)
                    context.reverse()
                    
                    # If we got data from the orchestrator, return it
                    if context:
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(f"PERF_METRIC: [SessionMemoryAgent] - [OrchestratorRead] - Duration: {duration_ms:.2f}ms")
                        return context
                    
            except Exception as orch_e:
                logger.error(f"Error getting context from orchestrator: {str(orch_e)}")
                # Fall back to local storage
            
            # FALLBACK: If orchestrator fails or returns no data, use local storage
            
            # Validate session
            if session_id not in self.sessions:
                session = self._get_session(session_id)
                if not session:
                    return []
            
            # Get interactions from most recent to oldest
            interactions = list(reversed(self.sessions[session_id]["interactions"]))
            
            # Simple token counting (approximate)
            context = []
            token_count = 0
            
            for interaction in interactions:
                # Estimate tokens (rough approximation: 4 chars ~ 1 token)
                interaction_tokens = len(interaction["content"]) // 4
                
                if token_count + interaction_tokens > max_tokens:
                    break
                
                context.append({
                    "role": interaction["role"],
                    "content": interaction["content"],
                    "timestamp": interaction["timestamp"]
                })
                token_count += interaction_tokens
            
            # Reverse back to chronological order
            context.reverse()
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [SessionMemoryAgent] - [DatabaseRead] - Duration: {duration_ms:.2f}ms")
            
            return context
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return []
    
    def _clear_session(self, session_id):
        """Clear a session's interactions."""
        try:
            # Try to clear interactions in Memory Orchestrator
            try:
                # Ensure client has the correct session ID
                self.memory_client.set_session_id(session_id)
                
                # Use bulk_delete to remove all memories for this session
                response = self.memory_client.bulk_delete(
                    memory_type="conversation"
                )
                
                if response.get("status") != "success":
                    logger.warning(f"Failed to clear session in orchestrator: {response}")
            except Exception as orch_e:
                logger.error(f"Error clearing session in orchestrator: {str(orch_e)}")
                # Continue with local storage as fallback
            
            # DUAL-WRITE: Also clear from local database during migration
            self.cursor.execute(
                "DELETE FROM interactions WHERE session_id = ?",
                (session_id,)
            )
            self.conn.commit()
            
            # Clear in-memory cache
            if session_id in self.sessions:
                self.sessions[session_id]["interactions"] = []
            
            return True
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {str(e)}")
            return False
    
    def _delete_session(self, session_id):
        """Delete a session."""
        try:
            # Try to delete session in Memory Orchestrator
            try:
                # Ensure client has the correct session ID
                self.memory_client.set_session_id(session_id)
                
                # End the session in the orchestrator
                response = self.memory_client._send_request(
                    "end_session",
                    {
                        "archive": True,
                        "summary": "Session terminated by SessionMemoryAgent"
                    },
                    session_id
                )
                
                if response.get("status") != "success":
                    logger.warning(f"Failed to end session in orchestrator: {response}")
                    
                # Also delete all memories for this session
                delete_response = self.memory_client.bulk_delete(memory_type="conversation")
                if delete_response.get("status") != "success":
                    logger.warning(f"Failed to delete session memories in orchestrator: {delete_response}")
                    
            except Exception as orch_e:
                logger.error(f"Error deleting session in orchestrator: {str(orch_e)}")
                # Continue with local storage as fallback
            
            # DUAL-WRITE: Also delete from local database during migration
            # Delete from database
            self.cursor.execute(
                "DELETE FROM interactions WHERE session_id = ?",
                (session_id,)
            )
            self.cursor.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            self.conn.commit()
            
            # Remove from in-memory cache
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    def _cleanup_sessions(self):
        """Clean up expired sessions."""
        try:
            now = datetime.now()
            
            # Get expired sessions
            self.cursor.execute(
                "SELECT session_id FROM sessions WHERE datetime(last_active) < datetime('now', '-1 hour')"
            )
            
            expired_sessions = [row[0] for row in self.cursor.fetchall()]
            
            # Delete expired sessions
            for session_id in expired_sessions:
                self._delete_session(session_id)
                logger.info(f"Deleted expired session {session_id}")
            
            # Limit number of sessions
            if len(self.sessions) > MAX_SESSIONS:
                # Get oldest sessions
                oldest_sessions = sorted(
                    self.sessions.items(),
                    key=lambda x: x[1]["last_active"]
                )[:len(self.sessions) - MAX_SESSIONS]
                
                # Delete oldest sessions
                for session_id, _ in oldest_sessions:
                    self._delete_session(session_id)
                    logger.info(f"Deleted oldest session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
    
    def handle_request(self, request):
        """Handle a request from the coordinator."""
        try:
            action = request.get("action", "")
            
            if action == "create_session":
                session_id = request.get("session_id", str(uuid.uuid4()))
                user_id = request.get("user_id", "default")
                metadata = request.get("metadata", {})
                
                result = self._create_session(session_id, user_id, metadata)
                
                return {
                    "status": "success" if result else "error",
                    "session_id": result,
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "add_interaction":
                session_id = request.get("session_id")
                role = request.get("role")
                content = request.get("content")
                metadata = request.get("metadata", {})
                
                if not session_id or not role or not content:
                    return {
                        "status": "error",
                        "message": "Missing required parameters",
                        "request_id": request.get("request_id", "")
                    }
                
                result = self._add_interaction(session_id, role, content, metadata)
                
                return {
                    "status": "success" if result else "error",
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "get_context":
                session_id = request.get("session_id")
                max_tokens = request.get("max_tokens", MAX_CONTEXT_TOKENS)
                
                if not session_id:
                    return {
                        "status": "error",
                        "message": "Missing session_id",
                        "request_id": request.get("request_id", "")
                    }
                
                context = self._get_context(session_id, max_tokens)
                
                return {
                    "status": "success",
                    "context": context,
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "clear_session":
                session_id = request.get("session_id")
                
                if not session_id:
                    return {
                        "status": "error",
                        "message": "Missing session_id",
                        "request_id": request.get("request_id", "")
                    }
                
                result = self._clear_session(session_id)
                
                return {
                    "status": "success" if result else "error",
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "delete_session":
                session_id = request.get("session_id")
                
                if not session_id:
                    return {
                        "status": "error",
                        "message": "Missing session_id",
                        "request_id": request.get("request_id", "")
                    }
                
                result = self._delete_session(session_id)
                
                return {
                    "status": "success" if result else "error",
                    "request_id": request.get("request_id", "")
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "request_id": request.get("request_id", "")
                }
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "request_id": request.get("request_id", "")
            }

    def cleanup_loop(self):
        """Loop for cleaning up expired sessions."""
        while self.running:
            # Ensure cursor exists before cleanup
            if not hasattr(self, 'cursor'):
                time.sleep(1)
                continue
            try:
                self._cleanup_sessions()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
            
            # Sleep for a while
            time.sleep(60)  # Check every minute
    
    def health_broadcast_loop(self):
        """Loop for broadcasting health status."""
        while self.running:
            try:
                # Prepare health status
                status = {
                    "component": "session_memory_agent",
                    "status": "running",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "active_sessions": len(self.sessions),
                        "db_path": DB_PATH
                    }
                }
                
                # Publish health status via PUB socket
                self.health_pub_socket.send_json(status)
                
            except Exception as e:
                logger.error(f"Error broadcasting health status: {str(e)}")
            
            # Sleep for a while
            time.sleep(5)
    
    def run(self):
        logger.info("Starting SessionMemoryAgent main loop")
        while self.running:
            try:
                if hasattr(self, 'socket'):
                    if self.socket.poll(timeout=100):
                        message = self.socket.recv_json()
                        if message.get("action") == "health_check":
                            self.socket.send_json({
                                "status": "ok" if self.initialization_status["is_initialized"] else "initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        if not self.initialization_status["is_initialized"]:
                            self.socket.send_json({
                                "status": "error",
                                "error": "Agent is still initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        response = self.handle_request(message)
                        self.socket.send_json(response)
                    else:
                        time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    if hasattr(self, 'socket'):
                        self.socket.send_json({'status': 'error','message': str(e)})
                except Exception as zmq_err:
                    logger.error(f"ZMQ error while sending error response: {zmq_err}")
                    time.sleep(1)
    
    def stop(self):
        """Stop the session memory agent."""
        logger.info("Stopping session memory agent")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_pub_socket'):
            self.health_pub_socket.close()
        
        # Close database connection
        if hasattr(self, 'conn'):
            self.conn.close()
        
        # Wait for threads to finish
        if self.health_thread:
            self.health_thread.join(timeout=1.0)
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=1.0)
        
        logger.info("Session memory agent stopped")

if __name__ == "__main__":
    # Ensure agent binds REP on 5574
    agent = SessionMemoryAgent(port=ZMQ_MEMORY_PORT)
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        agent.stop()
