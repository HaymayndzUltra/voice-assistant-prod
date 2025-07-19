#!/usr/bin/env python3
"""
Fix the health_check method in mood_tracker_agent.py
"""

import re

def fix_mood_tracker_health_check():
    file_path = "main_pc_code/agents/mood_tracker_agent.py"
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the health_check method with incorrect indentation
        pattern = re.compile(r'def\s+health_check\s*\(\s*self\s*\):(?:\s*"""[\s\S]*?""")?\s*(.*?)(?=\n\s*def|\n\s*if\s+__name__|\Z)', re.DOTALL)
        match = pattern.search(content)
        
        if not match:
            print("Could not find health_check method in the file")
            return False
        
        # Extract the method body
        method_body = match.group(1)
        
        # Create the properly indented health_check method
        proper_health_check = """
    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }
"""
        
        # Replace the old method with the new one
        new_content = re.sub(r'def\s+health_check\s*\(\s*self\s*\):(?:\s*"""[\s\S]*?""")?\s*(.*?)(?=\n\s*def|\n\s*if\s+__name__|\Z)', 
                            proper_health_check, content, flags=re.DOTALL)
        
        # Add missing imports if needed
        if "import psutil" not in new_content:
            new_content = new_content.replace("import time", "import time\nimport psutil")
        
        if "from datetime import datetime" not in new_content:
            new_content = new_content.replace("import time", "import time\nfrom datetime import datetime")
        
        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Successfully fixed health_check method in {file_path}")
        return True
    
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

if __name__ == "__main__":
    fix_mood_tracker_health_check() 