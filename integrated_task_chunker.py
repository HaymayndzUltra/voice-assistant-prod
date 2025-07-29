#!/usr/bin/env python3
"""
Integrated Task Chunker
Combines command_chunker.py logic with improved task chunking for better long task handling
"""

import re
import json
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

def get_philippines_time() -> datetime:
    """Get current Philippines time (UTC+8)"""
    utc_now = datetime.now(timezone.utc)
    philippines_tz = timezone(timedelta(hours=8))
    return utc_now.astimezone(philippines_tz)

def format_philippines_time_iso(dt: datetime) -> str:
    """Format datetime to Philippines time in ISO format"""
    philippines_tz = timezone(timedelta(hours=8))
    ph_time = dt.astimezone(philippines_tz)
    return ph_time.isoformat()

class IntegratedTaskChunker:
    """Integrated task chunker combining command and task chunking logic"""
    
    def __init__(self, max_chunk_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_length = 50
        self.priority_keywords = [
            'PHASE', 'OBJECTIVE', 'CONSTRAINTS', 'MEMORY', 'REPORTING',
            'SYSTEM_CONTEXT', 'SUCCESS_CRITERIA', 'AWAITING_GO_SIGNAL'
        ]
        self.command_separators = [
            ' && ', ' || ', ' ; ', ' | ', ' > ', ' >> ', ' < '
        ]
    
    def analyze_task_size(self, task_description: str) -> Dict[str, Any]:
        """Analyze task size and recommend chunking strategy"""
        length = len(task_description)
        
        analysis = {
            "length": length,
            "size_category": "",
            "recommended_strategy": "",
            "estimated_chunks": 0
        }
        
        if length <= self.max_chunk_size:
            analysis["size_category"] = "SMALL"
            analysis["recommended_strategy"] = "no_chunking"
            analysis["estimated_chunks"] = 1
        elif length <= self.max_chunk_size * 2:
            analysis["size_category"] = "MEDIUM"
            analysis["recommended_strategy"] = "priority_keywords"
            analysis["estimated_chunks"] = 2
        elif length <= self.max_chunk_size * 3:
            analysis["size_category"] = "LARGE"
            analysis["recommended_strategy"] = "mixed_strategy"
            analysis["estimated_chunks"] = 3
        else:
            analysis["size_category"] = "VERY_LARGE"
            analysis["recommended_strategy"] = "command_style"
            analysis["estimated_chunks"] = 4
        
        return analysis
    
    def chunk_by_priority_keywords(self, text: str) -> List[str]:
        """Chunk by priority keywords (from improved_task_chunker.py)"""
        chunks = []
        current_chunk = ""
        
        # Split by priority keywords
        parts = re.split(r'(\b(?:PHASE|OBJECTIVE|CONSTRAINTS|MEMORY|REPORTING|SYSTEM_CONTEXT|SUCCESS_CRITERIA|AWAITING_GO_SIGNAL)\b)', text, flags=re.IGNORECASE)
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                current_chunk += part
            else:  # Keyword
                if current_chunk and len(current_chunk.strip()) > self.min_chunk_length:
                    chunks.append(current_chunk.strip())
                    current_chunk = part
                else:
                    current_chunk += part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def chunk_by_command_style(self, text: str) -> List[str]:
        """Chunk using command_chunker.py logic"""
        chunks = []
        current_chunk = ""
        
        # Split by command separators
        parts = [text]
        for sep in self.command_separators:
            new_parts = []
            for part in parts:
                if sep in part:
                    split_parts = part.split(sep)
                    for i, sp in enumerate(split_parts):
                        if i > 0:
                            new_parts.append(sep)
                        new_parts.append(sp)
                else:
                    new_parts.append(part)
            parts = new_parts
        
        # Group parts into chunks
        for part in parts:
            if len(current_chunk + part) <= self.max_chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def chunk_by_sentences(self, text: str) -> List[str]:
        """Chunk by sentences (from improved_task_chunker.py)"""
        sentences = re.split(r'([.!?]+)\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk + sentence) <= self.max_chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def chunk_by_arguments(self, text: str) -> List[str]:
        """Chunk by arguments (from command_chunker.py)"""
        parts = re.split(r'(\s+--?\w+)', text)
        
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if len(current_chunk + part) <= self.max_chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def smart_chunk_task(self, task_description: str) -> List[str]:
        """Smart chunking with multiple strategies"""
        
        print(f"🔧 Smart chunking task: {len(task_description)} characters")
        
        # Analyze task size
        analysis = self.analyze_task_size(task_description)
        print(f"   Size: {analysis['size_category']}")
        print(f"   Strategy: {analysis['recommended_strategy']}")
        
        # Apply appropriate strategy
        if analysis["recommended_strategy"] == "no_chunking":
            return [task_description]
        
        elif analysis["recommended_strategy"] == "priority_keywords":
            chunks = self.chunk_by_priority_keywords(task_description)
            if len(chunks) <= 3 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
        
        elif analysis["recommended_strategy"] == "mixed_strategy":
            # Try priority keywords first
            chunks = self.chunk_by_priority_keywords(task_description)
            if len(chunks) <= 4 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
            
            # Try command style
            chunks = self.chunk_by_command_style(task_description)
            if len(chunks) <= 4 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
        
        elif analysis["recommended_strategy"] == "command_style":
            # Try command style first
            chunks = self.chunk_by_command_style(task_description)
            if len(chunks) <= 5 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
            
            # Fallback to arguments
            chunks = self.chunk_by_arguments(task_description)
            if len(chunks) <= 5 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
        
        # Fallback to sentences
        chunks = self.chunk_by_sentences(task_description)
        
        # Clean and validate chunks
        chunks = self._clean_chunks(chunks)
        
        print(f"✅ Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}: {len(chunk)} chars - {chunk[:50]}...")
        
        return chunks
    
    def _clean_chunks(self, chunks: List[str]) -> List[str]:
        """Clean and validate chunks"""
        cleaned_chunks = []
        
        for chunk in chunks:
            # Remove excessive whitespace
            cleaned = re.sub(r'\s+', ' ', chunk.strip())
            
            # Skip empty or very short chunks
            if len(cleaned) >= self.min_chunk_length:
                cleaned_chunks.append(cleaned)
            elif cleaned_chunks:
                # Merge very short chunks with previous chunk
                cleaned_chunks[-1] += " " + cleaned
        
        return cleaned_chunks if cleaned_chunks else ["Task description"]
    
    def create_short_description(self, long_description: str) -> str:
        """Create a short, descriptive task name"""
        
        # Try to extract the main objective
        objective_match = re.search(r'OBJECTIVE:\s*(.*?)(?=\s+CONSTRAINTS|\s+PHASES|\s+MEMORY|$)', long_description, re.IGNORECASE | re.DOTALL)
        if objective_match:
            objective = objective_match.group(1).strip()
            # Take first sentence or first 100 characters
            short_obj = re.split(r'[.!?]', objective)[0][:100].strip()
            return f"Task: {short_obj}"
        
        # Try to extract from SYSTEM_CONTEXT
        context_match = re.search(r'SYSTEM_CONTEXT:\s*(.*?)(?=\s+OBJECTIVE|\s+CONSTRAINTS|$)', long_description, re.IGNORECASE | re.DOTALL)
        if context_match:
            context = context_match.group(1).strip()
            # Take first meaningful line
            lines = [line.strip() for line in context.split('\n') if line.strip()]
            if lines:
                return f"System: {lines[0][:80]}"
        
        # Fallback: take first 100 characters
        return long_description[:100].strip() + "..."
    
    def create_improved_task(self, long_description: str) -> Dict[str, Any]:
        """Create an improved task with integrated chunking"""
        
        # Generate task ID with Philippines time
        ph_time = get_philippines_time()
        timestamp = ph_time.strftime('%Y%m%dT%H%M%S')
        
        # Create a shorter, more descriptive task ID
        short_desc = self.create_short_description(long_description)
        desc_part = short_desc.replace(' ', '_')[:30]
        task_id = f"{timestamp}_{desc_part}"
        
        # Smart chunk the long description
        chunks = self.smart_chunk_task(long_description)
        
        # Create task structure
        task = {
            "id": task_id,
            "description": short_desc,
            "full_description": long_description,  # Keep full description for reference
            "todos": [
                {
                    "text": chunk,
                    "done": False,
                    "chunk_index": i
                }
                for i, chunk in enumerate(chunks)
            ],
            "status": "in_progress",
            "created": format_philippines_time_iso(ph_time),
            "updated": format_philippines_time_iso(ph_time),
            "total_chunks": len(chunks),
            "chunking_method": "integrated"
        }
        
        return task

def test_integrated_chunking():
    """Test the integrated chunking system"""
    
    print("🧪 Testing Integrated Task Chunker")
    print("=" * 50)
    
    # Test with a very long description
    long_description = """alwaysApply: truedescription: |  SYSTEM_CONTEXT:    - Multi-agent, multi-container AI system (70+ Python agents)    - Two subsystems:        - MainPC: RTX 4090, Ubuntu, agents in main_pc_code/agents/, main_pc_code/FORMAINPC/        - PC2: RTX 3060, low CPU Ubuntu, agents in pc2_code/agents/    - Agents and dependencies defined in:        - main_pc_code/config/startup_config.yaml (MainPC)        - pc2_code/config/startup_config.yaml (PC2)    - Shared libraries: common/, common_utils/, etc.  OBJECTIVE:    - Perform a complete, clean, and dependency-correct Docker/PODMAN refactor for the entire system.    - Delete all existing Docker/Podman containers, images, and compose files.    - Generate a new Source of Truth (SoT) docker-compose setup, with logical agent grouping, correct dependency order, and optimized requirements per container.    - Ensure that each container only installs/downloads what is strictly necessary for its agents.    - Proactively analyze and resolve all dependency, timing, and startup order issues.  CONSTRAINTS:    - No redundant downloads or oversized images.    - All agent dependencies must be satisfied per container, but nothing extra.    - Startup order must respect agent interdependencies (e.g., core services before dependents).    - Group agents in containers by logical function and dependency, not just by subsystem.    - Maintain clear separation between MainPC and PC2, but allow for shared service containers if optimal.  PHASES:    - Phase 1: System Analysis & Cleanup        - Inventory all existing Docker/Podman containers, images, and compose files.        - Delete all old containers/images/compose files.        - Identify all agent groups, dependencies, and required libraries.    - Phase 2: Logical Grouping & Compose Generation        - Design optimal container groupings (by function, dependency, resource needs).        - Generate new docker-compose SoT with correct build contexts, volumes, networks, and healthchecks.        - Ensure requirements.txt per container is minimal and correct.    - Phase 3: Validation & Optimization        - Build and start all containers in dependency-correct order.        - Validate agent startup, health, and inter-container communication.        - Optimize for image size, startup time, and resource usage.        - Document the new architecture and compose setup.  MEMORY & REPORTING:    - Persist all actions, decisions, and SoT changes to MCP memory and memory-bank/*.md.    - Log all deletions, groupings, and compose generation steps.    - Escalate to user if ambiguous dependency or grouping is detected.success_criteria:  - All legacy Docker/Podman artifacts deleted.  - New SoT docker-compose file(s) generated and validated.  - All agents run with only their required dependencies.  - Startup order and healthchecks are correct.  - Full logs and memory updates available for audit.awaiting_go_signal: true"""
    
    chunker = IntegratedTaskChunker()
    
    print(f"\n1️⃣ Testing integrated chunking with {len(long_description)} characters...")
    chunks = chunker.smart_chunk_task(long_description)
    
    print(f"\n2️⃣ Chunking results:")
    for i, chunk in enumerate(chunks):
        print(f"   Chunk {i+1} ({len(chunk)} chars): {chunk[:80]}...")
    
    print(f"\n3️⃣ Creating improved task...")
    improved_task = chunker.create_improved_task(long_description)
    
    print(f"   Task ID: {improved_task['id']}")
    print(f"   Description: {improved_task['description']}")
    print(f"   Total chunks: {improved_task['total_chunks']}")
    print(f"   Chunking method: {improved_task['chunking_method']}")
    
    return True

def integrate_with_todo_manager():
    """Integrate the chunker with todo_manager"""
    
    print("🔗 Integrating with Todo Manager")
    print("=" * 40)
    
    try:
        # Import todo_manager functions
        from todo_manager import new_task, add_todo, list_open_tasks
        
        # Create a test task using integrated chunker
        chunker = IntegratedTaskChunker()
        
        test_description = """SYSTEM_CONTEXT: Multi-agent AI system with 70+ Python agents across MainPC (RTX 4090) and PC2 (RTX 3060). OBJECTIVE: Perform complete Docker/PODMAN refactor with logical agent grouping and optimized dependencies. CONSTRAINTS: No redundant downloads, minimal container requirements, proper startup order. PHASES: Phase 1 - System Analysis & Cleanup, Phase 2 - Logical Grouping & Compose Generation, Phase 3 - Validation & Optimization. MEMORY & REPORTING: Persist all changes to MCP memory and memory-bank/*.md. SUCCESS_CRITERIA: All legacy artifacts deleted, new SoT docker-compose validated, agents run with minimal dependencies."""
        
        print(f"📋 Creating test task with integrated chunking...")
        improved_task = chunker.create_improved_task(test_description)
        
        print(f"✅ Integrated task created:")
        print(f"   ID: {improved_task['id']}")
        print(f"   Description: {improved_task['description']}")
        print(f"   Chunks: {len(improved_task['todos'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Integrated Task Chunker")
    print("=" * 50)
    
    # Test integrated chunking
    test_integrated_chunking()
    
    print("\n" + "=" * 50)
    
    # Test integration with todo_manager
    integrate_with_todo_manager() 