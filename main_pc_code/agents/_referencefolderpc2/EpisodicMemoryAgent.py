import zmq
import json
import time
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('episodic_memory.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EpisodicMemoryAgent:
    def __init__(self, port: int = 5629):
        """Initialize the EpisodicMemoryAgent with ZMQ socket and database."""
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        
        # Initialize database
        self.db_path = "episodic_memory.db"
        self._init_database()
        
        # Initialize TF-IDF vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.episode_vectors = {}
        
        logger.info(f"EpisodicMemoryAgent initialized on port {port}")
    
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

if __name__ == '__main__':
    memory_agent = EpisodicMemoryAgent()
    memory_agent.run() 