from common.core.base_agent import BaseAgent
"""
AutoGen-inspired Framework for AI Agent Coordination
- Provides a framework for multiple agents to collaborate
- Handles message routing between agents
- Manages agent state and memory
- Implements task planning and execution
"""
import zmq
import json
import time
import logging
import threading
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "autogen_framework.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoGenFramework")

# ZMQ Configuration
ROUTER_PORT = 5650  # Port for agents to connect and send messages
DEALER_PORT = 5651  # Port for broadcasting messages to agents

class Message(BaseAgent):
    """Message class for(BaseAgent) agent communication"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutogenFramework")
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.message_type = message_type
        self.timestamp = datetime.now().isoformat()
        self.message_id = f"{sender}-{receiver}-{int(time.time() * 1000)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        msg = cls(
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            message_type=data["message_type"]
        )
        msg.timestamp = data["timestamp"]
        msg.message_id = data["message_id"]
        return msg

class Task(BaseAgent):
    """Task class for(BaseAgent) tracking multi-step operations"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutogenFramework")
        self.task_id = task_id
        self.description = description
        self.steps = steps
        self.current_step = 0
        self.status = "pending"  # pending, in_progress, completed, failed
        self.result = None
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "steps": self.steps,
            "current_step": self.current_step,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        task = cls(
            task_id=data["task_id"],
            description=data["description"],
            steps=data["steps"]
        )
        task.current_step = data["current_step"]
        task.status = data["status"]
        task.result = data["result"]
        task.created_at = data["created_at"]
        task.updated_at = data["updated_at"]
        return task
    
    def update_status(self, status: str, result: Optional[Any] = None):
        """Update task status"""
        self.status = status
        if result is not None:
            self.result = result
        self.updated_at = datetime.now().isoformat()
    
    def next_step(self) -> Optional[Dict[str, Any]]:
        """Get next step in task"""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.current_step += 1
            self.updated_at = datetime.now().isoformat()
            return step
        return None

class AgentRegistry(BaseAgent):
    """Registry for available agents"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutogenFramework")
        self.agents = {}
        self.capabilities = {}
        self.identity_to_agent = {}  # Maps ZMQ identities to agent IDs
    
    def register_agent(self, agent_id: str, identity: bytes, capabilities: List[str], endpoint: str = None):
        """Register an agent with its capabilities and ZMQ identity
        
        Args:
            agent_id: Unique identifier for the agent
            identity: ZMQ identity (socket identity bytes)
            capabilities: List of capabilities the agent has
            endpoint: Optional endpoint for direct communication
        """
        self.agents[agent_id] = {
            "identity": identity,
            "endpoint": endpoint,
            "capabilities": capabilities,
            "status": "online",
            "last_seen": datetime.now().isoformat()
        }
        
        # Map identity to agent_id
        self.identity_to_agent[identity] = agent_id
        
        # Update capabilities index
        for capability in capabilities:
            if capability not in self.capabilities:
                self.capabilities[capability] = []
            if agent_id not in self.capabilities[capability]:
                self.capabilities[capability].append(agent_id)
                
        logger.info(f"Agent registered: {agent_id} with capabilities: {capabilities}")
    
    def unregister_agent(self, agent_id: str = None, identity: bytes = None):
        """Unregister an agent by ID or identity"""
        # Find agent_id if only identity is provided
        if agent_id is None and identity is not None:
            agent_id = self.identity_to_agent.get(identity)
            if agent_id is None:
                logger.warning(f"No agent found with identity: {identity}")
                return
        
        if agent_id in self.agents:
            # Get identity for cleanup
            identity = self.agents[agent_id]["identity"]
            
            # Remove from capabilities index
            for capability, agents in self.capabilities.items():
                if agent_id in agents:
                    self.capabilities[capability].remove(agent_id)
            
            # Remove from identity map
            if identity in self.identity_to_agent:
                del self.identity_to_agent[identity]
            
            # Remove agent
            del self.agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
    
    def find_agent_for_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        return self.capabilities.get(capability, [])
    
    def get_agent_identity(self, agent_id: str) -> Optional[bytes]:
        """Get agent's ZMQ identity"""
        if agent_id in self.agents:
            return self.agents[agent_id]["identity"]
        return None
    
    def get_agent_id_from_identity(self, identity: bytes) -> Optional[str]:
        """Get agent ID from ZMQ identity"""
        return self.identity_to_agent.get(identity)
    
    def update_agent_status(self, agent_id: str, status: str):
        """Update agent status"""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = status
            self.agents[agent_id]["last_seen"] = datetime.now().isoformat()
    
    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered agents"""
        return self.agents

class MessageBus(BaseAgent):
    """ZMQ-based message bus for agent communication"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutogenFramework")
        self.router_port = router_port
        self.dealer_port = dealer_port
        self.context = zmq.Context()
        
        # ROUTER socket for receiving messages from agents
        self.router = self.context.socket(zmq.ROUTER)
        self.router.bind(f"tcp://*:{router_port}")
        
        # DEALER socket for sending messages to agents
        self.dealer = self.context.socket(zmq.DEALER)
        self.dealer.bind(f"tcp://*:{dealer_port}")
        
        # Message history
        self.message_history = []
        self.max_history = 1000
        
        # Running flag
        self.running = True
        
        # Agent registry
        self.agent_registry = AgentRegistry()
        
        # Start message processing thread
        self.router_thread = threading.Thread(target=self._process_router_messages)
        self.router_thread.daemon = True
        
        logger.info(f"MessageBus initialized with ROUTER on port {router_port} and DEALER on port {dealer_port}")
    
    def start(self):
        """Start the message bus"""
        self.router_thread.start()
        logger.info("MessageBus started")
    
    def _process_router_messages(self):
        """Process messages from the ROUTER socket"""
        logger.info("Starting ROUTER message processing thread")
        
        while self.running:
            try:
                # Use poll to avoid blocking indefinitely
                poller = zmq.Poller()
                poller.register(self.router, zmq.POLLIN)
                
                socks = dict(poller.poll(1000))  # 1 second timeout
                if self.router in socks and socks[self.router] == zmq.POLLIN:
                    # Receive multipart message
                    frames = self.router.recv_multipart()
                    
                    # Process message
                    if len(frames) >= 3:
                        identity = frames[0]
                        empty = frames[1]  # Empty delimiter frame
                        payload = frames[2]
                        
                        try:
                            message = json.loads(payload.decode('utf-8'))
                            self._handle_message(identity, message)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON message: {payload}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            traceback.print_exc()
            except Exception as e:
                logger.error(f"Error in ROUTER message processing: {e}")
                traceback.print_exc()
                time.sleep(1)  # Avoid tight loop in case of error
    
    def _handle_message(self, identity: bytes, message: Dict[str, Any]):
        """Handle incoming message from an agent"""
        action = message.get("action")
        
        if action == "register":
            # Register agent
            agent_id = message.get("agent_id")
            capabilities = message.get("capabilities", [])
            endpoint = message.get("endpoint")
            
            if agent_id:
                self.agent_registry.register_agent(agent_id, identity, capabilities, endpoint)
                self._send_response(identity, {
                    "status": "success",
                    "message": f"Agent {agent_id} registered successfully",
                    "router_port": self.router_port,
                    "dealer_port": self.dealer_port
                })
            else:
                self._send_response(identity, {
                    "status": "error",
                    "message": "Missing agent_id in registration request"
                })
        
        elif action == "unregister":
            # Unregister agent
            agent_id = message.get("agent_id")
            if agent_id:
                self.agent_registry.unregister_agent(agent_id=agent_id)
            else:
                self.agent_registry.unregister_agent(identity=identity)
                
            self._send_response(identity, {
                "status": "success",
                "message": "Agent unregistered successfully"
            })
        
        elif action == "send_message":
            # Send message to another agent
            msg_data = message.get("message", {})
            sender = self.agent_registry.get_agent_id_from_identity(identity)
            
            if not sender:
                self._send_response(identity, {
                    "status": "error",
                    "message": "Sender not registered"
                })
                return
            
            # Override sender with actual sender ID
            msg_data["sender"] = sender
            
            # Store in history
            self._store_message(msg_data)
            
            # Send to receiver
            success = self._route_message(msg_data)
            
            self._send_response(identity, {
                "status": "success" if success else "error",
                "message": "Message sent successfully" if success else "Failed to send message",
                "message_id": msg_data.get("message_id")
            })
        
        elif action == "broadcast":
            # Broadcast message to all agents or agents with specific capability
            msg_data = message.get("message", {})
            capability = message.get("capability")
            sender = self.agent_registry.get_agent_id_from_identity(identity)
            
            if not sender:
                self._send_response(identity, {
                    "status": "error",
                    "message": "Sender not registered"
                })
                return
            
            # Override sender with actual sender ID
            msg_data["sender"] = sender
            
            # Broadcast message
            count = self._broadcast_message(msg_data, capability)
            
            self._send_response(identity, {
                "status": "success",
                "message": f"Message broadcasted to {count} agents",
                "recipient_count": count
            })
        
        elif action == "get_agents":
            # Get list of registered agents
            capability = message.get("capability")
            
            if capability:
                agent_ids = self.agent_registry.find_agent_for_capability(capability)
                agents = {agent_id: self.agent_registry.agents[agent_id] for agent_id in agent_ids 
                         if agent_id in self.agent_registry.agents}
            else:
                agents = self.agent_registry.get_all_agents()
            
            # Remove binary identity from response
            sanitized_agents = {}
            for agent_id, agent_data in agents.items():
                agent_copy = agent_data.copy()
                if "identity" in agent_copy:
                    del agent_copy["identity"]
                sanitized_agents[agent_id] = agent_copy
            
            self._send_response(identity, {
                "status": "success",
                "agents": sanitized_agents
            })
        
        elif action == "ping":
            # Simple ping to check if message bus is alive
            self._send_response(identity, {
                "status": "success",
                "message": "pong",
                "timestamp": datetime.now().isoformat()
            })
        
        else:
            # Unknown action
            self._send_response(identity, {
                "status": "error",
                "message": f"Unknown action: {action}"
            })
    
    def _send_response(self, identity: bytes, response: Dict[str, Any]):
        """Send response back to the agent"""
        try:
            self.router.send_multipart([
                identity,
                b"",  # Empty delimiter frame
                json.dumps(response).encode('utf-8')
            ])
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    def _route_message(self, message: Dict[str, Any]) -> bool:
        """Route message to the intended recipient"""
        receiver = message.get("receiver")
        if not receiver:
            logger.error("Message has no receiver")
            return False
        
        # Get receiver's identity
        identity = self.agent_registry.get_agent_identity(receiver)
        if not identity:
            logger.error(f"Receiver not found: {receiver}")
            return False
        
        try:
            # Send message through DEALER socket
            self.dealer.send_multipart([
                identity,
                b"",  # Empty delimiter frame
                json.dumps(message).encode('utf-8')
            ])
            return True
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            return False
    
    def _broadcast_message(self, message: Dict[str, Any], capability: str = None) -> int:
        """Broadcast message to all agents or agents with specific capability"""
        if capability:
            # Get agents with specific capability
            agent_ids = self.agent_registry.find_agent_for_capability(capability)
        else:
            # Get all agents
            agent_ids = list(self.agent_registry.agents.keys())
        
        # Skip sender
        sender = message.get("sender")
        if sender in agent_ids:
            agent_ids.remove(sender)
        
        count = 0
        for agent_id in agent_ids:
            # Get agent's identity
            identity = self.agent_registry.get_agent_identity(agent_id)
            if identity:
                try:
                    # Create copy of message with this agent as receiver
                    msg_copy = message.copy()
                    msg_copy["receiver"] = agent_id
                    msg_copy["message_id"] = f"{sender}-{agent_id}-{int(time.time() * 1000)}"
                    
                    # Store in history
                    self._store_message(msg_copy)
                    
                    # Send through DEALER socket
                    self.dealer.send_multipart([
                        identity,
                        b"",  # Empty delimiter frame
                        json.dumps(msg_copy).encode('utf-8')
                    ])
                    count += 1
                except Exception as e:
                    logger.error(f"Error broadcasting to {agent_id}: {e}")
        
        return count
    
    def _store_message(self, message: Dict[str, Any]):
        """Store message in history"""
        self.message_history.append(message)
        
        # Trim history if needed
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
    
    def stop(self):
        """Stop the message bus"""
        self.running = False
        if self.router_thread.is_alive():
            self.router_thread.join(timeout=2.0)
        
        self.router.close()
        self.dealer.close()
        logger.info("MessageBus stopped")

class AutoGenFramework(BaseAgent):
    """Main framework for agent coordination"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutogenFramework")
        # Initialize message bus
        self.message_bus = MessageBus(router_port, dealer_port)
        
        # Running flag
        self.running = True
        
        logger.info("AutoGen Framework initialized")
    
    def start(self):
        """Start the framework"""
        self.message_bus.start()
        logger.info("AutoGen Framework started")
    
    def stop(self):
        """Stop the framework"""
        self.message_bus.stop()
        self.running = False
        logger.info("AutoGen Framework stopped")

def main():
    """Main entry point"""
    try:
        # Create and start framework
        framework = AutoGenFramework()
        framework.start()
        
        # Keep running until interrupted
        while framework.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down...")
                break
        
        # Stop framework
        framework.stop()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
