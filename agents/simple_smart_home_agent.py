#!/usr/bin/env python3
"""
SIMPLE WORKING SMART HOME AGENT
Based on the proven working device control approach
No complex threading, no BaseAgent complications - just pure working code
"""

import asyncio
import zmq
import json
import logging
from typing import Dict, Any
from plugp100.common.credentials import AuthCredential  
from plugp100.new.device_factory import connect, DeviceConnectConfiguration

class SimpleSmartHomeAgent:
    def __init__(self, port=7125):
        self.port = port
        self.setup_logging()
        self.setup_zmq()
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("SimpleSmartHomeAgent")
        
    def setup_zmq(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self.logger.info(f"✅ Simple Smart Home Agent listening on port {self.port}")
        
    async def control_device(self, action: str) -> Dict[str, Any]:
        """PROVEN WORKING DEVICE CONTROL - Same as successful test"""
        self.logger.info(f"🔄 Controlling device: {action}")
        
        try:
            # EXACT same code that works every time
            credentials = AuthCredential('dagsgarcia8@gmail.com', 'Prof2025!')
            device_config = DeviceConnectConfiguration(host='192.168.100.63', credentials=credentials)
            
            device = await connect(device_config)
            await device.update()
            
            if action == "turn_on":
                await device.turn_on()
                result = "✅ Light turned ON through Simple Agent!"
            elif action == "turn_off":
                await device.turn_off()
                result = "✅ Light turned OFF through Simple Agent!"
            elif action == "status":
                is_on = getattr(device, 'is_on', 'unknown')
                brightness = getattr(device, 'brightness', 'unknown')
                result = f"Light status: {'ON' if is_on else 'OFF'}, Brightness: {brightness}%"
            elif action.startswith("brightness_"):
                # Extract brightness percentage from action like "brightness_50"
                brightness = int(action.split("_")[1])
                if 1 <= brightness <= 100:
                    await device.set_brightness(brightness)
                    result = f"✅ Light brightness set to {brightness}%"
                else:
                    result = "❌ Brightness must be between 1-100%"
            else:
                result = f"Unknown action: {action}"
            
            # Close properly
            if hasattr(device, 'client'):
                await device.client.close()
            
            self.logger.info(f"✅ Success: {result}")
            return {"status": "success", "message": result}
            
        except Exception as e:
            self.logger.error(f"❌ Device control failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def process_voice_command(self, text: str) -> Dict[str, Any]:
        """Process voice commands with brightness support"""
        text = text.lower().strip()
        
        if "turn on" in text or "on" in text:
            return asyncio.run(self.control_device("turn_on"))
        elif "turn off" in text or "off" in text:
            return asyncio.run(self.control_device("turn_off"))
        elif "status" in text:
            return asyncio.run(self.control_device("status"))
        elif "brightness" in text or "dim" in text or "%" in text:
            # Extract brightness percentage from voice command
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                brightness = int(numbers[0])
                if 1 <= brightness <= 100:
                    return asyncio.run(self.control_device(f"brightness_{brightness}"))
                else:
                    return {"status": "error", "message": "Brightness must be between 1-100%"}
            else:
                return {"status": "error", "message": "Please specify brightness percentage (1-100%)"}
        elif "preset" in text:
            # Handle preset brightness levels
            if "1" in text:
                return asyncio.run(self.control_device("brightness_1"))
            elif "25" in text:
                return asyncio.run(self.control_device("brightness_25"))
            elif "50" in text:
                return asyncio.run(self.control_device("brightness_50"))
            elif "75" in text:
                return asyncio.run(self.control_device("brightness_75"))
            elif "100" in text:
                return asyncio.run(self.control_device("brightness_100"))
            else:
                return {"status": "error", "message": "Available presets: 1%, 25%, 50%, 75%, 100%"}
        else:
            return {"status": "error", "message": f"Unknown voice command: {text}\nSupported: turn on/off, brightness X%, preset X%, status"}
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = request.get("action")
        
        if action == "control_device":
            device_action = request.get("device_action")
            return asyncio.run(self.control_device(device_action))
            
        elif action == "voice_command":
            text = request.get("text", "")
            return self.process_voice_command(text)
            
        elif action == "health_check":
            return {
                "status": "healthy",
                "service": "SimpleSmartHomeAgent",
                "port": self.port,
                "device": "Tapo L520 at 192.168.100.63"
            }
            
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def run(self):
        """Main agent loop"""
        self.logger.info("🏠 Simple Smart Home Agent started!")
        
        try:
            while True:
                try:
                    # Wait for request
                    request = self.socket.recv_json()
                    self.logger.info(f"📨 Received: {request}")
                    
                    # Process request
                    response = self.handle_request(request)
                    
                    # Send response
                    self.socket.send_json(response)
                    self.logger.info(f"📤 Sent: {response}")
                    
                except zmq.ZMQError as e:
                    self.logger.error(f"ZMQ Error: {e}")
                    break
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}")
                    error_response = {"status": "error", "message": str(e)}
                    self.socket.send_json(error_response)
                    
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            self.socket.close()
            self.context.term()

if __name__ == "__main__":
    agent = SimpleSmartHomeAgent()
    agent.run()
