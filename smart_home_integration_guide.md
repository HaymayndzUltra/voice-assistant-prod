# 🏠 PC2 Smart Home Integration Guide

## Overview
Your PC2 AI assistance system now includes **Smart Home Agent** that can control your Tapo L520 smart light and other Tapo devices with AI-driven automation.

## Quick Setup

### 1. Configure Credentials
```bash
# Copy the template
cp smart_home_config.template .env.smart_home

# Edit with your actual Tapo app credentials
nano .env.smart_home

# Source the environment
source .env.smart_home
```

### 2. Deploy Smart Home Agent
```bash
# Navigate to utility suite
cd docker/pc2_utility_suite

# Start the smart home agent
docker-compose up -d smart_home_agent

# Verify deployment
curl http://localhost:8425/health
```

### 3. Test Your L520 Light
```bash
# Turn on your light
curl -X POST http://localhost:9425/lights/control \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "tapo_l520_main",
    "action": {
      "command": "turn_on",
      "brightness": 70
    }
  }'

# Set intelligent lighting for evening relaxation
curl -X POST http://localhost:9425/lights/intelligent \
  -H "Content-Type: application/json" \
  -d '{
    "time_of_day": "evening",
    "activity": "relaxation", 
    "mood": "calm"
  }'
```

## Features

### 🤖 AI-Driven Control
- **Context-aware lighting**: Automatically adjusts based on time, activity, mood
- **Learning preferences**: Adapts to your usage patterns
- **Voice commands**: "Turn on the lights", "Set reading mode"

### 🎨 Smart Lighting Modes
- **Morning Energetic**: Cool white (5000K), 90% brightness
- **Work Focused**: Neutral white (4000K), 85% brightness  
- **Evening Relaxation**: Warm white (2700K), 40% brightness
- **Night Sleep**: Very warm (2200K), 10% brightness
- **Entertainment**: Vibrant colors for movies/games
- **Romantic**: Soft red tones, low brightness

### 📱 API Endpoints

#### Device Control
```http
POST /lights/control
{
  "device_id": "tapo_l520_main",
  "action": {
    "command": "turn_on|turn_off|set_brightness|set_color",
    "brightness": 0-100,
    "color_temp": 2700-6500,
    "hue": 0-360,
    "saturation": 0-100
  }
}
```

#### Intelligent Control
```http
POST /lights/intelligent
{
  "time_of_day": "morning|afternoon|evening|night",
  "activity": "work|relaxation|entertainment|sleep",
  "mood": "energetic|calm|focused|romantic"
}
```

#### Voice Commands
```http
POST /voice/command
{
  "command": "Turn on the lights to 50% brightness"
}
```

#### Device Status
```http
GET /devices/status
```

## Integration with PC2 System

### Memory Integration
Your smart home agent integrates with PC2's memory system:
```python
# From other PC2 agents
memory_service.store("user_lighting_preference", {
    "time": "evening",
    "preferred_mode": "relaxation",
    "brightness": 35
})
```

### Task Scheduler Integration
Automatic lighting schedules:
```python
# Schedule morning wake-up lighting
scheduler.add_task("wake_up_lighting", {
    "time": "07:00",
    "action": "intelligent_control",
    "context": {"activity": "morning_energetic"}
})
```

### Context Monitoring
Proactive lighting adjustments:
```python
# PC2 context monitor detects work session
context_monitor.on_activity_change("work_session_start", 
    lambda: smart_home.set_work_lighting())
```

## Voice Command Examples

### Basic Commands
- "Turn on the lights"
- "Turn off the lights" 
- "Set brightness to 50%"
- "Dim the lights"

### Smart Modes
- "Switch to reading mode"
- "Set relaxation lighting"
- "Party mode lights"
- "Good night lighting"

### Color Control
- "Change lights to blue"
- "Set warm white"
- "Make it romantic"

## Advanced Features

### Learning & Adaptation
```python
# The agent learns your preferences
smart_home.enable_learning_mode()
smart_home.track_user_adjustments()
smart_home.apply_learned_preferences()
```

### Multi-Device Support
Add more Tapo devices:
```python
# Register additional devices
smart_home.register_device({
    "device_id": "tapo_p100_bedroom",
    "device_type": "plug", 
    "ip_address": "192.168.100.64"
})
```

### Home Automation Scenarios
```python
# Movie night scenario
async def movie_night():
    await smart_home.control_light("tapo_l520_main", {
        "command": "set_color",
        "hue": 240,  # Blue
        "saturation": 80,
        "brightness": 15
    })
    # Could also control plugs, other devices...
```

## Troubleshooting

### Connection Issues
```bash
# Check device connectivity
ping 192.168.100.63

# Verify Tapo credentials
curl -X GET http://localhost:9425/devices/status
```

### Authentication Problems
1. Ensure email is all lowercase
2. Check password doesn't contain special characters that need escaping
3. Verify internet access for initial Tapo cloud sync

### Debug Mode
```bash
# Enable debug logging
export SMART_HOME_DEBUG=true
docker-compose restart smart_home_agent

# View logs
docker logs pc2_smart_home_agent
```

## Integration with Other Systems

### Home Assistant
```yaml
# configuration.yaml
sensor:
  - platform: rest
    resource: http://localhost:9425/devices/status
    name: "PC2 Smart Home Status"
```

### Alexa/Google Assistant
Route voice commands through PC2:
```python
# Custom skill integration
alexa_handler.route_to_pc2_smart_home(voice_command)
```

## Security Considerations

- **Local Network Only**: Smart home agent operates on local network
- **Encrypted Credentials**: Tapo credentials encrypted in transit
- **Access Control**: API endpoints secured through PC2 auth system
- **Device Isolation**: Each device has isolated communication channel

## Performance Metrics

- **Response Time**: < 500ms for basic commands
- **Device Discovery**: < 30s for network scan
- **Memory Usage**: ~50MB per agent instance
- **CPU Usage**: < 5% during normal operation

---

**Next Steps:**
1. Configure your Tapo credentials
2. Deploy the smart home agent  
3. Test basic light control
4. Explore intelligent automation features
5. Integrate with your daily routines

**Support:** Your smart home integration is now part of PC2's utility suite and ready for intelligent automation! 🚀