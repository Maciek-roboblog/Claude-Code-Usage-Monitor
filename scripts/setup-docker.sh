#!/usr/bin/env bash
# Claude Monitor - Automated Docker Configuration (Linux/macOS)
# This script automatically configures the Docker environment for Claude Monitor

set -euo pipefail

# Configuration
PROJECT_NAME="Claude Code Usage Monitor"
IMAGE_NAME="claude-monitor"
CONTAINER_NAME="claude-usage-monitor"
COMPOSE_PROJECT="claude-code-usage-monitor"

# Colors for display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Utility functions
log_info() {
    [[ ${quiet:-false} == true ]] && return
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    [[ ${quiet:-false} == true ]] && return
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    [[ ${quiet:-false} == true ]] && return
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"   # errors should always show
}

# Echo function that respects quiet mode
quiet_echo() {
    [[ ${quiet:-false} == true ]] && return
    echo "$@"
}

# Detect Docker Compose command
detect_compose_command() {
    if command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    else
        compose_cmd="docker compose"
    fi
}

# Prerequisite checks
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi
    
    # Detect and set compose command
    detect_compose_command
    
    # Check Docker Compose (v1 or v2) using the previously detected command
    if ! ${compose_cmd} version &> /dev/null; then
        log_error "Docker Compose is not installed or not functioning."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    log_success "Prerequisites verified (using: $compose_cmd)"
}

# Automatic detection of Claude data
detect_claude_data() {
    log_info "Detecting Claude data..."
    
    local claude_paths=(
        "$HOME/.claude/projects"
        "$HOME/.config/claude/projects"
        "$HOME/Library/Application Support/Claude/projects"
        "$HOME/AppData/Local/Claude/projects"
        "$HOME/AppData/Roaming/Claude/projects"
    )
    
    for path in "${claude_paths[@]}"; do
        shopt -s nullglob
        jsonl_files=("$path"/*.jsonl)
        shopt -u nullglob
        if [[ -d "$path" && ${#jsonl_files[@]} -gt 0 ]]; then
            CLAUDE_DATA_PATH="$path"
            log_success "Claude data found: $CLAUDE_DATA_PATH"
            return 0
        fi
    done
    
    # Advanced search
    log_warning "Advanced search for Claude data..."
    local found_path
    found_path=$(find "$HOME" -maxdepth 5 -name "*.jsonl" -path "*claude*" -print -quit 2>/dev/null | head -1)
    
    if [ -n "$found_path" ]; then
        CLAUDE_DATA_PATH=$(dirname "$found_path")
        log_success "Claude data found: $CLAUDE_DATA_PATH"
        return 0
    fi
    
    log_warning "No Claude data found automatically."
    
    if [[ ${quiet:-false} == true ]]; then
        log_error "Claude data path required in quiet mode. Use --data-path option."
        exit 1
    fi
    
    read -p "Please enter the path to your Claude data: " CLAUDE_DATA_PATH
    
    if [ ! -d "$CLAUDE_DATA_PATH" ]; then
        log_error "The specified path does not exist: $CLAUDE_DATA_PATH"
        exit 1
    fi
}

# Cleanup existing resources
cleanup_existing() {
    log_info "Cleaning up existing resources..."
    
    # Stop existing containers
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    $compose_cmd down 2>/dev/null || true
    
    # Remove existing containers
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    log_success "Cleanup complete"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    # Build with optimizations
    DOCKER_BUILDKIT=1 docker build \
        --target runtime \
        --tag "$IMAGE_NAME:latest" \
        --tag "$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)" \
        . || {
        log_error "Image build failed"
        exit 1
    }
    
    log_success "Docker image built: $IMAGE_NAME:latest"
    
    # Show image size
    local image_size
    image_size=$(docker images "$IMAGE_NAME:latest" --format "table {{.Size}}" | tail -1)
    log_info "Image size: $image_size"
}

# Docker Compose configuration
setup_compose() {
    log_info "Configuring Docker Compose..."
    
    # Create a local .env file if needed
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Docker Compose configuration for Claude Monitor
CLAUDE_DATA_PATH=$CLAUDE_DATA_PATH
CLAUDE_PLAN=pro
CLAUDE_TIMEZONE=UTC
CLAUDE_THEME=auto
CLAUDE_DEBUG_MODE=false
COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT
EOF
        log_success ".env file created"
    fi
    
    # Validate configuration
    $compose_cmd config > /dev/null || {
        log_error "Invalid Docker Compose configuration"
        exit 1
    }
    
    log_success "Docker Compose configuration validated"
}

# Installation test
test_installation() {
    log_info "Testing installation..."

    # Health check test with better error handling
    if docker run --rm \
        -v "$CLAUDE_DATA_PATH:/data:ro" \
        --entrypoint python \
        "$IMAGE_NAME:latest" \
        -c "
            import sys
            try:
                from usage_analyzer.api import analyze_usage
                result = analyze_usage()
                if isinstance(result, dict):
                    print(f'✅ Test passed: {len(result.get(\"blocks\", []))} blocks found')
                    sys.exit(0)
                else:
                    print('❌ Test failed: Invalid result type')
                    sys.exit(1)
            except Exception as e:
                print(f'❌ Test failed: {e}')
                sys.exit(1)
        " 2>&1; then
        log_success "Installation test passed"
    else
        log_error "Installation test failed - image may not be functional"
        exit 1
    fi
}

# Start the service
start_service() {
    log_info "Starting Claude Monitor service..."
    
    # In quiet mode, default to background mode
    if [[ ${quiet:-false} == true ]]; then
        log_info "Starting in background mode (quiet mode)..."
        $compose_cmd up -d
        log_success "Service started in background"
        log_info "Use '$compose_cmd logs -f' to view logs"
        log_info "Use '$compose_cmd down' to stop"
        return
    fi
    
    quiet_echo
    quiet_echo "Choose startup mode:"
    quiet_echo "1) Interactive mode (docker run)"
    quiet_echo "2) Service mode ($compose_cmd)"
    quiet_echo "3) Background mode ($compose_cmd -d)"
    quiet_echo
    read -p "Your choice (1-3): " choice
    
    case $choice in
        1)
            log_info "Starting in interactive mode..."
            docker run -it --rm \
                --name "$CONTAINER_NAME" \
                -v "$CLAUDE_DATA_PATH:/data:ro" \
                "$IMAGE_NAME:latest"
            ;;
        2)
            log_info "Starting with Docker Compose..."
            $compose_cmd up
            ;;
        3)
            log_info "Starting in background..."
            $compose_cmd up -d
            log_success "Service started in background"
            log_info "Use '$compose_cmd logs -f' to view logs"
            log_info "Use '$compose_cmd down' to stop"
            ;;
        *)
            log_warning "Invalid option. Starting in interactive mode by default..."
            docker run -it --rm \
                --name "$CONTAINER_NAME" \
                -v "$CLAUDE_DATA_PATH:/data:ro" \
                "$IMAGE_NAME:latest"
            ;;
    esac
}

# Show help
show_help() {
    cat << EOF
Claude Monitor - Docker Configuration Script

Usage: $0 [OPTIONS]

OPTIONS:
    --help, -h              Show this help
    --cleanup-only          Only clean up (no build)
    --build-only            Only build the image (no start)
    --no-start              Do not start the service
    --data-path PATH        Specify the path to Claude data
    --quiet                 Quiet mode

EXAMPLES:
    $0                      Full automatic configuration
    $0 --build-only         Only build the image
    $0 --data-path ~/.claude/projects
                            Use a specific path
    $0 --cleanup-only       Clean up existing resources

EOF
}

# Main function
main() {
    local cleanup_only=false
    local build_only=false
    local no_start=false
    local quiet=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --cleanup-only)
                cleanup_only=true
                shift
                ;;
            --build-only)
                build_only=true
                shift
                ;;
            --no-start)
                no_start=true
                shift
                ;;
            --data-path)
                if [[ $# -lt 2 ]]; then
                    log_error "--data-path requires a value"
                    show_help
                    exit 1
                fi
                CLAUDE_DATA_PATH="$2"
                shift 2
                ;;
            --quiet)
                quiet=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    quiet_echo "Docker Configuration - $PROJECT_NAME"
    quiet_echo "=================================================="
    quiet_echo
    
    check_prerequisites
    
    if [ "$cleanup_only" = true ]; then
        cleanup_existing
        log_success "Cleanup complete"
        exit 0
    fi
    
    if [ -z "${CLAUDE_DATA_PATH:-}" ]; then
        detect_claude_data
    fi
    
    cleanup_existing
    build_image
    
    if [ "$build_only" = true ]; then
        log_success "Build complete"
        exit 0
    fi
    
    setup_compose
    test_installation
    
    if [ "$no_start" = false ]; then
        start_service
    fi
    
    quiet_echo
    quiet_echo "=================================================="
    log_success "Docker configuration completed successfully!"
    quiet_echo
    quiet_echo "Useful commands:"
    quiet_echo "  $compose_cmd up                 # Start"
    quiet_echo "  $compose_cmd down               # Stop"
    quiet_echo "  $compose_cmd logs -f            # View logs"
    quiet_echo "  docker exec -it $CONTAINER_NAME bash  # Enter the container"
    quiet_echo
    quiet_echo "Documentation: docs/docker/README.md"
}

# Run the script
main "$@"

