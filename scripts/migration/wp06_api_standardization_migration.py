#!/usr/bin/env python3
"""
WP-06 API Standardization Migration Script
Migrates agents to use standardized API contracts and communication patterns
Target: Agents with inconsistent API patterns
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class APIAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect API usage patterns"""
    
    def __init__(self):
        self.api_patterns = []
        self.response_patterns = []
        self.http_endpoints = []
        self.message_patterns = []
        self.api_score = 0
        
    def visit_FunctionDef(self, node):
        # Look for HTTP endpoint handlers
        if any(decorator.id == 'app.route' if hasattr(decorator, 'id') else False 
               for decorator in node.decorator_list):
            self.http_endpoints.append(f"HTTP endpoint: {node.name} (line {node.lineno})")
            self.api_score += 3
        
        # Look for API response functions
        if 'response' in node.name.lower() or 'reply' in node.name.lower():
            self.response_patterns.append(f"Response function: {node.name} (line {node.lineno})")
            self.api_score += 2
            
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Look for JSON response patterns
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['jsonify', 'json', 'dumps']):
            self.api_patterns.append(f"JSON response (line {node.lineno})")
            self.api_score += 1
        
        # Look for HTTP request patterns
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['get', 'post', 'put', 'delete', 'request']):
            self.api_patterns.append(f"HTTP request (line {node.lineno})")
            self.api_score += 2
        
        # Look for message sending patterns
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['send', 'send_message', 'publish', 'emit']):
            self.message_patterns.append(f"Message send (line {node.lineno})")
            self.api_score += 2
            
        self.generic_visit(node)

def find_api_intensive_agents() -> List[Path]:
    """Find agents that need API standardization"""
    root = Path.cwd()
    agent_files = []
    
    search_dirs = [
        "main_pc_code/agents",
        "pc2_code/agents", 
        "common",
        "phase1_implementation",
        "phase2_implementation"
    ]
    
    for search_dir in search_dirs:
        search_path = root / search_dir
        if search_path.exists():
            for python_file in search_path.rglob("*.py"):
                if (python_file.name != "__init__.py" and 
                    not python_file.name.startswith("test_") and
                    "_test" not in python_file.name):
                    agent_files.append(python_file)
    
    return agent_files

def analyze_api_patterns(file_path: Path) -> Dict:
    """Analyze a file for API usage patterns"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = APIAnalyzer()
        analyzer.visit(tree)
        
        # Additional pattern-based analysis
        content_lower = content.lower()
        
        # API response patterns
        response_patterns = len(re.findall(r'(return.*json|response.*json|jsonify|\.json\(\))', content_lower))
        
        # HTTP status code patterns  
        status_patterns = len(re.findall(r'(status.*code|http.*status|200|404|500)', content_lower))
        
        # Request/response patterns
        request_patterns = len(re.findall(r'(request\.get|request\.post|@app\.route)', content_lower))
        
        # Inconsistent response formats
        inconsistent_responses = len(re.findall(r'(return.*\{|return.*dict|return.*success)', content_lower))
        
        return {
            'file_path': file_path,
            'api_patterns': analyzer.api_patterns,
            'response_patterns': analyzer.response_patterns,
            'http_endpoints': analyzer.http_endpoints,
            'message_patterns': analyzer.message_patterns,
            'response_count': response_patterns,
            'status_count': status_patterns,
            'request_count': request_patterns,
            'inconsistent_count': inconsistent_responses,
            'api_score': analyzer.api_score + response_patterns + status_patterns + request_patterns,
            'needs_standardization': analyzer.api_score > 5 or inconsistent_responses > 3,
            'priority': 'high' if analyzer.api_score > 15 else 'medium' if analyzer.api_score > 8 else 'low'
        }
    
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e),
            'api_score': 0,
            'needs_standardization': False,
            'priority': 'low'
        }

def generate_api_integration_example(file_path: Path) -> str:
    """Generate example code for API standardization integration"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-06 API Standardization Integration for {agent_name}
# Add these imports and patterns to standardize your API

from common.api.contract import (
    get_api_processor, create_request, create_event,
    APIMessage, APIResponse, APIHeader, Status, Priority
)
from common.api.standard_contracts import register_all_standard_contracts

class {agent_name.title().replace("_", "")}APIIntegration:
    """API standardization for {agent_name}"""
    
    def __init__(self):
        self.api_processor = get_api_processor()
        register_all_standard_contracts(self.api_processor)
    
    def create_standard_response(self, data=None, error=None):
        """Create standardized API response"""
        if error:
            return APIResponse.error(error)
        return APIResponse.success(data)
    
    def send_standard_request(self, target_agent: str, endpoint: str, data: dict = None):
        """Send standardized API request"""
        message = create_request(
            source_agent="{agent_name}",
            target_agent=target_agent,
            endpoint=endpoint,
            data=data,
            priority=Priority.NORMAL
        )
        return message
    
    def broadcast_event(self, event_type: str, data: dict = None):
        """Broadcast standardized event"""
        message = create_event(
            source_agent="{agent_name}",
            event_type=event_type,
            data=data
        )
        return message
    
    async def process_api_message(self, message: APIMessage) -> APIMessage:
        """Process incoming API message with standardization"""
        return await self.api_processor.process_message(message)

# Example usage:
# api_integration = {agent_name.title().replace("_", "")}APIIntegration()
# response = api_integration.create_standard_response({{"status": "ready"}})
# request = api_integration.send_standard_request("target_agent", "/health_check")
'''
    
    return integration_example

def create_api_contract_template(agent_name: str) -> str:
    """Create custom API contract template for agent"""
    contract_template = f'''
# Custom API Contract for {agent_name}
from common.api.contract import APIContract, APIMessage, APIResponse, APIVersion, Status
from typing import Dict, Any

class {agent_name.title().replace("_", "")}Contract(APIContract):
    """Custom API contract for {agent_name} operations"""
    
    @property
    def name(self) -> str:
        return "{agent_name}"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate {agent_name} request"""
        # Add your validation logic here
        required_fields = ["action"]  # Customize as needed
        return all(field in payload for field in required_fields)
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate {agent_name} response"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process {agent_name} request"""
        action = message.payload.get("action")
        
        if action == "status":
            return APIResponse.success({{
                "agent": "{agent_name}",
                "status": "active",
                "capabilities": []  # Add your capabilities
            }})
        
        elif action == "process":
            # Add your processing logic here
            data = message.payload.get("data")
            return APIResponse.success({{
                "processed": True,
                "result": data  # Replace with actual processing
            }})
        
        return APIResponse.error(f"Unknown action: {{action}}")

# Register the contract
def register_{agent_name}_contract(processor):
    """Register {agent_name} contract with API processor"""
    contract = {agent_name.title().replace("_", "")}Contract()
    endpoints = ["/{agent_name}", "/api/v1/{agent_name}"]
    processor.register_contract(contract, endpoints)
'''
    
    return contract_template

def update_requirements_for_api_standardization():
    """Update requirements.txt with API standardization dependencies"""
    requirements_path = Path("requirements.txt")
    
    try:
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        # API standardization dependencies
        new_deps = [
            "# WP-06 API Standardization Dependencies",
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "pydantic==2.5.0",
            "python-multipart==0.0.6",
            "PyYAML==6.0.1"
        ]
        
        # Add dependencies if not already present
        for dep in new_deps:
            dep_name = dep.split('==')[0].replace("# ", "")
            if dep_name not in content:
                content += f"\n{dep}"
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated requirements.txt with API standardization dependencies")
        return True
    
    except Exception as e:
        print(f"❌ Error updating requirements.txt: {e}")
        return False

def generate_api_documentation():
    """Generate API documentation"""
    try:
        from common.api.openapi_generator import generate_api_documentation
        from common.api.contract import get_api_processor
        from common.api.standard_contracts import register_all_standard_contracts
        
        processor = get_api_processor()
        register_all_standard_contracts(processor)
        
        # Generate OpenAPI spec
        generate_api_documentation(processor, "docs/api_spec.json")
        
        # Create Swagger UI
        from common.api.openapi_generator import create_swagger_ui_html
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        
        with open(docs_dir / "api_docs.html", "w") as f:
            f.write(create_swagger_ui_html("/api_spec.json"))
        
        print(f"✅ Generated API documentation in docs/")
        return True
        
    except Exception as e:
        print(f"❌ Error generating API documentation: {e}")
        return False

def main():
    print("🚀 WP-06: API STANDARDIZATION MIGRATION")
    print("=" * 50)
    
    # Update requirements first
    update_requirements_for_api_standardization()
    
    # Find API-intensive agents
    agent_files = find_api_intensive_agents()
    print(f"📁 Found {len(agent_files)} agent files to analyze")
    
    # Analyze API patterns
    analysis_results = []
    for agent_file in agent_files:
        result = analyze_api_patterns(agent_file)
        analysis_results.append(result)
    
    # Sort by API score
    analysis_results.sort(key=lambda x: x.get('api_score', 0), reverse=True)
    
    # Filter candidates for standardization
    high_priority = [r for r in analysis_results if r.get('api_score', 0) >= 15]
    standardization_candidates = [r for r in analysis_results if r.get('needs_standardization', False)]
    
    print(f"\n📊 API STANDARDIZATION ANALYSIS:")
    print(f"✅ High priority targets: {len(high_priority)}")
    print(f"🔧 Standardization candidates: {len(standardization_candidates)}")
    
    # Show top agents needing API standardization
    if high_priority:
        print(f"\n🎯 TOP API STANDARDIZATION TARGETS:")
        for result in high_priority[:10]:  # Show top 10
            file_path = result['file_path']
            score = result.get('api_score', 0)
            print(f"\n📄 {file_path} (Score: {score})")
            print(f"   🔌 API patterns: {result.get('response_count', 0)}")
            print(f"   📡 HTTP endpoints: {len(result.get('http_endpoints', []))}")
            print(f"   💬 Message patterns: {len(result.get('message_patterns', []))}")
            print(f"   🎯 Priority: {result.get('priority', 'low')}")
    
    # Generate integration examples and templates
    examples_dir = Path("docs/api_integration_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    templates_dir = Path("docs/api_contract_templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    for result in standardization_candidates[:15]:  # Top 15 candidates
        file_path = result['file_path']
        agent_name = file_path.stem
        
        # Generate integration example
        integration_example = generate_api_integration_example(file_path)
        example_file = examples_dir / f"{agent_name}_api_integration.py"
        with open(example_file, 'w') as f:
            f.write(integration_example)
        
        # Generate contract template
        contract_template = create_api_contract_template(agent_name)
        template_file = templates_dir / f"{agent_name}_contract.py"
        with open(template_file, 'w') as f:
            f.write(contract_template)
        
        generated_count += 1
    
    # Generate API documentation
    generate_api_documentation()
    
    print(f"\n✅ WP-06 API STANDARDIZATION ANALYSIS COMPLETE!")
    print(f"🔧 API candidates: {len(standardization_candidates)} agents")
    print(f"📝 Generated examples: {generated_count} integration examples")
    print(f"📋 Generated templates: {generated_count} contract templates")
    
    print(f"\n🚀 API Standardization Benefits:")
    print(f"📈 Consistent API contracts across all agents")
    print(f"🔄 Standardized request/response formats")
    print(f"📊 Built-in validation and error handling")
    print(f"📚 Auto-generated OpenAPI documentation")
    print(f"🛡️  Rate limiting and security middleware")
    print(f"📋 Type-safe communication patterns")
    
    print(f"\n🚀 Next Steps:")
    print(f"1. API contracts are implemented in common/api/")
    print(f"2. Integration examples: docs/api_integration_examples/")
    print(f"3. Contract templates: docs/api_contract_templates/")
    print(f"4. API documentation: docs/api_docs.html")
    print(f"5. Use: from common.api.contract import get_api_processor")

if __name__ == "__main__":
    main() 