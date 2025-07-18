#!/bin/bash
set -euo pipefail

# Health check script for Claude Code Usage Monitor Docker container
# This script performs comprehensive health checks to ensure the application is running correctly

# Exit codes
EXIT_OK=0
EXIT_WARNING=1
EXIT_CRITICAL=2
EXIT_UNKNOWN=3

# Color codes for output (only when TTY)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Configuration
TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
VERBOSE=${HEALTH_CHECK_VERBOSE:-false}
DATA_PATH=${CLAUDE_DATA_PATH:-/data}

# Logging functions
log_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1" >&2
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_success() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
    fi
}

# Health check functions
check_data_access() {
    log_info "Checking data directory access..."

    if [[ ! -d "$DATA_PATH" ]]; then
        log_error "Data directory does not exist: $DATA_PATH"
        return $EXIT_CRITICAL
    fi

    if [[ ! -r "$DATA_PATH" ]]; then
        log_error "Data directory is not readable: $DATA_PATH"
        return $EXIT_CRITICAL
    fi

    log_success "Data directory accessible"
    return $EXIT_OK
}

check_jsonl_files() {
    log_info "Checking for .jsonl files..."

    local jsonl_count
    jsonl_count=$(find "$DATA_PATH" -name "*.jsonl" -type f 2>/dev/null | wc -l)

    if [[ $jsonl_count -eq 0 ]]; then
        log_warn "No .jsonl files found in $DATA_PATH"
        return $EXIT_WARNING
    fi

    log_success "Found $jsonl_count .jsonl files"
    return $EXIT_OK
}

check_python_imports() {
    log_info "Checking Python module imports..."

    # Test critical imports
    local import_errors=0

    # Check claude_monitor import
    if ! python -c "import claude_monitor" 2>/dev/null; then
        log_error "Failed to import claude_monitor module"
        ((import_errors++))
    fi

    # Check api import
    if ! python -c "from claude_monitor.data.analysis import analyze_usage" 2>/dev/null; then
        log_error "Failed to import analyze_usage function"
        ((import_errors++))
    fi

    # Check dependencies
    if ! python -c "import rich" 2>/dev/null; then
        log_error "Failed to import rich module"
        ((import_errors++))
    fi

    if ! python -c "import pytz" 2>/dev/null; then
        log_error "Failed to import pytz module"
        ((import_errors++))
    fi

    if [[ $import_errors -gt 0 ]]; then
        log_error "$import_errors import(s) failed"
        return $EXIT_CRITICAL
    fi

    log_success "All Python imports successful"
    return $EXIT_OK
}

check_analysis_function() {
    log_info "Testing analysis function..."

    # Create a temporary test to ensure the analysis function works
    local test_result
    if test_result=$(timeout "$TIMEOUT" python -c "
from claude_monitor.data.analysis import analyze_usage
import json
try:
    result = analyze_usage()
    if isinstance(result, dict):
        print('SUCCESS')
    else:
        print('ERROR: Invalid result type')
        exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
" 2>&1); then
        if [[ "$test_result" == "SUCCESS" ]]; then
            log_success "Analysis function working correctly"
            return $EXIT_OK
        else
            log_error "Analysis function failed: $test_result"
            return $EXIT_CRITICAL
        fi
    else
        log_error "Analysis function timed out or failed: $test_result"
        return $EXIT_CRITICAL
    fi
}

check_file_permissions() {
    log_info "Checking file permissions..."

    local permission_errors=0

    # Check read access to .jsonl files
    while IFS= read -r -d '' file; do
        if [[ ! -r "$file" ]]; then
            log_warn "Cannot read file: $file"
            ((permission_errors++))
        fi
    done < <(find "$DATA_PATH" -name "*.jsonl" -type f -print0 2>/dev/null)

    if [[ $permission_errors -gt 0 ]]; then
        log_warn "$permission_errors file(s) have permission issues"
        return $EXIT_WARNING
    fi

    log_success "File permissions OK"
    return $EXIT_OK
}

check_environment_variables() {
    log_info "Checking environment variables..."

    local env_warnings=0

    # Check required environment variables
    if [[ -z "${CLAUDE_DATA_PATH:-}" ]]; then
        log_warn "CLAUDE_DATA_PATH not set"
        ((env_warnings++))
    fi

    # Check optional but important variables
    local important_vars=("CLAUDE_PLAN" "CLAUDE_TIMEZONE" "CLAUDE_THEME")
    for var in "${important_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_info "$var not set (using default)"
        fi
    done

    if [[ $env_warnings -gt 0 ]]; then
        log_warn "$env_warnings environment variable(s) missing"
        return $EXIT_WARNING
    fi

    log_success "Environment variables OK"
    return $EXIT_OK
}

check_disk_space() {
    log_info "Checking disk space..."

    # Check available space in data directory
    local available_kb
    available_kb=$(df "$DATA_PATH" | tail -1 | awk '{print $4}')
    local available_mb=$((available_kb / 1024))

    if [[ $available_mb -lt 100 ]]; then
        log_warn "Low disk space: ${available_mb}MB available"
        return $EXIT_WARNING
    fi

    log_success "Disk space OK (${available_mb}MB available)"
    return $EXIT_OK
}

# Performance monitoring
get_memory_usage() {
    local mem_kb
    mem_kb=$(ps -o rss= -p $$ 2>/dev/null || echo "0")
    local mem_mb=$((mem_kb / 1024))
    echo "${mem_mb}MB"
}

get_load_average() {
    cut -d' ' -f1 /proc/loadavg 2>/dev/null || echo "unknown"
}

# Main health check function
run_health_checks() {
    local overall_status=$EXIT_OK
    local checks_passed=0
    local checks_failed=0
    local checks_warned=0

    log_info "Starting health checks..."

    # Define checks to run
    local checks=(
        "check_data_access"
        "check_jsonl_files"
        "check_python_imports"
        "check_analysis_function"
        "check_file_permissions"
        "check_environment_variables"
        "check_disk_space"
    )

    # Run each check
    for check in "${checks[@]}"; do
        if $check; then
            case $? in
                "$EXIT_OK")
                    ((checks_passed++))
                    ;;
                "$EXIT_WARNING")
                    ((checks_warned++))
                    if [[ $overall_status -eq $EXIT_OK ]]; then
                        overall_status=$EXIT_WARNING
                    fi
                    ;;
                *)
                    ((checks_failed++))
                    overall_status=$EXIT_CRITICAL
                    ;;
            esac
        else
            ((checks_failed++))
            overall_status=$EXIT_CRITICAL
        fi
    done

    # Summary
    echo ""
    echo "Health Check Summary:"
    echo "  Passed: $checks_passed"
    echo "  Warnings: $checks_warned"
    echo "  Failed: $checks_failed"
    echo "  Memory Usage: $(get_memory_usage)"
    echo "  Load Average: $(get_load_average)"

    case $overall_status in
        "$EXIT_OK")
            echo -e "${GREEN}✅ All health checks passed${NC}"
            ;;
        "$EXIT_WARNING")
            echo -e "${YELLOW}⚠️  Health checks passed with warnings${NC}"
            ;;
        "$EXIT_CRITICAL")
            echo -e "${RED}❌ Health checks failed${NC}"
            ;;
    esac

    return $overall_status
}

# Help function
show_help() {
    cat << EOF
🏥 Claude Code Usage Monitor - Health Check Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --verbose       Enable verbose output
    --timeout SEC   Set timeout for tests (default: 10)
    --data-path     Override data path (default: /data)
    --help          Show this help

ENVIRONMENT VARIABLES:
    HEALTH_CHECK_VERBOSE    Enable verbose mode (true/false)
    HEALTH_CHECK_TIMEOUT    Timeout in seconds (default: 10)
    CLAUDE_DATA_PATH        Data directory path (default: /data)

EXIT CODES:
    0    All checks passed
    1    Checks passed with warnings
    2    Critical health check failed
    3    Unknown error

EXAMPLES:
    # Basic health check
    $0

    # Verbose health check
    $0 --verbose

    # Custom timeout
    $0 --timeout 30

    # Custom data path
    $0 --data-path /custom/data
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --data-path)
            DATA_PATH="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit $EXIT_UNKNOWN
            ;;
    esac
done

# Run health checks
run_health_checks
exit $?
