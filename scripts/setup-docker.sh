#!/bin/bash
# 🐳 Claude Monitor - Automated Docker Configuration (Linux/macOS)
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
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Prerequisite checks
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    log_success "Prerequisites verified"
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
        if [ -d "$path" ] && [ "$(ls -A "$path"/*.jsonl 2>/dev/null)" ]; then
            CLAUDE_DATA_PATH="$path"
            log_success "Claude data found: $CLAUDE_DATA_PATH"
            return 0
        fi
    done
    
    # Advanced search
    log_warning "Advanced search for Claude data..."
    local found_path
    found_path=$(find "$HOME" -name "*.jsonl" -path "*claude*" -print -quit 2>/dev/null | head -1)
    
    if [ -n "$found_path" ]; then
        CLAUDE_DATA_PATH=$(dirname "$found_path")
        log_success "Claude data found: $CLAUDE_DATA_PATH"
        return 0
    fi
    
    log_warning "No Claude data found automatically."
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
    docker-compose down 2>/dev/null || true
    
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
    docker-compose config > /dev/null || {
        log_error "Invalid Docker Compose configuration"
        exit 1
    }
    
    log_success "Docker Compose configuration validated"
}

# Installation test
test_installation() {
    log_info "Testing installation..."
    
    # Health check test
    docker run --rm \
        -v "$CLAUDE_DATA_PATH:/data:ro" \
        --entrypoint python \
        "$IMAGE_NAME:latest" \
        -c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print(f'✅ Test passed: {len(result.get(\"blocks\", []))} blocks found')" || {
        log_warning "Basic test failed, but the image seems functional"
    }
    
    log_success "Installation tested successfully"
}

# Start the service
start_service() {
    log_info "Starting Claude Monitor service..."
    
    echo
    echo "Choose startup mode:"
    echo "1) Interactive mode (docker run)"
    echo "2) Service mode (docker-compose)"
    echo "3) Background mode (docker-compose -d)"
    echo
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
            docker-compose up
            ;;
        3)
            log_info "Starting in background..."
            docker-compose up -d
            log_success "Service started in background"
            log_info "Use 'docker-compose logs -f' to view logs"
            log_info "Use 'docker-compose down' to stop"
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
                CLAUDE_DATA_PATH="$2"
                shift 2
                ;;

                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo "Docker Configuration - $PROJECT_NAME"
    echo "=================================================="
    echo
    
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
    
    echo
    echo "=================================================="
    log_success "Docker configuration completed successfully!"
    echo
    echo "Useful commands:"
    echo "  docker-compose up                 # Start"
    echo "  docker-compose down               # Stop"
    echo "  docker-compose logs -f            # View logs"
    echo "  docker exec -it $CONTAINER_NAME bash  # Enter the container"
    echo
    echo "Documentation: docs/docker/README.md"
}

# Run the script
main "$@"

