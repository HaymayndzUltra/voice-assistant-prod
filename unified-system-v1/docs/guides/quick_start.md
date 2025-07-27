# Quick Start Guide

## Prerequisites

- Python 3.8+ 
- Docker & Docker Compose (optional)
- 4GB+ RAM (8GB recommended for full profile)
- Linux/Unix environment

## Installation

### Option 1: Local Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd unified-system-v1
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your settings
```

### Option 2: Docker Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd unified-system-v1
```

2. Build and run with Docker Compose:
```bash
docker-compose up -d
```

## Basic Usage

### Starting the System

Using the CLI:
```bash
# Start with default (core) profile
python main.py start

# Start with specific profile
python main.py start --profile vision
python main.py start --profile learning
python main.py start --profile tutoring
python main.py start --profile full
```

Using Docker:
```bash
# Start with profile
PROFILE=vision docker-compose up -d
```

### Checking System Status

```bash
# Check overall status
python main.py status

# Check specific agent health
python main.py health --agent ServiceRegistry

# View logs
tail -f logs/unified-system.log
```

### Running Tests

```bash
# Run all tests
python main.py test

# Run chaos tests
python main.py chaos

# Run routing benchmark
python main.py benchmark
```

### Stopping the System

```bash
# Using CLI
python main.py stop

# Using Docker
docker-compose down
```

## Profile Selection Guide

| Profile | Use Case | Memory | Agents |
|---------|----------|---------|--------|
| `core` | Basic conversational AI | 2GB | 16 |
| `vision` | Computer vision tasks | 4GB | 20 |
| `learning` | Adaptive learning | 6GB | 30 |
| `tutoring` | Educational assistant | 4GB | 28 |
| `full` | All capabilities | 8GB | 77 |

## Monitoring

### ObservabilityHub Dashboard
- URL: http://localhost:9000/dashboard
- Shows real-time agent status and metrics

### Prometheus Metrics
- URL: http://localhost:9090
- Query system metrics and alerts

### Grafana Dashboards
- URL: http://localhost:3000
- Default login: admin/admin

## Common Operations

### Loading Optional Agents

Optional agents load automatically when needed. To manually trigger:

```bash
curl -X POST http://localhost:7201/task \
  -H "Content-Type: application/json" \
  -d '{"type": "vision", "data": "..."}'
```

### Clearing Caches

```bash
# Clear model cache
curl -X POST http://localhost:7211/cache/clear

# Clear conversation memory
curl -X POST http://localhost:7220/memory/clear
```

## Troubleshooting

### Agent Won't Start
1. Check for port conflicts: `lsof -i :PORT`
2. Verify dependencies: `python main.py start --dry-run`
3. Check logs: `tail -f logs/agents/{agent_name}.log`

### High Memory Usage
1. Switch to a lighter profile
2. Check agent memory: `python main.py status`
3. Restart specific agents if needed

### System Not Responding
1. Check ObservabilityHub: http://localhost:9000/health
2. Review error logs: `grep ERROR logs/*.log`
3. Restart with core profile: `PROFILE=core python main.py start`

## Next Steps

- Read the [Operational Runbook](operational_runbook.md)
- Review [Architecture Documentation](../architecture/)
- Configure [Monitoring & Alerts](../monitoring/)
- Set up [CI/CD Pipeline](../../.github/workflows/ci.yml)