#!/bin/bash
set -euo pipefail

# Docker entrypoint script for Claude Code Usage Monitor
# Provides initialization, validation, and graceful signal handling

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Signal handling for graceful shutdown
cleanup() {
    log_info "Received termination signal, shutting down gracefully..."
    # Kill any background processes if they exist
    jobs -p | xargs -r kill 2>/dev/null
    exit 0
}

# Set up signal traps
trap cleanup SIGTERM SIGINT SIGQUIT

# Validate required environment variables
validate_environment() {
    log_info "Validating environment configuration..."
    
    # Validate CLAUDE_DATA_PATH
    if [[ -z "${CLAUDE_DATA_PATH:-}" ]]; then
        log_error "CLAUDE_DATA_PATH environment variable is not set"
        exit 1
    fi
    
    if [[ ! -d "${CLAUDE_DATA_PATH}" ]]; then
        log_error "Data directory ${CLAUDE_DATA_PATH} does not exist or is not accessible"
        log_error "Please ensure you've mounted Claude data directory to /data"
        log_error "Example: docker run -v ~/.claude/projects:/data claude-monitor"
        exit 1
    fi
    
    # Check for .jsonl files
    if ! find "${CLAUDE_DATA_PATH}" -name "*.jsonl" -type f | head -1 | grep -q .; then
        log_warn "No .jsonl files found in ${CLAUDE_DATA_PATH}"
        log_warn "Make sure your Claude data directory contains usage data files"
    else
        local jsonl_count
        jsonl_count=$(find "${CLAUDE_DATA_PATH}" -name "*.jsonl" -type f | wc -l)
        log_success "Found ${jsonl_count} .jsonl files in data directory"
    fi
    
    # Validate CLAUDE_PLAN
    if [[ -n "${CLAUDE_PLAN:-}" ]]; then
        case "${CLAUDE_PLAN}" in
            pro|max5|max20|custom_max)
                log_info "Using Claude plan: ${CLAUDE_PLAN}"
                ;;
            *)
                log_warn "Invalid CLAUDE_PLAN '${CLAUDE_PLAN}', defaulting to 'pro'"
                export CLAUDE_PLAN="pro"
                ;;
        esac
    fi
    
    # Validate CLAUDE_THEME
    if [[ -n "${CLAUDE_THEME:-}" ]]; then
        case "${CLAUDE_THEME}" in
            light|dark|auto)
                log_info "Using theme: ${CLAUDE_THEME}"
                ;;
            *)
                log_warn "Invalid CLAUDE_THEME '${CLAUDE_THEME}', defaulting to 'auto'"
                export CLAUDE_THEME="auto"
                ;;
        esac
    fi
    
    # Validate CLAUDE_REFRESH_INTERVAL
    if [[ -n "${CLAUDE_REFRESH_INTERVAL:-}" ]]; then
        if ! [[ "${CLAUDE_REFRESH_INTERVAL}" =~ ^[0-9]+$ ]] || [[ "${CLAUDE_REFRESH_INTERVAL}" -lt 1 ]]; then
            log_warn "Invalid CLAUDE_REFRESH_INTERVAL '${CLAUDE_REFRESH_INTERVAL}', defaulting to 3"
            export CLAUDE_REFRESH_INTERVAL="3"
        fi
    fi
}

# Test application startup
test_application() {
    log_info "Testing application startup..."
    
    if python -c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print(f'✓ Analysis successful: {len(result.get(\"blocks\", []))} blocks found')" 2>/dev/null; then
        log_success "Application startup test passed"
    else
        log_error "Application startup test failed"
        log_error "Please check your data volume mount and Claude data files"
        exit 1
    fi
}

# Initialize configuration
initialize() {
    log_info "🐳 Claude Code Usage Monitor - Docker Container Starting"
    log_info "Version: 1.0.19"
    
    # Debug mode logging
    if [[ "${CLAUDE_DEBUG_MODE:-false}" == "true" ]]; then
        log_info "Debug mode enabled"
        log_info "Environment variables:"
        log_info "  CLAUDE_DATA_PATH=${CLAUDE_DATA_PATH:-unset}"
        log_info "  CLAUDE_PLAN=${CLAUDE_PLAN:-unset}"
        log_info "  CLAUDE_TIMEZONE=${CLAUDE_TIMEZONE:-unset}"
        log_info "  CLAUDE_THEME=${CLAUDE_THEME:-unset}"
        log_info "  CLAUDE_REFRESH_INTERVAL=${CLAUDE_REFRESH_INTERVAL:-unset}"
    fi
    
    validate_environment
    test_application
    
    log_success "Initialization complete"
}

# Build command line arguments from environment variables
build_args() {
    local args=()
    
    if [[ -n "${CLAUDE_PLAN:-}" ]]; then
        args+=("--plan" "${CLAUDE_PLAN}")
    fi
    
    if [[ -n "${CLAUDE_TIMEZONE:-}" ]]; then
        args+=("--timezone" "${CLAUDE_TIMEZONE}")
    fi
    
    if [[ -n "${CLAUDE_THEME:-}" ]]; then
        args+=("--theme" "${CLAUDE_THEME}")
    fi
    
    echo "${args[@]}"
}

# Main execution
main() {
    # Initialize container
    initialize
    
    # If no arguments provided, use default behavior
    if [[ $# -eq 0 ]]; then
        log_info "Starting Claude Code Usage Monitor..."
        
        # Build arguments from environment variables
        local cmd_args
        readarray -t cmd_args < <(build_args)
        cmd_args=($(build_args))
        
        if [[ "${CLAUDE_DEBUG_MODE:-false}" == "true" ]]; then
            log_info "Executing: python claude_monitor.py ${cmd_args[*]}"
        fi
        
        # Execute the main application with signal handling
        exec python claude_monitor.py "${cmd_args[@]}"
    else
        # Execute provided command
        log_info "Executing custom command: $*"
        exec "$@"
    fi
}

# Run main function with all arguments
main "$@"
