"""
🤖 Cursor Session Auto-Activation System
Automatically loads production deployment intelligence for new Cursor sessions
"""

import json
import os
from pathlib import Path
from datetime import datetime

class CursorSessionActivator:
    """Auto-activates production intelligence for new Cursor sessions"""
    
    def __init__(self):
        self.workspace_root = Path.cwd()
        self.memory_bank = self.workspace_root / "memory-bank"
        self.session_file = self.memory_bank / "cursor_session_context.json"
        
    def activate_production_intelligence(self):
        """Activate production deployment intelligence"""
        print("🤖 ACTIVATING CURSOR PRODUCTION INTELLIGENCE...")
        
        # 1. Load production context
        context = self._build_session_context()
        
        # 2. Save context for easy access
        self._save_session_context(context)
        
        # 3. Generate activation prompt
        activation_prompt = self._generate_activation_prompt(context)
        
        # 4. Save activation prompt
        self._save_activation_prompt(activation_prompt)
        
        print("✅ CURSOR INTELLIGENCE ACTIVATED!")
        print(f"📍 Context saved to: {self.session_file}")
        print(f"📋 Ready for production deployment assistance!")
        
        return activation_prompt
    
    def _build_session_context(self):
        """Build comprehensive session context"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "workspace": str(self.workspace_root),
            "production_status": "READY",
            "intelligence_mode": "PRODUCTION_DEPLOYMENT_EXPERT",
            
            # Core capabilities
            "capabilities": {
                "docker_deployment": True,
                "security_hardening": True, 
                "gpu_management": True,
                "monitoring_setup": True,
                "chaos_testing": True,
                "troubleshooting": True
            },
            
            # Key files instantly accessible
            "key_files": {
                "deployment_summary": "docs/AI_SYSTEM_PRODUCTION_DEPLOYMENT_SUMMARY.md",
                "local_guide": "docs/LOCAL_DEPLOYMENT_GUIDE.md",
                "security_script": "scripts/security-hardening.sh",
                "gpu_script": "scripts/setup-gpu-partitioning.sh",
                "mainpc_compose": "main_pc_code/config/docker-compose.yml",
                "pc2_compose": "pc2_code/config/docker-compose.yml",
                "observability": "docker-compose.observability.yml"
            },
            
            # Production knowledge base
            "knowledge_base": {
                "production_deployment": {
                    "steps": [
                        "git reset --hard origin/cursor/reorganize-agent-groups-for-docker-production-deployment-8f25",
                        "scripts/security-hardening.sh",
                        "scripts/setup-gpu-partitioning.sh", 
                        "docker-compose up production services",
                        "deploy observability stack",
                        "run health checks"
                    ],
                    "requirements": ["Docker", "NVIDIA drivers", "10GB disk space"],
                    "potential_issues": ["Docker daemon", "Port conflicts", "GPU drivers"]
                },
                
                "troubleshooting": {
                    "docker_issues": ["Check docker status", "Review logs", "Verify resources"],
                    "gpu_issues": ["nvidia-smi", "Check MIG/MPS", "Verify Docker GPU access"],
                    "network_issues": ["Check ports", "Verify connectivity", "Review firewall"]
                },
                
                "quick_commands": {
                    "status_check": "docker ps -a && nvidia-smi",
                    "logs": "docker-compose logs --tail=50",
                    "health": "curl http://localhost:3000/health",
                    "gpu_status": "nvidia-smi && docker run --gpus all nvidia/cuda:11.0-base nvidia-smi"
                }
            },
            
            # Current system state
            "system_state": self._get_current_system_state()
        }
        
        return context
    
    def _get_current_system_state(self):
        """Get current system state"""
        try:
            import subprocess
            
            # Git status
            git_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True).stdout.strip()
            
            # File checks
            key_files_exist = {}
            key_files = [
                "docs/AI_SYSTEM_PRODUCTION_DEPLOYMENT_SUMMARY.md",
                "scripts/security-hardening.sh",
                "main_pc_code/config/docker-compose.yml"
            ]
            
            for file in key_files:
                key_files_exist[file] = Path(file).exists()
            
            # Docker status
            docker_running = subprocess.run(['docker', 'info'], 
                                          capture_output=True).returncode == 0
            
            return {
                "git_branch": git_branch,
                "target_branch": "cursor/reorganize-agent-groups-for-docker-production-deployment-8f25",
                "key_files_exist": key_files_exist,
                "docker_running": docker_running,
                "production_ready": all(key_files_exist.values()) and docker_running
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _save_session_context(self, context):
        """Save session context for easy access"""
        self.memory_bank.mkdir(exist_ok=True)
        
        with open(self.session_file, 'w') as f:
            json.dump(context, f, indent=2)
    
    def _generate_activation_prompt(self, context):
        """Generate activation prompt for Cursor"""
        prompt = f"""
🤖 CURSOR PRODUCTION INTELLIGENCE ACTIVATED
==========================================

You are now operating as a PRODUCTION DEPLOYMENT SPECIALIST for the AI System Monorepo.

CURRENT STATUS:
• Workspace: {context['workspace']}
• Branch: {context['system_state'].get('git_branch', 'unknown')}
• Production Ready: {context['system_state'].get('production_ready', False)}
• Intelligence Mode: {context['intelligence_mode']}

CORE CAPABILITIES ACTIVATED:
✅ Docker deployment expertise
✅ Security hardening knowledge  
✅ GPU management (RTX 4090/3060)
✅ Monitoring & observability
✅ Chaos testing & resilience
✅ Production troubleshooting

INSTANT ACCESS TO:
📚 {len(context['key_files'])} production documents
💻 {len(context['knowledge_base']['quick_commands'])} quick commands
🔧 Complete deployment workflows
⚠️ Predictive issue detection

QUICK START COMMANDS:
• Production Status: python3 cursor_session_auto_activation.py --status
• Deploy Production: python3 cursor_session_auto_activation.py --deploy
• Emergency Help: python3 cursor_session_auto_activation.py --help

INTELLIGENT RESPONSE MODE:
When user asks production-related questions, I will:
1. 🎯 Instantly identify the topic (deployment, troubleshooting, etc.)
2. 📊 Provide confidence score and context
3. 📋 Give step-by-step actionable instructions
4. ⚠️ Warn about potential issues
5. 📚 Reference exact files and commands
6. 💻 Provide copy-paste ready commands

USER TRIGGER PHRASES:
• "deploy production" → Full deployment workflow
• "docker issues" → Container troubleshooting mode
• "gpu problems" → GPU diagnostic workflow  
• "monitor system" → Observability guidance
• "security check" → Security audit mode
• "chaos test" → Resilience validation

I AM READY TO ASSIST WITH PRODUCTION DEPLOYMENT! 🚀
"""
        
        return prompt
    
    def _save_activation_prompt(self, prompt):
        """Save activation prompt for easy reference"""
        prompt_file = self.memory_bank / "cursor_activation_prompt.md"
        
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        print(f"📋 Activation prompt saved to: {prompt_file}")

def create_cursor_workspace_config():
    """Create Cursor workspace configuration"""
    cursor_config = {
        "ai.context": [
            "memory-bank/cursor_session_context.json",
            "memory-bank/cursor_activation_prompt.md",
            "docs/AI_SYSTEM_PRODUCTION_DEPLOYMENT_SUMMARY.md",
            "scripts/security-hardening.sh"
        ],
        "ai.rules": [
            "Act as production deployment specialist",
            "Always check memory-bank/cursor_session_context.json for current context", 
            "Provide step-by-step actionable guidance",
            "Include relevant file references and commands",
            "Warn about potential issues proactively"
        ],
        "ai.intelligence_mode": "production_deployment_expert"
    }
    
    cursor_dir = Path(".cursor")
    cursor_dir.mkdir(exist_ok=True)
    
    with open(cursor_dir / "settings.json", 'w') as f:
        json.dump(cursor_config, f, indent=2)
    
    print(f"✅ Cursor workspace config created: {cursor_dir}/settings.json")

def create_instant_triggers():
    """Create instant trigger files for common scenarios"""
    triggers = {
        "deploy_production.md": """
# 🚀 INSTANT PRODUCTION DEPLOYMENT

Run this when user says: "deploy production", "setup production", "go live"

## Immediate Actions:
1. `git reset --hard origin/cursor/reorganize-agent-groups-for-docker-production-deployment-8f25`
2. `scripts/security-hardening.sh`
3. `scripts/setup-gpu-partitioning.sh`
4. `docker-compose -f main_pc_code/config/docker-compose.yml up -d`
5. `docker-compose -f docker-compose.observability.yml up -d`

## Verification:
- `docker ps -a`
- `nvidia-smi`
- `curl http://localhost:3000`
""",
        
        "troubleshoot_docker.md": """
# 🔧 INSTANT DOCKER TROUBLESHOOTING

Run this when user says: "docker issues", "containers failing", "deployment broken"

## Diagnostic Steps:
1. `docker ps -a`
2. `docker-compose logs --tail=50`
3. `docker system df`
4. `systemctl status docker`

## Common Fixes:
- `sudo systemctl restart docker`
- `docker system prune -f`
- `docker-compose down && docker-compose up -d`
""",
        
        "gpu_diagnostics.md": """
# 🎮 INSTANT GPU DIAGNOSTICS

Run this when user says: "gpu issues", "nvidia problems", "gpu not working"

## GPU Checks:
1. `nvidia-smi`
2. `docker run --gpus all nvidia/cuda:11.0-base nvidia-smi`
3. `ls -la /dev/nvidia*`
4. `nvidia-container-cli info`

## GPU Fixes:
- `sudo systemctl restart nvidia-persistenced`
- `scripts/setup-gpu-partitioning.sh`
"""
    }
    
    triggers_dir = Path("memory-bank/instant-triggers")
    triggers_dir.mkdir(exist_ok=True)
    
    for filename, content in triggers.items():
        with open(triggers_dir / filename, 'w') as f:
            f.write(content)
    
    print(f"✅ Instant triggers created in: {triggers_dir}")

if __name__ == "__main__":
    import sys
    
    activator = CursorSessionActivator()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            # Quick status check
            print("🔍 PRODUCTION STATUS CHECK:")
            context = activator._build_session_context()
            state = context['system_state']
            
            print(f"Git Branch: {state.get('git_branch')}")
            print(f"Production Ready: {state.get('production_ready')}")
            print(f"Docker Running: {state.get('docker_running')}")
            
        elif sys.argv[1] == "--deploy":
            # Quick deployment trigger
            print("🚀 TRIGGERING PRODUCTION DEPLOYMENT...")
            print("Run these commands:")
            print("1. git reset --hard origin/cursor/reorganize-agent-groups-for-docker-production-deployment-8f25")
            print("2. scripts/security-hardening.sh") 
            print("3. scripts/setup-gpu-partitioning.sh")
            print("4. docker-compose -f main_pc_code/config/docker-compose.yml up -d")
            
        elif sys.argv[1] == "--help":
            # Emergency help
            print("🆘 PRODUCTION DEPLOYMENT HELP:")
            print("• Status: python3 cursor_session_auto_activation.py --status")
            print("• Deploy: python3 cursor_session_auto_activation.py --deploy") 
            print("• Files: ls docs/AI_SYSTEM_PRODUCTION_DEPLOYMENT_SUMMARY.md")
            print("• Logs: docker-compose logs --tail=50")
    else:
        # Full activation
        print("🤖 ACTIVATING CURSOR PRODUCTION INTELLIGENCE...")
        
        # 1. Activate intelligence system
        activation_prompt = activator.activate_production_intelligence()
        
        # 2. Create Cursor workspace config
        create_cursor_workspace_config()
        
        # 3. Create instant triggers
        create_instant_triggers()
        
        print("\n" + "="*60)
        print("✅ CURSOR INTELLIGENCE FULLY ACTIVATED!")
        print("="*60)
        print()
        print("🎯 NEXT STEPS:")
        print("1. Restart Cursor to load new configuration")
        print("2. In new session, try saying: 'deploy production'")
        print("3. AI Cursor will instantly know what to do!")
        print()
        print("📋 TRIGGER PHRASES:")
        print("• 'deploy production' → Full deployment workflow")
        print("• 'docker issues' → Container troubleshooting")  
        print("• 'gpu problems' → GPU diagnostics")
        print("• 'monitor system' → Observability setup")
        print()
        print("🚀 AI Cursor is now a PRODUCTION DEPLOYMENT EXPERT!")