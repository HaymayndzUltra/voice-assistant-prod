#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Cross-Machine Synchronization Service
Handles data sync between MainPC (RTX 4090) and PC2 (RTX 3060)
"""

import os
import time
import json
import redis
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SyncConfig:
    mainpc_host: str = get_service_ip("mainpc")
    pc2_host: str = get_service_ip("pc2")
    redis_port: int = 6379
    sync_interval: int = 300  # 5 minutes
    data_paths: list = None
    
    def __post_init__(self):
        if self.data_paths is None:
            self.data_paths = [
                "/app/data/shared",
                "/app/logs/critical",
                "/app/cache/models"
            ]

class CrossMachineSync:
    def __init__(self, config: SyncConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.redis_main = None
        self.redis_pc2 = None
        self.current_machine = self._detect_machine()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for sync service"""
        logger = configure_logging(__name__)
        return logging.getLogger("CrossMachineSync")
    
    def _detect_machine(self) -> str:
        """Detect which machine we're running on"""
        hostname = os.getenv("HOSTNAME", "unknown")
        if "mainpc" in hostname.lower():
            return "mainpc"
        elif "pc2" in hostname.lower():
            return "pc2"
        else:
            # Fallback to checking GPU memory
            try:
                import subprocess
                result = subprocess.run(
                    "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits",
                    shell=True, capture_output=True, text=True
                )
                if result.returncode == 0:
                    memory = int(result.stdout.strip().split('\n')[0])
                    # RTX 4090 has ~24GB, RTX 3060 has ~12GB
                    return "mainpc" if memory > 20000 else "pc2"
            except:
                pass
            
            return "unknown"
    
    async def initialize_connections(self):
        """Initialize Redis connections to both machines"""
        try:
            # Connect to MainPC Redis
            self.redis_main = redis.Redis(
                host=self.config.mainpc_host,
                port=self.config.redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await asyncio.get_event_loop().run_in_executor(None, self.redis_main.ping)
            
            # Connect to PC2 Redis (if different from MainPC)
            if self.config.pc2_host != self.config.mainpc_host:
                self.redis_pc2 = redis.Redis(
                    host=self.config.pc2_host,
                    port=self.config.redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                await asyncio.get_event_loop().run_in_executor(None, self.redis_pc2.ping)
            else:
                self.redis_pc2 = self.redis_main
            
            self.logger.info(f"✅ Connected to Redis on both machines from {self.current_machine}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def sync_memory_state(self):
        """Synchronize memory and state data between machines"""
        try:
            sync_key = f"sync:memory_state:{self.current_machine}"
            timestamp = datetime.now().isoformat()
            
            # Collect local memory state
            local_state = {
                "machine": self.current_machine,
                "timestamp": timestamp,
                "memory_usage": await self._get_memory_usage(),
                "active_sessions": await self._get_active_sessions(),
                "model_cache": await self._get_model_cache_info()
            }
            
            # Store in Redis for other machine to read
            if self.current_machine == "mainpc":
                self.redis_main.setex(sync_key, 600, json.dumps(local_state))  # 10 min TTL
            else:
                self.redis_pc2.setex(sync_key, 600, json.dumps(local_state))
            
            # Read state from other machine
            other_machine = "pc2" if self.current_machine == "mainpc" else "mainpc"
            other_key = f"sync:memory_state:{other_machine}"
            
            redis_client = self.redis_pc2 if other_machine == "pc2" else self.redis_main
            other_state_data = redis_client.get(other_key)
            
            if other_state_data:
                other_state = json.loads(other_state_data)
                await self._process_remote_state(other_state)
                self.logger.info(f"🔄 Synced memory state with {other_machine}")
            
        except Exception as e:
            self.logger.error(f"❌ Memory state sync failed: {e}")
    
    async def sync_model_metadata(self):
        """Synchronize model metadata and availability"""
        try:
            models_key = f"sync:models:{self.current_machine}"
            
            # Get local model information
            local_models = await self._get_local_models()
            
            # Store in Redis
            redis_client = self.redis_main if self.current_machine == "mainpc" else self.redis_pc2
            redis_client.setex(models_key, 1800, json.dumps(local_models))  # 30 min TTL
            
            self.logger.info(f"📦 Synced {len(local_models)} model entries")
            
        except Exception as e:
            self.logger.error(f"❌ Model metadata sync failed: {e}")
    
    async def sync_health_status(self):
        """Synchronize health status across machines"""
        try:
            health_key = f"sync:health:{self.current_machine}"
            
            # Collect health data
            health_data = {
                "machine": self.current_machine,
                "timestamp": datetime.now().isoformat(),
                "services": await self._get_service_health(),
                "resources": await self._get_resource_status(),
                "alerts": await self._get_active_alerts()
            }
            
            # Store health data
            redis_client = self.redis_main if self.current_machine == "mainpc" else self.redis_pc2
            redis_client.setex(health_key, 300, json.dumps(health_data))  # 5 min TTL
            
            self.logger.info(f"💚 Synced health status from {self.current_machine}")
            
        except Exception as e:
            self.logger.error(f"❌ Health status sync failed: {e}")
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage stats"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "used": memory.used,
                "available": memory.available,
                "percent": memory.percent
            }
        except:
            return {"error": "psutil not available"}
    
    async def _get_active_sessions(self) -> Dict[str, Any]:
        """Get active session information"""
        try:
            # Check Redis for active sessions
            redis_client = self.redis_main if self.current_machine == "mainpc" else self.redis_pc2
            session_keys = redis_client.keys("session:*")
            return {
                "active_count": len(session_keys),
                "sessions": session_keys[:10]  # First 10 for sample
            }
        except:
            return {"active_count": 0, "sessions": []}
    
    async def _get_model_cache_info(self) -> Dict[str, Any]:
        """Get model cache information"""
        cache_dir = Path("/app/models")
        if cache_dir.exists():
            models = list(cache_dir.glob("*.safetensors")) + list(cache_dir.glob("*.bin"))
            return {
                "cached_models": len(models),
                "cache_size_mb": sum(f.stat().st_size for f in models) // (1024 * 1024)
            }
        return {"cached_models": 0, "cache_size_mb": 0}
    
    async def _get_local_models(self) -> Dict[str, Any]:
        """Get local model inventory"""
        models_dir = Path("/app/models")
        models = {}
        
        if models_dir.exists():
            for model_file in models_dir.glob("*"):
                if model_file.is_file():
                    models[model_file.name] = {
                        "size": model_file.stat().st_size,
                        "modified": model_file.stat().st_mtime,
                        "machine": self.current_machine
                    }
        
        return models
    
    async def _get_service_health(self) -> Dict[str, str]:
        """Get health status of local services"""
        # This would integrate with your existing health check system
        return {"status": "healthy", "services_checked": 0}
    
    async def _get_resource_status(self) -> Dict[str, Any]:
        """Get current resource utilization"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(),
                "disk_usage": psutil.disk_usage('/').percent,
                "load_average": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            }
        except:
            return {"error": "resource info unavailable"}
    
    async def _get_active_alerts(self) -> List[str]:
        """Get any active system alerts"""
        # Placeholder for alert system integration
        return []
    
    async def _process_remote_state(self, remote_state: Dict[str, Any]):
        """Process state information from remote machine"""
        remote_machine = remote_state.get("machine", "unknown")
        self.logger.info(f"📊 Processing state from {remote_machine}")
        
        # Log interesting differences or alerts
        if "memory_usage" in remote_state:
            remote_memory = remote_state["memory_usage"]
            if isinstance(remote_memory, dict) and "percent" in remote_memory:
                if remote_memory["percent"] > 90:
                    self.logger.warning(f"⚠️  High memory usage on {remote_machine}: {remote_memory['percent']}%")
    
    async def run_sync_cycle(self):
        """Run one complete synchronization cycle"""
        self.logger.info(f"🔄 Starting sync cycle on {self.current_machine}")
        
        tasks = [
            self.sync_memory_state(),
            self.sync_model_metadata(),
            self.sync_health_status()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("✅ Sync cycle completed")
    
    async def run_continuous(self):
        """Run continuous synchronization"""
        await self.initialize_connections()
        
        self.logger.info(f"🚀 Starting continuous sync on {self.current_machine}")
        self.logger.info(f"⏰ Sync interval: {self.config.sync_interval} seconds")
        
        while True:
            try:
                await self.run_sync_cycle()
                await asyncio.sleep(self.config.sync_interval)
            except KeyboardInterrupt:
                self.logger.info("🛑 Sync service stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Sync cycle error: {e}")
                await asyncio.sleep(30)  # Short delay before retry

async def main():
    """Main entry point"""
    config = SyncConfig(
        mainpc_host=os.getenv("MAINPC_HOST", get_service_ip("mainpc")),
        pc2_host=os.getenv("PC2_HOST", get_service_ip("pc2")),
        sync_interval=int(os.getenv("SYNC_INTERVAL", "300"))
    )
    
    sync_service = CrossMachineSync(config)
    await sync_service.run_continuous()

if __name__ == "__main__":
    asyncio.run(main()) 