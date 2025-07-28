#!/usr/bin/env bash
# Run port collision detection script as part of CI
set -euo pipefail

python main_pc_code/check_port_conflicts.py
