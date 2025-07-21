#!/usr/bin/env python3
"""
🚀 DEMO MODERN AGENT - FULLY IMPLEMENTED EXAMPLE
================================================================
Shows complete implementation of:
✅ Unified Error Reporting (NATS + Legacy ZMQ)
✅ Standardized Health Checking (Redis-based)
✅ Universal Config Management (MainPC + PC2 compatible)

This is what ALL agents should look like after modernization!
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# ✅ STEP 1: Import the modern BaseAgent (INCLUDES EVERYTHING!)
from common.core.base_agent import BaseAgent

# ✅ STEP 2: Optional advanced imports (ONLY IF NEEDED)
from common.config_manager import load_unified_config, get_service_ip
from common.error_bus.nats_error_bus import ErrorSeverity, ErrorCategory
from common.health.standardized_health import HealthStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModernDemoAgent(BaseAgent):
    """
    🎯 PERFECT EXAMPLE: Modern AI System Agent
    
    ✅ AUTO-INCLUDES from BaseAgent:
    - Unified error reporting (ZMQ + NATS)
    - Standardized health checking (Redis)
    - Proper async lifecycle management
    - Event loop fixes (no more "Event loop is closed")
    - HTTP health endpoints
    """
    
    def __init__(self, port: int = 5999, config_path: str = None):
        # ✅ SINGLE LINE INITIALIZATION - EVERYTHING AUTO-SETUP!
        super().__init__(name="ModernDemoAgent", port=port, health_check_port=port+1)
        
        # ✅ OPTIONAL: Load config if needed (supports both MainPC + PC2)
        if config_path:
            self.config = load_unified_config(config_path)
            self.pc2_ip = get_service_ip("pc2")  # Auto uses env vars
        
        # ✅ AGENT-SPECIFIC INITIALIZATION
        self.processed_requests = 0
        self.last_activity = time.time()
        self.demo_data = {"status": "initialized", "mode": "demo"}
        
        logger.info(f"🚀 {self.name} fully initialized with modern infrastructure!")
    
    # ================================================================
    # 💼 BUSINESS LOGIC METHODS
    # ================================================================
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Business logic with automatic error reporting"""
        try:
            self.processed_requests += 1
            self.last_activity = time.time()
            
            # ✅ SIMULATE SOME PROCESSING
            if data.get("simulate_error"):
                raise ValueError("Simulated processing error for testing")
            
            # ✅ BUSINESS LOGIC HERE
            result = {
                "status": "success",
                "processed_at": datetime.now().isoformat(),
                "input_data": data,
                "agent_stats": {
                    "requests_processed": self.processed_requests,
                    "uptime_seconds": time.time() - self.start_time
                }
            }
            
            return result
            
        except ValueError as e:
            # ✅ AUTOMATIC ERROR REPORTING - SINGLE LINE!
            await self.report_error(
                "validation_error", 
                f"Data processing failed: {e}", 
                "warning",
                details={"input_data": data}
            )
            return {"status": "error", "message": str(e)}
            
        except Exception as e:
            # ✅ CRITICAL ERROR REPORTING
            await self.report_error(
                "processing_error",
                f"Unexpected error in data processing: {e}",
                "critical",
                details={"input_data": data, "error_type": type(e).__name__}
            )
            return {"status": "error", "message": "Internal processing error"}
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Override BaseAgent's request handler"""
        action = request.get("action")
        
        if action == "process":
            # ✅ RUN ASYNC METHOD FROM SYNC CONTEXT
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.process_data(request.get("data", {})))
                return result
            finally:
                loop.close()
                
        elif action == "get_stats":
            return {
                "status": "success",
                "stats": {
                    "requests_processed": self.processed_requests,
                    "last_activity": self.last_activity,
                    "uptime_seconds": time.time() - self.start_time,
                    "demo_data": self.demo_data
                }
            }
            
        elif action == "simulate_error":
            # ✅ DEMONSTRATE ERROR REPORTING
            asyncio.run(self.report_error(
                "demo_error",
                "This is a simulated error for testing",
                "info",
                details={"triggered_by": "user_request"}
            ))
            return {"status": "success", "message": "Error simulated and reported"}
            
        elif action in ["ping", "health", "health_check"]:
            # ✅ AUTOMATIC HEALTH CHECK (inherited from BaseAgent)
            return super().handle_request(request)
            
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
    
    # ================================================================
    # 🎯 OPTIONAL: ADVANCED ERROR REPORTING EXAMPLES
    # ================================================================
    
    async def demonstrate_advanced_error_reporting(self):
        """Show advanced error reporting capabilities"""
        
        # ✅ SIMPLE ERROR (most common)
        await self.report_error("demo", "Simple error message", "info")
        
        # ✅ STRUCTURED ERROR (recommended)
        await self.report_error(
            "database_connection",
            "Failed to connect to database",
            "error",
            details={
                "host": "localhost",
                "port": 5432,
                "timeout": 30,
                "retry_count": 3
            }
        )
        
        # ✅ ADVANCED ERROR (full features)
        if hasattr(self, 'unified_error_handler') and self.unified_error_handler:
            await self.unified_error_handler.report_error(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM,
                message="Critical system failure detected",
                details={
                    "component": "ModernDemoAgent",
                    "error_code": "SYS_001",
                    "affected_users": 150,
                    "recovery_action": "restart_required"
                },
                error_type="system_failure"
            )
    
    # ================================================================
    # 🏥 OPTIONAL: CUSTOM HEALTH CHECKS
    # ================================================================
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Optional: Extend health status with agent-specific data"""
        # ✅ GET STANDARD HEALTH STATUS
        base_status = super()._get_health_status()
        
        # ✅ ADD AGENT-SPECIFIC METRICS
        base_status.update({
            "agent_specific_metrics": {
                "requests_processed": self.processed_requests,
                "last_activity_seconds_ago": time.time() - self.last_activity,
                "demo_data": self.demo_data,
                "business_status": "operational" if self.processed_requests > 0 else "idle"
            }
        })
        
        return base_status


# ================================================================
# 🚀 MAIN EXECUTION EXAMPLE
# ================================================================

def main():
    """Demonstrate the modern agent"""
    print("🚀 Starting Modern Demo Agent...")
    
    try:
        # ✅ CREATE AGENT (auto-setup of error bus, health checks, etc.)
        agent = ModernDemoAgent(port=5999)
        
        print(f"✅ Agent initialized successfully!")
        print(f"📡 Main port: {agent.port}")
        print(f"🏥 Health check port: {agent.health_check_port}")
        print(f"🌐 Health URL: http://localhost:{agent.health_check_port + 1}/health")
        print(f"📊 Redis health key: agent:{agent.name}:ready")
        
        # ✅ RUN THE AGENT
        agent.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        agent.cleanup()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


# ================================================================
# 📋 USAGE EXAMPLES
# ================================================================

"""
🔧 TEST THE AGENT:

1️⃣ START AGENT:
   python demo_modern_agent.py

2️⃣ TEST BASIC HEALTH:
   curl http://localhost:6000/health

3️⃣ TEST ZMQ COMMUNICATION:
   import zmq
   context = zmq.Context()
   socket = context.socket(zmq.REQ)
   socket.connect("tcp://localhost:5999")
   
   # Health check
   socket.send_json({"action": "health"})
   print(socket.recv_json())
   
   # Process data
   socket.send_json({"action": "process", "data": {"test": "data"}})
   print(socket.recv_json())
   
   # Get stats
   socket.send_json({"action": "get_stats"})
   print(socket.recv_json())
   
   # Simulate error
   socket.send_json({"action": "simulate_error"})
   print(socket.recv_json())

4️⃣ CHECK REDIS HEALTH:
   redis-cli GET "agent:ModernDemoAgent:ready"

5️⃣ VIEW ERROR DASHBOARD:
   # If NATS + Dashboard running:
   # http://localhost:8080

📊 WHAT YOU GET AUTOMATICALLY:
✅ Error reporting to both ZMQ (SystemDigitalTwin) and NATS
✅ Health checks via HTTP, ZMQ, and Redis
✅ Proper async lifecycle management
✅ Event loop fixes
✅ Graceful shutdown
✅ JSON structured logging
✅ Service discovery integration
""" 