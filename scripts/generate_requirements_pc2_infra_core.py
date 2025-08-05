#!/usr/bin/env python3
"""generate_requirements_pc2_infra_core.py
Static-analysis helper that scans Python files under pc2_code/agents and
phase1_implementation/consolidated_agents/observability_hub for top-level
`import` statements, resolves them to PyPI package names (best-effort), and
prints a sorted requirements list you can redirect into a requirements.txt.

Usage:
    python scripts/generate_requirements_pc2_infra_core.py > docker/pc2_infra_core/requirements.auto.txt
"""
from __future__ import annotations
import ast
import pathlib
import sys
from typing import Set, Dict

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENT_DIRS = [
    PROJECT_ROOT / "pc2_code" / "agents",
    PROJECT_ROOT / "phase1_implementation" / "consolidated_agents" / "observability_hub" / "backup_observability_hub",
]
# Basic stdlib set for quick exclusion (could be extended)
STDLIB = {
    "abc","argparse","asyncio","base64","collections","concurrent","contextlib","copy","csv","datetime","functools","hashlib","heapq","html","http","io","itertools","json","logging","math","numbers","os","pathlib","pickle","platform","plistlib","queue","random","re","selectors","shlex","signal","socket","statistics","string","struct","subprocess","sys","threading","time","types","typing","uuid","warnings","weakref","zipfile","importlib","dataclasses","traceback","atexit","enum","textwrap","multiprocessing","pprint","fcntl","resource","signal","tempfile","inspect","tkinter","statistics","secrets","typing_extensions","ssl","email","urllib","xml","gzip","bz2","lzma","plistlib","selectors",
}
# Mapping for known alias-to-package differences
ALIAS_MAP: Dict[str, str] = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "zmq": "pyzmq",
}

def extract_imports(path: pathlib.Path) -> Set[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))
    modules: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for n in node.names:
                    modules.add(n.name.split(".")[0])
            else:
                if node.module:
                    modules.add(node.module.split(".")[0])
    return modules


def main():
    all_imports: Set[str] = set()
    for directory in AGENT_DIRS:
        for py in directory.rglob("*.py"):
            all_imports.update(extract_imports(py))
    # Filter stdlib & internal modules
    ext_deps = {
        ALIAS_MAP.get(m, m) for m in all_imports
        if m not in STDLIB and not m.startswith(("pc2_", "common", "phase1_"))
    }
    # Manual extras always needed
    ext_deps.update({
        "fastapi", "uvicorn", "redis", "nats-py", "prometheus-client", "torch", "psutil", "aiohttp", "asyncio-mqtt", "pydantic", "python-dotenv", "PyJWT", "requests", "httpx", "aiofiles", "starlette", "numpy", "scipy",
    })
    for pkg in sorted(ext_deps):
        print(pkg)

if __name__ == "__main__":
    main()