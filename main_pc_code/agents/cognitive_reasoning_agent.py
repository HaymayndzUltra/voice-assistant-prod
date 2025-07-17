"""CognitiveReasoningAgent
========================

Single entry-point replacing *ChainOfThoughtAgent*, *GoTToTAgent* and
*CognitiveModelAgent* as well as exposing integrated NLU → Validation → Goal
planning helpers.

For Phase-2 the agent focuses on the *reasoning* capability while delegating to
existing micro-services (NLUAgent, IntentionValidatorAgent, GoalManager,
TranslationService, DynamicIdentityAgent) over ZMQ using service-discovery.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import zmq

from common.core.base_agent import BaseAgent
from common.reasoning.engine import ReasoningEngine
from common.utils.error_publisher import ErrorPublisher
from common.utils.zmq_helper import create_socket, safe_socket_send, safe_socket_recv
from common.utils.circuit_breaker import CircuitBreaker
from main_pc_code.utils.service_discovery_client import discover_service

logger = logging.getLogger(__name__)


class CognitiveReasoningAgent(BaseAgent):
    """Unified reasoning + intent handling agent."""

    DEFAULT_PORT = int(os.environ.get("CR_AGENT_PORT", 5720))

    def __init__(self, *, port: int | None = None, name: str | None = None):
        super().__init__(name or "CognitiveReasoningAgent", port or self.DEFAULT_PORT)

        # Shared helpers
        self.error_publisher = ErrorPublisher(self.name)
        self.reasoning_engine = ReasoningEngine(error_publisher=self.error_publisher)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # ZMQ context comes from BaseAgent
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info("%s listening on tcp://*:%s", self.name, self.port)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_or_create_cb(self, service: str) -> CircuitBreaker:
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(service)
        return self.circuit_breakers[service]

    def _call_service(self, service_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call another micro-service via ZMQ using service-discovery."""
        cb = self._get_or_create_cb(service_name)
        if not cb.allow_request():
            return {"status": "error", "message": f"Circuit open for {service_name}"}

        try:
            svc = discover_service(service_name)
            if not svc:
                raise RuntimeError("Service not found in registry")
            endpoint = svc.get("endpoint") or f"tcp://{svc['host']}:{svc['port']}"
            sock = create_socket(self.context, zmq.REQ)
            sock.connect(endpoint)
            if not safe_socket_send(sock, payload):
                raise RuntimeError("send_timeout")
            ok, resp = safe_socket_recv(sock)
            if not ok:
                raise RuntimeError("recv_timeout")
            cb.record_success()
            return resp
        except Exception as exc:
            logger.error("Service call to %s failed: %s", service_name, exc)
            self.error_publisher.publish_error(error_type="service_call", severity="medium", details=str(exc))
            cb.record_failure()
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get("action")

        if action == "reason":
            prompt = request.get("prompt", "")
            strategy = request.get("strategy")
            result = self.reasoning_engine.generate(prompt, strategy=strategy)
            return {"status": "success", **result}

        if action == "analyze_intent":
            # Forward to NLU
            resp = self._call_service("NLUAgent", {"action": "analyze", "text": request.get("text", "")})
            return resp

        if action == "validate_intent":
            resp = self._call_service("IntentionValidatorAgent", request)
            return resp

        if action == "plan_goal":
            resp = self._call_service("GoalManager", {"action": "set_goal", "data": request})
            return resp

        return {"status": "error", "message": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    def run(self):  # type: ignore[override]
        logger.info("%s main loop started", self.name)
        while True:
            try:
                req = self.socket.recv_json()
                resp = self.handle_request(req)
                self.socket.send_json(resp)
            except Exception as exc:
                logger.error("Runtime error: %s", exc)
                self.error_publisher.publish_error(error_type="internal_error", severity="high", details=str(exc))
                try:
                    self.socket.send_json({"status": "error", "message": str(exc)})
                except Exception:  # pragma: no cover
                    pass