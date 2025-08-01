#!/bin/bash
# AI System Security Hardening Script
# Implements mTLS, Docker Content Trust, network policies, and security best practices

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${CERTS_DIR:-/etc/ai-system/certs}"
CA_VALIDITY_DAYS="${CA_VALIDITY_DAYS:-3650}"
CERT_VALIDITY_DAYS="${CERT_VALIDITY_DAYS:-365}"
DOCKER_CONTENT_TRUST="${DOCKER_CONTENT_TRUST:-1}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Create Certificate Authority (CA)
create_ca() {
    log "Creating Certificate Authority..."
    
    mkdir -p "$CERTS_DIR"/{ca,server,client,etcd,kubelet}
    cd "$CERTS_DIR"
    
    # Generate CA private key
    openssl genrsa -out ca/ca-key.pem 4096
    
    # Generate CA certificate
    openssl req -new -x509 -sha256 -days $CA_VALIDITY_DAYS \
        -key ca/ca-key.pem \
        -out ca/ca.pem \
        -subj "/CN=AI-System-CA/O=AI-System/C=US/ST=CA/L=San Francisco"
    
    # Set proper permissions
    chmod 400 ca/ca-key.pem
    chmod 444 ca/ca.pem
    
    log "Certificate Authority created successfully"
}

# Generate server certificates
create_server_certificates() {
    log "Generating server certificates..."
    
    local services=(
        "observability:observability,localhost,127.0.0.1,10.0.0.1"
        "coordination:coordination,localhost,127.0.0.1,10.0.0.2"
        "memory-stack:memory-stack,localhost,127.0.0.1,10.0.0.3"
        "api-gateway:api-gateway,localhost,127.0.0.1,10.0.0.4"
    )
    
    for service_config in "${services[@]}"; do
        local service_name=$(echo "$service_config" | cut -d: -f1)
        local sans=$(echo "$service_config" | cut -d: -f2)
        
        log "Creating certificate for service: $service_name"
        
        # Generate private key
        openssl genrsa -out "server/${service_name}-key.pem" 2048
        
        # Generate certificate signing request
        openssl req -new -sha256 \
            -key "server/${service_name}-key.pem" \
            -out "server/${service_name}.csr" \
            -subj "/CN=${service_name}/O=AI-System/C=US/ST=CA/L=San Francisco"
        
        # Create extensions file for SAN
        cat > "server/${service_name}-ext.cnf" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
EOF
        
        # Add SAN entries
        local index=1
        IFS=',' read -ra SAN_ARRAY <<< "$sans"
        for san in "${SAN_ARRAY[@]}"; do
            if [[ "$san" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                echo "IP.${index} = $san" >> "server/${service_name}-ext.cnf"
            else
                echo "DNS.${index} = $san" >> "server/${service_name}-ext.cnf"
            fi
            ((index++))
        done
        
        # Sign the certificate
        openssl x509 -req -sha256 -days $CERT_VALIDITY_DAYS \
            -in "server/${service_name}.csr" \
            -CA ca/ca.pem \
            -CAkey ca/ca-key.pem \
            -CAcreateserial \
            -out "server/${service_name}.pem" \
            -extensions v3_req \
            -extfile "server/${service_name}-ext.cnf"
        
        # Set permissions
        chmod 400 "server/${service_name}-key.pem"
        chmod 444 "server/${service_name}.pem"
        
        # Clean up CSR and extensions
        rm "server/${service_name}.csr" "server/${service_name}-ext.cnf"
    done
    
    log "Server certificates generated successfully"
}

# Generate client certificates
create_client_certificates() {
    log "Generating client certificates..."
    
    local clients=(
        "admin"
        "monitoring"
        "backup-client"
        "api-client"
    )
    
    for client in "${clients[@]}"; do
        log "Creating certificate for client: $client"
        
        # Generate private key
        openssl genrsa -out "client/${client}-key.pem" 2048
        
        # Generate certificate signing request
        openssl req -new -sha256 \
            -key "client/${client}-key.pem" \
            -out "client/${client}.csr" \
            -subj "/CN=${client}/O=AI-System-Clients/C=US/ST=CA/L=San Francisco"
        
        # Sign the certificate
        openssl x509 -req -sha256 -days $CERT_VALIDITY_DAYS \
            -in "client/${client}.csr" \
            -CA ca/ca.pem \
            -CAkey ca/ca-key.pem \
            -CAcreateserial \
            -out "client/${client}.pem"
        
        # Set permissions
        chmod 400 "client/${client}-key.pem"
        chmod 444 "client/${client}.pem"
        
        # Clean up CSR
        rm "client/${client}.csr"
    done
    
    log "Client certificates generated successfully"
}

# Setup Docker Content Trust
setup_docker_content_trust() {
    log "Setting up Docker Content Trust..."
    
    # Enable Docker Content Trust globally
    echo 'export DOCKER_CONTENT_TRUST=1' >> /etc/environment
    export DOCKER_CONTENT_TRUST=1
    
    # Create notary directory
    mkdir -p ~/.docker/trust/private
    
    # Generate root key for signing
    docker trust key generate ai-system-root
    
    # Generate repository key
    docker trust key generate ai-system-repo
    
    # Initialize trust for our repositories
    local repos=(
        "ghcr.io/ai-system/coordination"
        "ghcr.io/ai-system/memory_stack"
        "ghcr.io/ai-system/observability_hub"
        "ghcr.io/ai-system_pc2/vision_dream_suite"
    )
    
    for repo in "${repos[@]}"; do
        log "Initializing trust for repository: $repo"
        docker trust signer add ai-system-signer "$repo" --key ai-system-repo.pub || warn "Failed to add signer for $repo"
    done
    
    # Create policy for content trust
    cat > /etc/docker/content-trust-policy.json << 'EOF'
{
    "default": [
        {
            "type": "Notary",
            "keys": ["ai-system-root.pub"]
        }
    ],
    "repositories": {
        "ghcr.io/ai-system/*": [
            {
                "type": "Notary",
                "keys": ["ai-system-repo.pub"]
            }
        ]
    }
}
EOF
    
    log "Docker Content Trust configured"
}

# Configure Docker daemon security
configure_docker_security() {
    log "Configuring Docker daemon security..."
    
    # Create Docker daemon configuration
    cat > /etc/docker/daemon.json << EOF
{
    "hosts": ["unix:///var/run/docker.sock"],
    "tls": true,
    "tlscert": "${CERTS_DIR}/server/docker.pem",
    "tlskey": "${CERTS_DIR}/server/docker-key.pem",
    "tlsverify": true,
    "tlscacert": "${CERTS_DIR}/ca/ca.pem",
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "userland-proxy": false,
    "no-new-privileges": true,
    "seccomp-profile": "/etc/docker/seccomp-profile.json",
    "apparmor-profile": "docker-default",
    "selinux-enabled": true,
    "live-restore": true,
    "content-trust": {
        "trust-pinning": true,
        "official-image-policy": "require-signatures"
    }
}
EOF
    
    # Create Docker seccomp profile
    cat > /etc/docker/seccomp-profile.json << 'EOF'
{
    "defaultAction": "SCMP_ACT_ERRNO",
    "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
    "syscalls": [
        {
            "names": [
                "accept", "accept4", "access", "adjtimex", "alarm", "bind", "brk", "capget", "capset", "chdir", "chmod", "chown",
                "chroot", "clock_getres", "clock_gettime", "clock_nanosleep", "close", "connect", "copy_file_range", "creat",
                "dup", "dup2", "dup3", "epoll_create", "epoll_create1", "epoll_ctl", "epoll_pwait", "epoll_wait", "eventfd",
                "eventfd2", "execve", "execveat", "exit", "exit_group", "faccessat", "fadvise64", "fallocate", "fanotify_mark",
                "fchdir", "fchmod", "fchmodat", "fchown", "fchownat", "fcntl", "fdatasync", "fgetxattr", "flistxattr", "flock",
                "fork", "fremovexattr", "fsetxattr", "fstat", "fstatat", "fstatfs", "fsync", "ftruncate", "futex", "getcpu",
                "getcwd", "getdents", "getdents64", "getegid", "geteuid", "getgid", "getgroups", "getpeername", "getpgid",
                "getpgrp", "getpid", "getppid", "getpriority", "getrandom", "getresgid", "getresuid", "getrlimit", "get_robust_list",
                "getrusage", "getsid", "getsockname", "getsockopt", "get_thread_area", "gettid", "gettimeofday", "getuid",
                "getxattr", "inotify_add_watch", "inotify_init", "inotify_init1", "inotify_rm_watch", "io_cancel", "ioctl",
                "io_destroy", "io_getevents", "ioprio_get", "ioprio_set", "io_setup", "io_submit", "ipc", "kill", "lchown",
                "lgetxattr", "link", "linkat", "listen", "listxattr", "llistxattr", "lremovexattr", "lseek", "lsetxattr",
                "lstat", "madvise", "memfd_create", "mincore", "mkdir", "mkdirat", "mknod", "mknodat", "mlock", "mlock2",
                "mlockall", "mmap", "mmap2", "mprotect", "mq_getsetattr", "mq_notify", "mq_open", "mq_timedreceive",
                "mq_timedsend", "mq_unlink", "mremap", "msgctl", "msgget", "msgrcv", "msgsnd", "msync", "munlock", "munlockall",
                "munmap", "nanosleep", "newfstatat", "open", "openat", "pause", "pipe", "pipe2", "poll", "ppoll", "prctl",
                "pread64", "preadv", "prlimit64", "pselect6", "ptrace", "pwrite64", "pwritev", "read", "readahead", "readlink",
                "readlinkat", "readv", "recv", "recvfrom", "recvmmsg", "recvmsg", "remap_file_pages", "removexattr", "rename",
                "renameat", "renameat2", "restart_syscall", "rmdir", "rt_sigaction", "rt_sigpending", "rt_sigprocmask",
                "rt_sigqueueinfo", "rt_sigreturn", "rt_sigsuspend", "rt_sigtimedwait", "rt_tgsigqueueinfo", "sched_getaffinity",
                "sched_getattr", "sched_getparam", "sched_get_priority_max", "sched_get_priority_min", "sched_getscheduler",
                "sched_setaffinity", "sched_setattr", "sched_setparam", "sched_setscheduler", "sched_yield", "seccomp",
                "select", "semctl", "semget", "semop", "semtimedop", "send", "sendfile", "sendfile64", "sendmmsg", "sendmsg",
                "sendto", "setfsgid", "setfsuid", "setgid", "setgroups", "setitimer", "setpgid", "setpriority", "setregid",
                "setresgid", "setresuid", "setreuid", "setrlimit", "setsid", "setsockopt", "set_thread_area", "set_tid_address",
                "setuid", "setxattr", "shmat", "shmctl", "shmdt", "shmget", "shutdown", "sigaltstack", "signalfd", "signalfd4",
                "sigreturn", "socket", "socketcall", "socketpair", "splice", "stat", "statfs", "symlink", "symlinkat", "sync",
                "sync_file_range", "syncfs", "sysinfo", "syslog", "tee", "tgkill", "time", "timer_create", "timer_delete",
                "timerfd_create", "timerfd_gettime", "timerfd_settime", "timer_getoverrun", "timer_gettime", "timer_settime",
                "times", "tkill", "truncate", "umask", "uname", "unlink", "unlinkat", "utime", "utimensat", "utimes", "vfork",
                "vmsplice", "wait4", "waitid", "waitpid", "write", "writev"
            ],
            "action": "SCMP_ACT_ALLOW"
        }
    ]
}
EOF
    
    # Restart Docker daemon
    systemctl restart docker
    
    log "Docker security configuration completed"
}

# Setup network security policies
setup_network_policies() {
    log "Setting up network security policies..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        warn "kubectl not found, skipping Kubernetes network policies"
        return
    fi
    
    # Create default deny-all network policy
    cat > /tmp/default-deny-all.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ai-system-core
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ai-system-gpu
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ai-system-infra
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF
    
    # Create allow-internal-traffic policy
    cat > /tmp/allow-internal-traffic.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal-traffic
  namespace: ai-system-core
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ai-system-core
    - namespaceSelector:
        matchLabels:
          name: ai-system-gpu
    - namespaceSelector:
        matchLabels:
          name: ai-system-infra
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: ai-system-core
    - namespaceSelector:
        matchLabels:
          name: ai-system-gpu
    - namespaceSelector:
        matchLabels:
          name: ai-system-infra
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 443
EOF
    
    # Apply network policies
    kubectl apply -f /tmp/default-deny-all.yaml || warn "Failed to apply default deny policy"
    kubectl apply -f /tmp/allow-internal-traffic.yaml || warn "Failed to apply internal traffic policy"
    
    # Clean up temporary files
    rm -f /tmp/default-deny-all.yaml /tmp/allow-internal-traffic.yaml
    
    log "Network policies configured"
}

# Configure firewall rules
configure_firewall() {
    log "Configuring firewall rules..."
    
    # Check if UFW is available
    if command -v ufw &> /dev/null; then
        # Reset UFW to defaults
        ufw --force reset
        
        # Set default policies
        ufw default deny incoming
        ufw default allow outgoing
        
        # Allow SSH
        ufw allow ssh
        
        # Allow Docker daemon (if using remote access)
        ufw allow 2376/tcp
        
        # Allow Kubernetes API server
        ufw allow 6443/tcp
        
        # Allow kubelet API
        ufw allow 10250/tcp
        
        # Allow AI System services (adjust ports as needed)
        ufw allow 7200:7300/tcp  # AI System services
        ufw allow 8200:8300/tcp  # Health check ports
        ufw allow 9000:9200/tcp  # Monitoring ports
        
        # Allow inter-node communication
        ufw allow from 10.0.0.0/8 to any
        ufw allow from 172.16.0.0/12 to any
        ufw allow from 192.168.0.0/16 to any
        
        # Enable UFW
        ufw --force enable
        
        log "UFW firewall configured"
    elif command -v firewall-cmd &> /dev/null; then
        # Configure firewalld
        firewall-cmd --permanent --zone=public --add-service=ssh
        firewall-cmd --permanent --zone=public --add-port=2376/tcp
        firewall-cmd --permanent --zone=public --add-port=6443/tcp
        firewall-cmd --permanent --zone=public --add-port=10250/tcp
        firewall-cmd --permanent --zone=public --add-port=7200-7300/tcp
        firewall-cmd --permanent --zone=public --add-port=8200-8300/tcp
        firewall-cmd --permanent --zone=public --add-port=9000-9200/tcp
        
        # Add trusted networks
        firewall-cmd --permanent --zone=trusted --add-source=10.0.0.0/8
        firewall-cmd --permanent --zone=trusted --add-source=172.16.0.0/12
        firewall-cmd --permanent --zone=trusted --add-source=192.168.0.0/16
        
        firewall-cmd --reload
        
        log "firewalld configured"
    else
        warn "No supported firewall found (ufw or firewalld)"
    fi
}

# Setup system hardening
setup_system_hardening() {
    log "Applying system hardening..."
    
    # Disable unnecessary services
    local services_to_disable=(
        "telnet"
        "rsh"
        "rlogin"
        "vsftpd"
        "httpd"
        "nginx"
        "apache2"
    )
    
    for service in "${services_to_disable[@]}"; do
        if systemctl is-enabled "$service" &>/dev/null; then
            systemctl disable "$service"
            systemctl stop "$service"
            log "Disabled service: $service"
        fi
    done
    
    # Configure kernel parameters for security
    cat > /etc/sysctl.d/99-ai-system-security.conf << 'EOF'
# Network security
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# IPv6 security
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Kernel security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
kernel.kexec_load_disabled = 1

# File system security
fs.suid_dumpable = 0
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF
    
    # Apply sysctl settings
    sysctl -p /etc/sysctl.d/99-ai-system-security.conf
    
    # Configure audit logging
    if command -v auditctl &> /dev/null; then
        cat > /etc/audit/rules.d/ai-system.rules << 'EOF'
# Monitor file access
-w /etc/ai-system/ -p wa -k ai_system_config
-w /var/lib/docker/ -p wa -k docker_data
-w /etc/docker/ -p wa -k docker_config
-w /etc/kubernetes/ -p wa -k kubernetes_config

# Monitor privilege escalation
-a always,exit -F arch=b64 -S setuid -S setgid -S setreuid -S setregid -k privilege_escalation
-a always,exit -F arch=b32 -S setuid -S setgid -S setreuid -S setregid -k privilege_escalation

# Monitor network connections
-a always,exit -F arch=b64 -S socket -S connect -S bind -k network_connections
-a always,exit -F arch=b32 -S socket -S connect -S bind -k network_connections
EOF
        
        # Restart auditd
        systemctl restart auditd
        log "Audit logging configured"
    fi
    
    log "System hardening completed"
}

# Generate TLS configuration for services
generate_tls_configs() {
    log "Generating TLS configurations for services..."
    
    # Create observability TLS config
    cat > "${CERTS_DIR}/observability-tls.yaml" << EOF
tls:
  cert_file: "${CERTS_DIR}/server/observability.pem"
  key_file: "${CERTS_DIR}/server/observability-key.pem"
  ca_file: "${CERTS_DIR}/ca/ca.pem"
  client_auth_type: "RequireAndVerifyClientCert"
  min_version: "TLS1.2"
  cipher_suites:
    - "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
    - "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305"
    - "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
EOF
    
    # Create coordination service TLS config
    cat > "${CERTS_DIR}/coordination-tls.yaml" << EOF
tls:
  cert_file: "${CERTS_DIR}/server/coordination.pem"
  key_file: "${CERTS_DIR}/server/coordination-key.pem"
  ca_file: "${CERTS_DIR}/ca/ca.pem"
  client_auth_type: "RequireAndVerifyClientCert"
  min_version: "TLS1.2"
EOF
    
    # Create memory-stack TLS config
    cat > "${CERTS_DIR}/memory-stack-tls.yaml" << EOF
tls:
  cert_file: "${CERTS_DIR}/server/memory-stack.pem"
  key_file: "${CERTS_DIR}/server/memory-stack-key.pem"
  ca_file: "${CERTS_DIR}/ca/ca.pem"
  client_auth_type: "RequireAndVerifyClientCert"
  min_version: "TLS1.2"
EOF
    
    log "TLS configurations generated"
}

# Verify security configuration
verify_security() {
    log "Verifying security configuration..."
    
    # Check certificate validity
    for cert in "${CERTS_DIR}"/server/*.pem; do
        if openssl x509 -in "$cert" -noout -checkend 86400; then
            info "Certificate valid: $(basename "$cert")"
        else
            warn "Certificate expiring soon: $(basename "$cert")"
        fi
    done
    
    # Check Docker Content Trust
    if [[ "${DOCKER_CONTENT_TRUST}" == "1" ]]; then
        info "Docker Content Trust is enabled"
    else
        warn "Docker Content Trust is disabled"
    fi
    
    # Check firewall status
    if command -v ufw &> /dev/null; then
        ufw status
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --list-all
    fi
    
    # Check network policies (if Kubernetes is available)
    if command -v kubectl &> /dev/null && kubectl cluster-info &>/dev/null; then
        kubectl get networkpolicies -A || warn "No network policies found"
    fi
    
    log "Security verification completed"
}

# Main hardening function
perform_hardening() {
    log "Starting AI System security hardening..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
    
    # Create CA and certificates
    create_ca
    create_server_certificates
    create_client_certificates
    
    # Configure Docker security
    setup_docker_content_trust
    configure_docker_security
    
    # Setup network security
    setup_network_policies
    configure_firewall
    
    # Apply system hardening
    setup_system_hardening
    
    # Generate service configurations
    generate_tls_configs
    
    # Verify everything is working
    verify_security
    
    log "Security hardening completed successfully!"
    
    info "Next steps:"
    info "1. Restart all AI System services to apply TLS configurations"
    info "2. Update service configurations to use TLS certificates"
    info "3. Test mTLS connectivity between services"
    info "4. Monitor audit logs for security events"
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    harden          Apply full security hardening
    certs           Generate certificates only
    docker          Configure Docker security only
    network         Setup network policies only
    firewall        Configure firewall only
    verify          Verify security configuration
    help            Show this help message

Environment Variables:
    CERTS_DIR               Certificate directory (default: /etc/ai-system/certs)
    CA_VALIDITY_DAYS        CA certificate validity (default: 3650)
    CERT_VALIDITY_DAYS      Service certificate validity (default: 365)
    DOCKER_CONTENT_TRUST    Enable Docker Content Trust (default: 1)

Examples:
    $0 harden              # Full security hardening
    $0 certs               # Generate certificates only
    $0 verify              # Verify current security
EOF
}

case "${1:-harden}" in
    "harden")
        perform_hardening
        ;;
    "certs")
        create_ca
        create_server_certificates
        create_client_certificates
        generate_tls_configs
        ;;
    "docker")
        setup_docker_content_trust
        configure_docker_security
        ;;
    "network")
        setup_network_policies
        configure_firewall
        ;;
    "firewall")
        configure_firewall
        ;;
    "verify")
        verify_security
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        error "Unknown command: $1. Use 'help' for usage information."
        ;;
esac