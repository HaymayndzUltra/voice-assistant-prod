#!/usr/bin/env python3
"""
NATS Error Bus Dashboard
=======================
Web-based dashboard for monitoring and managing system errors
Provides real-time error tracking, analysis, and resolution tools
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import redis

from .nats_error_bus import NATSErrorBus, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

class ErrorDashboard:
    """Web dashboard for error monitoring and management"""
    
    def __init__(self, 
                 nats_servers: List[str] = None,
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 port: int = 8080):
        self.nats_servers = nats_servers or ["nats://localhost:4222"]
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.port = port
        
        # Flask app setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'error-dashboard-secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Error bus and Redis connections
        self.error_bus: Optional[NATSErrorBus] = None
        self.redis_client = None
        
        # Error statistics cache
        self.error_stats = {
            "total_errors": 0,
            "critical_errors": 0,
            "agents_with_errors": 0,
            "last_updated": None
        }
        
        self._setup_routes()
        self._setup_socket_events()
    
    async def initialize(self):
        """Initialize connections to NATS and Redis"""
        try:
            # Connect to NATS error bus
            self.error_bus = NATSErrorBus(self.nats_servers, "error_dashboard")
            await self.error_bus.connect()
            
            # Connect to Redis
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            self.redis_client.ping()
            
            # Subscribe to real-time error events
            await self._setup_error_subscriptions()
            
            logger.info("✅ Error Dashboard initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Error Dashboard: {e}")
            raise
    
    async def _setup_error_subscriptions(self):
        """Subscribe to real-time error events for live updates"""
        if not self.error_bus:
            return
        
        # Subscribe to all error events
        await self.error_bus.nc.subscribe(
            "errors.>",
            cb=self._handle_real_time_error
        )
        
        logger.info("✅ Real-time error subscriptions active")
    
    async def _handle_real_time_error(self, msg):
        """Handle real-time error events and push to dashboard"""
        try:
            error_data = json.loads(msg.data.decode())
            
            # Update statistics
            await self._update_error_stats()
            
            # Push to connected clients via WebSocket
            self.socketio.emit('new_error', {
                'error': error_data,
                'stats': self.error_stats
            })
            
        except Exception as e:
            logger.warning(f"Failed to handle real-time error: {e}")
    
    async def _update_error_stats(self):
        """Update error statistics cache"""
        try:
            if not self.redis_client:
                return
            
            # Get health data from Redis
            health_keys = self.redis_client.keys("agent:health:*")
            ready_keys = self.redis_client.keys("agent:ready:*")
            
            # Get recent errors (last 24 hours)
            recent_errors = await self._get_recent_errors(hours=24)
            
            # Calculate statistics
            critical_errors = len([e for e in recent_errors if e.get('severity') in ['critical', 'fatal']])
            agents_with_errors = len(set(e.get('agent_name') for e in recent_errors))
            
            self.error_stats = {
                "total_errors": len(recent_errors),
                "critical_errors": critical_errors,
                "agents_with_errors": agents_with_errors,
                "total_agents": len(health_keys),
                "ready_agents": len(ready_keys),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Failed to update error stats: {e}")
    
    async def _get_recent_errors(self, hours: int = 24) -> List[Dict]:
        """Get recent errors from all agents"""
        if not self.error_bus:
            return []
        
        try:
            # Query JetStream for recent errors from all agents
            consumer = await self.error_bus.js.subscribe(
                "errors.>",
                durable="dashboard_error_query"
            )
            
            errors = []
            start_time = datetime.now() - timedelta(hours=hours)
            
            async for msg in consumer.messages:
                try:
                    error_data = json.loads(msg.data.decode())
                    error_time = datetime.fromisoformat(error_data["timestamp"])
                    
                    if error_time >= start_time:
                        errors.append(error_data)
                    
                    await msg.ack()
                    
                    # Limit results for performance
                    if len(errors) >= 5000:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to parse error message: {e}")
                    await msg.ack()
            
            return errors
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent errors: {e}")
            return []
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('error_dashboard.html')
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get current error statistics"""
            return jsonify(self.error_stats)
        
        @self.app.route('/api/errors')
        def get_errors():
            """Get recent errors with filtering"""
            hours = int(request.args.get('hours', 24))
            severity = request.args.get('severity')
            agent = request.args.get('agent')
            
            # This would be async in real implementation
            # For now, return cached data
            return jsonify({
                "errors": [],
                "total": 0,
                "message": "Async error retrieval not implemented in this example"
            })
        
        @self.app.route('/api/agents')
        def get_agents():
            """Get agent health status"""
            if not self.redis_client:
                return jsonify({"error": "Redis not connected"})
            
            try:
                agents = {}
                
                # Get health data
                health_keys = self.redis_client.keys("agent:health:*")
                for key in health_keys:
                    agent_name = key.split(":")[-1]
                    health_data = self.redis_client.get(key)
                    if health_data:
                        agents[agent_name] = json.loads(health_data)
                
                # Get ready signals
                ready_keys = self.redis_client.keys("agent:ready:*")
                for key in ready_keys:
                    agent_name = key.split(":")[-1]
                    if agent_name in agents:
                        agents[agent_name]["ready"] = True
                    else:
                        ready_data = self.redis_client.get(key)
                        if ready_data:
                            agents[agent_name] = {
                                "ready": True,
                                "ready_data": json.loads(ready_data)
                            }
                
                return jsonify({"agents": agents})
                
            except Exception as e:
                return jsonify({"error": str(e)})
        
        @self.app.route('/api/errors/resolve', methods=['POST'])
        def resolve_error():
            """Mark an error as resolved"""
            data = request.get_json()
            error_id = data.get('error_id')
            resolution_notes = data.get('resolution_notes', '')
            
            # Implementation would update error in NATS JetStream
            return jsonify({
                "success": True,
                "message": f"Error {error_id} marked as resolved"
            })
    
    def _setup_socket_events(self):
        """Setup SocketIO events for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            emit('stats_update', self.error_stats)
            logger.info("Dashboard client connected")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            logger.info("Dashboard client disconnected")
        
        @self.socketio.on('request_update')
        def handle_update_request():
            """Handle manual update request"""
            asyncio.create_task(self._update_error_stats())
            emit('stats_update', self.error_stats)
    
    def run(self, debug=False):
        """Run the dashboard server"""
        logger.info(f"🚀 Starting Error Dashboard on port {self.port}")
        self.socketio.run(
            self.app,
            host='0.0.0.0',
            port=self.port,
            debug=debug
        )

# HTML Template for the dashboard
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error Bus Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2em; font-weight: bold; margin-bottom: 10px; }
        .stat-label { color: #666; font-size: 0.9em; }
        .critical { color: #e74c3c; }
        .warning { color: #f39c12; }
        .success { color: #27ae60; }
        .error-list { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .error-item { border-bottom: 1px solid #eee; padding: 15px 0; }
        .error-item:last-child { border-bottom: none; }
        .error-severity { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; }
        .severity-critical { background-color: #e74c3c; }
        .severity-error { background-color: #f39c12; }
        .severity-warning { background-color: #f1c40f; color: #333; }
        .severity-info { background-color: #3498db; }
        .update-time { color: #666; font-size: 0.8em; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 AI System Error Bus Dashboard</h1>
            <p>Real-time error monitoring and system health tracking</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number critical" id="total-errors">0</div>
                <div class="stat-label">Total Errors (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-number critical" id="critical-errors">0</div>
                <div class="stat-label">Critical Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-number warning" id="agents-with-errors">0</div>
                <div class="stat-label">Agents with Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-number success" id="ready-agents">0</div>
                <div class="stat-label">Ready Agents</div>
            </div>
        </div>
        
        <div class="error-list">
            <h2>Recent Errors</h2>
            <div id="error-items">
                <p>Loading errors...</p>
            </div>
        </div>
        
        <div class="update-time" id="last-update">
            Last updated: Never
        </div>
    </div>

    <script>
        const socket = io();
        
        socket.on('connect', function() {
            console.log('Connected to Error Dashboard');
        });
        
        socket.on('stats_update', function(stats) {
            document.getElementById('total-errors').textContent = stats.total_errors || 0;
            document.getElementById('critical-errors').textContent = stats.critical_errors || 0;
            document.getElementById('agents-with-errors').textContent = stats.agents_with_errors || 0;
            document.getElementById('ready-agents').textContent = stats.ready_agents || 0;
            
            if (stats.last_updated) {
                document.getElementById('last-update').textContent = 
                    'Last updated: ' + new Date(stats.last_updated).toLocaleString();
            }
        });
        
        socket.on('new_error', function(data) {
            console.log('New error received:', data.error);
            // Update stats
            socket.emit('stats_update', data.stats);
            
            // Add error to list (implementation depends on UI design)
            const errorList = document.getElementById('error-items');
            const errorItem = document.createElement('div');
            errorItem.className = 'error-item';
            errorItem.innerHTML = `
                <span class="error-severity severity-${data.error.severity}">${data.error.severity.toUpperCase()}</span>
                <strong>${data.error.agent_name}</strong>: ${data.error.message}
                <div style="font-size: 0.8em; color: #666; margin-top: 5px;">
                    ${new Date(data.error.timestamp).toLocaleString()} | Category: ${data.error.category}
                </div>
            `;
            errorList.prepend(errorItem);
            
            // Keep only latest 20 errors
            while (errorList.children.length > 20) {
                errorList.removeChild(errorList.lastChild);
            }
        });
        
        // Request update every 30 seconds
        setInterval(function() {
            socket.emit('request_update');
        }, 30000);
    </script>
</body>
</html>
'''

def create_dashboard_template():
    """Create the dashboard HTML template file"""
    import os
    
    # Create templates directory
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Write template file
    template_path = os.path.join(templates_dir, 'error_dashboard.html')
    with open(template_path, 'w') as f:
        f.write(DASHBOARD_TEMPLATE)
    
    return template_path

# CLI runner
if __name__ == "__main__":
    import sys
    
    # Create template file
    create_dashboard_template()
    
    async def main():
        dashboard = ErrorDashboard(port=8080)
        await dashboard.initialize()
        dashboard.run(debug=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Error Dashboard stopped")
        sys.exit(0)
