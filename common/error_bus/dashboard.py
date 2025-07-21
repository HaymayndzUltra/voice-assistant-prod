
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
NATS Error Bus Dashboard
Real-time error monitoring and analysis dashboard
"""

import asyncio
import nats
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List
import time

class ErrorDashboard:
    """Real-time error monitoring dashboard"""
    
    def __init__(self, nats_servers: List[str] = None):
        self.nats_servers = nats_servers or ["nats://localhost:4222"]
        self.nc = None
        self.js = None
        
        # Statistics
        self.error_counts = defaultdict(int)
        self.error_by_agent = defaultdict(int)
        self.error_by_severity = defaultdict(int)
        self.error_timeline = []
        self.flood_alerts = []
        
        # Configuration
        self.dashboard_update_interval = 5  # seconds
        self.max_timeline_entries = 1000
        
    async def start(self):
        """Start the dashboard"""
        # Connect to NATS
        self.nc = await nats.connect(servers=self.nats_servers)
        self.js = self.nc.jetstream()
        
        # Subscribe to all error messages
        await self.nc.subscribe("errors.>", cb=self._handle_error_message)
        
        # Start dashboard updates
        asyncio.create_task(self._dashboard_loop())
        
        print("Error Dashboard started")
    
    async def _handle_error_message(self, msg):
        """Handle incoming error messages"""
        try:
            error_data = json.loads(msg.data.decode())
            
            # Update statistics
            self.error_counts[error_data["error_type"]] += 1
            self.error_by_agent[error_data["source_agent"]] += 1
            self.error_by_severity[error_data["severity"]] += 1
            
            # Add to timeline
            self.error_timeline.append({
                "timestamp": error_data["timestamp"],
                "agent": error_data["source_agent"],
                "type": error_data["error_type"],
                "severity": error_data["severity"],
                "message": error_data["message"]
            })
            
            # Keep timeline size manageable
            if len(self.error_timeline) > self.max_timeline_entries:
                self.error_timeline = self.error_timeline[-self.max_timeline_entries:]
            
            # Check for flood patterns
            await self._check_flood_patterns()
            
        except Exception as e:
            print(f"Error processing dashboard message: {e}")
    
    async def _check_flood_patterns(self):
        """Check for error flood patterns"""
        now = datetime.now()
        recent_errors = [
            err for err in self.error_timeline 
            if datetime.fromisoformat(err["timestamp"]) > now - timedelta(minutes=5)
        ]
        
        # Check for floods by agent
        agent_counts = Counter(err["agent"] for err in recent_errors)
        for agent, count in agent_counts.items():
            if count > 20:  # More than 20 errors in 5 minutes
                self.flood_alerts.append({
                    "timestamp": now.isoformat(),
                    "type": "AGENT_FLOOD",
                    "agent": agent,
                    "count": count,
                    "message": f"Agent {agent} generated {count} errors in 5 minutes"
                })
        
        # Keep only recent alerts
        self.flood_alerts = [
            alert for alert in self.flood_alerts
            if datetime.fromisoformat(alert["timestamp"]) > now - timedelta(hours=1)
        ]
    
    async def _dashboard_loop(self):
        """Dashboard update loop"""
        while True:
            await asyncio.sleep(self.dashboard_update_interval)
            self._print_dashboard()
    
    def _print_dashboard(self):
        """Print dashboard to console"""
        print("\n" + "="*80)
        print(f"🚨 ERROR BUS DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Error counts by severity
        print("\n📊 ERRORS BY SEVERITY:")
        for severity in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
            count = self.error_by_severity.get(severity, 0)
            print(f"   {severity}: {count}")
        
        # Top error types
        print("\n🔝 TOP ERROR TYPES:")
        top_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for error_type, count in top_errors:
            print(f"   {error_type}: {count}")
        
        # Top error agents
        print("\n🤖 TOP ERROR AGENTS:")
        top_agents = sorted(self.error_by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
        for agent, count in top_agents:
            print(f"   {agent}: {count}")
        
        # Recent errors
        print("\n🕐 RECENT ERRORS (Last 10):")
        recent = self.error_timeline[-10:]
        for error in recent:
            timestamp = datetime.fromisoformat(error["timestamp"]).strftime("%H:%M:%S")
            print(f"   {timestamp} [{error['severity']}] {error['agent']}: {error['message'][:50]}...")
        
        # Flood alerts
        if self.flood_alerts:
            print("\n🚨 FLOOD ALERTS:")
            for alert in self.flood_alerts[-5:]:  # Last 5 alerts
                timestamp = datetime.fromisoformat(alert["timestamp"]).strftime("%H:%M:%S")
                print(f"   {timestamp} {alert['message']}")
        
        print("="*80)
    
    def get_stats(self) -> Dict:
        """Get dashboard statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_by_severity": dict(self.error_by_severity),
            "error_by_agent": dict(self.error_by_agent),
            "top_error_types": dict(sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_errors": self.error_timeline[-50:],
            "flood_alerts": self.flood_alerts[-10:]
        }

async def main():
    """Run the error dashboard"""
    dashboard = ErrorDashboard()
    await dashboard.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nDashboard stopped")

if __name__ == "__main__":
    asyncio.run(main())
