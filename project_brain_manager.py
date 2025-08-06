#!/usr/bin/env python3
"""
Project Brain Manager
Manages the central knowledge map and context for the entire project
"""

import json
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from dataclasses import dataclass, asdict
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

@dataclass
class BrainSection:
    """Represents a section of the project brain"""
    name: str
    path: str
    content: Dict[str, Any]
    last_updated: str
    priority: int = 1  # 1=critical, 2=important, 3=optional

@dataclass
class ContextQuery:
    """Query for loading specific brain context"""
    domains: List[str]  # e.g., ['task_management', 'cli_system']
    priority_threshold: int = 2  # Only load sections with priority <= this
    include_patterns: List[str] = None  # Patterns to include
    exclude_patterns: List[str] = None  # Patterns to exclude

class ProjectBrainManager:
    """Manages the project's central knowledge map"""
    
    def __init__(self):
        self.brain_root = Path("memory-bank/project-brain")
        self.context_cache = {}
        self.brain_index = {}
        self.last_full_load = None
        self._ensure_brain_structure()
        
    def _ensure_brain_structure(self):
        """Create brain directory structure if it doesn't exist"""
        brain_dirs = [
            "core",
            "modules", 
            "workflows",
            "progress",
            "meta"
        ]
        
        for dir_name in brain_dirs:
            dir_path = self.brain_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create brain index if it doesn't exist
        index_path = self.brain_root / "meta" / "brain-index.json"
        if not index_path.exists():
            self._create_initial_brain_index()
    
    def _create_initial_brain_index(self):
        """Create initial brain index structure"""
        initial_index = {
            "created": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "sections": {
                "core": {
                    "project-context": {"priority": 1, "description": "Overall project scope and goals"},
                    "architecture-overview": {"priority": 1, "description": "High-level system design"},
                    "technology-stack": {"priority": 2, "description": "Tech choices and rationale"},
                    "naming-conventions": {"priority": 2, "description": "Coding standards"}
                },
                "modules": {
                    "cli-system": {"priority": 1, "description": "CLI memory system knowledge"},
                    "task-management": {"priority": 1, "description": "Task workflow intelligence"},
                    "integration-points": {"priority": 2, "description": "Module connections"}
                },
                "workflows": {
                    "development-flow": {"priority": 2, "description": "Feature development process"},
                    "testing-strategy": {"priority": 2, "description": "QA approach"},
                    "deployment-process": {"priority": 3, "description": "Release procedures"}
                },
                "progress": {
                    "milestone-tracker": {"priority": 1, "description": "Major achievements"},
                    "pain-points": {"priority": 1, "description": "Known issues"},
                    "roadmap": {"priority": 2, "description": "Future plans"}
                }
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        index_path = self.brain_root / "meta" / "brain-index.json"
        with open(index_path, 'w') as f:
            json.dump(initial_index, f, indent=2)
        
        logger.info("✅ Created initial brain index")
        return initial_index
    
    def load_brain_index(self) -> Dict[str, Any]:
        """Load the brain index"""
        index_path = self.brain_root / "meta" / "brain-index.json"
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load brain index: {e}")
            return self._create_initial_brain_index()
    
    def load_full_context(self) -> Dict[str, Any]:
        """Load all brain files into memory"""
        logger.info("🧠 Loading full project brain context...")
        
        full_context = {
            "metadata": {
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "sections_loaded": 0,
                "total_size_kb": 0
            },
            "core": {},
            "modules": {},
            "workflows": {},
            "progress": {}
        }
        
        brain_index = self.load_brain_index()
        sections_loaded = 0
        
        for category, sections in brain_index.get("sections", {}).items():
            category_path = self.brain_root / category
            if not category_path.exists():
                continue
                
            full_context[category] = {}
            
            for section_name, section_info in sections.items():
                # Try multiple file extensions
                section_file = None
                for ext in ['.md', '.yaml', '.yml', '.json']:
                    potential_file = category_path / f"{section_name}{ext}"
                    if potential_file.exists():
                        section_file = potential_file
                        break
                
                if section_file:
                    try:
                        content = self._load_section_file(section_file)
                        full_context[category][section_name] = {
                            "content": content,
                            "metadata": section_info,
                            "file_path": str(section_file),
                            "last_modified": datetime.fromtimestamp(section_file.stat().st_mtime).isoformat()
                        }
                        sections_loaded += 1
                    except Exception as e:
                        logger.warning(f"Failed to load {section_file}: {e}")
        
        full_context["metadata"]["sections_loaded"] = sections_loaded
        self.context_cache = full_context
        self.last_full_load = datetime.now(timezone.utc)
        
        logger.info(f"✅ Loaded {sections_loaded} brain sections")
        return full_context
    
    def load_targeted_context(self, query: ContextQuery) -> Dict[str, Any]:
        """Load only relevant brain sections based on query"""
        logger.info(f"🎯 Loading targeted context for domains: {query.domains}")
        
        brain_index = self.load_brain_index()
        targeted_context = {
            "metadata": {
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "query": asdict(query),
                "sections_loaded": 0
            }
        }
        
        sections_loaded = 0
        
        for category, sections in brain_index.get("sections", {}).items():
            # Skip categories not in query domains (if specified)
            if query.domains and category not in query.domains:
                continue
                
            category_path = self.brain_root / category
            if not category_path.exists():
                continue
                
            targeted_context[category] = {}
            
            for section_name, section_info in sections.items():
                # Check priority threshold
                if section_info.get("priority", 1) > query.priority_threshold:
                    continue
                
                # Check include/exclude patterns
                if query.include_patterns:
                    if not any(pattern in section_name for pattern in query.include_patterns):
                        continue
                
                if query.exclude_patterns:
                    if any(pattern in section_name for pattern in query.exclude_patterns):
                        continue
                
                # Load the section
                section_file = None
                for ext in ['.md', '.yaml', '.yml', '.json']:
                    potential_file = category_path / f"{section_name}{ext}"
                    if potential_file.exists():
                        section_file = potential_file
                        break
                
                if section_file:
                    try:
                        content = self._load_section_file(section_file)
                        targeted_context[category][section_name] = {
                            "content": content,
                            "metadata": section_info,
                            "file_path": str(section_file)
                        }
                        sections_loaded += 1
                    except Exception as e:
                        logger.warning(f"Failed to load {section_file}: {e}")
        
        targeted_context["metadata"]["sections_loaded"] = sections_loaded
        logger.info(f"✅ Loaded {sections_loaded} targeted brain sections")
        return targeted_context
    
    def _load_section_file(self, file_path: Path) -> Any:
        """Load content from a brain section file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                return json.load(f)
            else:  # .md or other text files
                return f.read()
    
    def update_brain_section(self, category: str, section: str, content: Any):
        """Update specific brain section"""
        logger.info(f"📝 Updating brain section: {category}/{section}")
        
        section_path = self.brain_root / category / f"{section}.md"
        section_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine content format and save appropriately
        if isinstance(content, dict):
            # Save as YAML for structured data
            section_path = section_path.with_suffix('.yaml')
            with open(section_path, 'w') as f:
                yaml.dump(content, f, default_flow_style=False)
        else:
            # Save as markdown for text content
            with open(section_path, 'w') as f:
                f.write(str(content))
        
        # Update brain index
        self._update_brain_index(category, section)
        
        # Clear cache to force reload
        self.context_cache = {}
        
        logger.info(f"✅ Updated brain section: {section_path}")
    
    def _update_brain_index(self, category: str, section: str):
        """Update the brain index with new/modified section"""
        brain_index = self.load_brain_index()
        
        if category not in brain_index.get("sections", {}):
            brain_index.setdefault("sections", {})[category] = {}
        
        brain_index["sections"][category][section] = {
            "priority": 2,  # Default priority
            "description": f"Updated section: {section}",
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        brain_index["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Save updated index
        index_path = self.brain_root / "meta" / "brain-index.json"
        with open(index_path, 'w') as f:
            json.dump(brain_index, f, indent=2)
    
    def search_brain(self, query: str) -> List[Dict[str, Any]]:
        """Search for content in the brain"""
        logger.info(f"🔍 Searching brain for: {query}")
        
        results = []
        query_lower = query.lower()
        
        # Ensure we have context loaded
        if not self.context_cache:
            self.load_full_context()
        
        for category, sections in self.context_cache.items():
            if category == "metadata":
                continue
                
            for section_name, section_data in sections.items():
                content = section_data.get("content", "")
                
                # Search in content
                if query_lower in str(content).lower():
                    results.append({
                        "category": category,
                        "section": section_name,
                        "file_path": section_data.get("file_path"),
                        "relevance_score": str(content).lower().count(query_lower),
                        "metadata": section_data.get("metadata", {})
                    })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        logger.info(f"✅ Found {len(results)} relevant brain sections")
        return results
    
    def validate_brain_consistency(self) -> List[str]:
        """Check for conflicts or inconsistencies in brain content"""
        logger.info("🔍 Validating brain consistency...")
        
        issues = []
        brain_index = self.load_brain_index()
        
        # Check if all indexed sections exist
        for category, sections in brain_index.get("sections", {}).items():
            category_path = self.brain_root / category
            
            for section_name, section_info in sections.items():
                section_found = False
                for ext in ['.md', '.yaml', '.yml', '.json']:
                    potential_file = category_path / f"{section_name}{ext}"
                    if potential_file.exists():
                        section_found = True
                        break
                
                if not section_found:
                    issues.append(f"Missing section file: {category}/{section_name}")
        
        # Check for orphaned files (files not in index)
        for category_path in self.brain_root.iterdir():
            if category_path.is_dir() and category_path.name != "meta":
                category_name = category_path.name
                category_sections = brain_index.get("sections", {}).get(category_name, {})
                
                for file_path in category_path.iterdir():
                    if file_path.is_file():
                        section_name = file_path.stem
                        if section_name not in category_sections:
                            issues.append(f"Orphaned file not in index: {category_name}/{file_path.name}")
        
        if issues:
            logger.warning(f"⚠️ Found {len(issues)} brain consistency issues")
        else:
            logger.info("✅ Brain consistency validation passed")
        
        return issues
    
    def get_brain_summary(self) -> Dict[str, Any]:
        """Get a summary of the current brain state"""
        brain_index = self.load_brain_index()
        
        summary = {
            "created": brain_index.get("created"),
            "last_updated": brain_index.get("last_updated"),
            "version": brain_index.get("version"),
            "statistics": {
                "total_categories": len(brain_index.get("sections", {})),
                "total_sections": sum(len(sections) for sections in brain_index.get("sections", {}).values()),
                "priority_breakdown": {}
            },
            "categories": {}
        }
        
        # Calculate statistics
        for category, sections in brain_index.get("sections", {}).items():
            summary["categories"][category] = {
                "section_count": len(sections),
                "sections": list(sections.keys())
            }
            
            for section_info in sections.values():
                priority = section_info.get("priority", 1)
                summary["statistics"]["priority_breakdown"][f"priority_{priority}"] = \
                    summary["statistics"]["priority_breakdown"].get(f"priority_{priority}", 0) + 1
        
        return summary

def main():
    """Test the project brain manager"""
    print("🧠 Project Brain Manager Test")
    print("=" * 40)
    
    brain = ProjectBrainManager()
    
    # Test loading brain index
    print("\n📚 Brain Index:")
    index = brain.load_brain_index()
    print(json.dumps(index, indent=2))
    
    # Test brain summary
    print("\n📊 Brain Summary:")
    summary = brain.get_brain_summary()
    print(json.dumps(summary, indent=2))
    
    # Test validation
    print("\n🔍 Brain Validation:")
    issues = brain.validate_brain_consistency()
    if issues:
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        print("  ✅ No issues found")

if __name__ == "__main__":
    main()
