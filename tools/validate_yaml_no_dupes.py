#!/usr/bin/env python3
import sys, glob
from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

yaml = YAML(typ='rt')  # round-trip to detect duplicate keys
yaml.allow_duplicate_keys = False

TARGETS = [
  "main_pc_code/config/**/*.yaml",
  "pc2_code/config/**/*.yaml",
  "config/**/*.yaml",
  "docker-compose*.y*ml",
]

def main():
  errors = 0
  for pattern in TARGETS:
    for path in glob.glob(pattern, recursive=True):
      try:
        with open(path, 'r', encoding='utf-8') as f:
          yaml.load(f)
      except DuplicateKeyError as e:
        print(f"[DUPE-KEY] {path}: {e}")
        errors += 1
      except Exception as e:
        print(f"[YAML-ERROR] {path}: {e}")
        errors += 1
  if errors:
    print(f"FAIL: Found {errors} YAML issues")
    sys.exit(1)
  print("OK: No duplicate YAML keys detected")

if __name__ == "__main__":
  main()