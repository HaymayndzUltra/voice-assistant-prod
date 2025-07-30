import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.setsockopt(zmq.RCVTIMEO, 3000)
socket.setsockopt(zmq.SNDTIMEO, 3000)
socket.connect('tcp://localhost:5555')

msg = {'test': 'hello world'}
print('Sending:', msg)
socket.send_json(msg)
try:
    response = socket.recv_json()
    print('Received:', response)
except Exception as e:
    print('Error:', e)

socket.close()
context.term() 