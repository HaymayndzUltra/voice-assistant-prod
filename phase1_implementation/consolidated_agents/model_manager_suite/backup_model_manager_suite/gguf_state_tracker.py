#!/usr/bin/env python3
"""
GGUFStateTracker - State Management for GGUF Models
==================================================

This module provides state tracking functionality for GGUF models,
including VRAM management, model status tracking, and idle detection.
Originally part of GGUFModelManager, now extracted as a standalone component.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("GGUFStateTracker")

class GGUFStateTracker:
    """
    State tracker for GGUF models
    
    Tracks:
    - Loaded models and their VRAM usage
    - Model last used timestamps
    - VRAM budget and availability
    - Idle model detection
    """
    
    def __init__(self, port: int = 5576, **kwargs):
        """Initialize the GGUF state tracker
        
        Args:
            port: Port for the state tracker service (unused in consolidated version)
            **kwargs: Additional arguments
        """
        self.port = port
        
        # Model state tracking
        self.loaded_models = {}  # {model_id: vram_mb}
        self.model_last_used = {}  # {model_id: timestamp}
        self.model_status = {}  # {model_id: status}
        
        # VRAM management
        self.total_vram_mb = 0
        self.used_vram_mb = 0
        self.vram_budget_percentage = 80
        self.vram_budget_mb = 0
        
        # Threading
        self.lock = threading.RLock()
        
        # Initialize VRAM tracking
        self._init_vram_tracking()
        
        logger.info(f"GGUFStateTracker initialized on port {port}")
    
    def _init_vram_tracking(self):
        """Initialize VRAM tracking"""
        try:
            import torch
            if torch.cuda.is_available():
                self.total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
                self.vram_budget_mb = self.total_vram_mb * (self.vram_budget_percentage / 100)
                logger.info(f"VRAM tracking initialized: {self.total_vram_mb:.0f}MB total, {self.vram_budget_mb:.0f}MB budget")
            else:
                logger.warning("CUDA not available, VRAM tracking disabled")
                self.total_vram_mb = 0
                self.vram_budget_mb = 0
        except Exception as e:
            logger.error(f"Error initializing VRAM tracking: {e}")
            self.total_vram_mb = 0
            self.vram_budget_mb = 0
    
    def mark_model_loaded(self, model_id: str, vram_mb: float) -> None:
        """Mark a model as loaded with its VRAM usage
        
        Args:
            model_id: ID of the loaded model
            vram_mb: VRAM usage in MB
        """
        with self.lock:
            self.loaded_models[model_id] = vram_mb
            self.model_last_used[model_id] = time.time()
            self.model_status[model_id] = 'loaded'
            self.used_vram_mb += vram_mb
            
            logger.info(f"Model {model_id} marked as loaded (VRAM: {vram_mb:.1f}MB)")
    
    def mark_model_unloaded(self, model_id: str) -> None:
        """Mark a model as unloaded
        
        Args:
            model_id: ID of the unloaded model
        """
        with self.lock:
            if model_id in self.loaded_models:
                vram_mb = self.loaded_models[model_id]
                self.used_vram_mb -= vram_mb
                del self.loaded_models[model_id]
                
                if model_id in self.model_last_used:
                    del self.model_last_used[model_id]
                
                self.model_status[model_id] = 'unloaded'
                
                logger.info(f"Model {model_id} marked as unloaded (freed {vram_mb:.1f}MB VRAM)")
    
    def can_accommodate_model(self, required_vram_mb: float) -> bool:
        """Check if we can accommodate a model with given VRAM requirements
        
        Args:
            required_vram_mb: Required VRAM in MB
            
        Returns:
            bool: True if model can be accommodated
        """
        with self.lock:
            available_vram = self.vram_budget_mb - self.used_vram_mb
            can_accommodate = available_vram >= required_vram_mb
            
            logger.debug(f"VRAM check: required={required_vram_mb:.1f}MB, "
                        f"available={available_vram:.1f}MB, can_accommodate={can_accommodate}")
            
            return can_accommodate
    
    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """Get status of a specific model
        
        Args:
            model_id: ID of the model
            
        Returns:
            Dict containing model status information
        """
        with self.lock:
            if model_id not in self.model_status:
                return {
                    'status': 'unknown',
                    'loaded': False,
                    'vram_usage': 0,
                    'last_used': None
                }
            
            status = self.model_status[model_id]
            loaded = model_id in self.loaded_models
            vram_usage = self.loaded_models.get(model_id, 0)
            last_used = self.model_last_used.get(model_id)
            
            return {
                'status': status,
                'loaded': loaded,
                'vram_usage': vram_usage,
                'last_used': last_used
            }
    
    def get_all_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tracked models
        
        Returns:
            Dict mapping model_id to status information
        """
        with self.lock:
            all_status = {}
            for model_id in self.model_status:
                all_status[model_id] = self.get_model_status(model_id)
            return all_status
    
    def get_vram_usage(self) -> Dict[str, float]:
        """Get current VRAM usage statistics
        
        Returns:
            Dict containing VRAM usage information
        """
        with self.lock:
            return {
                'total_vram_mb': self.total_vram_mb,
                'used_vram_mb': self.used_vram_mb,
                'available_vram_mb': self.vram_budget_mb - self.used_vram_mb,
                'budget_vram_mb': self.vram_budget_mb,
                'budget_percentage': self.vram_budget_percentage
            }
    
    def check_idle_models(self, idle_timeout_seconds: int = 300) -> List[str]:
        """Check for idle models that should be unloaded
        
        Args:
            idle_timeout_seconds: Timeout in seconds for idle detection
            
        Returns:
            List of model IDs that are idle
        """
        with self.lock:
            current_time = time.time()
            idle_models = []
            
            for model_id, last_used in self.model_last_used.items():
                if current_time - last_used > idle_timeout_seconds:
                    idle_models.append(model_id)
            
            if idle_models:
                logger.info(f"Found {len(idle_models)} idle models: {idle_models}")
            
            return idle_models
    
    def update_model_usage(self, model_id: str) -> None:
        """Update the last used timestamp for a model
        
        Args:
            model_id: ID of the model being used
        """
        with self.lock:
            if model_id in self.loaded_models:
                self.model_last_used[model_id] = time.time()
                logger.debug(f"Updated usage timestamp for model {model_id}")
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models
        
        Returns:
            List of loaded model IDs
        """
        with self.lock:
            return list(self.loaded_models.keys())
    
    def get_model_vram_usage(self, model_id: str) -> float:
        """Get VRAM usage for a specific model
        
        Args:
            model_id: ID of the model
            
        Returns:
            VRAM usage in MB, 0 if model not loaded
        """
        with self.lock:
            return self.loaded_models.get(model_id, 0)
    
    def set_vram_budget(self, budget_percentage: float) -> None:
        """Set VRAM budget percentage
        
        Args:
            budget_percentage: Budget percentage (0-100)
        """
        with self.lock:
            if 0 <= budget_percentage <= 100:
                self.vram_budget_percentage = budget_percentage
                self.vram_budget_mb = self.total_vram_mb * (budget_percentage / 100)
                logger.info(f"VRAM budget set to {budget_percentage}% ({self.vram_budget_mb:.0f}MB)")
            else:
                logger.error(f"Invalid VRAM budget percentage: {budget_percentage}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics
        
        Returns:
            Dict containing comprehensive statistics
        """
        with self.lock:
            return {
                'total_models': len(self.model_status),
                'loaded_models': len(self.loaded_models),
                'vram_usage': self.get_vram_usage(),
                'model_status_summary': {
                    'loaded': len([s for s in self.model_status.values() if s == 'loaded']),
                    'unloaded': len([s for s in self.model_status.values() if s == 'unloaded']),
                    'unknown': len([s for s in self.model_status.values() if s == 'unknown'])
                }
            } 