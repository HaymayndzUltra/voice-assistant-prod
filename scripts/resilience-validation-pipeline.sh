#!/bin/bash
# AI System Resilience Validation Pipeline
# Automated chaos engineering and load testing for production readiness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHAOS_CONFIG="${CHAOS_CONFIG:-config/chaos/chaos-config.yaml}"
LOAD_CONFIG="${LOAD_CONFIG:-config/load-test/load-test-config.yaml}"
RESULTS_DIR="${RESULTS_DIR:-/tmp/resilience-validation}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

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

# Create results directory
create_results_dir() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    RESULTS_DIR="${RESULTS_DIR}_${timestamp}"
    mkdir -p "${RESULTS_DIR}"/{chaos,load,reports,metrics,screenshots}
    
    log "Results directory created: ${RESULTS_DIR}"
}

# Check system readiness
check_system_readiness() {
    log "Checking system readiness..."
    
    # Check if required services are running
    local required_services=(
        "prometheus"
        "grafana"
        "jaeger"
        "coordination"
        "memory-stack"
        "observability"
    )
    
    for service in "${required_services[@]}"; do
        if ! docker ps --format "table {{.Names}}" | grep -q "${service}"; then
            error "Required service ${service} is not running"
        fi
    done
    
    # Check if Prometheus is accessible
    if ! curl -s "${PROMETHEUS_URL}/api/v1/status/config" > /dev/null; then
        error "Prometheus is not accessible at ${PROMETHEUS_URL}"
    fi
    
    # Check if Grafana is accessible
    if ! curl -s "${GRAFANA_URL}/api/health" > /dev/null; then
        warn "Grafana is not accessible at ${GRAFANA_URL}"
    fi
    
    # Check GPU availability for MainPC
    if command -v nvidia-smi &> /dev/null; then
        if ! nvidia-smi &> /dev/null; then
            warn "NVIDIA GPU not available or driver issues"
        else
            info "GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)"
        fi
    fi
    
    log "System readiness check completed"
}

# Capture baseline metrics
capture_baseline_metrics() {
    log "Capturing baseline system metrics..."
    
    local baseline_file="${RESULTS_DIR}/metrics/baseline_metrics.json"
    
    # Collect baseline metrics from Prometheus
    local queries=(
        "node_memory_MemAvailable_bytes"
        "node_cpu_seconds_total"
        "nvidia_smi_utilization_gpu_ratio"
        "nvidia_smi_memory_used_bytes"
        "ai_system_slo_compliance"
        "ai_system_availability_percentage"
        "prometheus_tsdb_blocks_loaded"
    )
    
    echo "{" > "${baseline_file}"
    echo "  \"timestamp\": \"$(date -Iseconds)\"," >> "${baseline_file}"
    echo "  \"metrics\": {" >> "${baseline_file}"
    
    local first=true
    for query in "${queries[@]}"; do
        if [[ "$first" == false ]]; then
            echo "," >> "${baseline_file}"
        fi
        first=false
        
        local result=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${query}" | jq -r '.data.result[0].value[1] // "0"')
        echo "    \"${query}\": ${result}" >> "${baseline_file}"
    done
    
    echo "  }" >> "${baseline_file}"
    echo "}" >> "${baseline_file}"
    
    log "Baseline metrics captured: ${baseline_file}"
}

# Create Grafana snapshots
create_grafana_snapshots() {
    log "Creating Grafana dashboard snapshots..."
    
    local snapshot_dir="${RESULTS_DIR}/screenshots"
    
    # Dashboard URLs to capture
    local dashboards=(
        "d/ai-system-overview/ai-system-overview"
        "d/gpu-monitoring/gpu-monitoring"
        "d/slo-dashboard/slo-dashboard"
        "d/chaos-engineering/chaos-engineering"
    )
    
    for dashboard in "${dashboards[@]}"; do
        local dashboard_name=$(basename "${dashboard}")
        local snapshot_file="${snapshot_dir}/${dashboard_name}_$(date +%H%M%S).json"
        
        # Create snapshot via Grafana API
        local snapshot_response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -d '{"dashboard": {"id": null}, "expires": 3600}' \
            "${GRAFANA_URL}/api/snapshots" 2>/dev/null || echo '{"url": "unavailable"}')
        
        echo "${snapshot_response}" > "${snapshot_file}"
        
        info "Dashboard snapshot created: ${dashboard_name}"
    done
}

# Run load testing baseline
run_baseline_load_test() {
    log "Running baseline load test..."
    
    # Light load test to establish baseline performance
    python3 "${SCRIPT_DIR}/load-testing.py" \
        --pattern "constant" \
        --workload "conversation" \
        --service "coordination" \
        --max-users 10 \
        --duration 120 \
        --output "${RESULTS_DIR}/load/baseline_load_test.html" \
        > "${RESULTS_DIR}/load/baseline_load_test.log" 2>&1
    
    if [[ $? -eq 0 ]]; then
        log "Baseline load test completed successfully"
    else
        warn "Baseline load test encountered issues - continuing with validation"
    fi
}

# Execute chaos experiments
run_chaos_experiments() {
    log "Starting chaos engineering experiments..."
    
    local chaos_schedule="${SCRIPT_DIR}/../config/chaos/resilience-validation-schedule.yaml"
    
    # Create chaos schedule if it doesn't exist
    if [[ ! -f "${chaos_schedule}" ]]; then
        create_chaos_schedule "${chaos_schedule}"
    fi
    
    # Run chaos experiments
    python3 "${SCRIPT_DIR}/chaos-monkey.py" \
        --config "${CHAOS_CONFIG}" \
        --schedule "${chaos_schedule}" \
        > "${RESULTS_DIR}/chaos/chaos_experiments.log" 2>&1 &
    
    local chaos_pid=$!
    echo "${chaos_pid}" > "${RESULTS_DIR}/chaos/chaos_pid"
    
    log "Chaos experiments started (PID: ${chaos_pid})"
    
    # Monitor chaos experiments
    local chaos_duration=600  # 10 minutes
    local elapsed=0
    local interval=30
    
    while [[ $elapsed -lt $chaos_duration ]]; do
        if ! kill -0 "${chaos_pid}" 2>/dev/null; then
            log "Chaos experiments completed"
            break
        fi
        
        # Collect metrics during chaos
        collect_chaos_metrics "${elapsed}"
        
        sleep "${interval}"
        elapsed=$((elapsed + interval))
    done
    
    # Ensure chaos experiments are stopped
    if kill -0 "${chaos_pid}" 2>/dev/null; then
        warn "Stopping long-running chaos experiments"
        kill "${chaos_pid}"
    fi
}

# Create chaos experiment schedule
create_chaos_schedule() {
    local schedule_file="$1"
    
    cat > "${schedule_file}" << 'EOF'
experiments:
  - name: "coordination_latency_injection"
    type: "latency_injection"
    target: "coordination"
    duration: 60
    intensity: 0.3
    parameters:
      latency_ms: 500
    steady_state_hypothesis:
      checks:
        - metric: "ai_system_availability_percentage{service='coordination'}"
          threshold: 95
          operator: "gt"
    wait_after: 30

  - name: "memory_stack_error_injection"
    type: "error_injection"
    target: "memory-stack"
    duration: 45
    intensity: 0.1
    wait_after: 30

  - name: "vision_gpu_resource_exhaustion"
    type: "resource_exhaustion"
    target: "vision-gpu"
    duration: 90
    intensity: 0.7
    parameters:
      resource_type: "gpu"
    wait_after: 60

  - name: "network_partition_coordination_memory"
    type: "network_partition"
    target: "coordination"
    duration: 30
    parameters:
      targets: ["coordination", "memory-stack"]
    wait_after: 45

  - name: "redis_dependency_failure"
    type: "dependency_failure"
    target: "memory-stack"
    duration: 60
    parameters:
      dependency: "redis"
    wait_after: 30
EOF
    
    log "Chaos schedule created: ${schedule_file}"
}

# Collect metrics during chaos experiments
collect_chaos_metrics() {
    local elapsed_time=$1
    local metrics_file="${RESULTS_DIR}/metrics/chaos_metrics_${elapsed_time}s.json"
    
    # Enhanced metrics collection during chaos
    local chaos_queries=(
        "ai_system_slo_compliance"
        "ai_system_slo_error_budget_remaining"
        "ai_system_availability_percentage"
        "ai_system_response_time_p99_seconds"
        "nvidia_smi_utilization_gpu_ratio"
        "rate(ai_request_count[1m])"
        "rate(prometheus_rule_evaluation_failures_total[1m])"
        "up{job='ai-system'}"
    )
    
    echo "{" > "${metrics_file}"
    echo "  \"timestamp\": \"$(date -Iseconds)\"," >> "${metrics_file}"
    echo "  \"elapsed_time\": ${elapsed_time}," >> "${metrics_file}"
    echo "  \"metrics\": {" >> "${metrics_file}"
    
    local first=true
    for query in "${chaos_queries[@]}"; do
        if [[ "$first" == false ]]; then
            echo "," >> "${metrics_file}"
        fi
        first=false
        
        local result=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${query}" | jq -r '.data.result[] | {metric: .metric, value: .value[1]}' | jq -s .)
        echo "    \"${query}\": ${result}" >> "${metrics_file}"
    done
    
    echo "  }" >> "${metrics_file}"
    echo "}" >> "${metrics_file}"
}

# Run stress load testing
run_stress_load_testing() {
    log "Running stress load testing..."
    
    local load_tests=(
        "vision_spike_test:vision_inference:spike:vision-gpu:100:300"
        "conversation_ramp_test:conversation:ramp_up:coordination:200:600"
        "memory_burst_test:memory_retrieval:burst:memory-stack:150:450"
        "cross_system_test:mixed:sine_wave:coordination:75:900"
    )
    
    for test_config in "${load_tests[@]}"; do
        IFS=':' read -ra TEST_PARAMS <<< "${test_config}"
        local test_name="${TEST_PARAMS[0]}"
        local workload="${TEST_PARAMS[1]}"
        local pattern="${TEST_PARAMS[2]}"
        local service="${TEST_PARAMS[3]}"
        local max_users="${TEST_PARAMS[4]}"
        local duration="${TEST_PARAMS[5]}"
        
        log "Running load test: ${test_name}"
        
        python3 "${SCRIPT_DIR}/load-testing.py" \
            --pattern "${pattern}" \
            --workload "${workload}" \
            --service "${service}" \
            --max-users "${max_users}" \
            --duration "${duration}" \
            --output "${RESULTS_DIR}/load/${test_name}.html" \
            > "${RESULTS_DIR}/load/${test_name}.log" 2>&1 &
        
        local load_pid=$!
        echo "${load_pid}" > "${RESULTS_DIR}/load/${test_name}_pid"
        
        # Monitor test progress
        local test_elapsed=0
        local monitor_interval=30
        
        while [[ $test_elapsed -lt $duration ]]; do
            if ! kill -0 "${load_pid}" 2>/dev/null; then
                break
            fi
            
            # Check system health during load test
            check_system_health_during_test "${test_name}" "${test_elapsed}"
            
            sleep "${monitor_interval}"
            test_elapsed=$((test_elapsed + monitor_interval))
        done
        
        # Wait for test completion
        wait "${load_pid}" 2>/dev/null || true
        
        log "Load test completed: ${test_name}"
        
        # Recovery period between tests
        info "Recovery period: 60 seconds"
        sleep 60
    done
}

# Check system health during testing
check_system_health_during_test() {
    local test_name="$1"
    local elapsed="$2"
    local health_file="${RESULTS_DIR}/metrics/${test_name}_health_${elapsed}s.json"
    
    # Check critical SLOs and system stability
    local health_checks=(
        "ai_system_slo_compliance"
        "ai_system_availability_percentage"
        "up{job='ai-system'}"
        "nvidia_smi_utilization_gpu_ratio"
    )
    
    local critical_violations=0
    
    echo "{" > "${health_file}"
    echo "  \"test_name\": \"${test_name}\"," >> "${health_file}"
    echo "  \"elapsed_time\": ${elapsed}," >> "${health_file}"
    echo "  \"timestamp\": \"$(date -Iseconds)\"," >> "${health_file}"
    echo "  \"health_status\": {" >> "${health_file}"
    
    local first=true
    for check in "${health_checks[@]}"; do
        if [[ "$first" == false ]]; then
            echo "," >> "${health_file}"
        fi
        first=false
        
        local value=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${check}" | jq -r '.data.result[0].value[1] // "0"')
        echo "    \"${check}\": ${value}" >> "${health_file}"
        
        # Check critical thresholds
        if [[ "${check}" == "ai_system_slo_compliance" ]] && (( $(echo "${value} < 90" | bc -l) )); then
            critical_violations=$((critical_violations + 1))
            warn "Critical SLO violation detected: ${check} = ${value}"
        fi
    done
    
    echo "  }," >> "${health_file}"
    echo "  \"critical_violations\": ${critical_violations}" >> "${health_file}"
    echo "}" >> "${health_file}"
    
    # Emergency stop if too many violations
    if [[ $critical_violations -gt 2 ]]; then
        error "Too many critical violations detected - stopping test"
    fi
}

# Analyze results and generate reports
analyze_results() {
    log "Analyzing resilience validation results..."
    
    local report_file="${RESULTS_DIR}/reports/resilience_validation_report.html"
    local summary_file="${RESULTS_DIR}/reports/executive_summary.json"
    
    # Analyze chaos experiment results
    local chaos_success_rate=$(analyze_chaos_results)
    
    # Analyze load test results
    local load_test_success_rate=$(analyze_load_test_results)
    
    # Calculate overall resilience score
    local resilience_score=$(calculate_resilience_score "${chaos_success_rate}" "${load_test_success_rate}")
    
    # Generate executive summary
    generate_executive_summary "${summary_file}" "${resilience_score}" "${chaos_success_rate}" "${load_test_success_rate}"
    
    # Generate detailed HTML report
    generate_detailed_report "${report_file}" "${summary_file}"
    
    log "Analysis completed - Report: ${report_file}"
}

# Analyze chaos experiment results
analyze_chaos_results() {
    local chaos_log="${RESULTS_DIR}/chaos/chaos_experiments.log"
    local successful_experiments=0
    local total_experiments=0
    
    if [[ -f "${chaos_log}" ]]; then
        total_experiments=$(grep -c "Starting chaos experiment" "${chaos_log}" 2>/dev/null || echo "0")
        successful_experiments=$(grep -c "completed with status: completed" "${chaos_log}" 2>/dev/null || echo "0")
    fi
    
    if [[ $total_experiments -gt 0 ]]; then
        echo "scale=2; ${successful_experiments} * 100 / ${total_experiments}" | bc
    else
        echo "0"
    fi
}

# Analyze load test results
analyze_load_test_results() {
    local load_dir="${RESULTS_DIR}/load"
    local successful_tests=0
    local total_tests=0
    
    for log_file in "${load_dir}"/*.log; do
        if [[ -f "${log_file}" ]]; then
            total_tests=$((total_tests + 1))
            if grep -q "Load test completed.*Success: True" "${log_file}" 2>/dev/null; then
                successful_tests=$((successful_tests + 1))
            fi
        fi
    done
    
    if [[ $total_tests -gt 0 ]]; then
        echo "scale=2; ${successful_tests} * 100 / ${total_tests}" | bc
    else
        echo "0"
    fi
}

# Calculate overall resilience score
calculate_resilience_score() {
    local chaos_success="$1"
    local load_success="$2"
    
    # Weighted average: 60% chaos, 40% load testing
    echo "scale=2; (${chaos_success} * 0.6) + (${load_success} * 0.4)" | bc
}

# Generate executive summary
generate_executive_summary() {
    local summary_file="$1"
    local resilience_score="$2"
    local chaos_success="$3"
    local load_success="$4"
    
    cat > "${summary_file}" << EOF
{
  "validation_timestamp": "$(date -Iseconds)",
  "resilience_score": ${resilience_score},
  "chaos_engineering": {
    "success_rate": ${chaos_success},
    "status": "$(if (( $(echo "${chaos_success} >= 80" | bc -l) )); then echo "PASS"; else echo "FAIL"; fi)"
  },
  "load_testing": {
    "success_rate": ${load_success},
    "status": "$(if (( $(echo "${load_success} >= 85" | bc -l) )); then echo "PASS"; else echo "FAIL"; fi)"
  },
  "overall_status": "$(if (( $(echo "${resilience_score} >= 80" | bc -l) )); then echo "PRODUCTION_READY"; else echo "NEEDS_IMPROVEMENT"; fi)",
  "recommendations": $(generate_recommendations "${resilience_score}" "${chaos_success}" "${load_success}"),
  "artifacts": {
    "detailed_report": "reports/resilience_validation_report.html",
    "metrics_directory": "metrics/",
    "chaos_logs": "chaos/",
    "load_test_results": "load/"
  }
}
EOF
}

# Generate recommendations
generate_recommendations() {
    local resilience_score="$1"
    local chaos_success="$2"
    local load_success="$3"
    
    local recommendations='[]'
    
    if (( $(echo "${chaos_success} < 80" | bc -l) )); then
        recommendations=$(echo "${recommendations}" | jq '. + ["Improve failure recovery mechanisms - chaos engineering success rate below 80%"]')
    fi
    
    if (( $(echo "${load_success} < 85" | bc -l) )); then
        recommendations=$(echo "${recommendations}" | jq '. + ["Optimize performance under load - load testing success rate below 85%"]')
    fi
    
    if (( $(echo "${resilience_score} < 70" | bc -l) )); then
        recommendations=$(echo "${recommendations}" | jq '. + ["Critical: System requires significant resilience improvements before production deployment"]')
    elif (( $(echo "${resilience_score} < 80" | bc -l) )); then
        recommendations=$(echo "${recommendations}" | jq '. + ["Moderate: Address identified weaknesses for optimal production readiness"]')
    else
        recommendations=$(echo "${recommendations}" | jq '. + ["System demonstrates strong resilience characteristics for production deployment"]')
    fi
    
    echo "${recommendations}"
}

# Generate detailed HTML report
generate_detailed_report() {
    local report_file="$1"
    local summary_file="$2"
    
    local resilience_score=$(jq -r '.resilience_score' "${summary_file}")
    local overall_status=$(jq -r '.overall_status' "${summary_file}")
    
    cat > "${report_file}" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>AI System Resilience Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .score { font-size: 48px; font-weight: bold; color: $(if (( $(echo "${resilience_score} >= 80" | bc -l) )); then echo "#4CAF50"; else echo "#f44336"; fi); }
        .status { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
        .pass { border-color: #4CAF50; background-color: #f1f8e9; }
        .fail { border-color: #f44336; background-color: #ffebee; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI System Resilience Validation Report</h1>
        <div class="score">${resilience_score}%</div>
        <div class="status">${overall_status}</div>
        <p>Generated: $(date)</p>
    </div>
    
    <div class="section $(if [[ "${overall_status}" == "PRODUCTION_READY" ]]; then echo "pass"; else echo "fail"; fi)">
        <h2>Executive Summary</h2>
        <p>The AI System underwent comprehensive resilience validation including chaos engineering and load testing.</p>
        
        <h3>Test Results</h3>
        <table>
            <tr>
                <th>Test Category</th>
                <th>Success Rate</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Chaos Engineering</td>
                <td>$(jq -r '.chaos_engineering.success_rate' "${summary_file}")%</td>
                <td>$(jq -r '.chaos_engineering.status' "${summary_file}")</td>
            </tr>
            <tr>
                <td>Load Testing</td>
                <td>$(jq -r '.load_testing.success_rate' "${summary_file}")%</td>
                <td>$(jq -r '.load_testing.status' "${summary_file}")</td>
            </tr>
        </table>
        
        <h3>Recommendations</h3>
        <ul>
$(jq -r '.recommendations[] | "            <li>" + . + "</li>"' "${summary_file}")
        </ul>
    </div>
    
    <div class="section">
        <h2>Artifacts</h2>
        <ul>
            <li><a href="../metrics/">System Metrics</a></li>
            <li><a href="../chaos/">Chaos Engineering Logs</a></li>
            <li><a href="../load/">Load Test Results</a></li>
            <li><a href="../screenshots/">Dashboard Snapshots</a></li>
        </ul>
    </div>
</body>
</html>
EOF
    
    log "Detailed report generated: ${report_file}"
}

# Cleanup function
cleanup() {
    log "Performing cleanup..."
    
    # Stop any running chaos experiments
    if [[ -f "${RESULTS_DIR}/chaos/chaos_pid" ]]; then
        local chaos_pid=$(cat "${RESULTS_DIR}/chaos/chaos_pid")
        if kill -0 "${chaos_pid}" 2>/dev/null; then
            kill "${chaos_pid}"
            log "Stopped chaos experiments"
        fi
    fi
    
    # Stop any running load tests
    for pid_file in "${RESULTS_DIR}"/load/*_pid; do
        if [[ -f "${pid_file}" ]]; then
            local load_pid=$(cat "${pid_file}")
            if kill -0 "${load_pid}" 2>/dev/null; then
                kill "${load_pid}"
                log "Stopped load test (PID: ${load_pid})"
            fi
        fi
    done
    
    # Emergency stop chaos monkey
    python3 "${SCRIPT_DIR}/chaos-monkey.py" --emergency-stop || true
    
    log "Cleanup completed"
}

# Main execution
main() {
    log "Starting AI System Resilience Validation Pipeline"
    
    # Set up signal handlers for cleanup
    trap cleanup EXIT INT TERM
    
    # Create results directory
    create_results_dir
    
    # Check system readiness
    check_system_readiness
    
    # Capture baseline state
    capture_baseline_metrics
    create_grafana_snapshots
    
    # Run baseline load test
    run_baseline_load_test
    
    # Execute chaos engineering experiments
    run_chaos_experiments
    
    # Run comprehensive load testing
    run_stress_load_testing
    
    # Wait for system to stabilize
    log "Waiting for system stabilization..."
    sleep 120
    
    # Analyze results and generate reports
    analyze_results
    
    log "Resilience validation pipeline completed successfully"
    log "Results available in: ${RESULTS_DIR}"
    
    # Print summary
    local summary_file="${RESULTS_DIR}/reports/executive_summary.json"
    if [[ -f "${summary_file}" ]]; then
        local overall_status=$(jq -r '.overall_status' "${summary_file}")
        local resilience_score=$(jq -r '.resilience_score' "${summary_file}")
        
        echo ""
        echo "=================================="
        echo "RESILIENCE VALIDATION SUMMARY"
        echo "=================================="
        echo "Overall Status: ${overall_status}"
        echo "Resilience Score: ${resilience_score}%"
        echo "Report: ${RESULTS_DIR}/reports/resilience_validation_report.html"
        echo "=================================="
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --chaos-config FILE     Chaos configuration file (default: config/chaos/chaos-config.yaml)
    --load-config FILE      Load test configuration file (default: config/load-test/load-test-config.yaml)
    --results-dir DIR       Results directory (default: /tmp/resilience-validation)
    --prometheus-url URL    Prometheus URL (default: http://localhost:9090)
    --grafana-url URL       Grafana URL (default: http://localhost:3000)
    --help                  Show this help message

Environment Variables:
    CHAOS_CONFIG           Chaos configuration file path
    LOAD_CONFIG            Load test configuration file path
    RESULTS_DIR            Results directory path
    PROMETHEUS_URL         Prometheus server URL
    GRAFANA_URL            Grafana server URL

Examples:
    $0                                          # Run with defaults
    $0 --results-dir /home/user/validation     # Custom results directory
    $0 --chaos-config custom-chaos.yaml        # Custom chaos configuration
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --chaos-config)
            CHAOS_CONFIG="$2"
            shift 2
            ;;
        --load-config)
            LOAD_CONFIG="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --prometheus-url)
            PROMETHEUS_URL="$2"
            shift 2
            ;;
        --grafana-url)
            GRAFANA_URL="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Check dependencies
if ! command -v jq &> /dev/null; then
    error "jq is required but not installed"
fi

if ! command -v bc &> /dev/null; then
    error "bc is required but not installed"
fi

if ! command -v curl &> /dev/null; then
    error "curl is required but not installed"
fi

# Run the main pipeline
main "$@"