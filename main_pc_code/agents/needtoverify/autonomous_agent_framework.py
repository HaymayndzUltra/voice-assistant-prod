from common.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Autonomous Agent Framework
--------------------------
A sophisticated AI agent framework with goal-oriented reasoning, tool selection,
and iterative improvement capabilities.

Core Components:
1. Goal Interpreter/Reasoning Engine - Converts objectives into executable plans
2. Modular Toolbox - Provides various tools with autonomous selection logic
3. Reflexive Loop - Implements failure detection with automatic plan revision
4. Experience Memory - Persistent storage of successful strategies

This framework is designed to integrate with the existing voice assistant system
while providing advanced autonomous capabilities.
"""

import zmq
import json
import time
import logging
import sys
import os
import traceback
import threading
import hashlib
import pickle
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from datetime import datetime
import importlib
import inspect
import re
import zlib
import base64
from main_pc_code.agents.utils.data_optimizer import DataOptimizer


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", "..")))
from common.utils.path_manager import PathManager
# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.pc2_connections import get_connection_string

# Setup logging
LOG_PATH = PathManager.join_path("logs", "autonomous_agent_framework.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutonomousAgentFramework")

# ZMQ port for this agent
AUTONOMOUS_AGENT_FRAMEWORK_PORT = 5625
MODEL_MANAGER_PORT = 5556
MEMORY_AGENT_PORT = 5596

# Path for experience memory storage
EXPERIENCE_DB_PATH = PathManager.join_path("data", "experience_memory.pkl")
os.makedirs(os.path.dirname(EXPERIENCE_DB_PATH), exist_ok=True)

# Initialize DataOptimizer
optimizer = DataOptimizer()

class Tool(BaseAgent):
    """Base class for(BaseAgent) tools that can be used by the agent"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        self.name = name
        self.description = description
        self.required_params = required_params
        self.optional_params = optional_params or []
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided parameters"""
        raise NotImplementedError("Tool subclasses must implement execute method")
    
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate that all required parameters are present"""
        for param in self.required_params:
            if param not in params:
                return False, f"Missing required parameter: {param}"
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "required_params": self.required_params,
            "optional_params": self.optional_params
        }

class WebSearchTool(BaseAgent)(Tool):
    """Tool for searching the web"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        super().__init__(
            name="web_search",
            description="Search the web for information",
            required_params=["query"],
            optional_params=["num_results", "search_type"]
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a web search"""
        query = params["query"]
        num_results = params.get("num_results", 5)
        
        try:
            # Simple search implementation
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            results = []
            for result_div in soup.select('div.g')[:num_results]:
                title_elem = result_div.select_one('h3')
                link_elem = result_div.select_one('a')
                snippet_elem = result_div.select_one('div.VwiC3b')
                
                if title_elem and link_elem and 'href' in link_elem.attrs:
                    title = title_elem.get_text(strip=True)
                    link = link_elem['href']
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    if link.startswith('/url?q='):
                        link = link.split('/url?q=')[1].split('&')[0]
                    
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": snippet
                    })
            
            return {
                "status": "success",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in web search: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

class APIRequestTool(BaseAgent)(Tool):
    """Tool for making API requests"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        super().__init__(
            name="api_request",
            description="Make requests to external APIs",
            required_params=["url", "method"],
            optional_params=["headers", "params", "data", "json", "timeout"]
        )
        self.session = requests.Session()
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API request"""
        url = params["url"]
        method = params["method"].lower()
        headers = params.get("headers", {})
        request_params = params.get("params", {})
        data = params.get("data")
        json_data = params.get("json")
        timeout = params.get("timeout", 30)
        
        try:
            if method not in ["get", "post", "put", "delete", "patch"]:
                return {
                    "status": "error",
                    "error": f"Unsupported HTTP method: {method}"
                }
            
            request_method = getattr(self.session, method)
            response = request_method(
                url,
                headers=headers,
                params=request_params,
                data=data,
                json=json_data,
                timeout=timeout
            )
            
            # Try to parse as JSON
            try:
                json_response = response.json()
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "json": json_response
                }
            except:
                # Return text response if not JSON
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "text": response.text
                }
                
        except Exception as e:
            logger.error(f"Error in API request: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

class DataExtractionTool(BaseAgent)(Tool):
    """Tool for extracting structured data from text or HTML"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        super().__init__(
            name="data_extraction",
            description="Extract structured data from text or HTML",
            required_params=["source", "extraction_type"],
            optional_params=["selectors", "regex_patterns", "format"]
        )
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data extraction"""
        source = params["source"]
        extraction_type = params["extraction_type"]
        
        try:
            if extraction_type == "html":
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(source, 'html.parser')
                
                selectors = params.get("selectors", {})
                result = {}
                
                for key, selector in selectors.items():
                    elements = soup.select(selector)
                    if elements:
                        if len(elements) == 1:
                            result[key] = elements[0].get_text(strip=True)
                        else:
                            result[key] = [elem.get_text(strip=True) for elem in elements]
                
                return {
                    "status": "success",
                    "data": result
                }
                
            elif extraction_type == "regex":
                import re
                patterns = params.get("regex_patterns", {})
                result = {}
                
                for key, pattern in patterns.items():
                    matches = re.findall(pattern, source)
                    if matches:
                        if len(matches) == 1:
                            result[key] = matches[0]
                        else:
                            result[key] = matches
                
                return {
                    "status": "success",
                    "data": result
                }
                
            elif extraction_type == "table":
                # Simple table extraction from HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(source, 'html.parser')
                
                tables = []
                for table in soup.find_all('table'):
                    rows = []
                    for tr in table.find_all('tr'):
                        row = []
                        for td in tr.find_all(['td', 'th']):
                            row.append(td.get_text(strip=True))
                        if row:
                            rows.append(row)
                    if rows:
                        tables.append(rows)
                
                return {
                    "status": "success",
                    "tables": tables
                }
                
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported extraction type: {extraction_type}"
                }
                
        except Exception as e:
            logger.error(f"Error in data extraction: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

class FileOperationTool(BaseAgent)(Tool):
    """Tool for file operations"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        super().__init__(
            name="file_operation",
            description="Perform operations on files",
            required_params=["operation", "path"],
            optional_params=["content", "mode", "encoding"]
        )
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operation"""
        operation = params["operation"]
        path = params["path"]
        
        try:
            if operation == "read":
                mode = params.get("mode", "r")
                encoding = params.get("encoding", "utf-8")
                
                with open(path, mode, encoding=encoding) as f:
                    content = f.read()
                
                return {
                    "status": "success",
                    "content": content
                }
                
            elif operation == "write":
                if "content" not in params:
                    return {
                        "status": "error",
                        "error": "Missing required parameter for write operation: content"
                    }
                
                content = params["content"]
                mode = params.get("mode", "w")
                encoding = params.get("encoding", "utf-8")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                
                with open(path, mode, encoding=encoding) as f:
                    f.write(content)
                
                return {
                    "status": "success",
                    "path": path,
                    "bytes_written": len(content)
                }
                
            elif operation == "append":
                if "content" not in params:
                    return {
                        "status": "error",
                        "error": "Missing required parameter for append operation: content"
                    }
                
                content = params["content"]
                encoding = params.get("encoding", "utf-8")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                
                with open(path, "a", encoding=encoding) as f:
                    f.write(content)
                
                return {
                    "status": "success",
                    "path": path,
                    "bytes_appended": len(content)
                }
                
            elif operation == "delete":
                if os.path.exists(path):
                    if os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    
                    return {
                        "status": "success",
                        "path": path,
                        "deleted": True
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Path does not exist: {path}"
                    }
                    
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported file operation: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error in file operation: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

class Goal(BaseAgent):
    """Represents a goal to be achieved by the agent"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        self.id = hashlib.md5(f"{description}-{time.time()}".encode()).hexdigest()
        self.description = description
        self.criteria = criteria or []
        self.priority = priority
        self.status = "pending"  # pending, in_progress, completed, failed
        self.created_at = datetime.now().isoformat()
        self.completed_at = None
        self.result = None
        self.steps = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary representation"""
        return {
            "id": self.id,
            "description": self.description,
            "criteria": self.criteria,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "steps": self.steps
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Goal':
        """Create a goal from dictionary representation"""
        goal = cls(
            description=data["description"],
            criteria=data["criteria"],
            priority=data["priority"]
        )
        goal.id = data["id"]
        goal.status = data["status"]
        goal.created_at = data["created_at"]
        goal.completed_at = data["completed_at"]
        goal.result = data["result"]
        goal.steps = data["steps"]
        return goal
    
    def add_step(self, step: Dict[str, Any]) -> None:
        """Add a step to the goal"""
        self.steps.append(step)
    
    def update_status(self, status: str, result: Any = None) -> None:
        """Update the status of the goal"""
        self.status = status
        if status in ["completed", "failed"]:
            self.completed_at = datetime.now().isoformat()
        if result is not None:
            self.result = result

class Plan(BaseAgent):
    """Represents a plan to achieve a goal"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        self.id = hashlib.md5(f"{goal.id}-{time.time()}".encode()).hexdigest()
        self.goal = goal
        self.steps = steps or []
        self.current_step = 0
        self.status = "pending"  # pending, in_progress, completed, failed
        self.created_at = datetime.now().isoformat()
        self.completed_at = None
        self.result = None
        self.revisions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary representation"""
        return {
            "id": self.id,
            "goal": self.goal.to_dict(),
            "steps": self.steps,
            "current_step": self.current_step,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "revisions": self.revisions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """Create a plan from dictionary representation"""
        goal = Goal.from_dict(data["goal"])
        plan = cls(goal=goal, steps=data["steps"])
        plan.id = data["id"]
        plan.current_step = data["current_step"]
        plan.status = data["status"]
        plan.created_at = data["created_at"]
        plan.completed_at = data["completed_at"]
        plan.result = data["result"]
        plan.revisions = data["revisions"]
        return plan
    
    def add_step(self, step: Dict[str, Any]) -> None:
        """Add a step to the plan"""
        self.steps.append(step)
    
    def update_status(self, status: str, result: Any = None) -> None:
        """Update the status of the plan"""
        self.status = status
        if status in ["completed", "failed"]:
            self.completed_at = datetime.now().isoformat()
        if result is not None:
            self.result = result
    
    def revise(self, reason: str, new_steps: List[Dict[str, Any]]) -> None:
        """Revise the plan with new steps"""
        revision = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "old_steps": self.steps.copy(),
            "current_step": self.current_step
        }
        self.revisions.append(revision)
        self.steps = new_steps
        self.current_step = 0
    
    def next_step(self) -> Optional[Dict[str, Any]]:
        """Get the next step in the plan"""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.current_step += 1
            return step
        return None
    
    def get_current_step(self) -> Optional[Dict[str, Any]]:
        """Get the current step without advancing"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def get_remaining_steps(self) -> List[Dict[str, Any]]:
        """Get all remaining steps"""
        return self.steps[self.current_step:]
    
    def get_completed_steps(self) -> List[Dict[str, Any]]:
        """Get all completed steps"""
        return self.steps[:self.current_step]

class ExperienceMemory(BaseAgent):
    """Persistent storage for agent experiences and strategies"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousAgentFramework")
        self.db_path = db_path
        self.experiences = self._load_experiences()
    
    def _load_experiences(self) -> Dict[str, Any]:
        """Load experiences from disk"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading experiences: {str(e)}")
                return {
                    "goals": {},
                    "plans": {},
                    "strategies": {},
                    "failures": {},
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat()
                    }
                }
        else:
            return {
                "goals": {},
                "plans": {},
                "strategies": {},
                "failures": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
    
    def _save_experiences(self) -> None:
        """Save experiences to disk"""
        self.experiences["metadata"]["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.db_path, 'wb') as f:
                pickle.dump(self.experiences, f)
        except Exception as e:
            logger.error(f"Error saving experiences: {str(e)}")
    
    def add_goal(self, goal: Goal) -> None:
        """Add a goal to memory"""
        self.experiences["goals"][goal.id] = goal.to_dict()
        self._save_experiences()
    
    def add_plan(self, plan: Plan) -> None:
        """Add a plan to memory"""
        self.experiences["plans"][plan.id] = plan.to_dict()
        self._save_experiences()
    
    def add_strategy(self, name: str, description: str, steps: List[Dict[str, Any]], success_rate: float = 0.0) -> str:
        """Add a strategy to memory"""
        strategy_id = hashlib.md5(f"{name}-{time.time()}".encode()).hexdigest()
        self.experiences["strategies"][strategy_id] = {
            "id": strategy_id,
            "name": name,
            "description": description,
            "steps": steps,
            "success_rate": success_rate,
            "usage_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_used": None
        }
        self._save_experiences()
        return strategy_id
    
    def add_failure(self, goal_id: str, plan_id: str, step: Dict[str, Any], error: str, context: Dict[str, Any]) -> str:
        """Add a failure to memory"""
        failure_id = hashlib.md5(f"{goal_id}-{plan_id}-{time.time()}".encode()).hexdigest()
        self.experiences["failures"][failure_id] = {
            "id": failure_id,
            "goal_id": goal_id,
            "plan_id": plan_id,
            "step": step,
            "error": error,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
            "resolution": None
        }
        self._save_experiences()
        return failure_id
    
    def update_goal(self, goal: Goal) -> None:
        """Update a goal in memory"""
        if goal.id in self.experiences["goals"]:
            self.experiences["goals"][goal.id] = goal.to_dict()
            self._save_experiences()
    
    def update_plan(self, plan: Plan) -> None:
        """Update a plan in memory"""
        if plan.id in self.experiences["plans"]:
            self.experiences["plans"][plan.id] = plan.to_dict()
            self._save_experiences()
    
    def update_strategy_success_rate(self, strategy_id: str, success: bool) -> None:
        """Update the success rate of a strategy"""
        if strategy_id in self.experiences["strategies"]:
            strategy = self.experiences["strategies"][strategy_id]
            usage_count = strategy["usage_count"] + 1
            old_success_rate = strategy["success_rate"]
            
            # Update success rate with weighted average
            if success:
                new_success_rate = (old_success_rate * (usage_count - 1) + 1) / usage_count
            else:
                new_success_rate = (old_success_rate * (usage_count - 1)) / usage_count
            
            strategy["success_rate"] = new_success_rate
            strategy["usage_count"] = usage_count
            strategy["last_used"] = datetime.now().isoformat()
            
            self._save_experiences()
    
    def mark_failure_resolved(self, failure_id: str, resolution: str) -> None:
        """Mark a failure as resolved"""
        if failure_id in self.experiences["failures"]:
            self.experiences["failures"][failure_id]["resolved"] = True
            self.experiences["failures"][failure_id]["resolution"] = resolution
            self._save_experiences()
    
    def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a goal by ID"""
        return self.experiences["goals"].get(goal_id)
    
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a plan by ID"""
        return self.experiences["plans"].get(plan_id)
    
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get a strategy by ID"""
        return self.experiences["strategies"].get(strategy_id)
    
    def get_failure(self, failure_id: str) -> Optional[Dict[str, Any]]:
        """Get a failure by ID"""
        return self.experiences["failures"].get(failure_id)
    
    def get_strategies_for_goal(self, goal_description: str) -> List[Dict[str, Any]]:
        """Find strategies that might be applicable to a goal"""
        # Simple keyword matching for now
        keywords = set(re.findall(r'\w+', goal_description.lower()))
        
        matching_strategies = []
        for strategy_id, strategy in self.experiences["strategies"].items():
            strategy_keywords = set(re.findall(r'\w+', strategy["description"].lower()))
            strategy_name_keywords = set(re.findall(r'\w+', strategy["name"].lower()))
            
            # Calculate overlap
            description_overlap = len(keywords.intersection(strategy_keywords)) / max(1, len(keywords))
            name_overlap = len(keywords.intersection(strategy_name_keywords)) / max(1, len(keywords))
            
            # If significant overlap or high success rate, include the strategy
            if description_overlap > 0.3 or name_overlap > 0.5 or strategy["success_rate"] > 0.7:
                matching_strategies.append(strategy)
        
        # Sort by success rate
        matching_strategies.sort(key=lambda s: s["success_rate"], reverse=True)
        return matching_strategies
    
    def get_similar_failures(self, error: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar failures"""
        error_keywords = set(re.findall(r'\w+', error.lower()))
        
        similar_failures = []
        for failure_id, failure in self.experiences["failures"].items():
            failure_error_keywords = set(re.findall(r'\w+', failure["error"].lower()))
            
            # Calculate overlap
            error_overlap = len(error_keywords.intersection(failure_error_keywords)) / max(1, len(error_keywords))
            
            # If significant overlap and resolved, include the failure
            if error_overlap > 0.3 and failure["resolved"]:
                similar_failures.append(failure)
        
        return similar_failures

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise

# Example: When sending a message via ZMQ, optimize the payload first
# Replace all occurrences of socket.send_json or socket.send with optimized payload
# Example function to send optimized message:
def send_optimized_zmq(socket, data, method='compressed_msgpack'):
    optimized = optimizer.optimize_payload(data, method)
    socket.send_json(optimized)

# Replace direct socket.send_json(data) calls with send_optimized_zmq(socket, data)
