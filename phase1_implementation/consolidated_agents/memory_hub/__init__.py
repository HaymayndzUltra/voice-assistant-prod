"""Memory Hub Unified Service package.

This package consolidates 12 legacy memory-related agents into a single
FastAPI-based micro-service.  Each legacy agent will be integrated
progressively as a dedicated router or background component while
retaining 100 % of its original logic ("Walang Makakalimutan").

The public FastAPI instance is exposed in `memory_hub.memory_hub:app`.
"""

from importlib import import_module
from typing import List

__all__: List[str] = [
    "import_legacy_agents",
]


def import_legacy_agents() -> None:
    """Pre-import legacy agent modules so they can register routers/background tasks.

    This helper is *optional* at this stage.  It simply ensures the
    original modules are loaded which may have side-effects such as
    creating ZMQ sockets or background threads even before we explicitly
    wrap them.  When proper wrappers are ready, this function can be
    removed or updated.
    """
    legacy_modules = [
        "main_pc_code.agents.memory_client",
        "main_pc_code.agents.session_memory_agent",
        "main_pc_code.agents.knowledge_base",
        "pc2_code.agents.memory_orchestrator_service",
        "pc2_code.agents.unified_memory_reasoning_agent",
        "pc2_code.agents.context_manager",
        "pc2_code.agents.experience_tracker",
        "pc2_code.agents.cache_manager",
        "pc2_code.agents.ForPC2.proactive_context_monitor",
        "pc2_code.agents.ForPC2.unified_utils_agent",
        "pc2_code.agents.ForPC2.AuthenticationAgent",
        "pc2_code.agents.AgentTrustScorer",
    ]

    for module_path in legacy_modules:
        try:
            import_module(module_path)
        except ModuleNotFoundError:
            # Some agents may rely on platform-specific deps; ignore for now.
            pass