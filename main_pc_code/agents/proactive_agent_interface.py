#!/usr/bin/env python3
"""
Proactive Agent Interface - Migrated to BaseAgent
Unified reminder/suggestion broadcasting service for the agent system.

This agent provides a centralized interface for other agents (Jarvis Memory, 
Digital Twin, Learning Mode) to send proactive events, reminders, and suggestions.
"""
import zmq
import json
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from queue import Queue, Empty

# BaseAgent import - REQUIRED for migration
from common.core.base_agent import BaseAgent

# Standardized utilities
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.logger_util import get_json_logger
from main_pc_code.utils.network import get_host

# Constants for proactive interface
DEFAULT_PROACTIVE_PORT = 5558
DEFAULT_BROADCAST_PORT = 5559
MAX_EVENT_QUEUE_SIZE = 1000

class ProactiveAgentInterface(BaseAgent):
    """
    Proactive Agent Interface migrated to BaseAgent inheritance.
    
    Provides a centralized service for proactive event broadcasting across
    the agent system. Other agents can send events to this interface which
    then broadcasts them to appropriate subscribers.
    """
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        """
        Initialize the Proactive Agent Interface with BaseAgent inheritance.
        
        Args:
            port: Main service port for receiving proactive events
            health_check_port: Health check port (optional, defaults to port+1)
            **kwargs: Additional configuration parameters
        """
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', 'ProactiveAgentInterface'),
            port=port or DEFAULT_PROACTIVE_PORT,
            health_check_port=health_check_port,
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Event queue for processing proactive events
        self.event_queue = Queue(maxsize=MAX_EVENT_QUEUE_SIZE)
        
        # Broadcast port for sending events to subscribers
        self.broadcast_port = DEFAULT_BROADCAST_PORT
        
        # Statistics tracking
        self.stats = {
            'events_received': 0,
            'events_broadcasted': 0,
            'events_dropped': 0,
            'last_event_time': None,
            'start_time': time.time()
        }
        
        # Set up custom sockets for proactive event handling
        self._setup_proactive_sockets()
        
        # Start background event processing
        self._start_event_processor()
        
        self.logger.info(f"{self.name} initialized successfully", extra={
            "port": self.port,
            "health_check_port": self.health_check_port,
            "broadcast_port": self.broadcast_port,
            "component": "initialization"
        })
    
    def _setup_proactive_sockets(self):
        """Set up custom ZMQ sockets for proactive event handling."""
        try:
            # PULL socket for receiving proactive events from other agents
            self.pull_socket = self.context.socket(zmq.PULL)
            self.pull_socket.bind(f"tcp://*:{self.port}")
            self.logger.info(f"Event receiver socket bound to port {self.port}")
            
            # PUB socket for broadcasting events to subscribers
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(f"tcp://*:{self.broadcast_port}")
            self.logger.info(f"Event broadcaster socket bound to port {self.broadcast_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to set up proactive sockets: {e}")
            raise
    
    def _start_event_processor(self):
        """Start background thread for processing proactive events."""
        def event_processor():
            self.logger.info("Event processor thread started")
            while self.running:
                try:
                    # Check for incoming events with timeout
                    if self.pull_socket.poll(timeout=1000):  # 1 second timeout
                        try:
                            event_data = self.pull_socket.recv_json(zmq.NOBLOCK)
                            self._process_proactive_event(event_data)
                        except zmq.Again:
                            continue
                        except Exception as e:
                            self.logger.error(f"Error receiving event: {e}")
                    
                    # Process queued events
                    self._process_event_queue()
                    
                except Exception as e:
                    self.logger.error(f"Error in event processor: {e}")
                    time.sleep(1)
            
            self.logger.info("Event processor thread stopped")
        
        self.event_processor_thread = threading.Thread(target=event_processor, daemon=True)
        self.event_processor_thread.start()
    
    def _process_proactive_event(self, event_data: Dict[str, Any]):
        """
        Process an incoming proactive event.
        
        Args:
            event_data: Event data received from an agent
        """
        try:
            # Validate event data
            if not self._validate_event_data(event_data):
                self.logger.warning("Invalid event data received", extra={
                    "event_data": event_data,
                    "component": "event_processing"
                })
                self.stats['events_dropped'] += 1
                return
            
            # Add metadata to event
            enriched_event = {
                **event_data,
                'timestamp': datetime.now().isoformat(),
                'processed_by': self.name,
                'event_id': f"evt_{int(time.time()*1000)}"
            }
            
            # Queue event for broadcasting
            try:
                self.event_queue.put_nowait(enriched_event)
                self.stats['events_received'] += 1
                self.stats['last_event_time'] = time.time()
                
                self.logger.info("Proactive event queued for broadcasting", extra={
                    "event_type": event_data.get('type', 'unknown'),
                    "event_id": enriched_event['event_id'],
                    "source_agent": event_data.get('source_agent', 'unknown'),
                    "component": "event_processing"
                })
                
            except:
                # Queue is full
                self.logger.warning("Event queue full, dropping event", extra={
                    "event_type": event_data.get('type', 'unknown'),
                    "component": "event_processing"
                })
                self.stats['events_dropped'] += 1
                
        except Exception as e:
            self.logger.error(f"Error processing proactive event: {e}", extra={
                "event_data": event_data,
                "component": "event_processing"
            })
            self.stats['events_dropped'] += 1
    
    def _validate_event_data(self, event_data: Dict[str, Any]) -> bool:
        """
        Validate proactive event data.
        
        Args:
            event_data: Event data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['type', 'text']
        
        # Check required fields
        for field in required_fields:
            if field not in event_data:
                return False
        
        # Validate event type
        valid_types = ['reminder', 'suggestion', 'context', 'alert', 'notification']
        if event_data['type'] not in valid_types:
            return False
        
        # Validate text field
        if not isinstance(event_data['text'], str) or len(event_data['text'].strip()) == 0:
            return False
        
        return True
    
    def _process_event_queue(self):
        """Process events from the queue and broadcast them."""
        try:
            while not self.event_queue.empty():
                try:
                    event = self.event_queue.get_nowait()
                    self._broadcast_event(event)
                    self.event_queue.task_done()
                except Empty:
                    break
        except Exception as e:
            self.logger.error(f"Error processing event queue: {e}")
    
    def _broadcast_event(self, event: Dict[str, Any]):
        """
        Broadcast a proactive event to all subscribers.
        
        Args:
            event: Event data to broadcast
        """
        try:
            # Create broadcast message
            topic = f"proactive.{event['type']}"
            message = json.dumps(event)
            
            # Send to PUB socket
            self.publisher.send_multipart([
                topic.encode('utf-8'),
                message.encode('utf-8')
            ])
            
            self.stats['events_broadcasted'] += 1
            
            self.logger.info("Proactive event broadcasted", extra={
                "event_type": event['type'],
                "event_id": event.get('event_id'),
                "topic": topic,
                "component": "event_broadcasting"
            })
            
        except Exception as e:
            self.logger.error(f"Error broadcasting event: {e}", extra={
                "event": event,
                "component": "event_broadcasting"
            })
    
    def send_proactive_event(self, event_type: str, text: str, user: str = None, 
                           emotion: str = "neutral", extra: Dict[str, Any] = None) -> bool:
        """
        Send a proactive event (for local/internal use).
        
        Args:
            event_type: Type of event ('reminder', 'suggestion', 'context', etc.)
            text: Event message text
            user: Target user (optional)
            emotion: Emotional tone (optional)
            extra: Additional event data (optional)
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        try:
            event_data = {
                'type': event_type,
                'text': text,
                'user': user,
                'emotion': emotion,
                'proactive': True,
                'source_agent': self.name
            }
            
            if extra:
                event_data.update(extra)
            
            self._process_proactive_event(event_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending proactive event: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics for the proactive interface."""
        uptime = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'events_per_minute': (self.stats['events_received'] / uptime) * 60 if uptime > 0 else 0,
            'queue_size': self.event_queue.qsize(),
            'queue_max_size': MAX_EVENT_QUEUE_SIZE
        }
    
    def run(self):
        """
        Main execution method using BaseAgent's run() framework.
        """
        try:
            self.logger.info(f"Starting {self.name}")
            
            # Start statistics reporting
            self._start_statistics_reporting()
            
            # Call parent run() method for standard startup
            super().run()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested via KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in {self.name}: {e}")
            raise
        finally:
            self.cleanup()
    
    def _start_statistics_reporting(self):
        """Start periodic statistics reporting."""
        def stats_reporter():
            while self.running:
                try:
                    stats = self.get_statistics()
                    self.logger.info("Proactive interface statistics", extra={
                        "statistics": stats,
                        "component": "statistics_reporting"
                    })
                    time.sleep(300)  # Report every 5 minutes
                except Exception as e:
                    self.logger.error(f"Error in statistics reporting: {e}")
                    time.sleep(30)
        
        self.stats_reporter_thread = threading.Thread(target=stats_reporter, daemon=True)
        self.stats_reporter_thread.start()
    
    def cleanup(self):
        """
        Cleanup method with custom cleanup logic for proactive interface.
        """
        try:
            self.logger.info(f"Cleaning up {self.name}")
            
            # Process remaining events in queue
            try:
                while not self.event_queue.empty():
                    self._process_event_queue()
                    time.sleep(0.1)
            except:
                pass
            
            # Custom cleanup logic
            if hasattr(self, 'pull_socket'):
                self.pull_socket.close()
            
            if hasattr(self, 'publisher'):
                self.publisher.close()
            
            # Call parent cleanup
            super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Utility function for other agents to send proactive events
def send_proactive_event(event_type: str, text: str, user: str = None, 
                        emotion: str = "neutral", extra: Dict[str, Any] = None,
                        host: str = "localhost", port: int = DEFAULT_PROACTIVE_PORT) -> bool:
    """
    Utility function for other agents to send proactive events.
    
    Args:
        event_type: Type of event ('reminder', 'suggestion', 'context', etc.)
        text: Event message text
        user: Target user (optional)
        emotion: Emotional tone (optional)  
        extra: Additional event data (optional)
        host: ProactiveAgentInterface host (default: localhost)
        port: ProactiveAgentInterface port (default: 5558)
        
    Returns:
        True if event was sent successfully, False otherwise
    """
    context = None
    socket = None
    
    try:
        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.connect(f"tcp://{host}:{port}")
        
        event_data = {
            'type': event_type,
            'text': text,
            'user': user,
            'emotion': emotion,
            'proactive': True,
            'source_agent': 'external_utility'
        }
        
        if extra:
            event_data.update(extra)
        
        socket.send_json(event_data)
        
        print(f"[ProactiveAgentInterface] Sent event: {event_data}")
        return True
        
    except Exception as e:
        print(f"[ProactiveAgentInterface] Error sending event: {e}")
        return False
        
    finally:
        if socket:
            socket.close()
        if context:
            context.term()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run ProactiveAgentInterface")
    parser.add_argument('--port', type=int, help='Main service port')
    parser.add_argument('--health-port', type=int, help='Health check port')
    parser.add_argument('--broadcast-port', type=int, help='Broadcast port for events')
    parser.add_argument('--config', help='Configuration file path')
    
    # Add demo mode for testing
    parser.add_argument('--demo', action='store_true', help='Run demo mode with sample events')
    
    args = parser.parse_args()
    
    # Create and run agent
    agent = ProactiveAgentInterface(
        port=args.port,
        health_check_port=args.health_port
    )
    
    if args.demo:
        # Send some demo events
        import threading
        import time
        
        def demo_events():
            time.sleep(2)  # Wait for agent to start
            agent.send_proactive_event("suggestion", "Time to take a break!", user="DemoUser", emotion="encouraging")
            time.sleep(1)
            agent.send_proactive_event("reminder", "Meeting in 10 minutes", user="DemoUser", emotion="informative")
            time.sleep(1)
            agent.send_proactive_event("context", "Weather looks nice today", emotion="cheerful")
        
        demo_thread = threading.Thread(target=demo_events, daemon=True)
        demo_thread.start()
    
    agent.run()
