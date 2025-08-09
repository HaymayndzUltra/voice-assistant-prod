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

SKIP_PATTERNS = [
  os.path.normpath("k8s"),
  os.path.normpath("common/service_mesh/k8s"),
  os.path.normpath("tests/goss"),
]

def is_compose_file(path: str) -> bool:
  base = os.path.basename(path)
  return base.startswith("docker-compose") or base in {"compose.yml", "compose.yaml"}

def should_skip_path(path: str) -> bool:
  norm = os.path.normpath(path)
  # Skip docker compose files and known unused infra dirs
  if is_compose_file(norm):
    return True
  return any(sp in norm for sp in SKIP_PATTERNS)

def validate_yaml(path: str) -> int:
  """Return number of issues found (0 if ok). Supports multi-document YAML."""
  issues = 0
  try:
    with open(path, 'r', encoding='utf-8') as f:
      # Iterate all documents; ruamel will raise DuplicateKeyError if dupes
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
      if should_skip_path(path):
        continue
      errors += validate_yaml(path)
  if errors:
    print(f"FAIL: Found {errors} YAML issues")
    sys.exit(1)
  print("OK: No duplicate YAML keys detected (compose/k8s/goss skipped; multi-doc supported)")

if __name__ == "__main__":
  main()