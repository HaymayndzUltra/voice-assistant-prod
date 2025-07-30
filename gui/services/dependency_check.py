from __future__ import annotations

"""Dependency checker that warns the user (via EventBus toast) when optional
packages are missing.  Meant to be run once at GUI startup.
"""

import importlib
from typing import List

OPTIONAL_PACKAGES = [
    ("psutil", "System metrics"),
    ("matplotlib", "Charts"),
    ("networkx", "Graph visualisation"),
]


def check_dependencies(show_warning):  # show_warning: Callable[[str], None]
    missing: List[str] = []
    for name, _desc in OPTIONAL_PACKAGES:
        if importlib.util.find_spec(name) is None:
            missing.append(name)

    if missing:
        show_warning(
            "Missing optional libs: " + ", ".join(missing) + ". Charts/metrics may be limited."
        )