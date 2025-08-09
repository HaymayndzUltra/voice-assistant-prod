#!/usr/bin/env python3
"""
Phase 2.3: MMA vs MMS Parity Test
Functional diff test that fires identical JSON RPC calls to MMA (tcp://localhost:5570) 
and MMS (tcp://localhost:7721) and compares results for success status and key presence.
"""

import zmq
from typing import Dict, Any, List

class ParityTester:
    def __init__(self, mma_port: int = 5570, mms_port: int = 7721):
        self.mma_port = mma_port
        self.mms_port = mms_port
        self.context = zmq.Context()
        
    def send_request(self, port: int, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON RPC request to specified port and return response"""
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
        
        try:
            socket.connect(f"tcp://localhost:{port}")
            socket.send_json(request)
            response = socket.recv_json()
            return response
        except zmq.ZMQError as e:
            return {"status": "error", "message": f"ZMQ Error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Request Error: {e}"}
        finally:
            socket.close()
    
    def compare_responses(self, mma_response: Dict[str, Any], mms_response: Dict[str, Any], test_name: str) -> Dict[str, Any]:
        """Compare MMA and MMS responses and return analysis"""
        comparison = {
            "test_name": test_name,
            "mma_response": mma_response,
            "mms_response": mms_response,
            "status_match": mma_response.get("status") == mms_response.get("status"),
            "success_both": mma_response.get("status") == "ok" and mms_response.get("status") == "ok",
            "errors": []
        }
        
        # Check for critical differences
        if not comparison["status_match"]:
            comparison["errors"].append(f"Status mismatch: MMA={mma_response.get('status')}, MMS={mms_response.get('status')}")
        
        # Check for missing keys in MMS that exist in MMA
        mma_keys = set(mma_response.keys())
        mms_keys = set(mms_response.keys())
        missing_in_mms = mma_keys - mms_keys
        if missing_in_mms:
            comparison["errors"].append(f"Keys missing in MMS: {missing_in_mms}")
        
        return comparison
    
    def run_parity_tests(self) -> List[Dict[str, Any]]:
        """Run all parity tests and return results"""
        test_cases = [
            {
                "name": "health_check",
                "request": {"action": "health_check"}
            },
            {
                "name": "generate_basic",
                "request": {
                    "action": "generate",
                    "prompt": "Hello, this is a test",
                    "max_tokens": 10
                }
            },
            {
                "name": "generate_with_model",
                "request": {
                    "action": "generate",
                    "prompt": "What is 2+2?",
                    "max_tokens": 20,
                    "model_pref": "phi-3-mini-gguf"
                }
            },
            {
                "name": "load_model",
                "request": {
                    "action": "load_model",
                    "model_name": "phi-3-mini-gguf"
                }
            },
            {
                "name": "unload_model",
                "request": {
                    "action": "unload_model",
                    "model_name": "phi-3-mini-gguf"
                }
            },
            {
                "name": "list_models",
                "request": {"action": "list_models"}
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n🔍 Testing: {test_case['name']}")
            
            # Send to MMA
            mma_response = self.send_request(self.mma_port, test_case["request"])
            print(f"MMA Response: {mma_response}")
            
            # Send to MMS
            mms_response = self.send_request(self.mms_port, test_case["request"])
            print(f"MMS Response: {mms_response}")
            
            # Compare
            comparison = self.compare_responses(mma_response, mms_response, test_case["name"])
            results.append(comparison)
            
            if comparison["errors"]:
                print(f"⚠️  Issues found: {comparison['errors']}")
            else:
                print(f"✅ Parity check passed")
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive parity report"""
        total_tests = len(results)
        successful_parity = sum(1 for r in results if not r["errors"])
        success_rate = (successful_parity / total_tests) * 100 if total_tests > 0 else 0
        
        all_errors = []
        for result in results:
            all_errors.extend(result["errors"])
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_parity": successful_parity,
                "success_rate_percent": success_rate,
                "total_errors": len(all_errors)
            },
            "detailed_results": results,
            "all_errors": all_errors,
            "recommendation": "PROCEED" if success_rate >= 99 else "FIX_ISSUES"
        }

def main():
    """Main parity test execution"""
    print("🚀 Starting MMA vs MMS Parity Test (Phase 2.3)")
    print("=" * 60)
    
    tester = ParityTester()
    
    try:
        # Run all parity tests
        results = tester.run_parity_tests()
        
        # Generate report
        report = tester.generate_report(results)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 PARITY TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Successful Parity: {report['summary']['successful_parity']}")
        print(f"Success Rate: {report['summary']['success_rate_percent']:.1f}%")
        print(f"Total Errors: {report['summary']['total_errors']}")
        
        if report['all_errors']:
            print(f"\n❌ ERRORS FOUND:")
            for error in report['all_errors']:
                print(f"  - {error}")
        
        print(f"\n🎯 RECOMMENDATION: {report['recommendation']}")
        
        if report['recommendation'] == "PROCEED":
            print("✅ Phase 2.3 COMPLETED - Ready for Phase 3")
        else:
            print("⚠️  Phase 2.3 NEEDS FIXES - Address errors before Phase 3")
        
        return report['recommendation'] == "PROCEED"
        
    except Exception as e:
        print(f"❌ Parity test failed: {e}")
        return False
    finally:
        tester.context.term()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 