#!/usr/bin/env python
"""Dynamic command-line configuration parser for agents.

Usage inside an agent:
    from utils.config_parser import parse_agent_args
    args = parse_agent_args()

The parser always provides:
    args.host  -> str
    args.port  -> int
Plus any number of additional <name>_host / <name>_port entries
converted to appropriate str / int types.
"""
import argparse
import sys
from typing import List

_STANDARD_ARGS = ["host", "port"]


def _discover_dynamic_flags(argv: List[str]) -> List[str]:
    """Return flag names (without leading dashes) discovered in argv that are
    not the standard ones.
    Example: ['--modelmanager_host', '1234'] -> 'modelmanager_host'.
    """
    flags = []
    for item in argv:
        if item.startswith("--"):
            flag = item.lstrip("-")
            if flag not in _STANDARD_ARGS:
                flags.append(flag)
    return list(dict.fromkeys(flags))  # deduplicate preserving order


def parse_agent_args(argv: List[str] | None = None):
    """Parse command-line arguments passed to an agent.

    Always returns an ``argparse.Namespace`` providing at least:
        • host: str
        • port: int | None

    Additionally, any dynamic flags like ``--taskrouter_host`` or ``--modelmanager_port``
    are accepted automatically.  Flags ending in ``_port`` are parsed as ``int``,
    all others as ``str``.

    The function is intentionally lightweight and *never exits* the process –
    it raises ``ValueError`` on invalid input instead of calling ``sys.exit``.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(add_help=False)
    # Standard flags
    parser.add_argument("--host", default="localhost", type=str)
    parser.add_argument("--check_interval_seconds", type=int, default=15, help="How often to check VRAM and idle status.")
    parser.add_argument("--port", default=None, type=int)

    # GGUF VRAM Management Arguments
    parser.add_argument("--gguf_vram_management_enabled", action="store_true", help="Enable VRAM management for GGUF models.")
    parser.add_argument("--gguf_vram_budget_gb", type=float, default=12.0, help="VRAM budget in GB for GGUF models.")
    parser.add_argument("--gguf_idle_unload_timeout_seconds", type=int, default=300, help="Seconds of inactivity before unloading a GGUF model.")
    parser.add_argument("--gguf_check_interval_seconds", type=int, default=30, help="How often to check VRAM and idle status for GGUF models.")

    # Dynamically add flags discovered in argv so argparse won't error out
    for flag in _discover_dynamic_flags(argv):
        arg_name = f"--{flag}"
        arg_type = int if flag.endswith("_port") else str
        parser.add_argument(arg_name, dest=flag, type=arg_type)

    # Parse
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as e:  # pragma: no cover – convert to ValueError to avoid sys.exit
        raise ValueError(f"Argument parsing failed: {e}")

    return parsed
