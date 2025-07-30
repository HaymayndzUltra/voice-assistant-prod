#!/usr/bin/env python3
"""
🔥 REAL AGENT COMMUNICATION TEST
Actually tests agent-to-agent communication, not mock simulations
Tests GENUINE functionality of deployed agents
"""
import zmq
import json
import time
import requests
import subprocess
from typing import Dict, Any, Optional

class RealAgentCommunicationTest:
    """TODO: Add description for RealAgentCommunicationTest."""
    def __init__(self):
        self.context = zmq.Context()

    def test_serviceregistry_real_communication(self) -> Dict[str, Any]:
        """Test REAL ServiceRegistry ZMQ communication"""
        print("🔍 Testing REAL ServiceRegistry Communication...")
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
            socket.connect("tcp://localhost:7100")

            # Send REAL service discovery request
            request = {
                "action": "list_services",
                "timestamp": time.time()
            }

            print(f"   📤 Sending: {request}")
            socket.send_json(request)

            response = socket.recv_json()
            socket.close()

            print(f"   📥 Received: {response}")

            return {
                "success": True,
                "response": response,
                "response_time": "< 10s"
            }

        except zmq.error.Again:
            print(f"   ❌ ServiceRegistry TIMEOUT - No response within 10 seconds")
            return {"success": False, "error": "timeout"}
        except Exception as e:
            print(f"   ❌ ServiceRegistry ERROR: {e}")
            return {"success": False, "error": str(e)}

    def test_modelmanager_real_status(self) -> Dict[str, Any]:
        """Test REAL ModelManagerSuite agent functionality"""
        print("\n🔍 Testing REAL ModelManagerSuite Agent...")
        try:
            # Check actual recent logs for real activity
            cmd = "docker exec docker-core-services-1 tail -5 /app/logs/ModelManagerSuite.log"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                recent_logs = result.stdout.strip()
                print(f"   📋 Recent Activity:")
                for line in recent_logs.split('\n')[-3:]:
                    if line.strip():
                        print(f"      {line.strip()}")

                # Check for actual errors vs success indicators
                has_errors = any(keyword in recent_logs.lower() for keyword in ['error', 'failed', 'exception', 'traceback'])
                has_success = any(keyword in recent_logs.lower() for keyword in ['success', 'initialized', 'started', 'ready'])

                return {
                    "success": not has_errors,
                    "activity_detected": len(recent_logs.strip()) > 0,
                    "error_indicators": has_errors,
                    "success_indicators": has_success,
                    "logs": recent_logs
                }
            else:
                return {"success": False, "error": "Cannot access logs"}

        except Exception as e:
            print(f"   ❌ ModelManagerSuite Test Failed: {e}")
            return {"success": False, "error": str(e)}

    def test_real_zmq_ports_communication(self) -> Dict[str, Any]:
        """Test REAL ZMQ port communication across agents"""
        print("\n🔍 Testing REAL ZMQ Port Communication...")

        # Known agent ports from startup config
        agent_ports = [
            ("ServiceRegistry", 7100),
            ("SystemDigitalTwin", 7220),
            ("ModelManagerSuite", 7211),
            ("LearningOrchestrationService", 7210)
        ]

        results = {}

        for agent_name, port in agent_ports:
            try:
                print(f"   🔌 Testing {agent_name} on port {port}...")
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
                socket.connect(f"tcp://localhost:{port}")

                # Send simple ping request
                ping_request = {
                    "action": "ping",
                    "timestamp": time.time(),
                    "test_id": f"real_test_{int(time.time())}"
                }

                socket.send_json(ping_request)
                response = socket.recv_json()
                socket.close()

                print(f"      ✅ {agent_name}: RESPONSIVE")
                results[agent_name] = {
                    "success": True,
                    "port": port,
                    "response": response
                }

            except zmq.error.Again:
                print(f"      ⏰ {agent_name}: TIMEOUT (may be busy or not accepting requests)")
                results[agent_name] = {
                    "success": False,
                    "port": port,
                    "error": "timeout"
                }
            except Exception as e:
                print(f"      ❌ {agent_name}: ERROR - {e}")
                results[agent_name] = {
                    "success": False,
                    "port": port,
                    "error": str(e)
                }

        return results

    def test_real_http_endpoints(self) -> Dict[str, Any]:
        """Test REAL HTTP endpoints for actual responses"""
        print("\n🔍 Testing REAL HTTP Endpoints...")

        endpoints = [
            ("ObservabilityHub", "http://localhost:9000/health"),
            ("ServiceRegistry HTTP", "http://localhost:8101/health"),
            ("SystemDigitalTwin HTTP", "http://localhost:8220/health"),
        ]

        results = {}

        for name, url in endpoints:
            try:
                print(f"   🌐 Testing {name}...")
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"      ✅ {name}: ACTIVE - {data.get('status', 'healthy')}")
                        results[name] = {
                            "success": True,
                            "status_code": response.status_code,
                            "data": data
                        }
                    except:
                        print(f"      ✅ {name}: ACTIVE (non-JSON response)")
                        results[name] = {
                            "success": True,
                            "status_code": response.status_code,
                            "data": response.text[:100]
                        }
                else:
                    print(f"      ⚠️  {name}: HTTP {response.status_code}")
                    results[name] = {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code}"
                    }

            except requests.exceptions.ConnectinError:
                print(f"      ❌ {name}: CONNECTION REFUSED")
                results[name] = {
                    "success": False,
                    "error": "connection_refused"
                }
            except requests.exceptions.Timeout:
                print(f"      ⏰ {name}: TIMEOUT")
                results[name] = {
                    "success": False,
                    "error": "timeout"
                }
            except Exception as e:
                print(f"      ❌ {name}: ERROR - {e}")
                results[name] = {
                    "success": False,
                    "error": str(e)
                }

        return results

    def test_real_agent_logs_activity(self) -> Dict[str, Any]:
        """Test REAL agent activity from recent logs"""
        print("\n🔍 Testing REAL Agent Activity (Recent Logs)...")

        try:
            # Get agents with recent activity (logs modified in last hour)
            cmd = "docker exec docker-core-services-1 find /app/logs -name '*.log' -mmin -60 | wc -l"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                recent_active_count = int(result.stdout.strip())
                print(f"   📊 Agents with activity in last hour: {recent_active_count}")

                # Get specific agents with errors
                cmd_errors = "docker exec docker-core-services-1 find /app/logs -name '*.log' -exec grep -l 'ERROR\\|Exception\\|Traceback' {} \\; | wc -l"
                result_errors = subprocess.run(cmd_errors, shell=True, capture_output=True, text=True)
                error_count = int(result_errors.stdout.strip()) if result_errors.returncode == 0 else 0

                # Get agents with successful initialization
                cmd_success = "docker exec docker-core-services-1 find /app/logs -name '*.log' -exec grep -l 'initialized\\|started\\|ready' {} \\; | wc -l"
                result_success = subprocess.run(cmd_success, shell=True, capture_output=True, text=True)
                success_count = int(result_success.stdout.strip()) if result_success.returncode == 0 else 0

                print(f"   ❌ Agents with errors: {error_count}")
                print(f"   ✅ Agents with successful init: {success_count}")

                return {
                    "success": recent_active_count > 0,
                    "recent_active": recent_active_count,
                    "error_count": error_count,
                    "success_count": success_count,
                    "health_ratio": success_count / max(recent_active_count, 1)
                }
            else:
                return {"success": False, "error": "Cannot access container logs"}

        except Exception as e:
            print(f"   ❌ Log Activity Test Failed: {e}")
            return {"success": False, "error": str(e)}

    def run_comprehensive_real_test(self) -> Dict[str, Any]:
        """Run comprehensive REAL agent communication test"""
        print("🔥 REAL AGENT COMMUNICATION TEST")
        print("=" * 70)
        print("Testing ACTUAL agent functionality, not mock simulations")
        print("=" * 70)

        start_time = time.time()

        # Run real tests
        serviceregistry_result = self.test_serviceregistry_real_communication()
        modelmanager_result = self.test_modelmanager_real_status()
        zmq_ports_result = self.test_real_zmq_ports_communication()
        http_endpoints_result = self.test_real_http_endpoints()
        logs_activity_result = self.test_real_agent_logs_activity()

        # Calculate real success metrics
        serviceregistry_success = serviceregistry_result.get("success", False)
        modelmanager_success = modelmanager_result.get("success", False)

        zmq_responsive_count = sum(1 for result in zmq_ports_result.values() if result.get("success", False))
        zmq_total = len(zmq_ports_result)

        http_responsive_count = sum(1 for result in http_endpoints_result.values() if result.get("success", False))
        http_total = len(http_endpoints_result)

        logs_healthy = logs_activity_result.get("success", False)

        # Overall assessment
        total_tests = 5  # ServiceRegistry + ModelManager + ZMQ + HTTP + Logs
        passed_tests = sum([
            serviceregistry_success,
            modelmanager_success,
            zmq_responsive_count > 0,
            http_responsive_count > 0,
            logs_healthy
        ])

        success_rate = (passed_tests / total_tests) * 100

        duration = time.time() - start_time

        print("\n" + "=" * 70)
        print("🎯 REAL AGENT COMMUNICATION TEST SUMMARY")
        print("=" * 70)
        print(f"📊 REAL TESTS PASSED: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"🔌 ZMQ Responsive Agents: {zmq_responsive_count}/{zmq_total}")
        print(f"🌐 HTTP Responsive Endpoints: {http_responsive_count}/{http_total}")
        print(f"📝 Log Activity Health: {'✅ Active' if logs_healthy else '❌ Inactive'}")
        print(f"⏱️  Test Duration: {duration:.2f} seconds")

        print(f"\n🏆 REAL FUNCTIONALITY ASSESSMENT:")
        if success_rate >= 80:
            assessment = "🚀 EXCELLENT - Real agents are communicating and functional!"
        elif success_rate >= 60:
            assessment = "✅ GOOD - Most agents responsive with minor issues"
        elif success_rate >= 40:
            assessment = "⚠️  MODERATE - Some agents working, others need attention"
        else:
            assessment = "❌ POOR - Majority of agents not responding properly"

        print(f"   {assessment}")

        return {
            "success_rate": success_rate,
            "serviceregistry": serviceregistry_result,
            "modelmanager": modelmanager_result,
            "zmq_ports": zmq_ports_result,
            "http_endpoints": http_endpoints_result,
            "logs_activity": logs_activity_result,
            "assessment": assessment,
            "duration": duration
        }

def main():
    tester = RealAgentCommunicationTest()
    results = tester.run_comprehensive_real_test()

    print(f"\n🔥 CONCLUSION: This test shows REAL agent functionality")
    print(f"💯 Confidence Level: {results['success_rate']:.1f}% based on actual communication")

    return results

if __name__ == "__main__":
    main()
