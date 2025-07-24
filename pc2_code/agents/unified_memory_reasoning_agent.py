#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Unified Memory and Reasoning Agent for PC2
Combines features from:
- Contextual Memory Agent
- Memory Agent
- Context Manager
- Error Pattern Memory
"""

from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import os
import threading
import time
import logging
import hashlib
import traceback
# LAZY LOADING: import numpy as np
import re
from datetime import datetime
from collections import deque
from pathlib import Path
import sys


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.path_manager import PathManager
sys.path.insert(0, str(PathManager.get_project_root()))
# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.core.base_agent import BaseAgent
from pc2_code.config.system_config import config
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(Path(PathManager.get_project_root()) / "logs" / str(PathManager.get_logs_dir() / "unified_memory_reasoning_agent.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedMemoryReasoning")

# Define default constants (will be overridden by config)
DEFAULT_CONTEXT_STORE_PATH = "memory_store.json"
DEFAULT_ERROR_PATTERNS_PATH = "error_patterns.json"
DEFAULT_TWIN_STORE_PATH = "digital_twin_store.json"

# Memory agent registry for coordination
MEMORY_AGENT_REGISTRY = {
    'episodic': {'port': 5597, 'host': 'localhost'},
    'dreamworld': {'port': 5599, 'host': 'localhost'},
    # Add more agents as needed
}

# Priority levels
PRIORITY_LEVELS = {
    'low': 1,
    'normal': 5,
    'high': 10
}

class ContextManager:
    """Advanced context management for voice assistant conversations"""
    
    def __init__(self, min_size=5, max_size=20, initial_size=10):
        # Context window configuration
        self.min_size = min_size
        self.max_size = max_size
        self.current_size = initial_size
        self.context_window = deque(maxlen=self.current_size)
        
        # Context importance scoring
        self.importance_scores = {}
        self.importance_threshold = 0.5  # Minimum score to keep in context
        
        # Speaker-specific context
        self.speaker_contexts = {}
        
        # Keywords that indicate important context
        self.important_keywords = [
            'remember', 'don\'t forget', 'important', 'critical', 'essential',
            'alalahanin', 'tandaan', 'mahalaga', 'importante', 'kailangan'
        ]
        
        logger.info(f"[ContextManager] Initialized with size range {min_size}-{max_size}, current: {initial_size}")
    
    def add_to_context(self, text, speaker=None, metadata=None):
        """Add a new item to the context window with importance scoring"""
        if not text:
            return
            
        # Generate timestamp
        timestamp = time.time()
        
        # Calculate importance score
        importance = self._calculate_importance(text)
        
        # Create context item
        context_item = {
            'text': text,
            'timestamp': timestamp,
            'speaker': speaker,
            'importance': importance,
            'metadata': metadata or {}
        }
        
        # Add to main context window
        self.context_window.append(context_item)
        self.importance_scores[text] = importance
        
        # Add to speaker-specific context if applicable
        if speaker:
            if speaker not in self.speaker_contexts:
                self.speaker_contexts[speaker] = deque(maxlen=self.max_size)
            self.speaker_contexts[speaker].append(context_item)
        
        # Adjust context window size if needed
        self._adjust_context_size()
        
        logger.debug(f"[ContextManager] Added to context: '{text[:30]}...' (Score: {importance:.2f})")
    
    def get_context(self, speaker=None, max_items=None):
        """Get current context, optionally filtered by speaker"""
        if speaker and speaker in self.speaker_contexts:
            # Return speaker-specific context
            context = list(self.speaker_contexts[speaker])
        else:
            # Return general context
            context = list(self.context_window)
        
        # Sort by importance and recency
        context.sort(key=lambda x: (x['importance'], x['timestamp']), reverse=True)
        
        # Limit number of items if specified
        if max_items:
            context = context[:max_items]
            
        return context
    
    def get_context_text(self, speaker=None, max_items=None):
        """Get context as formatted text for LLM input"""
        context = self.get_context(speaker, max_items)
        
        # Format context items
        formatted_items = []
        for item in context:
            speaker_prefix = f"[{item['speaker']}]: " if item['speaker'] else ""
            formatted_items.append(f"{speaker_prefix}{item['text']}")
        
        return "\n".join(formatted_items)
    
    def clear_context(self, speaker=None):
        """Clear context, optionally only for a specific speaker"""
        if speaker:
            if speaker in self.speaker_contexts:
                self.speaker_contexts[speaker].clear()
                logger.info(f"[ContextManager] Cleared context for speaker: {speaker}")
        else:
            self.context_window.clear()
            self.importance_scores.clear()
            logger.info("[ContextManager] Cleared all context")
    
    def _calculate_importance(self, text):
        """Calculate importance score for a context item"""
        # Base importance
        importance = 0.5
        
        # Check for important keywords
        for keyword in self.important_keywords:
            if keyword.lower() in text.lower():
                importance += 0.2
                break
        
        # Check for questions (likely important)
        if '?' in text:
            importance += 0.1
        
        # Check for commands/requests
        command_patterns = [
            r'\b(please|paki|pakiusap)\b',
            r'\b(can you|could you|would you)\b',
            r'\b(i want|i need|i would like)\b',
            r'\b(gusto ko|kailangan ko)\b'
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, text.lower()):
                importance += 0.1
                break
        
        # Longer texts might contain more information
        if len(text.split()) > 15:
            importance += 0.1
        
        # Cap importance between 0 and 1
        return min(1.0, max(0.0, importance))
    
    def _adjust_context_size(self):
        """Dynamically adjust context window size based on conversation complexity"""
        # Calculate average importance
        avg_importance = np.mean(list(self.importance_scores.values())) if self.importance_scores else 0.5
        
        # Calculate conversation complexity (higher importance = more complex)
        if avg_importance > 0.7:
            # Complex conversation, increase context size
            target_size = min(self.max_size, self.current_size + 2)
        elif avg_importance < 0.3:
            # Simple conversation, decrease context size
            target_size = max(self.min_size, self.current_size - 1)
        else:
            # Maintain current size
            return
        
        # Only change if different from current
        if target_size != self.current_size:
            # Create new deque with new size
            new_context = deque(self.context_window, maxlen=target_size)
            self.context_window = new_context
            self.current_size = target_size
            logger.info(f"[ContextManager] Adjusted context size to {target_size} (avg importance: {avg_importance:.2f})")
    
    def prune_context(self):
        """Remove low-importance items if context is full"""
        if len(self.context_window) < self.current_size:
            return
            
        # Find items below threshold
        items_to_remove = []
        for item in self.context_window:
            if item['importance'] < self.importance_threshold:
                items_to_remove.append(item)
        
        # Remove low-importance items (up to 25% of window)
        max_to_remove = max(1, self.current_size // 4)
        for item in items_to_remove[:max_to_remove]:
            self.context_window.remove(item)
            if item['text'] in self.importance_scores:
                del self.importance_scores[item['text']]
            
        if items_to_remove:
            logger.debug(f"[ContextManager] Pruned {len(items_to_remove[:max_to_remove])} low-importance items")

class UnifiedMemoryReasoningAgent(BaseAgent):

    def _lazy_import_dependencies(self):
        """Lazy import heavy dependencies only when needed"""
        if not hasattr(self, '_dependencies_loaded'):
            try:
                import numpy as np
                self._dependencies_loaded = True
                if hasattr(self, 'logger'):
                    self.logger.info(f'{self.name}: Dependencies loaded successfully')
            except ImportError as e:
                self._dependencies_loaded = False
                if hasattr(self, 'logger'):
                    self.logger.error(f'{self.name}: Failed to load dependencies: {e}')
        return self._dependencies_loaded


    def _lazy_import_dependencies(self):
        """Lazy import heavy dependencies only when needed"""
        if not hasattr(self, '_dependencies_loaded'):
            try:
# LAZY LOADING:                 import numpy as np
                self._dependencies_loaded = True
                if hasattr(self, 'logger'):
                    self.logger.info(f'{self.name}: Dependencies loaded successfully')
            except ImportError as e:
                self._dependencies_loaded = False
                if hasattr(self, 'logger'):
                    self.logger.error(f'{self.name}: Failed to load dependencies: {e}')
        return self._dependencies_loaded

    """Unified Memory and Reasoning Agent that handles context, digital twins, and error patterns"""
    
    def __init__(self, zmq_port=7105, health_check_port=7106):
        """Initialize the unified memory and reasoning agent"""
        # Initialize BaseAgent first
        super().__init__(name="UnifiedMemoryReasoningAgent", port=zmq_port, 
                         health_check_port=health_check_port)
                         
        # Initialize lock for thread safety
        self.lock = threading.Lock()
        
        # Define storage paths
        self.context_store_path = config.get("context_store_path", DEFAULT_CONTEXT_STORE_PATH)
        self.error_patterns_path = config.get("error_patterns_path", DEFAULT_ERROR_PATTERNS_PATH)
        self.twin_store_path = config.get("twin_store_path", DEFAULT_TWIN_STORE_PATH)
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Initialize basic state
        self.initialized = False
        self.initialization_error = None
        
        # Memory configuration
        self.max_session_history = config.get("max_session_history", 50)
        self.token_budget_default = config.get("token_budget_default", 2000)
        self.token_compression_ratio = config.get("token_compression_ratio", 0.8)
        
        # Memory hierarchy
        self.memory_hierarchy = {
            "short_term": 50,    # Recent interactions
            "medium_term": 200,  # Less recent
            "long_term": 1000    # Historical
        }
        
        # Initialize empty data structures
        self.context_store = {"sessions": {}, "summaries": {}}
        self.error_patterns = {"patterns": {}, "history": []}
        self.twins = {}
        self.context_manager = None
        self.memory_agent_sockets = {}
        self.active_operations = {}
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        self.health_check_count = 0
        self.update_count = 0
        self.get_count = 0
        self.delete_count = 0
        self.successful_updates = 0
        self.failed_updates = 0
        
        logger.info("Unified Memory and Reasoning Agent initialized")
    
    def _perform_initialization(self):
        """Initialize agent components in background thread."""
        try:
            # Memory stores
            self.context_store = self.load_context_store()
            self.error_patterns = self.load_error_patterns()
            self.twins = self.load_twins()
            
            # Context management
            self.context_manager = ContextManager()
            
            # Coordination sockets for other memory agents (optional)
            self.memory_agent_sockets = {}
            for agent, info in MEMORY_AGENT_REGISTRY.items():
                try:
                    sock = self.context.socket(zmq.REQ)
                    sock.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
                    sock.connect(f"tcp://{info['host']}:{info['port']}")
                    self.memory_agent_sockets[agent] = sock
                    logger.info(f"Connected to memory agent: {agent}")
                except Exception as e:
                    logger.warning(f"Failed to connect to memory agent {agent}: {str(e)}")
            
            # Track in-progress operations for conflict resolution
            self.active_operations = {}
            
            self.initialized = True
            logger.info("Unified Memory and Reasoning Agent initialization completed")
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Unified Memory and Reasoning Agent initialization failed: {str(e)}")
            self.report_error("initialization_error", str(e), context={"agent": self.name})
    
    def load_context_store(self):
        """Load context store from file"""
        if os.path.exists(self.context_store_path):
            with open(self.context_store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"sessions": {}, "summaries": {}}
    
    def save_context_store(self):
        """Save context store to file"""
        with open(self.context_store_path, "w", encoding="utf-8") as f:
            json.dump(self.context_store, f, ensure_ascii=False, indent=2)
    
    def load_error_patterns(self):
        """Load error patterns from file"""
        if os.path.exists(self.error_patterns_path):
            with open(self.error_patterns_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"patterns": {}, "history": []}
    
    def save_error_patterns(self):
        """Save error patterns to file"""
        with open(self.error_patterns_path, "w", encoding="utf-8") as f:
            json.dump(self.error_patterns, f, ensure_ascii=False, indent=2)
    
    def load_twins(self):
        """Load digital twins from the store file"""
        try:
            if os.path.exists(self.twin_store_path):
                with open(self.twin_store_path, "r", encoding="utf-8") as f:
                    twins = json.load(f)
                logger.info(f"Loaded {len(twins)} digital twins from store")
                return twins
            logger.info("No existing twin store found, starting with empty store")
            return {}
        except Exception as e:
            logger.error(f"Error loading twin store: {e}")
            self.report_error("twin_store_error", f"Error loading twin store: {e}")
            return {}

    def save_twins(self):
        """Save digital twins to the store file"""
        try:
            with open(self.twin_store_path, "w", encoding="utf-8") as f:
                json.dump(self.twins, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.twins)} digital twins to store")
            return True
        except Exception as e:
            logger.error(f"Error saving twin store: {e}")
            self.report_error("twin_store_error", f"Error saving twin store: {e}")
            return False

    def update_twin(self, user_id, twin_data):
        """Update a user's digital twin"""
        with self.lock:
            self.twins[user_id] = twin_data
            if self.save_twins():
                self.successful_updates += 1
                logger.info(f"[UMRA] Updated twin for {user_id}")
                return True
            self.failed_updates += 1
            return False

    def get_twin(self, user_id):
        """Get a user's digital twin"""
        with self.lock:
            return self.twins.get(user_id, {})

    def delete_twin(self, user_id):
        """Delete a user's digital twin"""
        with self.lock:
            if user_id in self.twins:
                del self.twins[user_id]
                if self.save_twins():
                    logger.info(f"[UMRA] Deleted twin for {user_id}")
                    return True
            return False
    
    def get_session_id(self, user_id="default", project_name=None):
        """Generate a unique session ID"""
        if project_name:
            return f"{user_id}_{project_name}"
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{user_id}_{today}"
    
    def add_interaction(self, session_id, interaction_type, content, metadata=None):
        """Add a new interaction to session history"""
        with self.lock:
            if "sessions" not in self.context_store:
                self.context_store["sessions"] = {}
            
            if session_id not in self.context_store["sessions"]:
                self.context_store["sessions"][session_id] = []
            
            interaction = {
                "timestamp": time.time(),
                "type": interaction_type,
                "content": content,
            }
            
            if metadata:
                interaction["metadata"] = metadata
            
            self.context_store["sessions"][session_id].insert(0, interaction)
            
            if len(self.context_store["sessions"][session_id]) > self.max_session_history:
                self._update_session_summary(session_id)
                self.context_store["sessions"][session_id] = self.context_store["sessions"][session_id][:self.max_session_history]
            
            self.save_context_store()
            return True
    
    def _update_session_summary(self, session_id):
        """Create or update session summary"""
        try:
            if "sessions" not in self.context_store or session_id not in self.context_store["sessions"]:
                logger.warning(f"No session data found for {session_id}")
                return {
                    "last_updated": time.time(),
                    "code_context": "",
                    "conversation_summary": "",
                    "errors_encountered": [],
                    "key_decisions": []
                }
            
            session_data = self.context_store["sessions"][session_id]
            
            if "summaries" not in self.context_store:
                self.context_store["summaries"] = {}
            
            summary = {
                "last_updated": time.time()
            }
            
            # Process code snippets
            code_snippets = [entry["content"] for entry in session_data if entry["type"] == "code"]
            if code_snippets:
                code_summary = self._summarize_code(code_snippets)
                summary["code_context"] = code_summary
            
            # Process conversation
            user_queries = [entry["content"] for entry in session_data if entry["type"] == "user_query"]
            system_responses = [entry["content"] for entry in session_data if entry["type"] == "system_response"]
            if user_queries or system_responses:
                summary["conversation_summary"] = self._summarize_conversation(user_queries, system_responses)
            
            # Process errors
            errors = [entry["content"] for entry in session_data if entry["type"] == "error"]
            if errors:
                summary["errors_encountered"] = self._extract_key_errors(errors)
            else:
                summary["errors_encountered"] = []
            
            self.context_store["summaries"][session_id] = summary
            self.save_context_store()
            return summary
            
        except Exception as e:
            logger.error(f"Error updating session summary: {e}")
            return None
    
    def _summarize_code(self, code_snippets):
        """Summarize code snippets with domain detection"""
        try:
            # Combine all code
            all_code = "\n\n".join(code_snippets)
            
            # Detect domains
            domains = []
            if re.search(r"database|sql|sqlite", all_code.lower()):
                domains.append("database operations")
            if re.search(r"web|http|flask|api|route", all_code.lower()):
                domains.append("web functionality")
            if re.search(r"concurrency|thread|async", all_code.lower()):
                domains.append("concurrency features")
            
            # Create summary
            summary = f"Code Summary:\n"
            summary += f"Total snippets: {len(code_snippets)}\n"
            if domains:
                summary += f"Detected domains: {', '.join(domains)}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing code: {e}")
            return "Error summarizing code"
    
    def _summarize_conversation(self, user_queries, system_responses):
        """Summarize conversation history"""
        try:
            summary = "Conversation Summary:\n"
            summary += f"Total exchanges: {len(user_queries)}\n"
            
            # Add recent exchanges
            if user_queries:
                summary += "\nRecent exchanges:\n"
                for i in range(min(3, len(user_queries))):
                    summary += f"User: {user_queries[i][:100]}...\n"
                    if i < len(system_responses):
                        summary += f"System: {system_responses[i][:100]}...\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            return "Error summarizing conversation"
    
    def _extract_key_errors(self, errors):
        """Extract and categorize key errors"""
        try:
            key_errors = []
            for error in errors:
                # Basic error categorization
                if "timeout" in error.lower():
                    key_errors.append({"type": "timeout", "message": error})
                elif "connection" in error.lower():
                    key_errors.append({"type": "connection", "message": error})
                elif "permission" in error.lower():
                    key_errors.append({"type": "permission", "message": error})
                else:
                    key_errors.append({"type": "other", "message": error})
            
            return key_errors
            
        except Exception as e:
            logger.error(f"Error extracting key errors: {e}")
            return []
    
    def add_error_pattern(self, error_type, pattern, solution=None):
        """Add a new error pattern"""
        with self.lock:
            if "patterns" not in self.error_patterns:
                self.error_patterns["patterns"] = {}
            
            self.error_patterns["patterns"][error_type] = {
                "pattern": pattern,
                "solution": solution,
                "last_seen": time.time(),
                "occurrence_count": 1
            }
            
            # Add to history
            if "history" not in self.error_patterns:
                self.error_patterns["history"] = []
            
            self.error_patterns["history"].append({
                "timestamp": time.time(),
                "error_type": error_type,
                "pattern": pattern,
                "solution": solution
            })
            
            self.save_error_patterns()
            return True
    
    def get_error_solution(self, error_message):
        """Get solution for an error pattern"""
        try:
            for error_type, data in self.error_patterns.get("patterns", {}).items():
                if re.search(data["pattern"], error_message, re.IGNORECASE):
                    # Update occurrence count
                    data["occurrence_count"] += 1
                    data["last_seen"] = time.time()
                    self.save_error_patterns()
                    return data["solution"]
            return None
        except Exception as e:
            logger.error(f"Error getting error solution: {e}")
            return None
    
    def get_context_summary(self, session_id, max_tokens=None):
        """Get context summary for a session"""
        try:
            if "summaries" not in self.context_store or session_id not in self.context_store["summaries"]:
                # For simplicity, return a basic summary
                return {
                    "last_updated": time.time(),
                    "session_id": session_id,
                    "context": f"New session: {session_id}"
                }
            else:
                summary = self.context_store["summaries"][session_id]
                return summary
        except Exception as e:
            logger.error(f"Error getting context summary: {e}")
            return None
    
    def _compress_summary(self, summary, ratio):
        """Compress summary to fit token budget"""
        try:
            compressed = {}
            
            # Compress code context
            if "code_context" in summary:
                code_lines = summary["code_context"].split("\n")
                keep_lines = int(len(code_lines) * ratio)
                compressed["code_context"] = "\n".join(code_lines[:keep_lines])
            
            # Compress conversation summary
            if "conversation_summary" in summary:
                conv_lines = summary["conversation_summary"].split("\n")
                keep_lines = int(len(conv_lines) * ratio)
                compressed["conversation_summary"] = "\n".join(conv_lines[:keep_lines])
            
            # Keep errors and decisions as is
            if "errors_encountered" in summary:
                compressed["errors_encountered"] = summary["errors_encountered"]
            if "key_decisions" in summary:
                compressed["key_decisions"] = summary["key_decisions"]
            
            compressed["last_updated"] = summary["last_updated"]
            return compressed
            
        except Exception as e:
            logger.error(f"Error compressing summary: {e}")
            return summary
    
    def coordinate_memory(self, agent_name, operation, data, priority='normal'):
        """Coordinate a memory operation with another agent, with priority"""
        if agent_name not in self.memory_agent_sockets:
            logger.warning(f"Unknown memory agent: {agent_name}")
            return {'status': 'error', 'error': 'Unknown agent'}
        req = {
            'operation': operation,
            'data': data,
            'priority': priority
        }
        self.memory_agent_sockets[agent_name].send_string(json.dumps(req))
        poller = zmq.Poller()
        poller.register(self.memory_agent_sockets[agent_name], zmq.POLLIN)
        if poller.poll(5000):
            resp = self.memory_agent_sockets[agent_name].recv_string()
            return json.loads(resp)
        else:
            return {'status': 'error', 'error': 'Timeout'}

    def resolve_conflict(self, op_id, new_priority):
        """Resolve conflicts between memory operations based on priority"""
        if op_id in self.active_operations:
            existing_priority = self.active_operations[op_id]['priority']
            if PRIORITY_LEVELS[new_priority] > PRIORITY_LEVELS[existing_priority]:
                logger.info(f"Conflict resolved: {op_id} updated to higher priority {new_priority}")
                self.active_operations[op_id]['priority'] = new_priority
                return True
            else:
                logger.info(f"Conflict: {op_id} retains priority {existing_priority}")
                return False
        else:
            self.active_operations[op_id] = {'priority': new_priority}
            return True

    # Override handle_request method from BaseAgent
    def handle_request(self, request):
        """Handle incoming requests"""
        try:
            # If it's a health check, use BaseAgent's health check
            if request.get("action") in ["health_check", "ping", "health"]:
                return self._get_health_status()
            
            action = request.get("action")
            user_id = request.get("user_id", "default")
            
            # Update request tracking
            with self.lock:
                self.request_count += 1
                self.last_request_time = time.time()
            
            # Digital Twin Actions
            if action == "update_twin":
                self.update_count += 1
                twin_data = request.get("twin_data")
                if not twin_data:
                    self.failed_updates += 1
                    return {"status": "error", "reason": "No twin data provided"}
                
                if self.update_twin(user_id, twin_data):
                    return {"status": "ok"}
                return {"status": "error", "reason": "Failed to save twin data"}
                
            elif action == "get_twin":
                self.get_count += 1
                twin = self.get_twin(user_id)
                return {"status": "ok", "twin": twin}
                
            elif action == "delete_twin":
                self.delete_count += 1
                if self.delete_twin(user_id):
                    return {"status": "ok"}
                return {"status": "error", "reason": "User not found"}
            
            # Existing Memory Actions
            elif action == "add_interaction":
                session_id = request.get("session_id")
                interaction_type = request.get("interaction_type")
                content = request.get("content")
                metadata = request.get("metadata")
                
                if not all([session_id, interaction_type, content]):
                    return {"status": "error", "reason": "Missing required fields"}
                
                self.add_interaction(session_id, interaction_type, content, metadata)
                return {"status": "ok"}
                
            elif action == "get_context":
                session_id = request.get("session_id")
                max_tokens = request.get("max_tokens")
                
                if not session_id:
                    return {"status": "error", "reason": "Missing session_id"}
                
                summary = self.get_context_summary(session_id, max_tokens)
                return {"status": "ok", "context": summary}
                
            elif action == "add_error_pattern":
                error_type = request.get("error_type")
                pattern = request.get("pattern")
                solution = request.get("solution")
                
                if not all([error_type, pattern]):
                    return {"status": "error", "reason": "Missing required fields"}
                
                self.add_error_pattern(error_type, pattern, solution)
                return {"status": "ok"}
                
            elif action == "get_error_solution":
                error_message = request.get("error_message")
                
                if not error_message:
                    return {"status": "error", "reason": "Missing error_message"}
                
                solution = self.get_error_solution(error_message)
                return {"status": "ok", "solution": solution}
            
            else:
                return {"status": "error", "reason": "Unknown action"}
                
        except Exception as e:
            logger.error(f"[UMRA] Error handling request: {e}")
            self.report_error("request_handling_error", str(e), context={"request": request})
            with self.lock:
                self.error_count += 1
            return {"status": "error", "reason": str(e)}
    
    # Override get_health_status to add our own metrics
    def _get_health_status(self):
        """Get the current status of the Unified Memory Reasoning Agent"""
        # Get base health status from parent class
        base_status = super()._get_health_status()
        
        with self.lock:
            # Add our own metrics
            agent_status = {
                "service": "unified_memory_reasoning_agent",
                "request_count": self.request_count,
                "error_count": self.error_count,
                "last_request_time": self.last_request_time,
                "health_check_count": self.health_check_count,
                "update_count": self.update_count,
                "get_count": self.get_count,
                "delete_count": self.delete_count,
                "successful_updates": self.successful_updates,
                "failed_updates": self.failed_updates,
            }
            
            # Add initialization error if present
            if self.initialization_error:
                agent_status["initialization_error"] = self.initialization_error
            
            # Add memory statistics if initialized
            if self.initialized:
                agent_status.update({
                    "total_twins": len(self.twins) if hasattr(self, 'twins') else 0,
                    "total_sessions": len(self.context_store.get("sessions", {})) if hasattr(self, 'context_store') else 0,
                    "total_error_patterns": len(self.error_patterns.get("patterns", {})) if hasattr(self, 'error_patterns') else 0
                })
        
        # Update base status with our metrics
        base_status.update(agent_status)
        return base_status
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Cleaning up resources...")
        
        # Save any unsaved data
        try:
            if hasattr(self, 'context_store'):
                self.save_context_store()
            if hasattr(self, 'error_patterns'):
                self.save_error_patterns()
            if hasattr(self, 'twins'):
                self.save_twins()
        except Exception as e:
            logger.error(f"Error saving data during cleanup: {e}")
        
        # Close memory agent sockets
        if hasattr(self, 'memory_agent_sockets'):
            for agent, socket in self.memory_agent_sockets.items():
                try:
                    logger.debug(f"Closed socket for memory agent {agent}")
                except Exception as e:
                    logger.error(f"Error closing socket for memory agent {agent}: {e}")
        
        # Call parent class cleanup to handle standard sockets
        super().cleanup()
        logger.info("Cleanup complete")

def main():
    """Main entry point"""
    try:
        agent = UnifiedMemoryReasoningAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down agent")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
