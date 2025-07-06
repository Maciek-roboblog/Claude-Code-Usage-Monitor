# Makefile for Claude Code Usage Monitor Docker operations
# Provides convenient commands for building, running, and managing the Docker container

# Variables
IMAGE_NAME = claude-monitor
IMAGE_TAG = latest
CONTAINER_NAME = claude-usage-monitor

# Default local Claude data path (adjust as needed)
CLAUDE_DATA_PATH ?= ~/.claude/projects

# Docker build arguments
DOCKER_BUILDKIT = 1

.PHONY: help build build-no-cache run run-detached run-custom up down stop clean logs shell test health

# Default target
help: ## Show this help message
	@echo "🐳 Claude Code Usage Monitor - Docker Commands"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Build targets
build: ## Build production Docker image
	@echo "🔨 Building production image..."
	DOCKER_BUILDKIT=$(DOCKER_BUILDKIT) docker build \
		--target runtime \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):$(shell date +%Y%m%d-%H%M%S) \
		.
	@echo "✅ Production image built: $(IMAGE_NAME):$(IMAGE_TAG)"

build-no-cache: ## Build production image without cache
	@echo "🔨 Building production image (no cache)..."
	DOCKER_BUILDKIT=$(DOCKER_BUILDKIT) docker build \
		--no-cache \
		--target runtime \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		.

# Run targets
run: ## Run production container
	@echo "🚀 Starting production container..."
	@echo "📁 Using Claude data path: $(CLAUDE_DATA_PATH)"
	@if [ ! -d "$(shell eval echo $(CLAUDE_DATA_PATH))" ]; then \
		echo "❌ Error: Claude data path $(CLAUDE_DATA_PATH) does not exist"; \
		echo "Please set CLAUDE_DATA_PATH or ensure ~/.claude/projects exists"; \
		exit 1; \
	fi
	docker run -it --rm \
		--name $(CONTAINER_NAME) \
		-v $(CLAUDE_DATA_PATH):/data:ro \
		$(IMAGE_NAME):$(IMAGE_TAG)

run-dev: ## Run development container
	@echo "🚀 Starting development container..."
	docker-compose up

run-detached: ## Run production container in background
	@echo "🚀 Starting production container (detached)..."
	docker run -d \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-v $(CLAUDE_DATA_PATH):/data:ro \
		$(IMAGE_NAME):$(IMAGE_TAG)

run-custom: ## Run container with custom environment (PLAN=max5 TIMEZONE=UTC make run-custom)
	@echo "🚀 Starting container with custom config..."
	docker run -it --rm \
		--name $(CONTAINER_NAME)-custom \
		-v $(CLAUDE_DATA_PATH):/data:ro \
		-e CLAUDE_PLAN=$(PLAN) \
		-e CLAUDE_TIMEZONE=$(TIMEZONE) \
		-e CLAUDE_THEME=$(THEME) \
		-e CLAUDE_DEBUG_MODE=$(DEBUG) \
		$(IMAGE_NAME):$(IMAGE_TAG)

# Compose targets
up: ## Start services with docker-compose
	@echo "🚀 Starting services with docker-compose..."
	docker-compose up

up-dev: ## Start development services
	@echo "🚀 Starting development services..."
	docker-compose up

down: ## Stop and remove docker-compose services
	@echo "🛑 Stopping docker-compose services..."
	docker-compose down

# Management targets
stop: ## Stop running containers
	@echo "🛑 Stopping containers..."
	-docker stop $(CONTAINER_NAME) 2>/dev/null || true
	-docker-compose down 2>/dev/null || true

clean: ## Remove containers and images
	@echo "🧹 Cleaning up..."
	-docker stop $(CONTAINER_NAME) 2>/dev/null || true
	-docker rm $(CONTAINER_NAME) 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	-docker-compose down --rmi all 2>/dev/null || true

clean-all: ## Remove everything including volumes
	@echo "🧹 Full cleanup (including volumes)..."
	-docker-compose down --volumes --rmi all 2>/dev/null || true
	-docker system prune -f

# Utility targets
logs: ## Show container logs
	@echo "📋 Container logs:"
	@if docker ps | grep -q $(CONTAINER_NAME); then \
		docker logs -f $(CONTAINER_NAME); \
	elif docker-compose ps | grep -q claude-monitor; then \
		docker-compose logs -f; \
	else \
		echo "No running containers found"; \
	fi

shell: ## Open shell in running container
	@echo "🐚 Opening shell..."
	@if docker ps | grep -q $(CONTAINER_NAME); then \
		docker exec -it $(CONTAINER_NAME) /bin/bash; \
	elif docker-compose ps | grep -q claude-monitor; then \
		docker-compose exec claude-monitor /bin/bash; \
	else \
		echo "No running containers found. Starting temporary container..."; \
		docker run -it --rm \
			-v $(CLAUDE_DATA_PATH):/data:ro \
			--entrypoint /bin/bash \
			$(IMAGE_NAME):$(IMAGE_TAG); \
	fi

test: ## Test the application in container
	@echo "🧪 Testing application..."
	docker run --rm \
		-v $(CLAUDE_DATA_PATH):/data:ro \
		--entrypoint python \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		-c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print(f'✅ Test passed: {len(result.get(\"blocks\", []))} blocks found')"

health: ## Check container health
	@echo "🔍 Checking container health..."
	@if docker ps | grep -q $(CONTAINER_NAME); then \
		docker exec $(CONTAINER_NAME) python -c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print(f'✅ Health OK: {len(result.get(\"blocks\", []))} blocks')"; \
	else \
		echo "❌ Container not running"; \
		exit 1; \
	fi

# Info targets
info: ## Show Docker environment info
	@echo "ℹ️ Docker Environment Info:"
	@echo "  Image: $(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "  Container: $(CONTAINER_NAME)"
	@echo "  Claude Data Path: $(CLAUDE_DATA_PATH)"
	@echo "  Docker Buildkit: $(DOCKER_BUILDKIT)"
	@echo ""
	@echo "🐳 Docker Version:"
	@docker version --format "  Client: {{.Client.Version}} | Server: {{.Server.Version}}"
	@echo ""
	@echo "📦 Available Images:"
	@docker images | grep $(IMAGE_NAME) || echo "  No $(IMAGE_NAME) images found"

size: ## Show image sizes
	@echo "📏 Image Sizes:"
	@docker images | head -1
	@docker images | grep $(IMAGE_NAME) || echo "No $(IMAGE_NAME) images found"

# Example commands
examples: ## Show usage examples
	@echo "📚 Usage Examples:"
	@echo ""
	@echo "  Basic usage:"
	@echo "    make build && make run"
	@echo ""
	@echo "  Custom configuration:"
	@echo "    PLAN=max5 TIMEZONE=US/Eastern make run-custom"
	@echo ""
	@echo "  Background run:"
	@echo "    make run-detached"
	@echo ""
	@echo "  Custom data path:"
	@echo "    CLAUDE_DATA_PATH=/custom/path make run"
	@echo ""
	@echo "  Docker Compose:"
	@echo "    make up      # Start with compose"
	@echo "    make down    # Stop compose services"
