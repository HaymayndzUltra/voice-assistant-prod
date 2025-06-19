#!/usr/bin/env python3
"""
Redundant ZMQ Bridge
-------------------
Implements a redundant active-passive bridge for cross-machine communication
between Main PC and PC2. Includes automatic failover when the active bridge fails.
"""

import zmq
import json
import time
import sys
import threading
import logging
import argparse
import traceback
import socket
import os
import signal
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("RedundantBridge")

# Default configuration
DEFAULT_PRIMARY_PORT = 5600
DEFAULT_SECONDARY_PORT = 5601
DEFAULT_HEARTBEAT_PORT = 5610
DEFAULT_HEARTBEAT_INTERVAL = 1.0  # seconds
DEFAULT_HEARTBEAT_TIMEOUT = 3.0  # seconds
DEFAULT_MAIN_PC_ADDR = "tcp://192.168.1.27:5601"
DEFAULT_PC2_ADDR = "tcp://192.168.1.2:5602"
DEFAULT_RECONNECT_DELAY = 5.0  # seconds
DEFAULT_MAX_RECONNECT_ATTEMPTS = 5

class BridgeBase:
    """Base class for both active and passive bridges"""
    
    def __init__(self, listen_port, main_pc_addr, pc2_addr, heartbeat_port, 
                 heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL):
        """Initialize the bridge base
        
        Args:
            listen_port: Port to listen on
            main_pc_addr: Address for the Main PC endpoint
            pc2_addr: Address for the PC2 endpoint
            heartbeat_port: Port for heartbeat communication
            heartbeat_interval: Interval between heartbeat messages
        """
        self.listen_port = listen_port
        self.main_pc_addr = main_pc_addr
        self.pc2_addr = pc2_addr
        self.heartbeat_port = heartbeat_port
        self.heartbeat_interval = heartbeat_interval
        
        self.context = zmq.Context.instance()
        self.running = True
        self.start_time = time.time()
        
        # Connection status
        self.main_pc_status = "unknown"
        self.pc2_status = "unknown"
        
        # Message stats
        self.messages_received = 0
        self.messages_sent = 0
        self.errors = 0
        
        # Health check thread
        self.health_thread = None
        
        logger.info(f"Bridge initialized: Port {listen_port}, Heartbeat port {heartbeat_port}")
        logger.info(f"Main PC endpoint: {main_pc_addr}")
        logger.info(f"PC2 endpoint: {pc2_addr}")
    
    def setup_main_connections(self):
        """Setup main connections to MainPC and PC2"""
        # Setup Main PC socket (REQ) - this connects to Main PC services
        self.main_pc_socket = self.context.socket(zmq.REQ)
        self.main_pc_socket.setsockopt(zmq.LINGER, 0)
        self.main_pc_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        self.main_pc_socket.connect(self.main_pc_addr)
        
        # Setup PC2 socket (REQ) - this connects to PC2 services
        self.pc2_socket = self.context.socket(zmq.REQ)
        self.pc2_socket.setsockopt(zmq.LINGER, 0)
        self.pc2_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        self.pc2_socket.connect(self.pc2_addr)
        
        # Setup frontend socket (ROUTER) - this is where requests come in
        self.frontend = self.context.socket(zmq.ROUTER)
        
        try:
            self.frontend.bind(f"tcp://*:{self.listen_port}")
            logger.info(f"Listening for requests on port {self.listen_port}")
        except zmq.error.ZMQError as e:
            if e.errno == zmq.EADDRINUSE:
                logger.error(f"Port {self.listen_port} is already in use. Cannot bind.")
                raise
            else:
                logger.error(f"Error binding to port {self.listen_port}: {e}")
                raise
    
    def check_connection_health(self):
        """Check health of connections to both endpoints"""
        while self.running:
            try:
                # Check Main PC connection
                self.main_pc_socket.send(b'{"action":"ping"}', zmq.NOBLOCK)
                try:
                    self.main_pc_socket.recv()
                    if self.main_pc_status != "connected":
                        logger.info(f"Main PC connection established")
                    self.main_pc_status = "connected"
                except zmq.Again:
                    if self.main_pc_status != "disconnected":
                        logger.warning(f"Main PC connection timeout")
                    self.main_pc_status = "disconnected"
            except Exception as e:
                logger.error(f"Error checking Main PC connection: {e}")
                self.main_pc_status = "error"
                
            try:
                # Check PC2 connection
                self.pc2_socket.send(b'{"action":"ping"}', zmq.NOBLOCK)
                try:
                    self.pc2_socket.recv()
                    if self.pc2_status != "connected":
                        logger.info(f"PC2 connection established")
                    self.pc2_status = "connected"
                except zmq.Again:
                    if self.pc2_status != "disconnected":
                        logger.warning(f"PC2 connection timeout")
                    self.pc2_status = "disconnected"
            except Exception as e:
                logger.error(f"Error checking PC2 connection: {e}")
                self.pc2_status = "error"
                
            time.sleep(15)  # Check every 15 seconds
    
    def route_message(self, identity, message):
        """Route message to appropriate endpoint based on content"""
        try:
            # Try to parse message as JSON
            msg_data = json.loads(message.decode('utf-8'))
            
            # Determine target based on message content
            target = msg_data.get("target", "")
            
            if target.lower() == "main_pc":
                # Forward to Main PC
                logger.info(f"Routing to Main PC: {message[:100]}")
                self.main_pc_socket.send(message)
                try:
                    response = self.main_pc_socket.recv()
                    self.frontend.send_multipart([identity, response])
                    self.messages_sent += 1
                    logger.info(f"Response from Main PC: {response[:100]}")
                except zmq.Again:
                    self.frontend.send_multipart([identity, b'{"status":"error","message":"Timeout connecting to Main PC"}'])
                    self.errors += 1
            elif target.lower() == "pc2":
                # Forward to PC2
                logger.info(f"Routing to PC2: {message[:100]}")
                self.pc2_socket.send(message)
                try:
                    response = self.pc2_socket.recv()
                    self.frontend.send_multipart([identity, response])
                    self.messages_sent += 1
                    logger.info(f"Response from PC2: {response[:100]}")
                except zmq.Again:
                    self.frontend.send_multipart([identity, b'{"status":"error","message":"Timeout connecting to PC2"}'])
                    self.errors += 1
            else:
                # Cannot determine target, return error
                logger.warning(f"Unknown target in message: {target}")
                self.frontend.send_multipart([identity, b'{"status":"error","message":"Unknown target, specify target as main_pc or pc2"}'])
                self.errors += 1
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {message[:100]}")
            self.frontend.send_multipart([identity, b'{"status":"error","message":"Message must be valid JSON with target field"}'])
            self.errors += 1
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            logger.error(traceback.format_exc())
            self.frontend.send_multipart([identity, f'{{"status":"error","message":"Internal bridge error: {str(e)}"}}'.encode('utf-8')])
            self.errors += 1
    
    def get_status(self):
        """Get bridge status information"""
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "main_pc": self.main_pc_status,
            "pc2": self.pc2_status,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "errors": self.errors,
            "listen_port": self.listen_port,
            "heartbeat_port": self.heartbeat_port
        }
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        if hasattr(self, 'frontend'):
            self.frontend.close()
        if hasattr(self, 'main_pc_socket'):
            self.main_pc_socket.close()
        if hasattr(self, 'pc2_socket'):
            self.pc2_socket.close()
        # Don't terminate context as it might be shared

class ActiveBridge(BridgeBase):
    """Active (primary) bridge implementation"""
    
    def __init__(self, listen_port=DEFAULT_PRIMARY_PORT, main_pc_addr=DEFAULT_MAIN_PC_ADDR, 
                 pc2_addr=DEFAULT_PC2_ADDR, heartbeat_port=DEFAULT_HEARTBEAT_PORT,
                 heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL):
        """Initialize the active bridge
        
        Args:
            listen_port: Port to listen on (default: 5600)
            main_pc_addr: Address for the Main PC endpoint
            pc2_addr: Address for the PC2 endpoint
            heartbeat_port: Port for heartbeat communication (default: 5610)
            heartbeat_interval: Interval between heartbeat messages
        """
        super().__init__(listen_port, main_pc_addr, pc2_addr, heartbeat_port, heartbeat_interval)
        self.mode = "active"
        
        # Setup heartbeat socket
        self.heartbeat_socket = self.context.socket(zmq.PUB)
        try:
            self.heartbeat_socket.bind(f"tcp://*:{self.heartbeat_port}")
            logger.info(f"Heartbeat publisher bound to port {self.heartbeat_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding heartbeat socket: {e}")
            raise
        
        # Setup connections
        self.setup_main_connections()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeats, daemon=True)
        self.heartbeat_thread.start()
        logger.info("Active bridge initialized")
    
    def _send_heartbeats(self):
        """Send regular heartbeat messages"""
        logger.info(f"Starting heartbeat sender, interval: {self.heartbeat_interval}s")
        while self.running:
            try:
                # Create heartbeat message
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "instance": "active",
                    "port": self.listen_port,
                    "uptime": time.time() - self.start_time,
                    "load": self.messages_received / (time.time() - self.start_time) if (time.time() - self.start_time) > 0 else 0
                }
                
                # Send heartbeat
                self.heartbeat_socket.send_json(heartbeat)
                
                # Sleep until next heartbeat
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                time.sleep(self.heartbeat_interval)
    
    def start(self):
        """Start the active bridge"""
        # Start health check thread
        self.health_thread = threading.Thread(target=self.check_connection_health, daemon=True)
        self.health_thread.start()
        
        logger.info(f"Active bridge starting on port {self.listen_port}")
        try:
            while self.running:
                try:
                    # Receive message from frontend (client)
                    identity, message = self.frontend.recv_multipart(flags=zmq.NOBLOCK)
                    self.messages_received += 1
                    logger.info(f"Received message from {identity}: {message[:100]}")
                    
                    # Handle status request
                    if message == b'{"action":"status"}':
                        status_response = json.dumps(self.get_status()).encode('utf-8')
                        self.frontend.send_multipart([identity, status_response])
                        continue
                    
                    # Route message
                    self.route_message(identity, message)
                    
                except zmq.Again:
                    # No message available, short sleep
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    logger.error(traceback.format_exc())
                    self.errors += 1
        except KeyboardInterrupt:
            logger.info("Shutting down active bridge...")
        finally:
            self.running = False
            # Wait for threads to finish
            if self.health_thread and self.health_thread.is_alive():
                self.health_thread.join(timeout=1.0)
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=1.0)
            
            # Clean up
            self.cleanup()
            if hasattr(self, 'heartbeat_socket'):
                self.heartbeat_socket.close()
            
            logger.info("Active bridge shut down successfully")


class PassiveBridge(BridgeBase):
    """Passive (secondary) bridge implementation with failover capability"""
    
    def __init__(self, listen_port=DEFAULT_SECONDARY_PORT, main_pc_addr=DEFAULT_MAIN_PC_ADDR, 
                 pc2_addr=DEFAULT_PC2_ADDR, primary_port=DEFAULT_PRIMARY_PORT,
                 primary_heartbeat_port=DEFAULT_HEARTBEAT_PORT, heartbeat_port=DEFAULT_HEARTBEAT_PORT+1,
                 heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL, 
                 heartbeat_timeout=DEFAULT_HEARTBEAT_TIMEOUT):
        """Initialize the passive bridge
        
        Args:
            listen_port: Port to listen on (default: 5601)
            main_pc_addr: Address for the Main PC endpoint
            pc2_addr: Address for the PC2 endpoint
            primary_port: Port of the active bridge (default: 5600)
            primary_heartbeat_port: Heartbeat port of the active bridge (default: 5610)
            heartbeat_port: Port for own heartbeats if activated (default: 5611)
            heartbeat_interval: Interval between heartbeat messages
            heartbeat_timeout: Timeout for missing heartbeats before failover
        """
        super().__init__(listen_port, main_pc_addr, pc2_addr, heartbeat_port, heartbeat_interval)
        self.mode = "passive"
        self.primary_port = primary_port
        self.primary_heartbeat_port = primary_heartbeat_port
        self.heartbeat_timeout = heartbeat_timeout
        self.last_heartbeat_time = 0
        self.failover_mode = False
        self.heartbeat_thread = None
        
        # Setup heartbeat monitor socket
        self.heartbeat_monitor = self.context.socket(zmq.SUB)
        self.heartbeat_monitor.setsockopt_string(zmq.SUBSCRIBE, "")
        self.heartbeat_monitor.connect(f"tcp://localhost:{self.primary_heartbeat_port}")
        logger.info(f"Monitoring heartbeats from active bridge on port {self.primary_heartbeat_port}")
        
        # Setup own heartbeat socket (used after failover)
        self.heartbeat_socket = self.context.socket(zmq.PUB)
        
        # Setup connections
        self.setup_main_connections()
        
        # Start heartbeat monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_heartbeats, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Passive bridge initialized")
    
    def _monitor_heartbeats(self):
        """Monitor heartbeats from active bridge"""
        logger.info(f"Starting heartbeat monitor, timeout: {self.heartbeat_timeout}s")
        
        # Set initial last heartbeat time
        self.last_heartbeat_time = time.time()
        
        while self.running:
            try:
                # Try to receive a heartbeat
                try:
                    heartbeat = self.heartbeat_monitor.recv_json(flags=zmq.NOBLOCK)
                    self.last_heartbeat_time = time.time()
                    logger.debug(f"Received heartbeat from active bridge: {heartbeat}")
                except zmq.Again:
                    # No heartbeat received, check timeout
                    if time.time() - self.last_heartbeat_time > self.heartbeat_timeout:
                        # Heartbeat timeout
                        if not self.failover_mode:
                            logger.warning(f"No heartbeat received for {self.heartbeat_timeout}s. Initiating failover...")
                            self._initiate_failover()
                    
                # Short sleep
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error monitoring heartbeats: {e}")
                time.sleep(1.0)
    
    def _initiate_failover(self):
        """Initiate failover to become the active bridge"""
        logger.info("Initiating failover procedure")
        
        try:
            # Try to bind to the primary port
            new_frontend = self.context.socket(zmq.ROUTER)
            try:
                new_frontend.bind(f"tcp://*:{self.primary_port}")
                logger.info(f"Successfully bound to primary port {self.primary_port}")
                
                # Close old frontend and replace with new one
                old_port = self.listen_port
                self.frontend.close()
                self.frontend = new_frontend
                self.listen_port = self.primary_port
                
                # Update mode
                self.mode = "active (failed over)"
                self.failover_mode = True
                
                # Bind own heartbeat socket
                try:
                    self.heartbeat_socket.bind(f"tcp://*:{self.heartbeat_port}")
                    logger.info(f"Heartbeat publisher bound to port {self.heartbeat_port}")
                    
                    # Start heartbeat thread
                    self.heartbeat_thread = threading.Thread(target=self._send_heartbeats, daemon=True)
                    self.heartbeat_thread.start()
                except zmq.error.ZMQError as e:
                    logger.error(f"Error binding own heartbeat socket: {e}")
                
                # Broadcast failover notification
                self._broadcast_failover_notification(old_port)
                
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EADDRINUSE:
                    logger.error(f"Primary port {self.primary_port} is still in use, continuing as passive")
                    new_frontend.close()
                else:
                    logger.error(f"Error binding to primary port: {e}")
                    new_frontend.close()
        except Exception as e:
            logger.error(f"Error during failover: {e}")
    
    def _send_heartbeats(self):
        """Send regular heartbeat messages after failover"""
        logger.info(f"Starting heartbeat sender, interval: {self.heartbeat_interval}s")
        while self.running:
            try:
                # Create heartbeat message
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "instance": "passive_failedover",
                    "port": self.listen_port,
                    "uptime": time.time() - self.start_time,
                    "load": self.messages_received / (time.time() - self.start_time) if (time.time() - self.start_time) > 0 else 0
                }
                
                # Send heartbeat
                self.heartbeat_socket.send_json(heartbeat)
                
                # Sleep until next heartbeat
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _broadcast_failover_notification(self, old_port):
        """Broadcast a failover notification to clients"""
        try:
            # Create notification socket
            notification_socket = self.context.socket(zmq.PUB)
            notification_socket.bind(f"tcp://*:5612")  # Use a specific port for notifications
            
            # Allow time for connections
            time.sleep(0.2)
            
            # Create notification message
            notification = {
                "type": "failover_notification",
                "timestamp": time.time(),
                "new_active_port": self.listen_port,
                "old_active_port": old_port,
                "new_heartbeat_port": self.heartbeat_port
            }
            
            # Send notification
            notification_socket.send_json(notification)
            logger.info(f"Sent failover notification: {notification}")
            
            # Close socket after a delay to ensure delivery
            time.sleep(0.5)
            notification_socket.close()
        except Exception as e:
            logger.error(f"Error broadcasting failover notification: {e}")
    
    def start(self):
        """Start the passive bridge"""
        # Start health check thread
        self.health_thread = threading.Thread(target=self.check_connection_health, daemon=True)
        self.health_thread.start()
        
        logger.info(f"Passive bridge starting on port {self.listen_port}")
        try:
            while self.running:
                try:
                    # Receive message from frontend (client)
                    identity, message = self.frontend.recv_multipart(flags=zmq.NOBLOCK)
                    self.messages_received += 1
                    logger.info(f"Received message from {identity}: {message[:100]}")
                    
                    # Handle status request
                    if message == b'{"action":"status"}':
                        status = self.get_status()
                        status["mode"] = self.mode
                        status["failover_mode"] = self.failover_mode
                        status["last_heartbeat_age"] = time.time() - self.last_heartbeat_time
                        
                        status_response = json.dumps(status).encode('utf-8')
                        self.frontend.send_multipart([identity, status_response])
                        continue
                    
                    # Route message
                    self.route_message(identity, message)
                    
                except zmq.Again:
                    # No message available, short sleep
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    logger.error(traceback.format_exc())
                    self.errors += 1
        except KeyboardInterrupt:
            logger.info("Shutting down passive bridge...")
        finally:
            self.running = False
            # Wait for threads to finish
            if self.health_thread and self.health_thread.is_alive():
                self.health_thread.join(timeout=1.0)
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=1.0)
            
            # Clean up
            self.cleanup()
            if hasattr(self, 'heartbeat_monitor'):
                self.heartbeat_monitor.close()
            if hasattr(self, 'heartbeat_socket'):
                self.heartbeat_socket.close()
            
            logger.info("Passive bridge shut down successfully")


def is_port_in_use(port):
    """Check if the port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Redundant ZMQ Bridge')
    
    # Mode arguments
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--active', action='store_true', help='Run as active (primary) bridge')
    mode_group.add_argument('--passive', action='store_true', help='Run as passive (secondary) bridge')
    
    # Common arguments
    parser.add_argument('--main-pc', type=str, default=DEFAULT_MAIN_PC_ADDR, 
                        help='Main PC endpoint address')
    parser.add_argument('--pc2', type=str, default=DEFAULT_PC2_ADDR, 
                        help='PC2 endpoint address')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # Active bridge arguments
    parser.add_argument('--active-port', type=int, default=DEFAULT_PRIMARY_PORT, 
                        help='Port for active bridge to listen on')
    parser.add_argument('--active-heartbeat-port', type=int, default=DEFAULT_HEARTBEAT_PORT, 
                        help='Heartbeat port for active bridge')
    
    # Passive bridge arguments
    parser.add_argument('--passive-port', type=int, default=DEFAULT_SECONDARY_PORT, 
                        help='Port for passive bridge to listen on')
    parser.add_argument('--passive-heartbeat-port', type=int, default=DEFAULT_HEARTBEAT_PORT+1, 
                        help='Heartbeat port for passive bridge (used after failover)')
    parser.add_argument('--heartbeat-timeout', type=float, default=DEFAULT_HEARTBEAT_TIMEOUT, 
                        help='Timeout for missing heartbeats before failover')
    
    # Heartbeat arguments
    parser.add_argument('--heartbeat-interval', type=float, default=DEFAULT_HEARTBEAT_INTERVAL, 
                        help='Interval between heartbeat messages')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create bridge instance based on mode
    if args.active:
        # Check if active bridge port is available
        if is_port_in_use(args.active_port):
            logger.error(f"Port {args.active_port} is already in use. Please choose a different port.")
            sys.exit(1)
        
        # Check if heartbeat port is available
        if is_port_in_use(args.active_heartbeat_port):
            logger.error(f"Heartbeat port {args.active_heartbeat_port} is already in use. Please choose a different port.")
            sys.exit(1)
        
        logger.info(f"Starting as ACTIVE bridge on port {args.active_port}")
        bridge = ActiveBridge(
            listen_port=args.active_port,
            main_pc_addr=args.main_pc,
            pc2_addr=args.pc2,
            heartbeat_port=args.active_heartbeat_port,
            heartbeat_interval=args.heartbeat_interval
        )
    else:  # passive
        # Check if passive bridge port is available
        if is_port_in_use(args.passive_port):
            logger.error(f"Port {args.passive_port} is already in use. Please choose a different port.")
            sys.exit(1)
        
        logger.info(f"Starting as PASSIVE bridge on port {args.passive_port}")
        bridge = PassiveBridge(
            listen_port=args.passive_port,
            main_pc_addr=args.main_pc,
            pc2_addr=args.pc2,
            primary_port=args.active_port,
            primary_heartbeat_port=args.active_heartbeat_port,
            heartbeat_port=args.passive_heartbeat_port,
            heartbeat_interval=args.heartbeat_interval,
            heartbeat_timeout=args.heartbeat_timeout
        )
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        bridge.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start bridge
    bridge.start_time = time.time()
    bridge.start()

if __name__ == "__main__":
    main()
