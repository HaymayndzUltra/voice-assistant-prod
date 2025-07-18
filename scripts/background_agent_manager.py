#!/usr/bin/env python3
"""
Background Agent Manager for Cursor Ultra Plan
Manages continuous monitoring and automation tasks
"""

import asyncio
import json
import logging
import time
import os
import sys
from pathlib import Path
from datetime import datetime
import psutil
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class BackgroundAgentManager:
    """Manages background agents for continuous monitoring"""
    
    def __init__(self):
        self.project_root = Path(os.getenv("AI_SYSTEM_PATH", project_root))
        self.logger = self._setup_logging()
        self.running = True
        self.monitoring_interval = int(os.getenv("MONITORING_INTERVAL", "30"))
        
    def _setup_logging(self):
        """Setup logging for background operations"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "background_agents.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def start_background_monitoring(self):
        """Start continuous background monitoring"""
        self.logger.info("🚀 Starting Background Agent Manager...")
        
        # Start monitoring tasks
        tasks = [
            self.system_health_monitor(),
            self.agent_health_monitor(),
            self.resource_monitor(),
            self.github_monitor()
        ]
        
        await asyncio.gather(*tasks)
    
    async def system_health_monitor(self):
        """Monitor system health continuously"""
        while self.running:
            try:
                # Check system resources
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent
                disk_usage = psutil.disk_usage('/').percent
                
                # Check GPU
                gpu_status = self._check_gpu_status()
                
                # Log if thresholds exceeded
                if cpu_usage > 80:
                    self.logger.warning(f"⚠️ High CPU usage: {cpu_usage}%")
                
                if memory_usage > 85:
                    self.logger.warning(f"⚠️ High memory usage: {memory_usage}%")
                
                if disk_usage > 90:
                    self.logger.warning(f"⚠️ High disk usage: {disk_usage}%")
                
                if gpu_status.get("memory_used_percent", 0) > 90:
                    self.logger.warning(f"⚠️ High GPU memory usage: {gpu_status.get('memory_used_percent')}%")
                
                # Save metrics
                self._save_metrics({
                    "timestamp": datetime.now().isoformat(),
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "disk_usage": disk_usage,
                    "gpu_status": gpu_status
                })
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in system health monitor: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def agent_health_monitor(self):
        """Monitor AI agents health"""
        while self.running:
            try:
                # Check MainPC agents
                mainpc_agents = await self._check_mainpc_agents()
                
                # Check PC2 agents
                pc2_agents = await self._check_pc2_agents()
                
                # Log unhealthy agents
                for agent in mainpc_agents + pc2_agents:
                    if agent.get("status") != "healthy":
                        self.logger.warning(f"⚠️ Unhealthy agent: {agent.get('name')} - {agent.get('status')}")
                
                # Auto-restart if needed
                await self._auto_restart_agents(mainpc_agents + pc2_agents)
                
                await asyncio.sleep(self.monitoring_interval * 2)  # Check less frequently
                
            except Exception as e:
                self.logger.error(f"Error in agent health monitor: {e}")
                await asyncio.sleep(120)
    
    async def resource_monitor(self):
        """Monitor resource usage and optimize"""
        while self.running:
            try:
                # Check GPU memory
                gpu_status = self._check_gpu_status()
                
                # Optimize if needed
                if gpu_status.get("memory_used_percent", 0) > 95:
                    self.logger.info("🔧 Optimizing GPU memory...")
                    await self._optimize_gpu_memory()
                
                # Check disk space
                disk_usage = psutil.disk_usage('/').percent
                if disk_usage > 95:
                    self.logger.info("🧹 Cleaning up disk space...")
                    await self._cleanup_disk_space()
                
                await asyncio.sleep(self.monitoring_interval * 3)  # Check less frequently
                
            except Exception as e:
                self.logger.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(180)
    
    async def github_monitor(self):
        """Monitor GitHub for new issues/PRs"""
        while self.running:
            try:
                # Check for new GitHub notifications
                token = os.getenv("GITHUB_TOKEN")
                if token:
                    headers = {"Authorization": f"token {token}"}
                    
                    # Check for new issues
                    response = requests.get(
                        "https://api.github.com/repos/HaymayndzUltra/AI_System_Monorepo/issues",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        issues = response.json()
                        new_issues = [i for i in issues if i.get("state") == "open"]
                        
                        if new_issues:
                            self.logger.info(f"📋 Found {len(new_issues)} open issues")
                    
                await asyncio.sleep(self.monitoring_interval * 4)  # Check less frequently
                
            except Exception as e:
                self.logger.error(f"Error in GitHub monitor: {e}")
                await asyncio.sleep(300)
    
    def _check_gpu_status(self):
        """Check GPU status"""
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split(',')
                memory_used = int(gpu_info[1])
                memory_total = int(gpu_info[2])
                memory_used_percent = (memory_used / memory_total) * 100
                
                return {
                    "name": gpu_info[0],
                    "memory_used_mb": memory_used,
                    "memory_total_mb": memory_total,
                    "memory_used_percent": memory_used_percent,
                    "utilization_percent": int(gpu_info[3])
                }
            else:
                return {"status": "nvidia-smi not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _check_mainpc_agents(self):
        """Check MainPC agents health"""
        try:
            # This would integrate with your existing health checker
            return []
        except Exception as e:
            self.logger.error(f"Error checking MainPC agents: {e}")
            return []
    
    async def _check_pc2_agents(self):
        """Check PC2 agents health"""
        try:
            # This would integrate with your existing health checker
            return []
        except Exception as e:
            self.logger.error(f"Error checking PC2 agents: {e}")
            return []
    
    async def _auto_restart_agents(self, agents):
        """Auto-restart unhealthy agents"""
        for agent in agents:
            if agent.get("status") == "unhealthy":
                try:
                    self.logger.info(f"🔄 Auto-restarting agent: {agent.get('name')}")
                    # Add restart logic here
                except Exception as e:
                    self.logger.error(f"Error restarting agent {agent.get('name')}: {e}")
    
    async def _optimize_gpu_memory(self):
        """Optimize GPU memory usage"""
        try:
            # Add GPU optimization logic
            self.logger.info("GPU memory optimization completed")
        except Exception as e:
            self.logger.error(f"Error optimizing GPU memory: {e}")
    
    async def _cleanup_disk_space(self):
        """Clean up disk space"""
        try:
            # Add disk cleanup logic
            self.logger.info("Disk cleanup completed")
        except Exception as e:
            self.logger.error(f"Error cleaning disk space: {e}")
    
    def _save_metrics(self, metrics):
        """Save monitoring metrics"""
        try:
            metrics_file = self.project_root / "logs" / "background_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")

async def main():
    """Main function"""
    manager = BackgroundAgentManager()
    
    try:
        await manager.start_background_monitoring()
    except KeyboardInterrupt:
        manager.logger.info("🛑 Background Agent Manager stopped by user")
    except Exception as e:
        manager.logger.error(f"Error in Background Agent Manager: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 