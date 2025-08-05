import zmq
import json
from datetime import datetime

# PC2 Services with correct port numbers from SOT file
PC2_SERVICES = [
    # Phase 1 - Integration Layer Agents
    {"service_name": "TieredResponder", "port": 7100, "health_check_payload": {"action": "health_check"}},
    {"service_name": "AsyncProcessor", "port": 7101, "health_check_payload": {"action": "health_check"}},
    {"service_name": "CacheManager", "port": 7102, "health_check_payload": {"action": "health_check"}},
    {"service_name": "PerformanceMonitor", "port": 7103, "health_check_payload": {"action": "health_check"}},
    
    # Phase 2 - PC2-Specific Core Agents
    {"service_name": "DreamWorldAgent", "port": 7104, "health_check_payload": {"action": "health_check"}},
    {"service_name": "UnifiedMemoryReasoningAgent", "port": 7105, "health_check_payload": {"action": "health_check"}},
    {"service_name": "EpisodicMemoryAgent", "port": 7106, "health_check_payload": {"action": "health_check"}},
    {"service_name": "LearningAgent", "port": 7107, "health_check_payload": {"action": "health_check"}},
    {"service_name": "TutoringAgent", "port": 7108, "health_check_payload": {"action": "health_check"}},
    {"service_name": "KnowledgeBaseAgent", "port": 7109, "health_check_payload": {"action": "health_check"}},
    {"service_name": "MemoryManager", "port": 7110, "health_check_payload": {"action": "health_check"}},
    {"service_name": "ContextManager", "port": 7111, "health_check_payload": {"action": "health_check"}},
    {"service_name": "ExperienceTracker", "port": 7112, "health_check_payload": {"action": "health_check"}},
    {"service_name": "ResourceManager", "port": 7113, "health_check_payload": {"action": "health_check"}},
    {"service_name": "HealthMonitor", "port": 7114, "health_check_payload": {"action": "health_check"}},
    {"service_name": "TaskScheduler", "port": 7115, "health_check_payload": {"action": "health_check"}},
    
    # ForPC2 Agents
    {"service_name": "AuthenticationAgent", "port": 7116, "health_check_payload": {"action": "health_check"}},
    {"service_name": "UnifiedErrorAgent", "port": 7117, "health_check_payload": {"action": "health_check"}},
    {"service_name": "UnifiedUtilsAgent", "port": 7118, "health_check_payload": {"action": "health_check"}},
    {"service_name": "ProactiveContextMonitor", "port": 7119, "health_check_payload": {"action": "health_check"}},
    {"service_name": "SystemDigitalTwin", "port": 7120, "health_check_payload": {"action": "health_check"}},
    {"service_name": "RCAAgent", "port": 7121, "health_check_payload": {"action": "health_check"}},
    
    # Additional PC2 Core Agents
    {"service_name": "AgentTrustScorer", "port": 7122, "health_check_payload": {"action": "health_check"}},
    {"service_name": "FileSystemAssistantAgent", "port": 7123, "health_check_payload": {"action": "health_check"}},
    {"service_name": "RemoteConnectorAgent", "port": 7124, "health_check_payload": {"action": "health_check"}},
    {"service_name": "SelfHealingAgent", "port": 7125, "health_check_payload": {"action": "health_check"}},
    {"service_name": "UnifiedWebAgent", "port": 7126, "health_check_payload": {"action": "health_check"}},
    {"service_name": "DreamingModeAgent", "port": 7127, "health_check_payload": {"action": "health_check"}},
    {"service_name": "PerformanceLoggerAgent", "port": 7128, "health_check_payload": {"action": "health_check"}},
    {"service_name": "AdvancedRouter", "port": 7129, "health_check_payload": {"action": "health_check"}},
]

def check_service(service_info):
    """Check if a service is responding on its port."""
    name = service_info["service_name"]
    port = service_info["port"]
    payload = service_info["health_check_payload"]
    
    context = zmq.Context()
    sock = context.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
    sock.setsockopt(zmq.SNDTIMEO, 3000)
    
    try:
        addr = f"tcp://127.0.0.1:{port}"
        sock.connect(addr)
        sock.send_string(json.dumps(payload)
        
        try:
            resp = sock.recv_string()
            resp_json = json.loads(resp)
            
            if (resp_json.get("status") in ("ok", "success", "healthy") or 
                resp_json.get("service") or 
                resp_json.get("available") is not False):
                return {"Service Name": name, "Port": port, "Status": "[OK] Healthy", "Response": resp_json}
            else:
                return {"Service Name": name, "Port": port, "Status": "[WARN] Unhealthy", "Response": resp_json}
                
        except json.JSONDecodeError:
            return {"Service Name": name, "Port": port, "Status": "[WARN] Invalid JSON", "Response": resp}
            
    except zmq.error.Again:
        return {"Service Name": name, "Port": port, "Status": "[ERROR] Timeout", "Response": "No response within 3 seconds"}
    except Exception as e:
        return {"Service Name": name, "Port": port, "Status": "[ERROR] Error", "Response": str(e)}
    finally:
        sock.close()
        context.term()

def main():
    print(f"=== PC2 Services Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"Checking {len(PC2_SERVICES)} services...\n")
    
    results = []
    healthy_count = 0
    unhealthy_count = 0
    error_count = 0
    
    for service in PC2_SERVICES:
        result = check_service(service)
        results.append(result)
        
        # Print result immediately
        print(f"{result['Status']} {result['Service Name']} (Port {result['Port']})")
        
        # Count results
        if "Healthy" in result["Status"]:
            healthy_count += 1
        elif "Unhealthy" in result["Status"] or "Invalid JSON" in result["Status"]:
            unhealthy_count += 1
        else:
            error_count += 1
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pc2_healthcheck_results_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_services": len(PC2_SERVICES),
                "healthy": healthy_count,
                "unhealthy": unhealthy_count,
                "errors": error_count
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total Services: {len(PC2_SERVICES)}")
    print(f"[OK] Healthy: {healthy_count}")
    print(f"[WARN] Unhealthy: {unhealthy_count}")
    print(f"[ERROR] Errors: {error_count}")
    print(f"\nResults saved to: {filename}")
    
    if error_count > 0:
        print(f"\n[WARN] {error_count} services are not responding. You may need to start them first.")
        print("Use the system launcher or individual agent scripts to start the services.")

if __name__ == "__main__":
    main() 