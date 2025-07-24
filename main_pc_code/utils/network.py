import os
from typing import Optional
from common.env_helpers import get_env

# Attempt to import central configuration
try:
    from main_pc_code.config.system_config import config  # type: ignore
except Exception:
    # Fallback to empty config if import fails or during early bootstrap
    config = {}


def get_bind_address(default: str = "0.0.0.0") -> str:
    """Return the address to bind ZMQ sockets.

    Priority order:
        1. Environment variable BIND_ADDRESS
        2. config['network']['bind_address'] or config['bind_address']
        3. Supplied *default* value (defaults to '0.0.0.0').
    """
    return (
        os.environ.get("BIND_ADDRESS")
        or _nested_get(config, ["network", "bind_address"])  # type: ignore[arg-type]
        or config.get("bind_address")  # type: ignore[attr-defined]
        or default
    )


def get_host(env_var: str, config_key: Optional[str] = None, default: str = get_env("BIND_ADDRESS", "0.0.0.0")) -> str:
    """Return the host used for *connect* calls.

    Priority order:
        1. The given environment variable *env_var*
        2. The given *config_key* inside the central config (either at top level or under 'network')
        3. The supplied *default* value.
    """
    return (
        os.environ.get(env_var)
        or (_nested_get(config, ["network", config_key]) if config_key else None)  # type: ignore[arg-type]
        or (config.get(config_key) if config_key else None)  # type: ignore[attr-defined]
        or default
    )


def _nested_get(d: dict, keys):
    """Safe nested dict get."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur
