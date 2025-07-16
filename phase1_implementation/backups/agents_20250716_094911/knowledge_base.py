#!/usr/bin/env python3
"""
Knowledge Base Agent

Manages and provides access to the system's knowledge base.
Stores and retrieves factual information using the central memory system.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import zmq

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.agents.memory_client import MemoryClient

# -----------------------------------------------------------------------------
# Configuration & Logging
# -----------------------------------------------------------------------------

MAIN_PC_CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'main_pc_code'))
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR)

config = load_config()

# Ports are loaded from configuration or environment variables (Rule 2)
DEFAULT_PORT = int(os.environ.get("KNOWLEDGE_BASE_PORT", config.get("knowledge_base", {}).get("port", 5715)))
DEFAULT_HEALTH_PORT = int(os.environ.get("KNOWLEDGE_BASE_HEALTH_PORT", config.get("knowledge_base", {}).get("health_port", 6715)))

# Error Bus settings (Rule 8)
ERROR_BUS_HOST = os.environ.get("ERROR_BUS_HOST", os.environ.get("PC2_IP", "localhost"))
ERROR_BUS_PORT = int(os.environ.get("ERROR_BUS_PORT", 7150))
ERROR_BUS_ENDPOINT = f"tcp://{ERROR_BUS_HOST}:{ERROR_BUS_PORT}"

# Logging (Rule 7)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("KnowledgeBase")

# -----------------------------------------------------------------------------
# Agent Definition
# -----------------------------------------------------------------------------

class KnowledgeBase(BaseAgent):
    """Knowledge base manager using the central memory system."""

    def __init__(self, port: int = DEFAULT_PORT, health_port: int = DEFAULT_HEALTH_PORT):
        super().__init__(name="KnowledgeBase", port=port, health_check_port=health_port)

        # Memory client (external service, no local state)
        self.memory_client = MemoryClient()

        # Error Bus (Rule 8)
        self.context = zmq.Context.instance()
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(ERROR_BUS_ENDPOINT)

        self.start_time = time.time()
        self.request_count = 0
        logger.info("KnowledgeBase initialized successfully")

    # ------------------------------------------------------------------
    # Internal Utilities
    # ------------------------------------------------------------------

    def _report_error(self, error_type: str, error_message: str):
        """Publish an error to the central Error Bus (Rule 8)."""
        try:
            error_data = {
                "timestamp": time.time(),
                "agent": self.name,
                "error_type": error_type,
                "message": error_message,
                "severity": "ERROR",
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"{error_type}: {error_message}")
        except Exception as exc:
            logger.error(f"Failed to report error to error bus: {exc}")

    # ------------------------------------------------------------------
    # Request Processing
    # ------------------------------------------------------------------

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route incoming request to the appropriate handler."""
        self.request_count += 1
        if not isinstance(request, dict):
            return {"status": "error", "message": "Invalid request format"}

        action = request.get("action")
        handlers = {
            "add_fact": self.add_fact,
            "get_fact": self.get_fact,
            "update_fact": self.update_fact,
            "search_facts": self.search_facts,
            "health_check": lambda _: {"status": "success", "healthy": True},
        }
        handler = handlers.get(action)
        if not handler:
            return {"status": "error", "message": f"Unknown action: {action}"}
        return handler(request)

    # ------------------------------------------------------------------
    # Fact Operations
    # ------------------------------------------------------------------

    def add_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        topic = request.get("topic")
        content = request.get("content")
        if not topic or not content:
            return {"status": "error", "message": "Missing topic or content"}
        try:
            metadata = {"topic": topic}
            tags = [topic.lower()]
            resp = self.memory_client.add_memory(
                content=content,
                memory_type="knowledge_fact",
                memory_tier="long",
                importance=0.8,
                metadata=metadata,
                tags=tags,
            )
            if resp.get("status") == "success":
                return {"status": "success", "memory_id": resp.get("memory_id")}
            self._report_error("add_fact_error", resp.get("message", "Unknown error"))
            return {"status": "error", "message": resp.get("message", "Unknown error")}
        except Exception as exc:
            self._report_error("add_fact_exception", str(exc))
            return {"status": "error", "message": str(exc)}

    def get_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        topic = request.get("topic")
        if not topic:
            return {"status": "error", "message": "Missing topic"}
        try:
            # Prefer semantic search
            try:
                resp = self.memory_client.semantic_search(query=topic, k=1)
                if resp.get("status") == "success" and resp.get("results"):
                    return {"status": "success", "fact": resp["results"][0]}
            except Exception as exc:
                logger.warning(f"Semantic search failed: {exc}")
            # Fallback text search
            resp = self.memory_client.search_memory(query=str(topic), memory_type="knowledge_fact", limit=1)
            if resp.get("status") == "success" and resp.get("results"):
                return {"status": "success", "fact": resp["results"][0]}
            msg = resp.get("message", "Fact not found")
            self._report_error("get_fact_error", msg)
            return {"status": "error", "message": msg}
        except Exception as exc:
            self._report_error("get_fact_exception", str(exc))
            return {"status": "error", "message": str(exc)}

    def update_fact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        topic = request.get("topic")
        new_content = request.get("content")
        memory_id = request.get("memory_id")
        if not ((topic or memory_id) and new_content):
            return {"status": "error", "message": "Missing required parameters"}
        try:
            if memory_id:
                return self._update_memory_item(memory_id, new_content)
            # Search by topic
            resp = self.memory_client.search_memory(query=topic, memory_type="knowledge_fact", limit=1)
            if resp.get("status") == "success" and resp.get("results"):
                memory_id = resp["results"][0].get("memory_id")
                return self._update_memory_item(memory_id, new_content)
            msg = resp.get("message", "Fact not found")
            self._report_error("update_fact_search_error", msg)
            return {"status": "error", "message": msg}
        except Exception as exc:
            self._report_error("update_fact_exception", str(exc))
            return {"status": "error", "message": str(exc)}

    def _update_memory_item(self, memory_id: str, new_content: str) -> Dict[str, Any]:
        resp = self.memory_client.update_memory(memory_id=memory_id, update_payload={"content": new_content})
        if resp.get("status") == "success":
            return {"status": "success", "message": "Fact updated successfully"}
        msg = resp.get("message", "Update failed")
        self._report_error("update_fact_error", msg)
        return {"status": "error", "message": msg}

    def search_facts(self, request: Dict[str, Any]) -> Dict[str, Any]:
        query = request.get("query", "")
        limit = request.get("limit", 10)
        try:
            # Semantic first
            try:
                resp = self.memory_client.semantic_search(query=query, k=limit)
                if resp.get("status") == "success" and resp.get("results"):
                    return {"status": "success", "results": resp["results"]}
            except Exception as exc:
                logger.warning(f"Semantic search failed: {exc}")
            # Fallback text search
            resp = self.memory_client.search_memory(query=query, memory_type="knowledge_fact", limit=limit)
            if resp.get("status") == "success":
                return {"status": "success", "results": resp.get("results", [])}
            msg = resp.get("message", "Search failed")
            self._report_error("search_facts_error", msg)
            return {"status": "error", "message": msg}
        except Exception as exc:
            self._report_error("search_facts_exception", str(exc))
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Lifecycle & Health (Rules 5 & 6)
    # ------------------------------------------------------------------

    def perform_health_check(self) -> Dict[str, Any]:  # Rule 6 shortcut
        return self._get_health_status()

    def _get_health_status(self) -> Dict[str, Any]:
        uptime = int(time.time() - self.start_time)
        return {
            "status": "HEALTHY",
            "service": self.__class__.__name__,
            "uptime_seconds": uptime,
            "request_count": self.request_count,
            "timestamp": time.time(),
        }

    def cleanup(self):  # Rule 5
        logger.info("KnowledgeBase cleanup start")
        try:
            if hasattr(self, "error_bus_pub") and self.error_bus_pub:
                self.error_bus_pub.close()
            if hasattr(self, "context") and self.context:
                self.context.term()
            logger.info("KnowledgeBase cleanup complete")
        except Exception as exc:
            logger.error(f"Cleanup error: {exc}")
        super().cleanup()

# -----------------------------------------------------------------------------
# Entrypoint (Rule 0, 5)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    agent = None
    try:
        agent = KnowledgeBase()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down…")
    except Exception as exc:
        logger.critical(f"KnowledgeBase failed: {exc}", exc_info=True)
    finally:
        if agent and hasattr(agent, "cleanup"):
            agent.cleanup()
