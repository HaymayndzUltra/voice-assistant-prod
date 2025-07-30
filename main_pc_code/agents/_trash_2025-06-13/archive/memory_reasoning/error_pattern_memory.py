from main_pc_code.src.core.base_agent import BaseAgent
#!/usr/bin/env python3
# Error Pattern Memory - For tracking, learning, and suggesting fixes for common errors
# Maintains a database of encountered errors and their successful fixes
# Enables more intelligent auto-fix workflows

import zmq
import json
import os
import threading
import time
import logging
import re
import hashlib

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = str(PathManager.get_logs_dir() / "error_pattern_memory.log")
ERROR_PATTERN_STORE_PATH = "error_pattern_store.json"
ZMQ_ERROR_PATTERN_PORT = 5611  # New agent port

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class ErrorPatternMemory(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ErrorPatternMemory")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        self.error_store = self.load_error_store()
        self.lock = threading.Lock()
        self.running = True
        logging.info(f"[ErrorPatternMemory] Agent started on port {zmq_port}")
    
    def load_error_store(self):
        if os.path.exists(ERROR_PATTERN_STORE_PATH):
            with open(ERROR_PATTERN_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"errors": [], "fixes": {}, "success_rate": {}}
    
    def save_error_store(self):
        with open(ERROR_PATTERN_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.error_store, f, ensure_ascii=False, indent=2)
    
    def extract_error_signature(self, error_text):
        """
        Extract a normalized error signature from the full error text.
        This helps group similar errors together.
        """
        # Extract error type and message from Python-style tracebacks
        if "Traceback (most recent call last):" in error_text:
            # Extract the actual error line (last line of traceback)
            lines = error_text.strip().split('\n')
            for line in reversed(lines):
                if ': ' in line:
                    # For Python errors like "TypeError: cannot concatenate 'str' and 'int'"
                    parts = line.split(': ', 1)
                    if len(parts) == 2 and not parts[0].startswith(' '):
                        error_type, message = parts
                        return f"{error_type}: {message}"
            
            # Fallback: return last line if we couldn't parse it properly
            return lines[-1] if lines else error_text
        
        # For JavaScript/web-type errors
        if "Error:" in error_text:
            match = re.search(r'([A-Za-z]+Error:?[^:\n]+)', error_text)
            if match:
                return match.group(1)
        
        # For compiler errors, just take the first line
        first_line = error_text.split('\n')[0].strip()
        if first_line:
            return first_line
            
        # Fallback: use a truncated version of the full error
        return error_text[:100]
    
    def compute_error_hash(self, error_signature):
        """Compute a hash for an error signature for consistent lookup"""
        return hashlib.md5(error_signature.encode()).hexdigest()
    
    def normalize_code(self, code):
        """
        Normalize code by removing whitespace, variable names, etc.
        to better match similar code patterns
        """
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Remove empty lines and leading/trailing whitespace
        code = '\n'.join(line.strip() for line in code.split('\n') if line.strip())
        
        # For now, we'll keep it simple. In a more advanced version, 
        # you could replace variable names with placeholders.
        return code
    
    def record_error(self, error_text, code_context=None, language="python"):
        """
        Record a new error occurrence with optional code context
        Returns the error_id for referencing later
        """
        with self.lock:
            # Extract error signature
            error_signature = self.extract_error_signature(error_text)
            error_hash = self.compute_error_hash(error_signature)
            
            # Normalize code context if provided
            normalized_code = None
            if code_context:
                normalized_code = self.normalize_code(code_context)
            
            # Check if this error already exists
            found = False
            for error in self.error_store["errors"]:
                if error["hash"] == error_hash:
                    # Increment occurrence count
                    error["occurrences"] += 1
                    error["last_seen"] = time.time()
                    
                    # Add this code context if it's new
                    if normalized_code and normalized_code not in error["code_contexts"]:
                        error["code_contexts"].append(normalized_code)
                    
                    found = True
                    error_id = error["id"]
                    break
            
            # If it's a new error, add it
            if not found:
                error_id = len(self.error_store["errors"])
                new_error = {
                    "id": error_id,
                    "hash": error_hash,
                    "signature": error_signature,
                    "full_text": error_text[:500],  # Store just the first 500 chars to save space
                    "occurrences": 1,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "code_contexts": [normalized_code] if normalized_code else [],
                    "language": language
                }
                self.error_store["errors"].append(new_error)
                
                # Initialize success rate for new error
                self.error_store["success_rate"][str(error_id)] = {
                    "attempts": 0,
                    "successes": 0
                }
            
            self.save_error_store()
            return error_id
    
    def record_fix(self, error_id, fix_code, successful=True):
        """
        Record a fix attempt for a given error, and whether it was successful
        """
        with self.lock:
            error_id_str = str(error_id)
            
            # Normalize the fix code
            normalized_fix = self.normalize_code(fix_code)
            
            # Check if this error exists
            if error_id < len(self.error_store["errors"]):
                # Record in fixes dictionary if it doesn't exist
                if error_id_str not in self.error_store["fixes"]:
                    self.error_store["fixes"][error_id_str] = []
                
                # Check if this fix was already recorded
                fix_exists = False
                for fix in self.error_store["fixes"][error_id_str]:
                    if fix["normalized_code"] == normalized_fix:
                        # Update the fix's success count
                        fix["attempts"] += 1
                        if successful:
                            fix["successes"] += 1
                        fix["last_used"] = time.time()
                        fix_exists = True
                        break
                
                # If it's a new fix, add it
                if not fix_exists:
                    new_fix = {
                        "original_code": fix_code,
                        "normalized_code": normalized_fix,
                        "attempts": 1,
                        "successes": 1 if successful else 0,
                        "first_used": time.time(),
                        "last_used": time.time()
                    }
                    self.error_store["fixes"][error_id_str].append(new_fix)
                
                # Update overall success rate for this error
                if error_id_str not in self.error_store["success_rate"]:
                    self.error_store["success_rate"][error_id_str] = {
                        "attempts": 0,
                        "successes": 0
                    }
                
                self.error_store["success_rate"][error_id_str]["attempts"] += 1
                if successful:
                    self.error_store["success_rate"][error_id_str]["successes"] += 1
                
                self.save_error_store()
                return True
            
            return False
    
    def find_similar_errors(self, error_text, max_results=3):
        """
        Find errors similar to the given error text
        """
        with self.lock:
            error_signature = self.extract_error_signature(error_text)
            error_hash = self.compute_error_hash(error_signature)
            
            # First try exact match by hash
            exact_matches = []
            for error in self.error_store["errors"]:
                if error["hash"] == error_hash:
                    exact_matches.append(error)
            
            if exact_matches:
                return [e["id"] for e in exact_matches[:max_results]]
            
            # If no exact match, try keyword matching
            keywords = re.findall(r'\b\w+\b', error_signature)
            if not keywords:
                return []
            
            # Score each error by keyword matches
            scored_errors = []
            for error in self.error_store["errors"]:
                score = 0
                for keyword in keywords:
                    if keyword in error["signature"]:
                        score += 1
                if score > 0:
                    scored_errors.append((error["id"], score))
            
            # Sort by score (highest first) and return top matches
            scored_errors.sort(key=lambda x: x[1], reverse=True)
            return [id for id, _ in scored_errors[:max_results]]
    
    def get_best_fix(self, error_id):
        """
        Get the most successful fix for a given error
        """
        with self.lock:
            error_id_str = str(error_id)
            
            if error_id_str not in self.error_store["fixes"]:
                return None
            
            fixes = self.error_store["fixes"][error_id_str]
            if not fixes:
                return None
            
            # Sort fixes by success rate
            sorted_fixes = sorted(fixes, 
                                 key=lambda x: x["successes"] / max(x["attempts"], 1), 
                                 reverse=True)
            
            # Return the fix with the highest success rate
            return sorted_fixes[0]["original_code"]
    
    def get_all_fixes(self, error_id, ranked=True):
        """
        Get all recorded fixes for an error, optionally ranked by success rate
        """
        with self.lock:
            error_id_str = str(error_id)
            
            if error_id_str not in self.error_store["fixes"]:
                return []
            
            fixes = self.error_store["fixes"][error_id_str]
            if not fixes:
                return []
            
            if ranked:
                # Sort fixes by success rate
                fixes = sorted(fixes, 
                              key=lambda x: x["successes"] / max(x["attempts"], 1), 
                              reverse=True)
            
            # Return all fixes with their success rates
            return [{
                "code": fix["original_code"],
                "success_rate": fix["successes"] / max(fix["attempts"], 1),
                "attempts": fix["attempts"]
            } for fix in fixes]
    
    def get_error_details(self, error_id):
        """
        Get detailed information about a specific error
        """
        with self.lock:
            if error_id < len(self.error_store["errors"]):
                error = self.error_store["errors"][error_id]
                
                # Calculate success rate
                error_id_str = str(error_id)
                success_rate = 0
                if error_id_str in self.error_store["success_rate"]:
                    stats = self.error_store["success_rate"][error_id_str]
                    if stats["attempts"] > 0:
                        success_rate = stats["successes"] / stats["attempts"]
                
                return {
                    "id": error["id"],
                    "signature": error["signature"],
                    "occurrences": error["occurrences"],
                    "first_seen": error["first_seen"],
                    "last_seen": error["last_seen"],
                    "success_rate": success_rate,
                    "code_contexts": error["code_contexts"]
                }
            
            return None
    
    def handle_query(self, query):
        """
        Process incoming requests to the agent
        """
        action = query.get("action")
        
        if action == "record_error":
            error_text = query.get("error_text")
            code_context = query.get("code_context")
            language = query.get("language", "python")
            
            if not error_text:
                return {"status": "error", "message": "No error text provided"}
            
            error_id = self.record_error(error_text, code_context, language)
            return {"status": "ok", "error_id": error_id}
        
        elif action == "record_fix":
            error_id = query.get("error_id")
            fix_code = query.get("fix_code")
            successful = query.get("successful", True)
            
            if error_id is None or fix_code is None:
                return {"status": "error", "message": "Missing error_id or fix_code"}
            
            success = self.record_fix(error_id, fix_code, successful)
            return {"status": "ok" if success else "error"}
        
        elif action == "find_similar_errors":
            error_text = query.get("error_text")
            max_results = query.get("max_results", 3)
            
            if not error_text:
                return {"status": "error", "message": "No error text provided"}
            
            similar_errors = self.find_similar_errors(error_text, max_results)
            return {"status": "ok", "similar_errors": similar_errors}
        
        elif action == "get_best_fix":
            error_id = query.get("error_id")
            
            if error_id is None:
                return {"status": "error", "message": "No error_id provided"}
            
            best_fix = self.get_best_fix(error_id)
            if best_fix:
                return {"status": "ok", "fix_code": best_fix}
            else:
                return {"status": "error", "message": "No fixes found for this error"}
        
        elif action == "get_all_fixes":
            error_id = query.get("error_id")
            ranked = query.get("ranked", True)
            
            if error_id is None:
                return {"status": "error", "message": "No error_id provided"}
            
            fixes = self.get_all_fixes(error_id, ranked)
            return {"status": "ok", "fixes": fixes}
        
        elif action == "get_error_details":
            error_id = query.get("error_id")
            
            if error_id is None:
                return {"status": "error", "message": "No error_id provided"}
            
            details = self.get_error_details(error_id)
            if details:
                return {"status": "ok", "error_details": details}
            else:
                return {"status": "error", "message": "Error not found"}
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def run(self):
        """
        Main agent loop
        """
        while self.running:
            try:
                # Wait for next request from client
                message = self.socket.recv_string()
                logging.info(f"[ErrorPatternMemory] Received request")
                
                # Parse the request
                query = json.loads(message)
                
                # Process the request
                response = self.handle_query(query)
                
                # Send reply back to client
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logging.error(f"[ErrorPatternMemory] Error: {str(e)}")
                # Try to send error response if possible
                try:
                    self.socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
    
    def stop(self):
        """
        Stop the agent
        """
        self.running = False
        logging.info(f"[ErrorPatternMemory] Agent stopping")

# Helper function to send requests to the agent
def send_error_pattern_request(request, port=ZMQ_ERROR_PATTERN_PORT):
    """
    Send a request to the Error Pattern Memory Agent
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.connect(f"tcp://127.0.0.1:{port}")
    
    socket.send_string(json.dumps(request))
    response = socket.recv_string()
    
    socket.close()
    context.term()
    
    return json.loads(response)

# Helper functions for other agents to use
def record_error(error_text, code_context=None, language="python"):
    """
    Record an error occurrence
    Returns the error_id for later reference
    """
    request = {
        "action": "record_error",
        "error_text": error_text,
        "code_context": code_context,
        "language": language
    }
    response = send_error_pattern_request(request)
    return response.get("error_id") if response.get("status") == "ok" else None

def record_fix(error_id, fix_code, successful=True):
    """
    Record a fix for an error and whether it worked
    """
    request = {
        "action": "record_fix",
        "error_id": error_id,
        "fix_code": fix_code,
        "successful": successful
    }
    response = send_error_pattern_request(request)
    return response.get("status") == "ok"

def find_similar_errors(error_text, max_results=3):
    """
    Find errors similar to the given error text
    Returns a list of error_ids
    """
    request = {
        "action": "find_similar_errors",
        "error_text": error_text,
        "max_results": max_results
    }
    response = send_error_pattern_request(request)
    return response.get("similar_errors", []) if response.get("status") == "ok" else []

def get_best_fix(error_id):
    """
    Get the most successful fix for an error
    """
    request = {
        "action": "get_best_fix",
        "error_id": error_id
    }
    response = send_error_pattern_request(request)
    return response.get("fix_code") if response.get("status") == "ok" else None

def get_all_fixes(error_id, ranked=True):
    """
    Get all recorded fixes for an error
    """
    request = {
        "action": "get_all_fixes",
        "error_id": error_id,
        "ranked": ranked
    }
    response = send_error_pattern_request(request)
    return response.get("fixes", []) if response.get("status") == "ok" else []

def main():
    """
    Run the Error Pattern Memory Agent
    """
    agent = ErrorPatternMemory()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        logging.error(f"[ErrorPatternMemory] Fatal error: {str(e)}")
    finally:
        agent.stop()

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise