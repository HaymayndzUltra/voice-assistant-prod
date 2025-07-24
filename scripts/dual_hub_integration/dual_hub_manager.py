
# Dual-Hub Integration Module
# Auto-generated for Phase 2 Task 2D Pilot Agent Migration

import asyncio
import json
import time
import logging
from typing import Dict, Optional, Any
import aiohttp
import nats

class DualHubManager:
    """Manages dual-hub connectivity with intelligent failover"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.primary_hub = config["dual_hub_config"]["primary_hub"]["url"]
        self.fallback_hub = config["dual_hub_config"]["fallback_hub"]["url"]
        self.nats_url = config["dual_hub_config"]["nats_integration"]["primary_nats_url"]
        self.current_hub = self.primary_hub
        self.failover_count = 0
        self.logger = logging.getLogger(f"DualHubManager_{self.__class__.__name__}")
        
    async def publish_metrics(self, metrics: Dict) -> bool:
        """Publish metrics to current hub with failover logic"""
        try:
            # Try current hub first
            success = await self._publish_to_hub(self.current_hub, metrics)
            if success:
                return True
            
            # Failover to other hub
            other_hub = self.fallback_hub if self.current_hub == self.primary_hub else self.primary_hub
            self.logger.warning(f"Failing over from {self.current_hub} to {other_hub}")
            
            success = await self._publish_to_hub(other_hub, metrics)
            if success:
                self.current_hub = other_hub
                self.failover_count += 1
                return True
            
            self.logger.error("Both hubs failed, metrics lost")
            return False
            
        except Exception as e:
            self.logger.error(f"Metrics publishing failed: {str(e)}")
            return False
    
    async def _publish_to_hub(self, hub_url: str, metrics: Dict) -> bool:
        """Publish metrics to specific hub"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(f"{hub_url}/metrics", json=metrics) as response:
                    return response.status == 200
        except:
            return False
    
    async def publish_to_nats(self, subject: str, data: Dict) -> bool:
        """Publish data to NATS stream"""
        try:
            nc = await nats.connect(self.nats_url)
            await nc.publish(subject, json.dumps(data).encode())
            await nc.close()
            return True
        except Exception as e:
            self.logger.error(f"NATS publishing failed: {str(e)}")
            return False
    
    def get_current_hub(self) -> str:
        """Get currently active hub"""
        return self.current_hub
    
    def get_failover_stats(self) -> Dict:
        """Get failover statistics"""
        return {
            "current_hub": self.current_hub,
            "failover_count": self.failover_count,
            "primary_hub": self.primary_hub,
            "fallback_hub": self.fallback_hub
        }
