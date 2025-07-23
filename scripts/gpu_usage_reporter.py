#!/usr/bin/env python3
"""gpu_usage_reporter.py
Periodically reports GPU utilisation & memory to Prometheus Pushgateway (or stdout).
Requires GPUtil.
"""
import os
import time
import json
import argparse
from datetime import datetime

try:
    import GPUtil  # type: ignore
except ImportError:
    GPUtil = None


def collect_gpu_stats():
    if GPUtil is None:
        return []
    gpus = GPUtil.getGPUs()
    stats = []
    for g in gpus:
        stats.append({
            "id": g.id,
            "name": g.name,
            "load": round(g.load * 100, 1),
            "mem_used_mb": g.memoryUsed,
            "mem_total_mb": g.memoryTotal,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    return stats


def push_prometheus(stats, gateway):
    import requests
    body_lines = []
    for s in stats:
        labels = f'id="{s["id"]}",gpu="{s["name"].replace(" ", "_")}"'
        body_lines.append(f'gpu_load{{{labels}}} {s["load"]}')
        body_lines.append(f'gpu_mem_used_mb{{{labels}}} {s["mem_used_mb"]}')
    body = "\n".join(body_lines) + "\n"
    url = f"{gateway}/metrics/job/gpu_usage_reporter"
    requests.post(url, data=body, timeout=5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=30, help="Seconds between pushes")
    ap.add_argument("--gateway", help="Prometheus pushgateway URL (if omitted, prints to stdout)")
    args = ap.parse_args()
    if GPUtil is None:
        raise SystemExit("GPUtil not installed. pip install gputil")
    while True:
        stats = collect_gpu_stats()
        if args.gateway:
            try:
                push_prometheus(stats, args.gateway.rstrip("/"))
                print("Pushed", len(stats), "GPU metrics →", args.gateway)
            except Exception as e:
                print("Push failed:", e)
        else:
            print(json.dumps(stats, indent=2))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()