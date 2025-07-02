"""
Knowledge Base Agent implementation
Manages and provides access to the system's knowledge base
"""

import zmq
import json
import logging
import threading
import time
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
from main_pc_code.utils.config_loader import load_config
from src.core.base_agent import BaseAgent
import psutil

# Load configuration at module level
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('knowledge_base.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('KnowledgeBase')

class KnowledgeBase(BaseAgent):
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = config.get("port", 5571) if port is None else port
        agent_name = config.get("name", "KnowledgeBase")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Initialize database tracking
        self.db_path = os.path.join("data", "knowledge.db")
        self.fact_count = 0
        self.db_status = False
        self.start_time = time.time()
        
        # Initialize flags and events
        self.initialized = False
        self.initialization_error = None
        self.is_initialized = threading.Event()
        
        # Start initialization in background
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        
    def _perform_initialization(self):
        """Perform agent initialization in background."""
        try:
            # Initialize database
            self._init_database()
            
            # Mark as initialized
            self.initialized = True
            self.is_initialized.set()
            logger.info("KnowledgeBase initialization complete")
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Initialization failed: {e}")
            
    def _init_database(self):
        """Initialize SQLite database."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create facts table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on topic
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_facts_topic ON facts(topic)
            """)
            
            conn.commit()
            conn.close()
            
            self.db_status = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.db_status = False
            raise
            
    def _get_db_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        return conn, cursor
        
    def _get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status including database metrics."""
        base_status = super()._get_health_status()
        
        # Add database-specific metrics
        base_status.update({
            "db_status": self.db_status,
            "fact_count": self.fact_count,
            "db_path": self.db_path
        })
        
        return base_status
        
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        action = request.get("action")
        
        if action == "add_fact":
            topic = request.get("topic")
            content = request.get("content")
            
            if not topic or not content:
                return {"status": "error", "error": "Missing topic or content"}
                
            try:
                self.add_fact(topic, content)
                return {"status": "ok", "message": "Fact added successfully"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
                
        elif action == "query":
            topic = request.get("topic")
            
            if not topic:
                return {"status": "error", "error": "Missing topic"}
                
            try:
                facts = self.query_facts(topic)
                return {
                    "status": "ok",
                    "facts": facts
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
                
        return super().handle_request(request)
        
    def add_fact(self, topic: str, content: Union[Dict, List, str]) -> None:
        """Add a new fact to the knowledge base."""
        try:
            conn, cursor = self._get_db_connection()
            
            # Convert content to JSON string if it's a dict or list
            if isinstance(content, (dict, list)):
                content = json.dumps(content)
                
            cursor.execute(
                "INSERT INTO facts (topic, content) VALUES (?, ?)",
                (topic, content)
            )
            
            conn.commit()
            conn.close()
            
            self.fact_count += 1
            
        except Exception as e:
            logger.error(f"Error adding fact: {e}")
            raise
            
    def query_facts(self, topic: str) -> List[Dict]:
        """Query facts by topic."""
        try:
            conn, cursor = self._get_db_connection()
            
            cursor.execute(
                "SELECT id, topic, content, created_at, updated_at FROM facts WHERE topic = ?",
                (topic,)
            )
            
            facts = []
            for row in cursor.fetchall():
                fact = {
                    "id": row[0],
                    "topic": row[1],
                    "content": row[2],
                    "created_at": row[3],
                    "updated_at": row[4]
                }
                
                # Try to parse JSON content
                try:
                    fact["content"] = json.loads(fact["content"])
                except:
                    pass
                    
                facts.append(fact)
                
            conn.close()
            return facts
            
        except Exception as e:
            logger.error(f"Error querying facts: {e}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        try:
            # Check database connection if initialized
            if self.initialized:
                try:
                    conn, cursor = self._get_db_connection()
                    cursor.execute("SELECT COUNT(*) FROM facts")
                    self.fact_count = cursor.fetchone()[0]
                    conn.close()
                    self.db_status = True
                except Exception as e:
                    logger.error(f"Database health check failed: {e}")
                    self.db_status = False
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            self.db_status = False
            
        return {
            'status': 'success' if self.initialized and self.db_status else 'error',
            'ready': self.initialized and self.db_status,
            'initialized': self.initialized,
            'uptime': time.time() - self.start_time,
            'components': {
                'knowledge_store': self.db_status,
                'knowledge_retrieval': self.db_status,
                'knowledge_update': self.db_status
            },
            'fact_count': self.fact_count,
            'error': None if self.initialized and self.db_status else "Database not initialized or unhealthy"
        }
    
    def get_fact(self, topic: str) -> Dict[str, Any]:
        """Get a fact from the knowledge base.
        
        Args:
            topic: Topic of the fact to retrieve
            
        Returns:
            Dictionary with status and fact content
        """
        if not self.initialized:
            return {
                'status': 'error',
                'message': 'Knowledge base not initialized',
                'ready': False
            }
            
        try:
            facts = self.query_facts(topic)
            
            if not facts:
                return {
                    'status': 'warning',
                    'message': f'No facts found for topic: {topic}',
                    'facts': []
                }
                
            return {
                'status': 'success',
                'message': f'Found {len(facts)} facts for topic: {topic}',
                'facts': facts
            }
            
        except Exception as e:
            logger.error(f"Error retrieving fact: {e}")
            return {
                'status': 'error',
                'message': f'Error retrieving facts: {str(e)}'
            }
    
    def update_fact(self, topic: str, content: Union[Dict, List, str]) -> Dict[str, Any]:
        """Update facts for a given topic.
        
        Args:
            topic: Topic of the fact to update
            content: New content for the fact
            
        Returns:
            Dictionary with status and update results
        """
        if not self.initialized:
            return {
                'status': 'error',
                'message': 'Knowledge base not initialized',
                'ready': False
            }
            
        try:
            # First check if the fact exists
            facts = self.query_facts(topic)
            
            if not facts:
                # Create new fact if none exists
                self.add_fact(topic, content)
                return {
                    'status': 'success',
                    'message': 'New fact created',
                    'updated': 0,
                    'created': 1
                }
                
            # Update all existing facts for this topic
            conn, cursor = self._get_db_connection()
            
            # Convert content to JSON string if it's a dict or list
            if isinstance(content, (dict, list)):
                content = json.dumps(content)
                
            cursor.execute(
                """
                UPDATE facts
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE topic = ?
                """,
                (content, topic)
            )
            
            updated_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return {
                'status': 'success',
                'message': f'Updated {updated_count} facts',
                'updated': updated_count,
                'created': 0
            }
            
        except Exception as e:
            logger.error(f"Error updating fact: {e}")
            return {
                'status': 'error',
                'message': f'Error updating facts: {str(e)}'
            }
    
    def search_facts(self, query: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Search facts by keyword in topic or content.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with status and search results
        """
        if not self.initialized:
            return {
                'status': 'error',
                'message': 'Knowledge base not initialized',
                'ready': False
            }
            
        try:
            conn, cursor = self._get_db_connection()
            
            if query:
                # Search for query in topic or content
                cursor.execute(
                    """
                    SELECT id, topic, content, created_at, updated_at
                    FROM facts
                    WHERE topic LIKE ? OR content LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", limit)
                )
            else:
                # Return most recent facts
                cursor.execute(
                    """
                    SELECT id, topic, content, created_at, updated_at
                    FROM facts
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                
            facts = []
            for row in cursor.fetchall():
                fact = {
                    "id": row[0],
                    "topic": row[1],
                    "content": row[2],
                    "created_at": row[3],
                    "updated_at": row[4]
                }
                
                # Try to parse JSON content
                try:
                    fact["content"] = json.loads(fact["content"])
                except:
                    pass
                    
                facts.append(fact)
                
            conn.close()
            
            return {
                'status': 'success',
                'message': f'Found {len(facts)} results',
                'facts': facts
            }
            
        except Exception as e:
            logger.error(f"Error searching facts: {e}")
            return {
                'status': 'error',
                'message': f'Error searching facts: {str(e)}'
            }
    
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests and dispatch to appropriate handlers."""
        logger.info(f"Received request: {request}")
        
        action = request.get('action')
        
        if action == 'get_fact':
            return self.get_fact(request.get('topic', ''))
            
        elif action == 'add_fact':
            try:
                self.add_fact(request.get('topic', ''), request.get('content', ''))
                return {'status': 'success', 'message': 'Fact added successfully'}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}
                
        elif action == 'update_fact':
            return self.update_fact(request.get('topic', ''), request.get('content', ''))
            
        elif action == 'search_facts':
            query = request.get('query')
            query_str = query if query is not None else ""
            limit = request.get('limit', 10)
            return self.search_facts(query_str, limit)
            
        elif action == 'get_health':
            return self.get_health_status()
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Shutting down Knowledge Base Agent")
        super().cleanup()

    def health_check(self):
        """Perform a health check and return status."""
        try:
            is_healthy = self.initialized and self.db_status
            
            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "fact_count": self.fact_count,
                    "db_status": "active" if self.db_status else "inactive",
                    "database_path": self.db_path
                }
            }
            return status_report
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = KnowledgeBase()
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