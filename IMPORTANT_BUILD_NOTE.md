# ⚠️ IMPORTANT BUILD NOTE

## 🔴 **CRITICAL: Python Module Imports**

The services expect these Python modules to exist:
- `common` - Shared utilities
- `model_ops_coordinator` - Model operations
- `real_time_audio_pipeline` - Audio processing
- `affective_processing_center` - Emotion processing
- `unified_observability_center` - Monitoring
- `memory_fusion_hub` - Memory management

### **IF YOU GET `ModuleNotFoundError`:**

The services have `pyproject.toml` files that define them as installable packages.
The Dockerfiles expect these to work.

### **Quick Fix if imports fail:**

1. **Make sure `common/` has `__init__.py`:**
```bash
touch common/__init__.py
touch common/core/__init__.py
touch common/transport/__init__.py
```

2. **Make sure each service has `__init__.py`:**
```bash
touch model_ops_coordinator/__init__.py
touch real_time_audio_pipeline/__init__.py
# etc...
```

3. **If `app.py` doesn't exist, create a placeholder:**
```python
# model_ops_coordinator/app.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8212)
```

### **The services expect this structure:**
```
/workspace/
├── common/
│   ├── __init__.py
│   ├── pyproject.toml
│   └── core/
├── model_ops_coordinator/
│   ├── __init__.py
│   ├── pyproject.toml
│   └── app.py
└── (other services...)
```

## 💡 **TIP: Test Python imports first**

Before building Docker images, test locally:
```bash
cd /workspace
python3 -c "import common"
python3 -c "import model_ops_coordinator"
```

If these fail, the Docker builds will also fail!

---
**This is just a precaution. The structure should already be correct.**