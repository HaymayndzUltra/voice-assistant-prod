#!/usr/bin/env python3
"""
Smart Home Agent - Tapo Device Control with AI Integration
Integrates with hybrid API manager for voice control
"""

import asyncio
import json
import logging
from common.utils.log_setup import configure_logging
import os
import sys
import time
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project paths - use standard main_pc_code path management
import os
from pathlib import Path
from common.utils.env_standardizer import get_env
from common.core.base_agent import BaseAgent
from main_pc_code.agents.error_publisher import ErrorPublisher
project_root = Path(__file__).parent.parent.parent
# Removed from common.core.base_agent import BaseAgent
from common.hybrid_api_manager import api_manager

# Tapo device control
try:
    from plugp100.common.credentials import AuthCredential
    from plugp100.new.device_factory import connect, DeviceConnectConfiguration
    TAPO_AVAILABLE = True
except ImportError:
    TAPO_AVAILABLE = False
    logging.warning("plugp100 not available. Install with: pip install plugp100")

class SmartHomeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SmartHomeAgent",
            port=int(os.getenv('PORT', 7125)),
            health_port=int(os.getenv('HEALTH_PORT', 8125))
        )
        
        # Tapo credentials
        self.tapo_username = os.getenv('TAPO_USERNAME', 'dagsgarcia8@gmail.com')
        self.tapo_password = os.getenv('TAPO_PASSWORD', 'Prof2025!')
        
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
        
        # Initialize thread executor for async operations
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="TapoControl")
        
        # Initialize devices synchronously
        self.initialize_devices_sync()
        
    def initialize_devices_sync(self):
        """Initialize known Tapo devices synchronously"""
        if not TAPO_AVAILABLE:
            self.logger.error("plugp100 not available. Cannot control Tapo devices.")
            return
            
        if not self.tapo_username or not self.tapo_password:
            self.logger.error("Tapo credentials not set. Check TAPO_USERNAME and TAPO_PASSWORD")
            return
            
        self.logger.info("Initializing Tapo devices...")
        
        # Create a new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._initialize_devices_async())
        finally:
            loop.close()
        
        self.logger.info(f"Device initialization complete. Connected: {len(self.devices)} devices")
    
    async def _initialize_devices_async(self):
        """Async helper for device initialization"""
        credentials = AuthCredential(self.tapo_username, self.tapo_password)
        
        for ip, device_info in self.known_devices.items():
            try:
                device_type = device_info["type"]
                device_name = device_info["name"]
                
                # Create device configuration
                device_configuration = DeviceConnectConfiguration(
                    host=ip, 
                    credentials=credentials
                )
                
                # Connect to device
                device = await connect(device_configuration)
                await device.update()
                
                self.devices[device_name] = {
                    "device": device,
                    "ip": ip,
                    "type": device_type,
                    "protocol": device.protocol_version,
                    "components": str(device.get_device_components),
                    "last_update": time.time()
                }
                
                self.logger.info(f"✅ Connected to {device_name} ({device_type}) at {ip} using {device.protocol_version}")
                
                # Initialize device state
                self.device_states[device_name] = {
                    "online": True,
                    "on": getattr(device, 'is_on', False),
                    "last_update": time.time()
                }
                
            except Exception as e:
                self.logger.error(f"❌ Failed to connect to {device_name} at {ip}: {e}")
                # Initialize offline state
                self.device_states[device_name] = {
                    "online": False,
                    "last_update": time.time()
                }
    
    def control_device_sync(self, device_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control a smart home device synchronously - SIMPLE WORKING VERSION"""
        self.logger.info(f"Controlling device: {device_name} -> {action}")
        
        # Use the EXACT working approach - no thread executor complications
        try:
            import asyncio
            from plugp100.common.credentials import AuthCredential  
            from plugp100.new.device_factory import connect, DeviceConnectConfiguration
            
            async def simple_control():
                # EXACT same code that works in direct test
                credentials = AuthCredential('dagsgarcia8@gmail.com', 'Prof2025!')
                device_config = DeviceConnectConfiguration(host='192.168.100.63', credentials=credentials)
                
                device = await connect(device_config)
                await device.update()
                
                if action == "turn_on":
                    await device.turn_on()
                    result = "✅ Light turned on through agent!"
                elif action == "turn_off":
                    await device.turn_off()
                    result = "✅ Light turned off through agent!"
                else:
                    result = f"Unknown action: {action}"
                
                # Close properly
                if hasattr(device, 'client'):
                    await device.client.close()
                
                return {"status": "success", "message": result}
            
            # Run the async function directly
            return asyncio.run(simple_control())
            
        except Exception as e:
            self.logger.error(f"Device control failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def _run_async_control(self, device_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Run async device control - WORKING VERSION"""
        # Use the EXACT working approach without complex threading
        import asyncio
        try:
            return asyncio.run(self._simple_device_control(action))
        except Exception as e:
            self.logger.error(f"Device control failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _simple_device_control(self, action: str) -> Dict[str, Any]:
        """EXACT WORKING DEVICE CONTROL - Same as successful test"""
        from plugp100.common.credentials import AuthCredential  
        from plugp100.new.device_factory import connect, DeviceConnectConfiguration
        
        try:
            # EXACT same code that works in direct test
            credentials = AuthCredential('dagsgarcia8@gmail.com', 'Prof2025!')
            device_config = DeviceConnectConfiguration(host='192.168.100.63', credentials=credentials)
            
            device = await connect(device_config)
            await device.update()
            
            if action == "turn_on":
                await device.turn_on()
                result = "✅ Light turned on!"
            elif action == "turn_off":
                await device.turn_off()
                result = "✅ Light turned off!"
            else:
                result = f"Unknown action: {action}"
            
            # Close properly
            if hasattr(device, 'client'):
                await device.client.close()
            
            return {"status": "success", "message": result}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _control_device_fresh_connection(self, device_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control device with fresh connection - WORKING VERSION"""
        try:
            self.logger.info(f"🔄 Fresh connection control: {device_name} -> {action}")
            
            # WORKING APPROACH - Direct credentials, exact same as working test
            from plugp100.common.credentials import AuthCredential
            from plugp100.new.device_factory import connect, DeviceConnectConfiguration
            
            credentials = AuthCredential('dagsgarcia8@gmail.com', 'Prof2025!')
            device_config = DeviceConnectConfiguration(
                host="192.168.100.63",
                credentials=credentials
            )
            
            device = await connect(device_config)
            await device.update()
            
            # Execute control action
            if action == "turn_on":
                await device.turn_on()
                result = "✅ Device turned on successfully"
            elif action == "turn_off":
                await device.turn_off()
                result = "✅ Device turned off successfully"
            else:
                result = f"Unknown action: {action}"
            
            # Proper cleanup
            if hasattr(device, 'client'):
                await device.client.close()
            
            self.logger.info(f"✅ Control successful: {result}")
            return {"status": "success", "message": result}
                    
        except Exception as e:
            self.logger.error(f"❌ Fresh connection control failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _control_device_async(self, device_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Async device control helper"""
        device_obj = self.devices[device_name]["device"]
        
        if action == "turn_on":
            await device_obj.turn_on()
            await self._update_device_state_async(device_name)
            return {"status": "success", "message": f"{device_name} turned on"}
            
        elif action == "turn_off":
            await device_obj.turn_off()
            await self._update_device_state_async(device_name)
            return {"status": "success", "message": f"{device_name} turned off"}
            
        elif action == "set_brightness":
            brightness = kwargs.get("brightness", 100)
            if 1 <= brightness <= 100:
                if hasattr(device_obj, 'set_brightness'):
                    await device_obj.set_brightness(brightness)
                elif hasattr(device_obj, 'setBrightness'):
                    await device_obj.setBrightness(brightness)
                await self._update_device_state_async(device_name)
                return {"status": "success", "message": f"{device_name} brightness set to {brightness}%"}
            else:
                return {"status": "error", "message": "Brightness must be 1-100"}
                
        elif action == "set_color_temp":
            color_temp = kwargs.get("color_temp", 2700)
            if 2500 <= color_temp <= 6500:
                if hasattr(device_obj, 'set_color_temperature'):
                    await device_obj.set_color_temperature(color_temp)
                elif hasattr(device_obj, 'setColorTemp'):
                    await device_obj.setColorTemp(color_temp)
                await self._update_device_state_async(device_name)
                return {"status": "success", "message": f"{device_name} color temperature set to {color_temp}K"}
            else:
                return {"status": "error", "message": "Color temperature must be 2500-6500K"}
                
        elif action == "toggle":
            current_state = self.device_states.get(device_name, {}).get("on", False)
            if current_state:
                return await self._control_device_async(device_name, "turn_off")
            else:
                return await self._control_device_async(device_name, "turn_on")
                
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def update_device_state_sync(self, device_name: str):
        """Update device state synchronously"""
        if device_name not in self.devices:
            return
            
        try:
            # Create a new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._update_device_state_async(device_name))
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"Failed to update {device_name} state: {e}")
            self.device_states[device_name] = {
                "online": False,
                "last_update": time.time()
            }
    
    async def _update_device_state_async(self, device_name: str):
        """Update device state asynchronously"""
        device_obj = self.devices[device_name]["device"]
        
        # Update device state from the device
        await device_obj.update()
        
        # Get device information
        brightness = None
        color_temp = None
        
        # Try to get brightness if available
        if hasattr(device_obj, 'brightness'):
            brightness = device_obj.brightness
        
        # Try to get color temperature if available
        if hasattr(device_obj, 'color_temperature'):
            color_temp = device_obj.color_temperature
            
        self.device_states[device_name] = {
            "online": True,
            "on": getattr(device_obj, 'is_on', False),
            "brightness": brightness,
            "color_temp": color_temp,
            "last_update": time.time(),
            "protocol": getattr(device_obj, 'protocol_version', 'unknown'),
            "device_type": str(type(device_obj))
        }
    
    def get_device_status_sync(self) -> Dict[str, Any]:
        """Get status of all devices synchronously"""
        # Update device states
        for device_name in self.devices.keys():
            self.update_device_state_sync(device_name)
            
        return {
            "status": "success",
            "devices": self.device_states,
            "total_devices": len(self.devices),
            "voice_control": self.voice_control,
            "intelligent_control": self.intelligent_control
        }
    
    def process_voice_command_sync(self, text: str) -> Dict[str, Any]:
        """Process natural language voice commands synchronously"""
        if not self.voice_control:
            return {"status": "disabled", "message": "Voice control is disabled"}
            
        text = text.lower().strip()
        
        # Simple command patterns
        if any(word in text for word in ["turn on", "switch on", "open"]):
            if "light" in text or "living room" in text:
                return self.control_device_sync("Living Room Light", "turn_on")
                
        elif any(word in text for word in ["turn off", "switch off", "close"]):
            if "light" in text or "living room" in text:
                return self.control_device_sync("Living Room Light", "turn_off")
                
        elif any(word in text for word in ["bright", "dim", "brightness"]):
            # Extract percentage if available
            import re
            percent_match = re.search(r'(\d+)%?', text)
            if percent_match:
                brightness = int(percent_match.group(1))
                return self.control_device_sync("Living Room Light", "set_brightness", brightness=brightness)
            else:
                # Default bright/dim
                brightness = 80 if "bright" in text else 20
                return self.control_device_sync("Living Room Light", "set_brightness", brightness=brightness)
                
        elif any(word in text for word in ["warm", "cool", "temperature"]):
            if "warm" in text:
                return self.control_device_sync("Living Room Light", "set_color_temp", color_temp=2700)
            elif "cool" in text:
                return self.control_device_sync("Living Room Light", "set_color_temp", color_temp=5000)
                
        return {"status": "unknown", "message": "Command not recognized"}
    
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
                
                # Create device instance (using P100 base class for all Tapo devices)
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
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests synchronously"""
        action = request.get("action")
        
        if action == "control_device":
            device_name = request.get("device_name")
            device_action = request.get("device_action")
            parameters = request.get("parameters", {})
            return self.control_device_sync(device_name, device_action, **parameters)
            
        elif action == "voice_command":
            text = request.get("text", "")
            return self.process_voice_command_sync(text)
            
        elif action == "get_status":
            return self.get_device_status_sync()
            
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
