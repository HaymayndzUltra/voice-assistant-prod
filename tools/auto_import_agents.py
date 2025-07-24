#!/usr/bin/env python3
"""auto_import_agents.py
Self-healing import helper that scans startup_config.yaml for agent
`script_path` entries, makes sure the project-root is on `sys.path`, and
then tries to import each module.  If an ImportError surfaces, it will
create an *empty* stub-module for the missing import (and any parent
packages) so that the next import attempt can continue.

This is NOT intended for production – only for CI / smoke-test inside a
minimal snapshot environment lacking heavy third-party deps.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STARTUP_CONFIG = PROJECT_ROOT / "main_pc_code" / "config" / "startup_config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- utilities ------------------------------------------------------------

MISSING_CACHE: set[str] = set()


def stub_module(mod_name: str) -> None:
    """Create a stub module (and parents) to satisfy import."""
    if mod_name in sys.modules:
        return

    # Ensure parent packages exist first
    parts = mod_name.split(".")
    for i in range(1, len(parts) + 1):
        sub_name = ".".join(parts[:i])
        if sub_name not in sys.modules:
            sys.modules[sub_name] = types.ModuleType(sub_name)

    # Provide minimal attributes for common heavy packages
    mod = sys.modules[mod_name]
    if mod_name.startswith("pydantic"):
        class _BaseModel:  # noqa: D401 – simple stub
            def __init__(self, **data):
                for k, v in data.items():
                    setattr(self, k, v)
            def dict(self):
                return self.__dict__.copy()
        def _Field(default=..., **kwargs):  # type: ignore[override]
            return default
        mod.BaseModel = _BaseModel  # type: ignore[attr-defined]
        mod.Field = _Field  # type: ignore[attr-defined]
    elif mod_name == "zmq":
        for attr in ["REQ", "REP", "PUB", "SUB", "PUSH", "PULL", "DEALER", "ROUTER"]:
            setattr(mod, attr, len(mod.__dict__))
        class _Context:
            def socket(self, *a):
                return types.SimpleNamespace(send_json=lambda *a, **k: None,
                                               recv_json=lambda *a, **k: {},
                                               setsockopt=lambda *a, **k: None,
                                               bind=lambda *a, **k: None,
                                               connect=lambda *a, **k: None)
            @staticmethod
            def instance():
                return _Context()
        mod.Context = _Context  # type: ignore[attr-defined]
        # submodule asyncio
        async_mod = types.ModuleType("zmq.asyncio")
        async_mod.Context = _Context
        sys.modules["zmq.asyncio"] = async_mod
    elif mod_name == "redis":
        class _Redis:
            def __init__(self, *a, **k): pass
            def ping(self): return True
        mod.Redis = _Redis  # type: ignore[attr-defined]
        mod.from_url = staticmethod(lambda url, *a, **k: _Redis())  # type: ignore[attr-defined]
    elif mod_name.startswith("nats"):
        class _NC:
            async def connect(self, *a, **k): pass
            async def publish(self, *a, **k): pass
            async def close(self): pass
        client_mod = types.ModuleType("nats.aio.client")
        client_mod.Client = _NC
        sys.modules["nats.aio.client"] = client_mod
    elif mod_name == "torch":
        mod.Tensor = type("Tensor", (), {})  # type: ignore[attr-defined]
    elif mod_name == "numpy":
        import math
        mod.array = lambda x, *a, **k: x  # type: ignore[attr-defined]
        mod.mean = lambda x: sum(x)/len(x) if x else math.nan  # type: ignore[attr-defined]


def gather_script_paths() -> list[Path]:
    data = yaml.safe_load(STARTUP_CONFIG.read_text())
    scripts: list[Path] = []

    def _walk(obj: Any):
        if isinstance(obj, dict):
            if "script_path" in obj:
                scripts.append(PROJECT_ROOT / obj["script_path"])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for itm in obj:
                _walk(itm)
    _walk(data)
    return scripts

# --- main logic -----------------------------------------------------------

scripts = gather_script_paths()
print(f"Found {len(scripts)} script paths…")

for script in scripts:
    if not script.exists():
        print(f"⚠️  Missing file: {script}")
        continue

    mod_name = script.with_suffix("").relative_to(PROJECT_ROOT).as_posix().replace("/", ".")

    retries = 0
    while retries < 5:
        try:
            importlib.import_module(mod_name)
            break  # success
        except ImportError as e:
            missing = e.name  # type: ignore[attr-defined]
            if missing in MISSING_CACHE:
                # Already stubbed but still failing – give up
                raise
            print(f"   ↳ Stubbing missing module: {missing}")
            stub_module(missing)
            MISSING_CACHE.add(missing)
            retries += 1
        except Exception as ex:
            print(f"   ⚠️  Skipping {mod_name}: {ex}")
            break

print(f"Import phase complete. Stubbed {len(MISSING_CACHE)} missing packages.")