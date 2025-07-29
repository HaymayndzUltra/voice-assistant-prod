#!/usr/bin/env python3
"""
Improved Task Chunker
Handles very long task descriptions and breaks them into logical, manageable chunks
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

class ImprovedTaskChunker:
    """Improved task chunking system for long task descriptions"""
    
    def __init__(self):
        self.max_chunk_length = 200  # Maximum characters per chunk
        self.min_chunk_length = 50   # Minimum characters per chunk
        self.priority_keywords = [
            'PHASE', 'OBJECTIVE', 'CONSTRAINTS', 'MEMORY', 'REPORTING',
            'SYSTEM_CONTEXT', 'SUCCESS_CRITERIA', 'AWAITING_GO_SIGNAL'
        ]
    
    def chunk_long_task(self, task_description: str) -> List[str]:
        """Chunk a very long task description into manageable pieces"""
        
        print(f"🔧 Chunking task: {len(task_description)} characters")
        
        # Step 1: Try to split by priority keywords first
        chunks = self._split_by_priority_keywords(task_description)
        
        # Step 2: If still too long, split by sentences
        if len(chunks) <= 1 or any(len(chunk) > self.max_chunk_length for chunk in chunks):
            chunks = self._split_by_sentences(task_description)
        
        # Step 3: If still too long, split by phrases
        if len(chunks) <= 1 or any(len(chunk) > self.max_chunk_length for chunk in chunks):
            chunks = self._split_by_phrases(task_description)
        
        # Step 4: Clean and validate chunks
        chunks = self._clean_chunks(chunks)
        
        print(f"✅ Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}: {len(chunk)} chars - {chunk[:50]}...")
        
        return chunks
    
    def _split_by_priority_keywords(self, text: str) -> List[str]:
        """Split by priority keywords to maintain logical structure"""
        chunks = []
        current_chunk = ""
        
        # Split by priority keywords
        parts = re.split(r'(\b(?:PHASE|OBJECTIVE|CONSTRAINTS|MEMORY|REPORTING|SYSTEM_CONTEXT|SUCCESS_CRITERIA|AWAITING_GO_SIGNAL)\b)', text, flags=re.IGNORECASE)
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                current_chunk += part
            else:  # Keyword
                if current_chunk and len(current_chunk) > self.min_chunk_length:
                    chunks.append(current_chunk.strip())
                    current_chunk = part
                else:
                    current_chunk += part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split by sentences while respecting natural breaks"""
        # Split by sentence endings
        sentences = re.split(r'([.!?]+)\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # Add punctuation back
            
            if len(current_chunk + sentence) <= self.max_chunk_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def _split_by_phrases(self, text: str) -> List[str]:
        """Split by phrases when sentences are too long"""
        # Split by common phrase separators
        phrases = re.split(r'([,;:]\s+)', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(phrases), 2):
            phrase = phrases[i]
            if i + 1 < len(phrases):
                phrase += phrases[i + 1]  # Add separator back
            
            if len(current_chunk + phrase) <= self.max_chunk_length:
                current_chunk += phrase
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = phrase
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
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
    
    def create_improved_task(self, long_description: str) -> Dict[str, Any]:
        """Create an improved task with better chunking"""
        
        # Generate task ID with Philippines time
        ph_time = get_philippines_time()
        timestamp = ph_time.strftime('%Y%m%dT%H%M%S')
        
        # Create a shorter, more descriptive task ID
        short_desc = self._create_short_description(long_description)
        desc_part = short_desc.replace(' ', '_')[:30]
        task_id = f"{timestamp}_{desc_part}"
        
        # Chunk the long description
        chunks = self.chunk_long_task(long_description)
        
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
            "chunking_method": "improved"
        }
        
        return task
    
    def _create_short_description(self, long_description: str) -> str:
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

def fix_current_long_task():
    """Fix the current very long task by re-chunking it"""
    
    print("🔧 Fixing Current Long Task")
    print("=" * 40)
    
    try:
        # Read current todo-tasks.json
        with open('todo-tasks.json', 'r') as f:
            data = json.load(f)
        
        # Find the very long task
        long_task = None
        for task in data['tasks']:
            if len(task['description']) > 500:  # Very long task
                long_task = task
                break
        
        if not long_task:
            print("❌ No very long task found")
            return False
        
        print(f"📋 Found long task: {long_task['id']}")
        print(f"   Length: {len(long_task['description'])} characters")
        print(f"   Current chunks: {len(long_task['todos'])}")
        
        # Create improved chunker
        chunker = ImprovedTaskChunker()
        
        # Create improved task
        improved_task = chunker.create_improved_task(long_task['description'])
        
        print(f"\n✅ Improved task created:")
        print(f"   New ID: {improved_task['id']}")
        print(f"   Short description: {improved_task['description']}")
        print(f"   New chunks: {len(improved_task['todos'])}")
        
        # Replace the old task with the improved one
        for i, task in enumerate(data['tasks']):
            if task['id'] == long_task['id']:
                data['tasks'][i] = improved_task
                break
        
        # Save back to file
        with open('todo-tasks.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n🎯 Long task successfully fixed!")
        print(f"   Old task ID: {long_task['id']}")
        print(f"   New task ID: {improved_task['id']}")
        print(f"   Chunks improved: {len(long_task['todos'])} → {len(improved_task['todos'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing long task: {e}")
        return False

def test_chunking():
    """Test the improved chunking system"""
    
    print("🧪 Testing Improved Task Chunking")
    print("=" * 40)
    
    # Test with a very long description
    long_description = """alwaysApply: truedescription: |  SYSTEM_CONTEXT:    - Multi-agent, multi-container AI system (70+ Python agents)    - Two subsystems:        - MainPC: RTX 4090, Ubuntu, agents in main_pc_code/agents/, main_pc_code/FORMAINPC/        - PC2: RTX 3060, low CPU Ubuntu, agents in pc2_code/agents/    - Agents and dependencies defined in:        - main_pc_code/config/startup_config.yaml (MainPC)        - pc2_code/config/startup_config.yaml (PC2)    - Shared libraries: common/, common_utils/, etc.  OBJECTIVE:    - Perform a complete, clean, and dependency-correct Docker/PODMAN refactor for the entire system.    - Delete all existing Docker/Podman containers, images, and compose files.    - Generate a new Source of Truth (SoT) docker-compose setup, with logical agent grouping, correct dependency order, and optimized requirements per container.    - Ensure that each container only installs/downloads what is strictly necessary for its agents.    - Proactively analyze and resolve all dependency, timing, and startup order issues.  CONSTRAINTS:    - No redundant downloads or oversized images.    - All agent dependencies must be satisfied per container, but nothing extra.    - Startup order must respect agent interdependencies (e.g., core services before dependents).    - Group agents in containers by logical function and dependency, not just by subsystem.    - Maintain clear separation between MainPC and PC2, but allow for shared service containers if optimal.  PHASES:    - Phase 1: System Analysis & Cleanup        - Inventory all existing Docker/Podman containers, images, and compose files.        - Delete all old containers/images/compose files.        - Identify all agent groups, dependencies, and required libraries.    - Phase 2: Logical Grouping & Compose Generation        - Design optimal container groupings (by function, dependency, resource needs).        - Generate new docker-compose SoT with correct build contexts, volumes, networks, and healthchecks.        - Ensure requirements.txt per container is minimal and correct.    - Phase 3: Validation & Optimization        - Build and start all containers in dependency-correct order.        - Validate agent startup, health, and inter-container communication.        - Optimize for image size, startup time, and resource usage.        - Document the new architecture and compose setup.  MEMORY & REPORTING:    - Persist all actions, decisions, and SoT changes to MCP memory and memory-bank/*.md.    - Log all deletions, groupings, and compose generation steps.    - Escalate to user if ambiguous dependency or grouping is detected.success_criteria:  - All legacy Docker/Podman artifacts deleted.  - New SoT docker-compose file(s) generated and validated.  - All agents run with only their required dependencies.  - Startup order and healthchecks are correct.  - Full logs and memory updates available for audit.awaiting_go_signal: true"""
    
    chunker = ImprovedTaskChunker()
    
    print(f"\n1️⃣ Testing chunking with {len(long_description)} characters...")
    chunks = chunker.chunk_long_task(long_description)
    
    print(f"\n2️⃣ Chunking results:")
    for i, chunk in enumerate(chunks):
        print(f"   Chunk {i+1} ({len(chunk)} chars): {chunk[:80]}...")
    
    print(f"\n3️⃣ Creating improved task...")
    improved_task = chunker.create_improved_task(long_description)
    
    print(f"   Task ID: {improved_task['id']}")
    print(f"   Description: {improved_task['description']}")
    print(f"   Total chunks: {improved_task['total_chunks']}")
    
    return True

if __name__ == "__main__":
    print("🔧 Improved Task Chunker")
    print("=" * 40)
    
    # Test chunking
    test_chunking()
    
    print("\n" + "=" * 40)
    
    # Fix current long task
    fix_current_long_task() 