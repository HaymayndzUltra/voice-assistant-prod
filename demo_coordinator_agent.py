#!/usr/bin/env python3
"""
🎯 COORDINATOR AGENT EXAMPLE - CONFIG + INTER-MACHINE COMMUNICATION
================================================================
Perfect for coordinator agents (15% of use cases)

✅ ADDITIONAL FEATURES:
- Universal config management (MainPC + PC2)
- Inter-machine communication helpers
- Service discovery
- Advanced error context

🎯 USE CASES:
- RequestCoordinator
- ModelManager  
- SystemOrchestrator
- Cross-machine bridges
"""

import time
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

# ✅ BASE AGENT (automatic infrastructure)
from common.core.base_agent import BaseAgent

# ✅ COORDINATOR-SPECIFIC IMPORTS
from common.config_manager import (
    load_unified_config,
    get_agents_by_machine,
    get_service_ip,
    get_service_url
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoordinatorDemoAgent(BaseAgent):
    """
    🎯 COORDINATOR EXAMPLE: For agents that coordinate between systems
    
    ✅ INHERITS FROM BaseAgent:
    - Error reporting (ZMQ + NATS)
    - Health checks (HTTP + ZMQ + Redis)
    - Proper lifecycle management
    
    ✅ ADDS COORDINATOR FEATURES:
    - Universal config loading
    - Inter-machine communication
    - Service discovery
    - Multi-agent coordination
    """
    
    def __init__(self, port: int = 5997, config_path: str = "main_pc_code/config/startup_config.yaml"):
        # ✅ BASE INFRASTRUCTURE AUTO-SETUP
        super().__init__(name="CoordinatorDemoAgent", port=port)
        
        # ✅ LOAD UNIVERSAL CONFIG (supports MainPC + PC2)
        try:
            self.config = load_unified_config(config_path)
            logger.info(f"✅ Loaded config with {len(self.config['unified_agents'])} agents")
        except Exception as e:
            self.report_error("config_error", f"Failed to load config: {e}", "critical")
            self.config = {"unified_agents": []}
        
        # ✅ SERVICE DISCOVERY SETUP
        self.mainpc_ip = get_service_ip("mainpc")
        self.pc2_ip = get_service_ip("pc2") 
        self.redis_url = get_service_url("redis", 6379)
        
        # ✅ COORDINATOR STATE
        self.agent_registry = {}
        self.coordination_requests = []
        self.last_health_check = 0
        
        # ✅ AGENT CATEGORIZATION
        self.mainpc_agents = get_agents_by_machine(self.config, "mainpc")
        self.pc2_agents = get_agents_by_machine(self.config, "pc2")
        
        logger.info(f"🎯 Coordinator ready - MainPC: {len(self.mainpc_agents)}, PC2: {len(self.pc2_agents)}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle coordination requests"""
        action = request.get("action")
        
        if action == "coordinate_task":
            return self._coordinate_task(request)
        
        elif action == "register_agent":
            return self._register_agent(request)
        
        elif action == "get_agent_status":
            return self._get_agent_status(request)
        
        elif action == "list_agents":
            return self._list_agents()
        
        elif action == "cross_machine_request":
            return self._handle_cross_machine_request(request)
        
        elif action in ["ping", "health", "health_check"]:
            return super().handle_request(request)
        
        else:
            self.report_error("unknown_coordination_action", f"Unknown action: {action}", "warning")
            return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _coordinate_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a multi-agent task"""
        try:
            task_id = request.get("task_id", f"task_{int(time.time())}")
            target_agents = request.get("target_agents", [])
            task_data = request.get("task_data", {})
            
            # ✅ TASK COORDINATION LOGIC
            coordination_result = {
                "task_id": task_id,
                "started_at": datetime.now().isoformat(),
                "target_agents": target_agents,
                "status": "coordinating"
            }
            
            # ✅ VALIDATE AGENTS EXIST IN CONFIG
            available_agents = [agent['name'] for agent in self.config['unified_agents']]
            missing_agents = [agent for agent in target_agents if agent not in available_agents]
            
            if missing_agents:
                self.report_error(
                    "coordination_error", 
                    f"Task {task_id} references unknown agents: {missing_agents}",
                    "error",
                    details={"task_id": task_id, "missing_agents": missing_agents}
                )
                return {"status": "error", "error": f"Unknown agents: {missing_agents}"}
            
            # ✅ STORE COORDINATION REQUEST
            self.coordination_requests.append(coordination_result)
            
            logger.info(f"🎯 Coordinating task {task_id} with {len(target_agents)} agents")
            return {"status": "success", "coordination": coordination_result}
            
        except Exception as e:
            self.report_error("coordination_failure", f"Task coordination failed: {e}", "error")
            return {"status": "error", "message": "Coordination failed"}
    
    def _register_agent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Register an agent in the coordination registry"""
        try:
            agent_name = request.get("agent_name")
            agent_info = request.get("agent_info", {})
            
            if not agent_name:
                return {"status": "error", "error": "Missing agent_name"}
            
            # ✅ STORE AGENT INFO
            self.agent_registry[agent_name] = {
                **agent_info,
                "registered_at": datetime.now().isoformat(),
                "last_seen": time.time()
            }
            
            logger.info(f"📝 Registered agent: {agent_name}")
            return {"status": "success", "message": f"Agent {agent_name} registered"}
            
        except Exception as e:
            self.report_error("registration_error", f"Agent registration failed: {e}", "error")
            return {"status": "error", "message": "Registration failed"}
    
    def _get_agent_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of specific agent"""
        agent_name = request.get("agent_name")
        
        if not agent_name:
            return {"status": "error", "error": "Missing agent_name"}
        
        # ✅ CHECK IN REGISTRY
        if agent_name in self.agent_registry:
            agent_info = self.agent_registry[agent_name]
            return {
                "status": "success",
                "agent": agent_name,
                "info": agent_info,
                "last_seen_seconds_ago": time.time() - agent_info.get("last_seen", 0)
            }
        
        # ✅ CHECK IN CONFIG
        config_agent = None
        for agent in self.config['unified_agents']:
            if agent['name'] == agent_name:
                config_agent = agent
                break
        
        if config_agent:
            return {
                "status": "success",
                "agent": agent_name,
                "config": config_agent,
                "registered": False
            }
        
        return {"status": "error", "error": f"Agent {agent_name} not found"}
    
    def _list_agents(self) -> Dict[str, Any]:
        """List all known agents"""
        return {
            "status": "success",
            "agents": {
                "registered": list(self.agent_registry.keys()),
                "mainpc_config": [agent['name'] for agent in self.mainpc_agents],
                "pc2_config": [agent['name'] for agent in self.pc2_agents],
                "coordination_requests": len(self.coordination_requests)
            },
            "service_endpoints": {
                "mainpc_ip": self.mainpc_ip,
                "pc2_ip": self.pc2_ip,
                "redis_url": self.redis_url
            }
        }
    
    def _handle_cross_machine_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cross-machine communication"""
        try:
            target_machine = request.get("target_machine")  # "mainpc" or "pc2"
            target_agent = request.get("target_agent")
            message = request.get("message", {})
            
            if target_machine not in ["mainpc", "pc2"]:
                return {"status": "error", "error": "target_machine must be 'mainpc' or 'pc2'"}
            
            # ✅ GET TARGET IP
            target_ip = get_service_ip(target_machine)
            
            # ✅ FIND AGENT CONFIG
            agents = self.mainpc_agents if target_machine == "mainpc" else self.pc2_agents
            target_config = None
            
            for agent in agents:
                if agent['name'] == target_agent:
                    target_config = agent
                    break
            
            if not target_config:
                self.report_error(
                    "cross_machine_error",
                    f"Agent {target_agent} not found on {target_machine}",
                    "warning"
                )
                return {"status": "error", "error": f"Agent {target_agent} not found on {target_machine}"}
            
            # ✅ PREPARE CROSS-MACHINE MESSAGE
            cross_machine_result = {
                "target_machine": target_machine,
                "target_ip": target_ip,
                "target_agent": target_agent,
                "target_port": target_config.get('port'),
                "message_sent": message,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🌐 Cross-machine request: {target_machine}:{target_agent}")
            
            # ✅ SIMULATE SENDING (in real implementation, use ZMQ to target_ip:port)
            return {"status": "success", "cross_machine": cross_machine_result}
            
        except Exception as e:
            self.report_error("cross_machine_failure", f"Cross-machine request failed: {e}", "error")
            return {"status": "error", "message": "Cross-machine request failed"}
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Extended health status with coordination data"""
        base_status = super()._get_health_status()
        
        # ✅ ADD COORDINATOR-SPECIFIC METRICS
        base_status.update({
            "coordinator_metrics": {
                "registered_agents": len(self.agent_registry),
                "coordination_requests": len(self.coordination_requests),
                "config_agents_total": len(self.config['unified_agents']),
                "mainpc_agents": len(self.mainpc_agents),
                "pc2_agents": len(self.pc2_agents),
                "service_endpoints": {
                    "mainpc_ip": self.mainpc_ip,
                    "pc2_ip": self.pc2_ip,
                    "redis_url": self.redis_url
                }
            }
        })
        
        return base_status


# ================================================================
# 🚀 MAIN EXECUTION
# ================================================================

def main():
    """Run the coordinator agent"""
    print("🎯 Starting Coordinator Demo Agent...")
    print("✅ Features:")
    print("   - Universal config loading (MainPC + PC2)")
    print("   - Inter-machine communication")
    print("   - Service discovery")
    print("   - Multi-agent coordination")
    print("   - All BaseAgent features (error reporting, health checks)")
    
    try:
        agent = CoordinatorDemoAgent(port=5997)
        print(f"🎯 Coordinator running on port: {agent.port}")
        print(f"🌐 Service endpoints configured:")
        print(f"   - MainPC: {agent.mainpc_ip}")
        print(f"   - PC2: {agent.pc2_ip}")
        print(f"   - Redis: {agent.redis_url}")
        
        agent.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down coordinator...")
        agent.cleanup()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()


# ================================================================
# 📋 COORDINATOR TEST COMMANDS
# ================================================================

"""
🔧 TEST THE COORDINATOR:

1️⃣ START:
   python demo_coordinator_agent.py

2️⃣ TEST COORDINATION:
   import zmq
   context = zmq.Context()
   socket = context.socket(zmq.REQ)
   socket.connect("tcp://localhost:5997")
   
   # List all agents
   socket.send_json({"action": "list_agents"})
   print(socket.recv_json())
   
   # Coordinate task
   socket.send_json({
       "action": "coordinate_task",
       "task_id": "demo_task",
       "target_agents": ["KnowledgeBase", "ModelManager"],
       "task_data": {"operation": "load_model"}
   })
   print(socket.recv_json())
   
   # Cross-machine request
   socket.send_json({
       "action": "cross_machine_request",
       "target_machine": "pc2",
       "target_agent": "PrimaryTranslator",
       "message": {"action": "translate", "text": "hello"}
   })
   print(socket.recv_json())
   
   # Register agent
   socket.send_json({
       "action": "register_agent",
       "agent_name": "TestAgent",
       "agent_info": {"status": "healthy", "port": 6000}
   })
   print(socket.recv_json())

📊 COORDINATOR FEATURES:
✅ Universal config loading (MainPC + PC2 formats)
✅ Service discovery (get_service_ip, get_service_url)
✅ Inter-machine communication helpers
✅ Agent registry and coordination
✅ All BaseAgent features (error reporting, health, etc.)
""" 