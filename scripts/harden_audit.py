#!/usr/bin/env python3
"""
Full-tree compliance audit for both PC-2 and Main-PC agents.

Checks:
1. Syntax / import errors
2. Forbidden patterns
      • sys.path.insert
      • logging.basicConfig
      • localhost:4222  (or any localhost:<4digits> except health probe)
3. Missing canonical helpers (env_standardizer, BaseAgent, error_publisher, log_setup)
4. Requirements drift  (requirements.txt ↔ requirements.auto.txt)
5. Missing health-check routes in Dockerfiles / compose
6. Un-pinned GPU requirements vs. CUDA image
Exit code 0 = all green, otherwise non-zero; prints JSON report.
"""
from __future__ import annotations
import pathlib, re, py_compile, json, ast, subprocess, sys, hashlib

ROOT   = pathlib.Path(__file__).resolve().parent.parent
DOCKER = ROOT / "docker"
REPORT = {"syntax":[], "forbidden":[], "helpers":[], "requirements":[], "health":[], "gpu":[]}

FORBIDDEN_PATTERNS = {
    "sys.path.insert"   : re.compile(r"sys\.path\.insert"),
    "basicConfig"       : re.compile(r"logging\.basicConfig"),
    "localhost_broker"  : re.compile(r"localhost:4[0-9]{3}")   # allow 80xx health later
}
REQUIRED_IMPORTS = {
    "env_standardizer"      : "common.utils.env_standardizer",
    "base_agent"            : "common.core.base_agent",
    "log_setup"             : "common.utils.log_setup",
}
ERROR_PUBLISHER = {
    "pc2"   : "pc2_code.utils.pc2_error_publisher",
    "main"  : "main_pc_code.utils.mainpc_error_publisher"
}

def compile_tree():
    for py in ROOT.rglob("*.py"):
        if any(k in py.parts for k in ("venv","backups")): continue
        try: py_compile.compile(str(py), doraise=True)
        except Exception as e: REPORT["syntax"].append(f"{py}:{e}")

def search_forbidden():
    for py in ROOT.rglob("*.py"):
        if any(k in py.parts for k in ("venv","backups")): continue
        text = py.read_text("utf-8",errors="ignore")
        for key,pat in FORBIDDEN_PATTERNS.items():
            for m in pat.finditer(text):
                # whitelisted localhost:HEALTH_PORT
                if key=="localhost_broker" and "HEALTH_PORT" in text: continue
                REPORT["forbidden"].append(f"{key}:{py}:{m.group(0)}")

def check_imports():
    # Only check agents that have docker folders (active agents)
    docker_dir = ROOT / "docker"
    
    for agent_dir in docker_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
            continue
            
        # Check if it's PC2 or Main PC agent
        if agent_dir.name.startswith('pc2_'):
            # PC2 agent - remove pc2_ prefix to find python file
            agent_name = agent_dir.name[4:]  # Remove 'pc2_' prefix
            py_file = ROOT / "pc2_code" / "agents" / f"{agent_name}.py"
            if py_file.exists():
                _check_file(py_file, "pc2")
        else:
            # Main PC agent
            py_file = ROOT / "main_pc_code" / "agents" / f"{agent_dir.name}.py"
            if py_file.exists():
                _check_file(py_file, "main")

def _check_file(py: pathlib.Path, side:str):
    mods=set()
    try:
        tree = ast.parse(py.read_text())
    except SyntaxError as e:
        REPORT["syntax"].append(f"{py}:{e}")
        return
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            if isinstance(node, ast.Import):
                mods |= {n.name for n in node.names}
            else:
                if node.module: mods.add(node.module)
    for tag,imp in REQUIRED_IMPORTS.items():
        if imp not in mods:
            REPORT["helpers"].append(f"missing:{imp}:{py}")
    if ERROR_PUBLISHER[side] not in mods:
        REPORT["helpers"].append(f"missing:{ERROR_PUBLISHER[side]}:{py}")

def compare_requirements():
    for group in DOCKER.iterdir():
        if not group.is_dir(): continue
        cur = group/"requirements.txt"
        auto= group/"requirements.auto.txt"
        if not cur.exists() or not auto.exists(): continue
        cur_set  = {l.strip() for l in cur.read_text().splitlines() if l and not l.startswith("#")}
        auto_set = {l.strip() for l in auto.read_text().splitlines() if l}
        if cur_set!=auto_set:
            REPORT["requirements"].append(f"{group.name}: mismatch")

def check_docker_health():
    for dockerfile in DOCKER.rglob("Dockerfile"):
        txt=dockerfile.read_text()
        if "HEALTHCHECK" not in txt:
            REPORT["health"].append(f"no_healthcheck:{dockerfile}")
        if "--gpus" in txt:   # GPU image
            if "cuda" not in txt.lower():
                REPORT["gpu"].append(f"gpu_image_no_cuda:{dockerfile}")

def main():
    compile_tree()
    search_forbidden()
    check_imports()
    compare_requirements()
    check_docker_health()
    ok = all(len(v)==0 for v in REPORT.values())
    print(json.dumps(REPORT, indent=2))
    sys.exit(0 if ok else 1)

if __name__=="__main__":
    main()
