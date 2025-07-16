#!/usr/bin/env python3
"""
Code Generator Agent

Provides basic code generation capability (placeholder) while adhering to the
project's BaseAgent compliance standards. All configuration is loaded from the
central configuration or environment variables (see Compliance Protocol).
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any

import zmq

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# -----------------------------------------------------------------------------
# Configuration & Logging
# -----------------------------------------------------------------------------

config = load_config()

DEFAULT_PORT = int(os.environ.get(
    "CODE_GENERATOR_PORT",
    config.get("code_generator", {}).get("port", 5720),
))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("CodeGeneratorAgent")

# -----------------------------------------------------------------------------
# Agent Definition
# -----------------------------------------------------------------------------

class CodeGeneratorAgent(BaseAgent):
    """A minimal, compliant agent that can generate (placeholder) code."""

    def __init__(self, port: int = DEFAULT_PORT, **kwargs: Any):
        name = kwargs.get("name", "CodeGeneratorAgent")
        health_port = port + 1
        super().__init__(name=name, port=port, health_check_port=health_port)

        # Error-bus connection (Rule 8)
        self.context = zmq.Context.instance()
        self.error_bus_pub = self.context.socket(zmq.PUB)
        err_host = os.environ.get("ERROR_BUS_HOST", os.environ.get("PC2_IP", "localhost"))
        err_port = int(os.environ.get("ERROR_BUS_PORT", 7150))
        self.error_bus_pub.connect(f"tcp://{err_host}:{err_port}")

        self.start_time = time.time()
        self.request_count = 0
        logger.info(f"{self.name} initialised on port {port}")

    # ------------------------------------------------------------------
    # Request Handling
    # ------------------------------------------------------------------

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.request_count += 1
        action = request.get("action")
        if action == "generate_code":
            return self.generate_code(request)
        if action == "health_check":
            return self.perform_health_check()
        return {"status": "error", "message": f"Unknown action: {action}"}

    def generate_code(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Very simple placeholder implementation."""
        prompt = request.get("prompt", "")
        generated = f"# TODO: Auto-generated code for prompt: {prompt}"
        return {"status": "success", "code": generated}

    # ------------------------------------------------------------------
    # Health & Cleanup (Rules 5 & 6)
    # ------------------------------------------------------------------

    def perform_health_check(self) -> Dict[str, Any]:
        return self._get_health_status()

    def _get_health_status(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "service": self.name,
            "uptime_seconds": int(time.time() - self.start_time),
            "request_count": self.request_count,
            "timestamp": time.time(),
        }

    def cleanup(self) -> None:
        if hasattr(self, "error_bus_pub"):
            self.error_bus_pub.close()
        if hasattr(self, "context"):
            self.context.term()
        super().cleanup()

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    agent: CodeGeneratorAgent | None = None
    try:
        agent = CodeGeneratorAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted – shutting down…")
    except Exception as exc:  # pragma: no cover
        logger.critical(f"Fatal error: {exc}", exc_info=True)
    finally:
        if agent and hasattr(agent, "cleanup"):
            agent.cleanup() 