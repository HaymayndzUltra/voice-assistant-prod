import zmq
import json
import time
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))))
from common.utils.path_manager import PathManager
# Try to import sklearn, but don't fail if not available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError as e:
        print(f"Import error: {e}")
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE 
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from src.agents.pc2.error_bus_template import setup_error_reporting, report_error


# Load configuration at the module level
config = load_config()= True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: sklearn not available, text similarity features will be disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "episodic_memory_agent.log"))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EpisodicMemoryAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port: int = 7106, health_port: int = 7107):
         super().__init__(name="EpisodicMemoryAgent", port=7106)
"""Initialize the EpisodicMemoryAgent with ZMQ socket and database."""
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
        
        logger.info(f"EpisodicMemoryAgent starting on port {port} (health: {health_port})")
    
    def _setup_sockets(self):
        """Setup ZMQ sockets."""
        # Main socket for handling requests
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"EpisodicMemoryAgent main socket bound to port {self.port}")
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
                            'service': 'EpisodicMemoryAgent',
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
            self.db_path = str(PathManager.get_data_dir() / "episodic_memory.db")
            self._init_database()
            
            # Initialize TF-IDF vectorizer for text similarity (if available)
            if SKLEARN_AVAILABLE:
                self.vectorizer = TfidfVectorizer(stop_words='english')
                self.episode_vectors = {}
                logger.info("TF-IDF vectorizer initialized for text similarity")
            else:
                self.vectorizer = None
                self.episode_vectors = {}
                logger.warning("TF-IDF vectorizer not available, text similarity disabled")
            
            self.initialized = True
            logger.info("EpisodicMemoryAgent initialization completed")
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"EpisodicMemoryAgent initialization failed: {str(e)}")
    
    def _init_database(self):
        """Initialize SQLite database for episodic memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                profile TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                context TEXT,
                summary TEXT,
                importance_score REAL DEFAULT 0.5,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER,
                timestamp TIMESTAMP,
                speaker TEXT,
                content TEXT,
                intent TEXT,
                sentiment REAL,
                metadata TEXT,
                FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episode_tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER,
                tag TEXT,
                confidence REAL,
                FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)
            )
        ''')
        
        # New table for episode relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episode_relationships (
                relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_episode_id INTEGER,
                target_episode_id INTEGER,
                relationship_type TEXT,
                strength REAL,
                metadata TEXT,
                FOREIGN KEY (source_episode_id) REFERENCES episodes(episode_id),
                FOREIGN KEY (target_episode_id) REFERENCES episodes(episode_id)
            )
        ''')
        
        # New table for context groups
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                created_at TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episode_context_groups (
                episode_id INTEGER,
                group_id INTEGER,
                relevance_score REAL,
                FOREIGN KEY (episode_id) REFERENCES episodes(episode_id),
                FOREIGN KEY (group_id) REFERENCES context_groups(group_id),
                PRIMARY KEY (episode_id, group_id)
            )
        ''')
        
        # Create full-text search index
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                content,
                summary,
                context,
                content='episodes',
                content_rowid='episode_id'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _create_episode(self, user_id: str, profile: str, context: Dict[str, Any]) -> int:
        """Create a new episode and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate initial importance score
        importance_score = self._calculate_importance(context)
        
        cursor.execute('''
            INSERT INTO episodes 
            (user_id, profile, start_time, context, importance_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            profile,
            datetime.now(),
            json.dumps(context),
            importance_score
        ))
        
        episode_id = cursor.lastrowid
        
        # Update full-text search index
        cursor.execute('''
            INSERT INTO episodes_fts (rowid, content, summary, context)
            VALUES (?, ?, ?, ?)
        ''', (
            episode_id,
            '',  # Will be updated with interactions
            '',  # Will be updated with summary
            json.dumps(context)
        ))
        
        conn.commit()
        conn.close()
        
        return episode_id
    
    def _calculate_importance(self, context: Dict[str, Any]) -> float:
        """Calculate importance score for an episode based on context."""
        score = 0.5  # Base score
        
        # Adjust based on context factors
        if context.get('is_critical', False):
            score += 0.3
        if context.get('requires_action', False):
            score += 0.2
        if context.get('user_priority', 0) > 0:
            score += min(0.2, context['user_priority'] * 0.1)
        
        return min(1.0, max(0.0, score))
    
    def _add_interaction(self, episode_id: int, speaker: str, content: str, 
                        intent: str, sentiment: float, metadata: Dict[str, Any]):
        """Add an interaction to an episode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interactions 
            (episode_id, timestamp, speaker, content, intent, sentiment, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            episode_id,
            datetime.now(),
            speaker,
            content,
            intent,
            sentiment,
            json.dumps(metadata)
        ))
        
        # Update full-text search index
        cursor.execute('''
            UPDATE episodes_fts 
            SET content = content || ' ' || ?
            WHERE rowid = ?
        ''', (content, episode_id))
        
        conn.commit()
        conn.close()
    
    def _add_episode_tags(self, episode_id: int, tags: List[Dict[str, Any]]):
        """Add tags to an episode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for tag in tags:
            cursor.execute('''
                INSERT INTO episode_tags 
                (episode_id, tag, confidence)
                VALUES (?, ?, ?)
            ''', (
                episode_id,
                tag['tag'],
                tag['confidence']
            ))
        
        conn.commit()
        conn.close()
    
    def _add_episode_relationship(self, source_id: int, target_id: int, 
                                relationship_type: str, strength: float = 1.0,
                                metadata: Dict[str, Any] = None):
        """Add a relationship between episodes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO episode_relationships 
            (source_episode_id, target_episode_id, relationship_type, strength, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source_id,
            target_id,
            relationship_type,
            strength,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def _create_context_group(self, name: str, description: str, 
                            metadata: Dict[str, Any] = None) -> int:
        """Create a new context group."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO context_groups 
            (name, description, created_at, metadata)
            VALUES (?, ?, ?, ?)
        ''', (
            name,
            description,
            datetime.now(),
            json.dumps(metadata or {})
        ))
        
        group_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return group_id
    
    def _add_episode_to_context_group(self, episode_id: int, group_id: int, 
                                    relevance_score: float = 1.0):
        """Add an episode to a context group."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO episode_context_groups 
            (episode_id, group_id, relevance_score)
            VALUES (?, ?, ?)
        ''', (episode_id, group_id, relevance_score))
        
        conn.commit()
        conn.close()
    
    def _search_episodes(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhanced search for episodes matching the query criteria."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query conditions
        conditions = []
        params = []
        
        if 'user_id' in query:
            conditions.append("user_id = ?")
            params.append(query['user_id'])
        
        if 'profile' in query:
            conditions.append("profile = ?")
            params.append(query['profile'])
        
        if 'start_date' in query:
            conditions.append("start_time >= ?")
            params.append(query['start_date'])
        
        if 'end_date' in query:
            conditions.append("end_time <= ?")
            params.append(query['end_date'])
        
        if 'tag' in query:
            conditions.append("episode_id IN (SELECT episode_id FROM episode_tags WHERE tag = ?)")
            params.append(query['tag'])
        
        if 'context_group' in query:
            conditions.append("""
                episode_id IN (
                    SELECT episode_id 
                    FROM episode_context_groups 
                    WHERE group_id = ?
                )
            """)
            params.append(query['context_group'])
        
        if 'text_search' in query:
            # Use full-text search
            conditions.append("""
                episode_id IN (
                    SELECT rowid 
                    FROM episodes_fts 
                    WHERE episodes_fts MATCH ?
                )
            """)
            params.append(query['text_search'])
        
        if 'min_importance' in query:
            conditions.append("importance_score >= ?")
            params.append(query['min_importance'])
        
        # Build and execute query
        query_str = "SELECT episode_id FROM episodes"
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        if 'sort_by' in query:
            sort_field = query['sort_by']
            sort_order = query.get('sort_order', 'DESC')
            query_str += f" ORDER BY {sort_field} {sort_order}"
        
        cursor.execute(query_str, params)
        episode_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Get full episode details
        episodes = [self._get_episode(ep_id) for ep_id in episode_ids]
        
        # Apply relevance scoring if text search was used
        if 'text_search' in query:
            episodes = self._rank_by_relevance(episodes, query['text_search'])
        
        return episodes
    
    def _rank_by_relevance(self, episodes: List[Dict[str, Any]], 
                          query: str) -> List[Dict[str, Any]]:
        """Rank episodes by relevance to the search query."""
        if not episodes:
            return []
        
        # Prepare texts for vectorization
        texts = [ep['summary'] or '' for ep in episodes]
        texts.append(query)  # Add query to the end
        
        # Create TF-IDF vectors
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            query_vector = tfidf_matrix[-1]
            episode_vectors = tfidf_matrix[:-1]
            
            # Calculate cosine similarity
            similarities = cosine_similarity(query_vector, episode_vectors)[0]
            
            # Add relevance scores to episodes
            for episode, score in zip(episodes, similarities):
                episode['relevance_score'] = float(score)
            
            # Sort by relevance
            return sorted(episodes, key=lambda x: x['relevance_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error in relevance ranking: {e}")
            return episodes
    
    def _get_related_episodes(self, episode_id: int, 
                            relationship_type: Optional[str] = None,
                            limit: int = 5) -> List[Dict[str, Any]]:
        """Get episodes related to the given episode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT target_episode_id, relationship_type, strength
            FROM episode_relationships
            WHERE source_episode_id = ?
        '''
        params = [episode_id]
        
        if relationship_type:
            query += " AND relationship_type = ?"
            params.append(relationship_type)
        
        query += " ORDER BY strength DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        related = cursor.fetchall()
        
        conn.close()
        
        return [self._get_episode(ep_id) for ep_id, _, _ in related]
    
    def _get_context_group_episodes(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all episodes in a context group."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT episode_id, relevance_score
            FROM episode_context_groups
            WHERE group_id = ?
            ORDER BY relevance_score DESC
        ''', (group_id,))
        
        episodes = cursor.fetchall()
        conn.close()
        
        return [self._get_episode(ep_id) for ep_id, _ in episodes]
    
    def _update_episode_status(self, episode_id: int, status: str):
        """Update the status of an episode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE episodes
            SET status = ?
            WHERE episode_id = ?
        ''', (status, episode_id))
        
        conn.commit()
        conn.close()
    
    def _get_episode(self, episode_id: int) -> Optional[Dict[str, Any]]:
        """Get a complete episode with all its interactions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get episode details
        cursor.execute('''
            SELECT user_id, profile, start_time, end_time, context, summary,
                   importance_score, status
            FROM episodes
            WHERE episode_id = ?
        ''', (episode_id,))
        
        episode = cursor.fetchone()
        if not episode:
            conn.close()
            return None
        
        # Get interactions
        cursor.execute('''
            SELECT timestamp, speaker, content, intent, sentiment, metadata
            FROM interactions
            WHERE episode_id = ?
            ORDER BY timestamp
        ''', (episode_id,))
        
        interactions = cursor.fetchall()
        
        # Get tags
        cursor.execute('''
            SELECT tag, confidence
            FROM episode_tags
            WHERE episode_id = ?
        ''', (episode_id,))
        
        tags = cursor.fetchall()
        
        # Get context groups
        cursor.execute('''
            SELECT g.group_id, g.name, g.description, ecg.relevance_score
            FROM context_groups g
            JOIN episode_context_groups ecg ON g.group_id = ecg.group_id
            WHERE ecg.episode_id = ?
        ''', (episode_id,))
        
        context_groups = cursor.fetchall()
        
        conn.close()
        
        return {
            'episode_id': episode_id,
            'user_id': episode[0],
            'profile': episode[1],
            'start_time': episode[2],
            'end_time': episode[3],
            'context': json.loads(episode[4]),
            'summary': episode[5],
            'importance_score': episode[6],
            'status': episode[7],
            'interactions': [
                {
                    'timestamp': ts,
                    'speaker': sp,
                    'content': cont,
                    'intent': intent,
                    'sentiment': sent,
                    'metadata': json.loads(meta)
                }
                for ts, sp, cont, intent, sent, meta in interactions
            ],
            'tags': [
                {
                    'tag': tag,
                    'confidence': conf
                }
                for tag, conf in tags
            ],
            'context_groups': [
                {
                    'group_id': gid,
                    'name': name,
                    'description': desc,
                    'relevance_score': score
                }
                for gid, name, desc, score in context_groups
            ]
        }
    
    def run(self):
        """Main service loop."""
        logger.info("Starting EpisodicMemoryAgent service loop")
        
        while True:
            try:
                # Wait for request
                message = self.socket.recv_string()
                request = json.loads(message)
                
                # Handle request
                response = self.handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "error": str(e)
                }))


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to EpisodicMemoryAgent

        base_status.update({

            'service': 'EpisodicMemoryAgent',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get("action")
        
        try:
            if action == "create_episode":
                episode_id = self._create_episode(
                    request["user_id"],
                    request["profile"],
                    request["context"]
                )
                return {"status": "success", "episode_id": episode_id}
            
            elif action == "add_interaction":
                self._add_interaction(
                    request["episode_id"],
                    request["speaker"],
                    request["content"],
                    request["intent"],
                    request["sentiment"],
                    request.get("metadata", {})
                )
                return {"status": "success"}
            
            elif action == "add_episode_tags":
                self._add_episode_tags(
                    request["episode_id"],
                    request["tags"]
                )
                return {"status": "success"}
            
            elif action == "get_episode":
                episode = self._get_episode(request["episode_id"])
                if episode:
                    return {"status": "success", "episode": episode}
                return {"status": "error", "error": "Episode not found"}
            
            elif action == "search_episodes":
                episodes = self._search_episodes(request["query"])
                return {"status": "success", "episodes": episodes}
            
            elif action == "add_episode_relationship":
                self._add_episode_relationship(
                    request["source_id"],
                    request["target_id"],
                    request["relationship_type"],
                    request.get("strength", 1.0),
                    request.get("metadata")
                )
                return {"status": "success"}
            
            elif action == "create_context_group":
                group_id = self._create_context_group(
                    request["name"],
                    request["description"],
                    request.get("metadata")
                )
                return {"status": "success", "group_id": group_id}
            
            elif action == "add_to_context_group":
                self._add_episode_to_context_group(
                    request["episode_id"],
                    request["group_id"],
                    request.get("relevance_score", 1.0)
                )
                return {"status": "success"}
            
            elif action == "get_related_episodes":
                episodes = self._get_related_episodes(
                    request["episode_id"],
                    request.get("relationship_type"),
                    request.get("limit", 5)
                )
                return {"status": "success", "episodes": episodes}
            
            elif action == "get_context_group_episodes":
                episodes = self._get_context_group_episodes(request["group_id"])
                return {"status": "success", "episodes": episodes}
            
            elif action == "update_episode_status":
                self._update_episode_status(
                    request["episode_id"],
                    request["status"]
                )
                return {"status": "success"}
            
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"status": "error", "error": str(e)}



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = EpisodicMemoryAgent()
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