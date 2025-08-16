#!/usr/bin/env python3
import sys
import time
import socket
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def check_health(host: str, port: int, path: str = "/health", timeout_seconds: float = 2.0) -> int:
	url = f"http://{host}:{port}{path}"
	req = Request(url, method="GET")
	start_monotonic = time.monotonic()
	try:
		with urlopen(req, timeout=timeout_seconds) as resp:
			status = resp.getcode()
			latency_ms = int((time.monotonic() - start_monotonic) * 1000)
			print(f"OK {host}:{port}{path} status={status} latency_ms={latency_ms}")
			return 0 if status == 200 else 1
	except HTTPError as e:
		print(f"HTTP_ERROR {host}:{port}{path} status={e.code}")
		return 1
	except (URLError, socket.timeout) as e:
		print(f"CONNECTION_ERROR {host}:{port}{path} error={e}")
		return 1


def main(argv: list[str]) -> int:
	# Usage: python3 cli_health_check.py <serviceName> <port> [path] [host]
	if len(argv) < 3:
		print("Usage: python3 cli_health_check.py <serviceName> <port> [path] [host]", file=sys.stderr)
		return 2
	service_name = argv[1]
	try:
		port = int(argv[2])
	except ValueError:
		print("Port must be an integer", file=sys.stderr)
		return 2
	path = argv[3] if len(argv) >= 4 else "/health"
	host = argv[4] if len(argv) >= 5 else "127.0.0.1"
	print(f"Checking {service_name} at {host}:{port}{path} ...")
	return check_health(host, port, path)


if __name__ == "__main__":
	sys.exit(main(sys.argv))
