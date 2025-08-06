#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Alert Manager Agent
------------------
Manages alerts and notifications for the distributed voice assistant system.

Responsibilities:
- Receives alerts from various monitoring agents
- Categorizes and prioritizes alerts by severity
- Manages alert escalation and routing
- Sends notifications through multiple channels
- Tracks alert history and resolution status
- Provides alert aggregation and deduplication
- Manages alert rules and thresholds

This agent uses ZMQ REP socket on port 5593 to receive commands and alert requests,
and a PUB socket on port 5594 to broadcast alert notifications.
"""

import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
import datetime
from collections import defaultdict, deque
import sqlite3
import hashlib


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root()
from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)

# Import config parser utility with fallback
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
from common.env_helpers import get_env
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args = parse_agent_args()
except ImportError:
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = PathManager.join_path("logs", str(PathManager.get_logs_dir() / "alert_manager_agent.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)

logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AlertManagerAgent")

# ZMQ ports
ALERT_MANAGER_PORT = 5593
ALERT_MANAGER_HEALTH_PORT = 5594

# Alert severity levels
ALERT_SEVERITY_INFO = "info"
ALERT_SEVERITY_WARNING = "warning"
ALERT_SEVERITY_ERROR = "error"
ALERT_SEVERITY_CRITICAL = "critical"

# Alert status
ALERT_STATUS_ACTIVE = "active"
ALERT_STATUS_ACKNOWLEDGED = "acknowledged"
ALERT_STATUS_RESOLVED = "resolved"
ALERT_STATUS_CLOSED = "closed"

class Alert:
    """Class representing an alert"""
    def __init__(self, alert_id: str, title: str, message: str, severity: str = ALERT_SEVERITY_INFO,
                 source: str = None, tags: Dict[str, str] = None):
        self.alert_id = alert_id
        self.title = title
        self.message = message
        self.severity = severity
        self.source = source
        self.tags = tags or {}
        self.timestamp = time.time()
        self.status = ALERT_STATUS_ACTIVE
        self.acknowledged_by = None
        self.acknowledged_at = None
        self.resolved_by = None
        self.resolved_at = None
        self.notes = []
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "notes": self.notes
        }

class AlertManagerAgent:
    """Main alert manager agent class"""
    def __init__(self, port=None):
        try:
            # Set up ports
            self.main_port = port if port else ALERT_MANAGER_PORT
            self.health_port = self.main_port + 1
            self.health_rep_port = self.main_port + 2  # 5595
            
            # Initialize ZMQ context and server socket
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.main_port}")
            
            # Initialize PUB socket for alert notifications
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"AlertManagerAgent PUB socket bound to port {self.health_port}")
            
            # Initialize health REP socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_rep_port}")
            self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            
            # Alert storage
            self.active_alerts: Dict[str, Alert] = {}
            self.alert_history: deque = deque(maxlen=1000)
            self.alert_rules: Dict[str, Dict[str, Any]] = {}
            
            # Database setup
            self.db_path = Path(PathManager.join_path("data", str(PathManager.get_data_dir() / "alerts.db"))
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.db_path)
            self._create_tables()
            
            # Alert settings
            self.deduplication_window = 300  # 5 minutes
            self.escalation_delay = 1800  # 30 minutes
            
            # Monitoring threads
            self.escalation_thread = threading.Thread(target=self.escalation_loop, daemon=True)
            self.cleanup_thread = threading.Thread(target=self.cleanup_old_alerts_loop, daemon=True)
            self.running = True
            
            logger.info(f"AlertManagerAgent initialized on port {self.main_port}")
        except Exception as e:
            logger.error(f"Failed to initialize AlertManagerAgent: {str(e)}")
            raise

    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()
        
        # Alerts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY,
            alert_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            source TEXT,
            tags TEXT,
            timestamp REAL NOT NULL,
            status TEXT NOT NULL,
            acknowledged_by TEXT,
            acknowledged_at REAL,
            resolved_by TEXT,
            resolved_at REAL,
            notes TEXT
        )
        ''')
        
        # Alert rules table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY,
            rule_id TEXT UNIQUE NOT NULL,
            rule_name TEXT NOT NULL,
            conditions TEXT NOT NULL,
            actions TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
        
        self.conn.commit()
        logger.info("Database tables created")

    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'AlertManagerAgent',
            'timestamp': datetime.datetime.now().isoformat(),
            'escalation_thread_alive': self.escalation_thread.is_alive() if hasattr(self, 'escalation_thread') else False,
            'cleanup_thread_alive': self.cleanup_thread.is_alive() if hasattr(self, 'cleanup_thread') else False,
            'active_alerts': len(self.active_alerts),
            'port': self.main_port
        }

    def create_alert(self, title: str, message: str, severity: str = ALERT_SEVERITY_INFO,
                    source: str = None, tags: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a new alert"""
        try:
            # Generate alert ID
            alert_hash = hashlib.md5(f"{title}:{message}:{source}:{time.time()}".encode().hexdigest()
            alert_id = f"alert_{alert_hash[:8]}"
            
            # Check for duplicate alerts
            if self._is_duplicate_alert(title, message, source):
                return {'status': 'error', 'message': 'Duplicate alert detected'}
            
            # Create alert
            alert = Alert(alert_id, title, message, severity, source, tags)
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # Store in database
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO alerts (alert_id, title, message, severity, source, tags, timestamp, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (alert_id, title, message, severity, source, json.dumps(tags or {}), 
                  alert.timestamp, alert.status, json.dumps(alert.notes))
            self.conn.commit()
            
            # Publish alert notification
            self.pub_socket.send_json({
                'type': 'alert_created',
                'alert': alert.to_dict()
            })
            
            logger.info(f"Created alert: {alert_id} - {title} ({severity})")
            return {
                'status': 'success',
                'message': 'Alert created successfully',
                'alert_id': alert_id,
                'alert': alert.to_dict()
            }
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return {'status': 'error', 'message': str(e)}

    def _is_duplicate_alert(self, title: str, message: str, source: str) -> bool:
        """Check if an alert is a duplicate within the deduplication window"""
        current_time = time.time()
        cutoff_time = current_time - self.deduplication_window
        
        for alert in self.active_alerts.values():
            if (alert.title == title and alert.message == message and 
                alert.source == source and alert.timestamp > cutoff_time):
                return True
        return False

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: str = None) -> Dict[str, Any]:
        """Acknowledge an alert"""
        try:
            if alert_id not in self.active_alerts:
                return {'status': 'error', 'message': 'Alert not found'}
            
            alert = self.active_alerts[alert_id]
            alert.status = ALERT_STATUS_ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = time.time()
            
            if notes:
                alert.notes.append({
                    'timestamp': time.time(),
                    'user': acknowledged_by,
                    'action': 'acknowledged',
                    'note': notes
                })
            
            # Update database
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE alerts SET status = ?, acknowledged_by = ?, acknowledged_at = ?, notes = ?
            WHERE alert_id = ?
            ''', (alert.status, acknowledged_by, alert.acknowledged_at, 
                  json.dumps(alert.notes), alert_id)
            self.conn.commit()
            
            # Publish acknowledgment notification
            self.pub_socket.send_json({
                'type': 'alert_acknowledged',
                'alert_id': alert_id,
                'acknowledged_by': acknowledged_by
            })
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return {'status': 'success', 'message': 'Alert acknowledged successfully'}
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return {'status': 'error', 'message': str(e)}

    def resolve_alert(self, alert_id: str, resolved_by: str, notes: str = None) -> Dict[str, Any]:
        """Resolve an alert"""
        try:
            if alert_id not in self.active_alerts:
                return {'status': 'error', 'message': 'Alert not found'}
            
            alert = self.active_alerts[alert_id]
            alert.status = ALERT_STATUS_RESOLVED
            alert.resolved_by = resolved_by
            alert.resolved_at = time.time()
            
            if notes:
                alert.notes.append({
                    'timestamp': time.time(),
                    'user': resolved_by,
                    'action': 'resolved',
                    'note': notes
                })
            
            # Update database
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE alerts SET status = ?, resolved_by = ?, resolved_at = ?, notes = ?
            WHERE alert_id = ?
            ''', (alert.status, resolved_by, alert.resolved_at, 
                  json.dumps(alert.notes), alert_id)
            self.conn.commit()
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            # Publish resolution notification
            self.pub_socket.send_json({
                'type': 'alert_resolved',
                'alert_id': alert_id,
                'resolved_by': resolved_by
            })
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return {'status': 'success', 'message': 'Alert resolved successfully'}
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_active_alerts(self, severity: str = None) -> Dict[str, Any]:
        """Get all active alerts, optionally filtered by severity"""
        try:
            alerts = {}
            for alert_id, alert in self.active_alerts.items():
                if severity is None or alert.severity == severity:
                    alerts[alert_id] = alert.to_dict()
            
            return {
                'status': 'success',
                'alerts': alerts,
                'count': len(alerts)
            }
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_alert_history(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert history for the specified time range"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            recent_alerts = [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
            
            return {
                'status': 'success',
                'alerts': [alert.to_dict() for alert in recent_alerts],
                'count': len(recent_alerts)
            }
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return {'status': 'error', 'message': str(e)}

    def add_alert_rule(self, rule_id: str, rule_name: str, conditions: Dict[str, Any], 
                      actions: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new alert rule"""
        try:
            if rule_id in self.alert_rules:
                return {'status': 'error', 'message': 'Rule already exists'}
            
            rule = {
                'rule_id': rule_id,
                'rule_name': rule_name,
                'conditions': conditions,
                'actions': actions,
                'enabled': True
            }
            
            self.alert_rules[rule_id] = rule
            
            # Store in database
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO alert_rules (rule_id, rule_name, conditions, actions, enabled)
            VALUES (?, ?, ?, ?, ?)
            ''', (rule_id, rule_name, json.dumps(conditions), json.dumps(actions), True)
            self.conn.commit()
            
            logger.info(f"Added alert rule: {rule_id} - {rule_name}")
            return {'status': 'success', 'message': 'Alert rule added successfully'}
        except Exception as e:
            logger.error(f"Error adding alert rule: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = request.get('action', '')
        
        if action == 'health_check':
            return self._health_check()
        elif action == 'create_alert':
            return self.create_alert(
                request.get('title'),
                request.get('message'),
                request.get('severity', ALERT_SEVERITY_INFO),
                request.get('source'),
                request.get('tags')
            )
        elif action == 'acknowledge_alert':
            return self.acknowledge_alert(
                request.get('alert_id'),
                request.get('acknowledged_by'),
                request.get('notes')
            )
        elif action == 'resolve_alert':
            return self.resolve_alert(
                request.get('alert_id'),
                request.get('resolved_by'),
                request.get('notes')
            )
        elif action == 'get_active_alerts':
            return self.get_active_alerts(request.get('severity')
        elif action == 'get_alert_history':
            return self.get_alert_history(request.get('hours', 24)
        elif action == 'add_alert_rule':
            return self.add_alert_rule(
                request.get('rule_id'),
                request.get('rule_name'),
                request.get('conditions'),
                request.get('actions')
            )
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def _health_check_loop(self):
        """Health check loop for health REP socket"""
        logger.info(f"AlertManagerAgent health REP socket listening on port {self.health_rep_port}")
        while self.running:
            try:
                if self.health_socket.poll(1000) == 0:
                    continue
                message = self.health_socket.recv_json()
                if message.get("action") == "health_check":
                    response = self._health_check()
                else:
                    response = {"status": "error", "error": "Invalid health check request"}
                self.health_socket.send_json(response)
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logger.error(f"ZMQ error in health check loop: {e}")
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    def run(self):
        """Start managing alerts and handle requests"""
        logger.info(f"AlertManagerAgent starting on port {self.main_port}")
        
        # Start monitoring threads
        self.escalation_thread.start()
        self.cleanup_thread.start()
        self.health_thread.start()
        
        try:
            while self.running:
                try:
                    # Wait for messages with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()

    def escalation_loop(self):
        """Background thread for alert escalation"""
        logger.info("Starting alert escalation loop")
        while self.running:
            try:
                current_time = time.time()
                for alert_id, alert in list(self.active_alerts.items():
                    # Check if alert needs escalation
                    if (alert.status == ALERT_STATUS_ACTIVE and 
                        current_time - alert.timestamp > self.escalation_delay):
                        # Escalate alert
                        alert.severity = self._escalate_severity(alert.severity)
                        logger.warning(f"Escalated alert {alert_id} to {alert.severity}")
                        
                        # Publish escalation notification
                        self.pub_socket.send_json({
                            'type': 'alert_escalated',
                            'alert_id': alert_id,
                            'new_severity': alert.severity
                        })
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in escalation loop: {e}")
                time.sleep(60)

    def _escalate_severity(self, current_severity: str) -> str:
        """Escalate alert severity"""
        severity_levels = [ALERT_SEVERITY_INFO, ALERT_SEVERITY_WARNING, ALERT_SEVERITY_ERROR, ALERT_SEVERITY_CRITICAL]
        try:
            current_index = severity_levels.index(current_severity)
            if current_index < len(severity_levels) - 1:
                return severity_levels[current_index + 1]
        except ValueError:
            pass
        return current_severity

    def cleanup_old_alerts_loop(self):
        """Background thread for cleaning up old alerts"""
        logger.info("Starting alert cleanup loop")
        while self.running:
            try:
                # Clean up old alerts from database (older than 30 days)
                cutoff_time = time.time() - (30 * 24 * 3600)
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM alerts WHERE timestamp < ? AND status = ?', 
                             (cutoff_time, ALERT_STATUS_RESOLVED)
                deleted_count = cursor.rowcount
                self.conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old alerts")
                
                # Run cleanup every hour
                time.sleep(3600)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(3600)

    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Cleaning up AlertManagerAgent resources...")
        self.running = False
        
        if hasattr(self, 'escalation_thread'):
            self.escalation_thread.join(timeout=5)
        if hasattr(self, 'cleanup_thread'):
            self.cleanup_thread.join(timeout=5)
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        
        if hasattr(self, 'conn'):
            self.conn.close()
        
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Cleanup complete")

    def stop(self):
        """Stop the agent gracefully"""
        self.running = False

if __name__ == "__main__":
    # Create and run the Alert Manager Agent
    agent = AlertManagerAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Alert Manager Agent interrupted")
    finally:
        agent.cleanup() 