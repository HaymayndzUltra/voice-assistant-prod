import os
import zmq
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import math
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from dataclasses import dataclass
from enum import Enum
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from pc2_code.config.system_config import get_service_host, get_service_port

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dream_world_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScenarioType(BaseAgent):
    ETHICAL = "ethical"
    RESOURCE = "resource"
    SOCIAL = "social"
    STRATEGIC = "strategic"
    CUSTOM = "custom"

@dataclass
class ScenarioTemplate:
    name: str
    type: ScenarioType
    description: str
    initial_state: Dict[str, Any]
    actions: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    evaluation_metrics: List[str]
    metadata: Dict[str, Any]

class MCTSNode:
    def __init__(self, state: Dict[str, Any], parent=None, action=None):
         super().__init__(name="ScenarioType", port=None)
"""Initialize a node in the Monte Carlo Tree."""
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.uncertainty = 1.0
        self.causal_links = []
        self.counterfactuals = []
    
    def add_child(self, state: Dict[str, Any], action: Dict[str, Any]) -> 'MCTSNode':
        """Add a child node to this node."""
        child = MCTSNode(state, parent=self, action=action)
        self.children.append(child)
        return child
    
    def update(self, value: float, uncertainty: float = 0.0):
        """Update node statistics."""
        self.visits += 1
        self.value += value
        self.uncertainty = (self.uncertainty * (self.visits - 1) + uncertainty) / self.visits
    
    def get_ucb(self, exploration_weight: float = 1.41) -> float:
        """Calculate UCB (Upper Confidence Bound) for this node."""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.value / self.visits
        exploration = exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)
        uncertainty_factor = 1.0 - self.uncertainty  # Lower uncertainty increases exploration
        return exploitation + exploration * uncertainty_factor

class DreamWorldAgent:
    def __init__(self):
        """Initialize the Dream World Agent."""
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        
        # Get host and port from environment or config
        self.host = get_service_host('dream_world', '0.0.0.0')
        self.port = get_service_port('dream_world', 7104)  # Updated to expected port
        self.health_port = self.port + 1  # Health check port
        
        # Setup sockets first for immediate health check availability
        self._setup_sockets()
        
        # Start health check endpoint immediately
        self._start_health_check()
        
        # Start initialization in background thread
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        
        logger.info(f"DreamWorld Agent starting on {self.host}:{self.port} (health: {self.health_port})")
    
    def _setup_sockets(self):
        """Setup ZMQ sockets."""
        # ROUTER socket for handling requests
        try:
            self.socket = self.context.socket(zmq.ROUTER)
            self.socket.bind(f"tcp://{self.host}:{self.port}")
            logger.info(f"DreamWorld Agent listening on {self.host}:{self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {self.port}: {str(e)}")
            raise
        
        # Health check socket
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://{self.host}:{self.health_port}")
            logger.info(f"Health check endpoint on {self.host}:{self.health_port}")
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
                            'service': 'DreamWorldAgent',
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
            self.db_path = "dream_world.db"
            self._init_database()
            
            # Load scenario templates
            self.scenario_templates = self._load_scenario_templates()
            
            # Initialize simulation history
            self.simulation_history = []
            
            # Initialize thread pool for parallel simulations
            self.executor = ThreadPoolExecutor(max_workers=4)
            
            # Initialize dream world state
            self.dream_state = {}
            
            # Try to connect to dependencies (but don't fail if unavailable)
            self._setup_dependencies()
            
            self.initialized = True
            logger.info("Dream World Agent initialization completed")
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Dream World Agent initialization failed: {str(e)}")
    
    def _setup_dependencies(self):
        """Setup connections to dependencies (gracefully handle failures)."""
        # REQ socket for Enhanced Model Router (optional)
        try:
            self.model_socket = self.context.socket(zmq.REQ)
            model_host = get_service_host('enhanced_model_router', 'localhost')
            model_port = get_service_port('enhanced_model_router', 5598)
            self.model_socket.connect(f"tcp://{model_host}:{model_port}")
            self.model_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            logger.info(f"Connected to Enhanced Model Router at {model_host}:{model_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Enhanced Model Router: {str(e)}")
            self.model_socket = None
        
        # REQ socket for EpisodicMemoryAgent (optional)
        try:
            self.memory_socket = self.context.socket(zmq.REQ)
            memory_host = get_service_host('episodic_memory', 'localhost')
            memory_port = get_service_port('episodic_memory', 5629)
            self.memory_socket.connect(f"tcp://{memory_host}:{memory_port}")
            self.memory_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            logger.info(f"Connected to Episodic Memory Agent at {memory_host}:{memory_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Episodic Memory Agent: {str(e)}")
            self.memory_socket = None
    
    def _init_database(self):
        """Initialize SQLite database for scenario and simulation storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenarios (
                scenario_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                description TEXT,
                initial_state TEXT,
                actions TEXT,
                constraints TEXT,
                evaluation_metrics TEXT,
                metadata TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulations (
                simulation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                iterations INTEGER,
                best_action TEXT,
                expected_value REAL,
                uncertainty REAL,
                causal_analysis TEXT,
                counterfactuals TEXT,
                metadata TEXT,
                FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulation_states (
                state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER,
                step INTEGER,
                state TEXT,
                action TEXT,
                value REAL,
                uncertainty REAL,
                metadata TEXT,
                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_scenario_templates(self) -> Dict[str, ScenarioTemplate]:
        """Load scenario templates from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM scenarios')
        templates = {}
        
        for row in cursor.fetchall():
            template = ScenarioTemplate(
                name=row[1],
                type=ScenarioType(row[2]),
                description=row[3],
                initial_state=json.loads(row[4]),
                actions=json.loads(row[5]),
                constraints=json.loads(row[6]),
                evaluation_metrics=json.loads(row[7]),
                metadata=json.loads(row[8])
            )
            templates[template.name] = template
        
        conn.close()
        return templates
    
    def _save_simulation(self, scenario_id: int, iterations: int, 
                        best_action: Dict[str, Any], expected_value: float,
                        uncertainty: float, causal_analysis: List[Dict[str, Any]],
                        counterfactuals: List[Dict[str, Any]], metadata: Dict[str, Any]) -> int:
        """Save simulation results to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO simulations 
            (scenario_id, start_time, end_time, iterations, best_action,
             expected_value, uncertainty, causal_analysis, counterfactuals, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scenario_id,
            datetime.now(),
            datetime.now(),
            iterations,
            json.dumps(best_action),
            expected_value,
            uncertainty,
            json.dumps(causal_analysis),
            json.dumps(counterfactuals),
            json.dumps(metadata)
        ))
        
        simulation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return simulation_id
    
    def _save_simulation_state(self, simulation_id: int, step: int,
                              state: Dict[str, Any], action: Dict[str, Any],
                              value: float, uncertainty: float,
                              metadata: Dict[str, Any]):
        """Save a simulation state to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO simulation_states
            (simulation_id, step, state, action, value, uncertainty, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            simulation_id,
            step,
            json.dumps(state),
            json.dumps(action),
            value,
            uncertainty,
            json.dumps(metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _evaluate_state(self, state: Dict[str, Any], scenario: str) -> Tuple[float, float]:
        """Evaluate a state using the EnhancedModelRouter and calculate uncertainty."""
        try:
            self.model_socket.send_json({
                'action': 'evaluate_state',
                'state': state,
                'scenario': scenario
            })
            
            response = self.model_socket.recv_json()
            if response['status'] == 'success':
                # Calculate uncertainty based on state complexity and model confidence
                uncertainty = self._calculate_uncertainty(state, response.get('confidence', 0.5))
                return response['evaluation'], uncertainty
            else:
                logger.error(f"Error evaluating state: {response['message']}")
                return 0.0, 1.0
                
        except Exception as e:
            logger.error(f"Error in _evaluate_state: {str(e)}")
            return 0.0, 1.0
    
    def _calculate_uncertainty(self, state: Dict[str, Any], model_confidence: float) -> float:
        """Calculate uncertainty based on state complexity and model confidence."""
        # Base uncertainty on model confidence
        uncertainty = 1.0 - model_confidence
        
        # Increase uncertainty for complex states
        state_complexity = len(str(state)) / 1000  # Simple complexity metric
        uncertainty += min(0.3, state_complexity)
        
        return min(1.0, uncertainty)
    
    def _apply_action(self, state: Dict[str, Any], action: Dict[str, Any], 
                     scenario: str) -> Dict[str, Any]:
        """Apply an action to a state with causal tracking."""
        new_state = state.copy()
        
        # Get scenario template
        template = self.scenario_templates[scenario]
        
        # Apply action effects
        if 'effects' in action:
            for effect in action['effects']:
                if 'target' in effect and 'value' in effect:
                    target = effect['target'].split('.')
                    current = new_state
                    for i, key in enumerate(target[:-1]):
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    current[target[-1]] = effect['value']
        
        # Apply constraints
        for constraint in template.constraints:
            if constraint['type'] == 'range':
                target = constraint['target'].split('.')
                current = new_state
                for key in target[:-1]:
                    current = current[key]
                current[target[-1]] = max(
                    constraint['min'],
                    min(constraint['max'], current[target[-1]])
                )
        
        return new_state
    
    def _analyze_causality(self, state: Dict[str, Any], action: Dict[str, Any],
                          new_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze causal relationships between state changes."""
        causal_links = []
        
        # Compare states to identify changes
        for key, value in new_state.items():
            if key in state and state[key] != value:
                causal_links.append({
                    'cause': {
                        'action': action,
                        'state': state
                    },
                    'effect': {
                        'state': new_state,
                        'changed_key': key,
                        'old_value': state[key],
                        'new_value': value
                    }
                })
        
        return causal_links
    
    def _generate_counterfactuals(self, state: Dict[str, Any], action: Dict[str, Any],
                                scenario: str) -> List[Dict[str, Any]]:
        """Generate counterfactual scenarios for the given state and action."""
        counterfactuals = []
        
        # Get scenario template
        template = self.scenario_templates[scenario]
        
        # Generate alternative actions
        for alt_action in template.actions:
            if alt_action != action:
                # Apply alternative action
                alt_state = self._apply_action(state, alt_action, scenario)
                
                # Evaluate alternative outcome
                value, uncertainty = self._evaluate_state(alt_state, scenario)
                
                counterfactuals.append({
                    'action': alt_action,
                    'state': alt_state,
                    'value': value,
                    'uncertainty': uncertainty
                })
        
        return counterfactuals
    
    def _select_node(self, node: MCTSNode, scenario: str) -> MCTSNode:
        """Select a node using UCB with uncertainty consideration."""
        while node.children:
            if len(node.children) < len(self.scenario_templates[scenario].actions):
                return self._expand_node(node, scenario)
            
            node = max(node.children, key=lambda n: n.get_ucb())
        
        return node
    
    def _expand_node(self, node: MCTSNode, scenario: str) -> MCTSNode:
        """Expand a node by adding a child with causal analysis."""
        # Get untried actions
        tried_actions = {child.action for child in node.children}
        available_actions = [
            action for action in self.scenario_templates[scenario].actions
            if action not in tried_actions
        ]
        
        if not available_actions:
            return node
        
        # Select random untried action
        action = random.choice(available_actions)
        new_state = self._apply_action(node.state, action, scenario)
        
        # Analyze causality
        causal_links = self._analyze_causality(node.state, action, new_state)
        
        # Create child node
        child = node.add_child(new_state, action)
        child.causal_links = causal_links
        
        return child
    
    def _simulate(self, node: MCTSNode, scenario: str, max_depth: int = 10) -> Tuple[float, float]:
        """Simulate a random playout from a 
from main_pc_code.src.core.base_agent import BaseAgentnode with uncertainty tracking.
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = load_config()"""
        state = node.state.copy()
        depth = 0
        total_value = 0.0
        total_uncertainty = 0.0
        
        while depth < max_depth:
            # Get available actions
            available_actions = self.scenario_templates[scenario].actions
            
            if not available_actions:
                break
            
            # Select random action
            action = random.choice(available_actions)
            state = self._apply_action(state, action, scenario)
            
            # Evaluate state
            value, uncertainty = self._evaluate_state(state, scenario)
            total_value += value
            total_uncertainty += uncertainty
            
            depth += 1
        
        return total_value / max_depth, total_uncertainty / max_depth
    
    def _backpropagate(self, node: MCTSNode, value: float, uncertainty: float):
        """Backpropagate the result of a simulation with uncertainty."""
        while node:
            node.update(value, uncertainty)
            node = node.parent
    
    def run_simulation(self, scenario: str, iterations: int = 1000) -> Dict[str, Any]:
        """Run a Monte Carlo Tree Search simulation with enhanced features."""
        if scenario not in self.scenario_templates:
            return {
                'status': 'error',
                'message': f'Unknown scenario: {scenario}'
            }
        
        # Initialize root node
        root = MCTSNode(self.scenario_templates[scenario].initial_state)
        
        # Run MCTS iterations
        for i in range(iterations):
            # Selection
            node = self._select_node(root, scenario)
            
            # Expansion
            if node.visits > 0:
                node = self._expand_node(node, scenario)
            
            # Simulation
            value, uncertainty = self._simulate(node, scenario)
            
            # Backpropagation
            self._backpropagate(node, value, uncertainty)
            
            # Save simulation state
            self._save_simulation_state(
                simulation_id=0,  # Will be updated after simulation
                step=i,
                state=node.state,
                action=node.action,
                value=value,
                uncertainty=uncertainty,
                metadata={'iteration': i}
            )
        
        # Get best action
        if root.children:
            best_child = max(root.children, key=lambda n: n.value / n.visits)
            
            # Generate counterfactuals for best action
            counterfactuals = self._generate_counterfactuals(
                root.state,
                best_child.action,
                scenario
            )
            
            # Save simulation results
            simulation_id = self._save_simulation(
                scenario_id=0,  # Will be updated with actual scenario ID
                iterations=iterations,
                best_action=best_child.action,
                expected_value=best_child.value / best_child.visits,
                uncertainty=best_child.uncertainty,
                causal_analysis=best_child.causal_links,
                counterfactuals=counterfactuals,
                metadata={'scenario': scenario}
            )
            
            # Update simulation states with correct simulation_id
            self._update_simulation_states(simulation_id)
            
            return {
                'status': 'success',
                'scenario': scenario,
                'simulation_id': simulation_id,
                'best_action': best_child.action,
                'expected_value': best_child.value / best_child.visits,
                'uncertainty': best_child.uncertainty,
                'causal_analysis': best_child.causal_links,
                'counterfactuals': counterfactuals,
                'visits': best_child.visits
            }
        else:
            return {
                'status': 'error',
                'message': 'No valid actions found'
            }
    
    def _update_simulation_states(self, simulation_id: int):
        """Update simulation states with correct simulation_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE simulation_states
            SET simulation_id = ?
            WHERE simulation_id = 0
        ''', (simulation_id,))
        
        conn.commit()
        conn.close()
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        try:
            if action == 'run_simulation':
                return self.run_simulation(
                    request['scenario'],
                    request.get('iterations', 1000)
                )
            
            elif action == 'get_simulation_history':
                return self._get_simulation_history(
                    request.get('scenario'),
                    request.get('limit', 10)
                )
            
            elif action == 'create_scenario':
                return self._create_scenario(request['template'])
            
            elif action == 'get_scenario':
                return self._get_scenario(request['scenario_id'])
            
            elif action == 'update_scenario':
                return self._update_scenario(
                    request['scenario_id'],
                    request['updates']
                )
            
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown action: {action}'
                }
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _get_simulation_history(self, scenario: Optional[str] = None,
                              limit: int = 10) -> Dict[str, Any]:
        """Get simulation history with optional scenario filter."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT s.*, sc.name as scenario_name
            FROM simulations s
            JOIN scenarios sc ON s.scenario_id = sc.scenario_id
        '''
        params = []
        
        if scenario:
            query += ' WHERE sc.name = ?'
            params.append(scenario)
        
        query += ' ORDER BY s.start_time DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        simulations = cursor.fetchall()
        
        conn.close()
        
        return {
            'status': 'success',
            'simulations': [
                {
                    'simulation_id': row[0],
                    'scenario': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'iterations': row[4],
                    'best_action': json.loads(row[5]),
                    'expected_value': row[6],
                    'uncertainty': row[7],
                    'causal_analysis': json.loads(row[8]),
                    'counterfactuals': json.loads(row[9]),
                    'metadata': json.loads(row[10]),
                    'scenario_name': row[11]
                }
                for row in simulations
            ]
        }
    
    def _create_scenario(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new scenario from template."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scenarios 
            (name, type, description, initial_state, actions,
             constraints, evaluation_metrics, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            template['name'],
            template['type'],
            template['description'],
            json.dumps(template['initial_state']),
            json.dumps(template['actions']),
            json.dumps(template['constraints']),
            json.dumps(template['evaluation_metrics']),
            json.dumps(template.get('metadata', {})),
            datetime.now(),
            datetime.now()
        ))
        
        scenario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update scenario templates
        self.scenario_templates[template['name']] = ScenarioTemplate(
            name=template['name'],
            type=ScenarioType(template['type']),
            description=template['description'],
            initial_state=template['initial_state'],
            actions=template['actions'],
            constraints=template['constraints'],
            evaluation_metrics=template['evaluation_metrics'],
            metadata=template.get('metadata', {})
        )
        
        return {
            'status': 'success',
            'scenario_id': scenario_id
        }
    
    def _get_scenario(self, scenario_id: int) -> Dict[str, Any]:
        """Get scenario details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM scenarios WHERE scenario_id = ?', (scenario_id,))
        scenario = cursor.fetchone()
        
        conn.close()
        
        if scenario:
            return {
                'status': 'success',
                'scenario': {
                    'scenario_id': scenario[0],
                    'name': scenario[1],
                    'type': scenario[2],
                    'description': scenario[3],
                    'initial_state': json.loads(scenario[4]),
                    'actions': json.loads(scenario[5]),
                    'constraints': json.loads(scenario[6]),
                    'evaluation_metrics': json.loads(scenario[7]),
                    'metadata': json.loads(scenario[8]),
                    'created_at': scenario[9],
                    'updated_at': scenario[10]
                }
            }
        else:
            return {
                'status': 'error',
                'message': f'Scenario not found: {scenario_id}'
            }
    
    def _update_scenario(self, scenario_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update scenario details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current scenario
        cursor.execute('SELECT * FROM scenarios WHERE scenario_id = ?', (scenario_id,))
        scenario = cursor.fetchone()
        
        if not scenario:
            conn.close()
            return {
                'status': 'error',
                'message': f'Scenario not found: {scenario_id}'
            }
        
        # Update fields
        update_fields = []
        params = []
        
        for field, value in updates.items():
            if field in ['name', 'type', 'description', 'initial_state', 'actions',
                        'constraints', 'evaluation_metrics', 'metadata']:
                update_fields.append(f'{field} = ?')
                if field in ['initial_state', 'actions', 'constraints',
                           'evaluation_metrics', 'metadata']:
                    params.append(json.dumps(value))
                else:
                    params.append(value)
        
        if update_fields:
            update_fields.append('updated_at = ?')
            params.append(datetime.now())
            params.append(scenario_id)
            
            query = f'''
                UPDATE scenarios
                SET {', '.join(update_fields)}
                WHERE scenario_id = ?
            '''
            
            cursor.execute(query, params)
            conn.commit()
            
            # Update scenario templates
            if 'name' in updates:
                template = self.scenario_templates.pop(scenario[1])
                template.name = updates['name']
                self.scenario_templates[template.name] = template
            else:
                template = self.scenario_templates[scenario[1]]
                for field, value in updates.items():
                    setattr(template, field, value)
        
        conn.close()
        
        return {
            'status': 'success',
            'message': 'Scenario updated successfully'
        }
    
    def start(self):
        try:
            while True:
                # Receive message
                identity, _, message = self.socket.recv_multipart()
                message = json.loads(message.decode())
                
                # Process message
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_multipart([
                    identity,
                    b'',
                    json.dumps(response).encode()
                ])
                
        except KeyboardInterrupt:
            logger.info("Shutting down DreamWorld Agent...")
        finally:
            self.socket.close()
            self.context.term()


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to ScenarioType

        base_status.update({

            'service': 'ScenarioType',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status

    def run(self):

        """Run the agent's main loop."""

        logger.info(f"Starting {self.__class__.__name__} on port {self.port}")

        # Main loop implementation

        try:

            while True:

                # Your main processing logic here

                pass

        except KeyboardInterrupt:

            logger.info("Keyboard interrupt received, shutting down...")

        except Exception as e:

            logger.error(f"Error in main loop: {e}")

            raise



    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()
            
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Process message and return response
        return {"status": "success", "message": "Dream world updated"}



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ScenarioType()
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