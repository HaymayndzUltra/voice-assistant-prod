#!/usr/bin/env python3
import os
import sys
import socket
import time
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

try:
	import yaml  # type: ignore
except Exception:
	print("Requires PyYAML. Install with: pip install PyYAML", file=sys.stderr)
	sys.exit(2)

YAML_PATH = Path("pc2_code/config/startup_config.yaml")
PORT_OFFSET = int(os.getenv("PORT_OFFSET", "0") or 0)


def parse_ports(node: Any) -> List[int]:
	ports: List[int] = []
	if isinstance(node, dict):
		for k, v in node.items():
			if k == "health_check_port":
				ports.append(evaluate_port_value(v))
			else:
				ports.extend(parse_ports(v))
	elif isinstance(node, list):
		for item in node:
			ports.extend(parse_ports(item))
	return ports


def evaluate_port_value(value: Any) -> int:
	if isinstance(value, int):
		return value
	if isinstance(value, str):
		m = re.match(r"\s*\$\{PORT_OFFSET\}\s*\+\s*(\d+)\s*", value)
		if m:
			return PORT_OFFSET + int(m.group(1))
		try:
			return int(value)
		except ValueError:
			pass
	raise ValueError(f"Unrecognized port value: {value!r}")


def check_port(port: int, host: str = "127.0.0.1", path: str = "/health", timeout_seconds: float = 1.5) -> Tuple[int, float]:
	url = f"http://{host}:{port}{path}"
	req = Request(url, method="GET")
	start = time.monotonic()
	try:
		with urlopen(req, timeout=timeout_seconds) as resp:
			return resp.getcode(), (time.monotonic() - start)
	except (HTTPError, URLError, socket.timeout):
		return 0, (time.monotonic() - start)


def run_validation(stage_name: Optional[str] = None) -> int:
	if not YAML_PATH.exists():
		print(f"Missing {YAML_PATH}", file=sys.stderr)
		return 2
	with open(YAML_PATH, "r") as f:
		cfg = yaml.safe_load(f)
	ports = sorted(set(parse_ports(cfg)))
	ok = 0
	results = []
	for p in ports:
		status, latency = check_port(p)
		results.append({"port": p, "status": status, "latency_ms": int(latency * 1000)})
		if status == 200:
			ok += 1
	print(json.dumps({"stage": stage_name or "all", "total": len(ports), "ok": ok, "results": results}, indent=2))
	return 0 if ok > 0 else 1