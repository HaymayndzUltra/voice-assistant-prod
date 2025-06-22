#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
System Configuration
This module provides system configuration values
"""

# Default configuration
system_config = {
    "main_pc_agents": [
        {
            "name": "coordinator",
            "host": "localhost",
            "port": 5555,
            "required": True
        },
        {
            "name": "task_router",
            "host": "localhost",
            "port": 8570,
            "required": True
        },
        {
            "name": "health_monitor",
            "host": "localhost",
            "port": 5584,
            "required": True
        }
    ],
    "pc2_agents": [
        {
            "name": "enhanced_model_router",
            "host": "192.168.1.128",
            "port": 5598,
            "required": True
        },
        {
            "name": "consolidated_translator",
            "host": "192.168.1.128",
            "port": 5563,
            "required": True
        }
    ],
    "zmq": {
        "model_manager_port": 5556,
        "task_router_port": 8570,
        "health_monitor_port": 5584
    },
    "health_check_interval": 30,
    "vram": {
        "vram_budget_percentage": 80,
        "vram_budget_mb": 4096,
        "idle_unload_timeout_seconds": 300,
        "memory_check_interval": 5,
        "min_vram_mb": 512,
        "max_models_in_memory": 3
    }
} 