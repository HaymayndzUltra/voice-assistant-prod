"""Unified Reasoning Engine
===========================

Provides a single entry-point that exposes multiple reasoning *strategies* that
were previously split across dedicated agents (Chain-of-Thought, GoT/ToT, and
Cognitive Belief-graph reasoning).

During Phase-2 the *CognitiveReasoningAgent* will embed this engine and select
an appropriate strategy per request.

The initial implementation shells out to the existing agent classes so we can
migrate incrementally without breaking behaviour.  Once stable, the full logic
will be refactored *into* the strategy classes and legacy agents will be
removed.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from common.utils.circuit_breaker import CircuitBreaker
from common.utils.error_publisher import ErrorPublisher

# Re-use the existing agent classes (import lazily to avoid heavy startup costs)

logger = logging.getLogger(__name__)


class ReasoningStrategy:
    """Abstract base strategy."""

    name: str = "base"

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:  # noqa: D401
        raise NotImplementedError


class ChainOfThoughtStrategy(ReasoningStrategy):
    name = "chain_of_thought"

    def __init__(self):
        from main_pc_code.FORMAINPC.ChainOfThoughtAgent import ChainOfThoughtAgent  # inline import

        # Bind to *ephemeral* port 0 so we don't clash with the standalone agent.
        self._agent = ChainOfThoughtAgent(port=0, name="CoTEmbedded")

    def generate(self, prompt: str, **kwargs):  # noqa: D401
        # Pass through to existing implementation
        result = self._agent.generate_with_cot(prompt, code_context=kwargs.get("code_context"))
        return result


class GoTToTStrategy(ReasoningStrategy):
    name = "got_tot"

    def __init__(self):
        from main_pc_code.FORMAINPC.GOT_TOTAgent import GoTToTAgent

        self._agent = GoTToTAgent(port=0, name="GoTEmbedded")

    def generate(self, prompt: str, **kwargs):  # noqa: D401
        best_path, _ = self._agent.reason(prompt, context=kwargs.get("context", []))
        return {
            "solution": [n.state for n in best_path],
            "strategy": self.name,
        }


class BeliefGraphStrategy(ReasoningStrategy):
    name = "belief_graph"

    def __init__(self):
        from main_pc_code.FORMAINPC.CognitiveModelAgent import CognitiveModelAgent

        self._agent = CognitiveModelAgent(port=0, name="BeliefGraphEmbedded")

    def generate(self, prompt: str, **kwargs):  # noqa: D401
        # For now simply query belief consistency or add belief depending on kwargs
        action = kwargs.get("action", "query")
        if action == "add_belief":
            return self._agent.add_belief(prompt, belief_type="fact", relationships=[])
        return self._agent.query_belief_consistency(prompt)


class ReasoningEngine:
    """Facade exposing multiple reasoning strategies."""

    _strategies: Dict[str, ReasoningStrategy] = {}

    def __init__(self, *, error_publisher: ErrorPublisher | None = None):
        self.error_publisher = error_publisher or ErrorPublisher("ReasoningEngine")
        self._register_default_strategies()

    # ------------------------------------------------------------------
    def _register_default_strategies(self):
        for strat_cls in (ChainOfThoughtStrategy, GoTToTStrategy, BeliefGraphStrategy):
            try:
                strategy = strat_cls()
                self._strategies[strategy.name] = strategy
                logger.info("Registered reasoning strategy: %s", strategy.name)
            except Exception as exc:  # pragma: no cover – import errors etc.
                logger.error("Failed to initialise strategy %s: %s", strat_cls.__name__, exc)
                self.error_publisher.publish_error(
                    error_type="strategy_init",
                    severity="medium",
                    details={"strategy": strat_cls.__name__, "error": str(exc)},
                )

    # ------------------------------------------------------------------
    def available_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    def generate(self, prompt: str, *, strategy: str | None = None, **kwargs) -> Dict[str, Any]:
        """Generate a reasoning solution using *strategy* (or fallback)."""
        selected = self._choose_strategy(strategy)
        try:
            result = selected.generate(prompt, **kwargs)
            result.setdefault("strategy", selected.name)
            return result
        except Exception as exc:  # pragma: no cover – runtime failure
            logger.error("ReasoningEngine: strategy %s failed: %s", selected.name, exc)
            self.error_publisher.publish_error(
                error_type="reasoning_failure",
                severity="high",
                details={"strategy": selected.name, "error": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    def _choose_strategy(self, requested: str | None) -> ReasoningStrategy:
        if requested and requested in self._strategies:
            return self._strategies[requested]
        # Fallback priority order
        for pref in ("chain_of_thought", "got_tot", "belief_graph"):
            if pref in self._strategies:
                return self._strategies[pref]
        # Should never happen – at least one strategy must load.
        raise RuntimeError("No reasoning strategies available")