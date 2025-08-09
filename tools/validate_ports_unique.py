#!/usr/bin/env python3
import sys, os, re, glob, yaml
from collections import defaultdict

PATTERNS = [
  "main_pc_code/config/**/*.yaml",
  "pc2_code/config/**/*.yaml",
  "config/**/*.yaml",
  "docker-compose*.y*ml",
]

def normalize_port(v):
  if isinstance(v, int):
    return v
  if isinstance(v, str):
    m = re.search(r"\$\{PORT_OFFSET\}\+(\d+)", v)
    if m:
      return int(m.group(1))
    m2 = re.search(r"(\d+)", v)
    if m2:
      return int(m2.group(1))
  return None

def scan_file(path):
  with open(path, 'r', encoding='utf-8') as f:
    try:
      doc = yaml.safe_load(f) or {}
    except Exception as e:
      return [(path, f"Parse error: {e}")]
  issues = []
  seen = defaultdict(list)  # base_port -> [(agent, field)]
  def walk(node, agent_hint=None):
    if isinstance(node, dict):
      agent_name = node.get('name') or node.get('agent') or agent_hint
      for k,v in node.items():
        if k in ('port','health_check_port'):
          p = normalize_port(v)
          if p is not None:
            seen[p].append((agent_name or '?', k))
        else:
          walk(v, agent_name)
    elif isinstance(node, list):
      for it in node:
        walk(it, agent_hint)
  walk(doc)
  for p, uses in seen.items():
    if len(uses) > 1:
      issues.append((path, f"Port-base {p} reused: {uses}"))
  return issues

def main():
  errors=0
  for pattern in PATTERNS:
    for path in glob.glob(pattern, recursive=True):
      for (p, msg) in scan_file(path):
        print(f"[PORT-COLLISION] {p}: {msg}")
        errors += 1
  if errors:
    print(f"FAIL: Found {errors} port uniqueness issues")
    sys.exit(1)
  print("OK: No port-base collisions detected")

if __name__ == "__main__":
  main()