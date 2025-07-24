#!/usr/bin/env python3
"""run_mainpc_agents_smoketest.py
Lightweight smoke-test that imports and instantiates each agent defined in
main_pc_code/config/startup_config.yaml.  For safety, the agents are
created with `testing=True` flag when such constructor arg exists, and the
`run()` method is *not* invoked; this avoids heavy GPU/model loading while
still catching import errors, missing dependencies, and constructor-time
crashes.

Outputs a summary table and exits non-zero if any instantiation fails.
"""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, Any

import yaml
import os

# Ensure project root is on PYTHONPATH so "main_pc_code" package resolves
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

STARTUP_CONFIG = Path("main_pc_code/config/startup_config.yaml")

FAILED: dict[str, str] = {}


def gather_agent_specs() -> list[tuple[str, Path]]:
    data = yaml.safe_load(STARTUP_CONFIG.read_text())
    specs: list[tuple[str, Path]] = []

    def _walk(obj: Any):
        if isinstance(obj, dict):
            if "script_path" in obj:
                specs.append((obj.get("name") or '', Path(obj["script_path"])))
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for itm in obj:
                _walk(itm)

    _walk(data)
    return specs


def import_and_instantiate(script_path: Path):
    module_name = script_path.with_suffix("").as_posix().replace("/", ".")
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        FAILED[module_name] = f"import error: {e}"
        return

    # Heuristic: find first class subclassing BaseAgent in module
    from common.core.base_agent import BaseAgent  # local import

    agent_cls = None
    for name, obj in vars(mod).items():
        if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
            agent_cls = obj
            break

    if agent_cls is None:
        FAILED[module_name] = "no Agent class found"
        return

    try:
        # Some agents accept kwargs; pass testing flag if present.
        kwargs = {}
        if "testing" in inspect.signature(agent_cls).parameters:
            kwargs["testing"] = True
        agent = agent_cls(**kwargs)  # noqa: F841 – instantiation only
    except Exception as e:
        FAILED[module_name] = f"constructor error: {e}"


def main():
    specs = gather_agent_specs()
    for _, path in specs:
        if not path.exists():
            FAILED[str(path)] = "file missing"
            continue
        import_and_instantiate(path)

    ok = len(specs) - len(FAILED)
    print(f"Instantiated {ok}/{len(specs)} agents successfully")
    if FAILED:
        print("Failures:")
        for k, v in FAILED.items():
            print(f" - {k}: {v}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    # Provide lightweight stub modules for heavy deps not installed in CI
    import types
    for _mod in [
        "psutil", "torch", "numpy", "sounddevice",
        "networkx", "transformers", "pydantic", "requests", "noisereduce"
    ]:
        if _mod not in sys.modules:
            sys.modules[_mod] = types.ModuleType(_mod)

    # Special stub for redis
    if "redis" not in sys.modules:
        redis_stub = types.ModuleType("redis")
        class _Redis:
            def __init__(self, *a, **kw): pass
            def ping(self): return True
            def from_url(url, *a, **kw):
                return _Redis()
        redis_stub.Redis = _Redis
        redis_stub.from_url = staticmethod(_Redis.from_url)
        sys.modules["redis"] = redis_stub

    # Special stub for zmq
    if "zmq" not in sys.modules:
        zmq_stub = types.ModuleType("zmq")
        zmq_stub.REQ = 0
        zmq_stub.REP = 1
        zmq_stub.PUB = 2
        zmq_stub.SUB = 3
        class _Context:
            def socket(self, *a):
                class _Sock:
                    def setsockopt(self, *a, **k): pass
                    def bind(self, *a): pass
                    def connect(self, *a): pass
                    def send_json(self, *a, **k): pass
                    def recv_json(self, *a, **k): return {}
                    def close(self): pass
                return _Sock()
            @staticmethod
            def instance(): return _Context()
        zmq_stub.Context = _Context
        sys.modules["zmq"] = zmq_stub
        # minimal asyncio submodule
        zmq_async = types.ModuleType("zmq.asyncio")
        zmq_async.Context = _Context
        sys.modules["zmq.asyncio"] = zmq_async

    main()