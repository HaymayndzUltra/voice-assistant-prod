#!/usr/bin/env python3
"""
UnifiedHealthMonitor Agent
==========================

Purpose
-------
Consolidated monitoring service that replaces PredictiveHealthMonitor (main PC) and
HealthMonitor / PerformanceMonitor (PC2).

Responsibilities
----------------
1. Subscribe to the central *Error Bus* (ZMQ PUB/SUB, topic prefix ``ERROR:``)
   and maintain Prometheus counters per-agent / per-error-type.
2. Periodically request health information from **SystemDigitalTwin** to
   gather the list of registered agents, then scrape their ``/health`` endpoints
   to capture latency and status metrics.
3. Expose its own health endpoint (handled by BaseAgent) so that orchestrators
   can verify the monitor itself.

Implementation Notes
--------------------
• This agent is intentionally *read-only* – it never mutates system state.
• Uses ``prometheus_client`` registry that is already a project dependency.
• Keeps background threads lightweight so as not to contend with GPU resources.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List, Optional

import requests
import zmq
from prometheus_client import Counter, Gauge, start_http_server  # type: ignore

from common.core.base_agent import BaseAgent

# ---------------------------------------------------------------------------
# Constants & Environment
# ---------------------------------------------------------------------------
ERROR_TOPIC_PREFIX = b"ERROR:"
ERROR_BUS_PORT = int(os.getenv("ERROR_BUS_PORT", "7150"))
ERROR_BUS_HOST = os.getenv("ERROR_BUS_HOST", os.getenv("PC2_IP", "127.0.0.1"))
ERROR_BUS_ENDPOINT = f"tcp://{ERROR_BUS_HOST}:{ERROR_BUS_PORT}"

# SystemDigitalTwin lookup (defaults to localhost)
SDT_HOST = os.getenv("SYSTEM_DIGITAL_TWIN_HOST", "localhost")
SDT_PORT = int(os.getenv("SYSTEM_DIGITAL_TWIN_PORT", "7120"))

SCRAPE_INTERVAL_SEC = float(os.getenv("UHM_SCRAPE_INTERVAL", "15"))
PROMETHEUS_METRICS_PORT = int(os.getenv("UHM_METRICS_PORT", "9300"))

# ---------------------------------------------------------------------------
# UnifiedHealthMonitor implementation
# ---------------------------------------------------------------------------


class UnifiedHealthMonitor(BaseAgent):
    """Centralised health-monitoring agent."""

    def __init__(self, port: int = 8200, **kwargs):  # noqa: D401 – simple description ok
        # BaseAgent sets up sockets & health endpoints
        super().__init__(name="UnifiedHealthMonitor", port=port, **kwargs)

        # Prometheus metrics ---------------------------------------------------
        self._error_counter: Counter = Counter(
            "agent_errors_total",
            "Total number of errors published on the error bus, labelled by agent and error_type.",
            ["agent", "error_type"],
        )
        self._scrape_latency_gauge: Gauge = Gauge(
            "agent_health_latency_ms",
            "Latency (milliseconds) for HTTP /health scrape per agent.",
            ["agent"],
        )
        self._agent_health_status: Gauge = Gauge(
            "agent_health_status",
            "Agent health status (1 = ok/ready, 0 = not ok)",
            ["agent"],
        )

        # Expose Prometheus metrics on separate HTTP port ----------------------
        start_http_server(PROMETHEUS_METRICS_PORT)
        self.logger.info(
            "Prometheus metrics server started on port %d", PROMETHEUS_METRICS_PORT
        )

        # Prepare ZMQ SUB socket for the error bus -----------------------------
        self._error_sub_socket = self.context.socket(zmq.SUB)
        self._error_sub_socket.setsockopt(zmq.SUBSCRIBE, ERROR_TOPIC_PREFIX)
        self._error_sub_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 s poll timeout
        try:
            self._error_sub_socket.connect(ERROR_BUS_ENDPOINT)
            self.logger.info("Connected to error bus at %s", ERROR_BUS_ENDPOINT)
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Failed to connect to error bus: %s", exc, exc_info=True)

        # Background workers ---------------------------------------------------
        self._background_threads: List[threading.Thread] = []
        self._start_background_workers()

    # ---------------------------------------------------------------------
    # BaseAgent overrides
    # ---------------------------------------------------------------------

    def handle_request(self, request: Dict[str, any]) -> Dict[str, any]:  # noqa: ANN401
        """Simply respond with OK for ping/health; delegate others to super."""
        action = request.get("action") if isinstance(request, dict) else None
        if action in {"ping", "health", "health_check"}:
            return self._get_health_status()
        return super().handle_request(request)

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _start_background_workers(self):
        # Error-bus listener thread
        t_error = threading.Thread(target=self._error_bus_listener, daemon=True)
        t_error.start()
        self._background_threads.append(t_error)

        # Health scrape thread
        t_scrape = threading.Thread(target=self._scrape_loop, daemon=True)
        t_scrape.start()
        self._background_threads.append(t_scrape)

    # ------------------------ Error Bus ----------------------------------

    def _error_bus_listener(self):
        self.logger.info("Error-bus listener started")
        while self.running:
            try:
                if self._error_sub_socket.poll(timeout=1000) != 0:
                    raw_msg: bytes = self._error_sub_socket.recv()  # BLOCKS short
                    # Remove topic prefix
                    _, payload = raw_msg.split(b":", 1)
                    try:
                        data = json.loads(payload.decode("utf-8"))
                        agent_name = data.get("agent", "unknown")
                        error_type = data.get("error_type", "unknown")
                        self._error_counter.labels(agent=agent_name, error_type=error_type).inc()
                    except Exception as exc:  # noqa: BLE001
                        self.logger.warning("Malformed error-bus message: %s", exc)
            except zmq.error.Again:
                continue  # poll timeout
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Error in error-bus listener: %s", exc, exc_info=True)
                time.sleep(1)

    # ----------------------- Health Scrape -------------------------------

    def _scrape_loop(self):
        self.logger.info("Health-scrape thread started; interval %.1f s", SCRAPE_INTERVAL_SEC)
        while self.running:
            try:
                agent_list = self._fetch_agent_list()
                for agent in agent_list:
                    self._scrape_agent_health(agent)
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Health-scrape loop error: %s", exc, exc_info=True)
            time.sleep(SCRAPE_INTERVAL_SEC)

    def _fetch_agent_list(self) -> List[str]:
        """Query SystemDigitalTwin for a list of registered agents."""
        try:
            ctx = self.context
            sock = ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.LINGER, 0)
            sock.setsockopt(zmq.RCVTIMEO, 3000)
            sock.connect(f"tcp://{SDT_HOST}:{SDT_PORT}")
            sock.send_json({"action": "get_ok_agents"})
            response = sock.recv_json()
            if response.get("status") == "success":
                return response.get("agents", [])
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("Could not fetch agent list: %s", exc)
        return []

    def _scrape_agent_health(self, agent_name: str):
        """GET http://<agent_host>:<health_port>/health.

        Assumes that BaseAgent health ports = main port + 1000, and that host is
        reachable on localhost or via ServiceRegistry endpoint.
        """
        # First ask ServiceRegistry for endpoint
        host, health_port = self._resolve_agent_endpoint(agent_name)
        if host is None or health_port is None:
            return  # cannot resolve, skip
        try:
            t0 = time.time()
            url = f"http://{host}:{health_port}/health"
            r = requests.get(url, timeout=2)
            latency_ms = (time.time() - t0) * 1000.0
            self._scrape_latency_gauge.labels(agent=agent_name).set(latency_ms)
            ok = r.status_code == 200 and r.json().get("status") == "ok"
            self._agent_health_status.labels(agent=agent_name).set(1 if ok else 0)
        except Exception:
            self._agent_health_status.labels(agent=agent_name).set(0)

    def _resolve_agent_endpoint(self, agent_name: str) -> tuple[Optional[str], Optional[int]]:  # noqa: ANN401
        """Resolve agent endpoint using ServiceRegistry (via SystemDigitalTwin).
        Falls back to localhost:<default_port> if unknown.
        """
        try:
            ctx = self.context
            sock = ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.LINGER, 0)
            sock.setsockopt(zmq.RCVTIMEO, 2000)
            sock.connect(f"tcp://{SDT_HOST}:{SDT_PORT}")
            sock.send_json({"action": "get_agent_endpoint", "agent_name": agent_name})
            resp = sock.recv_json()
            if resp.get("status") == "success":
                host = resp.get("host", "localhost")
                port = int(resp.get("health_check_port", resp.get("port", 0)))
                return host, port
        except Exception:
            pass
        # Fallback, guess
        return "localhost", None


# ----------------------------------------------------------------------------
# Entrypoint helper
# ----------------------------------------------------------------------------


def main() -> None:  # noqa: D401 – simple description ok
    agent = UnifiedHealthMonitor()
    try:
        agent.run()
    finally:
        agent.cleanup()


if __name__ == "__main__":
    main()