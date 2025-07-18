#!/usr/bin/env python3
"""
Planning Orchestrator - Unified Planning and Task Management Service

Consolidates ModelOrchestrator (7010) and GoalManager (7005) into a single service.
Provides goal lifecycle management, task classification, and execution coordination.
"""

import os
import sys
import time
import logging
import threading
import json
import uuid
import heapq
import subprocess
import tempfile
import pickle
import psutil
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import zmq

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Common imports
from common.core.base_agent import BaseAgent
from common.utils.data_models import TaskDefinition, TaskResult, TaskStatus, ErrorSeverity

# Import path management
from common.utils.path_env import get_path, join_path, get_file_path, get_main_pc_code

# Configuration
from main_pc_code.utils.config_loader import load_config

# Optional imports with fallback
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence_transformers not available. Using keyword classification only.")

# Configuration
config = load_config()
logger = logging.getLogger('PlanningOrchestrator')

# Constants
DEFAULT_PORT = config.get('planning_orchestrator', {}).get('port', 7021)
HEALTH_CHECK_PORT = config.get('planning_orchestrator', {}).get('health_check_port', 7121)
ZMQ_REQUEST_TIMEOUT = config.get('zmq_request_timeout', 30000)
MAX_REFINEMENT_ITERATIONS = config.get('max_refinement_iterations', 3)
EMBEDDING_MODEL_NAME = config.get('embedding_model', "all-MiniLM-L6-v2")
METRICS_LOG_INTERVAL = config.get('metrics_log_interval', 60)
METRICS_SAVE_INTERVAL = config.get('metrics_save_interval', 300)

# Error Bus Configuration
ERROR_BUS_PORT = config.get('error_bus_port', 7150)
ERROR_BUS_HOST = os.environ.get('PC2_IP', config.get('pc2_ip', '192.168.100.17'))

# Memory Hub Configuration
MEMORY_HUB_PORT = config.get('memory_hub_port', 7010)
MEMORY_HUB_HOST = os.environ.get('PC2_IP', config.get('pc2_ip', '192.168.100.17')) 