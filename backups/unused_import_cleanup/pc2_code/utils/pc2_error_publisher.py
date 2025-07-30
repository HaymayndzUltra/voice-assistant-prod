#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PC2-Specific Error Publisher for PC2 Agents

Extended ErrorPublisher specifically designed for PC2 agents with:
- PC2-specific environment configuration
- Enhanced error categorization for PC2 services
- Integration with PC2 monitoring infrastructure
- Cross-machine error propagation to Main PC

Based on main_pc_code/agents/error_publisher.py with PC2 adaptations.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import zmq
from common.pools.zmq_pool import get_pub_socket
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine


class PC2ErrorPublisher:
    """PC2-specific error publisher with enhanced categorization and cross-machine propagation.

    Parameters
    ----------
    source : str
        Human-readable name of the PC2 agent/service publishing the error.
    endpoint : Optional[str]
        Full ZMQ endpoint (e.g. ``tcp://host:port``).  If *None*, it is constructed
        from PC2-specific environment variables.
    context : Optional[zmq.Context]
        Existing ZMQ context.  If *None*, the global instance is used.
    propagate_to_mainpc : bool, default=True
        Whether to also send critical errors to Main PC error bus.
    """

    def __init__(
        self, 
        source: str, 
        *, 
        endpoint: Optional[str] = None, 
        context: Optional[zmq.Context] = None,
        propagate_to_mainpc: bool = True
    ) -> None:
        self.source = source
        self.propagate_to_mainpc = propagate_to_mainpc
        self.endpoint = endpoint or self._build_default_endpoint()
        self.mainpc_endpoint = self._build_mainpc_endpoint() if propagate_to_mainpc else None
        
        self._ctx_provided = context is not None
        self.context = context or zmq.Context.instance()

        # Setup PC2 local error bus
        try:
            self.socket = get_pub_socket(self.endpoint).socket
            self.socket.connect(self.endpoint)
            logging.debug(f"PC2ErrorPublisher connected to local bus: {self.endpoint}")
        except Exception as exc:
            logging.error("PC2ErrorPublisher: failed to set up local PUB socket: %s", exc)
            self.socket = None

        # Setup Main PC error bus connection (for critical errors)
        self.mainpc_socket = None
        if self.propagate_to_mainpc and self.mainpc_endpoint:
            try:
                self.mainpc_socket = get_pub_socket(self.mainpc_endpoint).socket
                self.mainpc_socket.connect(self.mainpc_endpoint)
                logging.debug(f"PC2ErrorPublisher connected to Main PC bus: {self.mainpc_endpoint}")
            except Exception as exc:
                logging.warning("PC2ErrorPublisher: failed to connect to Main PC error bus: %s", exc)
                self.mainpc_socket = None

    def publish_error(
        self,
        *,
        error_type: str,
        severity: str = "error",
        details: Any = None,
        message_type: str = "error_report",
        category: str = "pc2_service",
        send_to_mainpc: Optional[bool] = None
    ) -> None:
        """Publish an error on the PC2 error bus with optional Main PC propagation.

        Parameters
        ----------
        error_type : str
            Short machine-friendly category of the error.
        severity : str, optional
            ``critical``, ``high``, ``medium``, ``low``, defaults to ``error``.
        details : Any, optional
            Additional JSON-serializable payload.
        message_type : str, optional
            Either ``error_report`` or ``critical_alert``.
        category : str, optional
            PC2-specific error category (``pc2_service``, ``memory_ops``, ``vision_processing``, etc.)
        send_to_mainpc : Optional[bool], optional
            Override default Main PC propagation behavior for this error.
        """
        if self.socket is None:
            return  # silently ignore if initialization failed

        # Determine if this should go to Main PC
        should_send_mainpc = send_to_mainpc
        if should_send_mainpc is None:
            should_send_mainpc = self.propagate_to_mainpc and severity in ["critical", "high"]

        # Build enhanced payload with PC2-specific metadata
        payload = {
            "message_type": message_type,
            "source": self.source,
            "source_machine": "PC2",
            "timestamp": datetime.utcnow().isoformat(),
            "error_data": {
                "error_id": str(uuid.uuid4()),
                "error_type": error_type,
                "severity": severity,
                "category": category,
                "details": details,
                "machine_context": {
                    "host": get_pc2_ip(),
                    "current_machine": get_current_machine(),
                    "runtime_env": os.environ.get("ENV", "development")
                }
            },
        }

        # Send to PC2 local error bus
        try:
            topic = f"PC2_ERROR:{category.upper()}"
            self.socket.send_string(f"{topic}:{json.dumps(payload)}")
            logging.debug(f"Published error to PC2 bus: {error_type} ({severity})")
        except Exception as exc:
            logging.error("PC2ErrorPublisher: failed to send error to PC2 bus: %s", exc)

        # Send to Main PC error bus for critical/high severity errors
        if should_send_mainpc and self.mainpc_socket is not None:
            try:
                # Add cross-machine metadata
                mainpc_payload = payload.copy()
                mainpc_payload["cross_machine_alert"] = True
                mainpc_payload["originating_machine"] = "PC2"
                
                topic = f"CROSS_MACHINE_ERROR:PC2"
                self.mainpc_socket.send_string(f"{topic}:{json.dumps(mainpc_payload)}")
                logging.info(f"Propagated {severity} error to Main PC: {error_type}")
            except Exception as exc:
                logging.error("PC2ErrorPublisher: failed to send error to Main PC: %s", exc)

    def publish_pc2_specific_error(
        self,
        *,
        error_type: str,
        pc2_component: str,
        severity: str = "error",
        details: Any = None,
        performance_impact: Optional[str] = None
    ) -> None:
        """Publish PC2-specific error with component and performance context.

        Parameters
        ----------
        error_type : str
            Short machine-friendly category of the error.
        pc2_component : str
            PC2 component (memory_orchestrator, cache_manager, vision_processing, etc.)
        severity : str, optional
            Error severity level.
        details : Any, optional
            Additional error context.
        performance_impact : Optional[str], optional
            Performance impact description (``none``, ``minimal``, ``moderate``, ``severe``).
        """
        enhanced_details = {
            "pc2_component": pc2_component,
            "performance_impact": performance_impact,
            "original_details": details
        }

        self.publish_error(
            error_type=error_type,
            severity=severity,
            details=enhanced_details,
            category=f"pc2_{pc2_component}",
            message_type="error_report"
        )

    def close(self) -> None:
        """Cleanly close both PC2 and Main PC PUB sockets."""
        if self.socket is not None:
            try:
                self.socket.close(linger=0)
            except Exception:
                pass

        if self.mainpc_socket is not None:
            try:
                self.mainpc_socket.close(linger=0)
            except Exception:
                pass

        if not self._ctx_provided and getattr(self, "context", None) is not None:
            try:
                self.context.term()
            except Exception:
                pass

    @staticmethod
    def _build_default_endpoint() -> str:
        """Build PC2 local error bus endpoint."""
        host = os.environ.get("PC2_ERROR_BUS_HOST", get_pc2_ip())
        port = int(os.environ.get("PC2_ERROR_BUS_PORT", 7150))
        return f"tcp://{host}:{port}"

    @staticmethod
    def _build_mainpc_endpoint() -> str:
        """Build Main PC error bus endpoint for cross-machine propagation."""
        host = os.environ.get("MAINPC_ERROR_BUS_HOST", get_mainpc_ip())
        port = int(os.environ.get("MAINPC_ERROR_BUS_PORT", 7150))
        return f"tcp://{host}:{port}"

    # Context manager support
    def __enter__(self) -> "PC2ErrorPublisher":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience factory for PC2 agents
def create_pc2_error_publisher(agent_name: str, **kwargs) -> PC2ErrorPublisher:
    """Factory function to create PC2ErrorPublisher with agent name."""
    return PC2ErrorPublisher(source=agent_name, **kwargs)
