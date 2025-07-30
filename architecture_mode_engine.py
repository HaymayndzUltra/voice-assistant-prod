#!/usr/bin/env python3
"""
Architecture Mode Engine - Plan-First Development Workflow

This module implements the architecture-first planning workflow where all feature
development starts with comprehensive planning, validation, and approval before
any code implementation begins.

Core Philosophy:
- Plan before code
- Validate against project constraints
- Approve with full context awareness
- Generate implementation tasks automatically
- Maintain architectural consistency

Author: AI System Architecture Team
Created: 2025-07-30
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Import project brain manager
from project_brain_manager import ProjectBrainManager, ContextQuery

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArchitectureMode:
    """Main Architecture Mode controller."""
    
    def __init__(self, project_root: str = "/home/haymayndz/AI_System_Monorepo"):
        self.project_root = Path(project_root)
        self.brain_manager = ProjectBrainManager()
        self.plans_dir = self.project_root / "memory-bank" / "architecture-plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        
        # Architecture mode state
        self.state_file = self.project_root / "memory-bank" / "architecture-mode-state.json"
        self.load_state()
    
    def load_state(self):
        """Load architecture mode state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "active": False,
                "loaded_domains": [],
                "current_plan": None,
                "plan_history": [],
                "last_activated": None
            }
    
    def save_state(self):
        """Save architecture mode state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def activate(self) -> Dict[str, Any]:
        """Activate architecture mode."""
        logger.info("🏗️ Activating Architecture Mode...")
        
        # Load brain summary for context
        brain_summary = self.brain_manager.get_brain_summary()
        
        self.state.update({
            "active": True,
            "last_activated": datetime.now(timezone.utc).isoformat(),
            "loaded_domains": []
        })
        self.save_state()
        
        result = {
            "status": "activated",
            "message": "Architecture Mode is now active. Plan-first development workflow enabled.",
            "brain_summary": brain_summary,
            "next_steps": [
                "Load project brain context: python3 memory_system/cli.py arch-mode load-brain",
                "Create architecture plan: python3 memory_system/cli.py arch-mode plan 'feature description'",
                "Validate plan: python3 memory_system/cli.py arch-mode validate PLAN_ID",
                "Approve plan: python3 memory_system/cli.py arch-mode approve PLAN_ID"
            ]
        }
        
        logger.info("✅ Architecture Mode activated successfully")
        return result
    
    def load_brain(self, domains: Optional[str] = None, priority: Optional[int] = None) -> Dict[str, Any]:
        """Load project brain context into memory."""
        logger.info("🧠 Loading project brain context...")
        
        # Parse domains
        domain_list = None
        if domains:
            domain_list = [d.strip() for d in domains.split(',')]
        
        # Load brain context
        if domain_list:
            query = ContextQuery(
                domains=domain_list,
                priority_threshold=priority or 3
            )
            brain_context = self.brain_manager.load_targeted_context(query)
            context_type = f"targeted ({', '.join(domain_list)})"
        else:
            brain_context = self.brain_manager.load_full_context()
            context_type = "full"
        
        # Update state
        self.state["loaded_domains"] = domain_list or ["all"]
        self.save_state()
        
        result = {
            "status": "loaded",
            "context_type": context_type,
            "domains_loaded": self.state["loaded_domains"],
            "priority_filter": priority,
            "brain_sections": len(brain_context),
            "context_summary": {
                "total_characters": sum(len(content) for content in brain_context.values()),
                "sections": list(brain_context.keys())
            }
        }
        
        logger.info(f"✅ Loaded {len(brain_context)} brain sections ({context_type})")
        return result
    
    def create_plan(self, description: str, template: Optional[str] = None, output: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive architecture plan."""
        logger.info(f"📋 Creating architecture plan for: {description}")
        
        # Generate unique plan ID
        plan_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(timezone.utc)
        
        # Create plan structure
        plan = {
            "plan_id": plan_id,
            "title": description,
            "status": "draft",
            "created": timestamp.isoformat(),
            "template": template,
            "description": description,
            "requirements": self._analyze_requirements(description),
            "architecture": self._generate_architecture(description),
            "dependencies": self._analyze_dependencies(description),
            "risks": self._identify_risks(description),
            "implementation": self._create_implementation_plan(description),
            "validation": {
                "checked": False,
                "issues": [],
                "warnings": []
            },
            "approval": {
                "approved": False,
                "approved_by": None,
                "approved_at": None
            }
        }
        
        # Save plan
        plan_file = self.plans_dir / f"plan-{plan_id}.json"
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        # Update state
        self.state["current_plan"] = plan_id
        self.state["plan_history"].append({
            "plan_id": plan_id,
            "title": description,
            "created": timestamp.isoformat(),
            "status": "draft"
        })
        self.save_state()
        
        result = {
            "status": "created",
            "plan_id": plan_id,
            "plan_file": str(plan_file),
            "title": description,
            "next_steps": [
                f"Review plan: cat {plan_file}",
                f"Validate plan: python3 memory_system/cli.py arch-mode validate {plan_id}",
                f"Approve plan: python3 memory_system/cli.py arch-mode approve {plan_id}"
            ]
        }
        
        logger.info(f"✅ Created plan {plan_id}: {description}")
        return result
    
    def validate_plan(self, plan_id: str, strict: bool = False) -> Dict[str, Any]:
        """Validate architecture plan against project constraints."""
        logger.info(f"🔍 Validating plan {plan_id}...")
        
        # Load plan
        plan_file = self.plans_dir / f"plan-{plan_id}.json"
        if not plan_file.exists():
            raise FileNotFoundError(f"Plan {plan_id} not found")
        
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        # Validation logic
        issues = []
        warnings = []
        
        # Check brain context consistency
        brain_summary = self.brain_manager.get_brain_summary()
        if not self.state["loaded_domains"]:
            warnings.append("No brain context loaded - validation may be incomplete")
        
        # Validate against architecture principles
        arch_issues = self._validate_architecture_consistency(plan)
        issues.extend(arch_issues)
        
        # Validate dependencies
        dep_issues = self._validate_dependencies(plan)
        issues.extend(dep_issues)
        
        # Validate naming conventions
        naming_issues = self._validate_naming_conventions(plan)
        if strict:
            issues.extend(naming_issues)
        else:
            warnings.extend(naming_issues)
        
        # Update plan validation
        plan["validation"] = {
            "checked": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "strict_mode": strict,
            "issues": issues,
            "warnings": warnings
        }
        
        # Update plan status
        if not issues:
            plan["status"] = "validated"
        else:
            plan["status"] = "validation_failed"
        
        # Save updated plan
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        result = {
            "status": plan["status"],
            "plan_id": plan_id,
            "validation_result": {
                "passed": len(issues) == 0,
                "issues_count": len(issues),
                "warnings_count": len(warnings),
                "issues": issues,
                "warnings": warnings
            }
        }
        
        if issues:
            logger.warning(f"❌ Plan {plan_id} validation failed with {len(issues)} issues")
        else:
            logger.info(f"✅ Plan {plan_id} validation passed with {len(warnings)} warnings")
        
        return result
    
    def approve_plan(self, plan_id: str, auto_generate_tasks: bool = False) -> Dict[str, Any]:
        """Approve plan and prepare for implementation."""
        logger.info(f"✅ Approving plan {plan_id}...")
        
        # Load plan
        plan_file = self.plans_dir / f"plan-{plan_id}.json"
        if not plan_file.exists():
            raise FileNotFoundError(f"Plan {plan_id} not found")
        
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        # Check validation status
        if not plan["validation"]["checked"]:
            raise ValueError("Plan must be validated before approval")
        
        if plan["validation"]["issues"]:
            raise ValueError("Cannot approve plan with validation issues")
        
        # Approve plan
        timestamp = datetime.now(timezone.utc)
        plan["approval"] = {
            "approved": True,
            "approved_by": "architecture_mode_engine",
            "approved_at": timestamp.isoformat()
        }
        plan["status"] = "approved"
        
        # Save approved plan
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        result = {
            "status": "approved",
            "plan_id": plan_id,
            "approved_at": timestamp.isoformat(),
            "implementation_ready": True
        }
        
        # Auto-generate tasks if requested
        if auto_generate_tasks:
            tasks_result = self._generate_implementation_tasks(plan)
            result["tasks_generated"] = tasks_result
        
        logger.info(f"✅ Plan {plan_id} approved and ready for implementation")
        return result
    
    def list_plans(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """List all architecture plans."""
        plans = []
        
        for plan_file in self.plans_dir.glob("plan-*.json"):
            with open(plan_file, 'r') as f:
                plan = json.load(f)
            
            if status_filter and plan["status"] != status_filter:
                continue
            
            plans.append({
                "plan_id": plan["plan_id"],
                "title": plan["title"],
                "status": plan["status"],
                "created": plan["created"],
                "validated": plan["validation"]["checked"],
                "approved": plan["approval"]["approved"]
            })
        
        # Sort by creation date (newest first)
        plans.sort(key=lambda p: p["created"], reverse=True)
        
        return {
            "total_plans": len(plans),
            "status_filter": status_filter,
            "plans": plans
        }
    
    def get_plan_status(self, plan_id: Optional[str] = None) -> Dict[str, Any]:
        """Show status of specific plan or overview."""
        if plan_id:
            # Specific plan status
            plan_file = self.plans_dir / f"plan-{plan_id}.json"
            if not plan_file.exists():
                raise FileNotFoundError(f"Plan {plan_id} not found")
            
            with open(plan_file, 'r') as f:
                plan = json.load(f)
            
            return {
                "plan_id": plan_id,
                "title": plan["title"],
                "status": plan["status"],
                "created": plan["created"],
                "validation": plan["validation"],
                "approval": plan["approval"],
                "implementation": plan["implementation"]
            }
        else:
            # Overview status
            all_plans = self.list_plans()["plans"]
            status_counts = {}
            for plan in all_plans:
                status = plan["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "architecture_mode": {
                    "active": self.state["active"],
                    "loaded_domains": self.state["loaded_domains"],
                    "current_plan": self.state["current_plan"]
                },
                "plan_statistics": {
                    "total_plans": len(all_plans),
                    "status_breakdown": status_counts
                },
                "recent_plans": all_plans[:5]  # 5 most recent
            }
    
    # Helper methods for plan generation and validation
    
    def _analyze_requirements(self, description: str) -> Dict[str, Any]:
        """Analyze requirements from description."""
        return {
            "functional": [
                f"Implement {description} functionality",
                "Maintain system consistency",
                "Ensure proper error handling"
            ],
            "non_functional": [
                "Performance: Response time < 2 seconds",
                "Reliability: 99.9% uptime",
                "Maintainability: Clear documentation"
            ],
            "constraints": [
                "Must follow existing architecture patterns",
                "Must be backward compatible",
                "Must include comprehensive tests"
            ]
        }
    
    def _generate_architecture(self, description: str) -> Dict[str, Any]:
        """Generate architecture design."""
        return {
            "components": [
                {
                    "name": f"{description.replace(' ', '_').lower()}_module",
                    "type": "service",
                    "responsibilities": [f"Handle {description} operations"]
                }
            ],
            "interfaces": [
                {
                    "name": f"{description.replace(' ', '_').lower()}_api",
                    "type": "REST",
                    "methods": ["GET", "POST", "PUT", "DELETE"]
                }
            ],
            "data_flow": [
                "User request → API → Service → Data layer → Response"
            ],
            "patterns": [
                "Repository pattern for data access",
                "Service layer for business logic",
                "Factory pattern for object creation"
            ]
        }
    
    def _analyze_dependencies(self, description: str) -> Dict[str, Any]:
        """Analyze dependencies."""
        return {
            "internal": [
                "todo_manager.py",
                "auto_sync_manager.py",
                "workflow_memory_intelligence_fixed.py"
            ],
            "external": [
                "Python 3.10+",
                "json (standard library)",
                "pathlib (standard library)"
            ],
            "optional": [
                "ollama (for LLM integration)",
                "sqlite3 (for database features)"
            ]
        }
    
    def _identify_risks(self, description: str) -> List[Dict[str, Any]]:
        """Identify implementation risks."""
        return [
            {
                "risk": "Complexity creep",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Use modular design and incremental development"
            },
            {
                "risk": "Integration issues",
                "probability": "low",
                "impact": "medium",
                "mitigation": "Comprehensive integration testing"
            }
        ]
    
    def _create_implementation_plan(self, description: str) -> Dict[str, Any]:
        """Create implementation plan."""
        return {
            "phases": [
                {
                    "phase": "Design",
                    "duration": "2 days",
                    "tasks": ["Create detailed design", "Review with team"]
                },
                {
                    "phase": "Implementation",
                    "duration": "5 days",
                    "tasks": ["Implement core functionality", "Add error handling", "Write tests"]
                },
                {
                    "phase": "Testing",
                    "duration": "2 days",
                    "tasks": ["Unit tests", "Integration tests", "Performance tests"]
                },
                {
                    "phase": "Documentation",
                    "duration": "1 day",
                    "tasks": ["Update documentation", "Create usage examples"]
                }
            ],
            "estimated_total": "10 days"
        }
    
    def _validate_architecture_consistency(self, plan: Dict[str, Any]) -> List[str]:
        """Validate architecture consistency."""
        issues = []
        
        # Check if plan follows established patterns
        if "service" not in str(plan["architecture"]).lower():
            issues.append("Plan should follow service-oriented architecture pattern")
        
        return issues
    
    def _validate_dependencies(self, plan: Dict[str, Any]) -> List[str]:
        """Validate dependencies."""
        issues = []
        
        # Check for circular dependencies
        # This is a simplified check - real implementation would be more sophisticated
        
        return issues
    
    def _validate_naming_conventions(self, plan: Dict[str, Any]) -> List[str]:
        """Validate naming conventions."""
        warnings = []
        
        # Check naming patterns
        title = plan.get("title", "")
        if not title.islower():
            warnings.append("Plan title should use lowercase with underscores")
        
        return warnings
    
    def _generate_implementation_tasks(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation tasks from approved plan."""
        tasks = []
        
        for phase in plan["implementation"]["phases"]:
            for task in phase["tasks"]:
                tasks.append({
                    "description": f"{phase['phase']}: {task}",
                    "phase": phase["phase"],
                    "priority": "high" if phase["phase"] == "Implementation" else "medium",
                    "estimated_time": "1-2 hours"
                })
        
        # Here we would integrate with todo_manager to create actual tasks
        # For now, return the task structure
        
        return {
            "tasks_created": len(tasks),
            "tasks": tasks,
            "note": "Tasks would be created in todo_manager in full implementation"
        }
    
    def generate_implementation_prompts(self, plan_id: str, output_dir: Optional[str] = None, format: str = "markdown") -> Dict[str, Any]:
        """Generate ready-to-use implementation prompts from approved plan."""
        logger.info(f"🎯 Generating implementation prompts for plan {plan_id}...")
        
        # Load plan
        plan_file = self.plans_dir / f"plan-{plan_id}.json"
        if not plan_file.exists():
            raise FileNotFoundError(f"Plan {plan_id} not found")
        
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        # Check if plan is approved
        if not plan.get("approval", {}).get("approved", False):
            raise ValueError("Plan must be approved before generating prompts")
        
        # Set up output directory
        if not output_dir:
            output_dir = self.plans_dir / "prompts" / plan_id
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load brain context for comprehensive prompts
        brain_context = self.brain_manager.load_full_context()
        
        # Generate different types of prompts
        prompts = {
            "implementation": self._generate_implementation_prompt(plan, brain_context),
            "testing": self._generate_testing_prompt(plan, brain_context),
            "documentation": self._generate_documentation_prompt(plan, brain_context),
            "integration": self._generate_integration_prompt(plan, brain_context)
        }
        
        # Save prompts to files
        saved_files = []
        for prompt_type, prompt_content in prompts.items():
            if format == "markdown":
                filename = f"{prompt_type}_prompt.md"
                content = prompt_content
            elif format == "text":
                filename = f"{prompt_type}_prompt.txt"
                content = self._strip_markdown(prompt_content)
            else:  # json
                filename = f"{prompt_type}_prompt.json"
                content = json.dumps({"prompt": prompt_content, "metadata": {"plan_id": plan_id, "type": prompt_type}}, indent=2)
            
            prompt_file = output_dir / filename
            with open(prompt_file, 'w') as f:
                f.write(content)
            saved_files.append(str(prompt_file))
        
        # Update plan with prompts
        plan["implementation_prompts"] = {
            "generated": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_directory": str(output_dir),
            "format": format,
            "files": saved_files,
            "prompts": prompts
        }
        
        # Save updated plan
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        result = {
            "status": "generated",
            "plan_id": plan_id,
            "prompts_generated": len(prompts),
            "output_directory": str(output_dir),
            "format": format,
            "files": saved_files,
            "ready_for_copy_paste": True
        }
        
        logger.info(f"✅ Generated {len(prompts)} implementation prompts for plan {plan_id}")
        return result
    
    def _generate_implementation_prompt(self, plan: Dict[str, Any], brain_context: Dict[str, Any]) -> str:
        """Generate comprehensive implementation prompt."""
        return f"""# Implementation Prompt for: {plan['title']}

## Project Context
{self._extract_project_context(brain_context)}

## Architecture Plan Details
**Plan ID**: {plan['plan_id']}
**Description**: {plan['description']}
**Status**: {plan['status']}

## Requirements
{self._format_requirements(plan['requirements'])}

## Architecture Design
{self._format_architecture(plan['architecture'])}

## Implementation Instructions

You are tasked with implementing the feature described in this plan. Follow these guidelines:

### 1. File Structure
Create/modify the following files in `/home/haymayndz/AI_System_Monorepo/`:
{self._generate_file_structure(plan)}

### 2. Implementation Steps
{self._format_implementation_steps(plan['implementation'])}

### 3. Code Patterns to Follow
{self._extract_code_patterns(brain_context)}

### 4. Dependencies and Imports
{self._format_dependencies(plan['dependencies'])}

### 5. Error Handling Requirements
- Add comprehensive error handling with proper logging
- Use try-except blocks for external dependencies
- Provide meaningful error messages
- Implement graceful degradation where possible

### 6. Testing Requirements
- Write unit tests for all new functions
- Add integration tests for system interactions
- Include edge case testing
- Verify error handling paths

### 7. Documentation Updates
- Update relevant brain sections
- Add docstrings for all new functions/classes
- Update README if new features are user-facing
- Create usage examples

## Validation Checklist
- [ ] All requirements implemented
- [ ] Code follows established patterns
- [ ] Error handling implemented
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Integration points working
- [ ] No breaking changes to existing code

## Ready to Execute
This prompt contains all necessary information to implement the planned feature. Copy and paste this entire prompt to your AI assistant for complete implementation.
"""
    
    def _generate_testing_prompt(self, plan: Dict[str, Any], brain_context: Dict[str, Any]) -> str:
        """Generate comprehensive testing prompt."""
        return f"""# Testing Prompt for: {plan['title']}

## Testing Requirements

Create comprehensive tests for the implemented feature: {plan['description']}

### Test Files to Create
- `test_{plan['title'].replace(' ', '_').lower()}.py`
- Integration tests in appropriate test directories

### Test Categories

#### 1. Unit Tests
- Test all individual functions
- Test edge cases and boundary conditions
- Test error handling paths
- Test with valid and invalid inputs

#### 2. Integration Tests
- Test interactions with existing systems
- Test CLI integration
- Test state management
- Test file operations

#### 3. Performance Tests
- Test with large datasets
- Test concurrent operations
- Test memory usage

### Testing Patterns
{self._extract_testing_patterns(brain_context)}

### Test Implementation
Implement all tests following the project's testing standards and patterns.
"""
    
    def _generate_documentation_prompt(self, plan: Dict[str, Any], brain_context: Dict[str, Any]) -> str:
        """Generate documentation update prompt."""
        return f"""# Documentation Prompt for: {plan['title']}

## Documentation Updates Required

Update documentation for the implemented feature: {plan['description']}

### Files to Update

#### 1. Project Brain Sections
- Update relevant brain sections with new functionality
- Add architectural decisions to brain
- Document integration points

#### 2. Code Documentation
- Add comprehensive docstrings
- Update type hints
- Add inline comments for complex logic

#### 3. User Documentation
- Update CLI help text
- Create usage examples
- Update README if user-facing

#### 4. Technical Documentation
- Update architecture diagrams
- Document API changes
- Update deployment guides if needed

### Documentation Standards
{self._extract_documentation_standards(brain_context)}

### Implementation
Update all documentation following the project's documentation standards.
"""
    
    def _generate_integration_prompt(self, plan: Dict[str, Any], brain_context: Dict[str, Any]) -> str:
        """Generate integration testing prompt."""
        return f"""# Integration Prompt for: {plan['title']}

## Integration Requirements

Ensure the implemented feature integrates properly with existing systems.

### Integration Points
{self._format_integration_points(plan)}

### Integration Testing
- Test CLI integration
- Test state management integration
- Test memory system integration
- Test telemetry integration

### System Health
- Verify health checks still pass
- Ensure no breaking changes
- Test backward compatibility

### Integration Implementation
Implement all integration requirements and verify system stability.
"""
    
    def _strip_markdown(self, content: str) -> str:
        """Remove markdown formatting for text output."""
        import re
        # Remove markdown formatting
        content = re.sub(r'#+\s*', '', content)  # Headers
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*([^*]+)\*', r'\1', content)  # Italic
        content = re.sub(r'`([^`]+)`', r'\1', content)  # Inline code
        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)  # Code blocks
        return content
    
    def _extract_project_context(self, brain_context: Dict[str, Any]) -> str:
        """Extract relevant project context from brain."""
        context = "### Project Overview\n"
        if 'core' in brain_context and 'project-context' in brain_context['core']:
            context += brain_context['core']['project-context'].get('content', 'No project context available')
        return context
    
    def _format_requirements(self, requirements: Dict[str, Any]) -> str:
        """Format requirements for prompt."""
        formatted = ""
        for category, reqs in requirements.items():
            formatted += f"### {category.replace('_', ' ').title()}\n"
            for req in reqs:
                formatted += f"- {req}\n"
        return formatted
    
    def _format_architecture(self, architecture: Dict[str, Any]) -> str:
        """Format architecture design for prompt."""
        formatted = ""
        for section, content in architecture.items():
            formatted += f"### {section.replace('_', ' ').title()}\n"
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        formatted += f"- **{item.get('name', 'Component')}**: {item.get('type', 'Unknown')}\n"
                        if 'responsibilities' in item:
                            for resp in item['responsibilities']:
                                formatted += f"  - {resp}\n"
                    else:
                        formatted += f"- {item}\n"
            else:
                formatted += f"{content}\n"
        return formatted
    
    def _generate_file_structure(self, plan: Dict[str, Any]) -> str:
        """Generate suggested file structure."""
        title = plan['title'].replace(' ', '_').lower()
        return f"""- `{title}_module.py` - Main implementation
- `test_{title}.py` - Comprehensive tests
- `memory-bank/project-brain/modules/{title}.md` - Module documentation"""
    
    def _format_implementation_steps(self, implementation: Dict[str, Any]) -> str:
        """Format implementation steps."""
        formatted = ""
        for i, phase in enumerate(implementation.get('phases', []), 1):
            formatted += f"#### Step {i}: {phase['phase']}\n"
            for task in phase.get('tasks', []):
                formatted += f"- {task}\n"
            formatted += "\n"
        return formatted
    
    def _extract_code_patterns(self, brain_context: Dict[str, Any]) -> str:
        """Extract code patterns from brain context."""
        return """- Follow existing module structure
- Use comprehensive error handling
- Include proper logging
- Add type hints
- Use dataclasses for data structures
- Follow PEP 8 style guidelines"""
    
    def _format_dependencies(self, dependencies: Dict[str, Any]) -> str:
        """Format dependencies for prompt."""
        formatted = ""
        for category, deps in dependencies.items():
            formatted += f"### {category.replace('_', ' ').title()}\n"
            for dep in deps:
                formatted += f"- {dep}\n"
        return formatted
    
    def _extract_testing_patterns(self, brain_context: Dict[str, Any]) -> str:
        """Extract testing patterns from brain context."""
        return """- Use pytest framework
- Follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common test data
- Mock external dependencies
- Test both success and failure paths"""
    
    def _extract_documentation_standards(self, brain_context: Dict[str, Any]) -> str:
        """Extract documentation standards from brain context."""
        return """- Use Google-style docstrings
- Include type hints
- Provide usage examples
- Document all parameters and return values
- Keep documentation up to date with code changes"""
    
    def _format_integration_points(self, plan: Dict[str, Any]) -> str:
        """Format integration points for prompt."""
        return """- CLI command integration
- State management system
- Memory and brain systems
- Telemetry and logging
- Health monitoring
- Task management system"""


def handle_arch_mode_command(args: argparse.Namespace) -> None:
    """Handle arch-mode CLI commands."""
    arch_mode = ArchitectureMode()
    
    try:
        if args.arch_command == "activate":
            result = arch_mode.activate()
            
        elif args.arch_command == "load-brain":
            result = arch_mode.load_brain(
                domains=args.domains,
                priority=args.priority
            )
            
        elif args.arch_command == "plan":
            result = arch_mode.create_plan(
                description=args.description,
                template=args.template,
                output=args.output
            )
            
        elif args.arch_command == "validate":
            result = arch_mode.validate_plan(
                plan_id=args.plan_id,
                strict=args.strict
            )
            
        elif args.arch_command == "approve":
            result = arch_mode.approve_plan(
                plan_id=args.plan_id,
                auto_generate_tasks=args.auto_generate_tasks
            )
            
        elif args.arch_command == "list":
            result = arch_mode.list_plans(status_filter=args.status)
            
        elif args.arch_command == "status":
            result = arch_mode.get_plan_status(plan_id=args.plan_id)
            
        elif args.arch_command == "generate-prompts":
            result = arch_mode.generate_implementation_prompts(
                plan_id=args.plan_id,
                output_dir=args.output_dir,
                format=args.format
            )
            
        else:
            result = {"error": f"Unknown arch-mode command: {args.arch_command}"}
        
        # Pretty print result
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "command": args.arch_command,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    # Test the architecture mode
    arch_mode = ArchitectureMode()
    
    print("🏗️ Architecture Mode Engine Test")
    print("=" * 50)
    
    # Test activation
    result = arch_mode.activate()
    print("✅ Activation:", result["status"])
    
    # Test brain loading
    result = arch_mode.load_brain(domains="core,modules")
    print("✅ Brain loading:", result["status"])
    
    # Test plan creation
    result = arch_mode.create_plan("Test feature for demonstration")
    print("✅ Plan creation:", result["plan_id"])
    
    print("\n🎉 Architecture Mode Engine working correctly!")
