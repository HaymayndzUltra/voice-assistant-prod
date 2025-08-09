#!/usr/bin/env python3
import sys, glob, os
from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

yaml = YAML(typ='rt')  # round-trip to detect duplicate keys
yaml.allow_duplicate_keys = False

TARGETS = [
  "main_pc_code/config/**/*.yaml",
  "pc2_code/config/**/*.yaml",
  "config/**/*.yaml",
  "**/*.yml",
  "**/*.yaml",
]

SKIP_DIR_PREFIXES = (
  os.path.normpath("k8s/"),
  os.path.normpath("common/service_mesh/k8s/"),
  os.path.normpath("tests/goss/"),
)
COMPOSE_BASENAMES = {"compose.yaml", "compose.yml"}

def should_skip(path: str) -> bool:
  norm = os.path.normpath(path)
  base = os.path.basename(norm)
  # Skip docker compose files
  if base.startswith("docker-compose") or base in COMPOSE_BASENAMES:
    return True
  # Skip unused k8s and goss dirs
  for p in SKIP_DIR_PREFIXES:
    if norm.startswith(p) or (os.sep + p) in norm:
      return True
  return False

def validate_yaml(path: str) -> int:
  """Return number of issues found (0 if ok). Supports multi-document YAML."""
  issues = 0
  try:
    with open(path, 'r', encoding='utf-8') as f:
      for _ in yaml.load_all(f):
        pass
  except DuplicateKeyError as e:
    print(f"[DUPE-KEY] {path}: {e}")
    issues += 1
  except Exception as e:
    print(f"[YAML-ERROR] {path}: {e}")
    issues += 1
  return issues

def main():
  errors = 0
  for pattern in TARGETS:
    for path in glob.glob(pattern, recursive=True):
      if should_skip(path):
        continue
      errors += validate_yaml(path)
  if errors:
    print(f"FAIL: Found {errors} YAML issues")
    sys.exit(1)
  print("OK: No YAML issues (compose/k8s/goss skipped; multi-doc supported)")

if __name__ == "__main__":
  main()