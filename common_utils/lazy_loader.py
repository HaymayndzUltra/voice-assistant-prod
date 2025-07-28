from types import ModuleType
from typing import List
import sys

from common_utils.agent_helpers import lazy_import

__all__ = ["enable"]

_HEAVY_MODULES_DEFAULT: List[str] = [
    "torch",
    "TTS",
    "sounddevice",
    "numpy",  # moderate but sometimes heavy with MKL
]


def enable(extra_modules: List[str] | None = None) -> None:
    """Install lazy import proxies for heavy modules.

    Args:
        extra_modules: optional additional module names to lazy load.
    """
    modules = list(_HEAVY_MODULES_DEFAULT)
    if extra_modules:
        modules.extend(extra_modules)
    for mod in modules:
        if mod not in sys.modules:
            lazy_import(mod)