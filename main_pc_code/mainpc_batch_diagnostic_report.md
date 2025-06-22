# Main PC Batch Diagnostic Report

## SECTION 1: ROOT CAUSE ANALYSIS

**Test Subject:** FORMAINPC/NLLBAdapter.py

**Full Foreground Output:**
```
ERROR:root:Error loading configuration: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
ERROR:NLLBTranslationAdapter:Error binding to port 5581 on address 0.0.0.0: Address already in use (addr='tcp://0.0.0.0:5581')
WARNING:NLLBTranslationAdapter:Attempting fallback bind to tcp://127.0.0.1:5581
ERROR:NLLBTranslationAdapter:Fallback bind also failed: Address already in use (addr='tcp://127.0.0.1:5581')
ERROR:NLLBTranslationAdapter:Error starting service: Cannot bind to port 5581
ERROR:NLLBTranslationAdapter:Traceback (most recent call last):
  File "/home/haymayndz/Voice-Assistant-Prod/FORMAINPC/NLLBAdapter.py", line 149, in __init__
    self.socket.bind(f"tcp://{self.bind_address}:{self.service_port}")
  File "/home/haymayndz/.local/lib/python3.10/site-packages/zmq/sugar/socket.py", line 320, in bind
    super().bind(addr)
  File "zmq/backend/cython/_zmq.py", line 998, in zmq.backend.cython._zmq.Socket.bind
  File "zmq/backend/cython/_zmq.py", line 187, in zmq.backend.cython._zmq._check_rc
zmq.error.ZMQError: Address already in use (addr='tcp://0.0.0.0:5581')

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/haymayndz/Voice-Assistant-Prod/FORMAINPC/NLLBAdapter.py", line 156, in __init__
    self.socket.bind(f"tcp://127.0.0.1:{self.service_port}")
  File "/home/haymayndz/.local/lib/python3.10/site-packages/zmq/sugar/socket.py", line 320, in bind
    super().bind(addr)
  File "zmq/backend/cython/_zmq.py", line 998, in zmq.backend.cython._zmq.Socket.bind
  File "zmq/backend/cython/_zmq.py", line 187, in zmq.backend.cython._zmq._check_rc
zmq.error.ZMQError: Address already in use (addr='tcp://127.0.0.1:5581')

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/haymayndz/Voice-Assistant-Prod/FORMAINPC/NLLBAdapter.py", line 522, in <module>
    service = NLLBTranslationAdapter()
  File "/home/haymayndz/Voice-Assistant-Prod/FORMAINPC/NLLBAdapter.py", line 161, in __init__
    raise RuntimeError(f"Cannot bind to port {self.service_port}") from e2
RuntimeError: Cannot bind to port 5581

WARNING: Could not import system_config. Using default/hardcoded settings for NLLBTranslationAdapter.
```

**Hypothesis:**
The systemic failure across all agents is likely due to one or more of the following root causes:
- The required ZMQ port (5581) is already in use, possibly by a previously launched or orphaned process, preventing new agents from binding to it.
- There is a configuration or environment issue (e.g., corrupted or missing system_config, or a misconfigured UTF-8 file) that causes agents to fall back to defaults and fail to initialize properly.
- The batch health check logic assumes agents will remain running, but if they crash immediately due to the above issues, the PID check and health logic will always report failure.

**Recommendation:**
- Investigate and free up the required ZMQ ports before running health checks.
- Check for and terminate any orphaned or zombie processes using the relevant ports.
- Validate and repair the system_config file and ensure all dependencies are correctly configured. 