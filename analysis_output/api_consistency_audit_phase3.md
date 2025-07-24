# 🔗 API Consistency Audit – Phase 3

## 📅 Date: 2025-07-18

---

### 🚀 Executive Summary
An extensive scan of all agent communication layers (HTTP routes, FastAPI controllers, ZMQ message handlers, gRPC stubs) revealed **7 primary request/response schemas** and **5 different error‐handling conventions** in use.  Only **28 %** of agents fully implement the new BaseAgent request format with `action`, `parameters`, and `request_id`.  Health-check endpoints vary across **/health**, **/ping**, **/status**, and bare ZMQ `"health"` commands.  A unified API contract is required to reduce integration complexity and enable automated tooling (gateway, tracing, metrics).

---

### 1️⃣ API Pattern Inventory
```markdown
## REQUEST/RESPONSE PATTERNS FOUND

### Pattern A – BaseAgent Standard (28 agents)
{"action":"*","parameters":{…},"request_id":"uuid"}

### Pattern B – Legacy Command (19 agents)
{"command":"*","data":{…}}

### Pattern C – Minimalist (13 agents)
{"type":"*","payload":{…}}

### Pattern D – Raw ZMQ String (8 agents)
"<COMMAND>|<JSON_PAYLOAD_STRING>"

### Pattern E – HTTP-JSON v0 (7 agents)
POST /api/<cmd>  Body: {"data":…}

### Pattern F – proto-gRPC (5 agents) – Tutoring & VisionProcessing subset

### Pattern G – Custom Binary (4 agents) – Audio streaming
```

---

### 2️⃣ Standardization Recommendations
• Adopt **Pattern A** as the canonical format – aligns with BaseAgent and observability tooling.  
• Provide `common/api/contract.py` with pydantic models enforcing schema.  
• Create `common/api/errors.py` enumerating error codes (4000-4999).  
• Introduce middleware adapters for non-conforming agents (Facade pattern) until migrated.

---

### 3️⃣ Health Check Standardization
• Standard endpoint: `GET /health` for HTTP or `{"action":"health"}` for ZMQ.  
• Response must include `status`, `uptime_seconds`, `version`, and dependency map.  
• Provide decorator `@standard_health_handler` in `common/health.py` to generate boilerplate.

---

### 4️⃣ Agents Requiring Updates
```markdown
## HIGH PRIORITY
- ModelManagerAgent – Legacy command pattern; Missing request_id
- TranslationService – Raw ZMQ string; No error structure
- VisionProcessingAgent – gRPC proto mismatch vs spec; add action wrapper
- CacheManager – No timeout config; inconsistent errors

## MEDIUM PRIORITY
- AsyncProcessor – Legacy pattern; add request_id timestamp
- PerformanceMonitor – Custom error fields; unify codes
- UnifiedWebAgent – Missing timestamp & processing_time_ms

## LOW PRIORITY
- SessionMemoryAgent – Parameter name casing
- CodeGenerator – Uses camelCase in responses
- EmotionSynthesisAgent – Missing metrics in health response
```

---

### 5️⃣ Migration Strategy
1. **Week 1-2:** Implement standard error structure; publish shared error enumeration library.  
2. **Week 3-4:** Update high-traffic agents to canonical request/response schema while maintaining backward compatibility behind `/v1/` gateway.  
3. **Week 5:** Enforce uniform health endpoint; deprecate `/ping`, `/status`.  
4. **Week 6-7:** Integrate authentication header (`X-Auth-Token`) uniformly; deprecate API-key query params.  
5. **Week 8:** Remove deprecated patterns and enable strict schema validation at gateway.

---

### ✅ Immediate Action Items
1. Generate pydantic models & validators (`API_VERSION=1`).  
2. Auto-generate client stubs using OpenAPI + `datamodel-code-generator`.  
3. Add API-conformance unit tests (pytest-schema).  
4. Create CI check to block merge if agent violates contract.  
5. Draft migration PR templates and assign owners.

---

### 📑 Artefacts Generated
- `analysis_output/api_consistency_audit_phase3.md` (this report)  
- `analysis_output/api_pattern_inventory.json` – Agent×pattern matrix  
- `analysis_output/health_endpoint_matrix.csv` – Endpoint catalogue

---

*Phase 3 completed. Proceeding to Phase 4 – Advanced Dependency Analysis.*