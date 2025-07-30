"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
WP-06 OpenAPI Documentation Generator
Generates OpenAPI/Swagger documentation for API contracts
"""

import json
from typing import Dict, Any, List, Optional
from common.api.contract import APIProcessor, APIContract, APIVersion, Status, Priority, MessageType
from common.api.standard_contracts import STANDARD_CONTRACTS
import logging

logger = logging.getLogger(__name__)

class OpenAPIGenerator:
    """Generate OpenAPI/Swagger documentation for API contracts"""
    
    def __init__(self, title: str = "AI System API", version: str = "1.0.0"):
        self.title = title
        self.version = version
        self.base_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "AI System Inter-Agent Communication API",
                "contact": {
                    "name": "AI System API Support",
                    "email": "api-support@aisystem.com"
                }
            },
            "servers": [
                {"url": "http://localhost:8000", "description": "Local development"},
                {"url": "https://api.aisystem.com", "description": "Production"}
            ],
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "AgentAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Agent-ID"
                    }
                }
            },
            "paths": {},
            "tags": []
        }
    
    def _get_base_schemas(self) -> Dict[str, Any]:
        """Get base API schemas"""
        return {
            "APIHeader": {
                "type": "object",
                "required": ["message_id", "timestamp", "version", "message_type", "source_agent", "target_agent"],
                "properties": {
                    "message_id": {"type": "string", "format": "uuid"},
                    "timestamp": {"type": "number", "format": "float"},
                    "version": {"type": "string", "enum": [v.value for v in APIVersion]},
                    "message_type": {"type": "string", "enum": [t.value for t in MessageType]},
                    "source_agent": {"type": "string"},
                    "target_agent": {"type": "string"},
                    "correlation_id": {"type": "string", "format": "uuid"},
                    "priority": {"type": "string", "enum": [p.value for p in Priority]},
                    "timeout": {"type": "number", "format": "float", "minimum": 0}
                }
            },
            "APIResponse": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"type": "string", "enum": [s.value for s in Status]},
                    "data": {"type": "object", "additionalProperties": True},
                    "error": {"type": "string"},
                    "error_code": {"type": "string"},
                    "metadata": {"type": "object", "additionalProperties": True},
                    "processing_time": {"type": "number", "format": "float"}
                }
            },
            "APIMessage": {
                "type": "object",
                "required": ["header", "payload"],
                "properties": {
                    "header": {"$ref": "#/components/schemas/APIHeader"},
                    "payload": {"type": "object", "additionalProperties": True}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "required": ["status", "error"],
                "properties": {
                    "status": {"type": "string", "enum": ["error"]},
                    "error": {"type": "string"},
                    "error_code": {"type": "string"},
                    "metadata": {"type": "object", "additionalProperties": True}
                }
            },
            "SuccessResponse": {
                "type": "object",
                "required": ["status", "data"],
                "properties": {
                    "status": {"type": "string", "enum": ["success"]},
                    "data": {"type": "object", "additionalProperties": True},
                    "metadata": {"type": "object", "additionalProperties": True},
                    "processing_time": {"type": "number", "format": "float"}
                }
            }
        }
    
    def _generate_contract_schema(self, contract: APIContract) -> Dict[str, Any]:
        """Generate schema for a specific contract"""
        contract_name = contract.name.replace("_", " ").title()
        
        # Base request schema
        request_schema = {
            "type": "object",
            "required": ["endpoint"],
            "properties": {
                "endpoint": {"type": "string", "description": f"Endpoint for {contract_name}"}
            }
        }
        
        # Base response schema
        response_schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": [s.value for s in Status]},
                "data": {"type": "object", "additionalProperties": True}
            }
        }
        
        return {
            f"{contract.name}Request": request_schema,
            f"{contract.name}Response": response_schema
        }
    
    def _generate_standard_contract_schemas(self) -> Dict[str, Any]:
        """Generate schemas for standard contracts"""
        schemas = {}
        
        # Health Check
        schemas["HealthCheckResponse"] = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                "timestamp": {"type": "number"},
                "agent": {"type": "string"}
            }
        }
        
        # Status
        schemas["StatusResponse"] = {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "inactive", "busy"]},
                "uptime": {"type": "number"},
                "load": {
                    "type": "object",
                    "properties": {
                        "cpu": {"type": "number", "minimum": 0, "maximum": 100},
                        "memory": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                },
                "connections": {
                    "type": "object",
                    "properties": {
                        "active": {"type": "integer", "minimum": 0},
                        "total": {"type": "integer", "minimum": 0}
                    }
                }
            }
        }
        
        # Configuration
        schemas["ConfigRequest"] = {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": ["get", "set", "list"]},
                "key": {"type": "string"},
                "value": {"type": "string"}
            }
        }
        
        schemas["ConfigResponse"] = {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
                "type": {"type": "string"},
                "updated": {"type": "boolean"},
                "config_keys": {"type": "array", "items": {"type": "string"}},
                "total": {"type": "integer"}
            }
        }
        
        # Model Management
        schemas["ModelRequest"] = {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": ["load", "unload", "predict", "train", "list"]},
                "model_id": {"type": "string"},
                "input_data": {"type": "object", "additionalProperties": True}
            }
        }
        
        schemas["ModelResponse"] = {
            "type": "object",
            "properties": {
                "model_id": {"type": "string"},
                "status": {"type": "string"},
                "model_info": {"type": "object", "additionalProperties": True},
                "predictions": {"type": "array", "items": {"type": "object"}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "models": {"type": "array", "items": {"type": "object"}}
            }
        }
        
        return schemas
    
    def _generate_paths(self, processor: APIProcessor) -> Dict[str, Any]:
        """Generate OpenAPI paths from registered contracts"""
        paths = {}
        
        for contract_name, contract in processor.registry.contracts.items():
            # Get endpoints for this contract
            endpoints = [ep for ep, cn in processor.registry.routes.items() if cn == contract_name]
            
            for endpoint in endpoints:
                paths[endpoint] = {
                    "post": {
                        "tags": [contract_name],
                        "summary": f"{contract.name.replace('_', ' ').title()} operation",
                        "description": f"Execute {contract.name} operation",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIMessage"}
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful operation",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                }
                            },
                            "400": {
                                "description": "Invalid request",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                }
                            },
                            "429": {
                                "description": "Rate limit exceeded",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                }
                            },
                            "500": {
                                "description": "Internal server error",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                }
                            }
                        },
                        "security": [{"AgentAuth": []}]
                    }
                }
        
        return paths
    
    def _generate_tags(self, processor: APIProcessor) -> List[Dict[str, str]]:
        """Generate OpenAPI tags from contracts"""
        tags = []
        
        for contract_name, contract in processor.registry.contracts.items():
            tags.append({
                "name": contract_name,
                "description": f"{contract.name.replace('_', ' ').title()} operations"
            })
        
        return tags
    
    def generate_spec(self, processor: Optional[APIProcessor] = None) -> Dict[str, Any]:
        """Generate complete OpenAPI specification"""
        spec = self.base_spec.copy()
        
        # Add base schemas
        spec["components"]["schemas"].update(self._get_base_schemas())
        spec["components"]["schemas"].update(self._generate_standard_contract_schemas())
        
        if processor:
            # Add contract-specific schemas
            for contract in processor.registry.contracts.values():
                contract_schemas = self._generate_contract_schema(contract)
                spec["components"]["schemas"].update(contract_schemas)
            
            # Generate paths and tags
            spec["paths"] = self._generate_paths(processor)
            spec["tags"] = self._generate_tags(processor)
        else:
            # Use standard contracts if no processor provided
            spec["paths"] = self._generate_standard_paths()
            spec["tags"] = self._generate_standard_tags()
        
        return spec
    
    def _generate_standard_paths(self) -> Dict[str, Any]:
        """Generate paths for standard contracts"""
        paths = {}
        
        for contract_name in STANDARD_CONTRACTS.keys():
            endpoint = f"/api/v1/{contract_name}"
            paths[endpoint] = {
                "post": {
                    "tags": [contract_name],
                    "summary": f"{contract_name.replace('_', ' ').title()} operation",
                    "description": f"Execute {contract_name} operation",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/APIMessage"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid request",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            }
                        }
                    },
                    "security": [{"AgentAuth": []}]
                }
            }
        
        return paths
    
    def _generate_standard_tags(self) -> List[Dict[str, str]]:
        """Generate tags for standard contracts"""
        tags = []
        
        for contract_name in STANDARD_CONTRACTS.keys():
            tags.append({
                "name": contract_name,
                "description": f"{contract_name.replace('_', ' ').title()} operations"
            })
        
        return tags
    
    def generate_json(self, processor: Optional[APIProcessor] = None, indent: int = 2) -> str:
        """Generate OpenAPI specification as JSON string"""
        spec = self.generate_spec(processor)
        return json.dumps(spec, indent=indent)
    
    def generate_yaml(self, processor: Optional[APIProcessor] = None) -> str:
        """Generate OpenAPI specification as YAML string"""
        try:
            import yaml
            spec = self.generate_spec(processor)
            return yaml.dump(spec, default_flow_style=False, sort_keys=False)
        except ImportError:
            logger.warning("PyYAML not available, returning JSON format")
            return self.generate_json(processor)
    
    def save_spec(self, filename: str, processor: Optional[APIProcessor] = None, format: str = "json"):
        """Save OpenAPI specification to file"""
        if format.lower() == "yaml":
            content = self.generate_yaml(processor)
        else:
            content = self.generate_json(processor)
        
        with open(filename, 'w') as f:
            f.write(content)
        
        logger.info(f"OpenAPI specification saved to {filename}")

def generate_api_documentation(processor: Optional[APIProcessor] = None, 
                             output_file: str = "api_spec.json") -> str:
    """Generate API documentation for the AI system"""
    generator = OpenAPIGenerator(
        title="AI System Inter-Agent API",
        version="1.0.0"
    )
    
    # Generate and save specification
    spec_json = generator.generate_json(processor)
    generator.save_spec(output_file, processor)
    
    logger.info(f"API documentation generated: {output_file}")
    return spec_json

def create_swagger_ui_html(spec_url: str = "/api_spec.json") -> str:
    """Create Swagger UI HTML page"""
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI System API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: '{spec_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>
"""
    return html_template

if __name__ == "__main__":
    # Generate documentation for standard contracts
    from common.api.contract import get_api_processor
    from common.api.standard_contracts import register_all_standard_contracts
    
    processor = get_api_processor()
    register_all_standard_contracts(processor)
    
    # Generate OpenAPI spec
    generate_api_documentation(processor, "api_spec.json")
    
    # Create Swagger UI HTML
    with open("api_docs.html", "w") as f:
        f.write(create_swagger_ui_html())
    
    print("API documentation generated:")
    print("- OpenAPI spec: api_spec.json")
    print("- Swagger UI: api_docs.html") 