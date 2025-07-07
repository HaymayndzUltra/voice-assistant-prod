#!/usr/bin/env python3
"""
Knowledge Base Agent

Manages and provides access to the system's knowledge base.
Stores and retrieves factual information using the central memory system.
"""

# Add the project's main_pc_code directory to the Python path
import sys
import json
import os
import zmq
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

from common.core.base_agent import BaseAgent
from main_pc_code.agents.memory_client import MemoryClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/knowledge_base.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KnowledgeBase")

class KnowledgeBase(BaseAgent):
    """
    KnowledgeBase: Manages factual knowledge using the central memory system.
    Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, port: int = 5715, health_port: int = 6715):
        super().__init__(name="KnowledgeBase", port=port, health_check_port=health_port)
        
        # Initialize MemoryClient
        self.memory_client = MemoryClient()
        
        # Error bus configuration
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        logger.info("KnowledgeBase initialized successfully")
        
    def _report_error(self, error_type: str, error_message: str):
        """Report errors to the central error bus"""
        try:
            error_data = {
                "timestamp": time.time(),
                "agent": self.name,
                "error_type": error_type,
                "message": error_message,
                "severity": "ERROR"
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"{error_type}: {error_message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests based on action type"""
        if not isinstance(request, dict):
            return {"status": "error", "message": "Invalid request format"}
            
        action = request.get("action")
        
        if action == "add_fact":
            return self.add_fact(request)
        elif action == "get_fact":
            return self.get_fact(request)
        elif action == "update_fact":
            return self.update_fact(request)
        elif action == "search_facts":
            return self.search_facts(request)
        elif action == "health_check":
            return {"status": "success", "agent": self.name, "healthy": True}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def add_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new fact to the knowledge base
        
        Args:
            request: Dict containing 'topic' and 'content'
            
        Returns:
            Dict with status and result
        """
        topic = request.get("topic")
        content = request.get("content")
        
        if not topic or not content:
            return {"status": "error", "message": "Missing topic or content"}
            
        try:
            # Add metadata and tags for better organization
            metadata = {"topic": topic}
            tags = [topic.lower()]
            
            response = self.memory_client.add_memory(
                content=content,
                memory_type="knowledge_fact",
                memory_tier="long",  # Knowledge facts should be long-term
                importance=0.8,      # Higher importance for facts
                metadata=metadata,
                tags=tags
            )
            
            if response.get("status") == "success":
                return {"status": "success", "message": "Fact added successfully", "memory_id": response.get("memory_id")}
            else:
                error_msg = response.get("message", "Unknown error")
                self._report_error("add_fact_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            self._report_error("add_fact_exception", str(e))
            return {"status": "error", "message": f"Exception while adding fact: {str(e)}"}

    def get_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve a fact by topic
        
        Args:
            request: Dict containing 'topic'
            
        Returns:
            Dict with status and fact if found
        """
        topic = request.get("topic")
        
        if not topic:
            return {"status": "error", "message": "Missing topic"}
            
        try:
            # First try semantic search if available
            try:
                response = self.memory_client.semantic_search(
                    query=topic, 
                    k=1
                )
                
                if response.get("status") == "success" and response.get("results"):
                    results = response.get("results", [])
                    if results:
                        return {"status": "success", "fact": results[0]}
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to text search: {e}")
            
            # Fall back to text search
            if topic is not None:
                response = self.memory_client.search_memory(
                    query=str(topic), 
                    memory_type="knowledge_fact", 
                    limit=1
                )
            else:
                return {"status": "error", "message": "Invalid topic"}
            
            if response.get("status") == "success":
                results = response.get("results", [])
                
                if results:
                    return {"status": "success", "fact": results[0]}
                else:
                    return {"status": "error", "message": "Fact not found"}
            else:
                error_msg = response.get("message", "Search failed")
                self._report_error("get_fact_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            self._report_error("get_fact_exception", str(e))
            return {"status": "error", "message": f"Exception while retrieving fact: {str(e)}"}

    def update_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing fact
        
        Args:
            request: Dict containing 'topic' and 'content'
            
        Returns:
            Dict with status and result
        """
        topic = request.get("topic")
        new_content = request.get("content")
        memory_id = request.get("memory_id")
        
        if not ((topic or memory_id) and new_content):
            return {"status": "error", "message": "Missing required parameters"}
            
        try:
            # If memory_id is provided, update directly
            if memory_id:
                update_resp = self.memory_client.update_memory(
                    memory_id=memory_id, 
                    update_payload={"content": new_content}
                )
                
                if update_resp.get("status") == "success":
                    return {"status": "success", "message": "Fact updated successfully"}
                else:
                    error_msg = update_resp.get("message", "Update failed")
                    self._report_error("update_fact_error", error_msg)
                    return {"status": "error", "message": error_msg}
            
            # Otherwise, search by topic first
            search_resp = self.memory_client.search_memory(
                query=topic, 
                memory_type="knowledge_fact", 
                limit=1
            )
            
            if search_resp.get("status") == "success":
                results = search_resp.get("results", [])
                
                if results:
                    memory_id = results[0].get("memory_id")
                    if memory_id:
                        update_resp = self.memory_client.update_memory(
                            memory_id=memory_id, 
                            update_payload={"content": new_content}
                        )
                        
                        if update_resp.get("status") == "success":
                            return {"status": "success", "message": "Fact updated successfully"}
                        else:
                            error_msg = update_resp.get("message", "Update failed")
                            self._report_error("update_fact_error", error_msg)
                            return {"status": "error", "message": error_msg}
                    else:
                        return {"status": "error", "message": "Malformed fact structure (missing memory_id)"}
                else:
                    return {"status": "error", "message": "Fact not found"}
            else:
                error_msg = search_resp.get("message", "Search failed")
                self._report_error("update_fact_search_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            self._report_error("update_fact_exception", str(e))
            return {"status": "error", "message": f"Exception while updating fact: {str(e)}"}

    def search_facts(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for facts matching a query
        
        Args:
            request: Dict containing 'query' and optional 'limit'
            
        Returns:
            Dict with status and search results
        """
        query = request.get("query", "")
        limit = request.get("limit", 10)
        
        try:
            # Try semantic search first if available
            try:
                response = self.memory_client.semantic_search(
                    query=query, 
                    k=limit
                )
                
                if response.get("status") == "success" and response.get("results"):
                    return {"status": "success", "results": response.get("results", [])}
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to text search: {e}")
            
            # Fall back to text search
            response = self.memory_client.search_memory(
                query=query, 
                memory_type="knowledge_fact", 
                limit=limit
            )
            
            if response.get("status") == "success":
                return {"status": "success", "results": response.get("results", [])}
            else:
                error_msg = response.get("message", "Search failed")
                self._report_error("search_facts_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            self._report_error("search_facts_exception", str(e))
            return {"status": "error", "message": f"Exception while searching facts: {str(e)}"}
            
    def cleanup(self):
        """Clean up resources before shutdown"""
        if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
            self.error_bus_pub.close()
        super().cleanup()

if __name__ == "__main__":
    import time
    try:
        agent = KnowledgeBase()
        agent.run()
    except KeyboardInterrupt:
        logger.info("KnowledgeBase shutting down")
    except Exception as e:
        logger.critical(f"KnowledgeBase failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and hasattr(agent, 'cleanup'):
            agent.cleanup() 