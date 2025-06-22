import zmq
import json
import time

class PerformanceMonitorHealth:
    def __init__(self, port=7103):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.running = True
    def start(self):
        print(f"Starting PerformanceMonitorHealth on port {self.port}")
        self.socket.bind(f"tcp://*:{self.port}")
        while self.running:
            try:
                request = self.socket.recv_json()
                if request.get('action') == 'health_check':
                    response = {'status': 'ok', 'service': 'PerformanceMonitor', 'port': self.port, 'timestamp': time.time()}
                else:
                    response = {'status': 'unknown_action', 'message': f"Unknown action: {request.get('action', 'none')}"}
                self.socket.send_json(response)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    def stop(self):
        self.running = False
        self.socket.close()
        self.context.term()

if __name__ == "__main__":
    agent = PerformanceMonitorHealth(7103)
    try:
        agent.start()
    except KeyboardInterrupt:
        print("Shutting down...")
        agent.stop() 