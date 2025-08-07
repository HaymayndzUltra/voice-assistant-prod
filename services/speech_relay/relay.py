"""
Speech Relay Service
--------------------
Forwards speech-trigger events from PC2 (Vision/Dream agents) to
MainPC StreamingTTSAgent via ZMQ.  Exposes Prometheus metrics.
"""
import asyncio, os, logging, grpc, sys, json, zmq
from pathlib import Path
from prometheus_client import start_http_server, Counter

# Add current directory to path for gRPC imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

import relay_pb2 as pb
import relay_pb2_grpc as pb_grpc

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("speech-relay")

DOWNSTREAM = os.getenv("MAINPC_TTS_ENDPOINT", "mainpc:5562")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9109"))
RELAY_PORT   = int(os.getenv("RELAY_PORT", "7130"))

TX = Counter("speech_relay_messages_total", "Msgs relayed")

class RelayServicer(pb_grpc.SpeechRelayServicer):
    def __init__(self):
        # Initialize ZMQ context and socket for downstream communication
        self.zmq_context = zmq.Context()
        self.tts_socket = self.zmq_context.socket(zmq.REQ)
        
        # Parse downstream endpoint (format: host:port)
        if ':' in DOWNSTREAM:
            host, port = DOWNSTREAM.split(':')
            self.tts_socket.connect(f"tcp://{host}:{port}")
            LOG.info(f"Connected to TTS agent at {host}:{port}")
        else:
            LOG.error(f"Invalid downstream endpoint format: {DOWNSTREAM}")
            raise ValueError(f"Invalid downstream endpoint format: {DOWNSTREAM}")
    
    async def Forward(self, request: pb.SpeechRequest, ctx):
        TX.inc()
        try:
            # Parse the JSON payload from the gRPC request
            payload = json.loads(request.payload)
            LOG.info(f"Forwarding speech request: {payload}")
            
            # Convert to ZMQ message format expected by StreamingTTSAgent
            zmq_message = {
                "text": payload.get("text", ""),
                "emotion": payload.get("emotion", "neutral"),
                "language": payload.get("language", "en"),
                "command": payload.get("command", None)
            }
            
            # Send via ZMQ to StreamingTTSAgent
            self.tts_socket.send_json(zmq_message)
            
            # Wait for response
            response = self.tts_socket.recv_json()
            LOG.info(f"TTS response: {response}")
            
            # Return success if TTS agent processed the request
            success = response.get("status") == "success"
            return pb.Ack(ok=success)
            
        except json.JSONDecodeError as e:
            LOG.error(f"Invalid JSON payload: {e}")
            return pb.Ack(ok=False)
        except zmq.ZMQError as e:
            LOG.error(f"ZMQ communication error: {e}")
            return pb.Ack(ok=False)
        except Exception as e:
            LOG.error(f"Error forwarding speech request: {e}")
            return pb.Ack(ok=False)

async def serve():
    server = grpc.aio.server()
    relay_servicer = RelayServicer()
    pb_grpc.add_SpeechRelayServicer_to_server(relay_servicer, server)
    server.add_insecure_port(f"[::]:{RELAY_PORT}")
    await server.start()
    LOG.info("Speech Relay listening on :%s → %s", RELAY_PORT, DOWNSTREAM)
    
    try:
        await server.wait_for_termination()
    finally:
        # Cleanup ZMQ resources
        if hasattr(relay_servicer, 'tts_socket'):
            relay_servicer.tts_socket.close()
        if hasattr(relay_servicer, 'zmq_context'):
            relay_servicer.zmq_context.term()

if __name__ == "__main__":
    # Prometheus
    start_http_server(METRICS_PORT)
    asyncio.run(serve())
