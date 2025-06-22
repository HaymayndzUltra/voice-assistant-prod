import zmq
import json
from typing import Dict, Any, Callable, List
import logging
from datetime import datetime
import asyncio
import time

class TieredResponder:
    def __init__(self):
        self.context = zmq.Context()
        self._setup_sockets()
        self._setup_tiers()
        self._setup_logging()
        
    def _setup_sockets(self):
        # Socket for receiving user queries
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind("tcp://*:5619")
        
        # Socket for sending responses
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.bind("tcp://*:5620")
        
    def _setup_tiers(self):
        self.tiers = [
            {
                'name': 'instant',
                'max_response_time': 0.1,  # 100ms
                'patterns': [
                    'hello', 'hi', 'kumusta', 'kamusta', 
                    'thanks', 'thank you', 'salamat',
                    'bye', 'goodbye', 'paalam'
                ],
                'handler': self._handle_instant_response
            },
            {
                'name': 'fast',
                'max_response_time': 1.0,  # 1 second
                'patterns': [
                    'what is', 'who is', 'when is',
                    'how to', 'how do i', 'can you',
                    'tell me about'
                ],
                'handler': self._handle_fast_response
            },
            {
                'name': 'deep',
                'max_response_time': 5.0,  # 5 seconds
                'patterns': [
                    'plan', 'analyze', 'write', 'create',
                    'design', 'build', 'explain deeply',
                    'give me a detailed'
                ],
                'handler': self._handle_deep_response
            }
        ]
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/tiered_responder.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TieredResponder')

    def start(self):
        """Start the tiered responder"""
        self.logger.info("Tiered Responder started")
        self._start_response_processor()
        
    def _start_response_processor(self):
        """Start background thread for processing queries"""
        def process_queries():
            while True:
                try:
                    query = self.pull_socket.recv_json()
                    self._handle_query(query)
                except Exception as e:
                    self.logger.error(f"Error processing query: {str(e)}")
                    time.sleep(1)

        thread = threading.Thread(target=process_queries, daemon=True)
        thread.start()

    def _handle_query(self, query: Dict[str, Any]):
        """Handle incoming query and route to appropriate tier"""
        text = query.get('text', '').lower()
        
        # Check instant response patterns first
        for tier in self.tiers:
            if any(pattern in text for pattern in tier['patterns']):
                asyncio.run(tier['handler'](query, tier['name']))
                return
        
        # If no pattern matches, default to deep analysis
        asyncio.run(self._handle_deep_response(query, 'deep'))

    async def _handle_instant_response(self, query: Dict[str, Any], tier_name: str):
        """Handle instant response queries"""
        start_time = time.time()
        
        # Get canned response
        response = self._get_canned_response(query['text'])
        
        # Send response immediately
        await self._send_response(query, response, tier_name)
        
        # Log response time
        response_time = time.time() - start_time
        self.logger.info(f"Instant response time: {response_time:.3f}s")

    async def _handle_fast_response(self, query: Dict[str, Any], tier_name: str):
        """Handle fast response queries"""
        start_time = time.time()
        
        # Use fast local model
        response = await self._get_fast_model_response(query['text'])
        
        # Send response
        await self._send_response(query, response, tier_name)
        
        # Log response time
        response_time = time.time() - start_time
        self.logger.info(f"Fast response time: {response_time:.3f}s")

    async def _handle_deep_response(self, query: Dict[str, Any], tier_name: str):
        """Handle deep analysis queries"""
        start_time = time.time()
        
        # Send thinking message first
        await self._send_thinking_message(query)
        
        # Get detailed response
        response = await self._get_deep_model_response(query['text'])
        
        # Send final response
        await self._send_response(query, response, tier_name)
        
        # Log response time
        response_time = time.time() - start_time
        self.logger.info(f"Deep response time: {response_time:.3f}s")

    def _get_canned_response(self, text: str) -> str:
        """Get pre-defined responses for instant queries"""
        responses = {
            'hello': "Hi there! How can I assist you today?",
            'hi': "Hello! What can I help you with?",
            'kumusta': "Kamusta! Paano kita matutulungan ngayon?",
            'thanks': "You're welcome! Is there anything else I can help with?",
            'bye': "Goodbye! Have a great day!"
        }
        
        # Get base word (hello -> hello, hi -> hi)
        base_word = text.split()[0].lower()
        return responses.get(base_word, "I'm here to help! What would you like to know?")

    async def _get_fast_model_response(self, text: str) -> str:
        """Get response from fast local model"""
        # Simulate model response
        return f"Fast response to: {text}"

    async def _get_deep_model_response(self, text: str) -> str:
        """Get detailed response from deep model"""
        # Simulate model response
        return f"Detailed analysis of: {text}"

    async def _send_thinking_message(self, query: Dict[str, Any]):
        """Send thinking message for deep queries"""
        message = {
            'type': 'thinking',
            'text': "Let me think about that for a moment...",
            'timestamp': datetime.now().isoformat()
        }
        self.push_socket.send_json(message)

    async def _send_response(self, query: Dict[str, Any], response: str, tier: str):
        """Send final response with tier information"""
        message = {
            'type': 'response',
            'text': response,
            'tier': tier,
            'timestamp': datetime.now().isoformat()
        }
        self.push_socket.send_json(message)

    def run(self):
        """Start the tiered responder"""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Tiered Responder shutting down...")
        finally:
            self.pull_socket.close()
            self.push_socket.close()
            self.context.term()

def main():
    responder = TieredResponder()
    responder.run()

if __name__ == "__main__":
    main()
