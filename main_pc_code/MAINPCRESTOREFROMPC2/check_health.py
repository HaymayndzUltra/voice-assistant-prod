#!/usr/bin/env python3

import zmq
import json
import sys
import time

ctx = zmq.Context()
s = ctx.socket(zmq.REQ)
s.setsockopt(zmq.LINGER, 0)
try:
    s.connect('tcp://localhost:5613')
    s.send_json({'action': 'get_system_health'})
    if s.poll(5000):
        resp = s.recv_json()
        print(json.dumps(resp, indent=2))
    else:
        print('No response from PredictiveHealthMonitor')
except Exception as e:
    print('Health check failed:', e)
finally:
    s.close()
    ctx.term() 