# Central Error Bus

ZeroMQ-based PUB/SUB service that gathers structured error events from all
agents (via IPC) and re-broadcasts them to any subscribers. Exposes Prometheus
metrics on `9105/metrics`.
