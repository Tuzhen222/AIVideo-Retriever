.PHONY: help clean clean-all clean-files clean-docker clean-volumes clean-networks clean-images clean-cache clean-unused clean-pycache start stop restart build build-dev rebuild rebuild-dev logs es-ingest es-status es-logs kibana-logs kibana-status kibana-open

# Default target
help:
	@echo "Available commands:"
	@echo "  make start          - Start all services"
	@echo "  make start-dev      - Start development services (detached, hot-reload)"
	@echo "  make dev            - Run dev services in foreground (hot-reload + live logs)"
	@echo "  make dev-up         - Run dev services detached (hot-reload)"
	@echo "  make dev-logs       - Tail logs from dev services"
	@echo "  make dev-restart    - Restart dev services (hot-reload stack)"
	@echo "  make dev-reload-env - Reload .env file (restart backend only)"
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
	@echo "  make clean-images    - Remove project images"
	@echo "  make clean-cache     - Remove build cache"
	@echo "  make clean-unused    - Remove all unused images and volumes (frees most space)"
	@echo "  make clean-pycache   - Remove Python cache files (__pycache__, *.pyc)"
	@echo ""
	@echo "Elasticsearch commands:"
	@echo "  make es-ingest       - Ingest JSON files into Elasticsearch"
	@echo "  make es-status       - Check Elasticsearch cluster status"
	@echo "  make es-logs         - Show Elasticsearch logs"
	@echo "  make kibana-logs     - Show Kibana logs"
	@echo "  make kibana-status   - Check Kibana API status"
	@echo "  make kibana-open     - Open Kibana in browser"

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

dev:
	@echo "🛑 Stopping production services first..."
	-docker-compose down 2>/dev/null || true
	@echo "🚀 Starting development services (foreground, with logs)..."
	docker-compose -f docker-compose.dev.yml up --build

dev-up:
	@echo "🛑 Stopping production services first..."
	-docker-compose down 2>/dev/null || true
	@echo "🚀 Starting development services (detached)..."
	docker-compose -f docker-compose.dev.yml up -d --build
	@echo "✅ Development services started (detached)"

dev-logs:
	@echo "📜 Tailing development logs..."
	docker-compose -f docker-compose.dev.yml logs -f

dev-restart:
	@echo "🔄 Restarting development services..."
	docker-compose -f docker-compose.dev.yml restart backend frontend
	@echo "✅ Development services restarted"

dev-reload-env:
	@echo "🔄 Reloading .env file (down/up backend to reload env)..."
	docker-compose -f docker-compose.dev.yml stop backend
	docker-compose -f docker-compose.dev.yml up -d backend
	@echo "✅ Backend restarted with new .env settings"

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
	-docker rm -f aivideo-backend aivideo-frontend aivideo-backend-dev aivideo-frontend-dev aivideo-elasticsearch aivideo-kibana aivideo-elasticsearch-dev aivideo-kibana-dev aivideo-qdrant aivideo-qdrant-dev 2>/dev/null || true
	-docker ps -a --filter "name=aivideo" -q | xargs -r docker rm -f 2>/dev/null || true
	@echo "✅ Docker containers removed"

clean-volumes:
	@echo "🧹 Removing Docker volumes..."
	-docker-compose down -v 2>/dev/null || true
	-docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true
	-docker volume ls --filter "name=aivideo" -q | xargs -r docker volume rm 2>/dev/null || true
	-docker volume ls --filter "name=elasticsearch" -q | xargs -r docker volume rm 2>/dev/null || true
	-docker volume ls --filter "name=qdrant" -q | xargs -r docker volume rm 2>/dev/null || true
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

clean-unused:
	@echo "🧹 Removing all unused Docker images and volumes..."
	@echo "📊 Current Docker disk usage:"
	@docker system df
	@echo ""
	@echo "🗑️  Removing unused images..."
	-docker image prune -a -f 2>/dev/null || echo "⚠️  Some images may be in use or prune already running"
	@echo "🗑️  Removing unused volumes..."
	-docker volume prune -f 2>/dev/null || echo "⚠️  Some volumes may be in use or prune already running"
	@echo "📊 Docker disk usage after cleanup:"
	@docker system df
	@echo "✅ Unused Docker images and volumes removed"

# Clean all Docker resources
clean-all: clean clean-images clean-cache clean-unused
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

# Elasticsearch commands
es-ingest:
	@echo "📦 Ingesting JSON files into Elasticsearch..."
	@docker-compose exec backend python -m app.services.elastic_search.ingest || \
	 docker-compose -f docker-compose.dev.yml exec backend python -m app.services.elastic_search.ingest || \
	 echo "⚠️  Please ensure services are running and backend container is available"

es-status:
	@echo "🔍 Checking Elasticsearch cluster status..."
	@curl -s http://localhost:9200/_cluster/health?pretty || \
	 echo "⚠️  Elasticsearch is not running or not accessible at http://localhost:9200"

es-logs:
	@echo "📋 Elasticsearch logs (Ctrl+C to exit)..."
	@docker-compose logs -f elasticsearch || \
	 docker-compose -f docker-compose.dev.yml logs -f elasticsearch || \
	 echo "⚠️  Elasticsearch container not found"

kibana-logs:
	@echo "📋 Kibana logs (Ctrl+C to exit)..."
	@docker-compose logs -f kibana || \
	 docker-compose -f docker-compose.dev.yml logs -f kibana || \
	 echo "⚠️  Kibana container not found"

kibana-status:
	@echo "🔍 Checking Kibana status..."
	@curl -s http://localhost:5601/api/status | python3 -m json.tool 2>/dev/null || \
	 curl -s http://localhost:5601/api/status || \
	 echo "⚠️  Kibana is not running or not accessible at http://localhost:5601"

kibana-open:
	@echo "🌐 Opening Kibana in browser..."
	@echo "   URL: http://localhost:5601"
	@which xdg-open >/dev/null 2>&1 && xdg-open http://localhost:5601 || \
	 which open >/dev/null 2>&1 && open http://localhost:5601 || \
	 which start >/dev/null 2>&1 && start http://localhost:5601 || \
	 echo "⚠️  Please open http://localhost:5601 manually in your browser"

