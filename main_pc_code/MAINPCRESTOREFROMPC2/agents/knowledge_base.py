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
from main_pc_code.utils.config_parser import parse_agent_args
from main_pc_code.src.core.base_agent import BaseAgent

_agent_args = parse_agent_args()

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
    def __init__(self, port: int = 5578, host: str = "localhost"):
        """Initialize Knowledge Base Agent.
        
        Args:
            port: Port to bind to (default: 5578)
            host: Host to bind to (default: localhost)
        """
        super().__init__(port=port, name="KnowledgeBase")
        
        # Initialize database tracking
        self.db_path = os.path.join("data", "knowledge.db")
        self.fact_count = 0
        self.db_status = False
        
        # Start initialization in background
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        
    def _perform_initialization(self):
        """Perform agent initialization in background."""
        try:
            # Initialize database
            self._init_database()
            
            # Mark as initialized
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
            return {'status': 'error', 'message': 'Knowledge base not initialized'}
            
        try:
            # Connect to database
            conn, cursor = self._get_db_connection()
            
            # Query for fact
            cursor.execute(
                "SELECT id, topic, content, created_at, updated_at FROM facts WHERE topic = ?",
                (topic,)
            )
            
            # Get result
            result = cursor.fetchone()
            
            # Close connection
            conn.close()
            
            if result:
                fact_id, topic, content_json, created_at, updated_at = result
                
                # Parse JSON content
                try:
                    content = json.loads(content_json)
                except json.JSONDecodeError:
                    content = {"value": content_json}
                
                logger.info(f"Retrieved fact: {topic}")
                
                return {
                    'status': 'success',
                    'fact': {
                        'id': fact_id,
                        'topic': topic,
                        'content': content,
                        'created_at': created_at,
                        'updated_at': updated_at
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': f"No fact found with topic '{topic}'"
                }
                
        except Exception as e:
            logger.error(f"Error retrieving fact: {e}")
            return {
                'status': 'error',
                'message': f"Failed to retrieve fact: {str(e)}"
            }
    
    def update_fact(self, topic: str, content: Union[Dict, List, str]) -> Dict[str, Any]:
        """Update an existing fact in the knowledge base.
        
        Args:
            topic: Topic of the fact to update
            content: New content for the fact
            
        Returns:
            Dictionary with status and message
        """
        try:
            # Validate inputs
            if not topic:
                return {'status': 'error', 'message': 'Topic cannot be empty'}
            
            # Serialize content to JSON if it's a dict or list
            if isinstance(content, (dict, list)):
                content_json = json.dumps(content)
            else:
                content_json = json.dumps({"value": str(content)})
            
            # Get current timestamp
            current_time = time.time()
            
            # Connect to database
            conn, cursor = self._get_db_connection()
            
            # Check if fact exists
            cursor.execute("SELECT id FROM facts WHERE topic = ?", (topic,))
            if not cursor.fetchone():
                conn.close()
                return {
                    'status': 'error',
                    'message': f"No fact found with topic '{topic}'. Use add_fact instead."
                }
            
            # Update fact
            cursor.execute(
                "UPDATE facts SET content = ?, updated_at = ? WHERE topic = ?",
                (content_json, current_time, topic)
            )
            
            # Commit changes
            conn.commit()
            
            # Close connection
            conn.close()
            
            logger.info(f"Updated fact: {topic}")
            
            return {
                'status': 'success',
                'message': f"Fact '{topic}' updated successfully"
            }
                
        except Exception as e:
            logger.error(f"Error updating fact: {e}")
            return {
                'status': 'error',
                'message': f"Failed to update fact: {str(e)}"
            }
    
    def search_facts(self, query: str = None, limit: int = 10) -> Dict[str, Any]:
        """Search for facts in the knowledge base.
        
        Args:
            query: Search string (will match against topic)
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with status and matching facts
        """
        try:
            # Connect to database
            conn, cursor = self._get_db_connection()
            
            # Prepare query
            if query:
                # Search for topics containing the query string
                sql = "SELECT id, topic, content, created_at, updated_at FROM facts WHERE topic LIKE ? ORDER BY updated_at DESC LIMIT ?"
                cursor.execute(sql, (f'%{query}%', limit))
            else:
                # Get most recently updated facts
                sql = "SELECT id, topic, content, created_at, updated_at FROM facts ORDER BY updated_at DESC LIMIT ?"
                cursor.execute(sql, (limit,))
            
            # Get results
            results = cursor.fetchall()
            
            # Close connection
            conn.close()
            
            # Format results
            facts = []
            for fact_id, topic, content_json, created_at, updated_at in results:
                # Parse JSON content
                try:
                    content = json.loads(content_json)
                except json.JSONDecodeError:
                    content = {"value": content_json}
                
                facts.append({
                    'id': fact_id,
                    'topic': topic,
                    'content': content,
                    'created_at': created_at,
                    'updated_at': updated_at
                })
            
            logger.info(f"Search found {len(facts)} facts")
            
            return {
                'status': 'success',
                'facts': facts,
                'count': len(facts)
            }
                
        except Exception as e:
            logger.error(f"Error searching facts: {e}")
            return {
                'status': 'error',
                'message': f"Failed to search facts: {str(e)}"
            }
        
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests.
        
        Args:
            request: Dictionary containing the request details
            
        Returns:
            Dictionary with response
        """
        action = request.get('action')
        
        if action == 'health':
            return self.get_health_status()
        elif action == 'add_fact':
            return self.add_fact(
                request.get('fact', {}).get('subject'),
                request.get('fact', {}).get('object')
            )
        elif action == 'query':
            return self.get_fact(request.get('query', {}).get('subject'))
        elif action == 'update_fact':
            return self.update_fact(
                request.get('fact', {}).get('subject'),
                request.get('fact', {}).get('object')
            )
        elif action == 'search_facts':
            return self.search_facts(
                request.get('query'),
                request.get('limit', 10)
            )
        else:
            return {
                'status': 'error',
                'message': f"Unknown action: {action}"
            }
            
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.context.term()
        logger.info("Knowledge Base stopped")

if __name__ == '__main__':
    agent = KnowledgeBase()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 