Unified Observability Center (UOC)

Run locally
- Python: create venv and install `unified_observability_center/requirements.txt`
- Start API: `export UOC_API_TOKENS=devtoken && uvicorn unified_observability_center.api.rest:app --host 0.0.0.0 --port 9100`

Docker
- Build: `docker build -t uoc -f Dockerfile.uoc .`
- Run: `docker run -e UOC_API_TOKENS=devtoken -p 9100:9100 uoc`

Kubernetes
- Deploy NATS cluster: `kubectl apply -f k8s/nats-cluster.yaml`
- Deploy UOC: `kubectl apply -f k8s/uoc-deployment.yaml`

Testing
- Focused tests: `PYTHONPATH=$(pwd) pytest -q unified_observability_center/tests`
- Load test: `python unified_observability_center/tools/load_test.py`