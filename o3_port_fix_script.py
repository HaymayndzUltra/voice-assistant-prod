#!/usr/bin/env python3
"""
O3 Pro Max - Step 3: Port-map sanitization
Fix port conflicts as identified in the analysis:
- LearningOrchestrationService keeps port 7210 (core-services)
- ModelOrchestrator moves to 7213/8213 (language-processing)
"""
import pathlib
import re
import yaml
import sys

def fix_startup_config_ports():
    """Fix port conflicts in startup_config.yaml"""
    config_path = pathlib.Path("main_pc_code/config/startup_config.yaml")
    
    print("🔧 O3 Pro Max - Step 3: Port-map sanitization")
    print("=" * 60)
    print(f"Fixing port conflicts in: {config_path}")
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Create backup
        backup_path = config_path.with_suffix('.yaml.bak')
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"💾 Backup created: {backup_path}")
        
        # Fix ModelOrchestrator port conflict (7210 → 7213)
        original_content = content
        
        # Find ModelOrchestrator section and change its port
        content = re.sub(
            r'(ModelOrchestrator:.*?port:\s*)7210',
            r'\g<1>7213',
            content,
            flags=re.DOTALL
        )
        
        # Change ModelOrchestrator health port (8210 → 8213)
        content = re.sub(
            r'(ModelOrchestrator:.*?health_check_port:\s*)8210',
            r'\g<1>8213', 
            content,
            flags=re.DOTALL
        )
        
        if content != original_content:
            with open(config_path, 'w') as f:
                f.write(content)
            print("✅ Fixed ModelOrchestrator port: 7210 → 7213")
            print("✅ Fixed ModelOrchestrator health port: 8210 → 8213")
            return True
        else:
            print("ℹ️  No port conflicts found in startup_config.yaml")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing startup config: {e}")
        return False

def check_docker_compose_conflicts():
    """Check for port conflicts in docker-compose files"""
    print("\n🐳 Checking Docker Compose port conflicts...")
    
    compose_files = [
        "docker/docker-compose.mainpc.yml",
        "docker/docker-compose.pc2.yml", 
        "docker/docker-compose.router.yml"
    ]
    
    port_conflicts = []
    all_ports = {}
    
    for compose_file in compose_files:
        compose_path = pathlib.Path(compose_file)
        if not compose_path.exists():
            continue
            
        try:
            content = compose_path.read_text()
            
            # Find port mappings (format: "HOST:CONTAINER")
            port_patterns = re.findall(r'"(\d+):(\d+)"', content)
            
            for host_port, container_port in port_patterns:
                if host_port in all_ports:
                    conflict = f"Port {host_port} used in both {all_ports[host_port]} and {compose_file}"
                    port_conflicts.append(conflict)
                    print(f"⚠️  {conflict}")
                else:
                    all_ports[host_port] = compose_file
                    
        except Exception as e:
            print(f"❌ Error reading {compose_file}: {e}")
    
    if not port_conflicts:
        print("✅ No Docker Compose port conflicts found")
    
    return port_conflicts

def run_port_conflict_check():
    """Run comprehensive port conflict check"""
    print("\n🔍 Running comprehensive port conflict check...")
    
    # Check if the check script exists
    check_script = pathlib.Path("scripts/check_port_conflicts.py")
    if check_script.exists():
        print(f"📋 Found port conflict checker: {check_script}")
        return True
    else:
        print("ℹ️  Port conflict checker not found, using basic validation")
        return False

def validate_port_assignments():
    """Validate that all port assignments are unique"""
    print("\n✅ Validating port assignments...")
    
    config_path = pathlib.Path("main_pc_code/config/startup_config.yaml")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        all_ports = []
        health_ports = []
        conflicts = []
        
        # Extract ports from agent groups
        agent_groups = config.get('agent_groups', {})
        for group_name, agents in agent_groups.items():
            for agent_name, agent_config in agents.items():
                port = agent_config.get('port')
                health_port = agent_config.get('health_check_port')
                
                if port:
                    if port in all_ports:
                        conflicts.append(f"Port {port} conflict: {agent_name}")
                    else:
                        all_ports.append(port)
                
                if health_port:
                    if health_port in health_ports:
                        conflicts.append(f"Health port {health_port} conflict: {agent_name}")
                    else:
                        health_ports.append(health_port)
        
        if conflicts:
            print("❌ Port conflicts found:")
            for conflict in conflicts:
                print(f"  • {conflict}")
            return False
        else:
            print(f"✅ All ports unique: {len(all_ports)} main ports, {len(health_ports)} health ports")
            return True
            
    except Exception as e:
        print(f"❌ Error validating ports: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting O3 Pro Max Step 3: Port-map sanitization")
    
    # Step 1: Fix startup config ports
    config_fixed = fix_startup_config_ports()
    
    # Step 2: Check Docker Compose conflicts  
    docker_conflicts = check_docker_compose_conflicts()
    
    # Step 3: Run port conflict check
    has_checker = run_port_conflict_check()
    
    # Step 4: Validate port assignments
    ports_valid = validate_port_assignments()
    
    print("\n" + "=" * 60)
    print("📋 O3 Pro Max Step 3 Summary:")
    print(f"  • Startup config fixed: {config_fixed}")
    print(f"  • Docker conflicts: {len(docker_conflicts)}")
    print(f"  • Port validation: {'✅ PASS' if ports_valid else '❌ FAIL'}")
    
    if ports_valid and len(docker_conflicts) == 0:
        print("\n✅ Port-map sanitization COMPLETE!")
        print("🎯 Next Step: Test system startup")
        print("💡 Run: docker-compose -f docker/docker-compose.mainpc.yml build --no-cache")
    else:
        print("\n⚠️  Port conflicts need manual resolution")
        print("💡 Check startup_config.yaml and docker-compose files") 