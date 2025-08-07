"""Sanity-check import & stub generation."""
import importlib, pathlib, subprocess, sys

def test_proto_generated():
    pkg = pathlib.Path("services/cross_gpu_scheduler")
    proto = pkg/"scheduler.proto"
    assert proto.exists()
    # Re-generate — should succeed and be idempotent
    subprocess.check_call([
        sys.executable, "-m", "grpc_tools.protoc",
        "-I", str(pkg), "--python_out", str(pkg),
        "--grpc_python_out", str(pkg), str(proto)
    ])
    importlib.import_module("services.cross_gpu_scheduler.scheduler_pb2")
