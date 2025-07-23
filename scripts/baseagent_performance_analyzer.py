#!/usr/bin/env python3
"""
BaseAgent Performance Analysis Script
Phase 1 Week 2 Day 2 - Performance profiling and optimization analysis
"""

import os
import re
import time
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

def analyze_baseagent_init_patterns(file_path: str) -> Dict[str, Any]:
    """Analyze BaseAgent initialization patterns and potential bottlenecks"""
    if not os.path.exists(file_path):
        return {'status': 'FILE_NOT_FOUND', 'patterns': []}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        patterns = {}
        
        # Analyze initialization complexity
        init_method = re.search(r'def __init__\(self[^)]*\):(.*?)(?=def|\Z)', content, re.DOTALL)
        if init_method:
            init_content = init_method.group(1)
            
            # Count potential performance bottlenecks
            patterns['config_loads'] = len(re.findall(r'load_unified_config|Config\(\)\.get_config', init_content))
            patterns['file_operations'] = len(re.findall(r'open\(|Path\(.*\)\.exists|os\.path\.exists', init_content))
            patterns['zmq_contexts'] = len(re.findall(r'zmq\.Context|zmq\.Socket', init_content))
            patterns['imports_in_init'] = len(re.findall(r'import |from .* import', init_content))
            patterns['thread_creation'] = len(re.findall(r'threading\.Thread|Thread\(', init_content))
            patterns['subprocess_calls'] = len(re.findall(r'subprocess\.|Popen', init_content))
            patterns['network_calls'] = len(re.findall(r'requests\.|urllib|socket\.', init_content))
            patterns['database_ops'] = len(re.findall(r'sqlite3|redis|mongo|db\.', init_content))
            
            # Estimate initialization complexity
            complexity_score = (
                patterns['config_loads'] * 2 +
                patterns['file_operations'] * 1 +
                patterns['zmq_contexts'] * 3 +
                patterns['imports_in_init'] * 1 +
                patterns['thread_creation'] * 4 +
                patterns['subprocess_calls'] * 5 +
                patterns['network_calls'] * 3 +
                patterns['database_ops'] * 3
            )
            patterns['complexity_score'] = complexity_score
            
            # Categorize complexity
            if complexity_score <= 5:
                patterns['complexity_category'] = 'LOW'
            elif complexity_score <= 15:
                patterns['complexity_category'] = 'MEDIUM'
            else:
                patterns['complexity_category'] = 'HIGH'
        
        # Analyze configuration patterns
        config_patterns = []
        if 'load_unified_config' in content:
            config_patterns.append('UNIFIED_CONFIG')
        if 'Config().get_config()' in content:
            config_patterns.append('PC2_CONFIG')
        if 'yaml.load' in content or 'yaml.safe_load' in content:
            config_patterns.append('DIRECT_YAML')
        if 'json.load' in content:
            config_patterns.append('DIRECT_JSON')
        patterns['config_patterns'] = config_patterns
        
        # Analyze error handling patterns
        error_patterns = []
        if 'self.report_error' in content:
            error_patterns.append('BASEAGENT_ERROR')
        if 'error_bus_template' in content:
            error_patterns.append('LEGACY_ERROR_BUS')
        if 'logging.error' in content:
            error_patterns.append('DIRECT_LOGGING')
        if 'try:' in content and 'except:' in content:
            error_patterns.append('TRY_EXCEPT')
        patterns['error_patterns'] = error_patterns
        
        # Analyze ZMQ usage patterns
        zmq_patterns = []
        if 'zmq_pool' in content or 'get_req_socket' in content:
            zmq_patterns.append('POOLED_ZMQ')
        if 'zmq.Context()' in content:
            zmq_patterns.append('DIRECT_CONTEXT')
        if 'socket.connect' in content:
            zmq_patterns.append('MANUAL_CONNECT')
        patterns['zmq_patterns'] = zmq_patterns
        
        return {
            'status': 'ANALYZED',
            'patterns': patterns,
            'optimization_potential': 'HIGH' if complexity_score > 15 else 'MEDIUM' if complexity_score > 5 else 'LOW'
        }
        
    except Exception as e:
        return {'status': f'ERROR: {e}', 'patterns': {}}

def test_agent_startup_time(agent_path: str, iterations: int = 3) -> Dict[str, Any]:
    """Test agent startup time to identify performance baselines"""
    if not os.path.exists(agent_path):
        return {'status': 'FILE_NOT_FOUND', 'times': []}
    
    startup_times = []
    
    for i in range(iterations):
        start_time = time.time()
        
        # Test import time only (not full agent startup to avoid port conflicts)
        test_script = f'''
import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = "{Path(__file__).resolve().parent.parent}"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

start = time.time()
try:
    module_path = "{agent_path}".replace("/", ".").replace(".py", "")
    module = __import__(module_path, fromlist=[""])
    import_time = time.time() - start
    print(f"IMPORT_TIME: {{import_time:.4f}}")
except Exception as e:
    print(f"IMPORT_ERROR: {{e}}")
'''
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).resolve().parent.parent
            )
            
            if result.returncode == 0 and "IMPORT_TIME:" in result.stdout:
                import_time = float(result.stdout.split("IMPORT_TIME:")[1].strip())
                startup_times.append(import_time)
            else:
                startup_times.append(-1)  # Error indicator
                
        except subprocess.TimeoutExpired:
            startup_times.append(-2)  # Timeout indicator
        except Exception as e:
            startup_times.append(-3)  # Exception indicator
    
    valid_times = [t for t in startup_times if t > 0]
    
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        
        # Categorize performance
        if avg_time <= 0.5:
            performance_category = 'EXCELLENT'
        elif avg_time <= 1.0:
            performance_category = 'GOOD'
        elif avg_time <= 2.0:
            performance_category = 'ACCEPTABLE'
        else:
            performance_category = 'NEEDS_OPTIMIZATION'
            
        return {
            'status': 'SUCCESS',
            'times': startup_times,
            'valid_times': valid_times,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'performance_category': performance_category
        }
    else:
        return {
            'status': 'FAILED',
            'times': startup_times,
            'valid_times': [],
            'performance_category': 'ERROR'
        }

def main():
    """Main performance analysis function"""
    print("=" * 70)
    print("PHASE 1 WEEK 2 DAY 2 - BASEAGENT PERFORMANCE ANALYSIS")
    print("=" * 70)
    
    # Representative agents for performance analysis
    representative_agents = [
        # Core Services (Critical Performance)
        ('main_pc_code/agents/service_registry_agent.py', 'CORE_SERVICE'),
        ('main_pc_code/agents/request_coordinator.py', 'CORE_SERVICE'),
        ('main_pc_code/agents/unified_system_agent.py', 'CORE_SERVICE'),
        
        # Memory & Learning (Complex Initialization)
        ('main_pc_code/agents/memory_client.py', 'MEMORY_SERVICE'),
        ('main_pc_code/agents/learning_orchestration_service.py', 'LEARNING_SERVICE'),
        ('main_pc_code/agents/predictive_health_monitor.py', 'MONITORING_SERVICE'),
        
        # Audio/Video (Resource Intensive)
        ('main_pc_code/agents/face_recognition_agent.py', 'VISION_SERVICE'),
        ('main_pc_code/agents/streaming_audio_capture.py', 'AUDIO_SERVICE'),
        ('main_pc_code/agents/fused_audio_preprocessor.py', 'AUDIO_SERVICE'),
        
        # AI/ML (Model Loading)
        ('main_pc_code/agents/model_orchestrator.py', 'AI_SERVICE'),
        ('main_pc_code/agents/nlu_agent.py', 'AI_SERVICE'),
        ('main_pc_code/agents/emotion_engine.py', 'AI_SERVICE'),
        
        # PC2 Services (Cross-Machine)
        ('pc2_code/agents/memory_orchestrator_service.py', 'PC2_MEMORY'),
        ('pc2_code/agents/unified_web_agent.py', 'PC2_WEB'),
        ('pc2_code/agents/remote_connector_agent.py', 'PC2_CONNECTOR'),
    ]
    
    print(f"\n🔍 ANALYZING {len(representative_agents)} REPRESENTATIVE AGENTS:")
    print("-" * 70)
    
    performance_results = {}
    pattern_summary = {}
    
    for agent_path, category in representative_agents:
        agent_name = os.path.basename(agent_path)
        print(f"\n📊 Analyzing: {agent_name} ({category})")
        
        # Pattern analysis
        pattern_result = analyze_baseagent_init_patterns(agent_path)
        
        # Performance testing
        perf_result = test_agent_startup_time(agent_path)
        
        # Store results
        performance_results[agent_name] = {
            'category': category,
            'path': agent_path,
            'patterns': pattern_result,
            'performance': perf_result
        }
        
        # Print summary
        if pattern_result['status'] == 'ANALYZED':
            patterns = pattern_result['patterns']
            complexity = patterns.get('complexity_category', 'UNKNOWN')
            score = patterns.get('complexity_score', 0)
            print(f"  📈 Complexity: {complexity} (Score: {score})")
            print(f"  🔧 Config Loads: {patterns.get('config_loads', 0)}")
            print(f"  🧵 Thread Creation: {patterns.get('thread_creation', 0)}")
            print(f"  🌐 ZMQ Contexts: {patterns.get('zmq_contexts', 0)}")
        
        if perf_result['status'] == 'SUCCESS':
            avg_time = perf_result['avg_time']
            perf_cat = perf_result['performance_category']
            print(f"  ⚡ Startup Time: {avg_time:.4f}s ({perf_cat})")
        else:
            print(f"  ❌ Performance Test: {perf_result['status']}")
        
        # Update pattern summary
        if pattern_result['status'] == 'ANALYZED':
            for pattern_type, patterns_list in pattern_result['patterns'].items():
                if pattern_type not in pattern_summary:
                    pattern_summary[pattern_type] = {}
                if isinstance(patterns_list, list):
                    for pattern in patterns_list:
                        if pattern not in pattern_summary[pattern_type]:
                            pattern_summary[pattern_type][pattern] = []
                        pattern_summary[pattern_type][pattern].append(agent_name)
                elif isinstance(patterns_list, (int, str)):
                    if patterns_list not in pattern_summary[pattern_type]:
                        pattern_summary[pattern_type][patterns_list] = []
                    pattern_summary[pattern_type][patterns_list].append(agent_name)
    
    # Generate optimization recommendations
    print("\n" + "=" * 70)
    print("📊 PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 70)
    
    # Performance categorization
    excellent_agents = []
    good_agents = []
    acceptable_agents = []
    needs_optimization = []
    error_agents = []
    
    total_avg_time = 0
    valid_performance_count = 0
    
    for agent_name, results in performance_results.items():
        perf_result = results['performance']
        if perf_result['status'] == 'SUCCESS':
            category = perf_result['performance_category']
            avg_time = perf_result['avg_time']
            total_avg_time += avg_time
            valid_performance_count += 1
            
            if category == 'EXCELLENT':
                excellent_agents.append((agent_name, avg_time))
            elif category == 'GOOD':
                good_agents.append((agent_name, avg_time))
            elif category == 'ACCEPTABLE':
                acceptable_agents.append((agent_name, avg_time))
            elif category == 'NEEDS_OPTIMIZATION':
                needs_optimization.append((agent_name, avg_time))
        else:
            error_agents.append(agent_name)
    
    if valid_performance_count > 0:
        overall_avg = total_avg_time / valid_performance_count
        print(f"📈 Overall Average Startup Time: {overall_avg:.4f}s")
        print(f"🏆 Excellent Performance ({len(excellent_agents)}): {[a[0] for a in excellent_agents]}")
        print(f"✅ Good Performance ({len(good_agents)}): {[a[0] for a in good_agents]}")
        print(f"⚠️  Acceptable Performance ({len(acceptable_agents)}): {[a[0] for a in acceptable_agents]}")
        print(f"🔧 Needs Optimization ({len(needs_optimization)}): {[a[0] for a in needs_optimization]}")
    
    if error_agents:
        print(f"❌ Performance Test Errors ({len(error_agents)}): {error_agents}")
    
    # Pattern analysis summary
    print(f"\n🔍 CONFIGURATION PATTERN ANALYSIS:")
    config_patterns = pattern_summary.get('config_patterns', {})
    for pattern, agents in config_patterns.items():
        print(f"  {pattern}: {len(agents)} agents")
    
    print(f"\n🔍 ERROR HANDLING PATTERN ANALYSIS:")
    error_patterns = pattern_summary.get('error_patterns', {})
    for pattern, agents in error_patterns.items():
        print(f"  {pattern}: {len(agents)} agents")
    
    print(f"\n🔍 ZMQ USAGE PATTERN ANALYSIS:")
    zmq_patterns = pattern_summary.get('zmq_patterns', {})
    for pattern, agents in zmq_patterns.items():
        print(f"  {pattern}: {len(agents)} agents")
    
    # Optimization recommendations
    print(f"\n🎯 OPTIMIZATION RECOMMENDATIONS:")
    
    if needs_optimization:
        print(f"  🔧 HIGH PRIORITY: Optimize {len(needs_optimization)} slow-starting agents")
        for agent_name, avg_time in sorted(needs_optimization, key=lambda x: x[1], reverse=True):
            print(f"     - {agent_name}: {avg_time:.4f}s")
    
    if 'UNIFIED_CONFIG' in config_patterns and 'PC2_CONFIG' in config_patterns:
        unified_count = len(config_patterns['UNIFIED_CONFIG'])
        pc2_count = len(config_patterns['PC2_CONFIG'])
        print(f"  ⚙️  MEDIUM PRIORITY: Unify config patterns ({unified_count} UNIFIED, {pc2_count} PC2)")
    
    if 'DIRECT_CONTEXT' in zmq_patterns:
        direct_count = len(zmq_patterns['DIRECT_CONTEXT'])
        print(f"  🌐 MEDIUM PRIORITY: Optimize {direct_count} agents using direct ZMQ contexts")
    
    # Save detailed results
    results_file = "phase1_week2_day2_performance_analysis.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'baseagent_performance',
            'agents_analyzed': len(representative_agents),
            'performance_results': performance_results,
            'pattern_summary': pattern_summary,
            'optimization_recommendations': {
                'high_priority_agents': [a[0] for a in needs_optimization],
                'config_unification_needed': 'UNIFIED_CONFIG' in config_patterns and 'PC2_CONFIG' in config_patterns,
                'zmq_optimization_needed': 'DIRECT_CONTEXT' in zmq_patterns
            }
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    print("\n✅ Day 2 Task 1 Complete: BaseAgent Performance Analysis")
    
    return performance_results, pattern_summary

if __name__ == "__main__":
    main() 