import zmq
import json
import logging
import threading
import time
from datetime import datetime, timedelta

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_decay_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemoryDecayManager:
    def __init__(self):
        self.context = zmq.Context()
        
        # Connect to UnifiedMemoryReasoningAgent
        self.umra_socket = self.context.socket(zmq.REQ)
        self.umra_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.umra_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.umra_socket.connect("tcp://localhost:5596")
        
        # Socket for other agents to query memory status
        self.query_socket = self.context.socket(zmq.REP)
        self.query_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.query_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.query_socket.bind("tcp://*:5624")
        
        # Decay parameters
        self.decay_rates = {
            'short_term': 0.1,  # 10% decay per cycle
            'medium_term': 0.05,  # 5% decay per cycle
            'long_term': 0.01  # 1% decay per cycle
        }
        
        # Consolidation thresholds
        self.consolidation_thresholds = {
            'short_to_medium': 0.7,  # Move to medium-term when score < 0.7
            'medium_to_long': 0.5  # Move to long-term when score < 0.5
        }
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_memories)
        self.monitor_thread.daemon = True
        self.running = True
        
        self.monitor_thread.start()
        logger.info("MemoryDecayManager initialized and listening on port 5624")
    
    def _run_decay_cycle(self):
        """Run a single decay cycle on all memories"""
        try:
            # Request current memories from UMRA
            self.umra_socket.send_json({
                'action': 'get_all_memories'
            })
            response = self.umra_socket.recv_json()
            
            if response['status'] != 'success':
                logger.error(f"Failed to get memories: {response.get('error')}")
                return
            
            memories = response['memories']
            updated_memories = []
            
            for memory in memories:
                memory_type = memory.get('type', 'short_term')
                current_score = memory.get('freshness_score', 1.0)
                timestamp = datetime.fromisoformat(memory.get('timestamp', datetime.now().isoformat()))
                age = datetime.now() - timestamp
                
                # Calculate decay based on memory type and age
                decay_rate = self.decay_rates.get(memory_type, 0.1)
                decay_factor = 1.0 - (decay_rate * (age.days + 1))
                new_score = max(0.0, min(1.0, current_score * decay_factor))
                
                # Check for consolidation
                if memory_type == 'short_term' and new_score < self.consolidation_thresholds['short_to_medium']:
                    # Consolidate to medium-term
                    memory['type'] = 'medium_term'
                    memory['freshness_score'] = 0.8  # Reset score for medium-term
                    memory['consolidated_from'] = 'short_term'
                    memory['consolidation_time'] = datetime.now().isoformat()
                elif memory_type == 'medium_term' and new_score < self.consolidation_thresholds['medium_to_long']:
                    # Consolidate to long-term
                    memory['type'] = 'long_term'
                    memory['freshness_score'] = 0.6  # Reset score for long-term
                    memory['consolidated_from'] = 'medium_term'
                    memory['consolidation_time'] = datetime.now().isoformat()
                else:
                    # Update score
                    memory['freshness_score'] = new_score
                
                updated_memories.append(memory)
            
            # Send updated memories back to UMRA
            self.umra_socket.send_json({
                'action': 'update_memories',
                'memories': updated_memories
            })
            
            response = self.umra_socket.recv_json()
            if response['status'] != 'success':
                logger.error(f"Failed to update memories: {response.get('error')}")
            
            logger.info(f"Completed decay cycle for {len(updated_memories)} memories")
            
        except Exception as e:
            logger.error(f"Error in decay cycle: {str(e)}")
    
    def _monitor_memories(self):
        """Monitor and decay memories periodically"""
        while self.running:
            try:
                self._run_decay_cycle()
                time.sleep(3600)  # Run decay cycle every hour
            except Exception as e:
                logger.error(f"Error in memory monitoring: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def get_memory_stats(self):
        """Get statistics about memory decay"""
        try:
            self.umra_socket.send_json({
                'action': 'get_memory_stats'
            })
            response = self.umra_socket.recv_json()
            
            if response['status'] == 'success':
                return response['stats']
            else:
                return {
                    'status': 'error',
                    'message': response.get('error', 'Unknown error')
                }
        except Exception as e:
            logger.error(f"Error getting memory stats: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def run(self):
        """Main loop to handle incoming requests"""
        logger.info("Starting MemoryDecayManager main loop")
        
        while self.running:
            try:
                message = self.query_socket.recv_json()
                action = message.get('action')
                
                if action == 'get_memory_stats':
                    response = self.get_memory_stats()
                elif action == 'force_decay_cycle':
                    self._run_decay_cycle()
                    response = {'status': 'success', 'message': 'Decay cycle completed'}
                else:
                    response = {
                        'status': 'error',
                        'message': 'Unknown action'
                    }
                
                self.query_socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.query_socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })
    
    def shutdown(self):
        """Gracefully shutdown the manager"""
        self.running = False
        self.umra_socket.close()
        self.query_socket.close()
        self.context.term()
        logger.info("MemoryDecayManager shutdown complete")

if __name__ == "__main__":
    manager = MemoryDecayManager()
    try:
        manager.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        manager.shutdown() 