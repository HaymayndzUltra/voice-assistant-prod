#!/usr/bin/env python3
"""
Test MCP Memory Integration
Validates that memory MCP setup is working
"""

import json
import subprocess
import sys
from pathlib import Path

def test_mcp_bridge_directly():
    """Test MCP bridge directly"""
    print("🧪 Testing MCP Bridge Directly...")
    
    try:
        # Test the bridge in test mode
        result = subprocess.run([
            "python3", "memory_system/mcp_bridge.py", "--test"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print("✅ MCP Bridge test passed")
            print(f"  Output: {result.stdout}")
            return True
        else:
            print("❌ MCP Bridge test failed")
            print(f"  Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ MCP Bridge test error: {e}")
        return False

def test_mcp_json_requests():
    """Test MCP bridge with JSON requests"""
    print("\n🔄 Testing MCP JSON Interface...")
    
    # Test requests
    test_requests = [
        {"method": "memory/read_graph", "params": {}},
        {"method": "memory/search_nodes", "params": {"query": "session"}},
        {"method": "memory/create_entities", "params": {
            "entities": [{
                "name": "test_mcp_integration",
                "entityType": "test",
                "observations": ["Testing MCP integration", "JSON interface validation"]
            }]
        }}
    ]
    
    success_count = 0
    
    for i, request in enumerate(test_requests):
        try:
            # Start the bridge process
            process = subprocess.Popen([
                "python3", "memory_system/mcp_bridge.py"
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE, text=True, cwd=Path.cwd())
            
            # Send request
            request_json = json.dumps(request)
            stdout, stderr = process.communicate(input=request_json + "\n", timeout=5)
            
            if stdout:
                response = json.loads(stdout.strip())
                if "error" not in response:
                    print(f"  ✅ Request {i+1}: {request['method']} - Success")
                    success_count += 1
                else:
                    print(f"  ❌ Request {i+1}: {request['method']} - {response['error']}")
            else:
                print(f"  ❌ Request {i+1}: {request['method']} - No response")
            
        except Exception as e:
            print(f"  ❌ Request {i+1}: {request['method']} - {e}")
        finally:
            try:
                process.terminate()
            except:
                pass
    
    print(f"\n📊 JSON Interface Results: {success_count}/{len(test_requests)} passed")
    return success_count == len(test_requests)

def test_memory_integration():
    """Test memory system integration"""
    print("\n🧠 Testing Memory System Integration...")
    
    try:
        from unified_memory_access import unified_memory
        from cascade_memory_integration import check_memory, continue_from_memory
        
        # Test unified memory
        search_results = unified_memory.search("test", limit=3)
        print(f"  ✅ Unified memory search: {len(search_results)} results")
        
        # Test cascade integration
        memory_status = check_memory()
        print(f"  ✅ Cascade memory check: {memory_status['todo_count']} TODOs")
        
        # Test continuation
        continuation = continue_from_memory()
        can_continue = continuation['continuation_plan']['can_continue']
        print(f"  ✅ Session continuation: {'Available' if can_continue else 'Not available'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Memory integration error: {e}")
        return False

def check_memory_files():
    """Check memory system files"""
    print("\n📁 Checking Memory System Files...")
    
    required_files = [
        "memory.json",
        "unified_memory_access.py", 
        "cascade_memory_integration.py",
        "memory_system/mcp_bridge.py",
        "todo-tasks.json",
        "cursor_state.json"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def main():
    print("🧠 MCP Memory Integration Test Suite")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("File Check", check_memory_files),
        ("Memory Integration", test_memory_integration),  
        ("MCP Bridge Direct", test_mcp_bridge_directly),
        ("MCP JSON Interface", test_mcp_json_requests)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 TEST SUMMARY:")
    print("=" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED! MCP Memory setup is working!")
        print("\nNext steps:")
        print("1. Restart Cursor to pickup new memory.json configuration") 
        print("2. Try using MCP memory tools (mcp3_*) in Cursor")
        print("3. Use check_my_memory.py for session continuity")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
