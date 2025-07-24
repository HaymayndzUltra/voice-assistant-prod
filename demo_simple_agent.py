#!/usr/bin/env python3
"""
🎯 SIMPLE AGENT EXAMPLE - MINIMAL IMPLEMENTATION
================================================================
Perfect for most agents (80% of use cases)

✅ WHAT YOU GET AUTOMATICALLY:
- Error reporting (just call self.report_error())
- Health checks (automatic HTTP + ZMQ + Redis)
- Graceful shutdown (no event loop errors)
- Service discovery integration

❌ WHAT YOU DON'T NEED:
- Manual error bus setup
- Custom health check code
- Complex config loading (unless needed)
- Advanced NATS features (unless needed)
"""

import time
import logging
from typing import Dict, Any

# ✅ SINGLE IMPORT - EVERYTHING INCLUDED!
from common.core.base_agent import BaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleDemoAgent(BaseAgent):
    """
    🎯 MINIMAL EXAMPLE: 80% of agents should look like this
    
    ✅ INHERITED AUTOMATICALLY:
    - self.report_error() - Works immediately
    - Health checks - Automatic
    - Redis ready signals - Automatic  
    - Graceful shutdown - Automatic
    """
    
    def __init__(self, port: int = 5998):
        # ✅ ONE LINE SETUP - EVERYTHING AUTO-CONFIGURED!
        super().__init__(name="SimpleDemoAgent", port=port)
        
        # ✅ YOUR BUSINESS LOGIC INITIALIZATION
        self.message_count = 0
        self.data_store = {}
        
        logger.info(f"✅ {self.name} ready to serve!")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests - override BaseAgent method"""
        action = request.get("action")
        
        if action == "store_data":
            # ✅ BUSINESS LOGIC + AUTO ERROR REPORTING
            try:
                key = request.get("key")
                value = request.get("value")
                
                if not key:
                    # ✅ SIMPLE ERROR REPORTING
                    self.report_error("validation_error", "Missing key in store_data request", "warning")
                    return {"status": "error", "message": "Missing key"}
                
                self.data_store[key] = value
                self.message_count += 1
                
                return {
                    "status": "success",
                    "message": f"Stored {key}",
                    "total_messages": self.message_count
                }
                
            except Exception as e:
                # ✅ AUTOMATIC ERROR REPORTING
                self.report_error("storage_error", f"Failed to store data: {e}", "error")
                return {"status": "error", "message": "Storage failed"}
        
        elif action == "get_data":
            try:
                key = request.get("key")
                value = self.data_store.get(key)
                
                return {
                    "status": "success",
                    "key": key,
                    "value": value,
                    "found": value is not None
                }
                
            except Exception as e:
                self.report_error("retrieval_error", f"Failed to get data: {e}", "error")
                return {"status": "error", "message": "Retrieval failed"}
        
        elif action == "get_stats":
            return {
                "status": "success",
                "stats": {
                    "message_count": self.message_count,
                    "stored_items": len(self.data_store),
                    "uptime_seconds": time.time() - self.start_time
                }
            }
        
        elif action in ["ping", "health", "health_check"]:
            # ✅ USE INHERITED HEALTH CHECK
            return super().handle_request(request)
        
        else:
            # ✅ SIMPLE ERROR LOGGING
            self.report_error("unknown_action", f"Unknown action: {action}", "info")
            return {"status": "error", "error": f"Unknown action: {action}"}


# ================================================================
# 🚀 MAIN EXECUTION
# ================================================================

def main():
    """Run the simple agent"""
    print("🚀 Starting Simple Demo Agent...")
    print("✅ Features included automatically:")
    print("   - Error reporting to SystemDigitalTwin + NATS")
    print("   - Health checks via HTTP, ZMQ, Redis")
    print("   - Graceful shutdown handling")
    print("   - Service discovery integration")
    
    try:
        agent = SimpleDemoAgent(port=5998)
        print(f"📡 Agent running on port: {agent.port}")
        print(f"🏥 Health check port: {agent.health_check_port}")
        
        agent.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        agent.cleanup()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()


# ================================================================
# 📋 QUICK TEST COMMANDS
# ================================================================

"""
🔧 TEST THE SIMPLE AGENT:

1️⃣ START:
   python demo_simple_agent.py

2️⃣ TEST WITH ZMQ:
   import zmq
   context = zmq.Context()
   socket = context.socket(zmq.REQ)
   socket.connect("tcp://localhost:5998")
   
   # Store data
   socket.send_json({"action": "store_data", "key": "test", "value": "hello"})
   print(socket.recv_json())
   
   # Get data
   socket.send_json({"action": "get_data", "key": "test"})
   print(socket.recv_json())
   
   # Get stats
   socket.send_json({"action": "get_stats"})
   print(socket.recv_json())
   
   # Health check
   socket.send_json({"action": "health"})
   print(socket.recv_json())

3️⃣ CHECK HEALTH:
   curl http://localhost:5999/health

4️⃣ CHECK REDIS:
   redis-cli GET "agent:SimpleDemoAgent:ready"

📊 AUTOMATIC FEATURES:
✅ self.report_error() works immediately
✅ Health monitoring automatic
✅ No event loop errors
✅ Service registration with SystemDigitalTwin
✅ Redis ready signals
✅ Proper cleanup on shutdown
""" 