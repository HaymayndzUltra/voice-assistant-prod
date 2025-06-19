from src.core.base_agent import BaseAgent
import zmq
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('learning_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LearningAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Learningagent")
        """Initialize the LearningAgent with ZMQ sockets and database."""
        self.port = port
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        
        # REQ socket for EpisodicMemoryAgent
        self.memory_socket = self.context.socket(zmq.REQ)
        self.memory_socket.connect("tcp://localhost:5629")  # EpisodicMemoryAgent
        
        # REQ socket for LocalFineTunerAgent
        self.tuner_socket = self.context.socket(zmq.REQ)
        self.tuner_socket.connect("tcp://localhost:5603")  # LocalFineTunerAgent
        
        # Initialize database
        self.db_path = "learning_agent.db"
        self._init_database()
        
        # Start pattern analysis thread
        self.running = True
        self.analysis_thread = Thread(target=self._analyze_patterns)
        self.analysis_thread.start()
        
        logger.info(f"LearningAgent initialized on port {port}")
    
    def _init_database(self):
        """Initialize SQLite database for learning data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                pattern_type TEXT,
                commands TEXT,
                frequency INTEGER,
                last_seen TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shortcuts (
                shortcut_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                name TEXT,
                description TEXT,
                commands TEXT,
                created_at TIMESTAMP,
                last_used TIMESTAMP,
                usage_count INTEGER,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_examples (
                example_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                input_text TEXT,
                expected_output TEXT,
                context TEXT,
                created_at TIMESTAMP,
                used_count INTEGER,
                success_rate REAL,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _analyze_patterns(self):
        """Analyze user behavior patterns periodically."""
        while self.running:
            try:
                # Get recent episodes
                self.memory_socket.send_json({
                    'action': 'search_episodes',
                    'query': {
                        'start_date': (datetime.now() - timedelta(days=7)).isoformat()
                    }
                })
                
                response = self.memory_socket.recv_json()
                
                if response['status'] == 'success':
                    episodes = response['episodes']
                    
                    # Analyze command sequences
                    for episode in episodes:
                        self._analyze_episode(episode)
                
                # Wait before next analysis
                time.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                logger.error(f"Error analyzing patterns: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _analyze_episode(self, episode: Dict[str, Any]):
        """Analyze a single episode for patterns."""
        # Group interactions by user
        user_interactions = defaultdict(list)
        
        for interaction in episode['interactions']:
            if interaction['speaker'] == 'user':
                user_interactions[episode['user_id']].append(interaction)
        
        # Analyze each user's interactions
        for user_id, interactions in user_interactions.items():
            # Look for command sequences
            sequences = self._find_command_sequences(interactions)
            
            # Store patterns
            for sequence in sequences:
                self._store_command_pattern(user_id, sequence)
            
            # Look for potential shortcuts
            shortcuts = self._identify_shortcuts(interactions)
            
            # Store shortcuts
            for shortcut in shortcuts:
                self._store_shortcut(user_id, shortcut)
    
    def _find_command_sequences(self, interactions: List[Dict[str, Any]], 
                              min_sequence_length: int = 2) -> List[List[Dict[str, Any]]]:
        """Find repeated sequences of commands."""
        sequences = []
        
        # Look for sequences of minimum length
        for i in range(len(interactions) - min_sequence_length + 1):
            sequence = interactions[i:i + min_sequence_length]
            
            # Check if this sequence appears elsewhere
            for j in range(i + 1, len(interactions) - min_sequence_length + 1):
                if self._compare_sequences(sequence, interactions[j:j + min_sequence_length]):
                    sequences.append(sequence)
        
        return sequences
    
    def _compare_sequences(self, seq1: List[Dict[str, Any]], 
                          seq2: List[Dict[str, Any]]) -> bool:
        """Compare two command sequences for similarity."""
        if len(seq1) != len(seq2):
            return False
        
        for cmd1, cmd2 in zip(seq1, seq2):
            if cmd1['content'] != cmd2['content']:
                return False
        
        return True
    
    def _identify_shortcuts(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify potential shortcuts from interactions."""
        shortcuts = []
        
        # Look for common command patterns
        command_counts = defaultdict(int)
        for interaction in interactions:
            command_counts[interaction['content']] += 1
        
        # Identify frequently used commands
        for command, count in command_counts.items():
            if count >= 3:  # Command used at least 3 times
                shortcuts.append({
                    'name': f"Shortcut for: {command[:30]}...",
                    'description': f"Automated shortcut for frequently used command",
                    'commands': [command],
                    'metadata': {
                        'usage_count': count,
                        'last_used': interactions[-1]['timestamp']
                    }
                })
        
        return shortcuts
    
    def _store_command_pattern(self, user_id: str, pattern: List[Dict[str, Any]]):
        """Store a command pattern in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute('''
            SELECT pattern_id, frequency 
            FROM command_patterns 
            WHERE user_id = ? AND commands = ?
        ''', (user_id, json.dumps([cmd['content'] for cmd in pattern])))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing pattern
            pattern_id, frequency = result
            cursor.execute('''
                UPDATE command_patterns 
                SET frequency = ?, last_seen = ?
                WHERE pattern_id = ?
            ''', (frequency + 1, datetime.now(), pattern_id))
        else:
            # Create new pattern
            cursor.execute('''
                INSERT INTO command_patterns 
                (user_id, pattern_type, commands, frequency, last_seen, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                'sequence',
                json.dumps([cmd['content'] for cmd in pattern]),
                1,
                datetime.now(),
                json.dumps({
                    'first_seen': pattern[0]['timestamp'],
                    'last_seen': pattern[-1]['timestamp']
                })
            ))
        
        conn.commit()
        conn.close()
    
    def _store_shortcut(self, user_id: str, shortcut: Dict[str, Any]):
        """Store a shortcut in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if shortcut exists
        cursor.execute('''
            SELECT shortcut_id 
            FROM shortcuts 
            WHERE user_id = ? AND commands = ?
        ''', (user_id, json.dumps(shortcut['commands'])))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing shortcut
            shortcut_id = result[0]
            cursor.execute('''
                UPDATE shortcuts 
                SET usage_count = usage_count + 1,
                    last_used = ?
                WHERE shortcut_id = ?
            ''', (datetime.now(), shortcut_id))
        else:
            # Create new shortcut
            cursor.execute('''
                INSERT INTO shortcuts 
                (user_id, name, description, commands, created_at, last_used, usage_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                shortcut['name'],
                shortcut['description'],
                json.dumps(shortcut['commands']),
                datetime.now(),
                datetime.now(),
                1,
                json.dumps(shortcut['metadata'])
            ))
        
        conn.commit()
        conn.close()
    
    def _get_command_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Get command patterns for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pattern_id, pattern_type, commands, frequency, last_seen, metadata
            FROM command_patterns
            WHERE user_id = ?
            ORDER BY frequency DESC, last_seen DESC
        ''', (user_id,))
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'pattern_id': row[0],
                'pattern_type': row[1],
                'commands': json.loads(row[2]),
                'frequency': row[3],
                'last_seen': row[4],
                'metadata': json.loads(row[5])
            })
        
        conn.close()
        return patterns
    
    def _get_shortcuts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get shortcuts for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT shortcut_id, name, description, commands, created_at, last_used, usage_count, metadata
            FROM shortcuts
            WHERE user_id = ?
            ORDER BY usage_count DESC, last_used DESC
        ''', (user_id,))
        
        shortcuts = []
        for row in cursor.fetchall():
            shortcuts.append({
                'shortcut_id': row[0],
                'name': row[1],
                'description': row[2],
                'commands': json.loads(row[3]),
                'created_at': row[4],
                'last_used': row[5],
                'usage_count': row[6],
                'metadata': json.loads(row[7])
            })
        
        conn.close()
        return shortcuts
    
    def _trigger_few_shot_learning(self, user_id: str, examples: List[Dict[str, Any]]):
        """Trigger few-shot learning with the LocalFineTunerAgent."""
        try:
            # Request fine-tuning
            self.tuner_socket.send_json({
                'action': 'trigger_few_shot_learning',
                'user_id': user_id,
                'examples': examples
            })
            
            # Get response
            response = self.tuner_socket.recv_json()
            
            if response['status'] == 'success':
                logger.info(f"Few-shot learning triggered for user {user_id}")
            else:
                logger.error(f"Few-shot learning failed: {response.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error triggering few-shot learning: {str(e)}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'get_patterns':
            user_id = request['user_id']
            
            patterns = self._get_command_patterns(user_id)
            
            return {
                'status': 'success',
                'patterns': patterns
            }
            
        elif action == 'get_shortcuts':
            user_id = request['user_id']
            
            shortcuts = self._get_shortcuts(user_id)
            
            return {
                'status': 'success',
                'shortcuts': shortcuts
            }
            
        elif action == 'trigger_learning':
            user_id = request['user_id']
            examples = request['examples']
            
            self._trigger_few_shot_learning(user_id, examples)
            
            return {
                'status': 'success'
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("LearningAgent started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.running = False
        self.analysis_thread.join()
        
        self.socket.close()
        self.memory_socket.close()
        self.tuner_socket.close()
        self.context.term()

if __name__ == '__main__':
    agent = LearningAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
