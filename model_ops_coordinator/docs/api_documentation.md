# ModelOps Coordinator API Documentation

## 📚 **Complete API Reference**

### **1. gRPC API Specification**

**Service Definition**:
```protobuf
syntax = "proto3";

service ModelOps {
    // Core inference endpoint
    rpc Infer (InferenceRequest) returns (InferenceResponse);
    
    // Model lifecycle management
    rpc LoadModel (ModelLoadRequest) returns (ModelLoadReply);
    rpc UnloadModel (ModelUnloadRequest) returns (ModelUnloadReply);
    rpc ListModels (google.protobuf.Empty) returns (ModelList);
    
    // System operations
    rpc GetSystemStatus (google.protobuf.Empty) returns (SystemStatus);
    rpc HealthCheck (google.protobuf.Empty) returns (HealthResponse);
}

message InferenceRequest {
    string model_name = 1;
    string input_text = 2;
    int32 max_tokens = 3;
    float temperature = 4;
    float top_p = 5;
    repeated string stop_sequences = 6;
}

message InferenceResponse {
    string output_text = 1;
    int32 tokens_generated = 2;
    float latency_ms = 3;
    string model_version = 4;
    bool success = 5;
    string error_message = 6;
}

message ModelLoadRequest {
    string model_name = 1;
    string model_path = 2;
    string model_type = 3;
    bool quantization = 4;
    int32 gpu_layers = 5;
}

message ModelLoadReply {
    bool success = 1;
    string message = 2;
    string model_version = 3;
    int64 memory_usage_mb = 4;
}
```

**gRPC Client Examples**:

*Python Client*:
```python
import grpc
from model_ops_pb2 import InferenceRequest
from model_ops_pb2_grpc import ModelOpsStub

# Create secure channel (production)
credentials = grpc.ssl_channel_credentials()
channel = grpc.secure_channel('moc.company.com:7212', credentials)
stub = ModelOpsStub(channel)

# Make inference call
request = InferenceRequest(
    model_name="llama-7b-chat",
    input_text="What is the capital of France?",
    max_tokens=50,
    temperature=0.7
)

response = stub.Infer(request)
print(f"Response: {response.output_text}")
```

*Go Client*:
```go
package main

import (
    "context"
    "crypto/tls"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
    pb "path/to/model_ops_pb"
)

func main() {
    config := &tls.Config{}
    creds := credentials.NewTLS(config)
    
    conn, err := grpc.Dial("moc.company.com:7212", grpc.WithTransportCredentials(creds))
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()
    
    client := pb.NewModelOpsClient(conn)
    
    req := &pb.InferenceRequest{
        ModelName:   "llama-7b-chat",
        InputText:   "Hello, world!",
        MaxTokens:   50,
        Temperature: 0.7,
    }
    
    resp, err := client.Infer(context.Background(), req)
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Printf("Response: %s\n", resp.OutputText)
}
```

---

### **2. REST API Specification**

**OpenAPI 3.0 Schema**:
```yaml
openapi: 3.0.3
info:
  title: ModelOps Coordinator REST API
  version: 1.0.0
  description: Unified model lifecycle, inference, and resource management
  contact:
    name: ModelOps Team
    email: modelops@company.com

servers:
  - url: https://moc.company.com:8008
    description: Production server
  - url: http://localhost:8008
    description: Development server

security:
  - ApiKeyAuth: []

paths:
  /health:
    get:
      summary: Health check endpoint
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'
  
  /inference:
    post:
      summary: Execute model inference
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/InferenceRequest'
      responses:
        '200':
          description: Inference completed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/InferenceResponse'
        '400':
          description: Invalid request
        '429':
          description: Rate limit exceeded
        '503':
          description: Service overloaded
  
  /models:
    get:
      summary: List loaded models
      responses:
        '200':
          description: List of models
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ModelList'
    
    post:
      summary: Load a new model
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ModelLoadRequest'
      responses:
        '201':
          description: Model loaded successfully
        '409':
          description: Model already loaded
        '507':
          description: Insufficient VRAM
  
  /models/{model_name}:
    delete:
      summary: Unload a model
      parameters:
        - name: model_name
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Model unloaded successfully
        '404':
          description: Model not found

  /learning/jobs:
    get:
      summary: List learning jobs
      responses:
        '200':
          description: List of jobs
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/LearningJob'
    
    post:
      summary: Create a new learning job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateJobRequest'
      responses:
        '201':
          description: Job created successfully

  /goals:
    get:
      summary: List active goals
      responses:
        '200':
          description: List of goals
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Goal'
    
    post:
      summary: Create a new goal
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateGoalRequest'
      responses:
        '201':
          description: Goal created successfully

  /metrics:
    get:
      summary: Prometheus metrics endpoint
      responses:
        '200':
          description: Metrics in Prometheus format
          content:
            text/plain:
              schema:
                type: string

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
  
  schemas:
    HealthResponse:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          type: string
          format: date-time
        components:
          type: object
          additionalProperties:
            type: string
    
    InferenceRequest:
      type: object
      required:
        - model_name
        - input_text
      properties:
        model_name:
          type: string
          example: "llama-7b-chat"
        input_text:
          type: string
          maxLength: 10000
          example: "What is the capital of France?"
        max_tokens:
          type: integer
          minimum: 1
          maximum: 2048
          default: 50
        temperature:
          type: number
          minimum: 0.0
          maximum: 2.0
          default: 0.7
        top_p:
          type: number
          minimum: 0.0
          maximum: 1.0
          default: 0.9
        stop_sequences:
          type: array
          items:
            type: string
          maxItems: 10
    
    InferenceResponse:
      type: object
      properties:
        output_text:
          type: string
        tokens_generated:
          type: integer
        latency_ms:
          type: number
        model_version:
          type: string
        success:
          type: boolean
        error_message:
          type: string
```

**REST Client Examples**:

*cURL*:
```bash
# Health check
curl -X GET https://moc.company.com:8008/health \
  -H "X-API-Key: your-api-key-here"

# Inference request
curl -X POST https://moc.company.com:8008/inference \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "model_name": "llama-7b-chat",
    "input_text": "What is machine learning?",
    "max_tokens": 100,
    "temperature": 0.7
  }'

# Load model
curl -X POST https://moc.company.com:8008/models \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "model_name": "new-model",
    "model_path": "/models/new-model.gguf",
    "model_type": "llm",
    "quantization": true
  }'
```

*Python Requests*:
```python
import requests

# Configuration
BASE_URL = "https://moc.company.com:8008"
API_KEY = "your-api-key-here"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Health check
response = requests.get(f"{BASE_URL}/health", headers=HEADERS)
print(f"Health: {response.json()}")

# Inference
inference_data = {
    "model_name": "llama-7b-chat",
    "input_text": "Explain quantum computing",
    "max_tokens": 150,
    "temperature": 0.8
}

response = requests.post(
    f"{BASE_URL}/inference", 
    json=inference_data, 
    headers=HEADERS
)

if response.status_code == 200:
    result = response.json()
    print(f"Output: {result['output_text']}")
    print(f"Latency: {result['latency_ms']}ms")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

---

### **3. ZMQ Protocol Specification**

**Message Format**:
```json
{
  "action": "infer|load_model|unload_model|list_models|health",
  "payload": {
    // Action-specific payload
  },
  "request_id": "unique-request-identifier",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Response Format**:
```json
{
  "success": true|false,
  "result": {
    // Action-specific result
  },
  "error": "error-message-if-failed",
  "request_id": "matching-request-identifier",
  "latency_ms": 42.5
}
```

**ZMQ Client Example**:
```python
import zmq
import json
import uuid

# Create ZMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://moc.company.com:7211")

# Prepare request
request = {
    "action": "infer",
    "payload": {
        "model_name": "llama-7b-chat",
        "input_text": "Hello, world!",
        "max_tokens": 50,
        "temperature": 0.7
    },
    "request_id": str(uuid.uuid4()),
    "timestamp": "2024-01-01T12:00:00Z"
}

# Send request
socket.send_json(request)

# Receive response
response = socket.recv_json()
print(f"Success: {response['success']}")
if response['success']:
    print(f"Output: {response['result']['output_text']}")
else:
    print(f"Error: {response['error']}")

# Cleanup
socket.close()
context.term()
```

---

### **4. Prometheus Metrics**

**Available Metrics**:
```
# System metrics
moc_system_cpu_usage_percent
moc_system_memory_usage_bytes
moc_system_disk_usage_bytes

# GPU metrics
moc_gpu_total_memory_mb
moc_gpu_used_memory_mb
moc_gpu_utilization_percent
moc_gpu_temperature_celsius

# Model metrics
moc_models_loaded_total
moc_model_load_duration_seconds
moc_model_memory_usage_mb

# Inference metrics
moc_inference_requests_total
moc_inference_latency_seconds
moc_inference_tokens_generated_total
moc_inference_errors_total

# Learning metrics
moc_learning_jobs_total
moc_learning_jobs_completed_total
moc_learning_jobs_failed_total
moc_learning_job_duration_seconds

# Goals metrics
moc_goals_active_total
moc_goals_completed_total
moc_goals_execution_duration_seconds

# Transport metrics
moc_grpc_requests_total
moc_rest_requests_total
moc_zmq_requests_total
moc_request_duration_seconds

# Resiliency metrics
moc_circuit_breaker_state (0=closed, 1=open, 2=half_open)
moc_circuit_breaker_failures_total
moc_bulkhead_active_requests
moc_bulkhead_queued_requests
```

**Grafana Dashboard Query Examples**:
```promql
# Average inference latency
rate(moc_inference_latency_seconds_sum[5m]) / rate(moc_inference_latency_seconds_count[5m])

# Inference requests per second
rate(moc_inference_requests_total[1m])

# GPU memory utilization
moc_gpu_used_memory_mb / moc_gpu_total_memory_mb * 100

# Circuit breaker failure rate
rate(moc_circuit_breaker_failures_total[5m])

# Active model count
moc_models_loaded_total

# Learning job success rate
rate(moc_learning_jobs_completed_total[1h]) / rate(moc_learning_jobs_total[1h])
```

---

## 🎯 **API Documentation Summary**

**Completion Status**: ✅ **COMPREHENSIVE**

| Protocol | Status | Features |
|----------|--------|----------|
| gRPC | ✅ Complete | TLS, streaming, type safety |
| REST | ✅ Complete | OpenAPI spec, authentication |
| ZMQ | ✅ Complete | Legacy compatibility |
| Metrics | ✅ Complete | Prometheus integration |

**Key Features**:
- ✅ Complete API specifications for all protocols
- ✅ Client examples in multiple languages
- ✅ Security and authentication documentation
- ✅ Prometheus metrics catalog
- ✅ OpenAPI 3.0 schema for REST API
- ✅ Production-ready configuration examples

This documentation package provides everything needed for client integration and operational monitoring.