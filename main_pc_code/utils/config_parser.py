#!/usr/bin/env python3
"""
Configuration Parser
This module provides utilities for parsing command-line arguments for agents.
"""

import sys
import argparse
from typing import List, Optional
from common.env_helpers import get_env

# Constants
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


def parse_agent_args(argv: Optional[List[str]] = None):
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
    parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), type=str)
    parser.add_argument("--port", default=None, type=int)

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
