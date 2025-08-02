#!/usr/bin/env bash
# Goss Test Runner for P2: Basic Functionality Regression Suite
# Executes all Goss test suites and generates reports

set -euo pipefail

GOSS_VERSION="v0.4.4"
GOSS_BIN="/usr/local/bin/goss"
TEST_DIR="tests/goss"
REPORT_DIR="tests/goss/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== P2: Goss Regression Test Suite Runner ==="
echo "Timestamp: $(date)"

# Create reports directory
mkdir -p "$REPORT_DIR"

# Download and install Goss if not present
if [ ! -f "$GOSS_BIN" ]; then
    echo "Installing Goss $GOSS_VERSION..."
    curl -fsSL https://github.com/goss-org/goss/releases/download/${GOSS_VERSION}/goss-linux-amd64 -o "$GOSS_BIN"
    chmod +x "$GOSS_BIN"
    echo "✅ Goss installed"
fi

# Function to run a test suite
run_test_suite() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .yaml)
    
    echo "--- Running $test_name tests ---"
    
    # Run Goss test with JSON output for CI integration
    if $GOSS_BIN -g "$test_file" validate --format json > "$REPORT_DIR/${test_name}_${TIMESTAMP}.json"; then
        echo "✅ $test_name: PASSED"
        
        # Also generate human-readable output
        $GOSS_BIN -g "$test_file" validate --format tap > "$REPORT_DIR/${test_name}_${TIMESTAMP}.tap" || true
        
        return 0
    else
        echo "❌ $test_name: FAILED"
        
        # Generate detailed failure report
        $GOSS_BIN -g "$test_file" validate --format json > "$REPORT_DIR/${test_name}_${TIMESTAMP}_FAILED.json" || true
        $GOSS_BIN -g "$test_file" validate > "$REPORT_DIR/${test_name}_${TIMESTAMP}_FAILED.txt" || true
        
        return 1
    fi
}

# Test execution summary
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

echo "=== Executing Test Suites ==="

# Run all test suites
for test_file in "$TEST_DIR"/*.yaml; do
    if [ -f "$test_file" ]; then
        if run_test_suite "$test_file"; then
            ((TESTS_PASSED++))
        else
            ((TESTS_FAILED++))
            FAILED_TESTS+=($(basename "$test_file" .yaml))
        fi
        echo ""
    fi
done

# Generate comprehensive report
cat << EOF > "$REPORT_DIR/test_summary_${TIMESTAMP}.md"
# P2 Goss Regression Test Summary

**Execution Time**: $(date)
**Total Test Suites**: $((TESTS_PASSED + TESTS_FAILED))
**Passed**: $TESTS_PASSED
**Failed**: $TESTS_FAILED

## Test Results

### ✅ Passed Tests
$(for i in $(seq 1 $TESTS_PASSED); do echo "- Test Suite $i"; done)

### ❌ Failed Tests
$(for test in "${FAILED_TESTS[@]}"; do echo "- $test"; done)

## CI Integration Status
- JSON reports generated for CI parsing
- TAP format available for test frameworks
- Detailed failure logs available for debugging

## Next Steps
$(if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ All tests passed - Ready for P3 Performance Baseline"
else
    echo "⚠️ $TESTS_FAILED test suite(s) failed - Investigation required before proceeding"
fi)

EOF

echo "=== Test Execution Summary ==="
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ ALL TESTS PASSED - Ready for next phase"
    exit 0
else
    echo "❌ SOME TESTS FAILED - Check reports in $REPORT_DIR"
    echo "Failed test suites: ${FAILED_TESTS[*]}"
    exit 1
fi