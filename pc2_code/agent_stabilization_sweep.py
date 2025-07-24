#!/usr/bin/env python
from __future__ import annotations
"""
Agent Stabilization Sweep

Launch every Python agent script in the `agents` directory sequentially and verify
that each can start up without crashing for at least 10 seconds.

If any agent fails (throws an exception, exits with a non-zero status, or terminates
in under 10 seconds), the sweep stops immediately and prints the full stderr
traceback for the failing agent, then exits with status 1.

Otherwise, prints a SUCCESS message and exits with status 0.

This utility makes no assumptions about individual CLI arguments. It tries three
invocation patterns in order:
  1. python <script> --server   (commonly used in service agents)
  2. python <script> --test     (quick test/health-check mode, if supported)
  3. python <script>            (default behaviour)

Environment variables identifying the PC role are injected so that agents relying
on them still work during the sweep.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

# --- Configuration ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
AGENTS_DIR = PROJECT_ROOT / "agents"

INVOCATION_PATTERNS: List[str] = [
    "{python} \"{script}\" --server",
    "{python} \"{script}\" --test",
    "{python} \"{script}\"",
]

# Seconds an agent must remain alive to be considered healthy
RUN_DURATION_SEC = 10

# Additional environment so that agents pick up correct context
BASE_ENV = dict(os.environ,
                VOICE_ASSISTANT_PC_ROLE="pc2",
                MACHINE_ROLE="PC2")

# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, flush=True)


def run_agent(script_path: Path) -> bool:
    """Run *script_path* using each invocation pattern until one passes.

    Returns True if the script survives for RUN_DURATION_SEC seconds,
    otherwise False.
    """
    for pattern in INVOCATION_PATTERNS:
        cmd = pattern.format(python=sys.executable, script=str(script_path))
        log(f"\n[TEST] Launching {script_path.relative_to(AGENTS_DIR.parent)} with: {cmd}")

        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=BASE_ENV,
                text=True,
            )

            start_time = time.time()
            # Poll until RUN_DURATION_SEC or process exit
            while True:
                if process.poll() is not None:
                    # Process exited – gather output and decide success
                    stdout, stderr = process.communicate()
                    runtime = time.time() - start_time
                    if process.returncode == 0 and runtime >= RUN_DURATION_SEC:
                        log(f"[PASS] {script_path.name} exited cleanly after {runtime:.1f}s")
                        return True
                    else:
                        log(f"[FAIL] Exit code {process.returncode} after {runtime:.1f}s. Stderr:\n{stderr}")
                        break  # Try next invocation pattern
                else:
                    runtime = time.time() - start_time
                    if runtime >= RUN_DURATION_SEC:
                        # Healthy – terminate politely
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        log(f"[PASS] {script_path.name} ran for {RUN_DURATION_SEC}s without crashing")
                        return True
                    time.sleep(0.5)
        except Exception as exc:
            log(f"[ERROR] Exception while launching {script_path.name}: {exc}")

    # All invocation patterns failed
    return False


def main() -> None:
    if not AGENTS_DIR.exists():
        print(f"Agents directory not found: {AGENTS_DIR}", file=sys.stderr)
        sys.exit(1)

    # Collect all *.py files (recursively) except __init__.py
    scripts = [p for p in AGENTS_DIR.rglob("*.py") if p.name != "__init__.py"]
    scripts.sort()

    log(f"Discovered {len(scripts)} agent scripts under {AGENTS_DIR}\n")

    for script in scripts:
        success = run_agent(script)
        if not success:
            log("\n==== STABILIZATION SWEEP FAILED ====\n")
            log(f"Agent failed: {script.relative_to(AGENTS_DIR.parent)}")
            sys.exit(1)

    log("\nSUCCESS: Comprehensive stabilization sweep complete. All agents validated.")
    sys.exit(0)


if __name__ == "__main__":
    main()
