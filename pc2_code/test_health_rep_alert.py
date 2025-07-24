import zmq
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url
ctx = zmq.Context()
s = ctx.socket(zmq.REQ)
s.setsockopt(zmq.RCVTIMEO, 3000)
s.setsockopt(zmq.SNDTIMEO, 3000)
s.connect('tcp://localhost:5595')
s.send_json({'action':'health_check'})
print(s.recv_json())
s.close()
ctx.term() 