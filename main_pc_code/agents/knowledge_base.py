"""

# Add the project's main_pc_code directory to the Python path
import sys
import json
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Knowledge Base Agent implementation
Manages and provides access to the system's knowledge base
"""

import logging
from typing import Dict, Any
from common.core.base_agent import BaseAgent
from main_pc_code.agents.memory_client import MemoryClient

class KnowledgeBase(
    """
    KnowledgeBase:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """BaseAgent):
    def __init__(self, port: int = 5571, health_port: int = 5572):
        super().__init__(name="KnowledgeBase", port=port, health_check_port=health_port)
        self.memory_client = MemoryClient()
        self.logger = logging.getLogger(self.__class__.__name__)

    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get("action")
        if action == "add_fact":
            return self.add_fact(request)
        elif action == "get_fact":
            return self.get_fact(request)
        elif action == "update_fact":
            return self.update_fact(request)
        elif action == "search_facts":
            return self.search_facts(request)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def add_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        topic = request.get("topic")
        content = request.get("content")
        if not topic or not content:
            return {"status": "error", "message": "Missing topic or content"}
        response = self.memory_client.add_memory(
            content=content,
            memory_type="knowledge_fact",
            metadata={"topic": topic}
        )
        if isinstance(response, dict) and response.get("status") == "success":
            return {"status": "ok", "message": "Fact added successfully"}
        return {"status": "error", "message": response.get("message", "Unknown error") if isinstance(response, dict) else str(response)}

    def get_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        topic = request.get("topic")
        if not topic:
            return {"status": "error", "message": "Missing topic"}
        response = self.memory_client.search_memory(query=topic, memory_type="knowledge_fact", limit=1)
        if isinstance(response, dict) and response.get("status") == "success":
            data = response.get("data")
            if isinstance(data, dict):
                results = data.get("results", [])
                if isinstance(results, list) and results:
                    return {"status": "ok", "fact": results[0]}
                return {"status": "error", "message": "Fact not found"}
            return {"status": "error", "message": "Malformed response from MemoryClient"}
        return {"status": "error", "message": response.get("message", "Search failed") if isinstance(response, dict) else str(response)}

    def update_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        topic = request.get("topic")
        new_content = request.get("content")
        if not topic or not new_content:
            return {"status": "error", "message": "Missing topic or new content"}
        search_resp = self.memory_client.search_memory(query=topic, memory_type="knowledge_fact", limit=1)
        if isinstance(search_resp, dict) and search_resp.get("status") == "success":
            data = search_resp.get("data")
            if isinstance(data, dict):
                results = data.get("results", [])
                if isinstance(results, list) and results:
                    fact = results[0]
                    memory_id = fact.get("memory_id") if isinstance(fact, dict) else None
                    if memory_id:
                        update_resp = self.memory_client.update_memory(memory_id, {"content": new_content})
                        if isinstance(update_resp, dict) and update_resp.get("status") == "success":
                            return {"status": "ok", "message": "Fact updated"}
                        return {"status": "error", "message": update_resp.get("message", "Update failed") if isinstance(update_resp, dict) else str(update_resp)}
                    return {"status": "error", "message": "Malformed fact structure (missing memory_id)"}
                return {"status": "error", "message": "Fact not found"}
            return {"status": "error", "message": "Malformed response from MemoryClient"}
        return {"status": "error", "message": search_resp.get("message", "Search failed") if isinstance(search_resp, dict) else str(search_resp)}

    def search_facts(self, request: Dict[str, Any]) -> Dict[str, Any]:
        query = request.get("query", "")
        limit = request.get("limit", 10)
        response = self.memory_client.search_memory(query=query, memory_type="knowledge_fact", limit=limit)
        if isinstance(response, dict) and response.get("status") == "success":
            data = response.get("data", {})
            if isinstance(data, dict):
                results = data.get("results", [])
                if isinstance(results, list):
                    return {"status": "ok", "results": results}
                return {"status": "error", "message": "Malformed results from MemoryClient"}
            return {"status": "error", "message": "Malformed response from MemoryClient"}
        return {"status": "error", "message": response.get("message", "Search failed") if isinstance(response, dict) else str(response)}

if __name__ == "__main__":
    agent = KnowledgeBase()
    agent.run() 