import zmq
import json
from common.env_helpers import get_env

def test_health():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect('tcp://localhost:5585')
    
    request = {'action': 'health_check'}
    print('Sending request:', request)
    socket.send_json(request)
    
    response = socket.recv_json()
    print('Received response:', response)
    
    socket.close()
    context.term()

if __name__ == '__main__':
    test_health() 