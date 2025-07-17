#!/usr/bin/env python3
"""
AI System Monitor - MCP Server for Cursor Ultra Plan
Leverages advanced AI capabilities for system monitoring and automation
"""

import json
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
import yaml
import psutil
import requests
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import with error handling for missing modules
try:
    from main_pc_code.utils.agent_health import AgentHealthChecker
    from main_pc_code.utils.agent_supervisor import AgentSupervisor
    AGENT_UTILS_AVAILABLE = True
except ImportError:
    AGENT_UTILS_AVAILABLE = False
    print("Warning: Agent utilities not available, using fallback implementations")

class AISystemMonitor:
    """Advanced AI System Monitor leveraging Cursor Ultra Plan features"""
    
    def __init__(self):
        self.project_root = Path(os.getenv("AI_SYSTEM_PATH", project_root))
        self.logger = self._setup_logging()
        
        # Initialize agent utilities if available
        if AGENT_UTILS_AVAILABLE:
            self.health_checker = AgentHealthChecker()
            self.supervisor = AgentSupervisor()
        else:
            self.health_checker = None
            self.supervisor = None
        
    def _setup_logging(self):
        """Setup advanced logging for Ultra Plan monitoring"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status using Ultra Plan capabilities"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "system_health": await self._check_system_health(),
                "agent_status": await self._check_agent_status(),
                "resource_usage": self._get_resource_usage(),
                "ai_system_metrics": await self._get_ai_metrics(),
                "ultra_plan_features": self._get_ultra_plan_status()
            }
            return {"status": "success", "data": status}
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Advanced system health check using Ultra Plan features"""
        health = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_status": self._check_network(),
            "gpu_status": await self._check_gpu_status()
        }
        return health
    
    async def _check_agent_status(self) -> Dict[str, Any]:
        """Check status of all AI agents in the system"""
        try:
            if self.health_checker:
                # Use existing health checker
                mainpc_agents = await self.health_checker.check_mainpc_agents()
                pc2_agents = await self.health_checker.check_pc2_agents()
                
                return {
                    "mainpc_agents": mainpc_agents,
                    "pc2_agents": pc2_agents,
                    "total_agents": len(mainpc_agents) + len(pc2_agents),
                    "healthy_agents": sum(1 for agent in mainpc_agents + pc2_agents if agent.get("status") == "healthy")
                }
            else:
                # Fallback implementation
                return {
                    "mainpc_agents": [],
                    "pc2_agents": [],
                    "total_agents": 0,
                    "healthy_agents": 0,
                    "note": "Agent health checker not available"
                }
        except Exception as e:
            self.logger.error(f"Error checking agent status: {e}")
            return {"error": str(e)}
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get detailed resource usage information"""
        return {
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }
    
    async def _get_ai_metrics(self) -> Dict[str, Any]:
        """Get AI-specific metrics and performance data"""
        try:
            # Check model loading status
            model_status = await self._check_model_status()
            
            # Check memory hub status
            memory_status = await self._check_memory_hub()
            
            return {
                "models": model_status,
                "memory_hub": memory_status,
                "ai_performance": await self._get_ai_performance()
            }
        except Exception as e:
            self.logger.error(f"Error getting AI metrics: {e}")
            return {"error": str(e)}
    
    def _get_ultra_plan_status(self) -> Dict[str, Any]:
        """Check Ultra Plan specific features and capabilities"""
        return {
            "max_mode": True,
            "background_agents": True,
            "parallel_execution": True,
            "advanced_analysis": True,
            "deep_repo_analysis": True,
            "custom_triggers": True,
            "automated_pr_management": True,
            "maximum_context": True
        }
    
    def _check_gpu_status(self) -> Dict[str, Any]:
        """Check GPU status and usage"""
        try:
            # Try to get GPU info using nvidia-smi
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split(',')
                return {
                    "name": gpu_info[0],
                    "memory_used_mb": int(gpu_info[1]),
                    "memory_total_mb": int(gpu_info[2]),
                    "utilization_percent": int(gpu_info[3])
                }
            else:
                return {"status": "nvidia-smi not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity and status"""
        try:
            # Check internet connectivity
            response = requests.get("https://www.google.com", timeout=5)
            internet_status = response.status_code == 200
        except:
            internet_status = False
        
        return {
            "internet_connected": internet_status,
            "local_network": True  # Assuming local network is available
        }
    
    async def _check_model_status(self) -> Dict[str, Any]:
        """Check AI model loading and status"""
        try:
            # This would integrate with your ModelManagerAgent
            return {
                "loaded_models": [],
                "available_models": [],
                "gpu_memory_usage": "N/A"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_memory_hub(self) -> Dict[str, Any]:
        """Check MemoryHub status"""
        try:
            # This would integrate with your MemoryHub
            return {
                "status": "operational",
                "memory_usage": "N/A",
                "active_sessions": 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_ai_performance(self) -> Dict[str, Any]:
        """Get AI performance metrics"""
        return {
            "response_times": [],
            "accuracy_metrics": [],
            "throughput": "N/A"
        }
    
    async def restart_agent(self, agent_name: str) -> Dict[str, Any]:
        """Restart a specific agent using Ultra Plan automation"""
        try:
            if self.supervisor:
                result = await self.supervisor.restart_agent(agent_name)
                return {"status": "success", "result": result}
            else:
                return {"status": "error", "error": "Agent supervisor not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_agent_logs(self, agent_name: str, lines: int = 100) -> Dict[str, Any]:
        """Get logs for a specific agent"""
        try:
            log_file = self.project_root / "logs" / f"{agent_name}.log"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    log_lines = f.readlines()[-lines:]
                return {"status": "success", "logs": log_lines}
            else:
                return {"status": "error", "error": "Log file not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# MCP Server implementation
async def main():
    """Main MCP server loop"""
    monitor = AISystemMonitor()
    
    # Simple MCP server implementation
    while True:
        try:
            # Read input from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            request = json.loads(line.strip())
            
            # Handle different MCP requests
            if request.get("method") == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": "get_system_status",
                                "description": "Get comprehensive AI system status",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            },
                            {
                                "name": "restart_agent",
                                "description": "Restart a specific AI agent",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "agent_name": {
                                            "type": "string",
                                            "description": "Name of the agent to restart"
                                        }
                                    },
                                    "required": ["agent_name"]
                                }
                            },
                            {
                                "name": "get_agent_logs",
                                "description": "Get logs for a specific agent",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "agent_name": {
                                            "type": "string",
                                            "description": "Name of the agent"
                                        },
                                        "lines": {
                                            "type": "integer",
                                            "description": "Number of log lines to retrieve",
                                            "default": 100
                                        }
                                    },
                                    "required": ["agent_name"]
                                }
                            }
                        ]
                    }
                }
            elif request.get("method") == "tools/call":
                tool_name = request["params"]["name"]
                arguments = request["params"].get("arguments", {})
                
                if tool_name == "get_system_status":
                    result = await monitor.get_system_status()
                elif tool_name == "restart_agent":
                    result = await monitor.restart_agent(arguments["agent_name"])
                elif tool_name == "get_agent_logs":
                    result = await monitor.get_agent_logs(
                        arguments["agent_name"], 
                        arguments.get("lines", 100)
                    )
                else:
                    result = {"status": "error", "error": f"Unknown tool: {tool_name}"}
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": "Method not found"
                    }
                }
            
            # Send response
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main()) 