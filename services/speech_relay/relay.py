"""
Speech Relay Service
--------------------
Forwards speech-trigger events from PC2 (Vision/Dream agents) to
MainPC StreamingTTSAgent via gRPC.  Exposes Prometheus metrics.
"""
import asyncio, os, logging, grpc, sys
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
    async def Forward(self, request: pb.SpeechRequest, ctx):
        TX.inc()
        # forward to MainPC TTS
        async with grpc.aio.insecure_channel(DOWNSTREAM) as ch:
            stub = pb_grpc.SpeechRelayStub(ch)
            await stub.Forward(request)
        return pb.Ack(ok=True)

async def serve():
    server = grpc.aio.server()
    pb_grpc.add_SpeechRelayServicer_to_server(RelayServicer(), server)
    server.add_insecure_port(f"[::]:{RELAY_PORT}")
    await server.start()
    LOG.info("Speech Relay listening on :%s → %s", RELAY_PORT, DOWNSTREAM)
    await server.wait_for_termination()

if __name__ == "__main__":
    # Prometheus
    start_http_server(METRICS_PORT)
    asyncio.run(serve())
