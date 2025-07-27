import zmq
import json
import logging
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
import os


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))))
from common.utils.path_manager import PathManager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from src.agents.pc2.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env


# Load configuration at the module level
config = load_config()# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "memory_manager.log"))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemoryManager(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port: int = 7110, health_port: int = 7111):
         super().__init__(name="MemoryManager", port=7110)
"""Initialize the MemoryManager with ZMQ socket and database."""
        self.port = port
        self.health_port = health_port
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        
        # Setup sockets first for immediate health check availability
        self._setup_sockets()
        
        # Start health check endpoint immediately
        self._start_health_check()
        
        # Start initialization in background thread
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        
        logger.info(f"MemoryManager starting on port {port} (health: {health_port})")
    
    def _setup_sockets(self):
        """Setup ZMQ sockets."""
        # Main socket for handling requests
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"MemoryManager main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {str(e)}")
            raise
        
        # Health check socket
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check endpoint on port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check to port {self.health_port}: {str(e)}")
            raise
    
    def _start_health_check(self):
        """Start health check endpoint in background thread."""
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'MemoryManager',
                            'initialization_status': 'complete' if self.initialized else 'in_progress',
                            'port': self.port,
                            'health_port': self.health_port,
                            'timestamp': datetime.now().isoformat()
                        }
                        if self.initialization_error:
                            response['initialization_error'] = str(self.initialization_error)
                    else:
                        response = {
                            'status': 'unknown_action',
                            'message': f"Unknown action: {request.get('action', 'none')}"
                        }
                    self.health_socket.send_json(response)
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                    time.sleep(1)
        
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()
    
    def _initialize_background(self):
        """Initialize agent components in background thread."""
        try:
            # Initialize database
            self.db_path = str(PathManager.get_data_dir() / "memory_store.db")
            self._init_database()
            
            # Connect to UnifiedMemoryReasoningAgent
            self.umra_socket = self.context.socket(zmq.REQ)
            self.umra_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5596")
            
            self.initialized = True
            logger.info("MemoryManager initialization completed")
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"MemoryManager initialization failed: {str(e)}")
    
    def _init_database(self):
        """Initialize SQLite database for memory management."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memory tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'general',
                importance_score REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_relationships (
                relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_memory_id INTEGER,
                target_memory_id INTEGER,
                relationship_type TEXT,
                strength REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_memory_id) REFERENCES memory_entries(memory_id),
                FOREIGN KEY (target_memory_id) REFERENCES memory_entries(memory_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_category_assignments (
                memory_id INTEGER,
                category_id INTEGER,
                relevance_score REAL DEFAULT 1.0,
                FOREIGN KEY (memory_id) REFERENCES memory_entries(memory_id),
                FOREIGN KEY (category_id) REFERENCES memory_categories(category_id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(memory_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON memory_entries(importance_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON memory_entries(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON memory_entries(expires_at)')
        
        conn.commit()
        conn.close()
        logger.info("Memory database initialized")
    
    def store_memory(self, content: str, memory_type: str = 'general', 
                    importance_score: float = 0.5, metadata: Dict[str, Any] = None,
                    expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Store a new memory entry."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO memory_entries 
                (content, memory_type, importance_score, metadata, expires_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                content, memory_type, importance_score, 
                json.dumps(metadata) if metadata else None,
                expires_at.isoformat() if expires_at else None,
                datetime.now().isoformat()
            ))
            
            memory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Stored memory {memory_id}: {content[:50]}...")
            return {
                'status': 'success',
                'memory_id': memory_id,
                'message': 'Memory stored successfully'
            }
            
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def retrieve_memory(self, query: str = None, memory_type: str = None, 
                       limit: int = 10) -> Dict[str, Any]:
        """Retrieve memories based on query or type."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if query:
                # Search by content
                cursor.execute('''
                    SELECT memory_id, content, memory_type, importance_score, 
                           access_count, last_accessed, created_at, metadata
                    FROM memory_entries 
                    WHERE content LIKE ? AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY importance_score DESC, last_accessed DESC
                    LIMIT ?
                ''', (f'%{query}%', datetime.now().isoformat(), limit))
            elif memory_type:
                # Filter by type
                cursor.execute('''
                    SELECT memory_id, content, memory_type, importance_score, 
                           access_count, last_accessed, created_at, metadata
                    FROM memory_entries 
                    WHERE memory_type = ? AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY importance_score DESC, last_accessed DESC
                    LIMIT ?
                ''', (memory_type, datetime.now().isoformat(), limit))
            else:
                # Get all recent memories
                cursor.execute('''
                    SELECT memory_id, content, memory_type, importance_score, 
                           access_count, last_accessed, created_at, metadata
                    FROM memory_entries 
                    WHERE expires_at IS NULL OR expires_at > ?
                    ORDER BY importance_score DESC, last_accessed DESC
                    LIMIT ?
                ''', (datetime.now().isoformat(), limit))
            
            memories = []
            for row in cursor.fetchall():
                memory = {
                    'memory_id': row[0],
                    'content': row[1],
                    'memory_type': row[2],
                    'importance_score': row[3],
                    'access_count': row[4],
                    'last_accessed': row[5],
                    'created_at': row[6],
                    'metadata': json.loads(row[7]) if row[7] else {}
                }
                memories.append(memory)
                
                # Update access count and last accessed
                cursor.execute('''
                    UPDATE memory_entries 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE memory_id = ?
                ''', (datetime.now().isoformat(), row[0]))
            
            conn.commit()
            conn.close()
            
            return {
                'status': 'success',
                'memories': memories,
                'count': len(memories)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def update_memory_importance(self, memory_id: int, importance_score: float) -> Dict[str, Any]:
        """Update the importance score of a memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE memory_entries 
                SET importance_score = ?
                WHERE memory_id = ?
            ''', (importance_score, memory_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    'status': 'error',
                    'message': 'Memory not found'
                }
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated memory {memory_id} importance to {importance_score}")
            return {
                'status': 'success',
                'message': 'Memory importance updated'
            }
            
        except Exception as e:
            logger.error(f"Error updating memory importance: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def delete_expired_memories(self) -> Dict[str, Any]:
        """Delete memories that have expired."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM memory_entries 
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            ''', (datetime.now().isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted {deleted_count} expired memories")
            return {
                'status': 'success',
                'deleted_count': deleted_count,
                'message': f'Deleted {deleted_count} expired memories'
            }
            
        except Exception as e:
            logger.error(f"Error deleting expired memories: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total memories
            cursor.execute('SELECT COUNT(*) FROM memory_entries')
            total_memories = cursor.fetchone()[0]
            
            # Memories by type
            cursor.execute('''
                SELECT memory_type, COUNT(*) 
                FROM memory_entries 
                GROUP BY memory_type
            ''')
            memories_by_type = dict(cursor.fetchall())
            
            # Average importance
            cursor.execute('SELECT AVG(importance_score) FROM memory_entries')
            avg_importance = cursor.fetchone()[0] or 0.0
            
            # Expired memories
            cursor.execute('''
                SELECT COUNT(*) 
                FROM memory_entries 
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            ''', (datetime.now().isoformat(),))
            expired_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'success',
                'stats': {
                    'total_memories': total_memories,
                    'memories_by_type': memories_by_type,
                    'average_importance': avg_importance,
                    'expired_memories': expired_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'store_memory':
            return self.store_memory(
                content=request.get('content'),
                memory_type=request.get('memory_type', 'general'),
                importance_score=request.get('importance_score', 0.5),
                metadata=request.get('metadata'),
                expires_at=datetime.fromisoformat(request['expires_at']) if request.get('expires_at') else None
            )
        
        elif action == 'retrieve_memory':
            return self.retrieve_memory(
                query=request.get('query'),
                memory_type=request.get('memory_type'),
                limit=request.get('limit', 10)
            )
        
        elif action == 'update_importance':
            return self.update_memory_importance(
                memory_id=request.get('memory_id'),
                importance_score=request.get('importance_score')
            )
        
        elif action == 'delete_expired':
            return self.delete_expired_memories()
        
        elif action == 'get_stats':
            return self.get_memory_stats()
        
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop to handle incoming requests."""
        logger.info("Starting MemoryManager main loop")
        
        while True:
            try:
                # Wait for request with timeout
                if self.socket.poll(1000) > 0:  # 1 second timeout
                    request = self.socket.recv_json()
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                
                # Clean up expired memories periodically
                if time.time() % 3600 < 1:  # Every hour
                    self.delete_expired_memories()
                    
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to MemoryManager

        base_status.update({

            'service': 'MemoryManager',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()
    
    def shutdown(self):
        """Gracefully shutdown the manager."""
        self.socket.close()
        self.health_socket.close()
        if hasattr(self, 'umra_socket'):
            self.umra_socket.close()
        self.context.term()
        logger.info("MemoryManager shutdown complete")



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = MemoryManager()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()
