#!/usr/bin/env python3
"""
Main-PC Health-Suite: Launches agents from startup_config.yaml then polls
their health-check endpoints to ensure they are running.

Usage:
    python mainpc_health_suite.py --startup main_pc_code/config/startup_config.yaml
    python mainpc_health_suite.py --startup ... --dry-run
"""
import argparse, subprocess, sys, time, yaml, os, signal, socket
from contextlib import closing
from threading import Thread

DEFAULT_TIMEOUT = 30            # seconds per agent
POLL_INTERVAL   = 1.0           # seconds

def port_open(host: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def launch_agent(agent_cfg, dry_run=False):
    env = os.environ.copy()
    env.update(agent_cfg.get("env_vars", {}))
    cmd = [sys.executable, agent_cfg["script_path"]]
    if dry_run or env.get("DEBUG_MODE", "false").lower() == "true":
        cmd.append("--dry-run")
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    return proc

def health_wait(agent_cfg):
    host = agent_cfg.get("host", "0.0.0.0")
    port = agent_cfg["port"]
    deadline = time.time() + DEFAULT_TIMEOUT
    while time.time() < deadline:
        if port_open(host, port):
            return True
        time.sleep(POLL_INTERVAL)
    return False

def stream_logs(name, proc):
    for line in proc.stdout:
        print(f"[{name}] {line.rstrip()}")

def main(startup_yaml, dry_run=False):
    with open(startup_yaml, "r") as f:
        config = yaml.safe_load(f)
    agent_sections = [k for k in config if k not in
                      ("environment", "resource_limits", "volumes",
                       "health_checks", "network")]
    agents = []
    for section in agent_sections:
        for agent in config[section]:
            if agent.get("required", False):
                agents.append(agent)

    procs = {}
    try:
        for a in agents:
            proc = launch_agent(a, dry_run)
            procs[a["name"]] = proc
            Thread(target=stream_logs, args=(a["name"], proc),
                   daemon=True).start()

        results = {}
        for a in agents:
            ok = health_wait(a)
            results[a["name"]] = ok
            status = "✅" if ok else "❌"
            print(f"{status} {a['name']} @ {a['host']}:{a['port']}")

        failed = [k for k, v in results.items() if not v]
        print("\nSUMMARY:")
        if failed:
            for f in failed:
                print(f"❌ {f} did not pass health-check.")
            sys.exit(len(failed))
        print("🎉 All agents healthy!")
    finally:
        for proc in procs.values():
            try:
                proc.send_signal(signal.SIGINT)
            except Exception:
                pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--startup", required=True,
                    help="Path to startup_config.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="Launch agents with --dry-run/DEBUG_MODE")
    args = ap.parse_args()
    main(args.startup, args.dry_run) 