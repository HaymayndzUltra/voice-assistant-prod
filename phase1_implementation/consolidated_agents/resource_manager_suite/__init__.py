#!/usr/bin/env python3
"""
ResourceManagerSuite - Phase 1 Consolidated Service
Port 7001 - MainPC

Consolidates:
- ResourceManager
- TaskScheduler  
- AsyncProcessor
- VRAMOptimizerAgent
"""

from .resource_manager_suite import ResourceManagerSuite

__all__ = ['ResourceManagerSuite'] 