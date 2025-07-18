#!/bin/bash
set -euo pipefail

# Volume initialization script for Claude Code Usage Monitor
# This script helps set up and validate Docker volumes for Claude data

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

# Help function
show_help() {
    cat << EOF
🐳 Claude Code Usage Monitor - Volume Initialization Script

This script helps you set up and validate Docker volumes for Claude data.

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    validate    Validate existing volume setup
    init        Initialize volume with sample data (for testing)
    info        Show information about volume setup
    help        Show this help message

OPTIONS:
    --data-path PATH    Path to Claude data directory (default: ~/.claude/projects)
    --container-path    Path inside container (default: /data)
    --check-only        Only check, don't make changes

EXAMPLES:
    # Validate default setup
    $0 validate

    # Validate custom path
    $0 validate --data-path /custom/claude/data

    # Show volume information
    $0 info

    # Initialize test data
    $0 init --data-path ./test-data

EOF
}

# Default values
DATA_PATH="$HOME/.claude/projects"
CONTAINER_PATH="/data"
CHECK_ONLY=false
COMMAND=""

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            validate|init|info|help)
                COMMAND="$1"
                shift
                ;;
            --data-path)
                DATA_PATH="$2"
                shift 2
                ;;
            --container-path)
                CONTAINER_PATH="$2"
                shift 2
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
}

# Validate volume setup
validate_volume() {
    log_info "Validating volume setup..."
    log_info "Data path: $DATA_PATH"
    log_info "Container path: $CONTAINER_PATH"
    
    # Check if data path exists
    if [[ ! -d "$DATA_PATH" ]]; then
        log_error "Data directory does not exist: $DATA_PATH"
        return 1
    fi
    
    # Check permissions
    if [[ ! -r "$DATA_PATH" ]]; then
        log_error "Data directory is not readable: $DATA_PATH"
        return 1
    fi
    
    # Count .jsonl files
    local jsonl_count
    jsonl_count=$(find "$DATA_PATH" -name "*.jsonl" -type f 2>/dev/null | wc -l)
    
    if [[ $jsonl_count -eq 0 ]]; then
        log_warn "No .jsonl files found in $DATA_PATH"
        log_warn "Make sure your Claude data directory contains usage data files"
        return 2
    else
        log_success "Found $jsonl_count .jsonl files in data directory"
    fi
    
    # Check file readability
    local readable_count=0
    while IFS= read -r -d '' file; do
        if [[ -r "$file" ]]; then
            ((readable_count++))
        fi
    done < <(find "$DATA_PATH" -name "*.jsonl" -type f -print0 2>/dev/null)
    
    if [[ $readable_count -lt $jsonl_count ]]; then
        log_warn "Some .jsonl files are not readable"
    else
        log_success "All .jsonl files are readable"
    fi
    
    # Show example Docker command
    log_info ""
    log_info "Docker command for this setup:"
    echo "docker run -it --rm -v \"$DATA_PATH:$CONTAINER_PATH:ro\" claude-monitor"
    
    return 0
}

# Show volume information
show_info() {
    log_info "Volume Setup Information"
    echo ""
    echo "Data Path Configuration:"
    echo "  Local path: $DATA_PATH"
    echo "  Container path: $CONTAINER_PATH"
    echo ""
    
    # Check if path exists
    if [[ -d "$DATA_PATH" ]]; then
        echo "Directory Status:"
        echo "  Exists: ✅ Yes"
        echo "  Readable: $([ -r "$DATA_PATH" ] && echo "✅ Yes" || echo "❌ No")"
        echo "  Size: $(du -sh "$DATA_PATH" 2>/dev/null | cut -f1 || echo "Unknown")"
        
        local jsonl_count
        jsonl_count=$(find "$DATA_PATH" -name "*.jsonl" -type f 2>/dev/null | wc -l)
        echo "  .jsonl files: $jsonl_count"
        
        if [[ $jsonl_count -gt 0 ]]; then
            echo ""
            echo "Recent files (last 5):"
            find "$DATA_PATH" -name "*.jsonl" -type f -printf '%T@ %p\n' 2>/dev/null | \
                sort -rn | head -5 | cut -d' ' -f2- | \
                while read -r file; do
                    echo "    $(basename "$file")"
                done
        fi
    else
        echo "Directory Status:"
        echo "  Exists: ❌ No"
    fi
    
    echo ""
    echo "Docker Commands:"
    echo "  Basic run:"
    echo "    docker run -it --rm -v \"$DATA_PATH:$CONTAINER_PATH:ro\" claude-monitor"
    echo ""
    echo "  With environment variables:"
    echo "    docker run -it --rm \\"
    echo "      -v \"$DATA_PATH:$CONTAINER_PATH:ro\" \\"
    echo "      -e CLAUDE_PLAN=max5 \\"
    echo "      -e CLAUDE_TIMEZONE=UTC \\"
    echo "      claude-monitor"
    echo ""
    echo "  Using Makefile:"
    echo "    CLAUDE_DATA_PATH=\"$DATA_PATH\" make run"
}

# Initialize test data (for development/testing)
init_test_data() {
    if [[ "$CHECK_ONLY" == "true" ]]; then
        log_info "Check-only mode: would create test data in $DATA_PATH"
        return 0
    fi
    
    log_info "Initializing test data in $DATA_PATH"
    
    # Create directory if it doesn't exist
    if [[ ! -d "$DATA_PATH" ]]; then
        log_info "Creating directory: $DATA_PATH"
        mkdir -p "$DATA_PATH"
    fi
    
    # Create a sample .jsonl file for testing
    local test_file
    test_file="$DATA_PATH/test-usage-$(date +%Y%m%d).jsonl"
    
    if [[ -f "$test_file" ]]; then
        log_warn "Test file already exists: $test_file"
    else
        log_info "Creating test file: $test_file"
        cat > "$test_file" << 'EOF'
{"timestamp": "2024-01-15T10:30:00Z", "model": "claude-3-sonnet-20240229", "usage": {"input_tokens": 1500, "output_tokens": 800, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}, "message_id": "test-msg-1", "request_id": "test-req-1"}
{"timestamp": "2024-01-15T10:35:00Z", "model": "claude-3-sonnet-20240229", "usage": {"input_tokens": 2000, "output_tokens": 1200, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}, "message_id": "test-msg-2", "request_id": "test-req-2"}
{"timestamp": "2024-01-15T10:40:00Z", "model": "claude-3-sonnet-20240229", "usage": {"input_tokens": 1800, "output_tokens": 900, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}, "message_id": "test-msg-3", "request_id": "test-req-3"}
EOF
        log_success "Test data created successfully"
    fi
    
    log_info "Test data initialization complete"
    validate_volume
}

# Main execution
main() {
    case "$COMMAND" in
        validate)
            validate_volume
            case $? in
                0) log_success "Volume validation passed" ;;
                1) log_error "Volume validation failed"; exit 1 ;;
                2) log_warn "Volume validation passed with warnings" ;;
            esac
            ;;
        info)
            show_info
            ;;
        init)
            init_test_data
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Parse arguments and run
parse_args "$@"
main
