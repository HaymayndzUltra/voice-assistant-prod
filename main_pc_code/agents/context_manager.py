#!/usr/bin/env python3
"""
Context Manager Agent

Manages context across different interactions and sessions.
Provides context retrieval and management services for other agents.
Uses the central memory system via MemoryClient.
"""

import sys
import os
import json
import zmq
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project's main_pc_code directory to the Python path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

from common.core.base_agent import BaseAgent
from main_pc_code.agents.memory_client import MemoryClient
from main_pc_code.utils.config_loader import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "context_manager.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContextManager")

class ContextManager(BaseAgent):
    """
    Context Manager Agent: Manages context across different interactions and sessions.
    Provides context retrieval and management services for other agents.
    Uses the central memory system via MemoryClient.
    Also reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    
    def __init__(self, port: int = 5716, health_port: int = 6716):
        """Initialize the context manager agent."""
        super().__init__(name="ContextManager", port=port, health_check_port=health_port)
        
        # Initialize memory client
        self.memory_client = MemoryClient()
        self.memory_client.set_agent_id(self.name)
        
        # Error bus configuration
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Cache for frequently accessed contexts
        self.context_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_last_cleanup = time.time()
        
        logger.info("ContextManager initialized successfully")
        
    def _report_error(self, error_type: str, error_message: str, severity: str = "ERROR"):
        """Report errors to the central error bus"""
        try:
            error_data = {
                "timestamp": time.time(),
                "agent": self.name,
                "error_type": error_type,
                "message": error_message,
                "severity": severity
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
        
        try:
            if action == "get_context":
                return self._get_context(request)
            elif action == "update_context":
                return self._update_context(request)
            elif action == "merge_contexts":
                return self._merge_contexts(request)
            elif action == "get_recent_interactions":
                return self._get_recent_interactions(request)
            elif action == "search_context":
                return self._search_context(request)
            elif action == "health_check":
                return {"status": "success", "agent": self.name, "healthy": True}
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self._report_error("request_processing_error", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _get_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get context for a specific session or interaction
        
        Args:
            request: Dict containing 'session_id' or 'context_id' and optional parameters
            
        Returns:
            Dict with status and context data
        """
        session_id = request.get("session_id")
        context_id = request.get("context_id")
        limit = request.get("limit", 20)
        include_metadata = request.get("include_metadata", False)
        
        if not (session_id or context_id):
            return {"status": "error", "message": "Missing session_id or context_id"}
        
        try:
            # Check cache first
            cache_key = f"context_{session_id or context_id}_{limit}"
            if cache_key in self.context_cache:
                cache_entry = self.context_cache[cache_key]
                if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                    logger.info(f"Context cache hit for {cache_key}")
                    return cache_entry["data"]
            
            # Get context from memory system
            if session_id:
                response = self.memory_client.get_children(
                    parent_id=session_id,
                    limit=limit,
                    sort_field="created_at",
                    sort_order="asc"  # Chronological order
                )
            else:
                # Get memory and its related memories
                response = self.memory_client.get_memory(memory_id=context_id)
                if response.get("status") == "success":
                    related_response = self.memory_client.get_related_memories(memory_id=context_id)
                    if related_response.get("status") == "success":
                        response["related_memories"] = related_response.get("results", [])
            
            if response.get("status") == "success":
                # Format context data
                context_data = self._format_context_data(response, include_metadata)
                
                # Cache the result
                self.context_cache[cache_key] = {
                    "timestamp": time.time(),
                    "data": context_data
                }
                
                # Cleanup cache if needed
                self._cleanup_cache()
                
                return context_data
            else:
                error_msg = response.get("message", "Failed to get context")
                self._report_error("get_context_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception getting context: {str(e)}"
            self._report_error("get_context_exception", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _update_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update context with new information
        
        Args:
            request: Dict containing context update information
            
        Returns:
            Dict with status and updated context
        """
        context_id = request.get("context_id")
        content = request.get("content")
        metadata = request.get("metadata", {})
        importance = request.get("importance")
        
        if not context_id or not content:
            return {"status": "error", "message": "Missing required parameters"}
        
        try:
            # Prepare update payload
            update_payload = {"content": content}
            if metadata:
                update_payload["metadata"] = metadata
            if importance is not None:
                update_payload["importance"] = importance
            
            # Update memory
            response = self.memory_client.update_memory(
                memory_id=context_id,
                update_payload=update_payload
            )
            
            if response.get("status") == "success":
                # Invalidate cache for this context
                for key in list(self.context_cache.keys()):
                    if context_id in key:
                        del self.context_cache[key]
                
                return {"status": "success", "message": "Context updated successfully"}
            else:
                error_msg = response.get("message", "Failed to update context")
                self._report_error("update_context_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception updating context: {str(e)}"
            self._report_error("update_context_exception", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _merge_contexts(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple contexts into a single context
        
        Args:
            request: Dict containing 'context_ids' and optional 'name'
            
        Returns:
            Dict with status and merged context ID
        """
        context_ids = request.get("context_ids", [])
        name = request.get("name", f"Merged context {datetime.now().isoformat()}")
        description = request.get("description", "Automatically merged context")
        
        if not context_ids or len(context_ids) < 2:
            return {"status": "error", "message": "Need at least two context IDs to merge"}
        
        try:
            # Create a new context group
            group_response = self.memory_client.create_context_group(
                name=name,
                description=description
            )
            
            if group_response.get("status") != "success":
                error_msg = group_response.get("message", "Failed to create context group")
                self._report_error("merge_contexts_error", error_msg)
                return {"status": "error", "message": error_msg}
            
            group_id = group_response.get("group_id")
            
            # Add contexts to group
            for context_id in context_ids:
                self.memory_client.add_to_group(
                    memory_id=context_id,
                    group_id=group_id
                )
            
            return {
                "status": "success",
                "message": f"Successfully merged {len(context_ids)} contexts",
                "group_id": group_id
            }
                
        except Exception as e:
            error_msg = f"Exception merging contexts: {str(e)}"
            self._report_error("merge_contexts_exception", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _get_recent_interactions(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recent interactions across all sessions
        
        Args:
            request: Dict containing optional 'limit', 'time_window', and 'user_id'
            
        Returns:
            Dict with status and recent interactions
        """
        limit = request.get("limit", 50)
        time_window = request.get("time_window", 24)  # hours
        user_id = request.get("user_id")
        
        try:
            # Search for recent interactions
            query = f"type:interaction created_at:>{(datetime.now() - timedelta(hours=time_window)).isoformat()}"
            
            if user_id:
                query += f" user_id:{user_id}"
            
            response = self.memory_client.search_memory(
                query=query,
                memory_type="interaction",
                limit=limit
            )
            
            if response.get("status") == "success":
                interactions = response.get("results", [])
                return {"status": "success", "interactions": interactions}
            else:
                error_msg = response.get("message", "Failed to get recent interactions")
                self._report_error("get_recent_interactions_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception getting recent interactions: {str(e)}"
            self._report_error("get_recent_interactions_exception", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _search_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for context based on query
        
        Args:
            request: Dict containing 'query' and optional parameters
            
        Returns:
            Dict with status and search results
        """
        query = request.get("query")
        session_id = request.get("session_id")
        limit = request.get("limit", 10)
        use_semantic = request.get("use_semantic", True)
        
        if not query:
            return {"status": "error", "message": "Missing query"}
        
        try:
            if use_semantic:
                # Try semantic search
                filters = {}
                if session_id:
                    filters["parent_id"] = session_id
                
                response = self.memory_client.semantic_search(
                    query=query,
                    filters=filters,
                    k=limit
                )
                
                if response.get("status") == "success" and response.get("results"):
                    return {"status": "success", "results": response.get("results", [])}
            
            # Fall back to text search
            search_params = {
                "query": query,
                "limit": limit
            }
            
            if session_id:
                search_params["parent_id"] = session_id
                
            response = self.memory_client.search_memory(**search_params)
            
            if response.get("status") == "success":
                return {"status": "success", "results": response.get("results", [])}
            else:
                error_msg = response.get("message", "Search failed")
                self._report_error("search_context_error", error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Exception searching context: {str(e)}"
            self._report_error("search_context_exception", error_msg)
            return {"status": "error", "message": error_msg}
    
    def _format_context_data(self, response: Dict[str, Any], include_metadata: bool) -> Dict[str, Any]:
        """Format context data for return"""
        if "results" in response:
            interactions = response.get("results", [])
            
            # Format interactions for context
            context_items = []
            for interaction in interactions:
                item = {
                    "memory_id": interaction.get("memory_id"),
                    "content": interaction.get("content", "")
                }
                
                if include_metadata:
                    item["metadata"] = interaction.get("metadata", {})
                    
                context_items.append(item)
            
            return {"status": "success", "context": context_items}
        else:
            memory = response.get("memory", {})
            related = response.get("related_memories", [])
            
            result = {
                "status": "success",
                "memory": {
                    "memory_id": memory.get("memory_id"),
                    "content": memory.get("content", "")
                },
                "related_memories": []
            }
            
            if include_metadata:
                result["memory"]["metadata"] = memory.get("metadata", {})
                
            for rel_memory in related:
                rel_item = {
                    "memory_id": rel_memory.get("memory_id"),
                    "content": rel_memory.get("content", ""),
                    "relationship_type": rel_memory.get("relationship_type", "")
                }
                
                if include_metadata:
                    rel_item["metadata"] = rel_memory.get("metadata", {})
                    
                result["related_memories"].append(rel_item)
                
            return result
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        
        # Only run cleanup every minute
        if current_time - self.cache_last_cleanup < 60:
            return
            
        expired_keys = []
        for key, entry in self.context_cache.items():
            if current_time - entry["timestamp"] > self.cache_ttl:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.context_cache[key]
            
        self.cache_last_cleanup = current_time
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
            self.error_bus_pub.close()
        super().cleanup()

# Example usage
if __name__ == "__main__":
    try:
        agent = ContextManager()
        agent.run()
    except KeyboardInterrupt:
        logger.info("ContextManager shutting down")
    except Exception as e:
        logger.critical(f"ContextManager failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and hasattr(agent, 'cleanup'):
            agent.cleanup() 