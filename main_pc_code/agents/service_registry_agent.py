#!/usr/bin/env python3
"""Service Registry Agent

A minimal, highly-available registry that other agents can query to discover
endpoints. It intentionally keeps zero external dependencies so that it can
start before the rest of the platform.

Implements two core actions:
1. ``register_agent`` – store/overwrite metadata about an agent.
2. ``get_agent_endpoint`` – return host/port (and extras) for a given agent.

Standard health actions (``ping``, ``health``, ``health_check``) are inherited
from :class:`common.core.base_agent.BaseAgent`.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, Any

from common.core.base_agent import BaseAgent
from common.utils.data_models import AgentRegistration

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_PORT = int(os.getenv("SERVICE_REGISTRY_PORT", 7100))
DEFAULT_HEALTH_PORT = int(os.getenv("SERVICE_REGISTRY_HEALTH_PORT", 8100))

logger = logging.getLogger("ServiceRegistryAgent")


class ServiceRegistryAgent(BaseAgent):
    """A tiny in-memory service registry."""

    def __init__(self, **kwargs):
        # Initialise registry storage before BaseAgent starts threads that
        # may call ``handle_request`` early.
        self.registry: Dict[str, Dict[str, Any]] = {}

        # Merge default ports with kwargs, but allow kwargs to override.
        port = int(kwargs.pop("port", DEFAULT_PORT))
        health = int(kwargs.pop("health_check_port", DEFAULT_HEALTH_PORT))

        super().__init__(name="ServiceRegistry", port=port, health_check_port=health, **kwargs)

    # ---------------------------------------------------------------------
    # Request handling
    # ---------------------------------------------------------------------
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch incoming requests by *action*.

        Parameters
        ----------
        request : Dict[str, Any]
            JSON-serialised request containing at minimum an ``action`` key.
        """
        action = request.get("action")

        # BaseAgent already handles the canonical health verbs.
        if action in {"ping", "health", "health_check"}:
            return super().handle_request(request)

        if action == "register_agent":
            return self._register_agent(request)

        if action == "get_agent_endpoint":
            return self._get_agent_endpoint(request)

        if action == "list_agents":
            return {
                "status": "success",
                "agents": list(self.registry.keys()),
            }

        return {"status": "error", "error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _register_agent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an agent registration request."""
        registration_data = request.get("registration_data") or request

        try:
            # Accept either already-validated AgentRegistration or raw dict.
            registration = (
                registration_data
                if isinstance(registration_data, AgentRegistration)
                else AgentRegistration(**registration_data)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid registration attempt: %s", exc)
            return {"status": "error", "error": str(exc)}

        self.registry[registration.agent_id] = {
            "host": registration.host,
            "port": registration.port,
            "health_check_port": registration.health_check_port,
            "agent_type": registration.agent_type,
            "capabilities": registration.capabilities,
            "metadata": registration.metadata,
            "last_registered": datetime.utcnow().isoformat(),
        }

        logger.info("Registered agent %s @ %s:%s", registration.agent_id, registration.host, registration.port)
        return {"status": "success"}

    def _get_agent_endpoint(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch the endpoint data for a given agent."""
        agent_name = request.get("agent_name")
        if not agent_name:
            return {"status": "error", "error": "Missing 'agent_name'"}

        if agent_name not in self.registry:
            return {"status": "error", "error": f"Agent {agent_name} not found"}

        data = self.registry[agent_name].copy()
        data.update({"status": "success"})
        return data


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = ServiceRegistryAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("ServiceRegistryAgent interrupted; shutting down")
