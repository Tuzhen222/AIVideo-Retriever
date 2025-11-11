.PHONY: help clean clean-all clean-files clean-docker clean-volumes clean-networks clean-images clean-cache clean-pycache start stop restart build build-dev rebuild rebuild-dev logs

# Default target
help:
	@echo "Available commands:"
	@echo "  make start          - Start all services"
	@echo "  make start-dev      - Start development services with hot-reload"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make build           - Build all images"
	@echo "  make build-dev       - Build development images"
	@echo "  make rebuild         - Rebuild all images (no cache)"
	@echo "  make rebuild-dev     - Rebuild development images (no cache)"
	@echo "  make logs            - Show logs from all services"
	@echo "  make clean           - Remove containers, volumes, networks"
	@echo "  make clean-all       - Remove everything (containers, volumes, networks, images, cache)"
	@echo "  make clean-files     - Remove temporary files (logs, cache, etc.)"
	@echo "  make clean-docker    - Remove all Docker resources"
	@echo "  make clean-volumes   - Remove all volumes"
	@echo "  make clean-networks  - Remove all networks"
	@echo "  make clean-images    - Remove all images"
	@echo "  make clean-cache     - Remove build cache"
	@echo "  make clean-pycache   - Remove Python cache files (__pycache__, *.pyc)"

# Start services
start:
	@echo "🛑 Stopping dev services first..."
	-docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	@echo "🚀 Starting production services..."
	docker-compose up -d
	@echo "✅ Production services started"

start-dev:
	@echo "🛑 Stopping production services first..."
	-docker-compose down 2>/dev/null || true
	@echo "🚀 Starting development services..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Development services started"

# Stop services
stop:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

# Restart services
restart: stop start

# Build images
build:
	docker-compose build

build-dev:
	docker-compose -f docker-compose.dev.yml build

rebuild:
	docker-compose build --no-cache

rebuild-dev:
	docker-compose -f docker-compose.dev.yml build --no-cache

# View logs
logs:
	docker-compose logs -f

# Clean Docker resources
clean: clean-docker clean-volumes clean-networks
	@echo "✅ Cleaned Docker containers, volumes, and networks"

clean-docker:
	@echo "🧹 Removing Docker containers..."
	-docker-compose down --remove-orphans 2>/dev/null || true
	-docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true
	-docker rm -f aivideo-backend aivideo-frontend aivideo-backend-dev aivideo-frontend-dev 2>/dev/null || true
	-docker ps -a --filter "name=aivideo" -q | xargs -r docker rm -f 2>/dev/null || true
	@echo "✅ Docker containers removed"

clean-volumes:
	@echo "🧹 Removing Docker volumes..."
	-docker-compose down -v 2>/dev/null || true
	-docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true
	-docker volume ls --filter "name=aivideo" -q | xargs -r docker volume rm 2>/dev/null || true
	@echo "✅ Docker volumes removed"

clean-networks:
	@echo "🧹 Removing Docker networks..."
	-docker network rm aivideo-network 2>/dev/null || true
	-docker network ls --filter "name=aivideo" -q | xargs -r docker network rm 2>/dev/null || true
	@echo "✅ Docker networks removed"

clean-images:
	@echo "🧹 Removing Docker images..."
	-docker images --filter "reference=*aivideo*" -q | xargs -r docker rmi -f 2>/dev/null || true
	-docker images --filter "reference=*backend*" -q | xargs -r docker rmi -f 2>/dev/null || true
	-docker images --filter "reference=*frontend*" -q | xargs -r docker rmi -f 2>/dev/null || true
	@echo "✅ Docker images removed"

clean-cache:
	@echo "🧹 Removing Docker build cache..."
	-docker builder prune -af
	@echo "✅ Docker build cache removed"

# Clean all Docker resources
clean-all: clean clean-images clean-cache
	@echo "✅ Cleaned all Docker resources"

# Clean Python cache
clean-pycache:
	@echo "🧹 Removing Python cache files..."
	-find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	-find . -type f -name "*.pyc" -delete 2>/dev/null || true
	-find . -type f -name "*.pyo" -delete 2>/dev/null || true
	-find . -type f -name "*.pyd" -delete 2>/dev/null || true
	-find . -type f -name ".Python" -delete 2>/dev/null || true
	@echo "✅ Python cache files removed"

# Clean temporary files
clean-files: clean-pycache
	@echo "🧹 Removing other temporary files..."
	@# Python build artifacts (pycache already cleaned above)
	-find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".eggs" -exec rm -rf {} + 2>/dev/null || true
	@# Node modules cache
	-find . -type d -name "node_modules/.cache" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".vite" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".nuxt" -exec rm -rf {} + 2>/dev/null || true
	@# Logs (keep directory structure)
	-find . -type f -name "*.log" -not -path "*/node_modules/*" -delete 2>/dev/null || true
	-find . -type f -name "*.log.*" -not -path "*/node_modules/*" -delete 2>/dev/null || true
	@# OS files
	-find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	-find . -type f -name "Thumbs.db" -delete 2>/dev/null || true
	@# IDE files
	-find . -type d -name ".idea" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".vscode" -exec rm -rf {} + 2>/dev/null || true
	-find . -type f -name "*.swp" -delete 2>/dev/null || true
	-find . -type f -name "*.swo" -delete 2>/dev/null || true
	-find . -type f -name "*~" -delete 2>/dev/null || true
	@# Test artifacts
	-find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	-find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@# Jupyter
	-find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Temporary files removed"

# Full clean (Docker + files)
clean-full: clean-all clean-files
	@echo "✅ Full clean completed - Docker resources and temporary files removed"

