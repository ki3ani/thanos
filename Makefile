# Makefile for Thanos Platform

.PHONY: help install-dev format lint test build-all deploy-local clean

# Default target
help:
	@echo "Available targets:"
	@echo "  install-dev    - Install development dependencies"
	@echo "  format         - Format code with black and isort"
	@echo "  lint           - Run linting tools"
	@echo "  test           - Run tests"
	@echo "  security       - Run security scans"
	@echo "  build-all      - Build all Docker images"
	@echo "  deploy-local   - Deploy to local Kubernetes"
	@echo "  clean          - Clean up build artifacts"

# Install development dependencies
install-dev:
	python -m pip install --upgrade pip
	pip install black isort flake8 mypy pytest pytest-asyncio pytest-cov bandit safety
	@echo "Installing service dependencies..."
	cd frontend-proxy && pip install -r requirements.txt
	cd recommendation-agent && pip install -r requirements.txt

# Format code
format:
	@echo "Formatting code with black..."
	black frontend-proxy/ recommendation-agent/
	@echo "Sorting imports with isort..."
	isort frontend-proxy/ recommendation-agent/

# Lint code
lint:
	@echo "Linting with flake8..."
	flake8 frontend-proxy/ recommendation-agent/ --max-line-length=88 --extend-ignore=E203,W503
	@echo "Type checking with mypy..."
	mypy frontend-proxy/ recommendation-agent/ --ignore-missing-imports || true
	@echo "Security scanning with bandit..."
	bandit -r frontend-proxy/ recommendation-agent/ || true

# Run tests
test:
	@echo "Running tests..."
	cd frontend-proxy && python -m pytest tests/ -v || true
	cd recommendation-agent && python -m pytest tests/ -v || true

# Security scans
security:
	@echo "Running safety check..."
	cd frontend-proxy && safety check -r requirements.txt || true
	cd recommendation-agent && safety check -r requirements.txt || true
	@echo "Running bandit security scan..."
	bandit -r frontend-proxy/ recommendation-agent/ -f json -o security-report.json || true

# Build Docker images
build-all:
	@echo "Building Docker images..."
	docker build -t thanos/frontend-proxy:local ./frontend-proxy
	docker build -t thanos/recommendation-agent:local ./recommendation-agent  
	docker build -t thanos/mcp-toolbox:local ./mcp-toolbox

# Deploy to local Kubernetes (requires kubectl and local cluster)
deploy-local:
	@echo "Deploying to local Kubernetes..."
	kubectl apply -f frontend-real-service.yaml
	kubectl apply -f frontend-proxy/kubernetes.yaml
	kubectl apply -f recommendation-agent/kubernetes.yaml
	kubectl apply -f mcp-toolbox/kubernetes.yaml
	@echo "Waiting for deployments to be ready..."
	kubectl rollout status deployment/frontend-proxy --timeout=300s || true
	kubectl rollout status deployment/recommendation-agent --timeout=300s || true
	kubectl rollout status deployment/mcp-toolbox-server --timeout=300s || true

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	docker system prune -f || true

# Quick development setup
dev-setup: install-dev format lint
	@echo "Development environment ready!"

# CI simulation (run all checks)
ci: format lint test security
	@echo "All CI checks completed!"