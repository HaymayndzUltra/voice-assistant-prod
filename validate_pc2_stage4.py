#!/usr/bin/env python3
"""
Stage 4: PC2 Post-Sync Continuous Validation (wrapper)
Probes all pc2 health_check_port entries via HTTP /health.
"""

import sys
from validate_pc2_stage_common import run_validation


if __name__ == "__main__":
	sys.exit(run_validation(stage_name="stage4"))
