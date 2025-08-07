# Cross-Machine GPU Scheduler

Lightweight gRPC service that assigns jobs to the least-busy GPU across **MainPC**
and **PC2**. Exposes Prometheus metrics at :8000 and a `GPUScheduler.Query` RPC 
at :7155.

See `scheduler.proto` for API.
