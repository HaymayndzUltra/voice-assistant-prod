@echo off
set PYTHONPATH=%PYTHONPATH%;%CD%

echo Checking Model Voting System Health...

REM Check voting manager
echo Checking Model Voting Manager...
python -c "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.setsockopt(zmq.RCVTIMEO, 2000); socket.connect('tcp://localhost:5620'); socket.send_string('{\"action\": \"health_check\"}'); response = socket.recv_string(); print('Voting Manager Response:', response)"

REM Check voting adapter
echo Checking Model Voting Adapter...
python -c "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.setsockopt(zmq.RCVTIMEO, 2000); socket.connect('tcp://localhost:5621'); socket.send_string('{\"action\": \"health_check\"}'); response = socket.recv_string(); print('Voting Adapter Response:', response)"

echo.
echo Health check completed 