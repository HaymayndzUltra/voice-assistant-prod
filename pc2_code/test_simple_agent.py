import zmq
import time

class SimpleTestAgent:
    def __init__(self, port=7101):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.running = True
        
    def start(self):
        print(f"Starting SimpleTestAgent on port {self.port}")
        self.socket.bind(f"tcp://*:{self.port}")
        
        while self.running:
            try:
                # Receive request
                request = self.socket.recv_json()
                print(f"Received request: {request}")
                
                # Check if it's a health check
                if request.get('action') == 'health_check':
                    response = {
                        'status': 'ok',
                        'service': 'SimpleTestAgent',
                        'port': self.port,
                        'timestamp': time.time()
                    }
                else:
                    response = {
                        'status': 'unknown_action',
                        'message': f"Unknown action: {request.get('action', 'none')}"
                    }
                
                # Send response
                self.socket.send_json(response)
                print(f"Sent response: {response}")
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    
    def stop(self):
        self.running = False
        self.socket.close()
        self.context.term()

if __name__ == "__main__":
    agent = SimpleTestAgent(7101)
    try:
        agent.start()
    except KeyboardInterrupt:
        print("Shutting down...")
        agent.stop() 