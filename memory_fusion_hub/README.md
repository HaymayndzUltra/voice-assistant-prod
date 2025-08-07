# Memory Fusion Hub (MFH)

A high-performance microservice that consolidates seven legacy memory agents into a unified, scalable solution.

## Features

- **Dual Transport**: ZMQ and gRPC APIs
- **Multi-Storage**: SQLite, PostgreSQL support with Redis caching
- **Resilience**: Circuit breakers, bulkheads, retry mechanisms
- **Event Sourcing**: Append-only event log for replication
- **Observability**: Prometheus metrics and structured logging
- **Performance**: Target ≤20ms p95 latency at 1,000 rps

## Development Status

This service is currently under development following an 8-phase implementation plan.

## Configuration

The service uses YAML configuration with environment variable substitution.
See `config/default.yaml` for the complete schema.