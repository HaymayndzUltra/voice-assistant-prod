import asyncio, os, grpc, logging
import pynvml
from prometheus_client import start_http_server, Gauge
import scheduler_pb2 as pb
import scheduler_pb2_grpc as pb_grpc

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("gpu-scheduler")

GPU_UTIL = Gauge("gpu_utilisation_percent",
                 "GPU utilisation", ["host", "index"])

class Scheduler(pb_grpc.GPUSchedulerServicer):
    def __init__(self) -> None:
        pynvml.nvmlInit()
        LOGGER.info("NVML initialised with %d GPU(s)",
                    pynvml.nvmlDeviceGetCount())

    async def Query(self, request: pb.ScheduleRequest,
                    context: grpc.aio.ServicerContext) -> pb.ScheduleReply:
        """Pick the least-busy GPU and return its index."""
        idx = min(
            range(pynvml.nvmlDeviceGetCount()),
            key=lambda i: pynvml.nvmlDeviceGetUtilizationRates(
                pynvml.nvmlDeviceGetHandleByIndex(i)
            ).gpu
        )
        util = pynvml.nvmlDeviceGetUtilizationRates(
            pynvml.nvmlDeviceGetHandleByIndex(idx)
        ).gpu
        host = os.getenv("HOSTNAME", "local")
        GPU_UTIL.labels(host, idx).set(util)
        LOGGER.debug("Job %s scheduled on GPU %d (util=%d%%)",
                     request.job_id, idx, util)
        return pb.ScheduleReply(target_gpu=idx)

async def serve() -> None:
    server = grpc.aio.server()
    pb_grpc.add_GPUSchedulerServicer_to_server(Scheduler(), server)
    server.add_insecure_port("[::]:7155")          # gRPC
    start_http_server(8000)                        # Prometheus
    LOGGER.info("GPU Scheduler running on :7155  (metrics :8000)")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
