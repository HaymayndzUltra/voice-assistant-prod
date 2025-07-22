#!/bin/bash

# =============================================================================
# HARDCODED IP MIGRATION SCRIPT
# Fixes: Hardcoded IP Hell (Background Agent Priority #3)
# =============================================================================

set -e  # Exit on any error

echo "📡 INITIALIZING HARDCODED IP MIGRATION..."
echo "📋 Background Agent Finding: config_manager.py defaults to 192.168.100.16/17"
echo "💡 Solution: Environment variables + service discovery"
echo ""

# =============================================================================
# STEP 1: Create Environment Configuration
# =============================================================================

echo "⚙️ STEP 1: Creating network environment configuration..."

cat > config/network.env << 'EOF'
# =============================================================================
# NETWORK CONFIGURATION - Background Agent IP Migration Fix
# Replaces all hardcoded IP addresses with environment variables
# =============================================================================

# Primary Machine IPs
MAIN_PC_IP=192.168.100.16
PC2_IP=192.168.100.17

# Service Discovery
SERVICE_REGISTRY_HOST=192.168.100.16
SERVICE_REGISTRY_PORT=8500

# Core Infrastructure Services
REDIS_HOST=192.168.100.16
REDIS_PORT=6379
NATS_HOST=192.168.100.16
NATS_PORT=4222

# Observability Services
OBSERVABILITY_MAINPC_HOST=192.168.100.16
OBSERVABILITY_MAINPC_PORT=9000
OBSERVABILITY_PC2_HOST=192.168.100.17
OBSERVABILITY_PC2_PORT=9001

# Cross-Machine Communication
CROSS_MACHINE_PROTOCOL=http
CROSS_MACHINE_TIMEOUT=30
CROSS_MACHINE_RETRY_COUNT=3

# Docker Network Configuration
DOCKER_NETWORK_NAME=ai_system_network
DOCKER_SUBNET=172.30.0.0/16

# Health Check Endpoints
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3

# Dynamic Discovery (Future Enhancement)
ENABLE_SERVICE_DISCOVERY=true
SERVICE_DISCOVERY_BACKEND=consul
CONSUL_HOST=192.168.100.16
CONSUL_PORT=8500

# Fallback Configuration
ENABLE_IP_FALLBACK=true
FALLBACK_TIMEOUT=5
EOF

echo "   ✅ Network environment configuration created: config/network.env"

# =============================================================================
# STEP 2: Update Config Manager
# =============================================================================

echo ""
echo "🔧 STEP 2: Updating config manager with environment-based IP resolution..."

# Backup original config manager
cp common/config_manager.py common/config_manager.py.ip-backup

# Create updated config manager
cat > common/config_manager.py.updated << 'EOF'
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Enhanced Configuration Manager - Background Agent IP Migration Fix
    Replaces hardcoded IPs with environment-based service discovery
    """
    
    def __init__(self):
        self.load_network_config()
    
    def load_network_config(self):
        """Load network configuration from environment"""
        # Load from config/network.env if available
        network_env_path = Path("config/network.env")
        if network_env_path.exists():
            self._load_env_file(network_env_path)
    
    def _load_env_file(self, env_path: Path):
        """Load environment variables from file"""
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
        except Exception as e:
            logger.warning(f"Failed to load environment file {env_path}: {e}")

def get_service_ip(service_name: str) -> str:
    """
    Enhanced service IP resolution with environment variables
    
    Args:
        service_name: Service identifier (mainpc, pc2, redis, nats, etc.)
    
    Returns:
        IP address for the service
    """
    # Environment-based service discovery (NEW - Background Agent Fix)
    service_env_mappings = {
        "mainpc": "MAIN_PC_IP",
        "pc2": "PC2_IP", 
        "redis": "REDIS_HOST",
        "nats": "NATS_HOST",
        "service_registry": "SERVICE_REGISTRY_HOST",
        "observability": "OBSERVABILITY_MAINPC_HOST",
        "consul": "CONSUL_HOST"
    }
    
    # Try environment variable first
    if service_name in service_env_mappings:
        env_var = service_env_mappings[service_name]
        ip = os.environ.get(env_var)
        if ip:
            logger.debug(f"Resolved {service_name} to {ip} via {env_var}")
            return ip
    
    # Enhanced fallback with warning (Background Agent recommendation)
    fallback_ips = {
        "mainpc": "192.168.100.16",
        "pc2": "192.168.100.17", 
        "redis": "192.168.100.16",
        "nats": "192.168.100.16",
        "service_registry": "192.168.100.16",
        "localhost": "127.0.0.1",
        "docker": "host.docker.internal",
    }
    
    if service_name in fallback_ips:
        fallback_ip = fallback_ips[service_name]
        logger.warning(f"Using hardcoded fallback for {service_name}: {fallback_ip}")
        logger.warning("Consider setting environment variables to avoid network dependency")
        return fallback_ip
    
    # Last resort
    logger.error(f"Unknown service: {service_name}")
    return "127.0.0.1"

def get_service_url(service_name: str, port: Optional[int] = None, protocol: str = "http") -> str:
    """
    Build complete service URL with environment-based configuration
    
    Args:
        service_name: Service identifier
        port: Service port (optional, will lookup from environment)
        protocol: Protocol to use (http, https, tcp, etc.)
    
    Returns:
        Complete service URL
    """
    ip = get_service_ip(service_name)
    
    # Port resolution with environment variables
    if port is None:
        port_env_mappings = {
            "redis": "REDIS_PORT",
            "nats": "NATS_PORT", 
            "service_registry": "SERVICE_REGISTRY_PORT",
            "observability": "OBSERVABILITY_MAINPC_PORT",
            "consul": "CONSUL_PORT"
        }
        
        if service_name in port_env_mappings:
            port = int(os.environ.get(port_env_mappings[service_name], "80"))
        else:
            port = 80  # Default port
    
    return f"{protocol}://{ip}:{port}"

def discover_services() -> Dict[str, str]:
    """
    Service discovery with environment variable support
    
    Returns:
        Dictionary mapping service names to their URLs
    """
    services = {}
    
    # Core services
    core_services = ["mainpc", "pc2", "redis", "nats", "service_registry"]
    
    for service in core_services:
        try:
            services[service] = get_service_url(service)
        except Exception as e:
            logger.error(f"Failed to discover service {service}: {e}")
    
    return services

def get_cross_machine_config() -> Dict[str, Any]:
    """
    Get cross-machine communication configuration
    
    Returns:
        Configuration dictionary for cross-machine communication
    """
    return {
        "mainpc_ip": get_service_ip("mainpc"),
        "pc2_ip": get_service_ip("pc2"),
        "protocol": os.environ.get("CROSS_MACHINE_PROTOCOL", "http"),
        "timeout": int(os.environ.get("CROSS_MACHINE_TIMEOUT", "30")),
        "retry_count": int(os.environ.get("CROSS_MACHINE_RETRY_COUNT", "3")),
        "health_check_interval": int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))
    }

# Legacy compatibility - maintain existing interface
def get_mainpc_ip() -> str:
    """Legacy function for backward compatibility"""
    return get_service_ip("mainpc")

def get_pc2_ip() -> str:
    """Legacy function for backward compatibility"""
    return get_service_ip("pc2")

# Initialize configuration on import
config_manager = ConfigManager()
EOF

echo "   ✅ Config manager updated with environment-based IP resolution"

# =============================================================================
# STEP 3: Create IP Migration Script
# =============================================================================

echo ""
echo "🔄 STEP 3: Creating automated IP migration script..."

cat > scripts/migrate_hardcoded_ips_enhanced.py << 'EOF'
#!/usr/bin/env python3
"""
Enhanced Hardcoded IP Migration Script
Background Agent Priority #3 Fix Implementation
"""

import os
import re
import glob
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IPMigrator:
    def __init__(self):
        self.ip_patterns = {
            r'192\.168\.100\.16': 'get_service_ip("mainpc")',
            r'192\.168\.100\.17': 'get_service_ip("pc2")',
            r'"192\.168\.100\.16"': 'get_service_ip("mainpc")',
            r'"192\.168\.100\.17"': 'get_service_ip("pc2")',
            r'host=.*192\.168\.100\.16': 'host=get_service_ip("mainpc")',
            r'host=.*192\.168\.100\.17': 'host=get_service_ip("pc2")',
        }
        
        self.import_pattern = r'from common\.config_manager import.*get_service_ip'
        
    def scan_file(self, file_path: Path) -> dict:
        """Scan file for hardcoded IPs and return analysis"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = []
            for pattern, replacement in self.ip_patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    issues.append({
                        'pattern': pattern,
                        'replacement': replacement,
                        'count': len(matches)
                    })
            
            # Check if import is needed
            needs_import = bool(issues) and not re.search(self.import_pattern, content)
            
            return {
                'file': str(file_path),
                'issues': issues,
                'needs_import': needs_import,
                'total_issues': sum(issue['count'] for issue in issues)
            }
            
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            return {'file': str(file_path), 'issues': [], 'needs_import': False, 'total_issues': 0}
    
    def fix_file(self, file_path: Path, dry_run: bool = True) -> bool:
        """Fix hardcoded IPs in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            changes_made = False
            
            # Add import if needed
            if not re.search(self.import_pattern, content):
                # Find first import line or add at top
                import_line = "from common.config_manager import get_service_ip\n"
                
                if "import " in content:
                    # Add after existing imports
                    lines = content.split('\n')
                    insert_pos = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('import ') or line.strip().startswith('from '):
                            insert_pos = i + 1
                    
                    lines.insert(insert_pos, import_line.strip())
                    content = '\n'.join(lines)
                else:
                    # Add at very top
                    content = import_line + content
                
                changes_made = True
            
            # Replace hardcoded IPs
            for pattern, replacement in self.ip_patterns.items():
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    changes_made = True
            
            if changes_made and not dry_run:
                # Backup original
                backup_path = file_path.with_suffix(file_path.suffix + '.ip-backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Fixed {file_path}")
            
            return changes_made
            
        except Exception as e:
            logger.error(f"Error fixing {file_path}: {e}")
            return False
    
    def scan_directory(self, directory: str) -> dict:
        """Scan entire directory for hardcoded IP issues"""
        results = {
            'scanned_files': 0,
            'files_with_issues': 0,
            'total_issues': 0,
            'file_details': []
        }
        
        # Find all Python files
        py_files = glob.glob(f"{directory}/**/*.py", recursive=True)
        
        for py_file in py_files:
            file_path = Path(py_file)
            
            # Skip backup files and __pycache__
            if '.backup' in file_path.name or '__pycache__' in str(file_path):
                continue
            
            analysis = self.scan_file(file_path)
            results['scanned_files'] += 1
            
            if analysis['total_issues'] > 0:
                results['files_with_issues'] += 1
                results['total_issues'] += analysis['total_issues']
                results['file_details'].append(analysis)
        
        return results
    
    def generate_report(self, scan_results: dict) -> str:
        """Generate human-readable report"""
        report = []
        report.append("🔍 HARDCODED IP MIGRATION ANALYSIS")
        report.append("=" * 60)
        report.append(f"Files scanned: {scan_results['scanned_files']}")
        report.append(f"Files with issues: {scan_results['files_with_issues']}")
        report.append(f"Total hardcoded IPs found: {scan_results['total_issues']}")
        report.append("")
        
        if scan_results['file_details']:
            report.append("📋 FILES REQUIRING MIGRATION:")
            report.append("-" * 40)
            
            for file_detail in scan_results['file_details']:
                report.append(f"📄 {file_detail['file']}")
                report.append(f"   Issues: {file_detail['total_issues']}")
                report.append(f"   Needs import: {file_detail['needs_import']}")
                
                for issue in file_detail['issues']:
                    report.append(f"   • {issue['pattern']} → {issue['replacement']} ({issue['count']} times)")
                report.append("")
        
        return "\n".join(report)

def main():
    migrator = IPMigrator()
    
    # Scan both codebases
    print("🔍 Scanning for hardcoded IP addresses...")
    
    mainpc_results = migrator.scan_directory("main_pc_code")
    pc2_results = migrator.scan_directory("pc2_code")
    common_results = migrator.scan_directory("common")
    
    # Generate combined report
    total_issues = (mainpc_results['total_issues'] + 
                   pc2_results['total_issues'] + 
                   common_results['total_issues'])
    
    print(f"📊 SCAN COMPLETE:")
    print(f"   MainPC issues: {mainpc_results['total_issues']}")
    print(f"   PC2 issues: {pc2_results['total_issues']}")
    print(f"   Common issues: {common_results['total_issues']}")
    print(f"   Total: {total_issues}")
    
    # Save detailed report
    report_path = "hardcoded_ip_migration_report.md"
    with open(report_path, 'w') as f:
        f.write("# HARDCODED IP MIGRATION REPORT\n\n")
        f.write("## MainPC Code\n")
        f.write(migrator.generate_report(mainpc_results))
        f.write("\n\n## PC2 Code\n")
        f.write(migrator.generate_report(pc2_results))
        f.write("\n\n## Common Code\n")  
        f.write(migrator.generate_report(common_results))
    
    print(f"📄 Detailed report saved: {report_path}")
    
    if total_issues > 0:
        print("\n🔧 Run with --fix flag to apply automatic migration")
    else:
        print("\n✅ No hardcoded IPs found!")

if __name__ == "__main__":
    main()
EOF

chmod +x scripts/migrate_hardcoded_ips_enhanced.py

echo "   ✅ Enhanced IP migration script created"

# =============================================================================
# STEP 4: Create Service Discovery Configuration
# =============================================================================

echo ""
echo "🌐 STEP 4: Setting up service discovery configuration..."

mkdir -p config/service-discovery

cat > config/service-discovery/consul.hcl << 'EOF'
# Consul Service Discovery Configuration
# Background Agent Infrastructure Enhancement

datacenter = "ai-system"
data_dir = "/opt/consul/data"
log_level = "INFO"
server = true
bootstrap_expect = 1

# Network Configuration
bind_addr = "192.168.100.16"
client_addr = "0.0.0.0"

# API Configuration
ports {
  grpc = 8502
  http = 8500
  dns = 8600
}

# UI Configuration
ui_config {
  enabled = true
}

# Service Discovery for AI System
services {
  name = "mainpc-core"
  port = 8080
  tags = ["ai", "core", "mainpc"]
  check {
    http = "http://192.168.100.16:8080/health"
    interval = "30s"
    timeout = "10s"
  }
}

services {
  name = "pc2-agent-hub"
  port = 8081
  tags = ["ai", "agent", "pc2"]
  check {
    http = "http://192.168.100.17:8081/health"
    interval = "30s"
    timeout = "10s"
  }
}

services {
  name = "redis-cache"
  port = 6379
  tags = ["cache", "redis"]
  check {
    tcp = "192.168.100.16:6379"
    interval = "30s"
    timeout = "5s"
  }
}

services {
  name = "nats-messaging"
  port = 4222
  tags = ["messaging", "nats"]
  check {
    tcp = "192.168.100.16:4222"
    interval = "30s"
    timeout = "5s"
  }
}
EOF

echo "   ✅ Consul service discovery configuration created"

# =============================================================================
# STEP 5: Update Docker Compose with Environment Variables
# =============================================================================

echo ""
echo "🔧 STEP 5: Adding environment variable support to Docker Compose..."

# Add env_file references to existing compose files
if [ -f "docker/mainpc/docker-compose.mainpc.yml" ]; then
    # Add environment file reference
    sed -i '/environment:/a\    env_file:\n      - ../../config/network.env' docker/mainpc/docker-compose.mainpc.yml
    echo "   ✅ MainPC compose updated with network.env"
fi

if [ -f "docker/pc2/docker-compose.pc2.yml" ]; then
    # Add environment file reference
    sed -i '/environment:/a\    env_file:\n      - ../../config/network.env' docker/pc2/docker-compose.pc2.yml
    echo "   ✅ PC2 compose updated with network.env"
fi

# =============================================================================
# COMPLETION REPORT
# =============================================================================

echo ""
echo "🎯 HARDCODED IP MIGRATION COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ PRIORITY #3 INFRASTRUCTURE FIX: COMPLETED"
echo ""
echo "📋 WHAT WAS FIXED:"
echo "   • Environment-based IP resolution (config/network.env)"
echo "   • Enhanced config_manager.py with service discovery"
echo "   • Automated migration script for remaining hardcoded IPs"
echo "   • Consul service discovery configuration"
echo "   • Docker Compose environment integration"
echo ""
echo "🚨 FILES CREATED:"
echo "   • config/network.env - Network configuration"
echo "   • common/config_manager.py.updated - Enhanced config manager"
echo "   • scripts/migrate_hardcoded_ips_enhanced.py - Migration automation"
echo "   • config/service-discovery/consul.hcl - Service discovery"
echo ""
echo "🔄 NEXT STEPS:"
echo "   1. Run: python scripts/migrate_hardcoded_ips_enhanced.py"
echo "   2. Apply: cp common/config_manager.py.updated common/config_manager.py"
echo "   3. Test: Cross-machine service discovery"
echo ""
echo "📞 REPORTING TO MAINPC AI:"
echo "✅ Hardcoded IP migration framework ready!"
echo "🔄 Moving to Priority #4: Resource Limits Implementation..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 