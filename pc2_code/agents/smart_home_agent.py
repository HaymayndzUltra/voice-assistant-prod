#!/usr/bin/env python3
"""
Smart Home Agent - Tapo Device Control with AI Integration
Integrates with hybrid API manager for voice control
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project paths
sys.path.append('/app')
sys.path.append('/home/haymayndz/AI_System_Monorepo')

from common.core.base_agent import BaseAgent
from common.hybrid_api_manager import api_manager

# Tapo device control
try:
    from PyP100 import PyL530, PyL520, PyP100
    TAPO_AVAILABLE = True
except ImportError:
    TAPO_AVAILABLE = False
    logging.warning("PyP100 not available. Install with: pip install PyP100")

class SmartHomeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SmartHomeAgent",
            port=int(os.getenv('PORT', 7125)),
            health_port=int(os.getenv('HEALTH_PORT', 8125))
        )
        
        # Tapo credentials
        self.tapo_username = os.getenv('TAPO_USERNAME')
        self.tapo_password = os.getenv('TAPO_PASSWORD')
        
        # Device management
        self.devices = {}
        self.device_states = {}
        self.last_discovery = 0
        self.discovery_interval = int(os.getenv('DEVICE_SCAN_INTERVAL', 60))
        
        # AI Integration settings
        self.voice_control = os.getenv('VOICE_CONTROL', 'enabled') == 'enabled'
        self.intelligent_control = os.getenv('INTELLIGENT_CONTROL', 'enabled') == 'enabled'
        
        # Known device from your screenshot
        self.known_devices = {
            "192.168.100.63": {
                "type": "L520",
                "name": "Living Room Light",
                "mac": "E0-D3-62-8A-72-5E"
            }
        }
        
        self.logger.info(f"SmartHomeAgent initialized. Voice control: {self.voice_control}")
        
        # Initialize devices
        asyncio.create_task(self.initialize_devices())
        
    async def initialize_devices(self):
        """Initialize known Tapo devices"""
        if not TAPO_AVAILABLE:
            self.logger.error("PyP100 not available. Cannot control Tapo devices.")
            return
            
        if not self.tapo_username or not self.tapo_password:
            self.logger.error("Tapo credentials not set. Check TAPO_USERNAME and TAPO_PASSWORD")
            return
            
        self.logger.info("Initializing Tapo devices...")
        
        for ip, device_info in self.known_devices.items():
            try:
                device_type = device_info["type"]
                device_name = device_info["name"]
                
                # Create device instance based on type
                if device_type == "L520":
                    device = PyL520.L520(ip, self.tapo_username, self.tapo_password)
                elif device_type == "L530":
                    device = PyL530.L530(ip, self.tapo_username, self.tapo_password)
                else:
                    device = PyP100.P100(ip, self.tapo_username, self.tapo_password)
                
                # Test connection
                await asyncio.to_thread(device.handshake)
                await asyncio.to_thread(device.login)
                
                # Get device info
                device_info_result = await asyncio.to_thread(device.getDeviceInfo)
                
                self.devices[device_name] = {
                    "device": device,
                    "ip": ip,
                    "type": device_type,
                    "info": device_info_result,
                    "last_update": time.time()
                }
                
                self.logger.info(f"✅ Connected to {device_name} ({device_type}) at {ip}")
                
                # Get initial state
                await self.update_device_state(device_name)
                
            except Exception as e:
                self.logger.error(f"❌ Failed to connect to {device_name} at {ip}: {e}")
    
    async def update_device_state(self, device_name: str):
        """Update device state"""
        if device_name not in self.devices:
            return
            
        try:
            device_obj = self.devices[device_name]["device"]
            device_info = await asyncio.to_thread(device_obj.getDeviceInfo)
            
            self.device_states[device_name] = {
                "online": True,
                "on": device_info.get("device_on", False),
                "brightness": device_info.get("brightness", 100),
                "color_temp": device_info.get("color_temp", 2700),
                "last_update": time.time(),
                "info": device_info
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update {device_name} state: {e}")
            self.device_states[device_name] = {
                "online": False,
                "last_update": time.time()
            }
    
    async def control_device(self, device_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control a smart home device"""
        if device_name not in self.devices:
            return {"status": "error", "message": f"Device {device_name} not found"}
            
        try:
            device_obj = self.devices[device_name]["device"]
            
            if action == "turn_on":
                await asyncio.to_thread(device_obj.turnOn)
                await self.update_device_state(device_name)
                return {"status": "success", "message": f"{device_name} turned on"}
                
            elif action == "turn_off":
                await asyncio.to_thread(device_obj.turnOff)
                await self.update_device_state(device_name)
                return {"status": "success", "message": f"{device_name} turned off"}
                
            elif action == "set_brightness":
                brightness = kwargs.get("brightness", 100)
                if 1 <= brightness <= 100:
                    await asyncio.to_thread(device_obj.setBrightness, brightness)
                    await self.update_device_state(device_name)
                    return {"status": "success", "message": f"{device_name} brightness set to {brightness}%"}
                else:
                    return {"status": "error", "message": "Brightness must be 1-100"}
                    
            elif action == "set_color_temp":
                color_temp = kwargs.get("color_temp", 2700)
                if 2500 <= color_temp <= 6500:
                    await asyncio.to_thread(device_obj.setColorTemp, color_temp)
                    await self.update_device_state(device_name)
                    return {"status": "success", "message": f"{device_name} color temperature set to {color_temp}K"}
                else:
                    return {"status": "error", "message": "Color temperature must be 2500-6500K"}
                    
            elif action == "toggle":
                current_state = self.device_states.get(device_name, {}).get("on", False)
                if current_state:
                    return await self.control_device(device_name, "turn_off")
                else:
                    return await self.control_device(device_name, "turn_on")
                    
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
                
        except Exception as e:
            self.logger.error(f"Device control failed for {device_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def process_voice_command(self, text: str) -> Dict[str, Any]:
        """Process natural language voice commands"""
        if not self.voice_control:
            return {"status": "disabled", "message": "Voice control is disabled"}
            
        text = text.lower().strip()
        
        # Simple command patterns (you can enhance with NLP)
        if any(word in text for word in ["turn on", "switch on", "open"]):
            if "light" in text or "living room" in text:
                return await self.control_device("Living Room Light", "turn_on")
                
        elif any(word in text for word in ["turn off", "switch off", "close"]):
            if "light" in text or "living room" in text:
                return await self.control_device("Living Room Light", "turn_off")
                
        elif "brightness" in text or "dim" in text or "bright" in text:
            # Extract brightness level
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                brightness = int(numbers[0])
                return await self.control_device("Living Room Light", "set_brightness", brightness=brightness)
            elif "dim" in text:
                return await self.control_device("Living Room Light", "set_brightness", brightness=30)
            elif "bright" in text:
                return await self.control_device("Living Room Light", "set_brightness", brightness=100)
                
        elif any(word in text for word in ["warm", "cool", "temperature"]):
            if "warm" in text:
                return await self.control_device("Living Room Light", "set_color_temp", color_temp=2700)
            elif "cool" in text:
                return await self.control_device("Living Room Light", "set_color_temp", color_temp=5000)
                
        # Use AI for complex commands
        if self.intelligent_control:
            return await self.ai_process_command(text)
            
        return {"status": "unknown", "message": "Command not recognized"}
    
    async def ai_process_command(self, text: str) -> Dict[str, Any]:
        """Use AI to understand complex commands"""
        try:
            # Create AI prompt for smart home control
            prompt = f"""
You are a smart home assistant. Parse this command and return JSON with the action to take:

Command: "{text}"

Available devices:
- Living Room Light (Tapo L520): can turn on/off, set brightness (1-100), set color temperature (2500-6500K)

Return JSON format:
{{
    "device": "device_name",
    "action": "turn_on|turn_off|set_brightness|set_color_temp|toggle",
    "parameters": {{"brightness": 50, "color_temp": 3000}},
    "confidence": 0.95
}}

If you can't understand the command, return {{"action": "unknown", "confidence": 0.0}}
"""
            
            # Use hybrid API manager for AI processing
            ai_response = await api_manager.llm_chat(prompt, temperature=0.1)
            
            # Parse AI response
            import json
            try:
                command_data = json.loads(ai_response)
                
                if command_data.get("action") == "unknown":
                    return {"status": "unknown", "message": "Could not understand command"}
                    
                device = command_data.get("device", "Living Room Light")
                action = command_data.get("action")
                parameters = command_data.get("parameters", {})
                
                return await self.control_device(device, action, **parameters)
                
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse AI response: {ai_response}")
                return {"status": "error", "message": "AI processing failed"}
                
        except Exception as e:
            self.logger.error(f"AI processing failed: {e}")
            return {"status": "error", "message": "AI processing unavailable"}
    
    async def get_device_status(self) -> Dict[str, Any]:
        """Get status of all devices"""
        # Update device states
        for device_name in self.devices.keys():
            await self.update_device_state(device_name)
            
        return {
            "status": "success",
            "devices": self.device_states,
            "total_devices": len(self.devices),
            "voice_control": self.voice_control,
            "intelligent_control": self.intelligent_control
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = request.get("action")
        
        if action == "control_device":
            device_name = request.get("device_name")
            device_action = request.get("device_action")
            parameters = request.get("parameters", {})
            return await self.control_device(device_name, device_action, **parameters)
            
        elif action == "voice_command":
            text = request.get("text", "")
            return await self.process_voice_command(text)
            
        elif action == "get_status":
            return await self.get_device_status()
            
        elif action == "health_check":
            return {
                "status": "healthy",
                "service": "SmartHomeAgent",
                "devices_connected": len(self.devices),
                "voice_control": self.voice_control
            }
            
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

if __name__ == "__main__":
    agent = SmartHomeAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.logger.info("SmartHomeAgent shutting down...")
    finally:
        agent.cleanup()
