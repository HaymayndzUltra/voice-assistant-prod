#!/usr/bin/env python3
"""
Unified Memory and Reasoning Agent for PC2
Combines features from:
- Contextual Memory Agent
- Memory Agent
- Context Manager
- Error Pattern Memory
"""

import zmq
import json
import os
import threading
import time
import logging
import hashlib
import traceback
import numpy as np
import re
from datetime import datetime
from collections import deque
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Constants
LOG_PATH = "logs/unified_memory_reasoning_agent.log"
CONTEXT_STORE_PATH = "memory_store.json"
ERROR_PATTERNS_PATH = "error_patterns.json"
TWIN_STORE_PATH = "digital_twin_store.json"  # Added for digital twin storage
ZMQ_PORT = 5596  # Unique port for PC2
HEALTH_CHECK_PORT = 5617  # Health check port, changed from 5597 to avoid conflict with DTA

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedMemoryReasoning")

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

class UnifiedMemoryReasoningAgent:
    def __init__(self, zmq_port=ZMQ_PORT, health_check_port=HEALTH_CHECK_PORT):
        """Initialize the unified memory and reasoning agent"""
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.health_socket = self.context.socket(zmq.REP)
        
        try:
            self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
            self.health_socket.bind(f"tcp://0.0.0.0:{health_check_port}")
            logger.info(f"Agent bound to ports {zmq_port} (main) and {health_check_port} (health)")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to ports: {e}")
            raise RuntimeError(f"Cannot bind to ports {zmq_port}/{health_check_port}")
        
        # Memory stores
        self.context_store = self.load_context_store()
        self.error_patterns = self.load_error_patterns()
        self.twins = self.load_twins()  # Added for digital twin storage
        
        # Context management
        self.context_manager = ContextManager()
        
        # Threading and locks
        self.lock = threading.Lock()
        self.running = True
        
        # Memory configuration
        self.max_session_history = 50
        self.token_budget_default = 2000
        self.token_compression_ratio = 0.8
        
        # Memory hierarchy
        self.memory_hierarchy = {
            "short_term": 50,    # Recent interactions
            "medium_term": 200,  # Less recent
            "long_term": 1000    # Historical
        }
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        self.health_check_count = 0
        self.update_count = 0
        self.get_count = 0
        self.delete_count = 0
        self.successful_updates = 0
        self.failed_updates = 0
        
        # Coordination sockets for other memory agents
        self.memory_agent_sockets = {}
        for agent, info in MEMORY_AGENT_REGISTRY.items():
            sock = self.context.socket(zmq.REQ)
            sock.connect(f"tcp://{info['host']}:{info['port']}")
            self.memory_agent_sockets[agent] = sock
        # Track in-progress operations for conflict resolution
        self.active_operations = {}
        
        logger.info("Unified Memory and Reasoning Agent initialized")
    
    def load_context_store(self):
        """Load context store from file"""
        if os.path.exists(CONTEXT_STORE_PATH):
            with open(CONTEXT_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"sessions": {}, "summaries": {}}
    
    def save_context_store(self):
        """Save context store to file"""
        with open(CONTEXT_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.context_store, f, ensure_ascii=False, indent=2)
    
    def load_error_patterns(self):
        """Load error patterns from file"""
        if os.path.exists(ERROR_PATTERNS_PATH):
            with open(ERROR_PATTERNS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"patterns": {}, "history": []}
    
    def save_error_patterns(self):
        """Save error patterns to file"""
        with open(ERROR_PATTERNS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.error_patterns, f, ensure_ascii=False, indent=2)
    
    def load_twins(self):
        """Load digital twins from the store file"""
        try:
            if os.path.exists(TWIN_STORE_PATH):
                with open(TWIN_STORE_PATH, "r", encoding="utf-8") as f:
                    twins = json.load(f)
                logger.info(f"Loaded {len(twins)} digital twins from store")
                return twins
            logger.info("No existing twin store found, starting with empty store")
            return {}
        except Exception as e:
            logger.error(f"Error loading twin store: {e}")
            return {}

    def save_twins(self):
        """Save digital twins to the store file"""
        try:
            with open(TWIN_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.twins, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.twins)} digital twins to store")
            return True
        except Exception as e:
            logger.error(f"Error saving twin store: {e}")
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
            
            # Keep history manageable
            if len(self.error_patterns["history"]) > 1000:
                self.error_patterns["history"] = self.error_patterns["history"][-1000:]
            
            self.save_error_patterns()
            return True
    
    def get_error_solution(self, error_message):
        """Get solution for an error pattern"""
        for error_type, data in self.error_patterns["patterns"].items():
            if re.search(data["pattern"], error_message, re.IGNORECASE):
                # Update occurrence count
                data["occurrence_count"] += 1
                data["last_seen"] = time.time()
                self.save_error_patterns()
                return data["solution"]
        return None
    
    def get_context_summary(self, session_id, max_tokens=None):
        """Get context summary for a session"""
        try:
            if "summaries" not in self.context_store or session_id not in self.context_store["summaries"]:
                # Generate new summary if needed
                summary = self._update_session_summary(session_id)
            else:
                summary = self.context_store["summaries"][session_id]
            
            if not summary:
                return None
            
            # Apply token limit if specified
            if max_tokens:
                # Simple token estimation (rough)
                total_tokens = len(str(summary)) // 4
                if total_tokens > max_tokens:
                    # Compress summary
                    compression_ratio = max_tokens / total_tokens
                    summary = self._compress_summary(summary, compression_ratio)
            
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

    def handle_request(self, request):
        """Handle incoming requests"""
        try:
            action = request.get("action")
            user_id = request.get("user_id", "default")
            
            # Update request tracking
            with self.lock:
                self.request_count += 1
                self.last_request_time = time.time()
            
            if action == "health_check":
                self.health_check_count += 1
                return self.get_status()
            
            # Digital Twin Actions
            elif action == "update_twin":
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
            
            elif action == "get_all_memories":
                # Return all memories (interactions) from all sessions as a flat list
                all_memories = []
                with self.lock:
                    sessions = self.context_store.get("sessions", {})
                    for session_id, interactions in sessions.items():
                        for interaction in interactions:
                            # Add type, freshness_score, timestamp for decay manager
                            memory = {
                                "type": interaction.get("metadata", {}).get("memory_type", "short_term"),
                                "freshness_score": interaction.get("metadata", {}).get("freshness_score", 1.0),
                                "timestamp": datetime.fromtimestamp(interaction.get("timestamp", time.time())).isoformat(),
                                "session_id": session_id,
                                "content": interaction.get("content", "")
                            }
                            all_memories.append(memory)
                return {"status": "success", "memories": all_memories}
            
            # Add priority and conflict resolution logic
            op_id = request.get('op_id', hashlib.md5(json.dumps(request, sort_keys=True).encode()).hexdigest())
            priority = request.get('priority', 'normal')
            # Conflict resolution
            if not self.resolve_conflict(op_id, priority):
                return {'status': 'error', 'error': 'Operation conflict: lower priority'}
            # Memory coordination example
            if request.get('coordinate_with'):
                agent = request['coordinate_with']
                operation = request.get('operation', 'read')
                data = request.get('data', {})
                coord_result = self.coordinate_memory(agent, operation, data, priority)
                return {'status': 'coordinated', 'result': coord_result}
            
            else:
                return {"status": "error", "reason": "Unknown action"}
                
        except Exception as e:
            logger.error(f"[UMRA] Error handling request: {e}")
            with self.lock:
                self.error_count += 1
            return {"status": "error", "reason": str(e)}
    
    def get_status(self):
        """Get the current status of the Unified Memory Reasoning Agent"""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                "status": "ok",
                "service": "unified_memory_reasoning_agent",
                "timestamp": time.time(),
                "uptime_seconds": uptime,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "last_request_time": self.last_request_time,
                "health_check_count": self.health_check_count,
                "update_count": self.update_count,
                "get_count": self.get_count,
                "delete_count": self.delete_count,
                "successful_updates": self.successful_updates,
                "failed_updates": self.failed_updates,
                "total_twins": len(self.twins),
                "total_sessions": len(self.context_store),
                "total_error_patterns": len(self.error_patterns),
                "bind_address": f"tcp://0.0.0.0:{ZMQ_PORT}",
                "health_check_address": f"tcp://0.0.0.0:{HEALTH_CHECK_PORT}"
            }
    
    def run(self):
        """Main service loop"""
        logger.info("Starting main service loop")
        
        while self.running:
            try:
                # Check main socket
                if self.socket.poll(timeout=100) == zmq.POLLIN:
                    msg = self.socket.recv_string()
                    request = json.loads(msg)
                    response = self.handle_request(request)
                    self.socket.send_string(json.dumps(response))
                
                # Check health socket
                if self.health_socket.poll(timeout=100) == zmq.POLLIN:
                    msg = self.health_socket.recv_string()
                    response = self.get_status()
                    self.health_socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                time.sleep(1)  # Prevent tight loop on error
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        self.socket.close()
        self.health_socket.close()
        self.context.term()
        logger.info("Agent stopped")

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
