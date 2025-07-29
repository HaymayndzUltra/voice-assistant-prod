#!/usr/bin/env python3
"""
Fix Long Task
Fixes the current very long task by re-chunking it properly
"""

import json
import re
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

def create_short_description(long_description: str) -> str:
    """Create a short, descriptive task name"""
    
    # Try to extract the main objective
    objective_match = re.search(r'OBJECTIVE:\s*(.*?)(?=\s+CONSTRAINTS|\s+PHASES|\s+MEMORY|$)', long_description, re.IGNORECASE | re.DOTALL)
    if objective_match:
        objective = objective_match.group(1).strip()
        # Take first sentence or first 100 characters
        short_obj = re.split(r'[.!?]', objective)[0][:100].strip()
        return f"Docker/PODMAN Refactor: {short_obj}"
    
    # Try to extract from SYSTEM_CONTEXT
    context_match = re.search(r'SYSTEM_CONTEXT:\s*(.*?)(?=\s+OBJECTIVE|\s+CONSTRAINTS|$)', long_description, re.IGNORECASE | re.DOTALL)
    if context_match:
        context = context_match.group(1).strip()
        # Take first meaningful line
        lines = [line.strip() for line in context.split('\n') if line.strip()]
        if lines:
            return f"Docker Refactor: {lines[0][:80]}"
    
    # Fallback: take first 100 characters
    return long_description[:100].strip() + "..."

def chunk_long_description(description: str) -> list:
    """Chunk long description into manageable pieces"""
    
    # Split by priority keywords first
    priority_keywords = ['PHASE', 'OBJECTIVE', 'CONSTRAINTS', 'MEMORY', 'REPORTING', 'SYSTEM_CONTEXT', 'SUCCESS_CRITERIA']
    
    # Split by keywords
    parts = re.split(r'(\b(?:PHASE|OBJECTIVE|CONSTRAINTS|MEMORY|REPORTING|SYSTEM_CONTEXT|SUCCESS_CRITERIA)\b)', description, flags=re.IGNORECASE)
    
    chunks = []
    current_chunk = ""
    
    for i, part in enumerate(parts):
        if i % 2 == 0:  # Regular text
            current_chunk += part
        else:  # Keyword
            if current_chunk and len(current_chunk.strip()) > 50:
                chunks.append(current_chunk.strip())
                current_chunk = part
            else:
                current_chunk += part
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # If still too long, split by sentences
    if len(chunks) <= 1:
        sentences = re.split(r'([.!?]+)\s+', description)
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk + sentence) <= 200:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
    
    # Clean chunks
    cleaned_chunks = []
    for chunk in chunks:
        cleaned = re.sub(r'\s+', ' ', chunk.strip())
        if len(cleaned) >= 30:
            cleaned_chunks.append(cleaned)
    
    return cleaned_chunks if cleaned_chunks else ["Task description"]

def fix_current_long_task():
    """Fix the current very long task"""
    
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
        
        # Create improved task
        ph_time = get_philippines_time()
        timestamp = ph_time.strftime('%Y%m%dT%H%M%S')
        
        # Create short description
        short_desc = create_short_description(long_task['description'])
        desc_part = short_desc.replace(' ', '_')[:30]
        new_task_id = f"{timestamp}_{desc_part}"
        
        # Chunk the description
        chunks = chunk_long_description(long_task['description'])
        
        print(f"\n✅ Improved task created:")
        print(f"   New ID: {new_task_id}")
        print(f"   Short description: {short_desc}")
        print(f"   New chunks: {len(chunks)}")
        
        # Create improved task structure
        improved_task = {
            "id": new_task_id,
            "description": short_desc,
            "full_description": long_task['description'],  # Keep full description
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
        print(f"   New task ID: {new_task_id}")
        print(f"   Chunks improved: {len(long_task['todos'])} → {len(chunks)}")
        
        # Show new chunks
        print(f"\n📋 New chunks:")
        for i, chunk in enumerate(chunks):
            print(f"   {i+1}. {chunk[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing long task: {e}")
        return False

if __name__ == "__main__":
    fix_current_long_task() 