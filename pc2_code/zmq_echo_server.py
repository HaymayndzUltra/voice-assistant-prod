import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind('tcp://*:5555')
print('ZMQ Echo Server listening on port 5555...')

while True:
    try:
        msg = socket.recv_json()
        print('Received:', msg)
        socket.send_json({'echo': msg})
    except Exception as e:
        print('Error:', e)
        break

socket.close()
context.term() 