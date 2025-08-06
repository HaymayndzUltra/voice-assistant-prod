#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# Context Summarizer Agent - For maintaining context in conversations with large LLMs
# Maintains a rolling summary of code, discussions, errors, and previous interactions
# Uses compression techniques to maximize context window efficiency

import zmq
import json
import os
import threading
import time
import logging
import hashlib
from datetime import datetime
from common.core.base_agent import BaseAgent
from common.env_helpers import get_env
from common.utils.log_setup import configure_logging

LOG_PATH = str(PathManager.get_logs_dir() / "context_summarizer_agent.log")
CONTEXT_STORE_PATH = "context_store.json"
ZMQ_CONTEXT_SUMMARIZER_PORT = 5610  # New agent port

logger = configure_logging(__name__)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class ContextSummarizerAgent(BaseAgent):
    def __init__(self, zmq_port=ZMQ_CONTEXT_SUMMARIZER_PORT):

        super().__init__(*args, **kwargs)        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
        self.context_store = self.load_context_store()
        self.lock = threading.Lock()
        self.running = True
        self.max_session_history = 50  # Maximum entries per session
        logging.info(f"[ContextSummarizer] Agent started on port {zmq_port}")
        
    def load_context_store(self):
        if os.path.exists(CONTEXT_STORE_PATH):
            with open(CONTEXT_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"sessions": {}, "summaries": {}}
    
    def save_context_store(self):
        with open(CONTEXT_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.context_store, f, ensure_ascii=False, indent=2)
    
    def get_session_id(self, user_id="default", project_name=None):
        """Generate a unique session ID based on user and optional project"""
        if project_name:
            return f"{user_id}_{project_name}"
        # Use today's date as part of the session ID if no project specified
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{user_id}_{today}"
    
    def add_interaction(self, session_id, interaction_type, content, metadata=None):
        """Add a new interaction to a session's history"""
        with self.lock:
            if "sessions" not in self.context_store:
                self.context_store["sessions"] = {}
                
            if session_id not in self.context_store["sessions"]:
                self.context_store["sessions"][session_id] = []
            
            # Add the new interaction
            interaction = {
                "timestamp": time.time(),
                "type": interaction_type,  # code, user_query, error, system_response, etc.
                "content": content,
            }
            
            if metadata:
                interaction["metadata"] = metadata
                
            # Add to beginning for efficiency (newer items first)
            self.context_store["sessions"][session_id].insert(0, interaction)
            
            # Trim if needed to keep session manageable
            if len(self.context_store["sessions"][session_id]) > self.max_session_history:
                # Before trimming, summarize the oldest items
                self._update_session_summary(session_id)
                # Then remove oldest items
                self.context_store["sessions"][session_id] = self.context_store["sessions"][session_id][:self.max_session_history]
            
            self.save_context_store()
            return True
    
    def _update_session_summary(self, session_id):
        """Create or update a summary for a session based on its history"""
        with self.lock:
            if "summaries" not in self.context_store:
                self.context_store["summaries"] = {}
                
            session_history = self.context_store["sessions"].get(session_id, [])
            if not session_history:
                return None
            
            # Initialize a summary structure if it doesn't exist
            if session_id not in self.context_store["summaries"]:
                self.context_store["summaries"][session_id] = {
                    "last_updated": time.time(),
                    "code_context": "",
                    "conversation_summary": "",
                    "errors_encountered": [],
                    "key_decisions": []
                }
            
            summary = self.context_store["summaries"][session_id]
            
            # Extract and organize content by type
            code_snippets = []
            user_queries = []
            system_responses = []
            errors = []
            
            for interaction in session_history:
                if interaction["type"] == "code":
                    code_snippets.append(interaction["content"])
                elif interaction["type"] == "user_query":
                    user_queries.append(interaction["content"])
                elif interaction["type"] == "system_response":
                    system_responses.append(interaction["content"])
                elif interaction["type"] == "error":
                    errors.append(interaction["content"])
            
            # Update the summary components
            if code_snippets:
                summary["code_context"] = self._summarize_code(code_snippets)
            
            if user_queries and system_responses:
                summary["conversation_summary"] = self._summarize_conversation(user_queries, system_responses)
            
            if errors:
                summary["errors_encountered"] = self._extract_key_errors(errors)
            
            summary["last_updated"] = time.time()
            self.save_context_store()
            return summary
    
    def _summarize_code(self, code_snippets):
        """Summarize code snippets to extract key components"""
        # This is a simplified version - a full implementation would use 
        # more sophisticated code analysis
        
        # Join all code snippets
        all_code = "\n\n".join(code_snippets)
        
        # Extract function names, class names, and other important structures
        import re

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
        functions = re.findall(r"def\s+(\w+)\s*\(", all_code)
        classes = re.findall(r"class\s+(\w+)\s*", all_code)
        imports = re.findall(r"import\s+(\w+)", all_code)
        
        # Create a summary
        summary = "Code contains: "
        if classes:
            summary += f"{len(classes)} classes ({', '.join(classes[:5])}{' and more' if len(classes) > 5 else ''}), "
        if functions:
            summary += f"{len(functions)} functions ({', '.join(functions[:5])}{' and more' if len(functions) > 5 else ''}), "
        if imports:
            summary += f"imports: {', '.join(imports[:5])}{' and more' if len(imports) > 5 else ''}"
        
        # Limit size while preserving key information
        if len(summary) > 1000:
            summary = summary[:997] + "..."
        
        return summary
    
    def _summarize_conversation(self, user_queries, system_responses):
        """Create a summary of the conversation flow"""
        combined = []
        
        # Pair queries and responses if possible
        for i, query in enumerate(user_queries):
            if i < len(system_responses):
                # Store only a short version
                short_query = query[:100] + "..." if len(query) > 100 else query
                # Just record that a response happened, not its content (to save space)
                combined.append(f"Q: {short_query} → Response provided")
        
        # Create a bullet list for the summary
        summary = "Recent conversation:\n"
        for item in combined[:5]:  # Limit to 5 most recent pairs
            summary += f"• {item}\n"
        
        if len(combined) > 5:
            summary += f"• ...and {len(combined)-5} earlier exchanges\n"
        
        return summary
    
    def _extract_key_errors(self, errors):
        """Extract and summarize key errors"""
        unique_errors = []
        error_hashes = set()
        
        for error in errors:
            # Create a hash for deduplication
            error_hash = hashlib.md5(error.encode().hexdigest()
            
            if error_hash not in error_hashes:
                error_hashes.add(error_hash)
                # Extract just the error type and message, not the full trace
                error_summary = error.split("\n")[0] if "\n" in error else error
                if len(error_summary) > 100:
                    error_summary = error_summary[:97] + "..."
                unique_errors.append(error_summary)
        
        return unique_errors[:5]  # Limit to 5 most recent unique errors
    
    def get_context_summary(self, session_id, max_tokens=1000):
        """Get a formatted context summary within token limit"""
        with self.lock:
            # First try to get an existing summary
            if "summaries" in self.context_store and session_id in self.context_store["summaries"]:
                summary = self.context_store["summaries"][session_id]
            else:
                # If no summary exists, create one now
                summary = self._update_session_summary(session_id)
                
            if not summary:
                return "No context available."
                
            # Format the summary for LLM consumption
            formatted_summary = f"CONTEXT SUMMARY (updated {datetime.fromtimestamp(summary['last_updated']).strftime('%Y-%m-%d %H:%M')})\n"
            
            # Add code context if available
            if summary["code_context"]:
                formatted_summary += f"\nCODE CONTEXT:\n{summary['code_context']}\n"
                
            # Add conversation summary if available
            if summary["conversation_summary"]:
                formatted_summary += f"\nCONVERSATION SUMMARY:\n{summary['conversation_summary']}\n"
                
            # Add errors if available
            if summary["errors_encountered"]:
                formatted_summary += "\nRECENT ERRORS:\n"
                for error in summary["errors_encountered"]:
                    formatted_summary += f"• {error}\n"
                    
            # Add key decisions if available
            if summary["key_decisions"]:
                formatted_summary += "\nKEY DECISIONS:\n"
                for decision in summary["key_decisions"]:
                    formatted_summary += f"• {decision}\n"
            
            # Simple token counting approximation
            tokens = len(formatted_summary.split()
            if tokens > max_tokens:
                # Truncate and add note about truncation
                words = formatted_summary.split()
                formatted_summary = " ".join(words[:max_tokens]) + f"\n[Note: Context truncated to {max_tokens} tokens]"
                
            return formatted_summary
    
    def record_key_decision(self, session_id, decision):
        """Record an important design decision or choice"""
        with self.lock:
            if "summaries" not in self.context_store:
                self.context_store["summaries"] = {}
                
            if session_id not in self.context_store["summaries"]:
                self._update_session_summary(session_id)
                
            if session_id in self.context_store["summaries"]:
                if "key_decisions" not in self.context_store["summaries"][session_id]:
                    self.context_store["summaries"][session_id]["key_decisions"] = []
                    
                self.context_store["summaries"][session_id]["key_decisions"].insert(0, decision)
                
                # Keep a reasonable number of decisions
                if len(self.context_store["summaries"][session_id]["key_decisions"]) > 10:
                    self.context_store["summaries"][session_id]["key_decisions"] = self.context_store["summaries"][session_id]["key_decisions"][:10]
                    
                self.save_context_store()
                return True
        
        return False
    
    def handle_query(self, query):
        """Process incoming requests to the agent"""
        action = query.get("action")
        user_id = query.get("user_id", "default")
        project = query.get("project")
        
        # Generate session ID
        session_id = self.get_session_id(user_id, project)
        
        if action == "add_interaction":
            interaction_type = query.get("type")
            content = query.get("content")
            metadata = query.get("metadata")
            
            success = self.add_interaction(session_id, interaction_type, content, metadata)
            return {"status": "ok" if success else "error"}
            
        elif action == "get_summary":
            max_tokens = query.get("max_tokens", 1000)
            summary = self.get_context_summary(session_id, max_tokens)
            return {"status": "ok", "summary": summary}
            
        elif action == "record_decision":
            decision = query.get("decision")
            success = self.record_key_decision(session_id, decision)
            return {"status": "ok" if success else "error"}
            
        elif action == "get_session_id":
            return {"status": "ok", "session_id": session_id}
            
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def run(self):
        """Main agent loop"""
        while self.running:
            try:
                # Wait for next request from client
                message = self.socket.recv_string()
                logging.info(f"[ContextSummarizer] Received request")
                
                # Parse the request
                query = json.loads(message)
                
                # Process the request
                response = self.handle_query(query)
                
                # Send reply back to client
                self.socket.send_string(json.dumps(response)
                
            except Exception as e:
                logging.error(f"[ContextSummarizer] Error: {str(e)}")
                # Try to send error response if possible
                try:
                    self.socket.send_string(json.dumps({"status": "error", "message": str(e)})
                except:
                    pass
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        logging.info(f"[ContextSummarizer] Agent stopping")

# Helper function to send requests to the agent
def send_context_request(request, port=ZMQ_CONTEXT_SUMMARIZER_PORT):
    """Send a request to the Context Summarizer Agent"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://127.0.0.1:{port}")
    
    socket.send_string(json.dumps(request)
    response = socket.recv_string()
    
    socket.close()
    context.term()
    
    return json.loads(response)

# Helper functions for other agents to use
def record_code(code, user_id="default", project=None, metadata=None):
    """Record code to the context history"""
    request = {
        "action": "add_interaction",
        "user_id": user_id,
        "project": project,
        "type": "code",
        "content": code,
        "metadata": metadata
    }
    return send_context_request(request)

def record_user_query(query, user_id="default", project=None):
    """Record a user query to the context history"""
    request = {
        "action": "add_interaction",
        "user_id": user_id,
        "project": project,
        "type": "user_query",
        "content": query
    }
    return send_context_request(request)

def record_system_response(response, user_id="default", project=None):
    """Record a system response to the context history"""
    request = {
        "action": "add_interaction",
        "user_id": user_id,
        "project": project,
        "type": "system_response",
        "content": response
    }
    return send_context_request(request)

def record_error(error, user_id="default", project=None):
    """Record an error to the context history"""
    request = {
        "action": "add_interaction",
        "user_id": user_id,
        "project": project,
        "type": "error",
        "content": error
    }
    return send_context_request(request)

def get_context_summary(user_id="default", project=None, max_tokens=1000):
    """Get a summary of the current context for a user/project"""
    request = {
        "action": "get_summary",
        "user_id": user_id,
        "project": project,
        "max_tokens": max_tokens
    }
    response = send_context_request(request)
    return response.get("summary", "")

def main():
    """Run the Context Summarizer Agent"""
    agent = ContextSummarizerAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        logging.error(f"[ContextSummarizer] Fatal error: {str(e)}")
    finally:
        agent.stop()

if __name__ == "__main__":
    main()
