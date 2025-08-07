# Cross-Machine GPU Scheduler

Lightweight gRPC service that assigns jobs to the least-busy GPU across **MainPC**
and **PC2**. Exposes Prometheus metrics at `${PORT_OFFSET}+8155` and a `GPUScheduler.Query` RPC 
at `${PORT_OFFSET}+7155`.

## Port Configuration

The service respects the `PORT_OFFSET` environment variable for configurable port allocation:
- **gRPC Port**: `${PORT_OFFSET}+7155` (default: 7155)
- **Metrics Port**: `${PORT_OFFSET}+8155` (default: 8155)

## Environment Variables

- `PORT_OFFSET`: Port offset for configurable port allocation (default: 0)
- `HOSTNAME`: Host identifier for metrics (default: "local")

See `scheduler.proto` for API.
